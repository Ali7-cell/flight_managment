from pydantic import BaseModel
from typing import Any

class DraftClaims(BaseModel):
    answer_text: str
    cited_refundable: bool | None = None
    cited_change_fee_amount: float | None = None
    cited_cancellation_window_hrs: int | None = None
    cited_applicable_refund_pct: int | None = None

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

    # 2. Applicable refund percentage tier check
    if claims.cited_applicable_refund_pct is not None:
        gt_pct = ground_truth.get("applicable_refund_percentage")
        if gt_pct is not None and claims.cited_applicable_refund_pct != gt_pct:
            flags.append(
                f"draft's stated refund percentage ({claims.cited_applicable_refund_pct}%) doesn't match currently applicable tier ({gt_pct}%)"
            )

    # 3. Change fee check
    if claims.cited_change_fee_amount is not None:
        gt_fee = ground_truth.get("change_fee_amount")
        if gt_fee is not None and abs(claims.cited_change_fee_amount - float(gt_fee)) > 0.01:
            flags.append(
                f"draft's stated change fee (${claims.cited_change_fee_amount}) doesn't match fare_rules.change_fee_amount (${gt_fee})"
            )

    # 4. Cancellation window check
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
    Explicitly prioritizes the booking's authoritative Postgres facts over Pinecone chunks.
    """
    if ground_truth:
        fare_type = ground_truth.get("fare_type", "flex")
        cabin = ground_truth.get("cabin_class", "Economy")
        ref_pct = ground_truth.get("applicable_refund_percentage", 100)
        is_ref = ground_truth.get("refundable", ref_pct > 0)
        fee = ground_truth.get("change_fee_amount", 0.0)
        hours_to_dep = ground_truth.get("hours_to_departure")

        if fare_type == "basic_economy":
            answer = (
                f"Regarding your Basic Economy booking ({ground_truth.get('booking_reference')}): "
                f"This ticket is strictly non-refundable for cash under our cancellation policy. "
                f"Voluntary cancellations yield no refund and no travel credit. "
                f"However, if the flight is cancelled by the airline, you will receive 100% travel credit valid for 12 months."
            )
            return DraftClaims(
                answer_text=answer,
                cited_refundable=False,
                cited_applicable_refund_pct=0,
                cited_change_fee_amount=None,
                cited_cancellation_window_hrs=None,
            )
        else:
            time_str = f"with approximately {hours_to_dep}h before departure, " if hours_to_dep is not None else ""
            fee_str = "no change fee" if (fee is None or fee == 0) else f"a ${fee:.2f} fee"
            answer = (
                f"Regarding your Flex ({cabin}) booking ({ground_truth.get('booking_reference')}): "
                f"{time_str}your ticket is eligible for a {ref_pct}% cash refund. "
                f"You may also opt for 100% travel credit (valid for 12 months) instead of a partial cash refund. "
                f"Changes are permitted with {fee_str} up to 24 hours prior to departure."
            )
            return DraftClaims(
                answer_text=answer,
                cited_refundable=is_ref,
                cited_applicable_refund_pct=ref_pct,
                cited_change_fee_amount=float(fee) if fee is not None else None,
                cited_cancellation_window_hrs=24,
            )

    # General question without specific booking
    answer = (
        "Airline Policy Overview:\n"
        "- Flex Fares: Refundable based on cancellation timing (100% at 72h+, 75% at 24-72h, 50% under 24h, 0% no-show). Passenger may also choose 100% travel credit.\n"
        "- Basic Economy Fares: Strictly non-refundable for cash. Airline cancellations receive 100% travel credit only."
    )
    return DraftClaims(
        answer_text=answer,
        cited_refundable=None,
        cited_applicable_refund_pct=None,
        cited_change_fee_amount=None,
        cited_cancellation_window_hrs=None,
    )

