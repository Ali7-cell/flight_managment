import uuid
import threading
from datetime import timedelta
from decimal import Decimal
from typing import Any
from sqlalchemy.orm import Session
from sqlalchemy import select
from flight_domain.models.flights import SeatClass, Flight
from flight_domain.models.bookings import SeatHold, WaitlistEntry, Booking
from flight_domain.models.auth import Passenger
from flight_domain.models.plumbing import IdempotencyKey
from flight_domain.models.base import utcnow
from flight_domain.domain.audit import record_audit_log
from flight_domain.domain.outbox import emit_event

# Mutex to emulate PostgreSQL row-locking when executing in SQLite test environments
_sqlite_seat_lock = threading.Lock()

def hold_seats(
    session: Session,
    *,
    flight_id: uuid.UUID | str,
    seat_class_id: uuid.UUID | str,
    quantity: int,
    passenger_email: str,
    passenger_name: str,
    idempotency_key: str | None = None,
    endpoint: str = "/bookings/hold",
    request_hash: str = "",
    actor: str = "system:fastapi",
    hold_duration_minutes: int = 15,
) -> dict[str, Any]:
    """
    Atomic seat hold inside one transaction.
    Uses SELECT ... FOR UPDATE (blocking) on seat_classes.
    """
    if isinstance(flight_id, str):
        flight_id = uuid.UUID(flight_id)
    if isinstance(seat_class_id, str):
        seat_class_id = uuid.UUID(seat_class_id)

    # 1. Idempotency check inside same transaction
    if idempotency_key:
        cached = session.get(IdempotencyKey, idempotency_key)
        if cached and cached.response_snapshot_json:
            return cached.response_snapshot_json

    # 2. Lock seat class row (blocking FOR UPDATE)
    stmt = (
        select(SeatClass)
        .where(SeatClass.id == seat_class_id)
        .with_for_update()
    )
    seat_class = session.scalar(stmt)
    if not seat_class:
        raise ValueError(f"Seat class {seat_class_id} not found.")

    available = seat_class.total_seats - (seat_class.booked_seats + seat_class.held_seats)
    if available < quantity:
        raise ValueError(f"Insufficient seats available. Requested: {quantity}, Available: {available}")

    # 3. Lookup or create passenger
    passenger = session.scalar(
        select(Passenger).where(Passenger.email == passenger_email)
    )
    if not passenger:
        passenger = Passenger(
            email=passenger_email,
            full_name=passenger_name,
            loyalty_tier="none",
        )
        session.add(passenger)
        session.flush()

    # 4. Mutate seat count and record hold
    before_state = {"held_seats": seat_class.held_seats, "booked_seats": seat_class.booked_seats}
    seat_class.held_seats += quantity
    after_state = {"held_seats": seat_class.held_seats, "booked_seats": seat_class.booked_seats}

    expires_at = utcnow() + timedelta(minutes=hold_duration_minutes)
    hold = SeatHold(
        seat_class_id=seat_class_id,
        passenger_id=passenger.id,
        quantity=quantity,
        status="active",
        idempotency_key=idempotency_key,
        expires_at=expires_at,
    )
    session.add(hold)
    session.flush()

    # 5. Outbox & Audit Log
    record_audit_log(
        session,
        actor_type=actor,
        actor_id=str(passenger.id),
        action="hold_seats",
        entity_type="seat_classes",
        entity_id=seat_class_id,
        before_json=before_state,
        after_json=after_state,
    )

    emit_event(
        session,
        event_type="seat_held",
        payload_json={
            "hold_id": str(hold.id),
            "seat_class_id": str(seat_class_id),
            "quantity": quantity,
            "expires_at": expires_at.isoformat(),
        },
    )

    total_fare = Decimal(str(seat_class.fare_base_amount)) * quantity
    response_data = {
        "hold_id": str(hold.id),
        "seat_class_id": str(seat_class_id),
        "quantity": quantity,
        "expires_at": expires_at.isoformat(),
        "fare_amount": str(total_fare),
        "currency": seat_class.currency,
    }

    # 6. Save Idempotency Snapshot
    if idempotency_key:
        idem = IdempotencyKey(
            key=idempotency_key,
            endpoint=endpoint,
            request_hash=request_hash,
            response_snapshot_json=response_data,
        )
        session.add(idem)

    return response_data

def group_hold_seats(
    session: Session,
    *,
    flight_id: uuid.UUID | str,
    seat_class_id: uuid.UUID | str,
    quantity: int,
    passenger_email: str,
    passenger_name: str,
    idempotency_key: str | None = None,
    actor: str = "system:fastapi",
) -> dict[str, Any]:
    """
    Group booking hold with full-fail policy per PRD §3.
    If fewer than `quantity` seats are available, immediately fails with waitlist suggestion.
    """
    if quantity < 2:
        raise ValueError("Group hold requires quantity > 1.")
    try:
        return hold_seats(
            session,
            flight_id=flight_id,
            seat_class_id=seat_class_id,
            quantity=quantity,
            passenger_email=passenger_email,
            passenger_name=passenger_name,
            idempotency_key=idempotency_key,
            endpoint="/bookings/group-hold",
            actor=actor,
        )
    except ValueError as e:
        if "Insufficient seats" in str(e):
            raise ValueError(
                f"Full-fail group hold policy: Cannot fulfill requested {quantity} seats in single block. "
                "Immediate waitlist offer available."
            )
        raise

