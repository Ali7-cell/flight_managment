import uuid
from datetime import date
from typing import Any
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from flight_domain.models.flights import Flight, SeatClass, FareRule

def search_flights(
    session: Session,
    origin: str,
    destination: str,
    departure_date: date | None = None,
) -> list[dict[str, Any]]:
    """
    Search endpoint returning available seats per class for a given route/date.
    FastAPI live inventory read.
    """
    stmt = (
        select(Flight)
        .where(
            Flight.origin == origin.upper().strip(),
            Flight.destination == destination.upper().strip(),
            Flight.status == "scheduled",
        )
    )
    if departure_date:
        stmt = stmt.where(func.date(Flight.departure_at) == departure_date)

    flights = session.scalars(stmt).all()
    results = []

    for f in flights:
        seat_classes_info = []
        for sc in f.seat_classes:
            available = max(0, sc.total_seats - (sc.booked_seats + sc.held_seats))
            seat_classes_info.append({
                "seat_class_id": str(sc.id),
                "class_name": sc.class_name,
                "total_seats": sc.total_seats,
                "available_seats": available,
                "fare_base_amount": float(sc.fare_base_amount),
                "currency": sc.currency,
                "fare_rules_id": str(sc.fare_rules_id),
            })
        results.append({
            "flight_id": str(f.id),
            "flight_number": f.flight_number,
            "origin": f.origin,
            "destination": f.destination,
            "origin_tz": f.origin_tz,
            "destination_tz": f.destination_tz,
            "departure_at": f.departure_at.isoformat(),
            "arrival_at": f.arrival_at.isoformat(),
            "status": f.status,
            "seat_classes": seat_classes_info,
        })
    return results

def get_fare_rule_details(session: Session, fare_class_id: uuid.UUID | str) -> dict[str, Any] | None:
    if isinstance(fare_class_id, str):
        fare_class_id = uuid.UUID(fare_class_id)
    rule = session.get(FareRule, fare_class_id)
    if not rule:
        return None
    return {
        "fare_rules_id": str(rule.id),
        "fare_class": rule.fare_class,
        "refundable": rule.refundable,
        "change_allowed": rule.change_allowed,
        "change_fee_amount": float(rule.change_fee_amount) if rule.change_fee_amount else None,
        "seat_choice_allowed": rule.seat_choice_allowed,
        "cancellation_window_hrs": rule.cancellation_window_hrs,
        "policy_text": rule.policy_text,
    }
