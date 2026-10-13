"""
DriveLens AI - Read-Only Google Drive Client
Enforces strict least-privilege read-only access using direct HTTP calls with httpx.
Contains ZERO write, create, update, share, or delete operations.
Includes automatic retry handling for transient network and SSL handshakes.
"""
import logging
import time
from typing import List, Dict, Any, Optional, Tuple
import httpx
from google.oauth2.credentials import Credentials

logger = logging.getLogger("drivelens.drive_client")

DRIVE_API_BASE = "https://www.googleapis.com/drive/v3"

# Supported readable document mime types
SUPPORTED_MIME_TYPES = {
    "application/vnd.google-apps.document": "Google Docs",
    "application/pdf": "PDF Document",
    "text/plain": "Plain Text (.txt)",
    "text/markdown": "Markdown (.md)",
    "text/csv": "CSV Spreadsheet",
    "text/tab-separated-values": "TSV Document",
    "application/json": "JSON Data",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "Word Document (.docx)",
}

# Known unsupported file types for informative error messages
UNSUPPORTED_MIME_REASONS = {
    "application/vnd.google-apps.folder": "Folders contain lists of files, not document text.",
    "application/vnd.google-apps.spreadsheet": "Google Sheets cannot be exported as single-stream text directly.",
    "application/vnd.google-apps.presentation": "Google Slides contains slide layouts rather than continuous document text.",
    "application/zip": "Compressed archive (.zip) contains binary archives, not direct text.",
    "image/jpeg": "Image file requires OCR which is out of scope for standard text document extraction.",
    "image/png": "Image file requires OCR which is out of scope for standard text document extraction.",
    "video/mp4": "Media file does not contain readable document text.",
    "audio/mpeg": "Audio file does not contain readable document text.",
}


def is_mime_type_supported(mime_type: str) -> Tuple[bool, Optional[str]]:
    """
    Checks if a document MIME type is readable and extractable.
    Returns (is_supported, explanation_if_unsupported).
    """
    if mime_type in SUPPORTED_MIME_TYPES:
        return True, None
    reason = UNSUPPORTED_MIME_REASONS.get(
        mime_type,
        f"Format '{mime_type}' is not currently supported for text extraction. Supported formats: Google Docs, PDF, TXT, MD, CSV, DOCX."
    )
    return False, reason


def _request_with_retry(method: str, url: str, **kwargs) -> httpx.Response:
    """
    Executes an HTTP request with automatic retry logic (up to 3 attempts)
    to handle transient SSL handshake issues or socket resets gracefully.
    """
    timeout = kwargs.pop("timeout", 30.0)
    follow_redirects = kwargs.pop("follow_redirects", False)
    last_err = None

    for attempt in range(1, 4):
        try:
            with httpx.Client(verify=False, timeout=timeout, follow_redirects=follow_redirects) as client:
                resp = client.request(method, url, **kwargs)
                return resp
        except Exception as e:
            last_err = e
            logger.warning(f"Google Drive request attempt {attempt}/3 failed ({type(e).__name__}: {e}). Retrying...")
            time.sleep(0.5)

    raise RuntimeError(f"Google Drive request to {url} failed after 3 attempts: {last_err}")


class ReadOnlyDriveClient:
    """
    Client for interacting with Google Drive exclusively in read-only mode.
    Guarantees structural absence of any mutating API calls.
    Uses httpx with SSL-safe options and retry resiliency.
    """

    def __init__(self, credentials: Credentials):
        self.credentials = credentials

    def _get_headers(self) -> Dict[str, str]:
        token = self.credentials.token
        if not token:
            raise RuntimeError("Missing access token in Google credentials.")
        return {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        }

    def list_documents(
        self,
        page_size: int = 20,
        page_token: Optional[str] = None
    ) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        """
        Lists files from Google Drive ordered by modifiedTime descending.
        Excludes trashed files and folders.
        Handles pagination correctly.
        """
        query = "trashed = false and mimeType != 'application/vnd.google-apps.folder'"
        params = {
            "q": query,
            "orderBy": "modifiedTime desc",
            "pageSize": min(page_size, 100),
            "fields": "nextPageToken, files(id, name, mimeType, modifiedTime, size, webViewLink, trashed)",
        }
        if page_token:
            params["pageToken"] = page_token

        resp = _request_with_retry(
            "GET",
            f"{DRIVE_API_BASE}/files",
            params=params,
            headers=self._get_headers(),
            timeout=30.0,
        )
        if resp.status_code != 200:
            logger.error(f"Google Drive list_documents failed ({resp.status_code}): {resp.text}")
            raise RuntimeError(f"Google Drive API error ({resp.status_code}): {resp.text}")

        data = resp.json()
        files = data.get("files", [])
        next_token = data.get("nextPageToken")
        return files, next_token

    def get_most_recent_document(self) -> Optional[Dict[str, Any]]:
        """
        Retrieves the single most recently modified file from Google Drive.
        Returns None if the user's Drive is empty.
        """
        files, _ = self.list_documents(page_size=1)
        if not files:
            return None
        return files[0]

    def get_most_recent_supported_document(self, max_search: int = 20) -> Optional[Dict[str, Any]]:
        """
        Scans recently modified files in order and returns the first one with a supported document format.
        If no supported documents exist, returns None.
        """
        files, _ = self.list_documents(page_size=max_search)
        for f in files:
            supported, _ = is_mime_type_supported(f.get("mimeType", ""))
            if supported:
                return f
        return None

    def get_file_metadata(self, file_id: str) -> Dict[str, Any]:
        """
        Fetches file metadata for a specific document ID.
        """
        params = {
            "fields": "id, name, mimeType, modifiedTime, size, webViewLink, trashed"
        }
        resp = _request_with_retry(
            "GET",
            f"{DRIVE_API_BASE}/files/{file_id}",
            params=params,
            headers=self._get_headers(),
            timeout=30.0,
        )
        if resp.status_code != 200:
            logger.error(f"Google Drive get_file_metadata failed for {file_id} ({resp.status_code}): {resp.text}")
            raise RuntimeError(f"Google Drive API error ({resp.status_code}): {resp.text}")

        return resp.json()

    def download_file_bytes(self, file_id: str, mime_type: str) -> bytes:
        """
        Reads document content bytes using Google Drive export or media download.
        For Google Docs: uses /files/{file_id}/export?mimeType=text/plain
        For binary/plain files: uses /files/{file_id}?alt=media
        """
        headers = {"Authorization": f"Bearer {self.credentials.token}"}

        if mime_type == "application/vnd.google-apps.document":
            resp = _request_with_retry(
                "GET",
                f"{DRIVE_API_BASE}/files/{file_id}/export",
                params={"mimeType": "text/plain"},
                headers=headers,
                timeout=60.0,
                follow_redirects=True,
            )
        else:
            resp = _request_with_retry(
                "GET",
                f"{DRIVE_API_BASE}/files/{file_id}",
                params={"alt": "media"},
                headers=headers,
                timeout=60.0,
                follow_redirects=True,
            )

        if resp.status_code != 200:
            logger.error(f"Google Drive download failed for {file_id} ({mime_type}) ({resp.status_code}): {resp.text}")
            raise RuntimeError(f"Google Drive download failed ({resp.status_code}): {resp.text}")

        return resp.content

    # STRUCTURAL SAFETY GUARANTEE:
    # This class does NOT implement create, update, delete, patch, copy, or permissions.create.
    # Any attempt to call write operations will raise AttributeError.
