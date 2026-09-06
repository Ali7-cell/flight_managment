from pydantic import BaseModel
from decimal import Decimal
from datetime import datetime
from uuid import UUID

class SeatClassAvailability(BaseModel):
    seat_class_id: UUID
    class_name: str
    total_seats: int
    available_seats: int
    fare_base_amount: Decimal
    formatted_fare: str
    currency: str
    fare_rules_id: UUID
    booking_cutoff_minutes: int | None = None

class FlightSearchItem(BaseModel):
    flight_id: UUID
    flight_number: str
    origin: str
    destination: str
    origin_tz: str
    destination_tz: str
    departure_at: datetime
    arrival_at: datetime
    status: str
    price_hold_duration_seconds: int = 900
    seat_classes: list[SeatClassAvailability]

class ConnectingLegInfo(BaseModel):
    flight_id: str
    flight_number: str
    origin: str
    destination: str
    departure_at: str
    arrival_at: str

class ConnectingFlightItem(BaseModel):
    is_connecting: bool = True
    layover_airport: str
    layover_duration_hours: float
    price_hold_duration_seconds: int = 900
    leg1: ConnectingLegInfo
    leg2: ConnectingLegInfo

class FareRuleResponse(BaseModel):
    fare_rules_id: UUID
    fare_class: str
    refundable: bool
    change_allowed: bool
    change_fee_amount: Decimal | None
    seat_choice_allowed: bool
    cancellation_window_hrs: int | None
    policy_text: str
