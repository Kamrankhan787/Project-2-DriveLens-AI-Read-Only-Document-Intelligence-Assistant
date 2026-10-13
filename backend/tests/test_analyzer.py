"""
Unit tests for DocumentAnalyzer using OpenAI SDK.
Verifies structured outputs, exactly 3 facts constraint,
handling of documents with insufficient facts (anti-hallucination),
and error handling.
Mocked responses used - live OpenAI API keys not required for unit tests.
"""
import pytest
from unittest.mock import MagicMock, patch
import openai
from app.analyzer import DocumentAnalyzer, ExtractedIntelligence
from app.schemas import AnalysisResponse


def test_analyzer_with_valid_openai_response():
    """Verify standard document intelligence analysis returns structured response with exactly 3 facts."""
    mock_intelligence = ExtractedIntelligence(
        key_facts=[
            "Total Q3 ARR reached $4.2M, representing a 28% year-over-year increase.",
            "Customer churn decreased to 1.4% following the new onboarding rollout.",
            "The enterprise tier accounted for 64% of total net new bookings."
        ],
        one_line_summary="Q3 demonstrated strong growth with ARR reaching $4.2M and enterprise bookings dominating new revenue.",
        source_evidence=[
            "ARR reached $4.2M (+28% YoY)",
            "Churn down to 1.4%",
            "Enterprise tier contributed 64% of net new bookings"
        ],
        limitations=[
            "Document does not report gross margins or operational expenses."
        ]
    )

    analyzer = DocumentAnalyzer(api_key="sk-test-key-12345")

    with patch("openai.OpenAI") as mock_openai_cls:
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client

        mock_choice = MagicMock()
        mock_choice.message.parsed = mock_intelligence
        mock_completion = MagicMock(choices=[mock_choice])
        mock_client.beta.chat.completions.parse.return_value = mock_completion

        res = analyzer.analyze_document(
            document_id="doc-123",
            document_title="Q3 Performance Review.gdoc",
            mime_type="application/vnd.google-apps.document",
            last_modified="2026-10-12T12:00:00Z",
            content_text="Q3 ARR reached $4.2M (+28% YoY). Churn decreased to 1.4%. Enterprise accounted for 64%."
        )

        assert isinstance(res, AnalysisResponse)
        assert res.document_id == "doc-123"
        assert res.document_title == "Q3 Performance Review.gdoc"
        assert len(res.key_facts) == 3
        assert "$4.2M" in res.key_facts[0]
        assert "ARR reaching $4.2M" in res.one_line_summary
        assert len(res.source_evidence) == 3
        assert len(res.limitations) == 1
        assert "read-only" in res.read_only_notice.lower()


def test_analyzer_insufficient_evidence_shortage_handling():
    """
    Verify anti-hallucination behavior:
    If a document only has 1 verifiable fact, the system fills remaining slots
    with explicit shortage notices instead of fabricating numbers.
    """
    mock_intelligence = ExtractedIntelligence(
        key_facts=[
            "The office will be closed on Friday, October 16th."
        ],
        one_line_summary="Office closure notification for October 16th.",
        source_evidence=["Office closed Friday Oct 16"],
        limitations=["Document contains only a single event notice."]
    )

    analyzer = DocumentAnalyzer(api_key="sk-test-key-12345")

    with patch("openai.OpenAI") as mock_openai_cls:
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client

        mock_choice = MagicMock()
        mock_choice.message.parsed = mock_intelligence
        mock_completion = MagicMock(choices=[mock_choice])
        mock_client.beta.chat.completions.parse.return_value = mock_completion

        res = analyzer.analyze_document(
            document_id="short-doc",
            document_title="Notice.txt",
            mime_type="text/plain",
            last_modified="2026-10-13T09:00:00Z",
            content_text="Notice: The office will be closed on Friday, October 16th."
        )

        assert len(res.key_facts) == 3
        assert res.key_facts[0] == "The office will be closed on Friday, October 16th."
        assert "Fact shortage" in res.key_facts[1]
        assert "Fact shortage" in res.key_facts[2]


def test_analyzer_empty_document_handling():
    """Verify empty document returns explicit shortage notice without calling OpenAI API."""
    analyzer = DocumentAnalyzer(api_key="sk-test-key")

    res = analyzer.analyze_document(
        document_id="empty-1",
        document_title="Empty Doc.txt",
        mime_type="text/plain",
        last_modified="2026-10-13T00:00:00Z",
        content_text=""
    )

    assert len(res.key_facts) == 3
    assert "empty" in res.key_facts[0].lower()
    assert "Fact shortage" in res.key_facts[1]
    assert "blank" in res.one_line_summary.lower()


def test_analyzer_api_error_handling():
    """Verify OpenAI API errors are raised as clear exceptions without leaking secrets."""
    analyzer = DocumentAnalyzer(api_key="sk-test-key")

    with patch("openai.OpenAI") as mock_openai_cls:
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_client.beta.chat.completions.parse.side_effect = openai.APIConnectionError(
            request=MagicMock(),
            message="Connection timed out"
        )

        with pytest.raises(RuntimeError) as exc_info:
            analyzer.analyze_document(
                document_id="err-doc",
                document_title="Sample.txt",
                mime_type="text/plain",
                last_modified="2026-10-13T00:00:00Z",
                content_text="Some valid content."
            )
        assert "OpenAI API analysis failed" in str(exc_info.value)
