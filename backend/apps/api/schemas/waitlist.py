from pydantic import BaseModel, Field
from uuid import UUID

class WaitlistJoinRequest(BaseModel):
    flight_id: UUID
    seat_class_id: UUID
    quantity: int = Field(gt=0, le=9)
    passenger_email: str
    passenger_name: str
    fare_type: str = "flex"

class WaitlistJoinResponse(BaseModel):
    waitlist_entry_id: UUID
    priority_score: float
    fare_type: str = "flex"
    status: str


class WaitlistPositionResponse(BaseModel):
    waitlist_entry_id: UUID
    status: str
    estimated_position: int | None
