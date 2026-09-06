import uuid
import secrets
from decimal import Decimal
from datetime import timezone, timedelta
from typing import Any
from sqlalchemy.orm import Session
from sqlalchemy import select
from flight_domain.models.bookings import Booking, SeatHold, Refund, TravelCredit
from flight_domain.models.flights import SeatClass, FareRule, Flight, PhysicalSeat
from flight_domain.models.auth import Passenger
from flight_domain.models.payments import Payment
from flight_domain.models.plumbing import IdempotencyKey
from flight_domain.models.base import utcnow
from flight_domain.domain.audit import record_audit_log
from flight_domain.domain.outbox import emit_event
from flight_domain.domain.seats import release_seat_and_promote
from flight_domain.clients.gmail import gmail_client

def generate_booking_reference() -> str:
    # 6-character uppercase alphanumeric PNR code
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return "".join(secrets.choice(alphabet) for _ in range(6))

def confirm_booking(
    session: Session,
    *,
    hold_id: uuid.UUID | str,
    payment_method_id: str,
    idempotency_key: str | None = None,
    actor: str = "system:fastapi",
) -> dict[str, Any]:
    """
    Converts a seat hold to a confirmed booking in one atomic transaction.
    1. Checks IdempotencyKey
    2. Locks SeatHold and SeatClass
    3. Decrements held_seats, increments booked_seats
    4. Records Payment and Booking
    5. Writes to outbox (domain_events) and audit_log
    6. Dispatches transactional booking confirmation email via Gmail
    """
    if isinstance(hold_id, str):
        hold_id = uuid.UUID(hold_id)

    if idempotency_key:
        cached = session.get(IdempotencyKey, idempotency_key)
        if cached and cached.response_snapshot_json:
            return cached.response_snapshot_json

    # 1. Lock seat hold
    hold_stmt = (
        select(SeatHold)
        .where(SeatHold.id == hold_id)
        .with_for_update()
    )
    hold = session.scalar(hold_stmt)
    if not hold:
        raise ValueError(f"Seat hold {hold_id} not found.")

    if hold.status != "active":
        raise ValueError(f"Seat hold status is '{hold.status}', cannot confirm.")

    # Timezone-safe comparison
    hold_expires = hold.expires_at.replace(tzinfo=timezone.utc) if hold.expires_at.tzinfo is None else hold.expires_at
    if hold_expires < utcnow():
        hold.status = "expired"
        raise ValueError("Seat hold has expired.")

    # 2. Lock seat class
    sc_stmt = (
        select(SeatClass)
        .where(SeatClass.id == hold.seat_class_id)
        .with_for_update()
    )
    seat_class = session.scalar(sc_stmt)
    if not seat_class:
        raise ValueError("Associated seat class not found.")

    # 3. Transition hold to booking
    seat_class.held_seats = max(0, seat_class.held_seats - hold.quantity)
    seat_class.booked_seats += hold.quantity

    total_amount = Decimal(str(seat_class.fare_base_amount)) * hold.quantity
    pnr_ref = generate_booking_reference()

    # 4. Create confirmed booking first
    booking = Booking(
        booking_reference=pnr_ref,
        passenger_id=hold.passenger_id,
        flight_id=seat_class.flight_id,
        seat_class_id=seat_class.id,
        quantity=hold.quantity,
        seat_number=hold.seat_number,
        fare_rules_id=seat_class.fare_rules_id,
        total_amount=total_amount,
        currency=seat_class.currency,
        status="confirmed",
        payment_id=None,
    )
    session.add(booking)
    session.flush()

    # Link physical seat to booking if assigned
    if hold.seat_number:
        p_seat = session.scalar(
            select(PhysicalSeat).where(
                PhysicalSeat.flight_id == seat_class.flight_id,
                PhysicalSeat.seat_number == hold.seat_number,
            )
        )
        if p_seat:
            p_seat.booking_id = booking.id

    # 5. Create payment record referencing valid booking.id
    payment = Payment(
        booking_id=booking.id,
        provider="stripe",
        provider_payment_id=f"pi_{uuid.uuid4().hex[:16]}",
        status="succeeded",
        amount=total_amount,
        currency=seat_class.currency,
    )
    session.add(payment)
    session.flush()

    # 6. Associate payment to booking and convert hold
    booking.payment_id = payment.id
    hold.status = "converted"

    # 7. Outbox & Audit
    record_audit_log(
        session,
        actor_type=actor,
        actor_id=str(hold.passenger_id),
        action="confirm_booking",
        entity_type="bookings",
        entity_id=booking.id,
        before_json={"hold_id": str(hold.id)},
        after_json={"booking_id": str(booking.id), "status": "confirmed", "pnr": pnr_ref},
    )

    emit_event(
        session,
        event_type="booking_confirmed",
        payload_json={
            "booking_id": str(booking.id),
            "booking_reference": pnr_ref,
            "flight_id": str(seat_class.flight_id),
            "seat_class_id": str(seat_class.id),
            "passenger_id": str(hold.passenger_id),
            "quantity": hold.quantity,
            "seat_number": hold.seat_number,
            "total_amount": str(total_amount),
            "currency": seat_class.currency,
        },
    )

    # 8. Dispatch transactional booking confirmation email
    passenger = session.get(Passenger, hold.passenger_id)
    flight = session.get(Flight, seat_class.flight_id)
    if passenger and flight:
        gmail_client.send(
            to=passenger.email,
            subject=f"Booking Confirmation - Flight {flight.flight_number} (PNR: {pnr_ref})",
            body=(
                f"Dear {passenger.full_name},\n\n"
                f"Your flight booking is confirmed!\n\n"
                f"Booking Reference (PNR): {pnr_ref}\n"
                f"Flight: {flight.flight_number} ({flight.origin} -> {flight.destination})\n"
                f"Departure: {flight.departure_at.strftime('%Y-%m-%d %H:%M UTC')}\n"
                f"Class: {seat_class.class_name.replace('_', ' ').title()}\n"
                f"Seats: {hold.quantity}" + (f" (Seat {hold.seat_number})" if hold.seat_number else "") + "\n"
                f"Total Paid: ${total_amount} {seat_class.currency}\n\n"
                f"Thank you for choosing AeroFlow Airlines!"
            ),
            metadata={"booking_id": str(booking.id), "pnr": pnr_ref},
        )

    response_data = {
        "booking_id": str(booking.id),
        "booking_reference": pnr_ref,
        "status": booking.status,
        "flight_id": str(booking.flight_id),
        "seat_class_id": str(booking.seat_class_id),
        "quantity": booking.quantity,
        "seat_number": booking.seat_number,
        "total_amount": str(booking.total_amount),
        "currency": booking.currency,
        "fare_rules_id": str(booking.fare_rules_id),
        "payment_id": str(payment.id),
        "created_at": booking.created_at.isoformat() if booking.created_at else utcnow().isoformat(),
    }

    if idempotency_key:
        session.add(IdempotencyKey(
            key=idempotency_key,
            endpoint=f"/bookings/{hold_id}/confirm",
            request_hash=payment_method_id,
            response_snapshot_json=response_data,
        ))

    return response_data

