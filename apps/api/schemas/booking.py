from pydantic import BaseModel, Field
from decimal import Decimal
from datetime import datetime
from uuid import UUID

class SeatHoldRequest(BaseModel):
    flight_id: UUID
    seat_class_id: UUID
    quantity: int = Field(gt=0, le=9)
    passenger_email: str
    passenger_name: str

class SeatHoldResponse(BaseModel):
    hold_id: UUID
    seat_class_id: UUID
    quantity: int
    expires_at: datetime
    fare_amount: Decimal
    currency: str

class GroupHoldRequest(BaseModel):
    flight_id: UUID
    seat_class_id: UUID
    quantity: int = Field(gt=1, le=9)
    passenger_email: str
    passenger_name: str

class BookingConfirmRequest(BaseModel):
    hold_id: UUID
    payment_method_id: str

class BookingResponse(BaseModel):
    booking_id: UUID
    booking_reference: str
    status: str
    flight_id: UUID
    seat_class_id: UUID
    quantity: int
    total_amount: Decimal
    currency: str
    fare_rules_id: UUID
    payment_id: UUID | None = None
    created_at: datetime

class BookingCancelRequest(BaseModel):
    reason: str | None = None

class BookingCancelResponse(BaseModel):
    booking_id: UUID
    status: str
    refund_id: UUID | None = None
    credit_issued_amount: Decimal | None = None

class RefundResponse(BaseModel):
    refund_id: UUID
    booking_id: UUID
    amount: Decimal
    status: str
    reason: str | None = None
    created_at: datetime
