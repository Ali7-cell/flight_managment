import sys
from pathlib import Path

_root = str(Path(__file__).resolve().parents[2])
if _root not in sys.path:
    sys.path.insert(0, _root)

try:
    from apps.worker.services.grounding import (
        DraftClaims,
        diff_claims_against_ground_truth,
        llm_structured_draft,
    )
    from apps.worker.services.fraud_detector import score_booking
    from apps.worker.services.ops_reporter import generate_ops_report
except ImportError:
    from services.grounding import (
        DraftClaims,
        diff_claims_against_ground_truth,
        llm_structured_draft,
    )
    from services.fraud_detector import score_booking
    from services.ops_reporter import generate_ops_report

__all__ = [
    "DraftClaims",
    "diff_claims_against_ground_truth",
    "llm_structured_draft",
    "score_booking",
    "generate_ops_report",
]
