import uuid
from datetime import datetime, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo, available_timezones
from typing import Any
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from flight_domain.models.flights import Flight, SeatClass, FareRule
from flight_domain.models.bookings import Booking
from flight_domain.models.base import utcnow
from flight_domain.domain.audit import record_audit_log
from flight_domain.domain.outbox import emit_event

def get_or_create_default_fare_rules(session: Session) -> dict[str, FareRule]:
    """Ensure default fare rules exist for economy, business, and first."""
    classes = {
        "economy": {
            "refundable": False,
            "change_allowed": False,
            "change_fee_amount": Decimal("150.00"),
            "seat_choice_allowed": False,
            "cancellation_window_hrs": 24,
            "policy_text": "Standard economy fare. Non-refundable. Changes incur a $150 fee. Seat selection at check-in.",
        },
        "business": {
            "refundable": True,
            "change_allowed": True,
            "change_fee_amount": Decimal("50.00"),
            "seat_choice_allowed": True,
            "cancellation_window_hrs": 48,
            "policy_text": "Business class fare. Refundable with $50 administrative fee. Free ticket changes. Free seat selection.",
        },
        "first": {
            "refundable": True,
            "change_allowed": True,
            "change_fee_amount": Decimal("0.00"),
            "seat_choice_allowed": True,
            "cancellation_window_hrs": 72,
            "policy_text": "First class flexible fare. 100% fully refundable anytime before departure. Unlimited free changes. Priority seat selection.",
        },
    }
    rules = {}
    for cls_name, info in classes.items():
        rule = session.scalar(select(FareRule).where(FareRule.fare_class == cls_name))
        if not rule:
            rule = FareRule(
                fare_class=cls_name,
                refundable=info["refundable"],
                change_allowed=info["change_allowed"],
                change_fee_amount=info["change_fee_amount"],
                seat_choice_allowed=info["seat_choice_allowed"],
                cancellation_window_hrs=info["cancellation_window_hrs"],
                policy_text=info["policy_text"],
            )
            session.add(rule)
            session.flush()
        rules[cls_name] = rule
    return rules

def create_flight(
    session: Session,
    *,
    flight_number: str,
    origin: str,
    destination: str,
    origin_tz: str,
    destination_tz: str,
    departure_local: datetime,
    arrival_local: datetime,
    seat_allocation: dict[str, int],
    actor: str = "human:super_admin",
) -> dict[str, Any]:
    """
    Admin endpoint to create a new flight:
    - Timezone validation and UTC conversion (PRD §13)
    - Validates seat allocation sums and positivity
    - Duplicate flight number check per day
    - Inserts flight and seat_classes
    - Emits audit log
    """
    valid_zones = available_timezones()
    if origin_tz not in valid_zones:
        raise ValueError(f"Invalid origin_tz: '{origin_tz}'")
    if destination_tz not in valid_zones:
        raise ValueError(f"Invalid destination_tz: '{destination_tz}'")

    # Timezone conversion: interpret local naive times in airport timezones
    tz_orig = ZoneInfo(origin_tz)
    tz_dest = ZoneInfo(destination_tz)

    dep_dt = departure_local.replace(tzinfo=tz_orig) if departure_local.tzinfo is None else departure_local.astimezone(tz_orig)
    arr_dt = arrival_local.replace(tzinfo=tz_dest) if arrival_local.tzinfo is None else arrival_local.astimezone(tz_dest)

    dep_utc = dep_dt.astimezone(timezone.utc)
    arr_utc = arr_dt.astimezone(timezone.utc)

    if arr_utc <= dep_utc:
        raise ValueError("Arrival time must be strictly after departure time.")

    # Seat allocation validation
    if not seat_allocation:
        raise ValueError("Seat allocation dictionary cannot be empty.")

    total_seats = 0
    for cls_name, count in seat_allocation.items():
        if cls_name not in ("economy", "business", "first"):
            raise ValueError(f"Unsupported class: {cls_name}. Allowed: economy, business, first.")
        if not isinstance(count, int) or count <= 0:
            raise ValueError(f"Seat count for {cls_name} must be a positive integer, got {count}.")
        total_seats += count

    # Duplicate flight-number detection for same day/route
    dep_date = dep_utc.date()
    existing = session.scalar(
        select(Flight).where(
            Flight.flight_number == flight_number,
            func.date(Flight.departure_at) == dep_date,
        )
    )
    if existing:
        raise ValueError(f"Duplicate flight number {flight_number} already exists departing on {dep_date}.")

    flight = Flight(
        flight_number=flight_number.upper().strip(),
        origin=origin.upper().strip(),
        destination=destination.upper().strip(),
        origin_tz=origin_tz,
        destination_tz=destination_tz,
        departure_at=dep_utc,
        arrival_at=arr_utc,
        status="scheduled",
        total_seats=total_seats,
    )
    session.add(flight)
    session.flush()

    rules = get_or_create_default_fare_rules(session)
    base_fares = {
        "economy": Decimal("250.00"),
        "business": Decimal("750.00"),
        "first": Decimal("1500.00"),
    }

    seat_class_map = {}
    for cls_name, count in seat_allocation.items():
        sc = SeatClass(
            flight_id=flight.id,
            class_name=cls_name,
            total_seats=count,
            booked_seats=0,
            held_seats=0,
            fare_rules_id=rules[cls_name].id,
            fare_base_amount=base_fares.get(cls_name, Decimal("300.00")),
            currency="USD",
        )
        session.add(sc)
        session.flush()
        seat_class_map[cls_name] = {
            "seat_class_id": str(sc.id),
            "total_seats": sc.total_seats,
            "fare_rules_id": str(sc.fare_rules_id),
            "fare_base_amount": str(sc.fare_base_amount),
        }

    record_audit_log(
        session,
        actor_type=actor,
        actor_id=None,
        action="create_flight",
        entity_type="flights",
        entity_id=flight.id,
        before_json=None,
        after_json={
            "flight_number": flight.flight_number,
            "origin": flight.origin,
            "destination": flight.destination,
            "total_seats": total_seats,
            "seat_allocation": seat_allocation,
        },
    )

    emit_event(
        session,
        event_type="flight_created",
        payload_json={
            "flight_id": str(flight.id),
            "flight_number": flight.flight_number,
            "departure_at": dep_utc.isoformat(),
        },
    )

    session.flush()
    return {
        "flight_id": str(flight.id),
        "flight_number": flight.flight_number,
        "origin": flight.origin,
        "destination": flight.destination,
        "origin_tz": flight.origin_tz,
        "destination_tz": flight.destination_tz,
        "departure_at_utc": dep_utc.isoformat(),
        "arrival_at_utc": arr_utc.isoformat(),
        "total_seats": flight.total_seats,
        "seat_classes": seat_class_map,
    }

