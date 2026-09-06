from pydantic import BaseModel
from decimal import Decimal
from uuid import UUID

class PaymentWebhookEvent(BaseModel):
    id: str                 # provider event id -> payment_webhook_events.provider_event_id (idempotency key)
    type: str               # e.g. 'payment_intent.succeeded'
    data: dict

class PaymentStatusResponse(BaseModel):
    payment_id: UUID
    booking_id: UUID
    status: str
    amount: Decimal
    currency: str
