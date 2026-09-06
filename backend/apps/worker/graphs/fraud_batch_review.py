from typing import TypedDict, Any
from langgraph.graph import StateGraph, START, END
from sqlalchemy import select, func
from flight_domain.db import SessionLocal
from flight_domain.models.bookings import Booking
from flight_domain.models.fraud import FraudScore
from flight_domain.domain.fraud import record_fraud_score

try:
    from apps.worker.services.fraud_detector import score_booking
    from apps.worker.checkpointer import checkpointer
except ImportError:
    from services.fraud_detector import score_booking  # type: ignore
    from checkpointer import checkpointer  # type: ignore

class FraudBatchState(TypedDict):
    scanned_count: int
    retroactively_flagged: int

def scan_historical_bookings(state: FraudBatchState) -> dict:
    scanned = 0
    flagged = 0

    with SessionLocal() as session:
        # Find historical bookings without an existing score
        unscored_bookings = session.scalars(
            select(Booking)
            .outerjoin(FraudScore, Booking.id == FraudScore.booking_id)
            .where(FraudScore.id.is_(None))
            .limit(100)
        ).all()

        for b in unscored_bookings:
            b_dict = {
                "id": b.id,
                "flight_id": b.flight_id,
                "quantity": b.quantity,
                "total_amount": float(b.total_amount),
                "created_at": b.created_at,
            }
            score, signals = score_booking(b_dict)
            record_fraud_score(session, booking_id=b.id, score=score, signals=signals)
            scanned += 1
            if score >= 0.7:
                flagged += 1

        session.commit()

    return {"scanned_count": scanned, "retroactively_flagged": flagged}

builder = StateGraph(FraudBatchState)
builder.add_node("scan_historical_bookings", scan_historical_bookings)
builder.add_edge(START, "scan_historical_bookings")
builder.add_edge("scan_historical_bookings", END)

fraud_batch_review_graph = builder.compile(checkpointer=checkpointer)
