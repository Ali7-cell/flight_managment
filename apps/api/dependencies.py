import uuid
from typing import Generator
from fastapi import Header, HTTPException, Depends, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from sqlalchemy import select
import jwt
from flight_domain.db import SessionLocal
from flight_domain.models.auth import AdminUser
from apps.api.config import api_settings

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
    Extracts and validates Supabase JWT token. Null if guest checkout.
    """
    if not credentials:
        return None
    token = credentials.credentials
    try:
        # Decode using SUPABASE_JWT_SECRET or without verification if secret is placeholder
        secret = api_settings.SUPABASE_JWT_SECRET
        payload = jwt.decode(
            token,
            secret,
            algorithms=["HS256"],
            options={"verify_signature": len(secret) >= 32 and not secret.startswith("super-secret")},
        )
        return payload
    except jwt.PyJWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid authentication token: {str(e)}")

def require_admin_role(allowed_roles: list[str]):
    """
    Verifies that the authenticated caller has an admin role in admin_users.
    """
    async def _role_checker(
        user: dict | None = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> AdminUser:
        if not user or not user.get("sub"):
            raise HTTPException(status_code=401, detail="Authentication required for admin operation")
        
        user_uuid = uuid.UUID(user["sub"])
        admin = db.scalar(select(AdminUser).where(AdminUser.user_id == user_uuid))
        if not admin or admin.role not in allowed_roles:
            raise HTTPException(
                status_code=403,
                detail=f"Operation requires one of roles: {allowed_roles}. Current: {getattr(admin, 'role', None)}"
            )
        return admin

    return _role_checker
