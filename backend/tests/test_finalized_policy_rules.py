import uuid
from decimal import Decimal
from datetime import timedelta
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from flight_domain.models.base import Base, utcnow
from flight_domain.models.flights import Flight, SeatClass, FareRule
from flight_domain.models.bookings import Booking, SeatHold, Refund, TravelCredit, WaitlistEntry
from flight_domain.models.auth import Passenger
from flight_domain.domain.bookings import confirm_booking, cancel_booking
from flight_domain.domain.seats import hold_seats, release_seat_and_promote
from flight_domain.domain.waitlist import join_waitlist, get_waitlist_position
from flight_domain.domain.policy import get_fare_rule_for_booking
from flight_domain.config import REFUND_ESCALATION_DAYS, WAITLIST_CLAIM_WINDOW_HOURS
from apps.worker.graphs.refund_escalation import find_and_escalate_stuck_refunds
from apps.worker.services.grounding import llm_structured_draft, diff_claims_against_ground_truth, DraftClaims

@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

def create_seed_flight(session, departure_in_hours=96):
    flight = Flight(
        flight_number="JOBY-202",
        origin="JFK",
        destination="LHR",
        origin_tz="America/New_York",
        destination_tz="Europe/London",
        departure_at=utcnow() + timedelta(hours=departure_in_hours),
        arrival_at=utcnow() + timedelta(hours=departure_in_hours + 7),
        status="scheduled",
        total_seats=70,
    )
    session.add(flight)
    session.flush()


    fare_rule_eco = FareRule(
        fare_class="economy",
        refundable=True,
        change_allowed=True,
        change_fee_amount=Decimal("50.00"),
        seat_choice_allowed=True,
        cancellation_window_hrs=24,
        policy_text="Economy fare rule",
    )
    session.add(fare_rule_eco)
    session.flush()

    sc_eco = SeatClass(
        flight_id=flight.id,
        class_name="economy",
        total_seats=50,
        booked_seats=0,
        held_seats=0,
        fare_base_amount=Decimal("150.00"),
        fare_rules_id=fare_rule_eco.id,
    )
    sc_biz = SeatClass(
        flight_id=flight.id,
        class_name="business",
        total_seats=20,
        booked_seats=0,
        held_seats=0,
        fare_base_amount=Decimal("450.00"),
        fare_rules_id=fare_rule_eco.id,
    )

    session.add_all([sc_eco, sc_biz])
    session.flush()
    return flight, sc_eco, sc_biz

def test_named_constants_defined():
    """Rule 5: Named constants REFUND_ESCALATION_DAYS=7 and WAITLIST_CLAIM_WINDOW_HOURS=2."""
    assert REFUND_ESCALATION_DAYS == 7
    assert WAITLIST_CLAIM_WINDOW_HOURS == 2

def test_basic_economy_rejected_on_non_economy(db_session):
    """Rule 2: Reject fare_type='basic_economy' unless seat class is 'Economy'."""
    flight, sc_eco, sc_biz = create_seed_flight(db_session)
    hold = hold_seats(
        db_session,
        flight_id=flight.id,
        seat_class_id=sc_biz.id,
        quantity=1,
        passenger_email="biz@example.com",
        passenger_name="Biz Traveler",
    )
    db_session.flush()

    # Attempting to confirm Business with basic_economy must fail
    with pytest.raises(ValueError) as exc:
        confirm_booking(
            db_session,
            hold_id=hold["hold_id"],
            payment_method_id="pm_test",
            fare_type="basic_economy",
        )
    assert "basic_economy fare type is only valid for Economy seat class" in str(exc.value)

def test_basic_economy_allowed_on_economy(db_session):
    """Rule 1 & 2: basic_economy allowed on Economy."""
    flight, sc_eco, sc_biz = create_seed_flight(db_session)
    hold = hold_seats(
        db_session,
        flight_id=flight.id,
        seat_class_id=sc_eco.id,
        quantity=1,
        passenger_email="eco@example.com",
        passenger_name="Eco Traveler",
    )
    db_session.flush()

    res = confirm_booking(
        db_session,
        hold_id=hold["hold_id"],
        payment_method_id="pm_test",
        fare_type="basic_economy",
    )
    assert res["status"] == "confirmed"
    booking = db_session.get(Booking, res["booking_id"])
    assert booking.fare_type == "basic_economy"

