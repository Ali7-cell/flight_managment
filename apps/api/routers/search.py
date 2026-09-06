import uuid
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from apps.api.dependencies import get_db
from apps.api.schemas.search import FlightSearchItem, ConnectingFlightItem, FareRuleResponse
from apps.api.schemas.admin import PhysicalSeatResponse
from flight_domain.domain.search import search_flights, search_connecting_flights, get_fare_rule_details
from flight_domain.domain.admin import get_flight_seat_map

router = APIRouter(tags=["Search"])

@router.get("/search/flights", response_model=list[FlightSearchItem])
def api_search_flights(
    origin: str = Query(..., min_length=3, max_length=3),
    destination: str = Query(..., min_length=3, max_length=3),
    departure_date: date | None = Query(None),
    currency: str = Query("USD", min_length=3, max_length=3),
    db: Session = Depends(get_db),
):
    try:
        flights = search_flights(
            db,
            origin=origin,
            destination=destination,
            departure_date=departure_date,
            currency=currency,
        )
        return flights
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/search/connecting", response_model=list[ConnectingFlightItem])
def api_search_connecting_flights(
    origin: str = Query(..., min_length=3, max_length=3),
    destination: str = Query(..., min_length=3, max_length=3),
    departure_date: date | None = Query(None),
    currency: str = Query("USD", min_length=3, max_length=3),
    db: Session = Depends(get_db),
):
    try:
        return search_connecting_flights(
            db,
            origin=origin,
            destination=destination,
            departure_date=departure_date,
            currency=currency,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/flights/{flight_id}/seat-map", response_model=list[PhysicalSeatResponse])
def api_get_flight_seat_map(
    flight_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    return get_flight_seat_map(db, flight_id=flight_id)

@router.get("/fares/{fare_class_id}/rules", response_model=FareRuleResponse)
def api_get_fare_rules(
    fare_class_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    rules = get_fare_rule_details(db, fare_class_id=fare_class_id)
    if not rules:
        raise HTTPException(status_code=404, detail="Fare rule not found")
    return rules
