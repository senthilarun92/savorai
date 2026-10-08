from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.sql import func

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)

    username = Column(String(30), unique=True, index=True, nullable=False)
    name = Column(String(100), nullable=True)
    email = Column(String(255), unique=True, index=True, nullable=False)

    # Google OAuth accounts use this stable Google subject ID.
    google_sub = Column(String(255), unique=True, index=True, nullable=True)

    # Local-password accounts use this.
    # Google-only accounts can keep this NULL.
    password_hash = Column(String(255), nullable=True)

    is_active = Column(Boolean, nullable=False, default=True)
    email_verified = Column(Boolean, nullable=False, default=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
    last_login_at = Column(DateTime(timezone=True), nullable=True)

