import time

import pytest
from fastapi.testclient import TestClient

from app.auth import SESSION_COOKIE, create_session_token
from app.config import settings
from app.main import app


@pytest.fixture
def configured_client(monkeypatch):
    monkeypatch.setattr(settings, "auth_username", "research-user")
    monkeypatch.setattr(settings, "auth_password", "private-test-password")
    monkeypatch.setattr(
        settings,
        "auth_secret",
        "dedicated-test-signing-secret-with-at-least-32-characters",
    )
    monkeypatch.setattr(settings, "auth_session_max_age_seconds", 3600)
    return TestClient(app)


def test_protected_api_rejects_requests_without_a_session(configured_client):
    response = configured_client.get("/api/v1/decisions")

    assert response.status_code == 401
    assert response.json()["detail"] == "Authentication required"


def test_login_sets_http_only_cookie_and_allows_api_access(configured_client):
    response = configured_client.post(
        "/api/v1/auth/login",
        json={"username": "research-user", "password": "private-test-password"},
    )

    assert response.status_code == 200
    assert response.json() == {"authenticated": True, "username": "research-user"}
    cookie = response.headers["set-cookie"]
    assert "HttpOnly" in cookie
    assert "SameSite=strict" in cookie
    assert "crosslayer_session=" in cookie
    assert configured_client.get("/api/v1/decisions").status_code == 200


def test_login_does_not_disclose_which_credential_was_wrong(configured_client):
    response = configured_client.post(
        "/api/v1/auth/login",
        json={"username": "research-user", "password": "wrong-password"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid username or password"
    assert SESSION_COOKIE not in configured_client.cookies


def test_session_expiration_rejects_old_signed_cookie(configured_client):
    old_token = create_session_token(
        int(time.time()) - settings.auth_session_max_age_seconds - 1
    )
    configured_client.cookies.set(SESSION_COOKIE, old_token)

    response = configured_client.get("/api/v1/decisions")

    assert response.status_code == 401


def test_logout_clears_session_and_reprotects_api(configured_client):
    login_response = configured_client.post(
        "/api/v1/auth/login",
        json={"username": "research-user", "password": "private-test-password"},
    )
    assert login_response.status_code == 200

    response = configured_client.post("/api/v1/auth/logout")

    assert response.status_code == 200
    assert "crosslayer_session=" in response.headers["set-cookie"]
    assert configured_client.get("/api/v1/decisions").status_code == 401


def test_missing_auth_configuration_fails_closed(monkeypatch):
    monkeypatch.setattr(settings, "auth_username", None)
    monkeypatch.setattr(settings, "auth_password", None)
    monkeypatch.setattr(settings, "auth_secret", None)
    client = TestClient(app)

    assert client.get("/api/v1/auth/session").json() == {
        "configured": False,
        "authenticated": False,
        "username": None,
    }
    assert client.get("/api/v1/decisions").status_code == 503
    assert client.post(
        "/api/v1/auth/login",
        json={"username": "any", "password": "any"},
    ).status_code == 503
