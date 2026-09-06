import uuid
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select
from apps.api.dependencies import get_db, require_idempotency_key, get_current_user, require_booking_owner_or_admin
from apps.api.schemas.booking import (
    SeatHoldRequest,
    SeatHoldResponse,
    GroupHoldRequest,
    MultiLegHoldRequest,
    BookingConfirmRequest,
    BookingResponse,
    BookingCancelRequest,
    BookingCancelResponse,
    PartialCancelRequest,
    PartialCancelResponse,
    CancellationResolutionRequest,
    CompensationClaimRequest,
    RefundResponse,
)
from flight_domain.domain.seats import hold_seats, group_hold_seats, hold_multi_leg_seats
from flight_domain.domain.bookings import (
    confirm_booking,
    cancel_booking,
    cancel_partial_booking,
    resolve_cancelled_flight_booking,
    get_booking,
)
from flight_domain.domain.autonomy import submit_compensation_claim
from flight_domain.models.bookings import Refund, Booking
from flight_domain.models.auth import Passenger

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
            seat_number=req.seat_number,
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

@router.post("/bookings/multi-leg-hold")
def api_multi_leg_hold(
    req: MultiLegHoldRequest,
    idempotency_key: str = Depends(require_idempotency_key),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        actor = f"customer:{user['sub']}" if user and "sub" in user else "guest"
        legs_payload = [
            {
                "flight_id": leg.flight_id,
                "seat_class_id": leg.seat_class_id,
                "quantity": leg.quantity,
                "seat_number": leg.seat_number,
            }
            for leg in req.legs
        ]
        return hold_multi_leg_seats(
            db,
            legs=legs_payload,
            passenger_email=req.passenger_email,
            passenger_name=req.passenger_name,
            idempotency_key=idempotency_key,
            actor=actor,
        )
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
            fare_type=req.fare_type,
            idempotency_key=idempotency_key,
            actor=actor,
        )
        return booking_data
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/bookings/{booking_id}", response_model=BookingResponse)
def api_get_booking(
    booking_id: str,
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
    booking=Depends(require_booking_owner_or_admin),
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
            idempotency_key=idempotency_key,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/bookings/{booking_id}/cancel-partial", response_model=PartialCancelResponse)
def api_cancel_partial_booking(
    booking_id: uuid.UUID,
    req: PartialCancelRequest,
    idempotency_key: str = Depends(require_idempotency_key),
    booking=Depends(require_booking_owner_or_admin),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        actor = f"customer:{user['sub']}" if user and "sub" in user else "customer"
        return cancel_partial_booking(
            db,
            booking_id=booking_id,
            seats_to_cancel=req.seats_to_cancel,
            reason=req.reason,
            actor=actor,
            idempotency_key=idempotency_key,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/bookings/{booking_id}/resolution")
def api_resolve_flight_cancellation(
    booking_id: uuid.UUID,
    req: CancellationResolutionRequest,
    booking=Depends(require_booking_owner_or_admin),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        actor = f"customer:{user['sub']}" if user and "sub" in user else "customer"
        return resolve_cancelled_flight_booking(
            db,
            booking_id=booking_id,
            resolution_choice=req.resolution_choice,
            target_flight_id=req.target_flight_id,
            actor=actor,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/bookings/compensation/claim")
def api_submit_compensation(
    req: CompensationClaimRequest,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        if not user or not user.get("sub"):
            raise HTTPException(status_code=401, detail="Authentication required to submit compensation claim.")
        
        user_uuid = uuid.UUID(user["sub"])
        passenger = db.scalar(select(Passenger).where(Passenger.user_id == user_uuid))
        if not passenger:
            raise HTTPException(status_code=404, detail="Passenger record not found for authenticated user.")

        return submit_compensation_claim(
            db,
            flight_id=req.flight_id,
            passenger_id=passenger.id,
            claim_type=req.claim_type,
            requested_amount=req.requested_amount,
            booking_id=req.booking_id,
            reason=req.reason,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/bookings/{booking_id}/refund", response_model=RefundResponse)
def api_request_refund(
    booking_id: uuid.UUID,
    idempotency_key: str = Depends(require_idempotency_key),
    booking=Depends(require_booking_owner_or_admin),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
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
        booking_id=booking_id,
        amount=refund.amount,
        status=refund.status,
        reason=refund.reason,
        created_at=refund.created_at,
    )
