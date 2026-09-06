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
    seat_number: str | None = None

class SeatHoldResponse(BaseModel):
    hold_id: UUID
    seat_class_id: UUID
    quantity: int
    seat_number: str | None = None
    expires_at: datetime
    fare_amount: Decimal
    currency: str

class GroupHoldRequest(BaseModel):
    flight_id: UUID
    seat_class_id: UUID
    quantity: int = Field(gt=1, le=9)
    passenger_email: str
    passenger_name: str

class LegHoldItem(BaseModel):
    flight_id: UUID
    seat_class_id: UUID
    quantity: int = Field(default=1, gt=0, le=9)
    seat_number: str | None = None

class MultiLegHoldRequest(BaseModel):
    legs: list[LegHoldItem]
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
    seat_number: str | None = None
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
    credit_expires_at: datetime | None = None

class PartialCancelRequest(BaseModel):
    seats_to_cancel: int = Field(gt=0)
    reason: str | None = None

class PartialCancelResponse(BaseModel):
    booking_id: UUID
    status: str
    cancelled_seats: int
    remaining_seats: int
    new_total_amount: Decimal
    refund_id: UUID | None = None
    credit_issued_amount: Decimal | None = None

class CancellationResolutionRequest(BaseModel):
    resolution_choice: str = Field(..., pattern="^(refund|credit|rebook)$")
    target_flight_id: UUID | None = None

class CompensationClaimRequest(BaseModel):
    flight_id: UUID
    claim_type: str = Field(..., pattern="^(schedule_change|denied_boarding|delay_compensation)$")
    requested_amount: Decimal = Field(gt=0)
    booking_id: UUID | None = None
    reason: str | None = None

class RefundResponse(BaseModel):
    refund_id: UUID
    booking_id: UUID
    amount: Decimal
    status: str
    reason: str | None = None
    created_at: datetime
