import pytest
import uuid
from decimal import Decimal
from flight_domain.domain.seats import hold_seats, group_hold_seats, resize_seat_class
from flight_domain.domain.bookings import confirm_booking, cancel_booking
from flight_domain.models.flights import SeatClass
from flight_domain.models.bookings import SeatHold, Booking

def test_hold_seats_and_idempotency(db_session, seed_data):
    sc_id = seed_data["economy_class"].id
    flight_id = seed_data["flight"].id
    key = f"idem-key-{uuid.uuid4()}"

    # First hold
    hold1 = hold_seats(
        db_session,
        flight_id=flight_id,
        seat_class_id=sc_id,
        quantity=2,
        passenger_email="john@example.com",
        passenger_name="John Doe",
        idempotency_key=key,
    )
    db_session.commit()

    assert hold1["quantity"] == 2
    assert "hold_id" in hold1

    # Verify held seats incremented
    sc = db_session.get(SeatClass, sc_id)
    assert sc.held_seats == 2

    # Replay with same idempotency key returns exact snapshot without re-incrementing
    hold2 = hold_seats(
        db_session,
        flight_id=flight_id,
        seat_class_id=sc_id,
        quantity=2,
        passenger_email="john@example.com",
        passenger_name="John Doe",
        idempotency_key=key,
    )
    assert hold2["hold_id"] == hold1["hold_id"]
    sc = db_session.get(SeatClass, sc_id)
    assert sc.held_seats == 2  # Didn't become 4

def test_group_hold_full_fail_policy(db_session, seed_data):
    sc_id = seed_data["economy_class"].id
    flight_id = seed_data["flight"].id

    # Set capacity so only 2 seats are available
    sc = db_session.get(SeatClass, sc_id)
    sc.total_seats = 10
    sc.booked_seats = 8
    sc.held_seats = 0
    db_session.commit()

    # Requesting 4 seats should trigger Full-Fail per PRD §3
    with pytest.raises(ValueError) as exc:
        group_hold_seats(
            db_session,
            flight_id=flight_id,
            seat_class_id=sc_id,
            quantity=4,
            passenger_email="group@example.com",
            passenger_name="Group Lead",
        )
    assert "Full-fail group hold policy" in str(exc.value)
    assert "waitlist offer available" in str(exc.value).lower()

def test_resize_seat_class_cannot_shrink_below_booked(db_session, seed_data):
    sc_id = seed_data["economy_class"].id

    # Book 15 seats
    sc = db_session.get(SeatClass, sc_id)
    sc.total_seats = 50
    sc.booked_seats = 15
    db_session.commit()

    # Attempt to shrink to 10 (< 15) must fail
    with pytest.raises(ValueError) as exc:
        resize_seat_class(
            db_session,
            seat_class_id=sc_id,
            new_total_seats=10,
        )
    assert "cannot shrink seat_classes" in str(exc.value)

    # Growing to 60 or shrinking to 20 (>= 15) succeeds
    res = resize_seat_class(db_session, seat_class_id=sc_id, new_total_seats=20)
    assert res["total_seats"] == 20

def test_booking_confirmation_and_cancellation(db_session, seed_data):
    sc_id = seed_data["first_class"].id
    flight_id = seed_data["flight"].id

    # 1. Hold seat
    hold = hold_seats(
        db_session,
        flight_id=flight_id,
        seat_class_id=sc_id,
        quantity=1,
        passenger_email="vip@example.com",
        passenger_name="VIP Flyer",
    )
    db_session.commit()

    # 2. Confirm booking
    confirmed = confirm_booking(
        db_session,
        hold_id=hold["hold_id"],
        payment_method_id="pm_card_visa",
    )
    db_session.commit()

    assert confirmed["status"] == "confirmed"
    booking_id = confirmed["booking_id"]

    sc = db_session.get(SeatClass, sc_id)
    assert sc.booked_seats == 1
    assert sc.held_seats == 0

    # 3. Cancel booking (first class is refundable)
    cancel_res = cancel_booking(
        db_session,
        booking_id=booking_id,
        reason="Change of plans",
    )
    db_session.commit()

    assert cancel_res["status"] == "cancelled"
    assert cancel_res["refund_id"] is not None

    # Seat was freed and booked_seats decremented
    db_session.refresh(sc)
    assert sc.booked_seats == 0
