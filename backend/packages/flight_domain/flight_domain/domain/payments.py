import uuid
from decimal import Decimal
from typing import Any
from sqlalchemy.orm import Session
from sqlalchemy import select
from flight_domain.models.payments import Payment, PaymentWebhookEvent
from flight_domain.models.bookings import Booking
from flight_domain.models.base import utcnow

def process_stripe_webhook(
    session: Session,
    *,
    provider_event_id: str,
    event_type: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    """
    Idempotent provider webhook receiver (PRD §11).
    Guards against duplicate charges and redeliveries via payment_webhook_events.
    """
    existing = session.get(PaymentWebhookEvent, provider_event_id)
    if existing:
        return {"status": "already_processed", "provider_event_id": provider_event_id}

    # Record webhook receipt inside same transaction
    webhook_log = PaymentWebhookEvent(
        provider_event_id=provider_event_id,
        provider="stripe",
        payload_json=payload,
        processed_at=utcnow(),
    )
    session.add(webhook_log)

    if event_type == "payment_intent.succeeded":
        data_obj = payload.get("data", {}).get("object", {})
        provider_payment_id = data_obj.get("id")
        if provider_payment_id:
            payment = session.scalar(
                select(Payment).where(
                    Payment.provider == "stripe",
                    Payment.provider_payment_id == provider_payment_id,
                ).with_for_update()
            )
            if payment:
                payment.status = "succeeded"
                booking = session.get(Booking, payment.booking_id)
                if booking and booking.status == "pending_payment":
                    booking.status = "confirmed"

    session.flush()
    return {"status": "processed", "provider_event_id": provider_event_id}

def get_payment_status(session: Session, payment_id: uuid.UUID | str) -> dict[str, Any] | None:
    if isinstance(payment_id, str):
        payment_id = uuid.UUID(payment_id)

    payment = session.get(Payment, payment_id)
    if not payment:
        return None

    return {
        "payment_id": str(payment.id),
        "booking_id": str(payment.booking_id),
        "status": payment.status,
        "amount": str(payment.amount),
        "currency": payment.currency,
    }
