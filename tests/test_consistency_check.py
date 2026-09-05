from decimal import Decimal
from apps.worker.services.grounding import (
    DraftClaims,
    diff_claims_against_ground_truth,
)
from apps.worker.graphs.policy_rag import consistency_check, PolicyRunState

def test_consistency_check_catches_wrong_refundability():
    """
    Contract test for policy-RAG grounding:
    Given a known NON-REFUNDABLE economy ticket,
    When a stubbed LLM response erroneously claims the ticket is fully refundable,
    Then consistency_check must flag the factual contradiction.
    """
    # Ground truth: Economy ticket is NOT refundable, has $150 change fee
    ground_truth = {
        "booking_id": "test-booking-123",
        "fare_class": "economy",
        "refundable": False,
        "change_allowed": False,
        "change_fee_amount": 150.0,
        "cancellation_window_hrs": 24,
    }

    # Deliberately wrong LLM claim: says it is refundable!
    hallucinated_claims = DraftClaims(
        answer_text="Good news! Your ticket is fully refundable up to 2 hours before flight.",
        cited_refundable=True,
        cited_change_fee_amount=0.0,
        cited_cancellation_window_hrs=2,
    )

    # Run deterministic diff
    flags = diff_claims_against_ground_truth(hallucinated_claims, ground_truth)

    assert len(flags) >= 2
    assert any("refundable=True" in f for f in flags)
    assert any("change fee" in f for f in flags)

def test_consistency_check_node_in_graph_state():
    """
    Test the actual LangGraph node `consistency_check` on state dictionary.
    """
    state: PolicyRunState = {
        "run_id": "run-test-456",
        "booking_id": "b-123",
        "customer_question": "Can I cancel and get my money back?",
        "booking_context": {
            "fare_class": "economy",
            "refundable": False,
            "change_fee_amount": 150.0,
            "cancellation_window_hrs": 24,
        },
        "retrieved_passages": [],
        "draft_answer": "Yes, cancel anytime for a full refund.",
        "_structured_claims": DraftClaims(
            answer_text="Yes, cancel anytime for a full refund.",
            cited_refundable=True,  # Contrasts with False
        ),
        "consistency_flags": [],
        "final_answer": None,
        "decision": None,
    }

    update = consistency_check(state)
    assert "consistency_flags" in update
    assert len(update["consistency_flags"]) > 0
    assert "refundable=True" in update["consistency_flags"][0]

def test_consistency_check_passes_grounded_answer():
    """
    When the claims strictly match ground truth, consistency_flags must be empty.
    """
    ground_truth = {
        "fare_class": "first",
        "refundable": True,
        "change_fee_amount": 0.0,
        "cancellation_window_hrs": 72,
    }

    accurate_claims = DraftClaims(
        answer_text="Your first-class ticket is 100% refundable with $0 change fees.",
        cited_refundable=True,
        cited_change_fee_amount=0.0,
        cited_cancellation_window_hrs=72,
    )

    flags = diff_claims_against_ground_truth(accurate_claims, ground_truth)
    assert flags == []
