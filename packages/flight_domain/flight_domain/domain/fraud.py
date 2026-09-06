import uuid
from datetime import timedelta
from decimal import Decimal
from typing import Any
from sqlalchemy.orm import Session
from sqlalchemy import select
from flight_domain.models.fraud import FraudScore
from flight_domain.models.bookings import Booking
from flight_domain.models.base import utcnow

def record_fraud_score(
    session: Session,
    booking_id: uuid.UUID | str,
    score: float,
    signals: dict[str, Any],
) -> FraudScore:
    if isinstance(booking_id, str):
        booking_id = uuid.UUID(booking_id)

    fraud_entry = FraudScore(
        booking_id=booking_id,
        score=Decimal(str(round(score, 4))),
        signals_json=signals,
        scored_at=utcnow(),
    )
    session.add(fraud_entry)
    session.flush()
    return fraud_entry

def bookings_since_last_scan(
    session: Session,
    lookback_hours: int = 24,
) -> list[dict[str, Any]]:
    """
    Find bookings that have not yet been scored by the batch fraud scanner.
    """
    cutoff = utcnow() - timedelta(hours=lookback_hours)
    scored_subq = select(FraudScore.booking_id)

    stmt = (
        select(Booking)
        .where(
            Booking.created_at >= cutoff,
            Booking.id.not_in(scored_subq),
        )
        .limit(100)
    )
    bookings = session.scalars(stmt).all()
    results = []
    for b in bookings:
        results.append({
            "id": str(b.id),
            "booking_reference": b.booking_reference,
            "passenger_id": str(b.passenger_id),
            "flight_id": str(b.flight_id),
            "quantity": b.quantity,
            "total_amount": float(b.total_amount),
            "created_at": b.created_at.isoformat() if b.created_at else None,
        })
    return results
