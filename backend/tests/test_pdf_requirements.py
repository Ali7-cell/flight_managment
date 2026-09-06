import uuid
import pytest
from decimal import Decimal
from datetime import datetime, timezone, timedelta
from sqlalchemy import select
from flight_domain.domain.admin import create_flight, cancel_flight, apply_schedule_change, get_flight_seat_map
from flight_domain.domain.seats import hold_seats, group_hold_seats, hold_multi_leg_seats, resize_seat_class
from flight_domain.domain.bookings import confirm_booking, cancel_booking, cancel_partial_booking
from flight_domain.domain.waitlist import join_waitlist, compute_priority_score
from flight_domain.domain.search import search_flights, search_connecting_flights
from flight_domain.domain.reconciliation import run_inventory_reconciliation
from flight_domain.domain.autonomy import submit_compensation_claim, review_compensation_claim
from flight_domain.models.flights import Flight, SeatClass, PhysicalSeat
from flight_domain.models.bookings import Booking, SeatHold, CompensationClaim
from flight_domain.models.auth import AdminUser, Passenger
from flight_domain.security import hash_password, create_jwt_token

def test_aircraft_capacity_validation(db_session):
    # UK -> Dubai flight departing 05:00, 100 total seats (20 First, 30 Business, 50 Economy)
    dep_local = datetime(2026, 10, 1, 5, 0)
    arr_local = datetime(2026, 10, 1, 15, 0)

    # 1. Matching aircraft capacity passes
    flight_data = create_flight(
        db_session,
        flight_number="BA105",
        origin="LHR",
        destination="DXB",
        origin_tz="Europe/London",
        destination_tz="Asia/Dubai",
        departure_local=dep_local,
        arrival_local=arr_local,
        aircraft_capacity=100,
        seat_allocation={"first": 20, "business": 30, "economy": 50},
    )
    assert flight_data["total_seats"] == 100
    assert "BA105" in flight_data["flight_number"]

    # 2. Mismatched capacity fails
    with pytest.raises(ValueError, match="must match declared aircraft capacity"):
        create_flight(
            db_session,
            flight_number="BA106",
            origin="LHR",
            destination="DXB",
            origin_tz="Europe/London",
            destination_tz="Asia/Dubai",
            departure_local=dep_local + timedelta(days=1),
            arrival_local=arr_local + timedelta(days=1),
            aircraft_capacity=120,  # mismatch with sum 100
            seat_allocation={"first": 20, "business": 30, "economy": 50},
        )

    # 3. Negative or zero seat count fails
    with pytest.raises(ValueError, match="must be a positive integer"):
        create_flight(
            db_session,
            flight_number="BA107",
            origin="LHR",
            destination="DXB",
            origin_tz="Europe/London",
            destination_tz="Asia/Dubai",
            departure_local=dep_local + timedelta(days=2),
            arrival_local=arr_local + timedelta(days=2),
            aircraft_capacity=50,
            seat_allocation={"first": -10, "business": 0, "economy": 50},
        )

def test_physical_seat_map_generation_and_selection(db_session):
    dep_local = datetime(2026, 11, 1, 6, 0)
    arr_local = datetime(2026, 11, 1, 16, 0)

    flight_data = create_flight(
        db_session,
        flight_number="EK500",
        origin="LHR",
        destination="DXB",
        origin_tz="Europe/London",
        destination_tz="Asia/Dubai",
        departure_local=dep_local,
        arrival_local=arr_local,
        aircraft_capacity=10,
        seat_allocation={"first": 4, "business": 6},
    )
    f_id = uuid.UUID(flight_data["flight_id"])

    # Verify physical seats were generated
    seat_map = get_flight_seat_map(db_session, f_id)
    assert len(seat_map) == 10
    seat_numbers = [s["seat_number"] for s in seat_map]
    assert "1A" in seat_numbers
    assert "1B" in seat_numbers

    # Hold a specific physical seat
    first_class = db_session.scalar(
        select(SeatClass).where(SeatClass.flight_id == f_id, SeatClass.class_name == "first")
    )
    assert first_class is not None

    hold = hold_seats(
        db_session,
        flight_id=f_id,
        seat_class_id=first_class.id,
        quantity=1,
        passenger_email="vip@example.com",
        passenger_name="VIP Passenger",
        seat_number="1A",
    )
    assert hold["seat_number"] == "1A"

    # Attempting to hold the same physical seat again fails
    with pytest.raises(ValueError, match="already occupied"):
        hold_seats(
            db_session,
            flight_id=f_id,
            seat_class_id=first_class.id,
            quantity=1,
            passenger_email="other@example.com",
            passenger_name="Other Passenger",
            seat_number="1A",
        )

