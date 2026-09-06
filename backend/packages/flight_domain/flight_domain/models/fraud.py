import uuid
from sqlalchemy import Column, Numeric, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from flight_domain.models.base import Base, utcnow, GUID, PG_JSONB

class FraudScore(Base):
    __tablename__ = "fraud_scores"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    booking_id = Column(GUID, ForeignKey("bookings.id"), nullable=False, index=True)
    score = Column(Numeric, nullable=False)
    signals_json = Column(PG_JSONB, nullable=False)
    scored_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)

    booking = relationship("Booking")
