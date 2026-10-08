import os
import re
import secrets
from datetime import datetime, timezone

from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2 import id_token
from google_auth_oauthlib.flow import Flow
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

load_dotenv()

# Local development only: Google OAuth callback uses HTTP on 127.0.0.1.
# Production must use HTTPS and must not enable insecure transport.
if os.getenv("SAVORAI_ENV", "development").lower() == "development":
    os.environ.setdefault("OAUTHLIB_INSECURE_TRANSPORT", "1")

from app.auth.dependencies import get_current_user
from app.auth.security import (
    create_access_token,
    hash_password,
    verify_password,
)
from app.database import get_db
from app.models import User
from app.schemas.auth import (
    SigninRequest,
    SignupRequest,
    UserResponse,
)


router = APIRouter(
    prefix="/api/auth",
    tags=["Authentication"],
)


AUTH_COOKIE_NAME = "ai_food_access"
AUTH_COOKIE_SECURE = False


def user_response(user: User) -> UserResponse:
    return UserResponse(
        id=user.id,
        username=user.username,
        name=user.name,
        email=user.email,
        email_verified=user.email_verified,
    )


@router.post(
    "/signup",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def signup(
    signup_data: SignupRequest,
    db: Session = Depends(get_db),
):
    """Create a new local-password user account."""

    existing_username = (
        db.query(User)
        .filter(
            func.lower(User.username) == signup_data.username
        )
        .first()
    )

    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username is already registered",
        )

    existing_email = (
        db.query(User)
        .filter(
            func.lower(User.email) == signup_data.email
        )
        .first()
    )

    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email is already registered",
        )

    user = User(
        username=signup_data.username,
        name=(
            signup_data.name.strip()
            if signup_data.name
            else None
        ),
        email=signup_data.email,
        password_hash=hash_password(
            signup_data.password
        ),
        is_active=True,
        email_verified=False,
    )

    db.add(user)

    try:
        db.commit()
        db.refresh(user)
    except IntegrityError as exc:
        print("GOOGLE OAUTH DB ERROR:", repr(exc))
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username or email is already registered",
        )

    return user_response(user)


@router.post(
    "/signin",
    response_model=UserResponse,
)
def signin(
    signin_data: SigninRequest,
    response: Response,
    db: Session = Depends(get_db),
):
    """Authenticate a local user and issue an HttpOnly cookie."""

    user = (
        db.query(User)
        .filter(
            func.lower(User.username)
            == signin_data.identifier
        )
        .first()
    )

    if not user:
        user = (
            db.query(User)
            .filter(
                func.lower(User.email)
                == signin_data.identifier
            )
            .first()
        )

    invalid_credentials = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid username/email or password",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not user or not user.is_active:
        raise invalid_credentials

    if not user.password_hash:
        raise invalid_credentials

    if not verify_password(
        signin_data.password,
        user.password_hash,
    ):
        raise invalid_credentials

    from datetime import datetime, timezone

    user.last_login_at = datetime.now(timezone.utc)

    token = create_access_token(
        user_id=user.id,
        username=user.username,
    )

    db.commit()

    response.set_cookie(
        key=AUTH_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=AUTH_COOKIE_SECURE,
        samesite="lax",
        max_age=30 * 60,
        path="/",
    )

    return user_response(user)


@router.get(
    "/me",
    response_model=UserResponse,
)
def get_me(
    current_user: User = Depends(get_current_user),
):
    """Return the currently authenticated user."""
    return user_response(current_user)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
)
def logout(response: Response):
    """Clear the authentication cookie."""
    response.delete_cookie(
        key=AUTH_COOKIE_NAME,
        path="/",
    )
    return None

# ============================================================
# GOOGLE OAUTH
# ============================================================

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "").strip()
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "").strip()
GOOGLE_REDIRECT_URI = os.getenv(
    "GOOGLE_REDIRECT_URI",
    "http://127.0.0.1:8000/api/auth/google/callback",
).strip()

