"""
Unit tests for DocumentExtractor.
Verifies plain text decoding, Google Doc exported text handling,
unsupported format error handling, empty content, and size truncation.
"""
import pytest
from app.document_extractor import (
    extract_document_text,
    DocumentExtractionError,
    MAX_DOCUMENT_CHARACTERS,
)


def test_extract_google_doc_text():
    """Verify Google Docs text extraction from UTF-8 bytes."""
    sample_text = "Project DriveLens AI: Milestone 1 completed on Oct 12, 2026."
    raw_bytes = sample_text.encode("utf-8")
    result = extract_document_text(raw_bytes, "application/vnd.google-apps.document")
    assert result == sample_text


def test_extract_plain_text_and_markdown():
    """Verify plain text and markdown extraction."""
    md_content = "# Architecture\n- Security: Read-Only\n- Scope: drive.readonly"
    raw_bytes = md_content.encode("utf-8")
    result = extract_document_text(raw_bytes, "text/markdown")
    assert result == md_content


def test_extract_empty_document():
    """Verify empty document returns empty string without error."""
    result = extract_document_text(b"", "text/plain")
    assert result == ""
    result2 = extract_document_text(b"   \n  ", "text/plain")
    assert result2 == ""


def test_extract_unsupported_mime_type():
    """Verify unsupported MIME type raises DocumentExtractionError with descriptive explanation."""
    with pytest.raises(DocumentExtractionError) as exc_info:
        extract_document_text(b"PK\x03\x04...", "application/zip")
    assert "archive" in str(exc_info.value).lower()


def test_document_truncation_limit():
    """Verify excessively long documents are truncated with an informative notice."""
    huge_text = "A" * 60_000
    raw_bytes = huge_text.encode("utf-8")
    result = extract_document_text(raw_bytes, "text/plain", max_chars=1000)
    assert len(result) < 2000
    assert "[DriveLens Notice: Document content truncated" in result
    assert result.startswith("A" * 1000)
