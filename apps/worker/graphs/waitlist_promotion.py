from typing import TypedDict, Any
from langgraph.graph import StateGraph, START, END
from flight_domain.db import SessionLocal
from flight_domain.domain.outbox import claim_unprocessed_events
from flight_domain.domain.seats import release_seat_and_promote

try:
    from apps.worker.checkpointer import checkpointer
except ImportError:
    from checkpointer import checkpointer  # type: ignore

class WaitlistPromoState(TypedDict):
    candidates: list[dict[str, Any]]
    promotions_count: int

def find_freed_seats(state: WaitlistPromoState) -> dict:
    with SessionLocal() as session:
        # Claim unprocessed seat_released events with SELECT FOR UPDATE SKIP LOCKED
        events = claim_unprocessed_events(session, event_type="seat_released", limit=50)
        session.commit()
    return {"candidates": events, "promotions_count": 0}

def promote_each(state: WaitlistPromoState) -> dict:
    count = 0
    candidates = state.get("candidates", [])
    for ev in candidates:
        payload = ev.get("payload", {})
        seat_class_id = payload.get("seat_class_id")
        qty = payload.get("quantity", 1)
        if seat_class_id:
            with SessionLocal() as session:
                res = release_seat_and_promote(
                    session,
                    seat_class_id=seat_class_id,
                    quantity=qty,
                    actor="system:langgraph:waitlist_promotion",
                )
                session.commit()
                if res.get("promoted"):
                    count += 1
    return {"promotions_count": count}

builder = StateGraph(WaitlistPromoState)
builder.add_node("find_freed_seats", find_freed_seats)
builder.add_node("promote_each", promote_each)
builder.add_edge(START, "find_freed_seats")
builder.add_edge("find_freed_seats", "promote_each")
builder.add_edge("promote_each", END)

waitlist_graph = builder.compile(checkpointer=checkpointer)
