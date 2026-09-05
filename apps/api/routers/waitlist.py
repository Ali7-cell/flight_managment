import uuid
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import select
from apps.api.dependencies import get_db, require_idempotency_key, get_current_user
from apps.api.schemas.waitlist import (
    WaitlistJoinRequest,
    WaitlistJoinResponse,
    WaitlistPositionResponse,
)
from flight_domain.domain.waitlist import join_waitlist, get_waitlist_position
from flight_domain.models.bookings import WaitlistEntry
from flight_domain.models.auth import Passenger

router = APIRouter(prefix="/waitlist", tags=["Waitlist"])

@router.post("", response_model=WaitlistJoinResponse)
def api_join_waitlist(
    req: WaitlistJoinRequest,
    idempotency_key: str = Depends(require_idempotency_key),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        res = join_waitlist(
            db,
            flight_id=req.flight_id,
            seat_class_id=req.seat_class_id,
            quantity=req.quantity,
            passenger_email=req.passenger_email,
            passenger_name=req.passenger_name,
        )
        return res
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{flight_id}/position", response_model=WaitlistPositionResponse)
def api_get_waitlist_position(
    flight_id: uuid.UUID,
    waitlist_entry_id: uuid.UUID | None = Query(None),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # If specific entry id is given, look it up; otherwise look up by current user passenger
    entry = None
    if waitlist_entry_id:
        entry = db.get(WaitlistEntry, waitlist_entry_id)
    elif user and "sub" in user:
        passenger = db.scalar(select(Passenger).where(Passenger.user_id == uuid.UUID(user["sub"])))
        if passenger:
            entry = db.scalar(
                select(WaitlistEntry).where(
                    WaitlistEntry.flight_id == flight_id,
                    WaitlistEntry.passenger_id == passenger.id,
                    WaitlistEntry.status == "waiting",
                ).order_by(WaitlistEntry.created_at.desc())
            )

    if not entry:
        raise HTTPException(status_code=404, detail="Active waitlist entry not found for this flight.")

    try:
        return get_waitlist_position(db, waitlist_entry_id=entry.id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