GOOGLE_STATE_COOKIE = "savorai_google_state"
GOOGLE_VERIFIER_COOKIE = "savorai_google_verifier"

GOOGLE_SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
]


def create_google_flow(
    state: str | None = None,
    code_verifier: str | None = None,
    autogenerate_code_verifier: bool = True,
) -> Flow:
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        raise RuntimeError(
            "Google OAuth credentials are not configured"
        )

    client_config = {
        "web": {
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": (
                "https://www.googleapis.com/oauth2/v1/certs"
            ),
            "redirect_uris": [GOOGLE_REDIRECT_URI],
        }
    }

    flow = Flow.from_client_config(
        client_config,
        scopes=GOOGLE_SCOPES,
        state=state,
        code_verifier=code_verifier,
        autogenerate_code_verifier=autogenerate_code_verifier,
    )

    flow.redirect_uri = GOOGLE_REDIRECT_URI
    return flow


def generate_google_username(
    db: Session,
    email: str,
) -> str:
    base = email.split("@", 1)[0].lower()

    base = re.sub(
        r"[^a-z0-9_]+",
        "_",
        base,
    ).strip("_")

    if len(base) < 3:
        base = "user"

    base = base[:24]

    candidate = base

    existing = (
        db.query(User)
        .filter(
            func.lower(User.username) == candidate
        )
        .first()
    )

    if not existing:
        return candidate

    for _ in range(20):
        suffix = secrets.token_hex(3)
        candidate = f"{base[:23]}_{suffix}"

        existing = (
            db.query(User)
            .filter(
                func.lower(User.username) == candidate
            )
            .first()
        )

        if not existing:
            return candidate

    raise RuntimeError("Unable to generate a unique username")


@router.get("/google/start")
def google_start():
    """Start Google OAuth login with PKCE."""

    try:
        state = secrets.token_urlsafe(32)

        # Let google-auth-oauthlib generate the PKCE verifier.
        # Only the derived challenge is sent to Google.
        flow = create_google_flow(
            state=state,
            autogenerate_code_verifier=True,
        )

        authorization_url, _ = flow.authorization_url(
            access_type="online",
            include_granted_scopes="true",
            prompt="select_account",
        )

        code_verifier = flow.code_verifier

        if not code_verifier:
            raise RuntimeError(
                "Google OAuth PKCE verifier was not generated"
            )

        redirect = RedirectResponse(
            authorization_url,
            status_code=status.HTTP_302_FOUND,
        )

        redirect.set_cookie(
            key=GOOGLE_STATE_COOKIE,
            value=state,
            httponly=True,
            secure=AUTH_COOKIE_SECURE,
            samesite="lax",
            max_age=10 * 60,
            path="/",
        )

        redirect.set_cookie(
            key=GOOGLE_VERIFIER_COOKIE,
            value=code_verifier,
            httponly=True,
            secure=AUTH_COOKIE_SECURE,
            samesite="lax",
            max_age=10 * 60,
            path="/",
        )

        return redirect

    except Exception as exc:
        print("GOOGLE OAUTH START ERROR:", repr(exc))

        return RedirectResponse(
            "/login?google_error=1",
            status_code=status.HTTP_303_SEE_OTHER,
        )


