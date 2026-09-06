from typing import TypedDict, Any
from langgraph.graph import StateGraph, START, END
from flight_domain.db import SessionLocal
from flight_domain.domain.fraud import bookings_since_last_scan, record_fraud_score

try:
    from apps.worker.services.fraud_detector import score_booking
    from apps.worker.checkpointer import checkpointer
except ImportError:
    from services.fraud_detector import score_booking  # type: ignore
    from checkpointer import checkpointer  # type: ignore

class FraudScanState(TypedDict):
    scanned_count: int
    flagged_count: int

def score_recent_bookings(state: FraudScanState) -> dict:
    scanned = 0
    flagged = 0
    with SessionLocal() as session:
        bookings = bookings_since_last_scan(session)
        for b in bookings:
            score, signals = score_booking(b)
            record_fraud_score(session, booking_id=b["id"], score=score, signals=signals)
            scanned += 1
            if score >= 0.7:
                flagged += 1
        session.commit()
    return {"scanned_count": scanned, "flagged_count": flagged}

builder = StateGraph(FraudScanState)
builder.add_node("score_recent_bookings", score_recent_bookings)
builder.add_edge(START, "score_recent_bookings")
builder.add_edge("score_recent_bookings", END)

fraud_scan_graph = builder.compile(checkpointer=checkpointer)
