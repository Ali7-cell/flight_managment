"""
AeroFlow FMS - Flight Database Seeder
Seeds realistic flights across popular international and domestic routes.
"""

import uuid
from decimal import Decimal
from datetime import datetime, timedelta, timezone
from flight_domain.db import get_db_session
from flight_domain.models.flights import Flight, SeatClass, FareRule

def seed():
    with get_db_session() as db:
        # Check existing flights
        existing = {f.flight_number for f in db.query(Flight).all()}
        print(f"Existing flights in database: {existing}")

        # 1. Ensure Fare Rules
        eco_rule = db.query(FareRule).filter_by(fare_class="economy").first()
        if not eco_rule:
            eco_rule = FareRule(
                id=uuid.uuid4(),
                fare_class="economy",
                refundable=False,
                change_allowed=True,
                change_fee_amount=Decimal("50.00"),
                seat_choice_allowed=False,
                cancellation_window_hrs=24,
                policy_text="Economy Standard: Non-refundable, date changes permitted with fee.",
            )
            db.add(eco_rule)

        biz_rule = db.query(FareRule).filter_by(fare_class="business").first()
        if not biz_rule:
            biz_rule = FareRule(
                id=uuid.uuid4(),
                fare_class="business",
                refundable=True,
                change_allowed=True,
                change_fee_amount=Decimal("0.00"),
                seat_choice_allowed=True,
                cancellation_window_hrs=48,
                policy_text="Business Premier: 100% refundable, free seat selection, lounge access.",
            )
            db.add(biz_rule)

        first_rule = db.query(FareRule).filter_by(fare_class="first").first()
        if not first_rule:
            first_rule = FareRule(
                id=uuid.uuid4(),
                fare_class="first",
                refundable=True,
                change_allowed=True,
                change_fee_amount=Decimal("0.00"),
                seat_choice_allowed=True,
                cancellation_window_hrs=72,
                policy_text="First Suite: 100% refundable with zero fees, private chauffeur service.",
            )
            db.add(first_rule)

        db.flush()

        # 2. Seed Flights
        now = datetime.now(timezone.utc)
        flights_to_seed = [
            {
                "flight_number": "AF204",
                "origin": "JFK",
                "destination": "LHR",
                "origin_tz": "America/New_York",
                "destination_tz": "Europe/London",
                "dep_offset_days": 2,
                "duration_hrs": 7,
                "classes": [
                    ("economy", 150, 480.00, eco_rule.id),
                    ("business", 30, 1450.00, biz_rule.id),
                    ("first", 8, 3200.00, first_rule.id),
                ]
            },
            {
                "flight_number": "BA105",
                "origin": "LHR",
                "destination": "DXB",
                "origin_tz": "Europe/London",
                "destination_tz": "Asia/Dubai",
                "dep_offset_days": 3,
                "duration_hrs": 7,
                "classes": [
                    ("economy", 120, 450.00, eco_rule.id),
                    ("business", 24, 1350.00, biz_rule.id),
                    ("first", 8, 2900.00, first_rule.id),
                ]
            },
            {
                "flight_number": "EK601",
                "origin": "DXB",
                "destination": "LHR",
                "origin_tz": "Asia/Dubai",
                "destination_tz": "Europe/London",
                "dep_offset_days": 4,
                "duration_hrs": 8,
                "classes": [
                    ("economy", 180, 520.00, eco_rule.id),
                    ("business", 35, 1600.00, biz_rule.id),
                ]
            },
            {
                "flight_number": "PK308",
                "origin": "KHI",
                "destination": "DXB",
                "origin_tz": "Asia/Karachi",
                "destination_tz": "Asia/Dubai",
                "dep_offset_days": 2,
                "duration_hrs": 3,
                "classes": [
                    ("economy", 140, 220.00, eco_rule.id),
                    ("business", 18, 550.00, biz_rule.id),
                ]
            },
            {
                "flight_number": "UA412",
                "origin": "SFO",
                "destination": "JFK",
                "origin_tz": "America/Los_Angeles",
                "destination_tz": "America/New_York",
                "dep_offset_days": 1,
                "duration_hrs": 6,
                "classes": [
                    ("economy", 160, 310.00, eco_rule.id),
                    ("business", 20, 890.00, biz_rule.id),
                ]
            },
        ]

        for item in flights_to_seed:
            fn = item["flight_number"]
            if fn in existing:
                print(f"Flight {fn} already exists, skipping.")
                continue

            dep_time = now + timedelta(days=item["dep_offset_days"], hours=10)
            arr_time = dep_time + timedelta(hours=item["duration_hrs"])
            total_seats = sum(c[1] for c in item["classes"])

            f = Flight(
                id=uuid.uuid4(),
                flight_number=fn,
                origin=item["origin"],
                destination=item["destination"],
                origin_tz=item["origin_tz"],
                destination_tz=item["destination_tz"],
                departure_at=dep_time,
                arrival_at=arr_time,
                status="scheduled",
                total_seats=total_seats,
            )
            db.add(f)
            db.flush()

            for class_name, seats, fare, rule_id in item["classes"]:
                sc = SeatClass(
                    id=uuid.uuid4(),
                    flight_id=f.id,
                    class_name=class_name,
                    total_seats=seats,
                    booked_seats=0,
                    held_seats=0,
                    fare_rules_id=rule_id,
                    fare_base_amount=Decimal(str(fare)),
                    currency="USD",
                )
                db.add(sc)

            print(f"Created flight {fn} ({item['origin']} -> {item['destination']}) with {len(item['classes'])} seat classes.")

        db.commit()
        print("Seeding complete successfully!")

if __name__ == "__main__":
    seed()
