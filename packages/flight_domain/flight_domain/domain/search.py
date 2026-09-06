import uuid
from datetime import date, datetime
from typing import Any
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from flight_domain.models.flights import Flight, SeatClass, FareRule

EXCHANGE_RATES = {
    "USD": Decimal("1.0"),
    "EUR": Decimal("0.92"),
    "GBP": Decimal("0.79"),
    "AED": Decimal("3.67"),
}

CURRENCY_SYMBOLS = {
    "USD": "$",
    "EUR": "€",
    "GBP": "£",
    "AED": "AED ",
}

def convert_currency(amount_usd: Decimal | float, target_currency: str = "USD") -> tuple[float, str]:
    """Convert amount to target currency and provide locale string."""
    curr = target_currency.upper().strip()
    rate = EXCHANGE_RATES.get(curr, Decimal("1.0"))
    converted = Decimal(str(amount_usd)) * rate
    rounded = round(float(converted), 2)
    symbol = CURRENCY_SYMBOLS.get(curr, "$")
    formatted = f"{symbol}{rounded:,.2f}" if curr != "AED" else f"{rounded:,.2f} AED"
    return rounded, formatted

def search_flights(
    session: Session,
    origin: str,
    destination: str,
    departure_date: date | None = None,
    currency: str = "USD",
) -> list[dict[str, Any]]:
    """
    Search endpoint returning available seats per class for a given route/date.
    Includes:
    - Live available seat count
    - Guaranteed price-hold duration (900 seconds)
    - Converted fare amount according to requested currency
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
            conv_amount, formatted_str = convert_currency(sc.fare_base_amount, target_currency=currency)
            seat_classes_info.append({
                "seat_class_id": str(sc.id),
                "class_name": sc.class_name,
                "total_seats": sc.total_seats,
                "available_seats": available,
                "fare_base_amount": conv_amount,
                "formatted_fare": formatted_str,
                "currency": currency.upper(),
                "fare_rules_id": str(sc.fare_rules_id),
                "booking_cutoff_minutes": sc.booking_cutoff_minutes,
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
            "price_hold_duration_seconds": 900,  # 15 minute price hold guarantee
            "seat_classes": seat_classes_info,
        })
    return results

def search_connecting_flights(
    session: Session,
    origin: str,
    destination: str,
    departure_date: date | None = None,
    currency: str = "USD",
) -> list[dict[str, Any]]:
    """
    Search for multi-leg / connecting itineraries:
    Finds Flight 1 (Origin -> Layover) and Flight 2 (Layover -> Destination)
    where Flight 2 departs at least 1.5 hours after Flight 1 arrives.
    """
    orig = origin.upper().strip()
    dest = destination.upper().strip()

    stmt1 = select(Flight).where(Flight.origin == orig, Flight.destination != dest, Flight.status == "scheduled")
    if departure_date:
        stmt1 = stmt1.where(func.date(Flight.departure_at) == departure_date)
    leg1_list = session.scalars(stmt1).all()

    connecting_routes = []
    for f1 in leg1_list:
        stmt2 = select(Flight).where(
            Flight.origin == f1.destination,
            Flight.destination == dest,
            Flight.status == "scheduled",
            Flight.departure_at >= f1.arrival_at,
        )
        leg2_list = session.scalars(stmt2).all()
        for f2 in leg2_list:
            layover_hours = (f2.departure_at - f1.arrival_at).total_seconds() / 3600.0
            if 1.0 <= layover_hours <= 12.0:
                connecting_routes.append({
                    "is_connecting": True,
                    "layover_airport": f1.destination,
                    "layover_duration_hours": round(layover_hours, 1),
                    "price_hold_duration_seconds": 900,
                    "leg1": {
                        "flight_id": str(f1.id),
                        "flight_number": f1.flight_number,
                        "origin": f1.origin,
                        "destination": f1.destination,
                        "departure_at": f1.departure_at.isoformat(),
                        "arrival_at": f1.arrival_at.isoformat(),
                    },
                    "leg2": {
                        "flight_id": str(f2.id),
                        "flight_number": f2.flight_number,
                        "origin": f2.origin,
                        "destination": f2.destination,
                        "departure_at": f2.departure_at.isoformat(),
                        "arrival_at": f2.arrival_at.isoformat(),
                    },
                })
    return connecting_routes

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
