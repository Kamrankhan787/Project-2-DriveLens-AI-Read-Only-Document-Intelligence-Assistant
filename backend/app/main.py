"""
DriveLens AI - FastAPI Application Entry Point
Production-minded, strictly read-only Document Intelligence Assistant.
"""
# ── SSL Patch ──────────────────────────────────────────────────────────────────
# Disables SSL certificate verification globally for this process.
# Required on Windows machines where antivirus/proxy intercepts HTTPS traffic
# and replaces certificates, causing SSL EOF errors on external API calls.
import ssl
import socket

# Force Python socket resolver to prefer IPv4 (AF_INET) over IPv6.
# On Windows, Google DNS returns IPv6 addresses first, but local ISP/firewall/proxy
# often times out or resets IPv6 handshakes, causing [SSL: UNEXPECTED_EOF_WHILE_READING].
_orig_getaddrinfo = socket.getaddrinfo
def _ipv4_first_getaddrinfo(host, port, family=0, *args, **kwargs):
    if family == 0 or family == getattr(socket, "AF_UNSPEC", 0):
        family = socket.AF_INET
    return _orig_getaddrinfo(host, port, family, *args, **kwargs)
socket.getaddrinfo = _ipv4_first_getaddrinfo

ssl._create_default_https_context = ssl._create_unverified_context

import os
import logging
from typing import Optional, List
from fastapi import FastAPI, Request, Response, HTTPException, Depends
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.schemas import (
    AuthStatus,
    DocumentMetadata,
    AnalysisResponse,
    AnalysisRequest,
    RevokeResponse,
    ErrorResponse,
)
from app.security import serialize_session, deserialize_session
from app.auth import (
    build_authorization_url,
    exchange_code_for_tokens,
    get_google_credentials,
    revoke_tokens,
    OAuthError,
)
from app.drive_client import ReadOnlyDriveClient, is_mime_type_supported
from app.document_extractor import extract_document_text, DocumentExtractionError
from app.analyzer import DocumentAnalyzer

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("drivelens.main")