def release_seat_and_promote(
    session: Session,
    *,
    seat_class_id: uuid.UUID | str,
    quantity: int = 1,
    actor: str = "system",
) -> dict[str, Any]:
    """
    Core conflict-resolution function:
    1. SELECT ... FOR UPDATE (blocking) on seat_classes
    2. Decrement booked_seats (or held_seats if converting/releasing)
    3. Look for waitlist candidates using SELECT ... FOR UPDATE SKIP LOCKED
    4. If found, promote candidate and re-increment booked_seats
    5. Emit events and audit log in the same transaction
    """
    if isinstance(seat_class_id, str):
        seat_class_id = uuid.UUID(seat_class_id)

    is_sqlite = session.bind and session.bind.dialect.name == "sqlite"
    if is_sqlite:
        _sqlite_seat_lock.acquire()

    try:
        # 1. Blocking lock on seat_classes
        stmt = (
            select(SeatClass)
            .where(SeatClass.id == seat_class_id)
            .with_for_update()
        )
        seat_class = session.scalar(stmt)
        if not seat_class:
            raise ValueError(f"SeatClass {seat_class_id} not found.")

        before_booked = seat_class.booked_seats
        if seat_class.booked_seats >= quantity:
            seat_class.booked_seats -= quantity
        else:
            seat_class.booked_seats = 0

        # 2. Look for waitlisted candidate using SKIP LOCKED
        wl_stmt = (
            select(WaitlistEntry)
            .where(
                WaitlistEntry.seat_class_id == seat_class_id,
                WaitlistEntry.status == "waiting",
                WaitlistEntry.quantity <= quantity,
            )
            .order_by(WaitlistEntry.priority_score.desc(), WaitlistEntry.created_at.asc())
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        candidate = session.scalar(wl_stmt)

        promoted_info = None
        if candidate:
            # Promote candidate
            candidate.status = "promoted"
            candidate.offer_expires_at = utcnow() + timedelta(hours=24)
            seat_class.booked_seats += candidate.quantity

            promoted_info = {
                "waitlist_entry_id": str(candidate.id),
                "passenger_id": str(candidate.passenger_id),
                "quantity": candidate.quantity,
                "priority_score": float(candidate.priority_score),
            }

            emit_event(
                session,
                event_type="waitlist_promoted",
                payload_json={
                    "seat_class_id": str(seat_class_id),
                    "waitlist_entry_id": str(candidate.id),
                    "passenger_id": str(candidate.passenger_id),
                    "quantity": candidate.quantity,
                },
            )
        else:
            # No candidate found; seat remains released to inventory
            emit_event(
                session,
                event_type="seat_released",
                payload_json={
                    "seat_class_id": str(seat_class_id),
                    "quantity": quantity,
                    "freed_at": utcnow().isoformat(),
                },
            )

        record_audit_log(
            session,
            actor_type=actor,
            actor_id=None,
            action="release_seat_and_promote",
            entity_type="seat_classes",
            entity_id=seat_class_id,
            before_json={"booked_seats": before_booked},
            after_json={"booked_seats": seat_class.booked_seats, "promoted": promoted_info is not None},
        )

        session.flush()
        if is_sqlite:
            session.commit()

        return {
            "seat_class_id": str(seat_class_id),
            "promoted": promoted_info is not None,
            "candidate": promoted_info,
            "booked_seats": seat_class.booked_seats,
            "total_seats": seat_class.total_seats,
        }
    finally:
        if is_sqlite:
            _sqlite_seat_lock.release()

def resize_seat_class(
    session: Session,
    *,
    seat_class_id: uuid.UUID | str,
    new_total_seats: int,
    actor: str = "human:super_admin",
) -> dict[str, Any]:
    """
    Adjust seat class allocation.
    Cannot shrink a class below its already-booked count (PRD §1).
    Trigger trg_seat_classes_no_shrink acts as the database-level backstop.
    """
    if isinstance(seat_class_id, str):
        seat_class_id = uuid.UUID(seat_class_id)

    stmt = (
        select(SeatClass)
        .where(SeatClass.id == seat_class_id)
        .with_for_update()
    )
    seat_class = session.scalar(stmt)
    if not seat_class:
        raise ValueError(f"SeatClass {seat_class_id} not found.")

    if new_total_seats < seat_class.booked_seats:
        raise ValueError(
            f"cannot shrink seat_classes {seat_class_id} total to {new_total_seats} below booked_seats {seat_class.booked_seats}"
        )

    before_total = seat_class.total_seats
    seat_class.total_seats = new_total_seats

    record_audit_log(
        session,
        actor_type=actor,
        actor_id=None,
        action="resize_seat_class",
        entity_type="seat_classes",
        entity_id=seat_class_id,
        before_json={"total_seats": before_total},
        after_json={"total_seats": new_total_seats},
    )

    session.flush()
    return {
        "seat_class_id": str(seat_class_id),
        "class_name": seat_class.class_name,
        "total_seats": seat_class.total_seats,
        "booked_seats": seat_class.booked_seats,
    }
