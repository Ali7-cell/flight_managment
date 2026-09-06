import sys
from pathlib import Path

_root = str(Path(__file__).resolve().parents[2])
if _root not in sys.path:
    sys.path.insert(0, _root)

try:
    from apps.worker.graphs.policy_rag import policy_graph
    from apps.worker.graphs.waitlist_promotion import waitlist_graph
    from apps.worker.graphs.checkin_reminders import checkin_reminder_graph
    from apps.worker.graphs.fraud_scan import fraud_scan_graph
    from apps.worker.graphs.fraud_batch_review import fraud_batch_review_graph
    from apps.worker.graphs.pinecone_ingest import pinecone_ingest_graph
    from apps.worker.graphs.refund_escalation import refund_escalation_graph
    from apps.worker.graphs.price_drop_alerts import price_drop_alerts_graph
    from apps.worker.graphs.ops_report import ops_report_graph
    from apps.worker.graphs.reconciliation import reconciliation_graph
    from apps.worker.graphs.live_chat import live_chat_graph
except ImportError:
    from graphs.policy_rag import policy_graph  # type: ignore
    from graphs.waitlist_promotion import waitlist_graph  # type: ignore
    from graphs.checkin_reminders import checkin_reminder_graph  # type: ignore
    from graphs.fraud_scan import fraud_scan_graph  # type: ignore
    from graphs.fraud_batch_review import fraud_batch_review_graph  # type: ignore
    from graphs.pinecone_ingest import pinecone_ingest_graph  # type: ignore
    from graphs.refund_escalation import refund_escalation_graph  # type: ignore
    from graphs.price_drop_alerts import price_drop_alerts_graph  # type: ignore
    from graphs.ops_report import ops_report_graph  # type: ignore
    from graphs.reconciliation import reconciliation_graph  # type: ignore
    from graphs.live_chat import live_chat_graph  # type: ignore

__all__ = [
    "policy_graph",
    "waitlist_graph",
    "checkin_reminder_graph",
    "fraud_scan_graph",
    "fraud_batch_review_graph",
    "pinecone_ingest_graph",
    "refund_escalation_graph",
    "price_drop_alerts_graph",
    "ops_report_graph",
    "reconciliation_graph",
    "live_chat_graph",
]
