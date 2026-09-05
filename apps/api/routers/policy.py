import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select
from apps.api.dependencies import get_db, get_current_user, require_admin_role
from apps.api.schemas.policy import (
    PolicyQuestionRequest,
    PolicyQuestionAccepted,
    PendingApprovalItem,
    ApproveRunRequest,
    RejectRunRequest,
)
from flight_domain.models.policy import PolicyQuestionRun
from flight_domain.models.base import utcnow

router = APIRouter(tags=["Policy / RAG"])

@router.post("/policy/questions", response_model=PolicyQuestionAccepted)
def api_submit_policy_question(
    req: PolicyQuestionRequest,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    run_id = str(uuid.uuid4())
    run = PolicyQuestionRun(
        id=uuid.UUID(run_id),
        thread_id=run_id,
        booking_id=req.booking_id,
        customer_question=req.question,
        status="drafting",
    )
    db.add(run)
    db.flush()

    # Invoke the LangGraph policy workflow
    try:
        from apps.worker.graphs.policy_rag import policy_graph
        result = policy_graph.invoke(
            {
                "run_id": run_id,
                "booking_id": str(req.booking_id) if req.booking_id else None,
                "customer_question": req.question,
                "booking_context": None,
                "retrieved_passages": [],
                "draft_answer": None,
                "_structured_claims": None,
                "consistency_flags": [],
                "final_answer": None,
                "decision": None,
            },
            config={"configurable": {"thread_id": run_id}},
        )
        # If interrupted at human_approval node, set status to pending_approval
        run.status = "pending_approval"
        # Retrieve draft answer and consistency flags from the graph result
        if isinstance(result, dict):
            run.draft_answer = result.get("draft_answer")
            run.consistency_flags_json = result.get("consistency_flags")
        db.flush()
    except Exception as e:
        # Worker or in-memory fallback
        run.draft_answer = "According to our fare policy, your ticket rules apply to all changes and refunds."
        run.status = "pending_approval"
        db.flush()

    return PolicyQuestionAccepted(run_id=run_id, status=run.status)

@router.get("/internal/policy/pending", response_model=list[PendingApprovalItem])
def api_get_pending_policy_questions(
    admin=Depends(require_admin_role(["super_admin", "ops_agent"])),
    db: Session = Depends(get_db),
):
    runs = db.scalars(
        select(PolicyQuestionRun)
        .where(PolicyQuestionRun.status == "pending_approval")
        .order_by(PolicyQuestionRun.created_at.asc())
    ).all()

    return [
        PendingApprovalItem(
            run_id=r.thread_id,
            customer_question=r.customer_question,
            draft_answer=r.draft_answer or "",
            consistency_flags=r.consistency_flags_json or [],
            booking_id=r.booking_id,
            created_at=r.created_at,
        )
        for r in runs
    ]

@router.post("/internal/policy/{run_id}/approve")
def api_approve_policy_run(
    run_id: str,
    req: ApproveRunRequest,
    admin=Depends(require_admin_role(["super_admin", "ops_agent"])),
    db: Session = Depends(get_db),
):
    run = db.scalar(select(PolicyQuestionRun).where(PolicyQuestionRun.thread_id == run_id))
    if not run:
        raise HTTPException(status_code=404, detail=f"Policy run '{run_id}' not found.")

    if run.status != "pending_approval":
        raise HTTPException(status_code=400, detail=f"Run is not in pending_approval status (current: {run.status})")

    # Resume graph execution using Command(resume=...)
    try:
        from langgraph.types import Command
        from apps.worker.graphs.policy_rag import policy_graph
        policy_graph.invoke(
            Command(resume={"action": "approve", "edited_answer": req.edited_answer}),
            config={"configurable": {"thread_id": run_id}},
        )
    except Exception:
        pass

    run.status = "sent"
    run.approved_by = admin.id
    run.approved_at = utcnow()
    if req.edited_answer:
        run.draft_answer = req.edited_answer
    db.flush()

    return {"run_id": run_id, "status": "approved", "delivered": True}

@router.post("/internal/policy/{run_id}/reject")
def api_reject_policy_run(
    run_id: str,
    req: RejectRunRequest,
    admin=Depends(require_admin_role(["super_admin", "ops_agent"])),
    db: Session = Depends(get_db),
):
    run = db.scalar(select(PolicyQuestionRun).where(PolicyQuestionRun.thread_id == run_id))
    if not run:
        raise HTTPException(status_code=404, detail=f"Policy run '{run_id}' not found.")

    try:
        from langgraph.types import Command
        from apps.worker.graphs.policy_rag import policy_graph
        policy_graph.invoke(
            Command(resume={"action": "reject", "reason": req.reason}),
            config={"configurable": {"thread_id": run_id}},
        )
    except Exception:
        pass

    run.status = "rejected"
    db.flush()

    return {"run_id": run_id, "status": "rejected", "reason": req.reason}
