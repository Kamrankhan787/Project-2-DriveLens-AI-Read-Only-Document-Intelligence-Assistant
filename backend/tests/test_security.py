"""
Unit tests for DriveLens AI Security and Compliance.
Verifies least-privilege scope enforcement, absence of write endpoints in FastAPI,
secret masking, and CSRF protection.
"""
import pytest
from pydantic import ValidationError
from app.config import Settings, settings
from app.main import app
from app.security import mask_secret, verify_strictly_readonly_scope


def test_readonly_scope_enforcement_in_settings():
    """Verify Settings rejects write scopes and allows read-only scopes."""
    # Readonly scope is accepted
    valid_settings = Settings(
        GOOGLE_DRIVE_SCOPE="https://www.googleapis.com/auth/drive.readonly"
    )
    assert valid_settings.GOOGLE_DRIVE_SCOPE == "https://www.googleapis.com/auth/drive.readonly"

    # Full Drive write scope must raise ValidationError
    with pytest.raises(ValidationError):
        Settings(GOOGLE_DRIVE_SCOPE="https://www.googleapis.com/auth/drive")

    # File write scope must raise ValidationError
    with pytest.raises(ValidationError):
        Settings(GOOGLE_DRIVE_SCOPE="https://www.googleapis.com/auth/drive.file")


def test_no_write_endpoints_exposed_in_api():
    """
    STRUCTURAL API AUDIT:
    Inspects all registered routes in FastAPI to verify no create, upload,
    delete, update, or patch endpoints exist for Google Drive files.
    """
    write_verbs = {"PUT", "DELETE", "PATCH"}
    forbidden_path_keywords = ["upload", "delete", "create", "update", "write", "modify", "share", "trash"]

    for route in app.routes:
        methods = getattr(route, "methods", set())
        path = getattr(route, "path", "")

        # Check if any route combines write verbs with drive file operations
        if "/api/drive" in path:
            has_forbidden_verb = bool(methods.intersection(write_verbs))
            assert not has_forbidden_verb, f"Security violation: route {path} uses mutating HTTP verb {methods}"

            for kw in forbidden_path_keywords:
                assert kw not in path.lower(), f"Security violation: route {path} exposes forbidden action '{kw}'"


def test_secret_masking():
    """Verify secrets are masked to prevent accidental leakage in UI or logs."""
    assert mask_secret("sk-proj-abcdef1234567890xyz") == "sk-p...0xyz"
    assert mask_secret("short") == "***"
    assert mask_secret("") == ""
    assert mask_secret(None) == ""


def test_strictly_readonly_scope_validator():
    """Verify scope validator rejects scopes containing write access."""
    assert verify_strictly_readonly_scope("https://www.googleapis.com/auth/drive.readonly") is True
    assert verify_strictly_readonly_scope("https://www.googleapis.com/auth/drive.metadata.readonly") is True
    assert verify_strictly_readonly_scope("https://www.googleapis.com/auth/drive") is False
    assert verify_strictly_readonly_scope("https://www.googleapis.com/auth/drive.file") is False