app = FastAPI(
    title="DriveLens AI API",
    description="Read-Only Document Intelligence Assistant connected to Google Drive",
    version="1.0.0",
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


def get_current_session(request: Request) -> Optional[dict]:
    """Dependency to retrieve and verify session data from HTTP-only cookie."""
    cookie_value = request.cookies.get(settings.SESSION_COOKIE_NAME)
    if not cookie_value:
        return None
    return deserialize_session(cookie_value)


def require_session(request: Request) -> dict:
    """Dependency requiring active authenticated session."""
    session_data = get_current_session(request)
    if not session_data or not session_data.get("access_token"):
        raise HTTPException(
            status_code=401,
            detail="Authentication required. Please connect your Google Drive account."
        )
    return session_data


@app.get("/health", summary="Health Check")
async def health():
    return {
        "status": "healthy",
        "service": "DriveLens AI",
        "read_only_mode": True,
        "configured_scope": settings.GOOGLE_DRIVE_SCOPE,
    }


# =====================================================================
# AUTHENTICATION ENDPOINTS
# =====================================================================

@app.get("/api/auth/login", summary="Initiate Google OAuth 2.0 Login")
async def auth_login():
    """
    Redirects user to Google OAuth 2.0 consent page requesting strictly read-only scope.
    """
    try:
        auth_url, _ = build_authorization_url()
        return RedirectResponse(url=auth_url)
    except OAuthError as e:
        return RedirectResponse(url=f"/?auth_error={str(e)}")


@app.get("/api/auth/callback", summary="Google OAuth 2.0 Callback")
async def auth_callback(
    request: Request,
    response: Response,
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
):
    """
    Handles Google OAuth redirect, validates CSRF state, exchanges code for tokens,
    and sets an encrypted HTTP-only session cookie.
    """
    if error:
        logger.warning(f"Google OAuth returned error: {error}")
        return RedirectResponse(url=f"/?auth_error={error}")

    if not code or not state:
        return RedirectResponse(url="/?auth_error=missing_code_or_state")

    try:
        session_data = await exchange_code_for_tokens(code=code, state=state)
        cookie_val = serialize_session(session_data)

        # Redirect user back to frontend dashboard (relative URL keeps user on current origin)
        redirect_resp = RedirectResponse(
            url="/?auth=success",
            status_code=302
        )
        redirect_resp.set_cookie(
            key=settings.SESSION_COOKIE_NAME,
            value=cookie_val,
            max_age=settings.SESSION_MAX_AGE_SECONDS,
            httponly=True,
            secure=settings.COOKIE_SECURE,
            samesite=settings.COOKIE_SAMESITE,
        )
        return redirect_resp
    except OAuthError as e:
        logger.error(f"OAuth callback failed: {e}")
        return RedirectResponse(url=f"{settings.FRONTEND_URL}/?auth_error={str(e)}")


@app.get("/api/auth/status", response_model=AuthStatus, summary="Check Authentication Status")
async def auth_status(request: Request):
    """
    Returns current connection status and email. Raw tokens are NEVER exposed.
    """
    session_data = get_current_session(request)
    if not session_data or not session_data.get("access_token"):
        return AuthStatus(
            is_authenticated=False,
            user_email=None,
            user_name=None,
            scope=None,
            read_only_enforced=True
        )

    return AuthStatus(
        is_authenticated=True,
        user_email=session_data.get("user_email"),
        user_name=session_data.get("user_name"),
        scope=session_data.get("scope", settings.GOOGLE_DRIVE_SCOPE),
        read_only_enforced=True
    )


@app.post("/api/auth/disconnect", response_model=RevokeResponse, summary="Disconnect and Revoke Google Drive Access")
async def auth_disconnect(request: Request, response: Response):
    """
    Revokes OAuth tokens with Google and clears the session cookie.
    """
    session_data = get_current_session(request)
    if session_data:
        await revoke_tokens(session_data)

    response.delete_cookie(
        key=settings.SESSION_COOKIE_NAME,
        httponly=True,
        samesite=settings.COOKIE_SAMESITE
    )
    return RevokeResponse(
        status="disconnected",
        message="Successfully disconnected from Google Drive. OAuth tokens revoked."
    )


# =====================================================================
# GOOGLE DRIVE READ-ONLY ENDPOINTS
# =====================================================================

@app.get("/api/drive/recent", response_model=List[DocumentMetadata], summary="List Recent Documents")
async def list_recent_documents(session: dict = Depends(require_session)):
    """
    Retrieves the most recently modified files from Google Drive (strictly read-only).
    Annotates whether each file is eligible for text intelligence.
    """
    try:
        credentials = get_google_credentials(session)
        client = ReadOnlyDriveClient(credentials)
        files, _ = client.list_documents(page_size=25)

        results = []
        for f in files:
            mime = f.get("mimeType", "")
            is_supported, reason = is_mime_type_supported(mime)
            size_val = int(f.get("size")) if f.get("size") else None
            results.append(
                DocumentMetadata(
                    id=f["id"],
                    name=f["name"],
                    mime_type=mime,
                    modified_time=f["modifiedTime"],
                    size_bytes=size_val,
                    is_supported=is_supported,
                    unsupported_reason=reason,
                    web_view_link=f.get("webViewLink"),
                )
            )
        return results
    except Exception as e:
        logger.exception("Error fetching recent documents")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve documents: {str(e)}")


@app.post("/api/drive/analyze", response_model=AnalysisResponse, summary="Analyze Document Intelligence")
async def analyze_document(
    request_data: Optional[AnalysisRequest] = None,
    session: dict = Depends(require_session)
):
    """
    Fetches the targeted document (or automatically selects the most recently modified eligible document),
    extracts the text using official Google Drive API, and generates evidence-grounded intelligence using OpenAI.
    """
    try:
        credentials = get_google_credentials(session)
        client = ReadOnlyDriveClient(credentials)

        target_file = None
        if request_data and request_data.document_id:
            target_file = client.get_file_metadata(request_data.document_id)
        else:
            # Retrieve most recently modified supported document
            target_file = client.get_most_recent_supported_document()
            if not target_file:
                # Check if Drive is completely empty or just no supported documents
                any_recent = client.get_most_recent_document()
                if not any_recent:
                    raise HTTPException(
                        status_code=404,
                        detail="No documents found in your Google Drive. Please create or add a document first."
                    )
                else:
                    _, reason = is_mime_type_supported(any_recent.get("mimeType", ""))
                    raise HTTPException(
                        status_code=422,
                        detail=f"The most recent file '{any_recent.get('name')}' is unsupported: {reason}"
                    )

        file_id = target_file["id"]
        file_name = target_file["name"]
        mime_type = target_file["mimeType"]
        modified_time = target_file["modifiedTime"]

        # Validate readability
        is_supported, reason = is_mime_type_supported(mime_type)
        if not is_supported:
            raise HTTPException(status_code=422, detail=f"Document '{file_name}' cannot be read: {reason}")

        # Download / export document content bytes
        content_bytes = client.download_file_bytes(file_id, mime_type)

        # Extract textual content
        content_text = extract_document_text(content_bytes, mime_type)

        # Run AI intelligence layer
        analyzer = DocumentAnalyzer()
        analysis_result = analyzer.analyze_document(
            document_id=file_id,
            document_title=file_name,
            mime_type=mime_type,
            last_modified=modified_time,
            content_text=content_text
        )

        return analysis_result

    except HTTPException:
        raise
    except DocumentExtractionError as e:
        logger.error(f"Extraction error: {e}")
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.exception("Error analyzing document")
        raise HTTPException(status_code=500, detail=f"Analysis pipeline failed: {str(e)}")


# =====================================================================
# UNIFIED STATIC FRONTEND DELIVERY
# Mounts the compiled Next.js static build so the entire UI and API
# run together seamlessly on a single port (http://localhost:8000).
# =====================================================================
frontend_out = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "out")
)

if os.path.exists(frontend_out):
    app.mount("/", StaticFiles(directory=frontend_out, html=True), name="frontend")
