import uuid
from sqlalchemy import Column, String, Numeric, DateTime, ForeignKey, CheckConstraint, UniqueConstraint
from sqlalchemy.orm import relationship
from flight_domain.models.base import Base, utcnow, GUID, PG_JSONB

class Payment(Base):
    __tablename__ = "payments"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    booking_id = Column(GUID, ForeignKey("bookings.id"), nullable=False)
    provider = Column(String, nullable=False, default="stripe")
    provider_payment_id = Column(String, nullable=False)
    status = Column(String, nullable=False, default="requires_payment")
    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String, nullable=False, default="USD")
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)

    booking_rel = relationship("Booking", foreign_keys=[booking_id])

    __table_args__ = (
        UniqueConstraint("provider", "provider_payment_id", name="uq_payment_provider_id"),
        CheckConstraint("status in ('requires_payment','processing','succeeded','failed','refunded')", name="chk_payment_status"),
    )

class PaymentWebhookEvent(Base):
    __tablename__ = "payment_webhook_events"

    provider_event_id = Column(String, primary_key=True)
    provider = Column(String, nullable=False, default="stripe")
    payload_json = Column(PG_JSONB, nullable=False)
    processed_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
