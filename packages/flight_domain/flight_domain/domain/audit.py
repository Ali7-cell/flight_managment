import uuid
from typing import Any
from sqlalchemy.orm import Session
from flight_domain.models.plumbing import AuditLog

def record_audit_log(
    session: Session,
    *,
    actor_type: str,
    actor_id: str | None,
    action: str,
    entity_type: str,
    entity_id: uuid.UUID | str | None,
    before_json: dict[str, Any] | None = None,
    after_json: dict[str, Any] | None = None,
) -> AuditLog:
    """
    Append-only business audit trail.
    actor_type: 'system:fastapi' | 'system:langgraph:<graph_name>' | 'human:<admin_user_id>'
    """
    if isinstance(entity_id, str):
        try:
            entity_id = uuid.UUID(entity_id)
        except ValueError:
            entity_id = None

    log_entry = AuditLog(
        actor_type=actor_type,
        actor_id=str(actor_id) if actor_id else None,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        before_json=before_json,
        after_json=after_json,
    )
    session.add(log_entry)
    return log_entry
