import os
import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from flight_domain.models.base import Base
from flight_domain.models.flights import Flight, SeatClass, FareRule
from flight_domain.models.auth import Passenger, AdminUser
from flight_domain.db import get_db_session
import flight_domain.db as fms_db
from apps.api.main import app
from apps.api.dependencies import get_db

TEST_DATABASE_URL = "sqlite:///:memory:"

@pytest.fixture(scope="session")
def engine():
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)

@pytest.fixture
def db_session(engine):
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = Session()
    try:
        yield session
    finally:
        session.rollback()
        session.close()

@pytest.fixture
def seed_data(db_session):
    """Seed sample flight, fare rules, and seat classes."""
    db_session.query(SeatClass).delete()
    db_session.query(Flight).delete()
    db_session.query(FareRule).delete()
    db_session.query(Passenger).delete()
    db_session.commit()

    # Create Fare Rules
    economy_rule = FareRule(
        fare_class="economy",
        refundable=False,
        change_allowed=False,
        change_fee_amount=Decimal("150.00"),
        seat_choice_allowed=False,
        cancellation_window_hrs=24,
        policy_text="Economy fare: strictly non-refundable. $150 change fee.",
    )
    first_rule = FareRule(
        fare_class="first",
        refundable=True,
        change_allowed=True,
        change_fee_amount=Decimal("0.00"),
        seat_choice_allowed=True,
        cancellation_window_hrs=72,
        policy_text="First class fare: 100% refundable with zero fees.",
    )
    db_session.add_all([economy_rule, first_rule])
    db_session.flush()

    # Create Flight (UK to Dubai)
    now = datetime.now(timezone.utc)
    flight = Flight(
        flight_number="BA105",
        origin="LHR",
        destination="DXB",
        origin_tz="Europe/London",
        destination_tz="Asia/Dubai",
        departure_at=now + timedelta(days=5),
        arrival_at=now + timedelta(days=5, hours=7),
        status="scheduled",
        total_seats=100,
    )
    db_session.add(flight)
    db_session.flush()

    # Create Seat Class (Economy: 50 seats)
    economy_class = SeatClass(
        flight_id=flight.id,
        class_name="economy",
        total_seats=50,
        booked_seats=0,
        held_seats=0,
        fare_rules_id=economy_rule.id,
        fare_base_amount=Decimal("250.00"),
        currency="USD",
    )
    first_class = SeatClass(
        flight_id=flight.id,
        class_name="first",
        total_seats=20,
        booked_seats=0,
        held_seats=0,
        fare_rules_id=first_rule.id,
        fare_base_amount=Decimal("1200.00"),
        currency="USD",
    )
    db_session.add_all([economy_class, first_class])
    db_session.flush()

    # Create Passengers
    p1 = Passenger(
        email="alice@example.com",
        full_name="Alice Smith",
        loyalty_tier="platinum",
    )
    p2 = Passenger(
        email="bob@example.com",
        full_name="Bob Jones",
        loyalty_tier="none",
    )
    db_session.add_all([p1, p2])
    db_session.commit()

    return {
        "flight": flight,
        "economy_class": economy_class,
        "first_class": first_class,
        "economy_rule": economy_rule,
        "first_rule": first_rule,
        "passengers": [p1, p2],
    }

@pytest.fixture
def client(engine):
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    def override_get_db():
        session = Session()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
