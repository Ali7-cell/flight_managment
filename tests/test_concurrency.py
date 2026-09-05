import concurrent.futures
from decimal import Decimal
from typing import Any
from sqlalchemy.orm import sessionmaker
from flight_domain.domain.seats import release_seat_and_promote
from flight_domain.models.bookings import WaitlistEntry
from flight_domain.models.flights import SeatClass

def test_concurrency_race_on_freed_seat(engine: Any, seed_data: dict[str, Any]):
    """
    Validates 02_system_architecture.md §3:
    Two concurrent callers racing on the same seat_class_id:
    - Exactly one promotion occurs
    - No capacity violation (booked_seats + held_seats <= total_seats)
    - booked_seats never drops below 0 or doubles
    """
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    seat_class_id = seed_data["economy_class"].id
    flight_id = seed_data["flight"].id
    p1 = seed_data["passengers"][0]

    # Set up scenario:
    # 1 seat is currently booked in a 10-seat class.
    # Exactly ONE passenger is waiting on the waitlist for 1 seat.
    with Session() as session:
        sc = session.get(SeatClass, seat_class_id)
        assert sc is not None
        setattr(sc, "total_seats", 10)
        setattr(sc, "booked_seats", 1)
        setattr(sc, "held_seats", 0)

        # Clear existing waitlist and add 1 waiting candidate
        session.query(WaitlistEntry).delete()
        wl = WaitlistEntry(
            flight_id=flight_id,
            seat_class_id=seat_class_id,
            passenger_id=p1.id,
            quantity=1,
            priority_score=Decimal("1000.00"),
            status="waiting",
        )
        session.add(wl)
        session.commit()
        wl_id = wl.id

    # Two concurrent callers run release_seat_and_promote simultaneously
    results = []

    def caller_task(caller_id: int):
        with Session() as session:
            try:
                res = release_seat_and_promote(
                    session,
                    seat_class_id=seat_class_id,
                    quantity=1,
                    actor=f"test:caller_{caller_id}",
                )
                session.commit()
                return res
            except Exception as e:
                session.rollback()
                return {"error": str(e)}

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        f1 = executor.submit(caller_task, 1)
        f2 = executor.submit(caller_task, 2)
        results = [f1.result(), f2.result()]

    # Assertions
    promotions = [r for r in results if r.get("promoted") is True]
    assert len(promotions) == 1, f"Expected exactly 1 promotion, got {len(promotions)}: {results}"

    # Verify final state in database
    with Session() as session:
        sc = session.get(SeatClass, seat_class_id)
        wl = session.get(WaitlistEntry, wl_id)
        assert sc is not None
        assert wl is not None

        # Capacity invariant
        booked = int(getattr(sc, "booked_seats"))
        held = int(getattr(sc, "held_seats"))
        total = int(getattr(sc, "total_seats"))

        assert booked + held <= total
        assert booked >= 0

        # Waitlist entry is now promoted
        assert str(getattr(wl, "status")) == "promoted"
