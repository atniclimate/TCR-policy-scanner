"""Tests for batch and ad-hoc DOCX generation modes (Plan 08-03).

Tests the updated run_all_tribes() batch generation flow and verifies
run_single_tribe() produces a full DOCX document (OPS-02 verification).

All tests use tmp_path fixtures with mock data -- no network or real
data files required.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_json(path: Path, data) -> None:
    """Write data as JSON to the given path, creating parent dirs."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f)


# ---------------------------------------------------------------------------
# Mock data builders (reused patterns from test_docx_integration.py)
# ---------------------------------------------------------------------------

def _mock_programs() -> list[dict]:
    """Return a list of 4 mock programs (2 critical, 2 high)."""
    return [
        {
            "id": "bia_tcr",
            "name": "BIA Tribal Climate Resilience",
            "agency": "Bureau of Indian Affairs",
            "federal_home": "DOI / BIA",
            "priority": "critical",
            "access_type": "direct_service",
            "funding_type": "Discretionary",
            "cfda": "15.156",
            "ci_status": "AT_RISK",
            "ci_determination": "FY26 budget uncertainty.",
            "description": "Annual awards to Tribes for climate adaptation planning.",
            "advocacy_lever": "Increase TCR funding to $50M annually",
            "tightened_language": "TCR faces flat funding despite rising demand.",
            "keywords": ["climate", "resilience"],
            "search_queries": ["tribal climate resilience"],
            "confidence_index": 0.85,
        },
        {
            "id": "fema_bric",
            "name": "FEMA BRIC",
            "agency": "FEMA",
            "federal_home": "DHS / FEMA",
            "priority": "critical",
            "access_type": "competitive",
            "funding_type": "Discretionary",
            "cfda": "97.047",
            "ci_status": "FLAGGED",
            "ci_determination": "BRIC terminated April 2025.",
            "description": "Building Resilient Infrastructure and Communities.",
            "advocacy_lever": "Restore BRIC funding and Tribal set-aside",
            "tightened_language": "BRIC program terminated; Tribal projects stranded.",
            "keywords": ["mitigation", "resilience"],
            "search_queries": ["BRIC tribal"],
            "confidence_index": 0.30,
        },
        {
            "id": "epa_gap",
            "name": "EPA Indian Environmental GAP",
            "agency": "EPA",
            "federal_home": "EPA / OEJ",
            "priority": "high",
            "access_type": "direct_service",
            "funding_type": "Discretionary",
            "cfda": "66.926",
            "ci_status": "STABLE",
            "ci_determination": "Permanent authorization.",
            "description": "General Assistance Program for Tribal environmental capacity.",
            "advocacy_lever": "Expand GAP funding for climate monitoring",
            "keywords": ["environmental", "capacity"],
            "search_queries": ["EPA GAP tribal"],
            "confidence_index": 0.70,
        },
        {
            "id": "doe_indian_energy",
            "name": "DOE Indian Energy",
            "agency": "Department of Energy",
            "federal_home": "DOE / OIE",
            "priority": "high",
            "access_type": "competitive",
            "funding_type": "Discretionary",
            "cfda": "81.104",
            "ci_status": "UNCERTAIN",
            "ci_determination": "IIJA supplement timing unclear.",
            "description": "Energy development and efficiency for Tribal communities.",
            "advocacy_lever": "Streamline Indian energy project approvals",
            "keywords": ["energy", "tribal"],
            "search_queries": ["DOE indian energy"],
            "confidence_index": 0.55,
        },
    ]


def _mock_registry(count: int = 3) -> dict:
    """Return mock tribal registry data with *count* Tribes."""
    tribes = []
    for i in range(1, count + 1):
        tribes.append({
            "tribe_id": f"epa_{i:03d}",
            "bia_code": str(i * 100),
            "name": f"Test Tribe {i}",
            "states": ["AZ"],
            "alternate_names": [],
            "epa_region": "9",
            "bia_recognized": True,
        })
    return {
        "metadata": {"total_tribes": count, "placeholder": False},
        "tribes": tribes,
    }


def _mock_ecoregion() -> dict:
    """Return mock ecoregion config."""
    return {
        "metadata": {"version": "test"},
        "ecoregions": {
            "southwest": {
                "name": "Southwest",
                "states": ["AZ", "NM", "NV"],
                "priority_programs": ["bia_tcr", "fema_bric"],
            },
        },
    }


