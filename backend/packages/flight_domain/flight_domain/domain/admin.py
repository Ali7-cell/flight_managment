import uuid
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo, available_timezones
from typing import Any
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from flight_domain.models.flights import Flight, SeatClass, FareRule, PhysicalSeat
from flight_domain.models.bookings import Booking
from flight_domain.models.plumbing import IdempotencyKey
from flight_domain.models.base import utcnow
from flight_domain.domain.audit import record_audit_log
from flight_domain.domain.outbox import emit_event

def get_or_create_default_fare_rules(session: Session) -> dict[str, FareRule]:
    """Ensure default fare rules exist across all classes, including basic and flexible economy."""
    classes = {
        "basic_economy": {
            "refundable": False,
            "change_allowed": False,
            "change_fee_amount": None,
            "seat_choice_allowed": False,
            "cancellation_window_hrs": None,
            "policy_text": "Basic economy fare. Non-refundable. No ticket changes allowed. No advance seat selection (assigned at gate).",
        },
        "economy": {
            "refundable": False,
            "change_allowed": True,
            "change_fee_amount": Decimal("150.00"),
            "seat_choice_allowed": False,
            "cancellation_window_hrs": 24,
            "policy_text": "Standard economy fare. Non-refundable. Changes incur a $150 fee. Seat selection at check-in.",
        },
        "flexible_economy": {
            "refundable": True,
            "change_allowed": True,
            "change_fee_amount": Decimal("50.00"),
            "seat_choice_allowed": True,
            "cancellation_window_hrs": 24,
            "policy_text": "Flexible economy fare. Refundable minus a $50 administrative fee. Free ticket changes. Advance seat selection included.",
        },
        "business": {
            "refundable": True,
            "change_allowed": True,
            "change_fee_amount": Decimal("50.00"),
            "seat_choice_allowed": True,
            "cancellation_window_hrs": 48,
            "policy_text": "Business class fare. Refundable with $50 administrative fee. Free ticket changes. Free premium seat selection.",
        },
        "first": {
            "refundable": True,
            "change_allowed": True,
            "change_fee_amount": Decimal("0.00"),
            "seat_choice_allowed": True,
            "cancellation_window_hrs": 72,
            "policy_text": "First class flexible fare. 100% fully refundable anytime before departure. Unlimited free changes. Priority suite selection.",
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

def _generate_physical_seat_map(
    session: Session,
    flight_id: uuid.UUID,
    seat_allocation: dict[str, int],
):
    """
    Generates realistic physical seat rows and letters for a flight based on seat allocations.
    E.g. First: 1A-1D (4 abreast)
         Business: 6A-6F (6 abreast)
         Economy: 11A-11F (6 abreast)
    """
    class_order = ["first", "business", "flexible_economy", "economy", "basic_economy"]
    current_row = 1
    letters_4 = ["A", "B", "C", "D"]
    letters_6 = ["A", "B", "C", "D", "E", "F"]

    for cls in class_order:
        count = seat_allocation.get(cls, 0)
        if count <= 0:
            continue
        
        letters = letters_4 if cls in ("first",) else letters_6
        col_idx = 0
        for _ in range(count):
            seat_col = letters[col_idx]
            seat_num = f"{current_row}{seat_col}"
            p_seat = PhysicalSeat(
                flight_id=flight_id,
                seat_number=seat_num,
                seat_row=current_row,
                seat_col=seat_col,
                class_name=cls,
                is_available=True,
            )
            session.add(p_seat)
            col_idx += 1
            if col_idx >= len(letters):
                col_idx = 0
                current_row += 1
        if col_idx != 0:
            current_row += 1

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
    aircraft_capacity: int | None = None,
    actor: str = "human:super_admin",
    idempotency_key: str | None = None,
) -> dict[str, Any]:
    """
    Admin endpoint to create a new flight:
    - Timezone validation and UTC conversion (PRD §13)
    - Validates seat allocation sums exactly to declared aircraft capacity
    - Rejects negative, zero, or non-integer seat counts
    - Duplicate flight number check per day
    - Inserts flight and seat_classes
    - Creates physical seat map definition
    - Emits audit log and outbox event
    """
    if idempotency_key:
        cached = session.get(IdempotencyKey, idempotency_key)
        if cached and cached.response_snapshot_json:
            return cached.response_snapshot_json

    valid_zones = available_timezones()
    if origin_tz not in valid_zones:
        raise ValueError(f"Invalid origin_tz: '{origin_tz}'")
    if destination_tz not in valid_zones:
        raise ValueError(f"Invalid destination_tz: '{destination_tz}'")

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
    allowed_classes = ("basic_economy", "economy", "flexible_economy", "business", "first")
    for cls_name, count in seat_allocation.items():
        if cls_name not in allowed_classes:
            raise ValueError(f"Unsupported class: {cls_name}. Allowed: {allowed_classes}.")
        if not isinstance(count, int) or count <= 0:
            raise ValueError(f"Seat count for {cls_name} must be a positive integer, got {count}.")
        total_seats += count

    # Validate that seat class totals sum exactly to declared aircraft capacity
    if aircraft_capacity is not None and aircraft_capacity != total_seats:
        raise ValueError(
            f"Seat allocation sum ({total_seats}) must match declared aircraft capacity ({aircraft_capacity})."
        )

    # Duplicate flight-number detection for same day/route
    dep_date = dep_utc.date()
    existing = session.scalar(
        select(Flight).where(
            Flight.flight_number == flight_number.upper().strip(),
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
        "basic_economy": Decimal("180.00"),
        "economy": Decimal("250.00"),
        "flexible_economy": Decimal("320.00"),
        "business": Decimal("750.00"),
        "first": Decimal("1500.00"),
    }
    overbooking_buffers = {
        "basic_economy": Decimal("5.0"),
        "economy": Decimal("5.0"),
        "flexible_economy": Decimal("2.0"),
        "business": Decimal("0.0"),  # Hard never-oversell guarantee
        "first": Decimal("0.0"),     # Hard never-oversell guarantee
    }
    booking_cutoffs = {
        "basic_economy": 180,  # 3 hours before departure
        "economy": 120,        # 2 hours before departure
        "flexible_economy": 90,# 1.5 hours before departure
        "business": 45,        # 45 minutes before departure
        "first": 30,           # 30 minutes before departure
    }

    seat_class_map = {}
    for cls_name, count in seat_allocation.items():
        sc = SeatClass(
            flight_id=flight.id,
            class_name=cls_name,
            total_seats=count,
            booked_seats=0,
            held_seats=0,
            overbooking_buffer_pct=overbooking_buffers.get(cls_name, Decimal("0.0")),
            booking_cutoff_minutes=booking_cutoffs.get(cls_name, 120),
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
            "overbooking_buffer_pct": float(sc.overbooking_buffer_pct),
            "booking_cutoff_minutes": sc.booking_cutoff_minutes,
        }

    # Generate physical seat map definition
    _generate_physical_seat_map(session, flight.id, seat_allocation)
    session.flush()

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
            "aircraft_capacity": aircraft_capacity,
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

    response_data = {
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

    if idempotency_key:
        session.add(IdempotencyKey(
            key=idempotency_key,
            endpoint="/admin/flights",
            request_hash=flight.flight_number,
            response_snapshot_json=response_data,
        ))

    return response_data

def get_flight_seat_map(session: Session, flight_id: uuid.UUID | str) -> list[dict[str, Any]]:
    """Return physical seat map layout with live availability."""
    if isinstance(flight_id, str):
        flight_id = uuid.UUID(flight_id)
    
    seats = session.scalars(
        select(PhysicalSeat)
        .where(PhysicalSeat.flight_id == flight_id)
        .order_by(PhysicalSeat.seat_row.asc(), PhysicalSeat.seat_col.asc())
    ).all()

    return [
        {
            "id": str(s.id),
            "seat_number": s.seat_number,
            "row": s.seat_row,
            "column": s.seat_col,
            "class_name": s.class_name,
            "is_available": s.is_available,
            "booking_id": str(s.booking_id) if s.booking_id else None,
        }
        for s in seats
    ]

def cancel_flight(
    session: Session,
    *,
    flight_id: uuid.UUID | str,
    actor: str = "human:super_admin",
    idempotency_key: str | None = None,
) -> dict[str, Any]:
    """
    Admin endpoint to cancel a flight entirely.
    Triggers downstream rebooking/refund flow.
    """
    if isinstance(flight_id, str):
        flight_id = uuid.UUID(flight_id)

    if idempotency_key:
        cached = session.get(IdempotencyKey, idempotency_key)
        if cached and cached.response_snapshot_json:
            return cached.response_snapshot_json

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

    res_data = {
        "flight_id": str(flight.id),
        "flight_number": flight.flight_number,
        "status": "cancelled",
        "affected_bookings": len(bookings),
    }

    if idempotency_key:
        session.add(IdempotencyKey(
            key=idempotency_key,
            endpoint=f"/admin/flights/{flight_id}/cancel",
            request_hash=str(flight_id),
            response_snapshot_json=res_data,
        ))

    return res_data

def apply_schedule_change(
    session: Session,
    *,
    flight_id: uuid.UUID | str,
    new_departure_local: datetime | None = None,
    new_arrival_local: datetime | None = None,
    new_origin: str | None = None,
    new_destination: str | None = None,
    actor: str = "human:ops_agent",
    idempotency_key: str | None = None,
) -> dict[str, Any]:
    """
    Edit flight schedule (time/route change) with cascading effect on existing bookings.
    If schedule is delayed > 2 hours or route altered, automatically flags override policy.
    """
    if isinstance(flight_id, str):
        flight_id = uuid.UUID(flight_id)

    if idempotency_key:
        cached = session.get(IdempotencyKey, idempotency_key)
        if cached and cached.response_snapshot_json:
            return cached.response_snapshot_json

    flight = session.scalar(select(Flight).where(Flight.id == flight_id).with_for_update())
    if not flight:
        raise ValueError(f"Flight {flight_id} not found.")

    tz_orig = ZoneInfo(flight.origin_tz)
    tz_dest = ZoneInfo(flight.destination_tz)

    dep_utc = flight.departure_at
    if new_departure_local is not None:
        dep_dt = new_departure_local.replace(tzinfo=tz_orig) if new_departure_local.tzinfo is None else new_departure_local.astimezone(tz_orig)
        dep_utc = dep_dt.astimezone(timezone.utc)

    arr_utc = flight.arrival_at
    if new_arrival_local is not None:
        arr_dt = new_arrival_local.replace(tzinfo=tz_dest) if new_arrival_local.tzinfo is None else new_arrival_local.astimezone(tz_dest)
        arr_utc = arr_dt.astimezone(timezone.utc)

    if arr_utc <= dep_utc:
        raise ValueError("New arrival time must be after new departure time.")

    time_shift_hours = abs((dep_utc - flight.departure_at).total_seconds()) / 3600.0
    route_changed = (new_origin and new_origin.upper() != flight.origin) or (new_destination and new_destination.upper() != flight.destination)

    old_state = {
        "origin": flight.origin,
        "destination": flight.destination,
        "departure_at": flight.departure_at.isoformat(),
        "arrival_at": flight.arrival_at.isoformat(),
    }

    if new_origin:
        flight.origin = new_origin.upper().strip()
    if new_destination:
        flight.destination = new_destination.upper().strip()
    flight.departure_at = dep_utc
    flight.arrival_at = arr_utc

    new_state = {
        "origin": flight.origin,
        "destination": flight.destination,
        "departure_at": dep_utc.isoformat(),
        "arrival_at": arr_utc.isoformat(),
        "significant_change": time_shift_hours >= 2.0 or route_changed,
    }

    record_audit_log(
        session,
        actor_type=actor,
        actor_id=None,
        action="apply_schedule_change",
        entity_type="flights",
        entity_id=flight.id,
        before_json=old_state,
        after_json=new_state,
    )

    emit_event(
        session,
        event_type="schedule_changed",
        payload_json={
            "flight_id": str(flight.id),
            "flight_number": flight.flight_number,
            "new_departure_at": dep_utc.isoformat(),
            "time_shift_hours": time_shift_hours,
            "route_changed": route_changed,
            "significant_change": time_shift_hours >= 2.0 or route_changed,
        },
    )

    res_data = {
        "flight_id": str(flight.id),
        "origin": flight.origin,
        "destination": flight.destination,
        "departure_at_utc": dep_utc.isoformat(),
        "arrival_at_utc": arr_utc.isoformat(),
        "significant_change": time_shift_hours >= 2.0 or route_changed,
    }

    if idempotency_key:
        session.add(IdempotencyKey(
            key=idempotency_key,
            endpoint=f"/admin/flights/{flight_id}",
            request_hash=dep_utc.isoformat(),
            response_snapshot_json=res_data,
        ))

    return res_data
