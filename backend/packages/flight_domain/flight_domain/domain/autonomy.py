import uuid
from decimal import Decimal
from typing import Any
from sqlalchemy.orm import Session
from sqlalchemy import select
from flight_domain.models.bookings import CompensationClaim, Booking
from flight_domain.models.flights import Flight
from flight_domain.models.auth import Passenger, AdminUser
from flight_domain.models.base import utcnow
from flight_domain.domain.audit import record_audit_log
from flight_domain.domain.outbox import emit_event

# Explicit Boundaries per Capstone PRD Domain 8
AUTO_APPROVED_ACTIONS = [
    "checkin_reminders",
    "price_drop_alerts",
    "standard_in_policy_refunds",
    "waitlist_promotions_within_priority",
    "booking_confirmation_notices",
]

HUMAN_SIGNOFF_REQUIRED_ACTIONS = [
    "schedule_change_compensation",
    "denied_boarding_compensation",
    "rag_drafted_policy_answers",
    "manual_credit_overrides",
    "flight_cancellation_decisions",
]

def submit_compensation_claim(
    session: Session,
    *,
    flight_id: uuid.UUID | str,
    passenger_id: uuid.UUID | str,
    claim_type: str,  # "schedule_change", "denied_boarding", "delay_compensation"
    requested_amount: Decimal | float,
    booking_id: uuid.UUID | str | None = None,
    reason: str | None = None,
    currency: str = "USD",
) -> dict[str, Any]:
    """
    Submits a compensation claim requiring supervisor sign-off per Domain 8.
    """
    if isinstance(flight_id, str):
        flight_id = uuid.UUID(flight_id)
    if isinstance(passenger_id, str):
        passenger_id = uuid.UUID(passenger_id)
    if isinstance(booking_id, str):
        booking_id = uuid.UUID(booking_id)

    if claim_type not in ("schedule_change", "denied_boarding", "delay_compensation"):
        raise ValueError(f"Invalid claim_type: {claim_type}. Allowed: schedule_change, denied_boarding, delay_compensation.")

    claim = CompensationClaim(
        flight_id=flight_id,
        passenger_id=passenger_id,
        booking_id=booking_id,
        claim_type=claim_type,
        requested_amount=Decimal(str(requested_amount)),
        currency=currency.upper(),
        status="pending_review",
        reason=reason,
    )
    session.add(claim)
    session.flush()

    record_audit_log(
        session,
        actor_type="passenger",
        actor_id=str(passenger_id),
        action="submit_compensation_claim",
        entity_type="compensation_claims",
        entity_id=claim.id,
        before_json=None,
        after_json={
            "claim_type": claim_type,
            "amount": str(claim.requested_amount),
            "status": "pending_review",
        },
    )

    emit_event(
        session,
        event_type="compensation_claim_submitted",
        payload_json={
            "claim_id": str(claim.id),
            "claim_type": claim_type,
            "flight_id": str(flight_id),
            "passenger_id": str(passenger_id),
            "requested_amount": str(claim.requested_amount),
        },
    )

    return {
        "claim_id": str(claim.id),
        "status": claim.status,
        "claim_type": claim.claim_type,
        "requested_amount": str(claim.requested_amount),
        "requires_human_signoff": True,
    }

def review_compensation_claim(
    session: Session,
    *,
    claim_id: uuid.UUID | str,
    action: str,  # "approve" | "reject"
    admin_user: AdminUser,
    notes: str | None = None,
) -> dict[str, Any]:
    """
    Human approval gate for compensation claims.
    Super-admin signoff required. Creates audit trail for regulatory compliance.
    """
    if isinstance(claim_id, str):
        claim_id = uuid.UUID(claim_id)

    claim = session.scalar(select(CompensationClaim).where(CompensationClaim.id == claim_id).with_for_update())
    if not claim:
        raise ValueError(f"Compensation claim {claim_id} not found.")

    if claim.status != "pending_review":
        raise ValueError(f"Claim is already {claim.status}.")

    new_status = "approved" if action.lower() == "approve" else "rejected"
    claim.status = new_status
    claim.reviewed_by = admin_user.id
    claim.reviewed_at = utcnow()

    record_audit_log(
        session,
        actor_type=f"human:{admin_user.role}:{admin_user.id}",
        actor_id=str(admin_user.id),
        action="review_compensation_claim",
        entity_type="compensation_claims",
        entity_id=claim.id,
        before_json={"status": "pending_review"},
        after_json={
            "status": new_status,
            "reviewed_by": str(admin_user.id),
            "notes": notes,
        },
    )

    emit_event(
        session,
        event_type=f"compensation_claim_{new_status}",
        payload_json={
            "claim_id": str(claim.id),
            "status": new_status,
            "passenger_id": str(claim.passenger_id),
            "amount": str(claim.requested_amount),
        },
    )

    session.flush()
    return {
        "claim_id": str(claim.id),
        "status": claim.status,
        "reviewed_by": str(admin_user.id),
        "reviewed_at": claim.reviewed_at.isoformat(),
    }

def list_pending_compensation_claims(session: Session) -> list[dict[str, Any]]:
    claims = session.scalars(
        select(CompensationClaim)
        .where(CompensationClaim.status == "pending_review")
        .order_by(CompensationClaim.created_at.asc())
    ).all()

    results = []
    for c in claims:
        flight = session.get(Flight, c.flight_id)
        passenger = session.get(Passenger, c.passenger_id)
        results.append({
            "claim_id": str(c.id),
            "flight_id": str(c.flight_id),
            "flight_number": flight.flight_number if flight else "Unknown",
            "passenger_id": str(c.passenger_id),
            "passenger_name": passenger.full_name if passenger else "Unknown",
            "passenger_email": passenger.email if passenger else "Unknown",
            "claim_type": c.claim_type,
            "requested_amount": str(c.requested_amount),
            "currency": c.currency,
            "reason": c.reason,
            "created_at": c.created_at.isoformat(),
        })
    return results
