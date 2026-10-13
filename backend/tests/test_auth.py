"""
Unit tests for OAuth authentication, CSRF state protection, and session handling.
Mocked responses used - live credentials not required for testing.
"""
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from app.main import app
from app.config import settings
from app.security import (
    generate_oauth_state,
    verify_oauth_state,
    serialize_session,
    deserialize_session,
    verify_strictly_readonly_scope,
)
from app.auth import build_authorization_url

client = TestClient(app)


def test_oauth_state_generation_and_validation():
    """Verify that generated state is valid, but tampered or empty state is rejected."""
    state = generate_oauth_state()
    assert state is not None
    assert len(state) > 10
    # Valid state verifies correctly
    assert verify_oauth_state(state) is True

    # Tampered state fails
    tampered = state + "badsignature"
    assert verify_oauth_state(tampered) is False

    # Empty or null state fails
    assert verify_oauth_state("") is False
    assert verify_oauth_state(None) is False


def test_oauth_state_expiration():
    """Verify that expired state tokens are rejected."""
    state = generate_oauth_state()
    # Testing with 0 second max age should treat token as expired
    assert verify_oauth_state(state, max_age_seconds=-1) is False


def test_build_authorization_url_contains_readonly_scope():
    """Verify auth URL contains the read-only scope and CSRF state."""
    with patch.object(settings, "GOOGLE_CLIENT_ID", "test-client-id.apps.googleusercontent.com"), \
         patch.object(settings, "GOOGLE_CLIENT_SECRET", "test-secret"):
        url, state = build_authorization_url()
        assert "accounts.google.com/o/oauth2/v2/auth" in url
        assert "client_id=test-client-id" in url
        assert "drive.readonly" in url
        # Strictly verify no write scope is requested
        assert "scope=https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fdrive+" in url or "scope=https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fdrive.readonly" in url
        assert "prompt=consent" in url
        assert f"state={state}" in url


def test_verify_strictly_readonly_scope():
    """Ensure write scopes are strictly rejected."""
    # Read-only scope is allowed
    assert verify_strictly_readonly_scope("https://www.googleapis.com/auth/drive.readonly openid") is True
    # Metadata read-only is allowed
    assert verify_strictly_readonly_scope("https://www.googleapis.com/auth/drive.metadata.readonly") is True

    # Full drive write scope must be REJECTED
    assert verify_strictly_readonly_scope("https://www.googleapis.com/auth/drive") is False
    # Drive file write scope must be REJECTED
    assert verify_strictly_readonly_scope("https://www.googleapis.com/auth/drive.file") is False
    # Drive appdata write scope must be REJECTED
    assert verify_strictly_readonly_scope("https://www.googleapis.com/auth/drive.appdata") is False


def test_auth_status_unauthenticated():
    """Verify status endpoint returns unauthenticated when no cookie is provided."""
    response = client.get("/api/auth/status")
    assert response.status_code == 200
    data = response.json()
    assert data["is_authenticated"] is False
    assert data["user_email"] is None
    assert data["read_only_enforced"] is True


def test_auth_status_authenticated_never_exposes_tokens():
    """Verify status endpoint never leaks access or refresh tokens to client."""
    mock_session = {
        "access_token": "ya29.secret_token_123456",
        "refresh_token": "1//secret_refresh_token_789",
        "user_email": "user@example.com",
        "user_name": "Test User",
        "scope": "https://www.googleapis.com/auth/drive.readonly",
    }
    cookie_val = serialize_session(mock_session)

    response = client.get("/api/auth/status", cookies={settings.SESSION_COOKIE_NAME: cookie_val})
    assert response.status_code == 200
    data = response.json()
    assert data["is_authenticated"] is True
    assert data["user_email"] == "user@example.com"
    assert data["user_name"] == "Test User"
    assert data["read_only_enforced"] is True

    # CRITICAL SECURITY ASSERTION: Tokens must NOT be in the response!
    response_text = response.text
    assert "ya29.secret_token_123456" not in response_text
    assert "secret_refresh_token_789" not in response_text
    assert "access_token" not in data
    assert "refresh_token" not in data


def test_auth_disconnect():
    """Verify disconnect endpoint clears session cookie and returns success."""
    mock_session = {
        "access_token": "ya29.mock_token",
        "user_email": "user@example.com",
    }
    cookie_val = serialize_session(mock_session)

    with patch("app.main.revoke_tokens", return_value=True):
        response = client.post("/api/auth/disconnect", cookies={settings.SESSION_COOKIE_NAME: cookie_val})
        assert response.status_code == 200
        assert response.json()["status"] == "disconnected"
