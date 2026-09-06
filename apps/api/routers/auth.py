import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select
from apps.api.dependencies import get_db, get_current_user
from apps.api.schemas.auth import UserSignupRequest, UserLoginRequest, TokenResponse
from flight_domain.models.auth import Passenger, AdminUser
from flight_domain.security import hash_password, verify_password, create_jwt_token

router = APIRouter(prefix="/auth", tags=["Auth"])

def seed_default_users(db: Session):
    """Seed default accounts if they don't exist for seamless development & demonstration."""
    # 1. Super Admin
    super_admin_email = "superadmin@aeroflow.com"
    super_pass = db.scalar(select(Passenger).where(Passenger.email == super_admin_email))
    if not super_pass:
        super_uid = uuid.UUID("11111111-1111-4111-8111-111111111111")
        super_pass = Passenger(
            id=super_uid,
            user_id=super_uid,
            email=super_admin_email,
            full_name="Lead Super Administrator",
            password_hash=hash_password("admin123"),
            loyalty_tier="platinum",
        )
        db.add(super_pass)
        db.flush()

        admin_rec = AdminUser(
            id=uuid.uuid4(),
            user_id=super_uid,
            email=super_admin_email,
            full_name="Lead Super Administrator",
            password_hash=hash_password("admin123"),
            role="super_admin",
        )
        db.add(admin_rec)

    # 2. Ops Agent
    ops_email = "ops@aeroflow.com"
    ops_pass = db.scalar(select(Passenger).where(Passenger.email == ops_email))
    if not ops_pass:
        ops_uid = uuid.UUID("22222222-2222-4222-8222-222222222222")
        ops_pass = Passenger(
            id=ops_uid,
            user_id=ops_uid,
            email=ops_email,
            full_name="Flight Operations Agent",
            password_hash=hash_password("ops123"),
            loyalty_tier="gold",
        )
        db.add(ops_pass)
        db.flush()

        ops_rec = AdminUser(
            id=uuid.uuid4(),
            user_id=ops_uid,
            email=ops_email,
            full_name="Flight Operations Agent",
            password_hash=hash_password("ops123"),
            role="ops_agent",
        )
        db.add(ops_rec)

    # 3. Customer Demo
    cust_email = "customer@aeroflow.com"
    cust_pass = db.scalar(select(Passenger).where(Passenger.email == cust_email))
    if not cust_pass:
        cust_uid = uuid.UUID("33333333-3333-4333-8333-333333333333")
        cust_pass = Passenger(
            id=cust_uid,
            user_id=cust_uid,
            email=cust_email,
            full_name="Jane Doe",
            password_hash=hash_password("customer123"),
            loyalty_tier="silver",
        )
        db.add(cust_pass)

    db.flush()

@router.post("/signup", response_model=TokenResponse)
def api_signup(req: UserSignupRequest, db: Session = Depends(get_db)):
    seed_default_users(db)
    existing = db.scalar(select(Passenger).where(Passenger.email == req.email))
    user_id = str(uuid.uuid4())
    pw_hash = hash_password(req.password) if hasattr(req, "password") and req.password else hash_password("password123")

    if existing:
        if existing.user_id and existing.password_hash:
            raise HTTPException(status_code=400, detail="Account with this email already exists.")
        existing.user_id = uuid.UUID(user_id)
        existing.full_name = req.full_name
        existing.password_hash = pw_hash
    else:
        passenger = Passenger(
            id=uuid.uuid4(),
            user_id=uuid.UUID(user_id),
            email=req.email,
            full_name=req.full_name,
            password_hash=pw_hash,
            loyalty_tier="none",
        )
        db.add(passenger)

    db.flush()
    token = create_jwt_token(user_id, req.email, role="customer")
    return TokenResponse(access_token=token, user_id=user_id, role="customer")

@router.post("/login", response_model=TokenResponse)
def api_login(req: UserLoginRequest, db: Session = Depends(get_db)):
    seed_default_users(db)
    passenger = db.scalar(select(Passenger).where(Passenger.email == req.email))
    if not passenger or not passenger.user_id:
        raise HTTPException(status_code=401, detail="Invalid credentials: user not found.")

    # Check password if stored
    if passenger.password_hash and hasattr(req, "password") and req.password:
        if not verify_password(req.password, passenger.password_hash):
            raise HTTPException(status_code=401, detail="Invalid password.")

    # Check if user is an admin
    admin = db.scalar(select(AdminUser).where(AdminUser.user_id == passenger.user_id))
    role = admin.role if admin else "customer"

    token = create_jwt_token(str(passenger.user_id), req.email, role=role)
    return TokenResponse(access_token=token, user_id=str(passenger.user_id), role=role)

@router.get("/me")
def api_get_current_user_profile(
    user: dict | None = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated.")
    
    user_uuid = uuid.UUID(user["sub"])
    passenger = db.scalar(select(Passenger).where(Passenger.user_id == user_uuid))
    admin = db.scalar(select(AdminUser).where(AdminUser.user_id == user_uuid))
    
    return {
        "user_id": user["sub"],
        "email": user.get("email"),
        "full_name": passenger.full_name if passenger else "Administrator",
        "loyalty_tier": passenger.loyalty_tier if passenger else "none",
        "role": admin.role if admin else "customer",
    }
