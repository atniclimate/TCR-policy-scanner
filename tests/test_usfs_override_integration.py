"""Integration test for USFS override logic and coverage report generation.

Validates that:
  - USFS conditional risk overrides NRI WFIR for fire-prone Tribes
  - Original NRI WFIR score is preserved in usfs_wildfire.nri_wfir_original
  - Coverage report JSON and Markdown are generated
  - Top hazards re-sorted after USFS override
  - Zero-risk USFS data does NOT override NRI WFIR
"""

import csv
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from src.packets.hazards import HazardProfileBuilder, NRI_HAZARD_CODES


def _write_json(path: Path, data: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _make_full_nri_csv(nri_dir: Path, rows: list[list]) -> None:
    """Write NRI CSV with all 18 hazard types."""
    headers = [
        "STCOFIPS", "COUNTY", "STATE", "RISK_SCORE", "RISK_RATNG",
        "RISK_VALUE", "EAL_VALT", "EAL_SCORE", "EAL_RATNG",
        "SOVI_SCORE", "SOVI_RATNG", "RESL_SCORE", "RESL_RATNG",
    ]
    for code in NRI_HAZARD_CODES:
        headers.extend([
            f"{code}_RISKS", f"{code}_RISKR", f"{code}_EALT",
            f"{code}_AFREQ", f"{code}_EVNTS",
        ])
    csv_path = nri_dir / "NRI_Table_Counties.csv"
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        for row in rows:
            writer.writerow(row)


def _build_county_row(fips, county, state, risk_score, eal_total, eal_score,
                      sovi_score, resl_score, wfir_risk, wfir_eal):
    """Helper to build a full 18-hazard county row."""
    row = [
        fips, county, state, str(risk_score), "",
        "100000", str(eal_total), str(eal_score), "",
        str(sovi_score), "", str(resl_score), "",
    ]
    for code in NRI_HAZARD_CODES:
        if code == "WFIR":
            row.extend([str(wfir_risk), "", str(wfir_eal), "3.0", "25"])
        else:
            row.extend(["0.0", "", "0", "0.0", "0"])
    return row


@pytest.fixture()
def integration_fixture(tmp_path: Path):
    """Set up a complete mini environment for integration testing."""
    # Registry
    reg_path = tmp_path / "tribal_registry.json"
    _write_json(reg_path, {
        "metadata": {"total_tribes": 3, "placeholder": False},
        "tribes": [
            {
                "tribe_id": "epa_001", "bia_code": "100",
                "name": "Fire Tribe Alpha", "states": ["AZ"],
                "alternate_names": [], "epa_region": "9", "bia_recognized": True,
            },
            {
                "tribe_id": "epa_002", "bia_code": "200",
                "name": "Cool Tribe Beta", "states": ["OK"],
                "alternate_names": [], "epa_region": "6", "bia_recognized": True,
            },
            {
                "tribe_id": "epa_003", "bia_code": "300",
                "name": "Lone Tribe Gamma", "states": ["GU"],
                "alternate_names": [], "epa_region": "9", "bia_recognized": True,
            },
        ],
    })

    # Crosswalk
    xwalk_path = tmp_path / "crosswalk.json"
    _write_json(xwalk_path, {
        "mappings": {
            "0400001": "epa_001",
            "4000001": "epa_002",
        }
    })

    # NRI dir
    nri_dir = tmp_path / "nri"
    nri_dir.mkdir()
    _make_full_nri_csv(nri_dir, [
        _build_county_row("04001", "Maricopa", "Arizona", 80.0, 100000, 90.0, 60.0, 50.0, 60.0, 50000),
        _build_county_row("40001", "Adair", "Oklahoma", 50.0, 150000, 55.0, 80.0, 30.0, 40.0, 30000),
    ])

    # Tribal relational CSV
    rel_csv = nri_dir / "NRI_Tribal_County_Relational.csv"
    with open(rel_csv, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["AIESSION", "STCOFIPS"])
        writer.writerow(["0400001", "04001"])
        writer.writerow(["4000001", "40001"])

    # USFS dir with mock XLSX
    usfs_dir = tmp_path / "usfs"
    usfs_dir.mkdir()
    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    ws.append(["GEOID", "name", "risk_to_homes", "burn_probability"])
    ws.append(["0400001", "Alpha Reservation", 85.0, 0.15])
    ws.append(["4000001", "Beta Reservation", 0.0, 0.0])
    wb.save(usfs_dir / "wrc_download.xlsx")
    wb.close()

    cache_dir = tmp_path / "hazard_profiles"
    outputs_dir = tmp_path / "outputs"

    config = {
        "packets": {
            "tribal_registry": {"data_path": str(reg_path)},
            "hazards": {
                "nri_dir": str(nri_dir),
                "usfs_dir": str(usfs_dir),
                "cache_dir": str(cache_dir),
                "crosswalk_path": str(xwalk_path),
            },
        }
    }

    return {
        "config": config,
        "cache_dir": cache_dir,
        "outputs_dir": outputs_dir,
        "nri_dir": nri_dir,
    }


class TestUSFSOverrideIntegration:
    """Integration tests for USFS override of NRI WFIR."""

    def test_usfs_overrides_wfir_for_fire_prone(self, integration_fixture):
        fix = integration_fixture
        with patch("src.packets.hazards.OUTPUTS_DIR", fix["outputs_dir"]):
            builder = HazardProfileBuilder(fix["config"])
            files = builder.build_all_profiles()

        assert files == 3

        with open(fix["cache_dir"] / "epa_001.json", encoding="utf-8") as f:
            alpha = json.load(f)

        nri = alpha["sources"]["fema_nri"]

        # USFS override: 60.0 -> 85.0
        assert nri["all_hazards"]["WFIR"]["risk_score"] == 85.0
        assert nri["all_hazards"]["WFIR"]["source"] == "USFS"
        assert nri["all_hazards"]["WFIR"]["risk_rating"] == "Very High"

    def test_original_wfir_preserved(self, integration_fixture):
        fix = integration_fixture
        with patch("src.packets.hazards.OUTPUTS_DIR", fix["outputs_dir"]):
            builder = HazardProfileBuilder(fix["config"])
            builder.build_all_profiles()

        with open(fix["cache_dir"] / "epa_001.json", encoding="utf-8") as f:
            alpha = json.load(f)

        usfs = alpha["sources"]["usfs_wildfire"]
        assert usfs["nri_wfir_original"] == 60.0

    def test_conditional_risk_field_present(self, integration_fixture):
        fix = integration_fixture
        with patch("src.packets.hazards.OUTPUTS_DIR", fix["outputs_dir"]):
            builder = HazardProfileBuilder(fix["config"])
            builder.build_all_profiles()

        with open(fix["cache_dir"] / "epa_001.json", encoding="utf-8") as f:
            alpha = json.load(f)

        usfs = alpha["sources"]["usfs_wildfire"]
        assert usfs["conditional_risk_to_structures"] == 85.0

    def test_zero_usfs_does_not_override(self, integration_fixture):
        fix = integration_fixture
        with patch("src.packets.hazards.OUTPUTS_DIR", fix["outputs_dir"]):
            builder = HazardProfileBuilder(fix["config"])
            builder.build_all_profiles()

        with open(fix["cache_dir"] / "epa_002.json", encoding="utf-8") as f:
            beta = json.load(f)

        nri = beta["sources"]["fema_nri"]
        # USFS risk_to_homes is 0.0, so NRI WFIR should NOT be overridden
        assert nri["all_hazards"]["WFIR"]["risk_score"] == 40.0
        assert "source" not in nri["all_hazards"]["WFIR"]

    def test_coverage_report_json_generated(self, integration_fixture):
        fix = integration_fixture
        with patch("src.packets.hazards.OUTPUTS_DIR", fix["outputs_dir"]):
            builder = HazardProfileBuilder(fix["config"])
            builder.build_all_profiles()

        report_path = fix["outputs_dir"] / "hazard_coverage_report.json"
        assert report_path.exists()

        with open(report_path, encoding="utf-8") as f:
            report = json.load(f)

        assert report["summary"]["total_profiles"] == 3
        assert report["summary"]["usfs_overrides"] == 1
        assert report["summary"]["nri_matched"] == 2
        assert report["summary"]["usfs_matched"] == 2
        assert report["summary"]["unmatched_profiles"] == 1  # epa_003 (GU)

    def test_coverage_report_md_generated(self, integration_fixture):
        fix = integration_fixture
        with patch("src.packets.hazards.OUTPUTS_DIR", fix["outputs_dir"]):
            builder = HazardProfileBuilder(fix["config"])
            builder.build_all_profiles()

        md_path = fix["outputs_dir"] / "hazard_coverage_report.md"
        assert md_path.exists()
        content = md_path.read_text(encoding="utf-8")
        assert "Hazard Coverage Report" in content
        assert "Per-State Breakdown" in content
        assert "Tribes Not Covered by Federal Hazard Data" in content

    def test_per_state_breakdown(self, integration_fixture):
        fix = integration_fixture
        with patch("src.packets.hazards.OUTPUTS_DIR", fix["outputs_dir"]):
            builder = HazardProfileBuilder(fix["config"])
            builder.build_all_profiles()

        with open(fix["outputs_dir"] / "hazard_coverage_report.json", encoding="utf-8") as f:
            report = json.load(f)

        per_state = report["per_state"]
        assert "AZ" in per_state
        assert per_state["AZ"]["total"] == 1
        assert per_state["AZ"]["nri_matched"] == 1
        assert per_state["AZ"]["usfs_matched"] == 1

        assert "OK" in per_state
        assert per_state["OK"]["total"] == 1

        assert "GU" in per_state
        assert per_state["GU"]["unmatched"] == 1

    def test_unmatched_tribe_no_state_data(self, integration_fixture):
        """Tribe epa_003 has states=['GU'] which has no NRI counties -> unmatched."""
        fix = integration_fixture
        with patch("src.packets.hazards.OUTPUTS_DIR", fix["outputs_dir"]):
            builder = HazardProfileBuilder(fix["config"])
            builder.build_all_profiles()

        with open(fix["cache_dir"] / "epa_003.json", encoding="utf-8") as f:
            gamma = json.load(f)

        nri = gamma["sources"]["fema_nri"]
        assert nri["counties_analyzed"] == 0
        # All 18 hazard types present with zero values for schema consistency
        assert len(nri["all_hazards"]) == 18
        for code, data in nri["all_hazards"].items():
            assert data["risk_score"] == 0.0, f"{code} should have zero risk_score"

    def test_top_hazards_resorted_after_override(self, integration_fixture):
        """After USFS override boosts WFIR, top_hazards should reflect new ranking."""
        fix = integration_fixture
        with patch("src.packets.hazards.OUTPUTS_DIR", fix["outputs_dir"]):
            builder = HazardProfileBuilder(fix["config"])
            builder.build_all_profiles()

        with open(fix["cache_dir"] / "epa_001.json", encoding="utf-8") as f:
            alpha = json.load(f)

        top = alpha["sources"]["fema_nri"]["top_hazards"]
        # Alpha only has WFIR as non-zero, so it should be the only top hazard
        assert len(top) == 1
        assert top[0]["code"] == "WFIR"
        assert top[0]["risk_score"] == 85.0  # USFS-overridden value
