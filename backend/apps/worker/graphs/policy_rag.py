from typing import TypedDict, Any
from langgraph.graph import StateGraph, START, END
from langgraph.types import interrupt, Command
from flight_domain.db import SessionLocal
from flight_domain.domain.policy import get_fare_rule_for_booking
from flight_domain.clients.pinecone import pinecone_client
from flight_domain.clients.gmail import gmail_client

try:
    from apps.worker.checkpointer import checkpointer
    from apps.worker.services.grounding import (
        diff_claims_against_ground_truth,
        llm_structured_draft,
        DraftClaims,
    )
except ImportError:
    from checkpointer import checkpointer  # type: ignore
    from services.grounding import (  # type: ignore
        diff_claims_against_ground_truth,
        llm_structured_draft,
        DraftClaims,
    )

class PolicyRunState(TypedDict):
    run_id: str
    booking_id: str | None
    customer_question: str
    booking_context: dict[str, Any] | None
    retrieved_passages: list[dict[str, Any]]
    draft_answer: str | None
    _structured_claims: Any
    consistency_flags: list[str]
    final_answer: str | None
    decision: str | None  # 'approve' | 'reject'

def fetch_booking_context(state: PolicyRunState) -> dict:
    booking_id = state.get("booking_id")
    if not booking_id:
        return {"booking_context": None}
    
    with SessionLocal() as session:
        ctx = get_fare_rule_for_booking(session, booking_id)
    return {"booking_context": ctx}

def retrieve_policy_passages(state: PolicyRunState) -> dict:
    fare_type = "all"
    ctx = state.get("booking_context")
    if isinstance(ctx, dict):
        fare_type = ctx.get("fare_class", "all")
    
    passages = pinecone_client.query_policy(
        query_text=state["customer_question"],
        fare_type_filter=fare_type,
    )
    return {"retrieved_passages": passages}

def draft_answer(state: PolicyRunState) -> dict:
    result = llm_structured_draft(
        question=state["customer_question"],
        ground_truth=state.get("booking_context"),
        general_policy=state.get("retrieved_passages", []),
    )
    return {
        "draft_answer": result.answer_text,
        "_structured_claims": result,
    }

def consistency_check(state: PolicyRunState) -> dict:
    claims = state.get("_structured_claims")
    if isinstance(claims, dict):
        claims = DraftClaims(**claims)
    elif claims is None:
        claims = DraftClaims(answer_text=state.get("draft_answer") or "")

    flags = diff_claims_against_ground_truth(claims, state.get("booking_context"))
    return {"consistency_flags": flags}

def route_after_check(state: PolicyRunState) -> str:
    draft = state.get("draft_answer") or ""
    if state.get("consistency_flags") and "REDRAFT_RETRY" in draft:
        return "redraft"
    return "approve"

def human_approval(state: PolicyRunState) -> dict:
    """
    Side-effect-free human approval gate using LangGraph interrupt().
    On resume, re-executes cleanly without duplicate actions.
    """
    decision = interrupt({
        "run_id": state["run_id"],
        "draft_answer": state.get("draft_answer"),
        "consistency_flags": state.get("consistency_flags", []),
    })
    action = decision.get("action", "approve") if isinstance(decision, dict) else "approve"
    edited = decision.get("edited_answer") if isinstance(decision, dict) else None
    return {
        "decision": action,
        "final_answer": edited or state.get("draft_answer"),
    }

def send_gmail(state: PolicyRunState) -> dict:
    recipient = "customer@example.com"
    gmail_client.send(
        to=recipient,
        subject=f"Regarding your flight policy question (Ref: {state.get('booking_id', 'General')})",
        body=state.get("final_answer") or "Your question has been reviewed by flight operations.",
        metadata={"run_id": state["run_id"]},
    )
    return {}

def record_rejection(state: PolicyRunState) -> dict:
    return {"final_answer": "Request rejected by supervisor."}

builder = StateGraph(PolicyRunState)
builder.add_node("fetch_booking_context", fetch_booking_context)
builder.add_node("retrieve_policy_passages", retrieve_policy_passages)
builder.add_node("draft_answer", draft_answer)
builder.add_node("consistency_check", consistency_check)
builder.add_node("human_approval", human_approval)
builder.add_node("send_gmail", send_gmail)
builder.add_node("record_rejection", record_rejection)

builder.add_edge(START, "fetch_booking_context")
builder.add_edge("fetch_booking_context", "retrieve_policy_passages")
builder.add_edge("retrieve_policy_passages", "draft_answer")
builder.add_edge("draft_answer", "consistency_check")
builder.add_conditional_edges(
    "consistency_check",
    route_after_check,
    {"redraft": "draft_answer", "approve": "human_approval"},
)
builder.add_conditional_edges(
    "human_approval",
    lambda s: s.get("decision", "approve"),
    {"approve": "send_gmail", "reject": "record_rejection"},
)
builder.add_edge("send_gmail", END)
builder.add_edge("record_rejection", END)

policy_graph = builder.compile(checkpointer=checkpointer)
