import uuid
import math
import threading
from datetime import timedelta
from decimal import Decimal
from typing import Any
from sqlalchemy.orm import Session
from sqlalchemy import select, case, func
from flight_domain.models.flights import SeatClass, Flight, PhysicalSeat, FareRule
from flight_domain.models.bookings import SeatHold, WaitlistEntry, Booking
from flight_domain.models.auth import Passenger
from flight_domain.models.plumbing import IdempotencyKey
from flight_domain.models.base import utcnow
from flight_domain.domain.audit import record_audit_log
from flight_domain.domain.outbox import emit_event
from flight_domain.clients.gmail import gmail_client
from flight_domain.config import WAITLIST_CLAIM_WINDOW_HOURS


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
    seat_number: str | None = None,
    idempotency_key: str | None = None,
    endpoint: str = "/bookings/hold",
    request_hash: str = "",
    actor: str = "system:fastapi",
    hold_duration_minutes: int = 15,
) -> dict[str, Any]:
    """
    Atomic seat hold inside one transaction.
    - Idempotency validation
    - Blocking row-lock on seat_classes
    - Explicit overbooking buffer enforcement (0% for First/Business, buffer for Economy)
    - Class-specific departure cutoff check
    - Physical seat reservation if selected
    - Emits outbox events and audit log
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

    # 3. Class-specific departure cutoff validation
    flight = session.get(Flight, seat_class.flight_id)
    if flight:
        now_dt = utcnow()
        dep_dt = flight.departure_at.replace(tzinfo=now_dt.tzinfo) if flight.departure_at.tzinfo is None else flight.departure_at
        mins_remaining = (dep_dt - now_dt).total_seconds() / 60.0
        if mins_remaining < seat_class.booking_cutoff_minutes:
            raise ValueError(
                f"Booking cutoff passed for class '{seat_class.class_name}'. "
                f"Booking closes {seat_class.booking_cutoff_minutes} minutes before departure (remaining: {int(mins_remaining)}m)."
            )

    # 4. Overbooking policy calculation
    buffer_pct = float(seat_class.overbooking_buffer_pct or 0.0)
    effective_max_capacity = math.floor(seat_class.total_seats * (1.0 + (buffer_pct / 100.0)))
    available = effective_max_capacity - (seat_class.booked_seats + seat_class.held_seats)
    if available < quantity:
        raise ValueError(f"Insufficient seats available. Requested: {quantity}, Available: {available}")

    # 5. Optional physical seat selection
    physical_seat_obj = None
    if seat_number:
        p_stmt = (
            select(PhysicalSeat)
            .where(
                PhysicalSeat.flight_id == seat_class.flight_id,
                PhysicalSeat.seat_number == seat_number.upper().strip(),
            )
            .with_for_update()
        )
        physical_seat_obj = session.scalar(p_stmt)
        if not physical_seat_obj:
            raise ValueError(f"Seat {seat_number} does not exist on this flight.")
        if not physical_seat_obj.is_available:
            raise ValueError(f"Seat {seat_number} is already occupied.")
        if physical_seat_obj.class_name != seat_class.class_name:
            raise ValueError(f"Seat {seat_number} belongs to class {physical_seat_obj.class_name}, not {seat_class.class_name}.")
        physical_seat_obj.is_available = False

    # 6. Lookup or create passenger
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

    # 7. Mutate seat count and record hold
    before_state = {"held_seats": seat_class.held_seats, "booked_seats": seat_class.booked_seats}
    seat_class.held_seats += quantity
    after_state = {"held_seats": seat_class.held_seats, "booked_seats": seat_class.booked_seats}

    expires_at = utcnow() + timedelta(minutes=hold_duration_minutes)
    hold = SeatHold(
        seat_class_id=seat_class_id,
        passenger_id=passenger.id,
        quantity=quantity,
        seat_number=seat_number.upper().strip() if seat_number else None,
        status="active",
        idempotency_key=idempotency_key,
        expires_at=expires_at,
    )
    session.add(hold)
    session.flush()

    # 8. Outbox & Audit Log
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
            "seat_number": hold.seat_number,
            "expires_at": expires_at.isoformat(),
        },
    )

    total_fare = Decimal(str(seat_class.fare_base_amount)) * quantity
    response_data = {
        "hold_id": str(hold.id),
        "seat_class_id": str(seat_class_id),
        "quantity": quantity,
        "seat_number": hold.seat_number,
        "expires_at": expires_at.isoformat(),
        "fare_amount": str(total_fare),
        "currency": seat_class.currency,
    }

    # 9. Save Idempotency Snapshot
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

def hold_multi_leg_seats(
    session: Session,
    *,
    legs: list[dict[str, Any]],
    passenger_email: str,
    passenger_name: str,
    idempotency_key: str | None = None,
    actor: str = "system:fastapi",
) -> dict[str, Any]:
    """
    Atomic multi-leg connecting itinerary hold:
    Holds all legs in one transaction. If any leg fails (e.g. sold out while checking out),
    the entire transaction is rolled back so no orphan leg remains held.
    """
    if len(legs) < 2:
        raise ValueError("Multi-leg hold requires at least 2 legs.")

    if idempotency_key:
        cached = session.get(IdempotencyKey, idempotency_key)
        if cached and cached.response_snapshot_json:
            return cached.response_snapshot_json

    holds = []
    total_amount = Decimal("0.00")
    currency = "USD"

    # Savepoint for atomic rollback of all legs
    savepoint = session.begin_nested()
    try:
        for idx, leg in enumerate(legs):
            h_data = hold_seats(
                session,
                flight_id=leg["flight_id"],
                seat_class_id=leg["seat_class_id"],
                quantity=leg.get("quantity", 1),
                passenger_email=passenger_email,
                passenger_name=passenger_name,
                seat_number=leg.get("seat_number"),
                endpoint=f"/bookings/multi-leg-hold-leg-{idx}",
                actor=actor,
            )
            holds.append(h_data)
            total_amount += Decimal(h_data["fare_amount"])
            currency = h_data["currency"]
        savepoint.commit()
    except Exception as e:
        savepoint.rollback()
        raise ValueError(f"Multi-leg itinerary failed: {str(e)}. All leg holds aborted.")

    result = {
        "multi_leg": True,
        "legs": holds,
        "total_amount": str(total_amount),
        "currency": currency,
        "expires_at": min(h["expires_at"] for h in holds),
    }

    if idempotency_key:
        session.add(IdempotencyKey(
            key=idempotency_key,
            endpoint="/bookings/multi-leg-hold",
            request_hash=passenger_email,
            response_snapshot_json=result,
        ))

    return result

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
    4. If found, promote candidate, notify via Gmail, and re-increment booked_seats
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
        # Dynamic ordering per policy rules:
        # 1. Loyalty tier: Platinum, then Gold, then Silver, then no tier
        # 2. Fare type: flex before basic_economy
        # 3. Time joined waitlist: earlier first
        loyalty_rank = case(
            (func.lower(Passenger.loyalty_tier) == "platinum", 1),
            (func.lower(Passenger.loyalty_tier) == "gold", 2),
            (func.lower(Passenger.loyalty_tier) == "silver", 3),
            else_=4,
        )
        fare_rank = case(
            (func.lower(WaitlistEntry.fare_type) == "flex", 1),
            else_=2,
        )

        wl_stmt = (
            select(WaitlistEntry)
            .join(Passenger, WaitlistEntry.passenger_id == Passenger.id)
            .where(
                WaitlistEntry.seat_class_id == seat_class_id,
                WaitlistEntry.status == "waiting",
                WaitlistEntry.quantity <= quantity,
            )
            .order_by(
                loyalty_rank.asc(),
                fare_rank.asc(),
                WaitlistEntry.created_at.asc(),
            )
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        candidate = session.scalar(wl_stmt)

        promoted_info = None
        if candidate:
            # Promote candidate with WAITLIST_CLAIM_WINDOW_HOURS (2 hours)
            candidate.status = "promoted"
            candidate.offer_expires_at = utcnow() + timedelta(hours=WAITLIST_CLAIM_WINDOW_HOURS)
            seat_class.booked_seats += candidate.quantity

            passenger = session.get(Passenger, candidate.passenger_id)
            passenger_email = passenger.email if passenger else "passenger@example.com"

            promoted_info = {
                "waitlist_entry_id": str(candidate.id),
                "passenger_id": str(candidate.passenger_id),
                "passenger_email": passenger_email,
                "quantity": candidate.quantity,
                "priority_score": float(candidate.priority_score) if candidate.priority_score else 0.0,
                "offer_expires_at": candidate.offer_expires_at.isoformat(),
            }

            # Send notification window email
            gmail_client.send(
                to=passenger_email,
                subject="Seat Available: Waitlist Promotion Offer",
                body=(
                    f"Great news! A seat has opened up for your flight. "
                    f"You have been auto-promoted. Your reservation offer is reserved for {WAITLIST_CLAIM_WINDOW_HOURS} hours until "
                    f"{candidate.offer_expires_at.strftime('%Y-%m-%d %H:%M UTC')}. "
                    f"Please confirm your booking before the deadline to claim your seat."
                ),
                metadata={"waitlist_entry_id": str(candidate.id)},
            )


            emit_event(
                session,
                event_type="waitlist_promoted",
                payload_json={
                    "seat_class_id": str(seat_class_id),
                    "waitlist_entry_id": str(candidate.id),
                    "passenger_id": str(candidate.passenger_id),
                    "quantity": candidate.quantity,
                    "offer_expires_at": candidate.offer_expires_at.isoformat(),
                },
            )

        after_booked = seat_class.booked_seats

        record_audit_log(
            session,
            actor_type=actor,
            actor_id=None,
            action="release_seat_and_promote",
            entity_type="seat_classes",
            entity_id=seat_class_id,
            before_json={"booked_seats": before_booked},
            after_json={
                "booked_seats": after_booked,
                "promoted_waitlist_id": str(candidate.id) if candidate else None,
            },
        )

        emit_event(
            session,
            event_type="seat_released",
            payload_json={
                "seat_class_id": str(seat_class_id),
                "released_quantity": quantity,
                "promoted": bool(candidate),
            },
        )

        session.flush()
        return {
            "seat_class_id": str(seat_class_id),
            "released_quantity": quantity,
            "promoted": bool(candidate),
            "promoted_details": promoted_info,
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
    idempotency_key: str | None = None,
) -> dict[str, Any]:
    """
    Adjust seat class allocation after bookings exist.
    CANNOT shrink below already booked count.
    Backstopped by database trigger trg_seat_classes_no_shrink.
    """
    if isinstance(seat_class_id, str):
        seat_class_id = uuid.UUID(seat_class_id)

    if idempotency_key:
        cached = session.get(IdempotencyKey, idempotency_key)
        if cached and cached.response_snapshot_json:
            return cached.response_snapshot_json

    stmt = select(SeatClass).where(SeatClass.id == seat_class_id).with_for_update()
    sc = session.scalar(stmt)
    if not sc:
        raise ValueError(f"SeatClass {seat_class_id} not found.")

    if new_total_seats < sc.booked_seats:
        raise ValueError(
            f"cannot shrink seat_classes {sc.id} total to {new_total_seats} below booked_seats {sc.booked_seats}"
        )

    before_total = sc.total_seats
    sc.total_seats = new_total_seats

    record_audit_log(
        session,
        actor_type=actor,
        actor_id=None,
        action="resize_seat_class",
        entity_type="seat_classes",
        entity_id=sc.id,
        before_json={"total_seats": before_total},
        after_json={"total_seats": new_total_seats},
    )

    emit_event(
        session,
        event_type="seat_class_resized",
        payload_json={
            "seat_class_id": str(sc.id),
            "flight_id": str(sc.flight_id),
            "old_total": before_total,
            "new_total": new_total_seats,
        },
    )

    session.flush()
    res_data = {
        "seat_class_id": str(sc.id),
        "class_name": sc.class_name,
        "old_total_seats": before_total,
        "new_total_seats": sc.total_seats,
        "total_seats": sc.total_seats,
        "booked_seats": sc.booked_seats,
    }

    if idempotency_key:
        session.add(IdempotencyKey(
            key=idempotency_key,
            endpoint=f"/admin/flights/{sc.flight_id}/seat-classes",
            request_hash=str(new_total_seats),
            response_snapshot_json=res_data,
        ))

    return res_data
