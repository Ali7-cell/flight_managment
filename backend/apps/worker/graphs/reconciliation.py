from typing import TypedDict, Any
from langgraph.graph import StateGraph, START, END
from flight_domain.db import SessionLocal
from flight_domain.domain.reconciliation import run_inventory_reconciliation

try:
    from apps.worker.checkpointer import checkpointer
except ImportError:
    from checkpointer import checkpointer  # type: ignore

class ReconciliationState(TypedDict):
    total_classes_checked: int
    discrepancies_count: int
    discrepancies: list[dict[str, Any]]
    status: str

def execute_reconciliation(state: ReconciliationState) -> dict:
    with SessionLocal() as session:
        result = run_inventory_reconciliation(session)
        session.commit()
    return result

builder = StateGraph(ReconciliationState)
builder.add_node("execute_reconciliation", execute_reconciliation)
builder.add_edge(START, "execute_reconciliation")
builder.add_edge("execute_reconciliation", END)

reconciliation_graph = builder.compile(checkpointer=checkpointer)
