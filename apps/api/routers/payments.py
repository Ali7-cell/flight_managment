import uuid
from fastapi import APIRouter, Depends, HTTPException, Header, Request
from sqlalchemy.orm import Session
from apps.api.dependencies import get_db, get_current_user
from apps.api.schemas.payments import PaymentStatusResponse
from apps.api.config import api_settings
from flight_domain.domain.payments import process_stripe_webhook, get_payment_status

router = APIRouter(prefix="/payments", tags=["Payments"])

@router.post("/webhook")
async def api_payment_webhook(
    request: Request,
    stripe_signature: str | None = Header(None, alias="Stripe-Signature"),
    db: Session = Depends(get_db),
):
    """
    Provider (Stripe) webhook receiver.
    Verifies signature header if secret is provided, checks payment_webhook_events for idempotency.
    """
    payload_bytes = await request.body()
    payload = await request.json()

    # Verify signature using Stripe client or mock client
    sig_secret = api_settings.STRIPE_WEBHOOK_SIGNING_SECRET
    from flight_domain.clients.stripe_client import mock_stripe_client
    if sig_secret and stripe_signature and not sig_secret.startswith("whsec_placeholder") and "dummy" not in sig_secret.lower():
        if not mock_stripe_client.verify_webhook_signature(payload_bytes, stripe_signature, sig_secret):
            raise HTTPException(status_code=400, detail="Invalid webhook signature")

    provider_event_id = payload.get("id")
    event_type = payload.get("type", "")
    if not provider_event_id:
        raise HTTPException(status_code=400, detail="Missing webhook event id")

    result = process_stripe_webhook(
        db,
        provider_event_id=provider_event_id,
        event_type=event_type,
        payload=payload,
    )
    return result

@router.get("/{payment_id}/status", response_model=PaymentStatusResponse)
def api_get_payment_status(
    payment_id: uuid.UUID,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    payment_data = get_payment_status(db, payment_id=payment_id)
    if not payment_data:
        raise HTTPException(status_code=404, detail="Payment record not found")
    return payment_data