@router.get("/google/callback")
def google_callback(
    request: Request,
    db: Session = Depends(get_db),
):
    """Complete Google OAuth login."""

    state_cookie = request.cookies.get(
        GOOGLE_STATE_COOKIE
    )

    verifier_cookie = request.cookies.get(
        GOOGLE_VERIFIER_COOKIE
    )

    state_query = request.query_params.get("state")
    code = request.query_params.get("code")
    oauth_error = request.query_params.get("error")

    if oauth_error:
        return RedirectResponse(
            "/login?google_error=1",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    if (
        not state_cookie
        or not verifier_cookie
        or not state_query
        or not secrets.compare_digest(
            state_cookie,
            state_query,
        )
    ):
        print("GOOGLE OAUTH STATE/PKCE ERROR")

        return RedirectResponse(
            "/login?google_error=1",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    if not code:
        print("GOOGLE OAUTH CODE MISSING")

        return RedirectResponse(
            "/login?google_error=1",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    try:
        # Recreate the Flow using the SAME verifier stored
        # in the temporary HttpOnly cookie.
        flow = create_google_flow(
            state=state_cookie,
            code_verifier=verifier_cookie,
            autogenerate_code_verifier=False,
        )

        flow.fetch_token(
            authorization_response=str(request.url)
        )

        credentials = flow.credentials

        if not credentials.id_token:
            raise ValueError(
                "Google ID token was not returned"
            )

        google_info = id_token.verify_oauth2_token(
            credentials.id_token,
            GoogleRequest(),
            GOOGLE_CLIENT_ID,
            clock_skew_in_seconds=5,
        )

        google_sub = str(
            google_info.get("sub", "")
        ).strip()

        email = str(
            google_info.get("email", "")
        ).strip().lower()

        name = str(
            google_info.get("name", "")
        ).strip()

        email_verified = bool(
            google_info.get(
                "email_verified",
                False,
            )
        )

        if not google_sub:
            raise ValueError(
                "Google subject ID missing"
            )

        if not email:
            raise ValueError(
                "Google email missing"
            )

        if not email_verified:
            raise ValueError(
                "Google email is not verified"
            )

        # Existing Google-linked account.
        user = (
            db.query(User)
            .filter(
                User.google_sub == google_sub
            )
            .first()
        )

        if user:

            if not user.is_active:
                raise ValueError(
                    "User account is inactive"
                )

            if name and not user.name:
                user.name = name

            user.email_verified = True

        else:

            # Link to an existing SavorAI account
            # when the verified Google email matches.
            user = (
                db.query(User)
                .filter(
                    func.lower(User.email) == email
                )
                .first()
            )

            if user:

                if not user.is_active:
                    raise ValueError(
                        "User account is inactive"
                    )

                if (
                    user.google_sub
                    and user.google_sub != google_sub
                ):
                    raise ValueError(
                        "This Google account is already linked"
                    )

                user.google_sub = google_sub
                user.email_verified = True

                if name and not user.name:
                    user.name = name

            else:

                username = generate_google_username(
                    db,
                    email,
                )

                user = User(
                    username=username,
                    name=name or None,
                    email=email,
                    google_sub=google_sub,
                    password_hash=None,
                    is_active=True,
                    email_verified=True,
                )

                db.add(user)

        user.last_login_at = datetime.now(
            timezone.utc
        )

        db.commit()
        db.refresh(user)

        token = create_access_token(
            user_id=user.id,
            username=user.username,
        )

        redirect = RedirectResponse(
            "/app",
            status_code=status.HTTP_303_SEE_OTHER,
        )

        redirect.delete_cookie(
            key=GOOGLE_STATE_COOKIE,
            path="/",
        )

        redirect.delete_cookie(
            key=GOOGLE_VERIFIER_COOKIE,
            path="/",
        )

        redirect.set_cookie(
            key=AUTH_COOKIE_NAME,
            value=token,
            httponly=True,
            secure=AUTH_COOKIE_SECURE,
            samesite="lax",
            max_age=30 * 60,
            path="/",
        )

        return redirect

    except (ValueError, RuntimeError) as exc:
        db.rollback()
        print("GOOGLE OAUTH ERROR:", repr(exc))

        return RedirectResponse(
            "/login?google_error=1",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    except IntegrityError as exc:
        db.rollback()
        print("GOOGLE OAUTH DB ERROR:", repr(exc))

        return RedirectResponse(
            "/login?google_error=1",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    except Exception as exc:
        db.rollback()
        print("GOOGLE OAUTH UNEXPECTED ERROR:", repr(exc))

        return RedirectResponse(
            "/login?google_error=1",
            status_code=status.HTTP_303_SEE_OTHER,
        )






