"""
DriveLens AI - Pydantic Request & Response Schemas
"""
from typing import List, Optional
from pydantic import BaseModel, Field


class AuthStatus(BaseModel):
    is_authenticated: bool = Field(..., description="Whether user currently has valid Google credentials")
    user_email: Optional[str] = Field(None, description="Authorized Google account email (if available)")
    user_name: Optional[str] = Field(None, description="Authorized Google account display name")
    scope: Optional[str] = Field(None, description="Active OAuth scope")
    read_only_enforced: bool = Field(True, description="Always true, confirms read-only constraints")


class DocumentMetadata(BaseModel):
    id: str = Field(..., description="Google Drive file ID")
    name: str = Field(..., description="File title/name")
    mime_type: str = Field(..., description="MIME type of the document")
    modified_time: str = Field(..., description="ISO 8601 timestamp of last modification")
    size_bytes: Optional[int] = Field(None, description="File size in bytes if available")
    is_supported: bool = Field(..., description="Whether document content can be extracted")
    unsupported_reason: Optional[str] = Field(None, description="Reason if format cannot be read")
    web_view_link: Optional[str] = Field(None, description="View link in Google Drive")


class AnalysisResponse(BaseModel):
    document_id: str = Field(..., description="Google Drive file ID of the analyzed document")
    document_title: str = Field(..., description="Exact title of the analyzed document")
    mime_type: str = Field(..., description="MIME type of the document")
    last_modified: str = Field(..., description="Last modification timestamp of the document")
    key_facts: List[str] = Field(
        ...,
        description="Exactly three key evidence-based facts or numbers from the document (or explicitly identified shortages)",
    )
    one_line_summary: str = Field(
        ...,
        description="A concise, high-impact one-line summary grounded exclusively in document contents",
    )
    source_evidence: List[str] = Field(
        default_factory=list,
        description="Verbatim quotations or short extracts serving as direct evidence for each key fact",
    )
    limitations: List[str] = Field(
        default_factory=list,
        description="Document constraints, gaps in data, or scope boundary clarifications",
    )
    read_only_notice: str = Field(
        default="Retrieved via strictly read-only Google Drive API. No file modification, creation, or deletion capabilities exist.",
        description="Confirmation of read-only access guarantee",
    )


class AnalysisRequest(BaseModel):
    document_id: Optional[str] = Field(
        None,
        description="Specific document ID to analyze, or leave null to automatically select the most recently modified document",
    )


class RevokeResponse(BaseModel):
    status: str
    message: str


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
    code: Optional[str] = None
