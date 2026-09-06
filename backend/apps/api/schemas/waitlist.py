from pydantic import BaseModel, Field
from uuid import UUID

class WaitlistJoinRequest(BaseModel):
    flight_id: UUID
    seat_class_id: UUID
    quantity: int = Field(gt=0, le=9)
    passenger_email: str
    passenger_name: str

class WaitlistJoinResponse(BaseModel):
    waitlist_entry_id: UUID
    priority_score: float
    status: str

class WaitlistPositionResponse(BaseModel):
    waitlist_entry_id: UUID
    status: str
    estimated_position: int | None