def _mock_congress(count: int = 3) -> dict:
    """Return mock congressional cache with delegations for *count* Tribes."""
    delegations = {}
    for i in range(1, count + 1):
        tid = f"epa_{i:03d}"
        delegations[tid] = {
            "tribe_id": tid,
            "districts": [],
            "states": ["AZ"],
            "senators": [],
            "representatives": [],
        }
    return {
        "metadata": {
            "congress_session": "119",
            "total_members": 0,
            "total_committees": 0,
            "total_tribes_mapped": count,
        },
        "members": {},
        "committees": {},
        "delegations": delegations,
    }


def _mock_graph_schema() -> dict:
    """Return mock graph_schema.json with structural asks."""
    return {
        "authorities": [],
        "funding_vehicles": [],
        "barriers": [],
        "structural_asks": [
            {
                "id": "ask_multi_year",
                "name": "Multi-Year Funding Stability",
                "description": "Shift from annual to multi-year authorization.",
                "target": "Congress",
                "urgency": "FY26",
                "mitigates": ["bar_appropriations_volatility"],
                "programs": ["bia_tcr", "epa_gap", "doe_indian_energy"],
            },
        ],
    }


# ---------------------------------------------------------------------------
# Fixture: batch config with N Tribes
# ---------------------------------------------------------------------------

@pytest.fixture
def batch_config_3(tmp_path):
    """Build a 3-Tribe mock environment for batch tests."""
    return _build_batch_config(tmp_path, tribe_count=3)


@pytest.fixture
def batch_config_30(tmp_path):
    """Build a 30-Tribe mock environment for GC test."""
    return _build_batch_config(tmp_path, tribe_count=30)


def _build_batch_config(tmp_path: Path, tribe_count: int) -> dict:
    """Create all mock data files for *tribe_count* Tribes."""
    _write_json(tmp_path / "tribal_registry.json", _mock_registry(tribe_count))
    _write_json(tmp_path / "ecoregion_config.json", _mock_ecoregion())
    _write_json(tmp_path / "congressional_cache.json", _mock_congress(tribe_count))
    _write_json(tmp_path / "graph_schema.json", _mock_graph_schema())

    # Per-Tribe caches (empty awards/hazards for all)
    award_dir = tmp_path / "award_cache"
    hazard_dir = tmp_path / "hazard_profiles"
    for i in range(1, tribe_count + 1):
        tid = f"epa_{i:03d}"
        _write_json(award_dir / f"{tid}.json", {"tribe_id": tid, "awards": []})
        _write_json(hazard_dir / f"{tid}.json", {"tribe_id": tid, "sources": {}})

    output_dir = tmp_path / "outputs" / "packets"

    config = {
        "packets": {
            "tribal_registry": {"data_path": str(tmp_path / "tribal_registry.json")},
            "ecoregion": {"data_path": str(tmp_path / "ecoregion_config.json")},
            "congressional_cache": {"data_path": str(tmp_path / "congressional_cache.json")},
            "output_dir": str(output_dir),
            "awards": {
                "alias_path": str(tmp_path / "tribal_aliases.json"),
                "cache_dir": str(award_dir),
                "fuzzy_threshold": 85,
            },
            "hazards": {
                "nri_dir": str(tmp_path / "nri"),
                "usfs_dir": str(tmp_path / "usfs"),
                "cache_dir": str(hazard_dir),
                "crosswalk_path": str(tmp_path / "crosswalk.json"),
            },
            "docx": {
                "enabled": True,
                "output_dir": str(output_dir),
            },
        },
    }
    return {
        "config": config,
        "programs": _mock_programs(),
        "tmp_path": tmp_path,
        "output_dir": output_dir,
    }


