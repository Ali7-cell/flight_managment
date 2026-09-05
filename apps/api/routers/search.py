import uuid
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from apps.api.dependencies import get_db
from apps.api.schemas.search import FlightSearchItem, FareRuleResponse
from flight_domain.domain.search import search_flights, get_fare_rule_details

router = APIRouter(tags=["Search"])

@router.get("/search/flights", response_model=list[FlightSearchItem])
def api_search_flights(
    origin: str = Query(..., min_length=3, max_length=3),
    destination: str = Query(..., min_length=3, max_length=3),
    departure_date: date | None = Query(None),
    db: Session = Depends(get_db),
):
    try:
        flights = search_flights(
            db,
            origin=origin,
            destination=destination,
            departure_date=departure_date,
        )
        return flights
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/fares/{fare_class_id}/rules", response_model=FareRuleResponse)
def api_get_fare_rules(
    fare_class_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    rules = get_fare_rule_details(db, fare_class_id=fare_class_id)
    if not rules:
        raise HTTPException(status_code=404, detail="Fare rule not found")
    return rules