def cancel_flight(
    session: Session,
    *,
    flight_id: uuid.UUID | str,
    actor: str = "human:super_admin",
) -> dict[str, Any]:
    """
    Admin endpoint to cancel a flight entirely.
    Triggers downstream rebooking/refund flow via outbox events.
    """
    if isinstance(flight_id, str):
        flight_id = uuid.UUID(flight_id)

    stmt = select(Flight).where(Flight.id == flight_id).with_for_update()
    flight = session.scalar(stmt)
    if not flight:
        raise ValueError(f"Flight {flight_id} not found.")

    if flight.status == "cancelled":
        return {"flight_id": str(flight_id), "status": "already_cancelled"}

    flight.status = "cancelled"

    # Find affected bookings
    bookings = session.scalars(
        select(Booking).where(Booking.flight_id == flight_id, Booking.status == "confirmed")
    ).all()

    for b in bookings:
        b.status = "cancelled"

    record_audit_log(
        session,
        actor_type=actor,
        actor_id=None,
        action="cancel_flight",
        entity_type="flights",
        entity_id=flight.id,
        before_json={"status": "scheduled"},
        after_json={"status": "cancelled", "affected_bookings_count": len(bookings)},
    )

    emit_event(
        session,
        event_type="flight_cancelled",
        payload_json={
            "flight_id": str(flight.id),
            "flight_number": flight.flight_number,
            "affected_booking_ids": [str(b.id) for b in bookings],
        },
    )

    session.flush()
    return {
        "flight_id": str(flight.id),
        "flight_number": flight.flight_number,
        "status": "cancelled",
        "affected_bookings": len(bookings),
    }

def apply_schedule_change(
    session: Session,
    *,
    flight_id: uuid.UUID | str,
    new_departure_local: datetime,
    new_arrival_local: datetime,
    actor: str = "human:ops_agent",
) -> dict[str, Any]:
    """
    Edit flight schedule with cascading effect on existing bookings.
    """
    if isinstance(flight_id, str):
        flight_id = uuid.UUID(flight_id)

    flight = session.scalar(select(Flight).where(Flight.id == flight_id).with_for_update())
    if not flight:
        raise ValueError(f"Flight {flight_id} not found.")

    tz_orig = ZoneInfo(flight.origin_tz)
    tz_dest = ZoneInfo(flight.destination_tz)

    dep_utc = (new_departure_local.replace(tzinfo=tz_orig) if new_departure_local.tzinfo is None else new_departure_local).astimezone(timezone.utc)
    arr_utc = (new_arrival_local.replace(tzinfo=tz_dest) if new_arrival_local.tzinfo is None else new_arrival_local).astimezone(timezone.utc)

    if arr_utc <= dep_utc:
        raise ValueError("New arrival time must be after new departure time.")

    old_dep = flight.departure_at.isoformat()
    flight.departure_at = dep_utc
    flight.arrival_at = arr_utc

    record_audit_log(
        session,
        actor_type=actor,
        actor_id=None,
        action="apply_schedule_change",
        entity_type="flights",
        entity_id=flight.id,
        before_json={"departure_at": old_dep},
        after_json={"departure_at": dep_utc.isoformat()},
    )

    emit_event(
        session,
        event_type="schedule_changed",
        payload_json={
            "flight_id": str(flight.id),
            "flight_number": flight.flight_number,
            "new_departure_at": dep_utc.isoformat(),
        },
    )

    session.flush()
    return {
        "flight_id": str(flight.id),
        "departure_at_utc": dep_utc.isoformat(),
        "arrival_at_utc": arr_utc.isoformat(),
    }
