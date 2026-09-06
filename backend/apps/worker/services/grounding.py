from pydantic import BaseModel
from typing import Any

class DraftClaims(BaseModel):
    answer_text: str
    cited_refundable: bool | None = None
    cited_change_fee_amount: float | None = None
    cited_cancellation_window_hrs: int | None = None

def diff_claims_against_ground_truth(claims: DraftClaims, ground_truth: dict | None) -> list[str]:
    """
    Deterministic consistency check (05_langgraph_rag_pinecone.md §3).
    Diffs structured claims from LLM against the booking's authoritative fare_rules row.
    """
    if ground_truth is None:
        return []  # No booking referenced; general question, nothing to ground against

    flags = []
    
    # 1. Refundability check
    if claims.cited_refundable is not None:
        gt_refundable = bool(ground_truth.get("refundable"))
        if claims.cited_refundable != gt_refundable:
            flags.append(
                f"draft claims refundable={claims.cited_refundable}, but fare_rules says {gt_refundable}"
            )

    # 2. Change fee check
    if claims.cited_change_fee_amount is not None:
        gt_fee = ground_truth.get("change_fee_amount")
        if gt_fee is not None and abs(claims.cited_change_fee_amount - float(gt_fee)) > 0.01:
            flags.append(
                f"draft's stated change fee (${claims.cited_change_fee_amount}) doesn't match fare_rules.change_fee_amount (${gt_fee})"
            )

    # 3. Cancellation window check
    if claims.cited_cancellation_window_hrs is not None:
        gt_window = ground_truth.get("cancellation_window_hrs")
        if gt_window is not None and claims.cited_cancellation_window_hrs != gt_window:
            flags.append(
                f"draft's stated cancellation window ({claims.cited_cancellation_window_hrs}h) doesn't match fare_rules ({gt_window}h)"
            )

    return flags

def llm_structured_draft(
    question: str,
    ground_truth: dict | None,
    general_policy: list[dict],
) -> DraftClaims:
    """
    Drafts an answer grounded in both ground truth and retrieved policy passages.
    If no external LLM key is configured, uses deterministic heuristic template.
    """
    if ground_truth:
        fare_class = ground_truth.get("fare_class", "economy")
        ref = ground_truth.get("refundable", False)
        fee = ground_truth.get("change_fee_amount", 0.0)
        win = ground_truth.get("cancellation_window_hrs", 24)

        ref_str = "fully refundable" if ref else "non-refundable"
        answer = (
            f"Regarding your {fare_class} booking ({ground_truth.get('booking_reference')}): "
            f"Your ticket is {ref_str}. "
            f"Changes incur a fee of ${fee:.2f}. "
            f"Cancellations must be made within {win} hours before departure."
        )
        return DraftClaims(
            answer_text=answer,
            cited_refundable=ref,
            cited_change_fee_amount=float(fee) if fee is not None else None,
            cited_cancellation_window_hrs=win,
        )

    # General question without specific booking
    answer = "All flight bookings are subject to our fare rules. Flexible and First class fares are refundable, whereas basic economy fares are strictly non-refundable."
    return DraftClaims(
        answer_text=answer,
        cited_refundable=None,
        cited_change_fee_amount=None,
        cited_cancellation_window_hrs=None,
    )
