import uuid
import secrets
from decimal import Decimal
from datetime import timezone
from typing import Any
from sqlalchemy.orm import Session
from sqlalchemy import select
from flight_domain.models.bookings import Booking, SeatHold, Refund
from flight_domain.models.flights import SeatClass, FareRule
from flight_domain.models.payments import Payment
from flight_domain.models.plumbing import IdempotencyKey
from flight_domain.models.base import utcnow
from flight_domain.domain.audit import record_audit_log
from flight_domain.domain.outbox import emit_event
from flight_domain.domain.seats import release_seat_and_promote

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

    # 1. Create confirmed booking first
    booking = Booking(
        booking_reference=pnr_ref,
        passenger_id=hold.passenger_id,
        flight_id=seat_class.flight_id,
        seat_class_id=seat_class.id,
        quantity=hold.quantity,
        fare_rules_id=seat_class.fare_rules_id,
        total_amount=total_amount,
        currency=seat_class.currency,
        status="confirmed",
        payment_id=None,
    )
    session.add(booking)
    session.flush()

    # 2. Create payment record referencing valid booking.id
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

    # 3. Associate payment to booking and convert hold
    booking.payment_id = payment.id
    hold.status = "converted"

    # Outbox & Audit
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
            "total_amount": str(total_amount),
            "currency": seat_class.currency,
        },
    )

    response_data = {
        "booking_id": str(booking.id),
        "booking_reference": pnr_ref,
        "status": booking.status,
        "flight_id": str(booking.flight_id),
        "seat_class_id": str(booking.seat_class_id),
        "quantity": booking.quantity,
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
) -> dict[str, Any]:
    """
    Cancel booking with policy branching by fare type (PRD §4):
    - Refundable -> creates Refund record (minus change/cancellation fee)
    - Non-refundable -> travel credit issued
    - Releases seat and immediately attempts waitlist promotion via release_seat_and_promote
    """
    if isinstance(booking_id, str):
        booking_id = uuid.UUID(booking_id)

    stmt = (
        select(Booking)
        .where(Booking.id == booking_id)
        .with_for_update()
    )
    booking = session.scalar(stmt)
    if not booking:
        raise ValueError(f"Booking {booking_id} not found.")

    if booking.status in ("cancelled", "refunded"):
        raise ValueError(f"Booking is already {booking.status}.")

    # Lookup fare rules
    fare_rule = session.get(FareRule, booking.fare_rules_id)
    refund_id = None
    credit_issued = None

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
        # Non-refundable or credit-only
        credit_issued = booking.total_amount

    booking.status = "cancelled"

    # Crucial: Release the seat and run promotion in the same transaction!
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

    session.flush()
    return {
        "booking_id": str(booking.id),
        "status": booking.status,
        "refund_id": str(refund_id) if refund_id else None,
        "credit_issued_amount": str(credit_issued) if credit_issued else None,
    }

def get_booking(session: Session, booking_id: uuid.UUID | str) -> dict[str, Any] | None:
    if isinstance(booking_id, str):
        booking_id = uuid.UUID(booking_id)
    booking = session.get(Booking, booking_id)
    if not booking:
        return None
    return {
        "booking_id": str(booking.id),
        "booking_reference": booking.booking_reference,
        "status": booking.status,
        "flight_id": str(booking.flight_id),
        "seat_class_id": str(booking.seat_class_id),
        "quantity": booking.quantity,
        "total_amount": str(booking.total_amount),
        "currency": booking.currency,
        "fare_rules_id": str(booking.fare_rules_id),
        "payment_id": str(booking.payment_id) if booking.payment_id else None,
        "created_at": booking.created_at.isoformat() if booking.created_at else utcnow().isoformat(),
    }
