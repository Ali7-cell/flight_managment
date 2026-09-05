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

class FlightPatchRequest(BaseModel):
    departure_local: datetime
    arrival_local: datetime

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
