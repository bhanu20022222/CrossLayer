import hashlib
import hmac
import time

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field

from app.config import settings

router = APIRouter()

SESSION_COOKIE = "crosslayer_session"
SESSION_COOKIE_PATH = "/api/v1"
MIN_SECRET_LENGTH = 32


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=1, max_length=1024)


def auth_is_configured() -> bool:
    return bool(
        settings.auth_username
        and settings.auth_password
        and settings.auth_secret
        and len(settings.auth_secret) >= MIN_SECRET_LENGTH
    )


def create_session_token(issued_at: int | None = None) -> str:
    if not auth_is_configured():
        raise RuntimeError("Dashboard authentication is not configured")
    timestamp = int(time.time()) if issued_at is None else int(issued_at)
    message = f"crosslayer-session-v1:{timestamp}".encode()
    signature = hmac.new(
        settings.auth_secret.encode(), message, hashlib.sha256
    ).hexdigest()
    return f"{timestamp}.{signature}"


def valid_session_token(token: str | None, now: int | None = None) -> bool:
    if not token or not auth_is_configured():
        return False
    try:
        timestamp_text, supplied_signature = token.split(".", 1)
        timestamp = int(timestamp_text)
    except (ValueError, TypeError):
        return False

    current_time = int(time.time()) if now is None else int(now)
    if timestamp > current_time or current_time - timestamp > settings.auth_session_max_age_seconds:
        return False

    expected_token = create_session_token(timestamp)
    _, expected_signature = expected_token.split(".", 1)
    return hmac.compare_digest(supplied_signature, expected_signature)


def request_is_authenticated(request: Request) -> bool:
    return valid_session_token(request.cookies.get(SESSION_COOKIE))


def set_session_cookie(response: Response) -> None:
    response.set_cookie(
        key=SESSION_COOKIE,
        value=create_session_token(),
        max_age=settings.auth_session_max_age_seconds,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite="strict",
        path=SESSION_COOKIE_PATH,
    )


@router.get("/auth/session")
def session(request: Request):
    authenticated = request_is_authenticated(request)
    return {
        "configured": auth_is_configured(),
        "authenticated": authenticated,
        "username": settings.auth_username if authenticated else None,
    }


@router.post("/auth/login")
def login(payload: LoginRequest, response: Response):
    if not auth_is_configured():
        raise HTTPException(
            status_code=503,
            detail=(
                "Dashboard authentication is not configured. Set "
                "CROSSLAYER_AUTH_USERNAME, CROSSLAYER_AUTH_PASSWORD, and a "
                "CROSSLAYER_AUTH_SECRET of at least 32 characters, then restart the backend."
            ),
        )

    username_matches = hmac.compare_digest(
        payload.username.encode(), settings.auth_username.encode()
    )
    password_matches = hmac.compare_digest(
        payload.password.encode(), settings.auth_password.encode()
    )
    if not username_matches or not password_matches:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    set_session_cookie(response)
    return {"authenticated": True, "username": settings.auth_username}


@router.post("/auth/logout")
def logout(response: Response):
    response.delete_cookie(
        key=SESSION_COOKIE,
        path=SESSION_COOKIE_PATH,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite="strict",
    )
    return {"authenticated": False}
