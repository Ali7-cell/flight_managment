import uuid
import jwt
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select
from apps.api.dependencies import get_db
from apps.api.schemas.auth import UserSignupRequest, UserLoginRequest, TokenResponse
from apps.api.config import api_settings
from flight_domain.models.auth import Passenger, AdminUser
from flight_domain.models.base import utcnow

router = APIRouter(prefix="/auth", tags=["Auth"])

def create_jwt_token(user_id: str, email: str, role: str | None = None) -> str:
    payload = {
        "sub": user_id,
        "email": email,
        "role": role,
        "iat": utcnow(),
        "exp": utcnow() + timedelta(days=7),
    }
    return jwt.encode(payload, api_settings.SUPABASE_JWT_SECRET, algorithm="HS256")

@router.post("/signup", response_model=TokenResponse)
def api_signup(req: UserSignupRequest, db: Session = Depends(get_db)):
    existing = db.scalar(select(Passenger).where(Passenger.email == req.email))
    user_id = str(uuid.uuid4())
    if existing:
        if existing.user_id:
            raise HTTPException(status_code=400, detail="Account with this email already exists.")
        existing.user_id = uuid.UUID(user_id)
        existing.full_name = req.full_name
    else:
        passenger = Passenger(
            id=uuid.uuid4(),
            user_id=uuid.UUID(user_id),
            email=req.email,
            full_name=req.full_name,
            loyalty_tier="none",
        )
        db.add(passenger)
    
    db.flush()
    token = create_jwt_token(user_id, req.email)
    return TokenResponse(access_token=token, user_id=user_id, role="customer")

@router.post("/login", response_model=TokenResponse)
def api_login(req: UserLoginRequest, db: Session = Depends(get_db)):
    passenger = db.scalar(select(Passenger).where(Passenger.email == req.email))
    if not passenger or not passenger.user_id:
        raise HTTPException(status_code=401, detail="Invalid credentials or user not registered.")

    # Check if this user is also an admin
    admin = db.scalar(select(AdminUser).where(AdminUser.user_id == passenger.user_id))
    role = admin.role if admin else "customer"

    token = create_jwt_token(str(passenger.user_id), req.email, role=role)
    return TokenResponse(access_token=token, user_id=str(passenger.user_id), role=role)
