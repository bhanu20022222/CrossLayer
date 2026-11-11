from fastapi.testclient import TestClient

from app.auth import SESSION_COOKIE, create_session_token
from app.config import settings
from app.main import app


def authenticated_test_client() -> TestClient:
    settings.auth_username = "test-user"
    settings.auth_password = "test-password-for-unit-tests"
    settings.auth_secret = "test-only-signing-secret-that-is-long-enough"
    settings.auth_session_max_age_seconds = 28800

    client = TestClient(app)
    client.cookies.set(SESSION_COOKIE, create_session_token())
    return client