def test_partial_cancellation_proportional_refund(db_session, seed_data):
    sc = seed_data["economy_class"]
    flight = seed_data["flight"]

    # 1. Hold 4 seats
    hold = hold_seats(
        db_session,
        flight_id=flight.id,
        seat_class_id=sc.id,
        quantity=4,
        passenger_email="family@example.com",
        passenger_name="Family Group",
    )
    # 2. Confirm booking
    booking_res = confirm_booking(
        db_session,
        hold_id=hold["hold_id"],
        payment_method_id="pm_card_visa",
    )
    b_id = booking_res["booking_id"]
    orig_amount = Decimal(booking_res["total_amount"])

    # 3. Partially cancel 2 seats
    part_res = cancel_partial_booking(
        db_session,
        booking_id=b_id,
        seats_to_cancel=2,
        reason="Two members cannot travel",
    )

    assert part_res["cancelled_seats"] == 2
    assert part_res["remaining_seats"] == 2
    assert Decimal(part_res["new_total_amount"]) == orig_amount / 2
    assert part_res["status"] == "confirmed"

def test_multi_leg_atomic_hold(db_session, seed_data):
    sc1 = seed_data["economy_class"]
    f1 = seed_data["flight"]

    # Create a second connecting flight
    f2_res = create_flight(
        db_session,
        flight_number="DXB-SYD-1",
        origin="DXB",
        destination="SYD",
        origin_tz="Asia/Dubai",
        destination_tz="Australia/Sydney",
        departure_local=datetime(2026, 12, 1, 18, 0),
        arrival_local=datetime(2026, 12, 2, 6, 0),
        aircraft_capacity=50,
        seat_allocation={"economy": 50},
    )
    f2_id = uuid.UUID(f2_res["flight_id"])
    sc2_id = uuid.UUID(f2_res["seat_classes"]["economy"]["seat_class_id"])

    # Hold both legs atomically
    multi_hold = hold_multi_leg_seats(
        db_session,
        legs=[
            {"flight_id": f1.id, "seat_class_id": sc1.id, "quantity": 1},
            {"flight_id": f2_id, "seat_class_id": sc2_id, "quantity": 1},
        ],
        passenger_email="globetrotter@example.com",
        passenger_name="World Traveler",
    )
    assert multi_hold["multi_leg"] is True
    assert len(multi_hold["legs"]) == 2

def test_waitlist_priority_rule_fare_class_weighting():
    # Platinum + First class vs Gold + Economy
    score_plat_first = compute_priority_score("platinum", fare_class="first")
    score_gold_econ = compute_priority_score("gold", fare_class="economy")
    score_plat_econ = compute_priority_score("platinum", fare_class="economy")
    score_none_first = compute_priority_score("none", fare_class="first")

    # Platinum First should exceed Platinum Economy
    assert score_plat_first > score_plat_econ
    # First class bonus (+300) pushes even 'none' tier above 'silver' economy (200 + 25)
    assert score_none_first > compute_priority_score("silver", fare_class="economy")

def test_reconciliation_drift_detection(db_session, seed_data):
    sc = seed_data["economy_class"]
    # Intentionally inject drift: increment booked_seats without confirmed booking
    sc.booked_seats = 99
    db_session.commit()

    recon_res = run_inventory_reconciliation(db_session)
    assert recon_res["status"] == "drift_detected"
    assert recon_res["discrepancies_count"] >= 1
    drift_item = [d for d in recon_res["discrepancies"] if d["seat_class_id"] == str(sc.id)][0]
    assert drift_item["recorded_booked_seats"] == 99

def test_compensation_claim_autonomy_workflow(db_session, seed_data):
    flight = seed_data["flight"]
    passenger = seed_data["passengers"][0]

    # Submit claim (requires human sign-off per Domain 8)
    claim_res = submit_compensation_claim(
        db_session,
        flight_id=flight.id,
        passenger_id=passenger.id,
        claim_type="denied_boarding",
        requested_amount=600.0,
        reason="Overbooked gate denial",
    )
    assert claim_res["requires_human_signoff"] is True
    assert claim_res["status"] == "pending_review"

    # Supervisor review
    admin = AdminUser(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        email="super@aeroflow.com",
        role="super_admin",
    )
    db_session.add(admin)
    db_session.flush()

    review_res = review_compensation_claim(
        db_session,
        claim_id=claim_res["claim_id"],
        action="approve",
        admin_user=admin,
        notes="Mandatory EU261/DOT passenger compensation approved",
    )
    assert review_res["status"] == "approved"
    assert review_res["reviewed_by"] == str(admin.id)
