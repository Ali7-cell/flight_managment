import uuid
from sqlalchemy import Column, String, Integer, Numeric, Boolean, DateTime, ForeignKey, CheckConstraint, UniqueConstraint
from sqlalchemy.orm import relationship
from flight_domain.models.base import Base, utcnow, GUID

class Flight(Base):
    __tablename__ = "flights"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    flight_number = Column(String, nullable=False)
    origin = Column(String(3), nullable=False)
    destination = Column(String(3), nullable=False)
    origin_tz = Column(String, nullable=False)
    destination_tz = Column(String, nullable=False)
    departure_at = Column(DateTime(timezone=True), nullable=False)
    arrival_at = Column(DateTime(timezone=True), nullable=False)
    status = Column(String, nullable=False, default="scheduled")
    total_seats = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)

    seat_classes = relationship("SeatClass", back_populates="flight", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint("status in ('scheduled','cancelled','departed','completed')", name="chk_flight_status"),
        CheckConstraint("total_seats > 0", name="chk_flight_total_seats"),
        CheckConstraint("arrival_at > departure_at", name="chk_flight_arrival_after_departure"),
    )

class FareRule(Base):
    __tablename__ = "fare_rules"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    fare_class = Column(String, nullable=False)
    refundable = Column(Boolean, nullable=False, default=False)
    change_allowed = Column(Boolean, nullable=False, default=False)
    change_fee_amount = Column(Numeric(10, 2), nullable=True)
    seat_choice_allowed = Column(Boolean, nullable=False, default=False)
    cancellation_window_hrs = Column(Integer, nullable=True)
    policy_text = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)

class SeatClass(Base):
    __tablename__ = "seat_classes"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    flight_id = Column(GUID, ForeignKey("flights.id", ondelete="CASCADE"), nullable=False, index=True)
    class_name = Column(String, nullable=False)
    total_seats = Column(Integer, nullable=False)
    booked_seats = Column(Integer, nullable=False, default=0)
    held_seats = Column(Integer, nullable=False, default=0)
    fare_rules_id = Column(GUID, ForeignKey("fare_rules.id"), nullable=False)
    fare_base_amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String, nullable=False, default="USD")
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)

    flight = relationship("Flight", back_populates="seat_classes")
    fare_rule = relationship("FareRule")

    __table_args__ = (
        UniqueConstraint("flight_id", "class_name", name="uq_flight_class"),
        CheckConstraint("class_name in ('economy','business','first')", name="chk_seat_class_name"),
        CheckConstraint("total_seats >= 0", name="chk_seat_total_positive"),
        CheckConstraint("booked_seats >= 0", name="chk_seat_booked_positive"),
        CheckConstraint("held_seats >= 0", name="chk_seat_held_positive"),
        CheckConstraint("fare_base_amount >= 0", name="chk_seat_fare_positive"),
        CheckConstraint("booked_seats + held_seats <= total_seats", name="chk_seat_capacity"),
    )
