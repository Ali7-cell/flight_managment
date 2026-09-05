import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select
from apps.api.dependencies import get_db, require_idempotency_key, require_admin_role
from apps.api.schemas.admin import (
    FlightCreateRequest,
    FlightPatchRequest,
    SeatClassResizeRequest,
    AuditLogEntry,
)
from flight_domain.domain.admin import create_flight, cancel_flight, apply_schedule_change
from flight_domain.domain.seats import resize_seat_class
from flight_domain.models.plumbing import AuditLog
from flight_domain.models.flights import SeatClass

router = APIRouter(prefix="/admin", tags=["Admin"])

@router.post("/flights")
def admin_create_flight(
    req: FlightCreateRequest,
    idempotency_key: str = Depends(require_idempotency_key),
    admin=Depends(require_admin_role(["super_admin", "ops_agent"])),
    db: Session = Depends(get_db),
):
    try:
        flight_data = create_flight(
            db,
            flight_number=req.flight_number,
            origin=req.origin,
            destination=req.destination,
            origin_tz=req.origin_tz,
            destination_tz=req.destination_tz,
            departure_local=req.departure_local,
            arrival_local=req.arrival_local,
            seat_allocation=req.seat_allocation,
            actor=f"human:{admin.role}:{admin.id}",
        )
        return flight_data
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.patch("/flights/{flight_id}")
def admin_patch_flight(
    flight_id: uuid.UUID,
    req: FlightPatchRequest,
    idempotency_key: str = Depends(require_idempotency_key),
    admin=Depends(require_admin_role(["super_admin", "ops_agent"])),
    db: Session = Depends(get_db),
):
    try:
        return apply_schedule_change(
            db,
            flight_id=flight_id,
            new_departure_local=req.departure_local,
            new_arrival_local=req.arrival_local,
            actor=f"human:{admin.role}:{admin.id}",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/flights/{flight_id}/cancel")
def admin_cancel_flight(
    flight_id: uuid.UUID,
    idempotency_key: str = Depends(require_idempotency_key),
    admin=Depends(require_admin_role(["super_admin"])),
    db: Session = Depends(get_db),
):
    try:
        return cancel_flight(
            db,
            flight_id=flight_id,
            actor=f"human:{admin.role}:{admin.id}",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.patch("/flights/{flight_id}/seat-classes")
def admin_resize_seat_class(
    flight_id: uuid.UUID,
    req: SeatClassResizeRequest,
    idempotency_key: str = Depends(require_idempotency_key),
    admin=Depends(require_admin_role(["super_admin"])),
    db: Session = Depends(get_db),
):
    # Find matching seat class for this flight
    sc = db.scalar(
        select(SeatClass).where(
            SeatClass.flight_id == flight_id,
            SeatClass.class_name == req.class_name,
        )
    )
    if not sc:
        raise HTTPException(status_code=404, detail=f"Seat class '{req.class_name}' not found for flight {flight_id}")

    try:
        return resize_seat_class(
            db,
            seat_class_id=sc.id,
            new_total_seats=req.new_total_seats,
            actor=f"human:{admin.role}:{admin.id}",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/flights/{flight_id}/audit-log", response_model=list[AuditLogEntry])
def admin_get_audit_log(
    flight_id: uuid.UUID,
    admin=Depends(require_admin_role(["super_admin", "ops_agent"])),
    db: Session = Depends(get_db),
):
    logs = db.scalars(
        select(AuditLog)
        .where(AuditLog.entity_id == flight_id)
        .order_by(AuditLog.created_at.desc())
    ).all()

    return [
        AuditLogEntry(
            id=log.id,
            actor_type=log.actor_type,
            actor_id=log.actor_id,
            action=log.action,
            before=log.before_json,
            after=log.after_json,
            created_at=log.created_at,
        )
        for log in logs
    ]
