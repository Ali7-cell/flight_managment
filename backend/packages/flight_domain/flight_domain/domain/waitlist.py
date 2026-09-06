import uuid
from decimal import Decimal
from typing import Any
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from flight_domain.models.bookings import WaitlistEntry
from flight_domain.models.auth import Passenger
from flight_domain.models.flights import SeatClass
from flight_domain.models.base import utcnow
from flight_domain.domain.seats import release_seat_and_promote
from flight_domain.domain.outbox import emit_event

def compute_priority_score(
    loyalty_tier: str,
    fare_class: str = "economy",
    created_at_ts: float | None = None,
) -> float:
    """
    Compute waitlist priority score:
    - Loyalty tier weight:
        platinum: 1000.0
        gold: 500.0
        silver: 200.0
        none: 0.0
    - Fare class weight:
        first: 300.0
        business: 150.0
        flexible_economy: 75.0
        economy: 25.0
        basic_economy: 0.0
    - Booking time bonus: fraction added based on earlier timestamp (FIFO within tier/class).
    """
    tier_scores = {
        "platinum": 1000.0,
        "gold": 500.0,
        "silver": 200.0,
        "none": 0.0,
    }
    fare_class_scores = {
        "first": 300.0,
        "business": 150.0,
        "flexible_economy": 75.0,
        "economy": 25.0,
        "basic_economy": 0.0,
    }
    base_tier = tier_scores.get(loyalty_tier.lower(), 0.0)
    base_class = fare_class_scores.get(fare_class.lower(), 25.0)

    ts = created_at_ts or utcnow().timestamp()
    time_factor = max(0.0, (2000000000.0 - ts) / 1000000.0)
    return round(base_tier + base_class + time_factor, 4)

def join_waitlist(
    session: Session,
    *,
    flight_id: uuid.UUID | str,
    seat_class_id: uuid.UUID | str,
    quantity: int,
    passenger_email: str,
    passenger_name: str,
) -> dict[str, Any]:
    if isinstance(flight_id, str):
        flight_id = uuid.UUID(flight_id)
    if isinstance(seat_class_id, str):
        seat_class_id = uuid.UUID(seat_class_id)

    seat_class = session.get(SeatClass, seat_class_id)
    fare_class = seat_class.class_name if seat_class else "economy"

    # Check passenger
    passenger = session.scalar(select(Passenger).where(Passenger.email == passenger_email))
    if not passenger:
        passenger = Passenger(
            email=passenger_email,
            full_name=passenger_name,
            loyalty_tier="none",
        )
        session.add(passenger)
        session.flush()

    score = compute_priority_score(passenger.loyalty_tier, fare_class=fare_class)

    entry = WaitlistEntry(
        flight_id=flight_id,
        seat_class_id=seat_class_id,
        passenger_id=passenger.id,
        quantity=quantity,
        priority_score=Decimal(str(score)),
        status="waiting",
    )
    session.add(entry)
    session.flush()

    emit_event(
        session,
        event_type="waitlist_joined",
        payload_json={
            "waitlist_entry_id": str(entry.id),
            "flight_id": str(flight_id),
            "seat_class_id": str(seat_class_id),
            "passenger_id": str(passenger.id),
            "priority_score": score,
        },
    )

    return {
        "waitlist_entry_id": str(entry.id),
        "priority_score": score,
        "status": entry.status,
    }

def get_waitlist_position(
    session: Session,
    waitlist_entry_id: uuid.UUID | str,
) -> dict[str, Any]:
    if isinstance(waitlist_entry_id, str):
        waitlist_entry_id = uuid.UUID(waitlist_entry_id)

    entry = session.get(WaitlistEntry, waitlist_entry_id)
    if not entry:
        raise ValueError(f"Waitlist entry {waitlist_entry_id} not found.")

    if entry.status != "waiting":
        return {
            "waitlist_entry_id": str(entry.id),
            "status": entry.status,
            "estimated_position": None,
        }

    ahead_count = session.scalar(
        select(func.count(WaitlistEntry.id)).where(
            WaitlistEntry.seat_class_id == entry.seat_class_id,
            WaitlistEntry.status == "waiting",
            (WaitlistEntry.priority_score > entry.priority_score)
            | (
                (WaitlistEntry.priority_score == entry.priority_score)
                & (WaitlistEntry.created_at < entry.created_at)
            ),
        )
    )

    return {
        "waitlist_entry_id": str(entry.id),
        "status": entry.status,
        "estimated_position": (ahead_count or 0) + 1,
    }

def reclaim_expired_promotions(session: Session) -> int:
    """
    Finds auto-promoted waitlist offers that expired without claim,
    marks them expired, and re-promotes the seat to the next eligible person.
    """
    now_dt = utcnow()
    expired_entries = session.scalars(
        select(WaitlistEntry)
        .where(
            WaitlistEntry.status.in_(["promoted", "promotion_offered"]),
            WaitlistEntry.offer_expires_at.is_not(None),
            WaitlistEntry.offer_expires_at <= now_dt,
        )
        .with_for_update(skip_locked=True)
    ).all()

    reclaimed_count = 0
    for entry in expired_entries:
        entry.status = "expired"
        reclaimed_count += 1
        # Re-release seat and promote next person
        release_seat_and_promote(
            session,
            seat_class_id=entry.seat_class_id,
            quantity=entry.quantity,
            actor="system:waitlist_reaper",
        )

    session.flush()
    return reclaimed_count
