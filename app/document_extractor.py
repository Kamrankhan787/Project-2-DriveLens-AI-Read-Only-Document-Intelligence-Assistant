"""
DriveLens AI - Document Content Extraction
Extracts readable plain text from various Google Drive file formats safely.
"""
import io
import logging
from typing import Optional
from app.drive_client import is_mime_type_supported

logger = logging.getLogger("drivelens.extractor")

# Default safety limit for AI context processing (prevents token overflow & huge costs)
MAX_DOCUMENT_CHARACTERS = 50_000


class DocumentExtractionError(Exception):
    """Raised when text cannot be extracted from a document."""
    pass


def extract_document_text(
    content_bytes: bytes,
    mime_type: str,
    max_chars: int = MAX_DOCUMENT_CHARACTERS
) -> str:
    """
    Extracts plain text string from raw document bytes based on MIME type.
    Handles Google Docs export, plain text, Markdown, CSV, PDF, and Word documents.
    """
    if not content_bytes:
        return ""

    is_supported, unsupported_reason = is_mime_type_supported(mime_type)
    if not is_supported:
        raise DocumentExtractionError(unsupported_reason or f"Unsupported MIME type: {mime_type}")

    extracted_text = ""

    try:
        if mime_type == "application/vnd.google-apps.document":
            # Exported as text/plain from Google Docs API
            extracted_text = content_bytes.decode("utf-8", errors="replace")

        elif mime_type in ("text/plain", "text/markdown", "text/csv", "text/tab-separated-values", "application/json"):
            # Plain textual formats
            try:
                extracted_text = content_bytes.decode("utf-8")
            except UnicodeDecodeError:
                extracted_text = content_bytes.decode("latin-1", errors="replace")

        elif mime_type == "application/pdf":
            # PDF extraction using pypdf
            try:
                import pypdf
                pdf_reader = pypdf.PdfReader(io.BytesIO(content_bytes))
                pages_text = []
                for idx, page in enumerate(pdf_reader.pages):
                    page_content = page.extract_text()
                    if page_content:
                        pages_text.append(page_content)
                extracted_text = "\n\n".join(pages_text)
            except Exception as e:
                logger.error(f"Failed to parse PDF content: {e}")
                raise DocumentExtractionError(f"PDF extraction error: {str(e)}")

        elif mime_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            # Word .docx extraction using python-docx
            try:
                import docx
                doc = docx.Document(io.BytesIO(content_bytes))
                paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
                extracted_text = "\n\n".join(paragraphs)
            except Exception as e:
                logger.error(f"Failed to parse DOCX content: {e}")
                raise DocumentExtractionError(f"DOCX extraction error: {str(e)}")

        else:
            raise DocumentExtractionError(f"Handler missing for supported MIME type '{mime_type}'.")

    except DocumentExtractionError:
        raise
    except Exception as e:
        logger.error(f"Unexpected error extracting text for mime {mime_type}: {e}")
        raise DocumentExtractionError(f"Could not extract text from document: {str(e)}")

    extracted_text = extracted_text.strip()

    # Safety truncation for very large documents
    if len(extracted_text) > max_chars:
        logger.info(f"Document text length ({len(extracted_text)}) exceeds limit ({max_chars}); truncating.")
        extracted_text = (
            extracted_text[:max_chars]
            + f"\n\n[DriveLens Notice: Document content truncated to first {max_chars} characters for safe analysis.]"
        )

    return extracted_text
