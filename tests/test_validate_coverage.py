"""Tests for scripts/validate_coverage.py coverage validation logic."""

import json
from pathlib import Path

from scripts.validate_coverage import (
    analyze_awards,
    analyze_congressional,
    analyze_cross_source,
    analyze_documents,
    analyze_hazards,
    analyze_registry,
    build_coverage_report,
    format_console_report,
    format_markdown_report,
)


class TestAwardCoverageCounting:
    """Test award cache file analysis."""

    def test_counts_populated_and_zero_files(self, tmp_path: Path) -> None:
        """Files with awards counted as populated; empty ones as zero."""
        # Populated file
        (tmp_path / "epa_001.json").write_text(
            json.dumps({
                "tribe_id": "epa_001",
                "awards": [{"award_id": "A1", "obligation": 100}],
                "total_obligation": 100,
                "award_count": 1,
            }),
            encoding="utf-8",
        )
        # Zero file
        (tmp_path / "epa_002.json").write_text(
            json.dumps({
                "tribe_id": "epa_002",
                "awards": [],
                "total_obligation": 0,
                "award_count": 0,
            }),
            encoding="utf-8",
        )
        result = analyze_awards(tmp_path)
        assert result["total"] == 2
        assert result["populated"] == 1
        assert result["zero_ids"] == ["epa_002"]
        assert result["coverage_pct"] == 50.0

    def test_empty_directory(self, tmp_path: Path) -> None:
        """Empty directory returns zero counts."""
        result = analyze_awards(tmp_path)
        assert result["total"] == 0
        assert result["populated"] == 0
        assert result["coverage_pct"] == 0.0

    def test_nonexistent_directory(self, tmp_path: Path) -> None:
        """Non-existent directory returns zero counts."""
        result = analyze_awards(tmp_path / "does_not_exist")
        assert result["total"] == 0

    def test_total_obligation_nonzero_counts_as_populated(self, tmp_path: Path) -> None:
        """File with total_obligation > 0 but empty awards list is populated."""
        (tmp_path / "epa_003.json").write_text(
            json.dumps({
                "tribe_id": "epa_003",
                "awards": [],
                "total_obligation": 500,
                "award_count": 0,
            }),
            encoding="utf-8",
        )
        result = analyze_awards(tmp_path)
        assert result["populated"] == 1


class TestHazardCoverageCounting:
    """Test hazard profile file analysis."""

    def test_counts_nri_and_usfs_separately(self, tmp_path: Path) -> None:
        """NRI and USFS are counted as separate coverage metrics."""
        # Has NRI but no USFS
        (tmp_path / "epa_001.json").write_text(
            json.dumps({
                "tribe_id": "epa_001",
                "sources": {
                    "fema_nri": {
                        "composite": {"risk_score": 55.0},
                    },
                    "usfs_wildfire": {},
                },
            }),
            encoding="utf-8",
        )
        # Has NRI and USFS
        (tmp_path / "epa_002.json").write_text(
            json.dumps({
                "tribe_id": "epa_002",
                "sources": {
                    "fema_nri": {
                        "composite": {"risk_score": 70.0},
                    },
                    "usfs_wildfire": {"risk_to_homes": 0.42},
                },
            }),
            encoding="utf-8",
        )
        # Zero NRI
        (tmp_path / "epa_003.json").write_text(
            json.dumps({
                "tribe_id": "epa_003",
                "sources": {
                    "fema_nri": {
                        "composite": {"risk_score": 0},
                    },
                },
            }),
            encoding="utf-8",
        )

        result = analyze_hazards(tmp_path)
        assert result["total"] == 3
        assert result["nri_populated"] == 2
        assert result["usfs_populated"] == 1
        assert result["zero_ids"] == ["epa_003"]
        assert result["coverage_pct"] == 66.7

    def test_nonexistent_directory(self, tmp_path: Path) -> None:
        """Non-existent directory returns zero counts."""
        result = analyze_hazards(tmp_path / "nope")
        assert result["total"] == 0


