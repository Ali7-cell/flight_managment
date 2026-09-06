import logging
import uuid
from typing import Any
from flight_domain.config import settings

logger = logging.getLogger("flight_domain.stripe")

class MockStripeClient:
    """
    Dummy/Mock Stripe Client.
    Emulates Stripe charges, payment intents, refunds, and webhook generation
    for development and testing without requiring a live Stripe account or secret key.
    """
    def __init__(self, api_key: str | None = None, signing_secret: str | None = None):
        self.api_key = api_key or settings.STRIPE_SECRET_KEY
        self.signing_secret = signing_secret or settings.STRIPE_WEBHOOK_SIGNING_SECRET
        logger.info("Initialized MockStripeClient (Dummy Stripe Module active).")

    def create_payment_intent(
        self,
        amount: int | float,
        currency: str = "usd",
        payment_method: str = "pm_card_visa",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Simulate creating and immediately confirming a Stripe PaymentIntent."""
        pi_id = f"pi_mock_{uuid.uuid4().hex[:16]}"
        logger.info(f"[DUMMY STRIPE] Created PaymentIntent {pi_id} for {amount} {currency}")
        return {
            "id": pi_id,
            "object": "payment_intent",
            "amount": int(amount * 100) if isinstance(amount, float) else amount,
            "currency": currency.lower(),
            "status": "succeeded",
            "payment_method": payment_method,
            "metadata": metadata or {},
        }

    def create_refund(
        self,
        payment_intent_id: str,
        amount: int | float | None = None,
        reason: str = "requested_by_customer",
    ) -> dict[str, Any]:
        """Simulate processing a refund."""
        refund_id = f"re_mock_{uuid.uuid4().hex[:16]}"
        logger.info(f"[DUMMY STRIPE] Processed refund {refund_id} for PaymentIntent {payment_intent_id}")
        return {
            "id": refund_id,
            "object": "refund",
            "payment_intent": payment_intent_id,
            "amount": amount,
            "status": "succeeded",
            "reason": reason,
        }

    def construct_event(
        self,
        event_type: str,
        payment_intent_id: str | None = None,
        amount: int = 10000,
        currency: str = "usd",
    ) -> dict[str, Any]:
        """Generate a mock Stripe webhook event payload."""
        event_id = f"evt_mock_{uuid.uuid4().hex[:16]}"
        pi_id = payment_intent_id or f"pi_mock_{uuid.uuid4().hex[:16]}"
        return {
            "id": event_id,
            "object": "event",
            "type": event_type,
            "data": {
                "object": {
                    "id": pi_id,
                    "object": "payment_intent",
                    "amount": amount,
                    "currency": currency,
                    "status": "succeeded" if "succeeded" in event_type else "failed",
                }
            },
        }

    def verify_webhook_signature(
        self,
        payload_bytes: bytes,
        signature: str | None,
        sig_secret: str | None = None,
    ) -> bool:
        """
        Verify webhook signature. In mock mode, permits placeholder / dummy signatures.
        """
        secret = sig_secret or self.signing_secret
        if not secret or secret.startswith("whsec_placeholder") or "dummy" in secret.lower():
            return True
        try:
            import stripe
            stripe.Webhook.construct_event(payload_bytes, signature, secret)
            return True
        except Exception as e:
            logger.warning(f"[DUMMY STRIPE] Signature validation fallback: {e}")
            return False

mock_stripe_client = MockStripeClient()
stripe_client = mock_stripe_client