def cancel_booking(
    session: Session,
    *,
    booking_id: uuid.UUID | str,
    reason: str | None = None,
    actor: str = "customer",
    idempotency_key: str | None = None,
) -> dict[str, Any]:
    """
    Cancel entire booking with policy branching by fare type (PRD §4):
    - Refundable -> creates Refund record (minus change/cancellation fee)
    - Non-refundable -> travel credit issued with 1-year expiration
    - Releases seats and promotes waitlist via release_seat_and_promote
    - Dispatches transactional cancellation receipt via Gmail
    """
    if isinstance(booking_id, str):
        booking_id = uuid.UUID(booking_id)

    if idempotency_key:
        cached = session.get(IdempotencyKey, idempotency_key)
        if cached and cached.response_snapshot_json:
            return cached.response_snapshot_json

    stmt = select(Booking).where(Booking.id == booking_id).with_for_update()
    booking = session.scalar(stmt)
    if not booking:
        raise ValueError(f"Booking {booking_id} not found.")

    if booking.status in ("cancelled", "refunded"):
        raise ValueError(f"Booking is already {booking.status}.")

    fare_rule = session.get(FareRule, booking.fare_rules_id)
    refund_id = None
    credit_issued = None
    credit_expires_at = None

    if fare_rule and fare_rule.refundable:
        fee = fare_rule.change_fee_amount or Decimal("0.00")
        refund_amount = max(Decimal("0.00"), booking.total_amount - Decimal(str(fee)))
        refund = Refund(
            booking_id=booking.id,
            amount=refund_amount,
            reason=reason or "Customer cancellation",
            status="pending",
        )
        session.add(refund)
        session.flush()
        refund_id = refund.id

        emit_event(
            session,
            event_type="refund_requested",
            payload_json={
                "refund_id": str(refund.id),
                "booking_id": str(booking.id),
                "amount": str(refund_amount),
            },
        )
    else:
        # Non-refundable: issue 1-year valid travel credit
        credit_expires_at = utcnow() + timedelta(days=365)
        credit = TravelCredit(
            passenger_id=booking.passenger_id,
            booking_id=booking.id,
            amount=booking.total_amount,
            currency=booking.currency,
            expires_at=credit_expires_at,
            status="active",
        )
        session.add(credit)
        session.flush()
        credit_issued = booking.total_amount

    booking.status = "cancelled"

    # Free physical seat if assigned
    if booking.seat_number:
        p_seat = session.scalar(
            select(PhysicalSeat).where(
                PhysicalSeat.flight_id == booking.flight_id,
                PhysicalSeat.seat_number == booking.seat_number,
            )
        )
        if p_seat:
            p_seat.is_available = True
            p_seat.booking_id = None

    # Release seat and promote waitlist candidate in same transaction
    promo_result = release_seat_and_promote(
        session,
        seat_class_id=booking.seat_class_id,
        quantity=booking.quantity,
        actor=actor,
    )

    record_audit_log(
        session,
        actor_type=actor,
        actor_id=str(booking.passenger_id),
        action="cancel_booking",
        entity_type="bookings",
        entity_id=booking.id,
        before_json={"status": "confirmed"},
        after_json={
            "status": "cancelled",
            "refund_id": str(refund_id) if refund_id else None,
            "credit_issued": str(credit_issued) if credit_issued else None,
            "promotion": promo_result,
        },
    )

    emit_event(
        session,
        event_type="booking_cancelled",
        payload_json={
            "booking_id": str(booking.id),
            "seat_class_id": str(booking.seat_class_id),
            "quantity": booking.quantity,
            "reason": reason,
        },
    )

    # Dispatch cancellation email receipt
    passenger = session.get(Passenger, booking.passenger_id)
    if passenger:
        refund_str = f"A refund of ${refund_amount} has been initiated." if refund_id else f"A travel credit of ${credit_issued} valid until {credit_expires_at.strftime('%Y-%m-%d')} has been issued."
        gmail_client.send(
            to=passenger.email,
            subject=f"Cancellation Receipt - Booking {booking.booking_reference}",
            body=(
                f"Dear {passenger.full_name},\n\n"
                f"Your booking (PNR: {booking.booking_reference}) has been successfully cancelled.\n\n"
                f"{refund_str}\n\n"
                f"If you have any questions, our support team is here to assist."
            ),
            metadata={"booking_id": str(booking.id)},
        )

    res_data = {
        "booking_id": str(booking.id),
        "status": booking.status,
        "refund_id": str(refund_id) if refund_id else None,
        "credit_issued_amount": str(credit_issued) if credit_issued else None,
        "credit_expires_at": credit_expires_at.isoformat() if credit_expires_at else None,
    }

    if idempotency_key:
        session.add(IdempotencyKey(
            key=idempotency_key,
            endpoint=f"/bookings/{booking_id}/cancel",
            request_hash=reason or "",
            response_snapshot_json=res_data,
        ))

    return res_data

