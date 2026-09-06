from typing import Any
from sqlalchemy.orm import Session
from sqlalchemy import select
from flight_domain.models.plumbing import DomainEvent
from flight_domain.models.base import utcnow

def emit_event(
    session: Session,
    *,
    event_type: str,
    payload_json: dict[str, Any],
) -> DomainEvent:
    """
    Outbox table writer.
    Writes one row in the SAME transaction as the state mutation.
    Event types:
      'seat_released', 'booking_confirmed', 'booking_cancelled',
      'refund_requested', 'flight_cancelled', 'schedule_changed'
    """
    event = DomainEvent(
        event_type=event_type,
        payload_json=payload_json,
        created_at=utcnow(),
        processed=False,
    )
    session.add(event)
    return event

def claim_unprocessed_events(
    session: Session,
    *,
    event_type: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """
    Claim events using SELECT ... FOR UPDATE SKIP LOCKED.
    Marks claimed events as processed=True in the same transaction.
    """
    stmt = (
        select(DomainEvent)
        .where(DomainEvent.processed == False)
    )
    if event_type:
        stmt = stmt.where(DomainEvent.event_type == event_type)
    
    stmt = (
        stmt.order_by(DomainEvent.created_at.asc())
        .limit(limit)
        .with_for_update(skip_locked=True)
    )

    events = session.scalars(stmt).all()
    claimed_payloads = []
    now_ts = utcnow()
    for ev in events:
        ev.processed = True
        ev.processed_at = now_ts
        claimed_payloads.append({
            "id": ev.id,
            "event_type": ev.event_type,
            "payload": ev.payload_json,
            "created_at": ev.created_at.isoformat() if ev.created_at else None,
        })
    session.flush()
    return claimed_payloads
