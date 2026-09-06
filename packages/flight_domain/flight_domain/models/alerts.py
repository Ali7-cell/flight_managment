import uuid
from sqlalchemy import Column, String, Numeric, DateTime
from flight_domain.models.base import Base, utcnow, GUID

class PriceAlert(Base):
    __tablename__ = "price_alerts"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    passenger_email = Column(String, nullable=False, index=True)
    origin = Column(String(3), nullable=False)
    destination = Column(String(3), nullable=False)
    target_price = Column(Numeric(10, 2), nullable=False)
    last_notified_price = Column(Numeric(10, 2), nullable=True)
    last_notified_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
