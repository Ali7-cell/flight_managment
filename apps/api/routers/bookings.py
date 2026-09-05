import uuid
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select
from apps.api.dependencies import get_db, require_idempotency_key, get_current_user
from apps.api.schemas.booking import (
    SeatHoldRequest,
    SeatHoldResponse,
    GroupHoldRequest,
    BookingConfirmRequest,
    BookingResponse,
    BookingCancelRequest,
    BookingCancelResponse,
    RefundResponse,
)
from flight_domain.domain.seats import hold_seats, group_hold_seats
from flight_domain.domain.bookings import confirm_booking, cancel_booking, get_booking
from flight_domain.models.bookings import Refund, Booking

router = APIRouter(tags=["Bookings"])

@router.post("/bookings/hold", response_model=SeatHoldResponse)
def api_hold_seats(
    req: SeatHoldRequest,
    idempotency_key: str = Depends(require_idempotency_key),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        actor = f"customer:{user['sub']}" if user and "sub" in user else "guest"
        hold_data = hold_seats(
            db,
            flight_id=req.flight_id,
            seat_class_id=req.seat_class_id,
            quantity=req.quantity,
            passenger_email=req.passenger_email,
            passenger_name=req.passenger_name,
            idempotency_key=idempotency_key,
            actor=actor,
        )
        return hold_data
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/bookings/group-hold", response_model=SeatHoldResponse)
def api_group_hold_seats(
    req: GroupHoldRequest,
    idempotency_key: str = Depends(require_idempotency_key),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        actor = f"customer:{user['sub']}" if user and "sub" in user else "guest"
        hold_data = group_hold_seats(
            db,
            flight_id=req.flight_id,
            seat_class_id=req.seat_class_id,
            quantity=req.quantity,
            passenger_email=req.passenger_email,
            passenger_name=req.passenger_name,
            idempotency_key=idempotency_key,
            actor=actor,
        )
        return hold_data
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/bookings/{hold_id}/confirm", response_model=BookingResponse)
def api_confirm_booking(
    hold_id: uuid.UUID,
    req: BookingConfirmRequest,
    idempotency_key: str = Depends(require_idempotency_key),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        actor = f"customer:{user['sub']}" if user and "sub" in user else "guest"
        booking_data = confirm_booking(
            db,
            hold_id=hold_id,
            payment_method_id=req.payment_method_id,
            idempotency_key=idempotency_key,
            actor=actor,
        )
        return booking_data
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/bookings/{booking_id}", response_model=BookingResponse)
def api_get_booking(
    booking_id: uuid.UUID,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    booking_data = get_booking(db, booking_id=booking_id)
    if not booking_data:
        raise HTTPException(status_code=404, detail="Booking not found")
    return booking_data

@router.post("/bookings/{booking_id}/cancel", response_model=BookingCancelResponse)
def api_cancel_booking(
    booking_id: uuid.UUID,
    req: BookingCancelRequest,
    idempotency_key: str = Depends(require_idempotency_key),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        actor = f"customer:{user['sub']}" if user and "sub" in user else "customer"
        return cancel_booking(
            db,
            booking_id=booking_id,
            reason=req.reason,
            actor=actor,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/bookings/{booking_id}/refund", response_model=RefundResponse)
def api_request_refund(
    booking_id: uuid.UUID,
    idempotency_key: str = Depends(require_idempotency_key),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    booking = db.get(Booking, booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    refund = Refund(
        booking_id=booking_id,
        amount=booking.total_amount,
        reason="Manual customer refund request",
        status="pending",
    )
    db.add(refund)
    db.flush()

    return RefundResponse(
        refund_id=refund.id,
        booking_id=booking.id,
        amount=refund.amount,
        status=refund.status,
        reason=refund.reason,
        created_at=refund.created_at,
    )

@router.get("/refunds/{refund_id}", response_model=RefundResponse)
def api_get_refund(
    refund_id: uuid.UUID,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    refund = db.get(Refund, refund_id)
    if not refund:
        raise HTTPException(status_code=404, detail="Refund not found")

    return RefundResponse(
        refund_id=refund.id,
        booking_id=refund.booking_id,
        amount=refund.amount,
        status=refund.status,
        reason=refund.reason,
        created_at=refund.created_at,
    )
