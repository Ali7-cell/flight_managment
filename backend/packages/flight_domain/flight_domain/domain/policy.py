import uuid
from datetime import timedelta
from typing import Any
from sqlalchemy.orm import Session
from sqlalchemy import select
from flight_domain.models.bookings import Booking
from flight_domain.models.flights import Flight, FareRule, SeatClass
from flight_domain.models.policy import PolicyDoc, PolicyDocChunk, PolicyQuestionRun
from flight_domain.models.auth import Passenger
from flight_domain.models.base import utcnow

def get_fare_rule_for_booking(session: Session, booking_id: uuid.UUID | str) -> dict[str, Any] | None:
    """
    Fetch the booking's ground-truth fare rule from Postgres.
    Used by the RAG pipeline consistency-check node to ground LLM claims.
    """
    if isinstance(booking_id, str):
        booking_id = uuid.UUID(booking_id)

    booking = session.get(Booking, booking_id)
    if not booking:
        return None

    fare_rule = session.get(FareRule, booking.fare_rules_id)
    seat_class = session.get(SeatClass, booking.seat_class_id)
    flight = session.get(Flight, booking.flight_id)

    fare_type = getattr(booking, "fare_type", "flex") or "flex"
    cabin_name = seat_class.class_name if seat_class else "Economy"

    # Compute currently-applicable refund percentage from time-to-departure and fare_type
    hours_to_dep = None
    applicable_refund_pct = 0
    now_dt = utcnow()

    if flight and flight.departure_at:
        dep_dt = (
            flight.departure_at.replace(tzinfo=now_dt.tzinfo)
            if flight.departure_at.tzinfo is None
            else flight.departure_at
        )
        hours_to_dep = round((dep_dt - now_dt).total_seconds() / 3600.0, 1)

    if fare_type == "basic_economy":
        applicable_refund_pct = 0
    else:  # flex fare
        if hours_to_dep is None or hours_to_dep >= 72.0:
            applicable_refund_pct = 100
        elif hours_to_dep >= 24.0:
            applicable_refund_pct = 75
        elif hours_to_dep >= 0.0:
            applicable_refund_pct = 50
        else:
            applicable_refund_pct = 0

    return {
        "booking_id": str(booking.id),
        "booking_reference": booking.booking_reference,
        "fare_type": fare_type,
        "fare_class": fare_rule.fare_class if fare_rule else cabin_name.lower(),
        "cabin_class": cabin_name,
        "hours_to_departure": hours_to_dep,
        "applicable_refund_percentage": applicable_refund_pct,
        "travel_credit_option_percentage": 100,
        "refundable": (applicable_refund_pct > 0),
        "change_allowed": (fare_type == "flex"),
        "change_fee_amount": 0.0 if cabin_name.lower() in ("business", "first") else 50.0 if fare_type == "flex" else None,
        "seat_choice_allowed": (fare_type == "flex"),
        "cancellation_window_hrs": fare_rule.cancellation_window_hrs if fare_rule else 24,
        "policy_text": fare_rule.policy_text if fare_rule else f"{fare_type.replace('_', ' ').title()} fare on {cabin_name}",
    }


def policy_docs_changed_since_last_ingest(session: Session) -> list[dict[str, Any]]:
    docs = session.scalars(select(PolicyDoc)).all()
    results = []
    for d in docs:
        results.append({
            "id": str(d.id),
            "title": d.title,
            "content_hash": d.content_hash,
            "fare_type_scope": d.fare_type_scope or "all",
            "category": d.category,
            "policy_text": d.title + ": policy details...",
        })
    return results

def record_chunk_ingestion(session: Session, policy_doc_id: uuid.UUID | str, chunks: list[dict[str, Any]]):
    if isinstance(policy_doc_id, str):
        policy_doc_id = uuid.UUID(policy_doc_id)

    for i, c in enumerate(chunks):
        chunk = PolicyDocChunk(
            policy_doc_id=policy_doc_id,
            chunk_index=i,
            content=c.get("content", ""),
            pinecone_vector_id=c.get("pinecone_vector_id", f"{policy_doc_id}-{i}"),
        )
        session.add(chunk)
    session.flush()

def flights_needing_checkin_reminder(session: Session) -> list[dict[str, Any]]:
    """
    Departure between now+23h and now+25h, status='scheduled'.
    Suppresses cancelled flights in one query pass (PRD §6).
    """
    now = utcnow()
    window_start = now + timedelta(hours=23)
    window_end = now + timedelta(hours=25)

    stmt = (
        select(Flight)
        .where(
            Flight.status == "scheduled",
            Flight.departure_at >= window_start,
            Flight.departure_at <= window_end,
        )
    )
    flights = session.scalars(stmt).all()
    results = []
    for f in flights:
        # fetch confirmed passengers
        bookings = session.scalars(
            select(Booking).where(Booking.flight_id == f.id, Booking.status == "confirmed")
        ).all()
        for b in bookings:
            p = session.get(Passenger, b.passenger_id)
            if p:
                results.append({
                    "id": str(f.id),
                    "flight_number": f.flight_number,
                    "origin": f.origin,
                    "destination": f.destination,
                    "origin_tz": f.origin_tz,
                    "destination_tz": f.destination_tz,
                    "departure_at": f.departure_at,
                    "passenger_email": p.email,
                    "passenger_name": p.full_name,
                })
    return results
