from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID

class FlightCreateRequest(BaseModel):
    flight_number: str
    origin: str = Field(min_length=3, max_length=3)
    destination: str = Field(min_length=3, max_length=3)
    origin_tz: str
    destination_tz: str
    departure_local: datetime
    arrival_local: datetime
    seat_allocation: dict[str, int]
    aircraft_capacity: int | None = None

class FlightPatchRequest(BaseModel):
    departure_local: datetime | None = None
    arrival_local: datetime | None = None
    origin: str | None = Field(None, min_length=3, max_length=3)
    destination: str | None = Field(None, min_length=3, max_length=3)

class SeatClassResizeRequest(BaseModel):
    class_name: str
    new_total_seats: int = Field(ge=0)

class AuditLogEntry(BaseModel):
    id: int
    actor_type: str
    actor_id: str | None = None
    action: str
    before: dict | None = None
    after: dict | None = None
    created_at: datetime

class PhysicalSeatResponse(BaseModel):
    id: str
    seat_number: str
    row: int
    column: str
    class_name: str
    is_available: bool
    booking_id: str | None = None

class CompensationClaimItem(BaseModel):
    claim_id: str
    flight_id: str
    flight_number: str
    passenger_id: str
    passenger_name: str
    passenger_email: str
    claim_type: str
    requested_amount: str
    currency: str
    reason: str | None = None
    created_at: str

class CompensationReviewRequest(BaseModel):
    action: str = Field(..., pattern="^(approve|reject)$")
    notes: str | None = None
