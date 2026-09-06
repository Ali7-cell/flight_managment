from sqlalchemy import Column, String, BigInteger, Integer, Boolean, DateTime
from flight_domain.models.base import Base, utcnow, GUID, PG_JSONB

# Use Integer for SQLite compatibility (SQLite requires INTEGER PRIMARY KEY for autoincrement)
PK_BIGINT = BigInteger().with_variant(Integer, "sqlite")

class IdempotencyKey(Base):
    __tablename__ = "idempotency_keys"

    key = Column(String, primary_key=True)
    endpoint = Column(String, nullable=False)
    request_hash = Column(String, nullable=False)
    response_snapshot_json = Column(PG_JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)

class DomainEvent(Base):
    __tablename__ = "domain_events"

    id = Column(PK_BIGINT, primary_key=True, autoincrement=True)
    event_type = Column(String, nullable=False)
    payload_json = Column(PG_JSONB, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    processed = Column(Boolean, nullable=False, default=False)
    processed_at = Column(DateTime(timezone=True), nullable=True)

class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(PK_BIGINT, primary_key=True, autoincrement=True)
    actor_type = Column(String, nullable=False)
    actor_id = Column(String, nullable=True)
    action = Column(String, nullable=False)
    entity_type = Column(String, nullable=False)
    entity_id = Column(GUID, nullable=True)
    before_json = Column(PG_JSONB, nullable=True)
    after_json = Column(PG_JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