def test_cancellation_refund_tiers_flex(db_session):
    """Rule for Flex: 100% at 72h+, 75% at 24-72h, 50% under 24h, 0% no-show."""
    # 1. 72+ hours: 100% refund
    flight_72, sc_eco, _ = create_seed_flight(db_session, departure_in_hours=80)
    hold = hold_seats(db_session, flight_id=flight_72.id, seat_class_id=sc_eco.id, quantity=1, passenger_email="p1@test.com", passenger_name="P1")
    bk1 = confirm_booking(db_session, hold_id=hold["hold_id"], payment_method_id="pm_1", fare_type="flex")
    res1 = cancel_booking(db_session, booking_id=bk1["booking_id"])
    assert res1["refund_id"] is not None
    refund1 = db_session.get(Refund, res1["refund_id"])
    assert refund1.amount == Decimal("150.00")  # 100%

    # 2. 24-72 hours: 75% refund
    flight_48, sc_eco2, _ = create_seed_flight(db_session, departure_in_hours=48)
    hold2 = hold_seats(db_session, flight_id=flight_48.id, seat_class_id=sc_eco2.id, quantity=1, passenger_email="p2@test.com", passenger_name="P2")
    bk2 = confirm_booking(db_session, hold_id=hold2["hold_id"], payment_method_id="pm_2", fare_type="flex")
    res2 = cancel_booking(db_session, booking_id=bk2["booking_id"])
    refund2 = db_session.get(Refund, res2["refund_id"])
    assert refund2.amount == Decimal("112.50")  # 75% of 150.00

    # 3. Under 24 hours: 50% refund
    flight_12, sc_eco3, _ = create_seed_flight(db_session, departure_in_hours=12)
    hold3 = hold_seats(db_session, flight_id=flight_12.id, seat_class_id=sc_eco3.id, quantity=1, passenger_email="p3@test.com", passenger_name="P3")
    bk3 = confirm_booking(db_session, hold_id=hold3["hold_id"], payment_method_id="pm_3", fare_type="flex")
    res3 = cancel_booking(db_session, booking_id=bk3["booking_id"])
    refund3 = db_session.get(Refund, res3["refund_id"])
    assert refund3.amount == Decimal("75.00")  # 50% of 150.00

def test_basic_economy_cancellation_policy(db_session):
    """basic_economy voluntary = 0 refund & 0 credit; airline cancellation = 100% travel credit."""
    flight, sc_eco, _ = create_seed_flight(db_session, departure_in_hours=80)
    hold = hold_seats(db_session, flight_id=flight.id, seat_class_id=sc_eco.id, quantity=1, passenger_email="be@test.com", passenger_name="BE Traveler")
    bk = confirm_booking(db_session, hold_id=hold["hold_id"], payment_method_id="pm_1", fare_type="basic_economy")

    # Voluntary cancel: no cash, no credit
    res_vol = cancel_booking(db_session, booking_id=bk["booking_id"], actor="customer", reason="Voluntary cancel")
    assert res_vol["refund_id"] is None
    assert res_vol["credit_issued_amount"] is None

    # Airline initiated cancel on a second booking: gets 100% travel credit
    hold2 = hold_seats(db_session, flight_id=flight.id, seat_class_id=sc_eco.id, quantity=1, passenger_email="be2@test.com", passenger_name="BE Traveler 2")
    bk2 = confirm_booking(db_session, hold_id=hold2["hold_id"], payment_method_id="pm_2", fare_type="basic_economy")
    res_air = cancel_booking(db_session, booking_id=bk2["booking_id"], actor="airline", reason="Flight cancelled by airline")
    assert res_air["refund_id"] is None
    assert Decimal(res_air["credit_issued_amount"]) == Decimal("150.00")