def cancel_partial_booking(
    session: Session,
    *,
    booking_id: uuid.UUID | str,
    seats_to_cancel: int,
    reason: str | None = None,
    actor: str = "customer",
    idempotency_key: str | None = None,
) -> dict[str, Any]:
    """
    Partial cancellation on a multi-passenger booking:
    - Atomically reduces booking quantity
    - Proportional refund or travel credit calculation
    - Releases cancelled seats back to inventory & promotes waitlist
    - Dispatches partial cancellation receipt
    """
    if isinstance(booking_id, str):
        booking_id = uuid.UUID(booking_id)

    if idempotency_key:
        cached = session.get(IdempotencyKey, idempotency_key)
        if cached and cached.response_snapshot_json:
            return cached.response_snapshot_json

    stmt = select(Booking).where(Booking.id == booking_id).with_for_update()
    booking = session.scalar(stmt)
    if not booking:
        raise ValueError(f"Booking {booking_id} not found.")

    if booking.status != "confirmed":
        raise ValueError(f"Cannot partially cancel booking with status '{booking.status}'.")

    if seats_to_cancel <= 0:
        raise ValueError("seats_to_cancel must be greater than zero.")
    if seats_to_cancel >= booking.quantity:
        raise ValueError(f"For full cancellation, use standard cancel endpoint (booking has {booking.quantity} seats).")

    fare_rule = session.get(FareRule, booking.fare_rules_id)
    price_per_seat = booking.total_amount / Decimal(booking.quantity)
    proportional_base = price_per_seat * Decimal(seats_to_cancel)

    refund_id = None
    credit_issued = None
    if fare_rule and fare_rule.refundable:
        fee_per_seat = (fare_rule.change_fee_amount or Decimal("0.00"))
        prop_refund = max(Decimal("0.00"), proportional_base - (fee_per_seat * Decimal(seats_to_cancel)))
        refund = Refund(
            booking_id=booking.id,
            amount=prop_refund,
            reason=reason or f"Partial cancellation of {seats_to_cancel} seats",
            status="pending",
        )
        session.add(refund)
        session.flush()
        refund_id = refund.id
    else:
        credit = TravelCredit(
            passenger_id=booking.passenger_id,
            booking_id=booking.id,
            amount=proportional_base,
            currency=booking.currency,
            expires_at=utcnow() + timedelta(days=365),
            status="active",
        )
        session.add(credit)
        session.flush()
        credit_issued = proportional_base

    # Update remaining booking state
    old_qty = booking.quantity
    old_amt = booking.total_amount
    booking.quantity -= seats_to_cancel
    booking.total_amount -= proportional_base

    # Release partial seats to waitlist/inventory
    release_seat_and_promote(
        session,
        seat_class_id=booking.seat_class_id,
        quantity=seats_to_cancel,
        actor=actor,
    )

    record_audit_log(
        session,
        actor_type=actor,
        actor_id=str(booking.passenger_id),
        action="cancel_partial_booking",
        entity_type="bookings",
        entity_id=booking.id,
        before_json={"quantity": old_qty, "total_amount": str(old_amt)},
        after_json={"quantity": booking.quantity, "total_amount": str(booking.total_amount)},
    )

    emit_event(
        session,
        event_type="booking_partially_cancelled",
        payload_json={
            "booking_id": str(booking.id),
            "cancelled_seats": seats_to_cancel,
            "remaining_seats": booking.quantity,
            "refund_id": str(refund_id) if refund_id else None,
        },
    )

    res_data = {
        "booking_id": str(booking.id),
        "status": booking.status,
        "cancelled_seats": seats_to_cancel,
        "remaining_seats": booking.quantity,
        "new_total_amount": str(booking.total_amount),
        "refund_id": str(refund_id) if refund_id else None,
        "credit_issued_amount": str(credit_issued) if credit_issued else None,
    }

    if idempotency_key:
        session.add(IdempotencyKey(
            key=idempotency_key,
            endpoint=f"/bookings/{booking_id}/cancel-partial",
            request_hash=str(seats_to_cancel),
            response_snapshot_json=res_data,
        ))

    return res_data

