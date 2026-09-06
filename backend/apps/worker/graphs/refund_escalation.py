from datetime import timedelta
from typing import TypedDict, Any
from langgraph.graph import StateGraph, START, END
from sqlalchemy import select
from flight_domain.db import SessionLocal
from flight_domain.models.bookings import Refund
from flight_domain.models.base import utcnow
from flight_domain.clients.gmail import gmail_client

try:
    from apps.worker.checkpointer import checkpointer
except ImportError:
    from checkpointer import checkpointer  # type: ignore

class RefundEscalationState(TypedDict):
    days_threshold: int
    escalated_count: int

def find_and_escalate_stuck_refunds(state: RefundEscalationState) -> dict:
    days = state.get("days_threshold", 3)
    cutoff = utcnow() - timedelta(days=days)
    count = 0

    with SessionLocal() as session:
        stuck_refunds = session.scalars(
            select(Refund)
            .where(
                Refund.status == "pending",
                Refund.created_at <= cutoff,
            )
        ).all()

        for r in stuck_refunds:
            gmail_client.send(
                to="ops-escalations@yourdomain.com",
                subject=f"[ESCALATION] Stuck Refund {r.id} Pending > {days} days",
                body=f"Refund ID {r.id} for Booking ID {r.booking_id} has been pending since {r.created_at}. Amount: ${r.amount}.",
                metadata={"refund_id": str(r.id), "booking_id": str(r.booking_id)},
            )
            count += 1

    return {"escalated_count": count}

builder = StateGraph(RefundEscalationState)
builder.add_node("escalate", find_and_escalate_stuck_refunds)
builder.add_edge(START, "escalate")
builder.add_edge("escalate", END)

refund_escalation_graph = builder.compile(checkpointer=checkpointer)
