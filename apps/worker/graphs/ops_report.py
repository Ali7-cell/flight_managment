from typing import TypedDict, Any
from langgraph.graph import StateGraph, START, END
from flight_domain.db import SessionLocal
from flight_domain.clients.gmail import gmail_client

try:
    from apps.worker.services.ops_reporter import generate_ops_report
    from apps.worker.checkpointer import checkpointer
except ImportError:
    from services.ops_reporter import generate_ops_report  # type: ignore
    from checkpointer import checkpointer  # type: ignore

class OpsReportState(TypedDict):
    report: dict[str, Any]
    delivered: bool

def compile_and_dispatch_report(state: OpsReportState) -> dict:
    with SessionLocal() as session:
        report_data = generate_ops_report(session)

    flights = report_data.get("flights", [])
    overall_load = report_data.get("overall_load_factor", 0.0)
    total_rev = report_data.get("total_revenue", 0.0)

    summary_text = (
        f"AeroFlow Airline Operations Daily/Weekly Report\n\n"
        f"Overall Load Factor: {overall_load:.1%}\n"
        f"Total Confirmed Revenue: ${total_rev:,.2f}\n"
        f"Active Flights Monitored: {len(flights)}\n\n"
        f"Top Flight Highlights:\n"
    )
    for f in flights[:5]:
        summary_text += (
            f" - Flight {f.get('flight_number')}: Load Factor {f.get('load_factor', 0):.1%}, "
            f"Revenue: ${f.get('revenue', 0):,.2f}, Booked: {f.get('booked_seats')}/{f.get('total_seats')}\n"
        )

    gmail_client.send(
        to="ops-management@yourdomain.com",
        subject=f"Daily Operations Report - System Load Factor {overall_load:.1%}",
        body=summary_text,
        metadata={"overall_load_factor": overall_load, "total_revenue": total_rev},
    )

    return {"report": report_data, "delivered": True}

builder = StateGraph(OpsReportState)
builder.add_node("compile_and_dispatch_report", compile_and_dispatch_report)
builder.add_edge(START, "compile_and_dispatch_report")
builder.add_edge("compile_and_dispatch_report", END)

ops_report_graph = builder.compile(checkpointer=checkpointer)