def resolve_cancelled_flight_booking(
    session: Session,
    *,
    booking_id: uuid.UUID | str,
    resolution_choice: str,  # "refund", "credit", "rebook"
    target_flight_id: uuid.UUID | str | None = None,
    actor: str = "customer",
) -> dict[str, Any]:
    """
    Flight cancellation downstream resolution:
    Passenger chooses between:
    - 100% full refund (ignoring non-refundable fare restrictions)
    - 100% travel credit with 1-year expiration
    - Automatic free rebooking to an alternate flight
    """
    if isinstance(booking_id, str):
        booking_id = uuid.UUID(booking_id)

    booking = session.scalar(select(Booking).where(Booking.id == booking_id).with_for_update())
    if not booking:
        raise ValueError(f"Booking {booking_id} not found.")

    flight = session.get(Flight, booking.flight_id)
    if flight and flight.status != "cancelled":
        raise ValueError("Flight is not cancelled. Cancellation resolution only applies to cancelled flights.")

    if resolution_choice == "refund":
        refund = Refund(
            booking_id=booking.id,
            amount=booking.total_amount,
            reason="Airline flight cancellation compensation refund",
            status="pending",
        )
        session.add(refund)
        session.flush()
        return {"resolution": "refund", "refund_id": str(refund.id), "amount": str(booking.total_amount)}

    elif resolution_choice == "credit":
        exp = utcnow() + timedelta(days=365)
        credit = TravelCredit(
            passenger_id=booking.passenger_id,
            booking_id=booking.id,
            amount=booking.total_amount,
            currency=booking.currency,
            expires_at=exp,
            status="active",
        )
        session.add(credit)
        session.flush()
        return {"resolution": "credit", "credit_id": str(credit.id), "amount": str(booking.total_amount), "expires_at": exp.isoformat()}

    elif resolution_choice == "rebook":
        if not target_flight_id:
            raise ValueError("target_flight_id required for rebooking.")
        target_flight = session.get(Flight, target_flight_id)
        if not target_flight or target_flight.status != "scheduled":
            raise ValueError("Target flight is not available for rebooking.")

        booking.flight_id = target_flight.id
        booking.status = "confirmed"
        return {"resolution": "rebooked", "new_flight_number": target_flight.flight_number, "status": "confirmed"}

    raise ValueError(f"Unsupported resolution_choice: {resolution_choice}")

def get_booking(session: Session, booking_id: uuid.UUID | str) -> dict[str, Any] | None:
    booking = None
    if isinstance(booking_id, uuid.UUID):
        booking = session.get(Booking, booking_id)
    else:
        try:
            parsed_uuid = uuid.UUID(str(booking_id))
            booking = session.get(Booking, parsed_uuid)
        except ValueError:
            pass
        if not booking:
            booking = session.scalar(select(Booking).where(Booking.booking_reference == str(booking_id).upper()))
    if not booking:
        return None

    return {
        "booking_id": str(booking.id),
        "booking_reference": booking.booking_reference,
        "status": booking.status,
        "flight_id": str(booking.flight_id),
        "seat_class_id": str(booking.seat_class_id),
        "quantity": booking.quantity,
        "seat_number": booking.seat_number,
        "total_amount": str(booking.total_amount),
        "currency": booking.currency,
        "fare_rules_id": str(booking.fare_rules_id),
        "payment_id": str(booking.payment_id) if booking.payment_id else None,
        "created_at": booking.created_at.isoformat() if booking.created_at else utcnow().isoformat(),
    }