def test_dynamic_waitlist_priority_ordering(db_session):
    """
    Rule 3: Waitlist priority = loyalty tier (Platinum > Gold > Silver > none),
    then fare_type (flex before basic_economy), then join time — computed fresh.
    """
    flight, sc_eco, _ = create_seed_flight(db_session)

    # 1. Join Gold member with flex
    p_gold = Passenger(email="gold@test.com", full_name="Gold Passenger", loyalty_tier="gold")
    db_session.add(p_gold)
    db_session.flush()
    wl1 = join_waitlist(db_session, flight_id=flight.id, seat_class_id=sc_eco.id, quantity=1, passenger_email="gold@test.com", passenger_name="Gold", fare_type="flex")

    # 2. Join Platinum member with flex (joined AFTER gold, but has higher loyalty tier)
    p_plat = Passenger(email="plat@test.com", full_name="Platinum Passenger", loyalty_tier="platinum")
    db_session.add(p_plat)
    db_session.flush()
    wl2 = join_waitlist(db_session, flight_id=flight.id, seat_class_id=sc_eco.id, quantity=1, passenger_email="plat@test.com", passenger_name="Plat", fare_type="flex")

    # 3. Join Silver member with basic_economy
    p_silver = Passenger(email="silver@test.com", full_name="Silver Passenger", loyalty_tier="silver")
    db_session.add(p_silver)
    db_session.flush()
    wl3 = join_waitlist(db_session, flight_id=flight.id, seat_class_id=sc_eco.id, quantity=1, passenger_email="silver@test.com", passenger_name="Silver", fare_type="basic_economy")

    # Platinum must be #1 position, Gold #2, Silver #3
    pos_plat = get_waitlist_position(db_session, wl2["waitlist_entry_id"])
    pos_gold = get_waitlist_position(db_session, wl1["waitlist_entry_id"])
    pos_silver = get_waitlist_position(db_session, wl3["waitlist_entry_id"])

    assert pos_plat["estimated_position"] == 1
    assert pos_gold["estimated_position"] == 2
    assert pos_silver["estimated_position"] == 3

    # Now simulate promotion: Platinum must be chosen first!
    promo = release_seat_and_promote(db_session, seat_class_id=sc_eco.id, quantity=1)
    assert promo["promoted"] is True
    assert promo["promoted_details"]["waitlist_entry_id"] == wl2["waitlist_entry_id"]

    # Verify claim window is exactly 2 hours (WAITLIST_CLAIM_WINDOW_HOURS)
    plat_entry = db_session.get(WaitlistEntry, wl2["waitlist_entry_id"])
    assert plat_entry.status == "promoted"
    diff_hours = (
        plat_entry.offer_expires_at.replace(tzinfo=None)
        - plat_entry.created_at.replace(tzinfo=None)
    ).total_seconds() / 3600.0
    assert abs(diff_hours - 2.0) < 0.1


def test_rag_applicable_refund_percentage_computation(db_session):
    """Rule 6: RAG context computes currently-applicable refund percentage based on time-to-departure."""
    # Booking 80 hours away: 100%
    flight_80, sc_eco, _ = create_seed_flight(db_session, departure_in_hours=80)
    hold = hold_seats(db_session, flight_id=flight_80.id, seat_class_id=sc_eco.id, quantity=1, passenger_email="rag1@test.com", passenger_name="RAG 1")
    bk1 = confirm_booking(db_session, hold_id=hold["hold_id"], payment_method_id="pm_1", fare_type="flex")
    ctx1 = get_fare_rule_for_booking(db_session, bk1["booking_id"])
    assert ctx1["applicable_refund_percentage"] == 100
    assert ctx1["fare_type"] == "flex"

    # Booking 30 hours away: 75%
    flight_30, sc_eco2, _ = create_seed_flight(db_session, departure_in_hours=30)
    hold2 = hold_seats(db_session, flight_id=flight_30.id, seat_class_id=sc_eco2.id, quantity=1, passenger_email="rag2@test.com", passenger_name="RAG 2")
    bk2 = confirm_booking(db_session, hold_id=hold2["hold_id"], payment_method_id="pm_2", fare_type="flex")
    ctx2 = get_fare_rule_for_booking(db_session, bk2["booking_id"])
    assert ctx2["applicable_refund_percentage"] == 75

    # Booking with basic_economy: 0% cash refund
    hold3 = hold_seats(db_session, flight_id=flight_80.id, seat_class_id=sc_eco.id, quantity=1, passenger_email="rag3@test.com", passenger_name="RAG 3")
    bk3 = confirm_booking(db_session, hold_id=hold3["hold_id"], payment_method_id="pm_3", fare_type="basic_economy")
    ctx3 = get_fare_rule_for_booking(db_session, bk3["booking_id"])
    assert ctx3["applicable_refund_percentage"] == 0
    assert ctx3["fare_type"] == "basic_economy"

    # Test LLM draft answer reflects the 75% tier for booking 2
    draft = llm_structured_draft("How much refund can I get if I cancel?", ctx2, [])
    assert draft.cited_applicable_refund_pct == 75
    assert "75% cash refund" in draft.answer_text
    flags = diff_claims_against_ground_truth(draft, ctx2)
    assert len(flags) == 0
