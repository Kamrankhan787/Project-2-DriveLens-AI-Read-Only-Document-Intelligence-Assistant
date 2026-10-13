"""
Unit tests for ReadOnlyDriveClient.
Verifies read-only constraints, sorting by modifiedTime, pagination,
empty results handling, and absence of write methods.
Mocked responses used - live Google Drive access not required for unit tests.
"""
import pytest
from unittest.mock import MagicMock, patch
from googleapiclient.errors import HttpError
from app.drive_client import ReadOnlyDriveClient, is_mime_type_supported


def test_drive_client_strictly_has_no_write_methods():
    """
    STRUCTURAL SAFETY TEST:
    Ensures that ReadOnlyDriveClient exposes zero mutating methods.
    """
    mock_creds = MagicMock()
    with patch("app.drive_client.build"):
        client = ReadOnlyDriveClient(mock_creds)

    write_method_names = [
        "create", "upload", "delete", "update", "patch", "copy",
        "create_file", "delete_file", "update_file", "upload_file",
        "permissions_create", "permissions_delete"
    ]

    for method in write_method_names:
        assert not hasattr(client, method), f"Security violation: client has write method '{method}'!"


def test_list_documents_orders_by_modified_time_desc():
    """Verify list_documents specifies orderBy='modifiedTime desc' and excludes folders/trashed."""
    mock_creds = MagicMock()
    with patch("app.drive_client.build") as mock_build:
        mock_service = MagicMock()
        mock_build.return_value = mock_service

        mock_files_resource = mock_service.files.return_value
        mock_list_call = mock_files_resource.list.return_value
        mock_list_call.execute.return_value = {
            "files": [
                {
                    "id": "doc1",
                    "name": "Q3 Financial Report.docx",
                    "mimeType": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    "modifiedTime": "2026-10-12T14:30:00Z"
                },
                {
                    "id": "doc2",
                    "name": "Project Proposal.gdoc",
                    "mimeType": "application/vnd.google-apps.document",
                    "modifiedTime": "2026-10-10T10:00:00Z"
                }
            ],
            "nextPageToken": "token123"
        }

        client = ReadOnlyDriveClient(mock_creds)
        files, next_token = client.list_documents(page_size=10)

        # Assert correct query parameters passed to Google API
        mock_files_resource.list.assert_called_once()
        kwargs = mock_files_resource.list.call_args[1]
        assert "modifiedTime desc" in kwargs["orderBy"]
        assert "trashed = false" in kwargs["q"]
        assert kwargs["pageSize"] == 10
        assert len(files) == 2
        assert files[0]["id"] == "doc1"
        assert next_token == "token123"


def test_empty_drive_handling():
    """Verify empty drive returns empty list or None without error or fabrication."""
    mock_creds = MagicMock()
    with patch("app.drive_client.build") as mock_build:
        mock_service = MagicMock()
        mock_build.return_value = mock_service
        mock_service.files.return_value.list.return_value.execute.return_value = {
            "files": []
        }

        client = ReadOnlyDriveClient(mock_creds)
        recent = client.get_most_recent_document()
        assert recent is None

        supported = client.get_most_recent_supported_document()
        assert supported is None


def test_supported_mime_types():
    """Verify mime type detection correctly categorizes readable documents and explains unsupported files."""
    # Supported
    supported, _ = is_mime_type_supported("application/vnd.google-apps.document")
    assert supported is True
    supported, _ = is_mime_type_supported("text/plain")
    assert supported is True
    supported, _ = is_mime_type_supported("application/pdf")
    assert supported is True

    # Unsupported
    supported, reason = is_mime_type_supported("application/zip")
    assert supported is False
    assert "archive" in reason.lower()

    supported, reason = is_mime_type_supported("image/png")
    assert supported is False
    assert "image" in reason.lower()


def test_download_file_bytes_dispatches_proper_api():
    """Verify Google Docs uses export while binary/text uses get_media."""
    mock_creds = MagicMock()
    with patch("app.drive_client.build") as mock_build:
        mock_service = MagicMock()
        mock_build.return_value = mock_service

        client = ReadOnlyDriveClient(mock_creds)

        # Test Google Doc export
        mock_service.files.return_value.export.return_value.execute.return_value = b"Google Doc text"
        content = client.download_file_bytes("doc123", "application/vnd.google-apps.document")
        assert content == b"Google Doc text"
        mock_service.files.return_value.export.assert_called_with(fileId="doc123", mimeType="text/plain")

        # Test plain text get_media
        mock_service.files.return_value.get_media.return_value.execute.return_value = b"Plain file data"
        content2 = client.download_file_bytes("txt123", "text/plain")
        assert content2 == b"Plain file data"
        mock_service.files.return_value.get_media.assert_called_with(fileId="txt123")
