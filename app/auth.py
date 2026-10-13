"""
DriveLens AI - OAuth 2.0 Flow and Authentication Management
Manages Google OAuth authorization, code exchange, token revocation,
and session credential restoration.
"""
import logging
import urllib.parse
from typing import Dict, Any, Tuple, Optional
import httpx
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from app.config import settings
from app.security import generate_oauth_state, verify_oauth_state, verify_strictly_readonly_scope

logger = logging.getLogger("drivelens.auth")

GOOGLE_AUTH_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
GOOGLE_REVOKE_ENDPOINT = "https://oauth2.googleapis.com/revoke"
GOOGLE_USERINFO_ENDPOINT = "https://www.googleapis.com/oauth2/v3/userinfo"


class OAuthError(Exception):
    """Custom exception for OAuth failures."""
    pass


def build_authorization_url() -> Tuple[str, str]:
    """
    Constructs Google OAuth 2.0 authorization URL requesting strictly read-only Drive permissions.
    Generates a cryptographically signed CSRF state token.
    """
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        raise OAuthError("Google OAuth credentials are not configured. Please set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET.")

    state = generate_oauth_state()

    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "response_type": "code",
        # Request strictly read-only scope plus openid/email for user verification
        "scope": f"{settings.GOOGLE_DRIVE_SCOPE} openid email profile",
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
        "include_granted_scopes": "true",
    }

    query_str = urllib.parse.urlencode(params)
    auth_url = f"{GOOGLE_AUTH_ENDPOINT}?{query_str}"
    return auth_url, state



async def exchange_code_for_tokens(code: str, state: str) -> Dict[str, Any]:
    """
    Validates CSRF state and exchanges the authorization code for tokens with Google.
    Retrieves user profile info without storing raw tokens in frontend.
    """
    if not verify_oauth_state(state):
        raise OAuthError("Invalid or expired OAuth state. Request rejected for CSRF protection.")

    token_payload = {
        "code": code,
        "client_id": settings.GOOGLE_CLIENT_ID,
        "client_secret": settings.GOOGLE_CLIENT_SECRET,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "grant_type": "authorization_code",
    }

    async with httpx.AsyncClient(verify=False, timeout=15.0) as client:
        resp = await client.post(GOOGLE_TOKEN_ENDPOINT, data=token_payload)
        if resp.status_code != 200:
            logger.error(f"Failed to exchange OAuth code: {resp.text}")
            raise OAuthError(f"Google token exchange failed ({resp.status_code}): {resp.text}")

        token_data = resp.json()

    granted_scope = token_data.get("scope", "")
    if not verify_strictly_readonly_scope(granted_scope):
        raise OAuthError("Security violation: Granted scope contains write privileges. Refusing credentials.")

    user_email = None
    user_name = None

    # Fetch user info if access token is available
    access_token = token_data.get("access_token")
    if access_token:
        try:
            async with httpx.AsyncClient(verify=False, timeout=10.0) as client:
                info_resp = await client.get(
                    GOOGLE_USERINFO_ENDPOINT,
                    headers={"Authorization": f"Bearer {access_token}"}
                )
                if info_resp.status_code == 200:
                    user_info = info_resp.json()
                    user_email = user_info.get("email")
                    user_name = user_info.get("name")
        except Exception as e:
            logger.warning(f"Could not retrieve user info: {e}")

    # Build internal session state dictionary
    session_data = {
        "access_token": access_token,
        "refresh_token": token_data.get("refresh_token"),
        "token_type": token_data.get("token_type", "Bearer"),
        "expires_in": token_data.get("expires_in"),
        "scope": granted_scope,
        "user_email": user_email,
        "user_name": user_name,
    }

    return session_data


def get_google_credentials(session_data: Dict[str, Any]) -> Credentials:
    """
    Reconstructs Google OAuth2 Credentials object from session tokens.
    Refreshes automatically if expired and refresh_token is present.
    """
    if not session_data or not session_data.get("access_token"):
        raise OAuthError("No active credentials found in session. Please connect your Google account.")

    creds = Credentials(
        token=session_data.get("access_token"),
        refresh_token=session_data.get("refresh_token"),
        token_uri=GOOGLE_TOKEN_ENDPOINT,
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
        scopes=[settings.GOOGLE_DRIVE_SCOPE],
    )

    if creds.expired and creds.refresh_token:
        try:
            with httpx.Client(verify=False, timeout=15.0) as client:
                refresh_resp = client.post(
                    GOOGLE_TOKEN_ENDPOINT,
                    data={
                        "client_id": settings.GOOGLE_CLIENT_ID,
                        "client_secret": settings.GOOGLE_CLIENT_SECRET,
                        "refresh_token": creds.refresh_token,
                        "grant_type": "refresh_token",
                    }
                )
                if refresh_resp.status_code == 200:
                    new_tokens = refresh_resp.json()
                    new_access_token = new_tokens.get("access_token")
                    creds.token = new_access_token
                    session_data["access_token"] = new_access_token
                else:
                    logger.error(f"Token refresh failed: {refresh_resp.text}")
                    raise OAuthError(f"Token refresh failed ({refresh_resp.status_code}): {refresh_resp.text}")
        except Exception as e:
            logger.error(f"Failed to refresh expired Google token: {e}")
            raise OAuthError("Google credentials expired and could not be refreshed. Please reconnect.")

    return creds


async def revoke_tokens(session_data: Dict[str, Any]) -> bool:
    """
    Revokes the current OAuth token with Google and removes access.
    """
    token_to_revoke = session_data.get("refresh_token") or session_data.get("access_token")
    if not token_to_revoke:
        return True

    try:
        async with httpx.AsyncClient(verify=False, timeout=10.0) as client:
            resp = await client.post(
                GOOGLE_REVOKE_ENDPOINT,
                params={"token": token_to_revoke},
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            logger.info(f"Token revocation status: {resp.status_code}")
            return resp.status_code == 200
    except Exception as e:
        logger.warning(f"Exception while revoking token: {e}")
        return False

