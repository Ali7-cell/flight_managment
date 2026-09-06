import uuid
from sqlalchemy import Column, String, DateTime, CheckConstraint
from flight_domain.models.base import Base, utcnow, GUID

class Passenger(Base):
    __tablename__ = "passengers"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    user_id = Column(GUID, nullable=True, index=True)
    email = Column(String, nullable=False, index=True)
    full_name = Column(String, nullable=False)
    phone = Column(String, nullable=True)
    password_hash = Column(String, nullable=True)
    loyalty_tier = Column(String, nullable=False, default="none")
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        CheckConstraint("loyalty_tier in ('none','silver','gold','platinum')", name="chk_passenger_loyalty_tier"),
    )

class AdminUser(Base):
    __tablename__ = "admin_users"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    user_id = Column(GUID, nullable=False, unique=True)
    email = Column(String, nullable=True, index=True)
    full_name = Column(String, nullable=True)
    password_hash = Column(String, nullable=True)
    role = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        CheckConstraint("role in ('super_admin','ops_agent')", name="chk_admin_user_role"),
    )
