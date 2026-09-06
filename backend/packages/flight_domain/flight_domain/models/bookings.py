import uuid
from sqlalchemy import Column, String, Integer, Numeric, DateTime, ForeignKey, CheckConstraint
from sqlalchemy.orm import relationship
from flight_domain.models.base import Base, utcnow, GUID

class SeatHold(Base):
    __tablename__ = "seat_holds"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    seat_class_id = Column(GUID, ForeignKey("seat_classes.id"), nullable=False)
    passenger_id = Column(GUID, ForeignKey("passengers.id"), nullable=True)
    quantity = Column(Integer, nullable=False)
    seat_number = Column(String, nullable=True)
    status = Column(String, nullable=False, default="active")
    idempotency_key = Column(String, nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)

    seat_class = relationship("SeatClass")
    passenger = relationship("Passenger")

    __table_args__ = (
        CheckConstraint("quantity > 0", name="chk_seat_hold_quantity"),
        CheckConstraint("status in ('active','expired','converted','released')", name="chk_seat_hold_status"),
    )

class Booking(Base):
    __tablename__ = "bookings"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    booking_reference = Column(String, nullable=False, unique=True)
    passenger_id = Column(GUID, ForeignKey("passengers.id"), nullable=False, index=True)
    flight_id = Column(GUID, ForeignKey("flights.id"), nullable=False, index=True)
    seat_class_id = Column(GUID, ForeignKey("seat_classes.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    seat_number = Column(String, nullable=True)
    fare_rules_id = Column(GUID, ForeignKey("fare_rules.id"), nullable=False)
    total_amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String, nullable=False, default="USD")
    status = Column(String, nullable=False, default="pending_payment", index=True)
    payment_id = Column(GUID, ForeignKey("payments.id", name="fk_bookings_payment", use_alter=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)

    passenger = relationship("Passenger")
    flight = relationship("Flight")
    seat_class = relationship("SeatClass")
    fare_rule = relationship("FareRule")
    payment = relationship("Payment", foreign_keys=[payment_id], back_populates="booking_rel")

    __table_args__ = (
        CheckConstraint("quantity > 0", name="chk_booking_quantity"),
        CheckConstraint("total_amount >= 0", name="chk_booking_amount"),
        CheckConstraint("status in ('pending_payment','confirmed','cancelled','refunded','completed')", name="chk_booking_status"),
    )

class WaitlistEntry(Base):
    __tablename__ = "waitlist_entries"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    flight_id = Column(GUID, ForeignKey("flights.id"), nullable=False)
    seat_class_id = Column(GUID, ForeignKey("seat_classes.id"), nullable=False)
    passenger_id = Column(GUID, ForeignKey("passengers.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    priority_score = Column(Numeric, nullable=False)
    status = Column(String, nullable=False, default="waiting")
    offer_expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)

    flight = relationship("Flight")
    seat_class = relationship("SeatClass")
    passenger = relationship("Passenger")

    __table_args__ = (
        CheckConstraint("quantity > 0", name="chk_waitlist_quantity"),
        CheckConstraint("status in ('waiting','promotion_offered','promoted','expired','cancelled')", name="chk_waitlist_status"),
    )

class Refund(Base):
    __tablename__ = "refunds"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    booking_id = Column(GUID, ForeignKey("bookings.id"), nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    reason = Column(String, nullable=True)
    status = Column(String, nullable=False, default="pending")
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    booking = relationship("Booking")

    __table_args__ = (
        CheckConstraint("amount >= 0", name="chk_refund_amount"),
        CheckConstraint("status in ('pending','processing','completed','failed')", name="chk_refund_status"),
    )

class TravelCredit(Base):
    __tablename__ = "travel_credits"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    passenger_id = Column(GUID, ForeignKey("passengers.id"), nullable=False, index=True)
    booking_id = Column(GUID, ForeignKey("bookings.id"), nullable=True)
    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String, nullable=False, default="USD")
    expires_at = Column(DateTime(timezone=True), nullable=False)
    status = Column(String, nullable=False, default="active")
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)

    passenger = relationship("Passenger")
    booking = relationship("Booking")

    __table_args__ = (
        CheckConstraint("amount >= 0", name="chk_credit_amount"),
        CheckConstraint("status in ('active','used','expired')", name="chk_credit_status"),
    )

class CompensationClaim(Base):
    __tablename__ = "compensation_claims"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    flight_id = Column(GUID, ForeignKey("flights.id"), nullable=False)
    passenger_id = Column(GUID, ForeignKey("passengers.id"), nullable=False)
    booking_id = Column(GUID, ForeignKey("bookings.id"), nullable=True)
    claim_type = Column(String, nullable=False)  # 'schedule_change', 'denied_boarding', 'delay_compensation'
    requested_amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String, nullable=False, default="USD")
    status = Column(String, nullable=False, default="pending_review")  # 'pending_review', 'approved', 'rejected'
    reviewed_by = Column(GUID, nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    reason = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)

    flight = relationship("Flight")
    passenger = relationship("Passenger")
    booking = relationship("Booking")

    __table_args__ = (
        CheckConstraint("requested_amount >= 0", name="chk_comp_amount"),
        CheckConstraint("claim_type in ('schedule_change','denied_boarding','delay_compensation')", name="chk_claim_type"),
        CheckConstraint("status in ('pending_review','approved','rejected')", name="chk_comp_status"),
    )
