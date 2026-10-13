"""
DriveLens AI - Application Configuration & Settings
"""
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator


import os

_BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_ROOT_DIR = os.path.abspath(os.path.join(_BACKEND_DIR, ".."))
_ENV_FILES = (
    os.path.join(_BACKEND_DIR, ".env"),
    os.path.join(_ROOT_DIR, ".env"),
    ".env",
)


class Settings(BaseSettings):
    # Google OAuth 2.0
    GOOGLE_CLIENT_ID: str = Field(default="", description="Google OAuth 2.0 Client ID")
    GOOGLE_CLIENT_SECRET: str = Field(default="", description="Google OAuth 2.0 Client Secret")
    GOOGLE_REDIRECT_URI: str = Field(
        default="http://localhost:8000/api/auth/callback",
        description="Google OAuth 2.0 Redirect URI"
    )

    # Strictly read-only scope for Drive. Write scopes are explicitly forbidden.
    GOOGLE_DRIVE_SCOPE: str = Field(
        default="https://www.googleapis.com/auth/drive.readonly",
        description="OAuth scope for Google Drive (strictly read-only)"
    )

    # Groq Configuration
    GROQ_API_KEY: str = Field(default="", description="Groq API Key")
    GROQ_MODEL: str = Field(default="openai/gpt-oss-120b", description="Groq Model name")

    # Security & Session Settings
    SESSION_SECRET_KEY: str = Field(
        default="drivelens-default-dev-secret-change-in-production-32bytes",
        description="Key used to sign session cookies and OAuth CSRF state tokens"
    )
    SESSION_COOKIE_NAME: str = "drivelens_session"
    SESSION_MAX_AGE_SECONDS: int = 60 * 60 * 24 * 7  # 7 days
    COOKIE_SECURE: bool = False  # Set to True in production HTTPS
    COOKIE_SAMESITE: str = "lax"

    # Server & CORS
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    FRONTEND_URL: str = "http://localhost:3000"
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ]
    ENVIRONMENT: str = "development"

    model_config = SettingsConfigDict(
        env_file=_ENV_FILES,
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @field_validator("GOOGLE_DRIVE_SCOPE")
    @classmethod
    def validate_readonly_scope(cls, v: str) -> str:
        # Enforce security principle: NEVER allow write scopes
        forbidden_scopes = [
            "https://www.googleapis.com/auth/drive",
            "https://www.googleapis.com/auth/drive.file",
            "https://www.googleapis.com/auth/drive.appdata",
            "https://www.googleapis.com/auth/drive.scripts",
        ]
        if v.strip() in forbidden_scopes:
            raise ValueError(
                f"Scope '{v}' violates DriveLens read-only policy! "
                "Only read-only scopes (e.g. https://www.googleapis.com/auth/drive.readonly) are permitted."
            )
        return v


settings = Settings()
