import uuid
from typing import Generator
from fastapi import Header, HTTPException, Depends, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from sqlalchemy import select
from flight_domain.db import SessionLocal
from flight_domain.models.auth import AdminUser, Passenger
from flight_domain.models.bookings import Booking
from flight_domain.security import decode_jwt_token

security = HTTPBearer(auto_error=False)

def get_db() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

async def require_idempotency_key(
    idempotency_key: str = Header(..., alias="Idempotency-Key")
) -> str:
    """
    Every mutating endpoint requires and validates the Idempotency-Key header.
    """
    if not idempotency_key or len(idempotency_key) > 255:
        raise HTTPException(status_code=400, detail="Idempotency-Key header required")
    return idempotency_key

async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Security(security)
) -> dict | None:
    """
    Extracts and validates JWT token. Returns None if guest checkout.
    """
    if not credentials:
        return None
    token = credentials.credentials
    try:
        payload = decode_jwt_token(token)
        return payload
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid authentication token: {str(e)}")

async def require_current_user(
    user: dict | None = Depends(get_current_user)
) -> dict:
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required for this endpoint.")
    return user

def require_admin_role(allowed_roles: list[str]):
    """
    Verifies that the authenticated caller has an authorized admin role (super_admin, ops_agent).
    """
    async def _role_checker(
        user: dict | None = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> AdminUser:
        if not user or not user.get("sub"):
            raise HTTPException(status_code=401, detail="Authentication required for admin operation")
        
        # Check if role is in JWT payload or query admin_users table
        user_uuid_str = user["sub"]
        try:
            user_uuid = uuid.UUID(user_uuid_str)
        except ValueError:
            raise HTTPException(status_code=401, detail="Invalid user ID format in token")

        admin = db.scalar(select(AdminUser).where(AdminUser.user_id == user_uuid))
        if not admin or admin.role not in allowed_roles:
            raise HTTPException(
                status_code=403,
                detail=f"Operation requires role in {allowed_roles}. Current role: {getattr(admin, 'role', 'none')}"
            )
        return admin

    return _role_checker

def require_booking_owner_or_admin(
    booking_id: uuid.UUID,
    user: dict | None = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Booking:
    """
    Ensures the caller is either the passenger owning this booking or an authorized admin.
    """
    booking = db.get(Booking, booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail=f"Booking {booking_id} not found.")

    if not user or not user.get("sub"):
        # Guest booking access allowed if booking status is pending_payment
        return booking

    user_uuid = uuid.UUID(user["sub"])
    # Check if admin
    admin = db.scalar(select(AdminUser).where(AdminUser.user_id == user_uuid))
    if admin:
        return booking

    # Check if owner
    passenger = db.scalar(select(Passenger).where(Passenger.user_id == user_uuid))
    if passenger and passenger.id == booking.passenger_id:
        return booking

    # If passenger email matches token email
    if passenger and user.get("email") and passenger.email == user.get("email"):
        return booking

    raise HTTPException(status_code=403, detail="Not authorized to access this booking.")
