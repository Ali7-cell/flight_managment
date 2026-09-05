from datetime import datetime, timezone
from fastapi import FastAPI
from flight_domain.db import SessionLocal

try:
    from apps.worker.graphs import (
        waitlist_graph,
        checkin_reminder_graph,
        fraud_scan_graph,
        pinecone_ingest_graph,
        refund_escalation_graph,
    )
    from apps.worker.services.ops_reporter import generate_ops_report
except ImportError:
    from graphs import (  # type: ignore
        waitlist_graph,
        checkin_reminder_graph,
        fraud_scan_graph,
        pinecone_ingest_graph,
        refund_escalation_graph,
    )
    from services.ops_reporter import generate_ops_report  # type: ignore

app = FastAPI(
    title="Flight Management System Worker",
    version="1.0.0",
    docs_url=None,  # internal only, not in public OpenAPI schema
    redoc_url=None,
)

def run_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")

@app.post("/trigger/waitlist-promotion")
def trigger_waitlist_promotion():
    thread_id = f"wl-promo-{run_timestamp()}"
    result = waitlist_graph.invoke(
        {"candidates": [], "promotions_count": 0},
        config={"configurable": {"thread_id": thread_id}},
    )
    return {"status": "success", "thread_id": thread_id, "result": result}

@app.post("/trigger/checkin-reminders")
def trigger_checkin_reminders():
    thread_id = f"checkin-{run_timestamp()}"
    result = checkin_reminder_graph.invoke(
        {"flights": [], "sent_count": 0},
        config={"configurable": {"thread_id": thread_id}},
    )
    return {"status": "success", "thread_id": thread_id, "result": result}

@app.post("/trigger/price-drop-alerts")
def trigger_price_drop_alerts():
    # Debounce threshold + per-passenger cooldown stub
    return {"status": "success", "alerts_sent": 0}

@app.post("/trigger/ops-report")
def trigger_ops_report():
    with SessionLocal() as session:
        report = generate_ops_report(session)
    return {"status": "success", "report": report}

@app.post("/trigger/fraud-scan")
def trigger_fraud_scan():
    thread_id = f"fraud-{run_timestamp()}"
    result = fraud_scan_graph.invoke(
        {"scanned_count": 0, "flagged_count": 0},
        config={"configurable": {"thread_id": thread_id}},
    )
    return {"status": "success", "thread_id": thread_id, "result": result}

@app.post("/trigger/pinecone-ingest")
def trigger_pinecone_ingest():
    thread_id = f"ingest-{run_timestamp()}"
    result = pinecone_ingest_graph.invoke(
        {"docs": [], "chunks_ingested": 0},
        config={"configurable": {"thread_id": thread_id}},
    )
    return {"status": "success", "thread_id": thread_id, "result": result}

@app.post("/trigger/refund-escalation")
def trigger_refund_escalation():
    thread_id = f"refund-esc-{run_timestamp()}"
    result = refund_escalation_graph.invoke(
        {"days_threshold": 3, "escalated_count": 0},
        config={"configurable": {"thread_id": thread_id}},
    )
    return {"status": "success", "thread_id": thread_id, "result": result}

@app.get("/healthz")
def healthz():
    return {"status": "ok", "service": "apps/worker"}
