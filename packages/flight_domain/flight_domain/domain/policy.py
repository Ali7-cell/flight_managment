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
    if not fare_rule:
        return None

    return {
        "booking_id": str(booking.id),
        "booking_reference": booking.booking_reference,
        "fare_class": fare_rule.fare_class,
        "refundable": fare_rule.refundable,
        "change_allowed": fare_rule.change_allowed,
        "change_fee_amount": float(fare_rule.change_fee_amount) if fare_rule.change_fee_amount is not None else None,
        "seat_choice_allowed": fare_rule.seat_choice_allowed,
        "cancellation_window_hrs": fare_rule.cancellation_window_hrs,
        "policy_text": fare_rule.policy_text,
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
