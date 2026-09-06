from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID

class PolicyQuestionRequest(BaseModel):
    booking_id: UUID | None = None
    question: str = Field(min_length=1, max_length=2000)

class PolicyQuestionAccepted(BaseModel):
    run_id: str          # == LangGraph thread_id
    status: str          # 'drafting' immediately after submit

class PendingApprovalItem(BaseModel):
    run_id: str
    customer_question: str
    draft_answer: str
    consistency_flags: list[str]
    booking_id: UUID | None
    created_at: datetime

class ApproveRunRequest(BaseModel):
    edited_answer: str | None = None

class RejectRunRequest(BaseModel):
    reason: str
