import uuid
from decimal import Decimal
from typing import Any
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from flight_domain.models.bookings import WaitlistEntry
from flight_domain.models.auth import Passenger
from flight_domain.models.flights import SeatClass
from flight_domain.models.base import utcnow

def compute_priority_score(loyalty_tier: str, created_at_ts: float | None = None) -> float:
    """
    Compute waitlist priority score:
    Tier base score:
      platinum: 1000.0
      gold: 500.0
      silver: 200.0
      none: 0.0
    Time bonus: fraction added based on earlier timestamp (FIFO within tier).
    """
    tier_scores = {
        "platinum": 1000.0,
        "gold": 500.0,
        "silver": 200.0,
        "none": 0.0,
    }
    base = tier_scores.get(loyalty_tier.lower(), 0.0)
    # Earlier timestamp gets a tiny addition: inverted fraction
    ts = created_at_ts or utcnow().timestamp()
    time_factor = max(0.0, (2000000000.0 - ts) / 1000000.0)
    return round(base + time_factor, 4)

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

    score = compute_priority_score(passenger.loyalty_tier)

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

    # Position is count of waiting entries ahead with higher priority or earlier creation
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