class TestCongressionalAnalysis:
    """Test congressional cache analysis."""

    def test_counts_delegations_with_members(self, tmp_path: Path) -> None:
        """Delegations with senators or reps counted as populated."""
        cache = {
            "metadata": {},
            "members": {},
            "committees": {},
            "delegations": {
                "epa_001": {
                    "senators": [{"name": "Sen A"}],
                    "representatives": [{"name": "Rep B"}],
                },
                "epa_002": {
                    "senators": [],
                    "representatives": [],
                },
                "epa_003": {
                    "senators": [{"name": "Sen C"}],
                    "representatives": [],
                },
            },
        }
        path = tmp_path / "congressional_cache.json"
        path.write_text(json.dumps(cache), encoding="utf-8")

        result = analyze_congressional(path)
        assert result["total"] == 3
        assert result["populated"] == 2
        assert result["unmapped_ids"] == ["epa_002"]
        assert result["coverage_pct"] == 66.7

    def test_missing_file(self, tmp_path: Path) -> None:
        """Missing file returns zero counts."""
        result = analyze_congressional(tmp_path / "missing.json")
        assert result["total"] == 0

    def test_total_tribes_universe_denominator(self, tmp_path: Path) -> None:
        """When total_tribes provided, coverage_pct uses that denominator."""
        cache = {
            "delegations": {
                "epa_001": {"senators": [{"name": "S"}], "representatives": []},
            },
        }
        path = tmp_path / "congressional_cache.json"
        path.write_text(json.dumps(cache), encoding="utf-8")

        result = analyze_congressional(path, total_tribes=10)
        assert result["total"] == 10
        assert result["populated"] == 1
        assert result["coverage_pct"] == 10.0


class TestRegistryAnalysis:
    """Test tribal registry analysis."""

    def test_counts_bia_and_states(self, tmp_path: Path) -> None:
        """BIA codes (non-TBD) and states are counted correctly."""
        registry = {
            "metadata": {},
            "tribes": [
                {"tribe_id": "epa_001", "bia_code": "820", "states": ["OK"]},
                {"tribe_id": "epa_002", "bia_code": "TBD", "states": ["CA"]},
                {"tribe_id": "epa_003", "bia_code": "", "states": []},
            ],
        }
        path = tmp_path / "tribal_registry.json"
        path.write_text(json.dumps(registry), encoding="utf-8")

        result = analyze_registry(path)
        assert result["total"] == 3
        assert result["with_bia"] == 1
        assert result["with_states"] == 2
        assert result["coverage_pct"] == 100.0

    def test_missing_file(self, tmp_path: Path) -> None:
        """Missing file returns zero counts."""
        result = analyze_registry(tmp_path / "nope.json")
        assert result["total"] == 0


class TestDocumentAnalysis:
    """Test document generation counting."""

    def test_counts_files_in_subdirectories(self, tmp_path: Path) -> None:
        """Counts DOCX files in the four expected subdirectories."""
        (tmp_path / "internal").mkdir()
        (tmp_path / "congressional").mkdir()
        (tmp_path / "regional" / "internal").mkdir(parents=True)
        (tmp_path / "regional" / "congressional").mkdir(parents=True)

        (tmp_path / "internal" / "epa_001.docx").write_text("doc")
        (tmp_path / "internal" / "epa_002.docx").write_text("doc")
        (tmp_path / "congressional" / "epa_001.docx").write_text("doc")
        (tmp_path / "congressional" / "epa_003.docx").write_text("doc")
        (tmp_path / "regional" / "internal" / "pacific_nw.docx").write_text("doc")
        (tmp_path / "regional" / "congressional" / "pacific_nw.docx").write_text("doc")

        result = analyze_documents(tmp_path)
        assert result["doc_a"] == 2
        assert result["doc_b"] == 2
        assert result["doc_c"] == 1
        assert result["doc_d"] == 1
        assert result["complete_packets"] == 1  # epa_001 has both A+B
        assert result["doc_b_only"] == 1  # epa_003 has B but no A

    def test_empty_directory(self, tmp_path: Path) -> None:
        """Empty directory returns zero counts."""
        result = analyze_documents(tmp_path)
        assert result["doc_a"] == 0
        assert result["doc_b"] == 0
        assert result["complete_packets"] == 0


