import jwt

from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.security import decode_access_token
from app.database import get_db
from app.models import User


AUTH_COOKIE_NAME = "ai_food_access"


def get_current_user(
    access_token: str | None = Cookie(
        default=None,
        alias=AUTH_COOKIE_NAME,
    ),
    db: Session = Depends(get_db),
) -> User:
    """Return the authenticated active user from the HttpOnly auth cookie."""

    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    try:
        payload = decode_access_token(access_token)
        user_id = int(payload.get("sub", ""))
        token_type = payload.get("type")

        if token_type != "access":
            raise ValueError("Invalid token type")

    except (ValueError, TypeError, jwt.PyJWTError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token",
        )

    user = (
        db.query(User)
        .filter(
            User.id == user_id,
            User.is_active.is_(True),
        )
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is inactive or unavailable",
        )

    return user


def get_optional_current_user(
    access_token: str | None = Cookie(
        default=None,
        alias=AUTH_COOKIE_NAME,
    ),
    db: Session = Depends(get_db),
) -> User | None:
    """Return the active user when authenticated, otherwise None."""

    if not access_token:
        return None

    try:
        payload = decode_access_token(access_token)
        user_id = int(payload.get("sub", ""))
        token_type = payload.get("type")

        if token_type != "access":
            return None

    except (ValueError, TypeError, jwt.PyJWTError):
        return None

    return (
        db.query(User)
        .filter(
            User.id == user_id,
            User.is_active.is_(True),
        )
        .first()
    )