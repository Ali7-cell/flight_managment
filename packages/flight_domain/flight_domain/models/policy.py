import uuid
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, CheckConstraint
from sqlalchemy.orm import relationship
from flight_domain.models.base import Base, utcnow, GUID, PG_JSONB

class PolicyDoc(Base):
    __tablename__ = "policy_docs"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    title = Column(String, nullable=False)
    source_url = Column(String, nullable=True)
    content_hash = Column(String, nullable=False)
    fare_type_scope = Column(String, nullable=True)
    category = Column(String, nullable=False, default="general")
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)

    chunks = relationship("PolicyDocChunk", back_populates="policy_doc", cascade="all, delete-orphan")

class PolicyDocChunk(Base):
    __tablename__ = "policy_doc_chunks"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    policy_doc_id = Column(GUID, ForeignKey("policy_docs.id", ondelete="CASCADE"), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    content = Column(String, nullable=False)
    pinecone_vector_id = Column(String, nullable=False, unique=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)

    policy_doc = relationship("PolicyDoc", back_populates="chunks")

class PolicyQuestionRun(Base):
    __tablename__ = "policy_question_runs"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    thread_id = Column(String, nullable=False, unique=True)
    booking_id = Column(GUID, ForeignKey("bookings.id"), nullable=True)
    customer_question = Column(String, nullable=False)
    draft_answer = Column(String, nullable=True)
    consistency_flags_json = Column(PG_JSONB, nullable=True)
    status = Column(String, nullable=False, default="drafting")
    approved_by = Column(GUID, ForeignKey("admin_users.id"), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)

    booking = relationship("Booking")
    admin = relationship("AdminUser")

    __table_args__ = (
        CheckConstraint("status in ('drafting','pending_approval','approved','rejected','sent')", name="chk_policy_run_status"),
    )
