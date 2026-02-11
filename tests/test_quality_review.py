"""Tests for DocumentQualityReviewer (Plan 14-05, Task 1).

Verifies audience leakage detection, air gap violation detection,
placeholder text detection, confidential marking correctness,
clean document pass, and batch review aggregation.

Uses python-docx to create small mock DOCX files with targeted content.
"""

import tempfile
from pathlib import Path

import pytest
from docx import Document

from src.packets.doc_types import DOC_A, DOC_B, DOC_C, DOC_D
from src.packets.quality_review import (
    BatchReviewResult,
    DocumentQualityReviewer,
    ReviewIssue,
    ReviewResult,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _create_mock_docx(tmp_dir: Path, filename: str, paragraphs: list[str]) -> Path:
    """Create a mock DOCX file with given paragraph text.

    Args:
        tmp_dir: Directory to save the DOCX file.
        filename: Name of the DOCX file.
        paragraphs: List of paragraph strings to add to the document.

    Returns:
        Path to the created DOCX file.
    """
    doc = Document()
    for text in paragraphs:
        doc.add_paragraph(text)
    path = tmp_dir / filename
    doc.save(str(path))
    return path


def _make_clean_paragraphs(count: int = 25) -> list[str]:
    """Generate a list of clean, factual paragraphs for a passing doc.

    Includes Executive Summary header and factual content only. No internal
    strategy terms, no air gap violations, no placeholder text.

    Args:
        count: Number of paragraphs to generate.

    Returns:
        List of paragraph strings.
    """
    paras = [
        "Executive Summary",
        "This document provides an overview of federal funding opportunities "
        "relevant to climate resilience programs.",
        "The Tribe has a strong history of federal partnerships for disaster "
        "preparedness and environmental protection.",
        "Federal programs include FEMA BRIC, EPA Water Infrastructure, and "
        "USDA Conservation Reserve programs.",
        "The congressional delegation has shown consistent support for "
        "Tribal climate adaptation funding.",
        "Recent federal awards demonstrate ongoing investment in Tribal "
        "community resilience infrastructure.",
        "Climate hazard analysis indicates elevated risk from wildfire, "
        "flooding, and extreme heat events.",
        "Recommended policy priorities focus on multi-hazard planning and "
        "capacity building initiatives.",
        "Cross-agency coordination opportunities exist between FEMA, EPA, "
        "and DOI programs.",
        "The FY26 appropriations cycle presents opportunities for increased "
        "funding allocations.",
    ]
    # Pad to requested count with generic factual content
    while len(paras) < count:
        paras.append(
            f"Additional program analysis (paragraph {len(paras) + 1}) "
            f"covers federal funding patterns and grant eligibility."
        )
    return paras[:count]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestAudienceLeakageDetection:
    """Verify detection of internal-only content in congressional documents."""

    def test_detects_audience_leakage_in_congressional_doc(self, tmp_path):
        """Congressional doc (DOC_B) with 'Strategic Leverage' triggers critical issue."""
        paras = _make_clean_paragraphs(25)
        paras.append("We should use Strategic Leverage to advance our position.")
        path = _create_mock_docx(tmp_path, "test_leak.docx", paras)

        reviewer = DocumentQualityReviewer()
        result = reviewer.review_document(path, DOC_B)

        leakage_issues = [
            i for i in result.issues if i.category == "audience_leakage"
        ]
        assert len(leakage_issues) >= 1
        assert leakage_issues[0].severity == "critical"
        assert not result.passed

    def test_no_false_positive_for_internal_doc(self, tmp_path):
        """Internal doc (DOC_A) with same 'Strategic Leverage' text has no audience leakage."""
        paras = _make_clean_paragraphs(25)
        paras.append("We should use Strategic Leverage to advance our position.")
        # Add CONFIDENTIAL marking since DOC_A expects it
        paras.append("CONFIDENTIAL - For Internal Use Only")
        path = _create_mock_docx(tmp_path, "test_internal.docx", paras)

        reviewer = DocumentQualityReviewer()
        result = reviewer.review_document(path, DOC_A)

        leakage_issues = [
            i for i in result.issues if i.category == "audience_leakage"
        ]
        assert len(leakage_issues) == 0

    def test_detects_multiple_leakage_patterns(self, tmp_path):
        """Congressional doc with multiple forbidden patterns detects all of them."""
        paras = _make_clean_paragraphs(25)
        paras.append("The leverage point is clear for this lobbying effort.")
        paras.append("We need a messaging framework for the window of opportunity.")
        path = _create_mock_docx(tmp_path, "test_multi_leak.docx", paras)

        reviewer = DocumentQualityReviewer()
        result = reviewer.review_document(path, DOC_B)

        leakage_issues = [
            i for i in result.issues if i.category == "audience_leakage"
        ]
        # Should detect at least: leverage point, lobbying, messaging framework, window of opportunity
        assert len(leakage_issues) >= 4
        assert not result.passed

    def test_regional_congressional_leakage_detected(self, tmp_path):
        """Regional congressional doc (DOC_D) also detects audience leakage."""
        paras = _make_clean_paragraphs(25)
        paras.append("This is our pressure point strategy.")
        path = _create_mock_docx(tmp_path, "test_regional_leak.docx", paras)

        reviewer = DocumentQualityReviewer()
        result = reviewer.review_document(path, DOC_D)

        leakage_issues = [
            i for i in result.issues if i.category == "audience_leakage"
        ]
        assert len(leakage_issues) >= 1
        assert not result.passed


class TestAirGapViolations:
    """Verify detection of organizational/tool names in any document."""

    def test_detects_air_gap_violation(self, tmp_path):
        """Document with 'TCR Policy Scanner' triggers air gap critical issue."""
        paras = _make_clean_paragraphs(25)
        paras.append("Data from TCR Policy Scanner analysis.")
        # Add CONFIDENTIAL for DOC_A
        paras.append("CONFIDENTIAL")
        path = _create_mock_docx(tmp_path, "test_airgap.docx", paras)

        reviewer = DocumentQualityReviewer()
        result = reviewer.review_document(path, DOC_A)

        airgap_issues = [
            i for i in result.issues if i.category == "air_gap"
        ]
        assert len(airgap_issues) >= 1
        assert airgap_issues[0].severity == "critical"
        assert not result.passed

    def test_detects_atni_air_gap(self, tmp_path):
        """Document with 'ATNI' triggers air gap violation."""
        paras = _make_clean_paragraphs(25)
        paras.append("Coordinated with ATNI policy team.")
        paras.append("CONFIDENTIAL")
        path = _create_mock_docx(tmp_path, "test_atni.docx", paras)

        reviewer = DocumentQualityReviewer()
        result = reviewer.review_document(path, DOC_A)

        airgap_issues = [
            i for i in result.issues if i.category == "air_gap"
        ]
        assert len(airgap_issues) >= 1
        assert not result.passed

    def test_air_gap_checked_for_all_doc_types(self, tmp_path):
        """Air gap violations are detected regardless of document type."""
        for dtc in [DOC_A, DOC_B, DOC_C, DOC_D]:
            paras = _make_clean_paragraphs(25)
            paras.append("Generated by automated pipeline.")
            if dtc.confidential:
                paras.append("CONFIDENTIAL")
            path = _create_mock_docx(
                tmp_path, f"test_airgap_{dtc.doc_type}.docx", paras
            )

            reviewer = DocumentQualityReviewer()
            result = reviewer.review_document(path, dtc)

            airgap_issues = [
                i for i in result.issues if i.category == "air_gap"
            ]
            assert len(airgap_issues) >= 1, (
                f"Air gap not detected for DOC_{dtc.doc_type}"
            )


class TestPlaceholderDetection:
    """Verify detection of placeholder text in documents."""

    def test_detects_placeholder(self, tmp_path):
        """Document with 'data pending' triggers placeholder warning."""
        paras = _make_clean_paragraphs(25)
        paras.append("Award information: data pending for this Tribe.")
        paras.append("CONFIDENTIAL")
        path = _create_mock_docx(tmp_path, "test_placeholder.docx", paras)

        reviewer = DocumentQualityReviewer()
        result = reviewer.review_document(path, DOC_A)

        placeholder_issues = [
            i for i in result.issues if i.category == "placeholder"
        ]
        assert len(placeholder_issues) >= 1
        assert placeholder_issues[0].severity == "warning"
        # Placeholders are warnings, not critical -- doc still passes
        assert result.passed

    def test_detects_tbd_placeholder(self, tmp_path):
        """Document with 'TBD' triggers placeholder warning."""
        paras = _make_clean_paragraphs(25)
        paras.append("Congressional district: TBD")
        paras.append("CONFIDENTIAL")
        path = _create_mock_docx(tmp_path, "test_tbd.docx", paras)

        reviewer = DocumentQualityReviewer()
        result = reviewer.review_document(path, DOC_A)

        placeholder_issues = [
            i for i in result.issues if i.category == "placeholder"
        ]
        assert len(placeholder_issues) >= 1


class TestCleanDocPasses:
    """Verify that a well-formed document passes all checks."""

    def test_clean_doc_passes_as_congressional(self, tmp_path):
        """Clean document reviewed as DOC_B passes all checks."""
        paras = _make_clean_paragraphs(25)
        path = _create_mock_docx(tmp_path, "test_clean.docx", paras)

        reviewer = DocumentQualityReviewer()
        result = reviewer.review_document(path, DOC_B)

        assert result.passed
        critical_issues = [
            i for i in result.issues if i.severity == "critical"
        ]
        assert len(critical_issues) == 0

    def test_clean_doc_passes_as_internal(self, tmp_path):
        """Clean internal document with CONFIDENTIAL marking passes."""
        paras = _make_clean_paragraphs(25)
        paras.append("CONFIDENTIAL - For Internal Use Only")
        path = _create_mock_docx(tmp_path, "test_clean_internal.docx", paras)

        reviewer = DocumentQualityReviewer()
        result = reviewer.review_document(path, DOC_A)

        assert result.passed


class TestConfidentialCorrectness:
    """Verify confidential marking checks."""

    def test_internal_doc_missing_confidential(self, tmp_path):
        """Internal doc (DOC_A) without CONFIDENTIAL marking gets warning."""
        paras = _make_clean_paragraphs(25)
        # No CONFIDENTIAL marking
        path = _create_mock_docx(
            tmp_path, "test_no_conf.docx", paras
        )

        reviewer = DocumentQualityReviewer()
        result = reviewer.review_document(path, DOC_A)

        formatting_issues = [
            i for i in result.issues if i.category == "formatting"
        ]
        assert len(formatting_issues) >= 1
        assert "CONFIDENTIAL" in formatting_issues[0].message

    def test_congressional_doc_with_confidential(self, tmp_path):
        """Congressional doc (DOC_B) with CONFIDENTIAL gets critical issue."""
        paras = _make_clean_paragraphs(25)
        paras.append("CONFIDENTIAL - Do not distribute.")
        path = _create_mock_docx(
            tmp_path, "test_bad_conf.docx", paras
        )

        reviewer = DocumentQualityReviewer()
        result = reviewer.review_document(path, DOC_B)

        formatting_issues = [
            i for i in result.issues if i.category == "formatting"
        ]
        assert len(formatting_issues) >= 1
        assert formatting_issues[0].severity == "critical"
        assert not result.passed

    def test_congressional_doc_with_for_congressional_not_flagged(self, tmp_path):
        """Congressional doc with 'For Congressional Office Use' is not flagged.

        The footer 'For Congressional Office Use' contains 'confidential'
        as a substring of 'congressional'. This should NOT trigger a
        false positive.
        """
        paras = _make_clean_paragraphs(25)
        paras.append("For Congressional Office Use")
        path = _create_mock_docx(
            tmp_path, "test_footer.docx", paras
        )

        reviewer = DocumentQualityReviewer()
        result = reviewer.review_document(path, DOC_B)

        formatting_issues = [
            i for i in result.issues if i.category == "formatting"
        ]
        assert len(formatting_issues) == 0


class TestContentChecks:
    """Verify minimum content and executive summary checks."""

    def test_short_doc_gets_warning(self, tmp_path):
        """Document with fewer than 20 paragraphs gets content warning."""
        paras = ["Executive Summary", "Short content."]
        path = _create_mock_docx(tmp_path, "test_short.docx", paras)

        reviewer = DocumentQualityReviewer()
        result = reviewer.review_document(path, DOC_B)

        content_issues = [
            i
            for i in result.issues
            if i.category == "content" and "paragraph" in i.message.lower()
        ]
        assert len(content_issues) >= 1

    def test_missing_executive_summary(self, tmp_path):
        """Document without Executive Summary header gets content warning."""
        paras = ["Introduction"] + [
            f"Paragraph {i} of content." for i in range(25)
        ]
        path = _create_mock_docx(tmp_path, "test_no_exec.docx", paras)

        reviewer = DocumentQualityReviewer()
        result = reviewer.review_document(path, DOC_B)

        exec_issues = [
            i
            for i in result.issues
            if i.category == "content" and "executive summary" in i.message.lower()
        ]
        assert len(exec_issues) >= 1


class TestBatchReview:
    """Verify batch review aggregation."""

    def test_batch_review_aggregation(self, tmp_path):
        """Batch review of multiple docs produces correct aggregated totals."""
        # Create directory structure
        internal_dir = tmp_path / "internal"
        internal_dir.mkdir()
        congressional_dir = tmp_path / "congressional"
        congressional_dir.mkdir()

        # Create a passing internal doc (DOC_A)
        paras_good = _make_clean_paragraphs(25)
        paras_good.append("CONFIDENTIAL - For Internal Use Only")
        _create_mock_docx(internal_dir, "tribe_a_internal_strategy_fy26.docx", paras_good)

        # Create a passing congressional doc (DOC_B)
        paras_clean = _make_clean_paragraphs(25)
        _create_mock_docx(congressional_dir, "tribe_a_congressional_overview_fy26.docx", paras_clean)

        # Create a failing congressional doc (DOC_B) -- has audience leakage
        paras_bad = _make_clean_paragraphs(25)
        paras_bad.append("We need to use strategic leverage for this lobbying effort.")
        _create_mock_docx(congressional_dir, "tribe_b_congressional_overview_fy26.docx", paras_bad)

        reviewer = DocumentQualityReviewer()
        batch_result = reviewer.review_batch(tmp_path)

        assert batch_result.total_reviewed == 3
        assert batch_result.total_passed >= 2
        assert batch_result.total_failed >= 1
        assert batch_result.critical_issues >= 1
        assert "audience_leakage" in batch_result.issues_by_category

    def test_batch_review_empty_directory(self, tmp_path):
        """Batch review of empty directory produces zero totals."""
        reviewer = DocumentQualityReviewer()
        batch_result = reviewer.review_batch(tmp_path)

        assert batch_result.total_reviewed == 0
        assert batch_result.total_passed == 0
        assert batch_result.total_failed == 0


class TestReportGeneration:
    """Verify markdown report generation."""

    def test_generate_report_contains_summary(self, tmp_path):
        """Generated report contains summary section with pass rate."""
        # Create a simple batch result
        internal_dir = tmp_path / "internal"
        internal_dir.mkdir()
        paras = _make_clean_paragraphs(25)
        paras.append("CONFIDENTIAL")
        _create_mock_docx(internal_dir, "test.docx", paras)

        reviewer = DocumentQualityReviewer()
        batch_result = reviewer.review_batch(tmp_path)
        report = reviewer.generate_report(batch_result)

        assert "# Document Quality Review Report" in report
        assert "## Summary" in report
        assert "Pass Rate" in report

    def test_generate_report_zero_docs(self):
        """Report for zero documents still produces valid markdown."""
        batch_result = BatchReviewResult(
            total_reviewed=0,
            total_passed=0,
            total_failed=0,
            critical_issues=0,
            warning_issues=0,
            issues_by_category={},
            failed_documents=[],
        )
        reviewer = DocumentQualityReviewer()
        report = reviewer.generate_report(batch_result)

        assert "# Document Quality Review Report" in report
        assert "Total Reviewed:** 0" in report