class TestCrossSourceCompleteness:
    """Test cross-source completeness calculation."""

    def test_complete_partial_and_none(self, tmp_path: Path) -> None:
        """Correctly categorizes Tribes by data availability."""
        award_dir = tmp_path / "awards"
        hazard_dir = tmp_path / "hazards"
        award_dir.mkdir()
        hazard_dir.mkdir()

        # epa_001: has awards, hazards, delegation -> complete
        (award_dir / "epa_001.json").write_text(
            json.dumps({"awards": [{"a": 1}], "total_obligation": 100}),
            encoding="utf-8",
        )
        (hazard_dir / "epa_001.json").write_text(
            json.dumps({"sources": {"fema_nri": {"composite": {"risk_score": 50}}}}),
            encoding="utf-8",
        )

        # epa_002: has awards, no hazards, has delegation -> partial
        (award_dir / "epa_002.json").write_text(
            json.dumps({"awards": [{"a": 2}], "total_obligation": 200}),
            encoding="utf-8",
        )
        (hazard_dir / "epa_002.json").write_text(
            json.dumps({"sources": {"fema_nri": {"composite": {"risk_score": 0}}}}),
            encoding="utf-8",
        )

        # epa_003: no awards, no hazards, no delegation -> none
        (award_dir / "epa_003.json").write_text(
            json.dumps({"awards": [], "total_obligation": 0}),
            encoding="utf-8",
        )
        (hazard_dir / "epa_003.json").write_text(
            json.dumps({"sources": {"fema_nri": {"composite": {"risk_score": 0}}}}),
            encoding="utf-8",
        )

        # Congressional cache with delegations for epa_001 and epa_002
        cong_path = tmp_path / "congressional_cache.json"
        cong_path.write_text(
            json.dumps({
                "delegations": {
                    "epa_001": {"senators": [{"name": "S"}], "representatives": []},
                    "epa_002": {"senators": [{"name": "S"}], "representatives": []},
                }
            }),
            encoding="utf-8",
        )

        result = analyze_cross_source(award_dir, hazard_dir, cong_path)
        assert result["complete"] == 1  # epa_001
        assert result["partial_award_deleg"] == 1  # epa_002
        assert result["none"] == 1  # epa_003
        assert result["total_tribes"] == 3


class TestJsonOutputFormat:
    """Test JSON output structure."""

    def test_report_has_all_sections(self, tmp_path: Path) -> None:
        """build_coverage_report returns dict with all expected top-level keys."""
        report = build_coverage_report(
            award_dir=tmp_path / "awards",
            hazard_dir=tmp_path / "hazards",
            congressional_path=tmp_path / "cong.json",
            registry_path=tmp_path / "reg.json",
            packets_dir=tmp_path / "packets",
        )
        assert "generated_at" in report
        assert "version" in report
        assert "awards" in report
        assert "hazards" in report
        assert "congressional" in report
        assert "registry" in report
        assert "documents" in report
        assert "cross_source" in report

    def test_report_is_json_serializable(self, tmp_path: Path) -> None:
        """The full report dict is JSON-serializable."""
        report = build_coverage_report(
            award_dir=tmp_path,
            hazard_dir=tmp_path,
            congressional_path=tmp_path / "c.json",
            registry_path=tmp_path / "r.json",
            packets_dir=tmp_path,
        )
        serialized = json.dumps(report)
        assert len(serialized) > 0


class TestMarkdownOutputFormat:
    """Test markdown report formatting."""

    def test_markdown_has_headers_and_tables(self, tmp_path: Path) -> None:
        """Markdown output contains expected headers and table formatting."""
        report = build_coverage_report(
            award_dir=tmp_path,
            hazard_dir=tmp_path,
            congressional_path=tmp_path / "c.json",
            registry_path=tmp_path / "r.json",
            packets_dir=tmp_path,
        )
        md = format_markdown_report(report)
        assert "# Data Coverage Report v1.2" in md
        assert "## Data Sources" in md
        assert "## Document Generation" in md
        assert "## Cross-Source Completeness" in md
        assert "## Coverage Gaps" in md
        assert "|" in md  # Tables present

    def test_console_report_has_sections(self, tmp_path: Path) -> None:
        """Console output contains expected section headers."""
        report = build_coverage_report(
            award_dir=tmp_path,
            hazard_dir=tmp_path,
            congressional_path=tmp_path / "c.json",
            registry_path=tmp_path / "r.json",
            packets_dir=tmp_path,
        )
        console = format_console_report(report)
        assert "Data Sources:" in console
        assert "Document Generation:" in console
        assert "Completeness:" in console