def _make_orchestrator(env: dict):
    """Create a PacketOrchestrator with patched structural asks loader."""
    from src.packets.orchestrator import PacketOrchestrator

    orch = PacketOrchestrator(env["config"], env["programs"])

    graph_path = env["tmp_path"] / "graph_schema.json"

    def patched_load():
        with open(graph_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("structural_asks", [])

    orch._load_structural_asks = patched_load
    return orch


# ===========================================================================
# Batch generation tests
# ===========================================================================


class TestBatchGeneration:
    """Tests for PacketOrchestrator.run_all_tribes() batch mode."""

    def test_batch_generates_docx_per_tribe(self, batch_config_3):
        """run_all_tribes() generates multi-doc packets per Tribe.

        With no awards/hazards/delegation, each Tribe gets Doc B only
        (congressional overview), placed in congressional/ subdirectory.
        """
        orch = _make_orchestrator(batch_config_3)

        # Mock generate_strategic_overview to avoid needing full strategic data
        orch.generate_strategic_overview = MagicMock(
            return_value=Path("STRATEGIC-OVERVIEW.docx")
        )

        result = orch.run_all_tribes()

        output_dir = batch_config_3["output_dir"]
        congressional_dir = output_dir / "congressional"
        docx_files = (
            list(congressional_dir.glob("*.docx"))
            if congressional_dir.exists()
            else []
        )

        assert len(docx_files) == 3, (
            f"Expected 3 .docx files in congressional/, found {len(docx_files)}: "
            f"{[f.name for f in docx_files]}"
        )
        assert result["success"] == 3
        assert result["doc_b_count"] == 3

    def test_batch_error_isolation(self, batch_config_3):
        """One Tribe failure does not halt others; return dict shows error count."""
        orch = _make_orchestrator(batch_config_3)
        orch.generate_strategic_overview = MagicMock(
            return_value=Path("STRATEGIC-OVERVIEW.docx")
        )

        # Make the second Tribe fail by patching generate_tribal_docs
        original_gen = orch.generate_tribal_docs
        call_count = 0

        def failing_gen(context, tribe, doc_types=None):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise RuntimeError("Simulated failure for Tribe 2")
            return original_gen(context, tribe, doc_types)

        orch.generate_tribal_docs = failing_gen

        result = orch.run_all_tribes()

        assert result["success"] == 2
        assert result["errors"] == 1
        assert result["total"] == 3

    def test_batch_gc_called(self, batch_config_30):
        """gc.collect() is called at Tribe 25 during batch of 30."""
        orch = _make_orchestrator(batch_config_30)
        orch.generate_strategic_overview = MagicMock(
            return_value=Path("STRATEGIC-OVERVIEW.docx")
        )

        with patch("gc.collect") as mock_gc:
            orch.run_all_tribes()
            # gc.collect() should be called at i=25 (Tribe 25)
            # With 30 Tribes, i%25==0 only at i=25
            assert mock_gc.call_count >= 1, (
                f"Expected gc.collect() called at least once, "
                f"got {mock_gc.call_count} calls"
            )

    def test_batch_progress_format(self, batch_config_3, capsys):
        """Stdout includes [1/3] and [3/3] progress format."""
        orch = _make_orchestrator(batch_config_3)
        orch.generate_strategic_overview = MagicMock(
            return_value=Path("STRATEGIC-OVERVIEW.docx")
        )

        orch.run_all_tribes()

        captured = capsys.readouterr()
        assert "[1/3]" in captured.out, f"Missing [1/3] in output: {captured.out[:200]}"
        assert "[3/3]" in captured.out, f"Missing [3/3] in output: {captured.out[:200]}"

    def test_batch_return_dict(self, batch_config_3):
        """Return dict has required keys with correct types."""
        orch = _make_orchestrator(batch_config_3)
        orch.generate_strategic_overview = MagicMock(
            return_value=Path("STRATEGIC-OVERVIEW.docx")
        )

        result = orch.run_all_tribes()

        assert isinstance(result, dict)
        assert "success" in result
        assert "errors" in result
        assert "total" in result
        assert "duration_s" in result
        assert result["total"] == 3
        assert result["duration_s"] > 0
        assert result["success"] + result["errors"] == result["total"]

    def test_batch_strategic_overview_called(self, batch_config_3):
        """generate_strategic_overview() is called once after batch."""
        orch = _make_orchestrator(batch_config_3)
        orch.generate_strategic_overview = MagicMock(
            return_value=Path("STRATEGIC-OVERVIEW.docx")
        )

        orch.run_all_tribes()

        orch.generate_strategic_overview.assert_called_once()


class TestSingleTribeGeneration:
    """OPS-02 verification: run_single_tribe() produces full DOCX."""

    def test_single_tribe_generates_full_document(self, batch_config_3):
        """run_single_tribe() generates a .docx file (OPS-02)."""
        orch = _make_orchestrator(batch_config_3)

        # run_single_tribe calls sys.exit on failure, so we use the first Tribe
        orch.run_single_tribe("Test Tribe 1")

        output_dir = batch_config_3["output_dir"]
        docx_files = list(output_dir.glob("*.docx")) if output_dir.exists() else []

        assert len(docx_files) >= 1, (
            f"Expected at least 1 .docx file, found {len(docx_files)}"
        )
        # Verify the specific file exists
        expected_file = output_dir / "epa_001.docx"
        assert expected_file.exists(), f"Expected {expected_file} to exist"
        assert expected_file.stat().st_size > 0
