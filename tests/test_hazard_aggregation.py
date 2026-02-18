"""Unit tests for area-weighted NRI hazard aggregation (HZRD-03, HZRD-04).

Tests the core algorithmic changes in src/packets/hazards.py:
  - score_to_rating() quintile-based rating derivation
  - Area-weighted averaging for multi-county Tribes
  - Non-zero hazard filtering
  - Top-5 hazard extraction and ranking
  - EAL dollar amounts use weighted sum (not average)
"""

import csv
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from src.packets.hazards import (
    HazardProfileBuilder,
    NRI_HAZARD_CODES,
    _safe_float,
    score_to_rating,
)



# ============================================================================
# _safe_float() unit tests -- NaN/Inf guards (GRIBBLE-06)
# ============================================================================


class TestSafeFloat:
    """Test _safe_float handles NaN, Inf, and -Inf values."""

    def test_nan_string_returns_default(self):
        assert _safe_float("nan") == 0.0

    def test_nan_float_returns_default(self):
        assert _safe_float(float("nan")) == 0.0

    def test_inf_string_returns_default(self):
        assert _safe_float("inf") == 0.0

    def test_neg_inf_string_returns_default(self):
        assert _safe_float("-inf") == 0.0

    def test_inf_float_returns_default(self):
        assert _safe_float(float("inf")) == 0.0

    def test_neg_inf_float_returns_default(self):
        assert _safe_float(float("-inf")) == 0.0

    def test_nan_with_custom_default(self):
        assert _safe_float("nan", default=-1.0) == -1.0

    def test_normal_values_unchanged(self):
        assert _safe_float("42.5") == 42.5
        assert _safe_float(100) == 100.0
        assert _safe_float(0.0) == 0.0

    def test_none_returns_default(self):
        assert _safe_float(None) == 0.0

    def test_empty_string_returns_default(self):
        assert _safe_float("") == 0.0


# ============================================================================
# score_to_rating() unit tests
# ============================================================================


class TestScoreToRating:
    """Test quintile-based score-to-rating conversion."""

    def test_very_high(self):
        assert score_to_rating(80) == "Very High"
        assert score_to_rating(100) == "Very High"
        assert score_to_rating(95.5) == "Very High"

    def test_relatively_high(self):
        assert score_to_rating(60) == "Relatively High"
        assert score_to_rating(79.9) == "Relatively High"

    def test_relatively_moderate(self):
        assert score_to_rating(40) == "Relatively Moderate"
        assert score_to_rating(59.9) == "Relatively Moderate"

    def test_relatively_low(self):
        assert score_to_rating(20) == "Relatively Low"
        assert score_to_rating(39.9) == "Relatively Low"

    def test_very_low(self):
        assert score_to_rating(0) == "Very Low"
        assert score_to_rating(19.9) == "Very Low"

    def test_boundary_values(self):
        """Exact boundary values go to the higher bracket."""
        assert score_to_rating(80) == "Very High"
        assert score_to_rating(60) == "Relatively High"
        assert score_to_rating(40) == "Relatively Moderate"
        assert score_to_rating(20) == "Relatively Low"

    def test_just_below_boundaries(self):
        """Values just below boundaries stay in lower bracket."""
        assert score_to_rating(79.99) == "Relatively High"
        assert score_to_rating(59.99) == "Relatively Moderate"
        assert score_to_rating(39.99) == "Relatively Low"
        assert score_to_rating(19.99) == "Very Low"

    def test_zero_and_hundred(self):
        """Edge cases: min and max scores."""
        assert score_to_rating(0.0) == "Very Low"
        assert score_to_rating(100.0) == "Very High"

    def test_mid_range_values(self):
        """Typical mid-range scores."""
        assert score_to_rating(50.0) == "Relatively Moderate"
        assert score_to_rating(70.0) == "Relatively High"
        assert score_to_rating(10.0) == "Very Low"
        assert score_to_rating(30.0) == "Relatively Low"
        assert score_to_rating(90.0) == "Very High"

    def test_returns_string(self):
        """Return type is always str."""
        for score in [0, 20, 40, 60, 80, 100]:
            assert isinstance(score_to_rating(score), str)

    def test_all_five_ratings_reachable(self):
        """All five NRI rating strings are producible."""
        ratings = {score_to_rating(s) for s in [0, 20, 40, 60, 80]}
        expected = {
            "Very Low",
            "Relatively Low",
            "Relatively Moderate",
            "Relatively High",
            "Very High",
        }
        assert ratings == expected


# ============================================================================
# Helper: build test fixtures
# ============================================================================


def _write_json(path: Path, data: dict) -> None:
    """Write JSON file with UTF-8 encoding."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _make_nri_csv(nri_dir: Path, rows: list[list]) -> None:
    """Write a mock NRI county CSV with standard headers + WFIR/DRGT/HRCN hazards."""
    headers = [
        "STCOFIPS", "COUNTY", "STATE", "RISK_SCORE", "RISK_RATNG",
        "RISK_VALUE", "EAL_VALT", "EAL_SCORE", "EAL_RATNG",
        "SOVI_SCORE", "SOVI_RATNG", "RESL_SCORE", "RESL_RATNG",
    ]
    for code in ["WFIR", "DRGT", "HRCN"]:
        headers.extend([
            f"{code}_RISKS", f"{code}_RISKR", f"{code}_EALT",
            f"{code}_AFREQ", f"{code}_EVNTS",
        ])
    nri_csv = nri_dir / "NRI_Table_Counties.csv"
    with open(nri_csv, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        for row in rows:
            writer.writerow(row)


def _make_tribal_relational_csv(nri_dir: Path, relations: list[tuple[str, str]]) -> None:
    """Write a mock NRI Tribal County Relational CSV."""
    csv_path = nri_dir / "NRI_Tribal_County_Relational.csv"
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["AIESSION", "STCOFIPS"])
        for geoid, fips in relations:
            writer.writerow([geoid, fips])


def _make_area_weights(path: Path, crosswalk: dict) -> None:
    """Write a mock area weights JSON."""
    total_links = sum(len(v) for v in crosswalk.values())
    data = {
        "metadata": {
            "total_aiannh_entities": len(crosswalk),
            "total_county_links": total_links,
        },
        "crosswalk": crosswalk,
    }
    _write_json(path, data)


# ============================================================================
# Area-weighted aggregation tests
# ============================================================================


class TestAreaWeightedAggregation:
    """Test area-weighted NRI aggregation for multi-county Tribes."""

    @pytest.fixture
    def base_fixture(self, tmp_path: Path) -> dict:
        """Provide reusable test dirs and registry."""
        # Mini registry
        registry = {
            "metadata": {"total_tribes": 2, "placeholder": False},
            "tribes": [
                {
                    "tribe_id": "epa_001",
                    "bia_code": "100",
                    "name": "Test Tribe Alpha",
                    "states": ["AZ"],
                    "alternate_names": [],
                    "epa_region": "9",
                    "bia_recognized": True,
                },
                {
                    "tribe_id": "epa_002",
                    "bia_code": "200",
                    "name": "Test Tribe Beta",
                    "states": ["OK"],
                    "alternate_names": [],
                    "epa_region": "6",
                    "bia_recognized": True,
                },
            ],
        }
        reg_path = tmp_path / "tribal_registry.json"
        _write_json(reg_path, registry)

        crosswalk = {
            "mappings": {
                "0400001": "epa_001",
                "0400002": "epa_001",
                "4000001": "epa_002",
            }
        }
        crosswalk_path = tmp_path / "aiannh_tribe_crosswalk.json"
        _write_json(crosswalk_path, crosswalk)

        nri_dir = tmp_path / "nri"
        nri_dir.mkdir()

        usfs_dir = tmp_path / "usfs"
        usfs_dir.mkdir()

        cache_dir = tmp_path / "hazard_profiles"

        return {
            "tmp_path": tmp_path,
            "reg_path": str(reg_path),
            "crosswalk_path": str(crosswalk_path),
            "nri_dir": nri_dir,
            "usfs_dir": str(usfs_dir),
            "cache_dir": str(cache_dir),
        }

    def _make_config(self, fix: dict) -> dict:
        """Build a config dict from fixture paths."""
        return {
            "packets": {
                "tribal_registry": {"data_path": fix["reg_path"]},
                "hazards": {
                    "nri_dir": str(fix["nri_dir"]),
                    "usfs_dir": fix["usfs_dir"],
                    "cache_dir": fix["cache_dir"],
                    "crosswalk_path": fix["crosswalk_path"],
                },
            }
        }

    def test_single_county_passthrough(self, base_fixture: dict) -> None:
        """Single county (weight 1.0): scores pass through unchanged."""
        fix = base_fixture
        nri_dir = fix["nri_dir"]

        # One county for epa_002 (4000001 -> 40001)
        _make_nri_csv(nri_dir, [
            ["40001", "Adair", "Oklahoma", "50.0", "Relatively Moderate",
             "300000", "150000", "55.0", "Relatively Moderate",
             "80.0", "Very High", "30.0", "Relatively Low",
             "20.0", "Relatively Low", "10000", "1.0", "10",
             "70.0", "Relatively High", "200000", "4.0", "60",
             "40.0", "Relatively Moderate", "50000", "1.5", "20"],
        ])
        _make_tribal_relational_csv(nri_dir, [("4000001", "40001")])

        config = self._make_config(fix)
        builder = HazardProfileBuilder(config)
        county_data = builder._load_nri_county_data()
        tribal_counties = builder._load_nri_tribal_relational()

        tribe = {"tribe_id": "epa_002", "name": "Test Tribe Beta", "states": ["OK"]}
        profile = builder._build_tribe_nri_profile("epa_002", tribe, county_data, tribal_counties)

        assert profile["counties_analyzed"] == 1
        assert profile["composite"]["risk_score"] == 50.0
        assert profile["composite"]["sovi_score"] == 80.0
        assert profile["composite"]["resl_score"] == 30.0
        # EAL total: weighted sum with weight 1.0 = passthrough
        assert profile["composite"]["eal_total"] == 150000.0

    def test_two_equal_weight_counties(self, base_fixture: dict) -> None:
        """Two counties with equal weights: scores average exactly."""
        fix = base_fixture
        nri_dir = fix["nri_dir"]

        _make_nri_csv(nri_dir, [
            # County 1: risk=80, eal=100000
            ["04001", "Maricopa", "Arizona", "80.0", "Very High",
             "1000000", "100000", "70.0", "Relatively High",
             "60.0", "Relatively High", "50.0", "Relatively Moderate",
             "90.0", "Very High", "200000", "5.0", "100",
             "40.0", "Relatively Moderate", "50000", "2.0", "30",
             "0.0", "", "0", "0.0", "0"],
            # County 2: risk=60, eal=200000
            ["04003", "Pima", "Arizona", "60.0", "Relatively High",
             "800000", "200000", "50.0", "Relatively Moderate",
             "40.0", "Relatively Moderate", "70.0", "Relatively High",
             "70.0", "Relatively High", "100000", "3.0", "50",
             "80.0", "Very High", "150000", "6.0", "80",
             "0.0", "", "0", "0.0", "0"],
        ])
        _make_tribal_relational_csv(nri_dir, [
            ("0400001", "04001"),
            ("0400002", "04003"),
        ])

        config = self._make_config(fix)
        builder = HazardProfileBuilder(config)
        county_data = builder._load_nri_county_data()
        tribal_counties = builder._load_nri_tribal_relational()

        tribe = {"tribe_id": "epa_001", "name": "Test Tribe Alpha", "states": ["AZ"]}
        profile = builder._build_tribe_nri_profile("epa_001", tribe, county_data, tribal_counties)

        assert profile["counties_analyzed"] == 2
        # Equal weights: average of 80 and 60 = 70
        assert profile["composite"]["risk_score"] == 70.0
        # EAL total: weighted sum = 0.5*100000 + 0.5*200000 = 150000
        assert profile["composite"]["eal_total"] == 150000.0
        # SOVI: average of 60 and 40 = 50
        assert profile["composite"]["sovi_score"] == 50.0
        # RESL: average of 50 and 70 = 60
        assert profile["composite"]["resl_score"] == 60.0

    def test_unequal_area_weights(self, base_fixture: dict) -> None:
        """Two counties with unequal weights (0.7 and 0.3): proportional averaging."""
        fix = base_fixture
        nri_dir = fix["nri_dir"]
        weights_path = nri_dir / "tribal_county_area_weights.json"

        _make_nri_csv(nri_dir, [
            # County 1: risk=80
            ["04001", "Maricopa", "Arizona", "80.0", "Very High",
             "1000000", "100000", "90.0", "Very High",
             "60.0", "Relatively High", "50.0", "Relatively Moderate",
             "90.0", "Very High", "200000", "5.0", "100",
             "40.0", "Relatively Moderate", "50000", "2.0", "30",
             "10.0", "Very Low", "1000", "0.1", "1"],
            # County 2: risk=60
            ["04003", "Pima", "Arizona", "60.0", "Relatively High",
             "800000", "200000", "70.0", "Relatively High",
             "40.0", "Relatively Moderate", "70.0", "Relatively High",
             "70.0", "Relatively High", "100000", "3.0", "50",
             "80.0", "Very High", "150000", "6.0", "80",
             "20.0", "Relatively Low", "5000", "0.5", "5"],
        ])
        _make_tribal_relational_csv(nri_dir, [
            ("0400001", "04001"),
            ("0400002", "04003"),
        ])

        # Create area weights: 0.7 for 04001, 0.3 for 04003
        _make_area_weights(weights_path, {
            "0400001": [{"county_fips": "04001", "weight": 0.7, "overlap_area_sqkm": 100}],
            "0400002": [{"county_fips": "04003", "weight": 0.3, "overlap_area_sqkm": 42.9}],
        })

        config = self._make_config(fix)
        with patch("src.packets.hazards.TRIBAL_COUNTY_WEIGHTS_PATH", weights_path):
            builder = HazardProfileBuilder(config)

        county_data = builder._load_nri_county_data()
        tribal_counties = builder._load_nri_tribal_relational()

        tribe = {"tribe_id": "epa_001", "name": "Test Tribe Alpha", "states": ["AZ"]}
        profile = builder._build_tribe_nri_profile("epa_001", tribe, county_data, tribal_counties)

        assert profile["counties_analyzed"] == 2
        # Weighted: 0.7*80 + 0.3*60 = 56 + 18 = 74
        assert profile["composite"]["risk_score"] == 74.0
        # EAL total: 0.7*100000 + 0.3*200000 = 70000 + 60000 = 130000
        assert profile["composite"]["eal_total"] == 130000.0
        # SOVI: 0.7*60 + 0.3*40 = 42 + 12 = 54
        assert profile["composite"]["sovi_score"] == 54.0
        # RESL: 0.7*50 + 0.3*70 = 35 + 21 = 56
        assert profile["composite"]["resl_score"] == 56.0

    def test_nonzero_hazard_filtering(self, base_fixture: dict) -> None:
        """Zero-score hazards are included with zero values for schema consistency."""
        fix = base_fixture
        nri_dir = fix["nri_dir"]

        # HRCN has risk_score=0 in both counties
        _make_nri_csv(nri_dir, [
            ["04001", "Maricopa", "Arizona", "80.0", "Very High",
             "1000000", "100000", "90.0", "Very High",
             "60.0", "Relatively High", "50.0", "Relatively Moderate",
             "90.0", "Very High", "200000", "5.0", "100",
             "40.0", "Relatively Moderate", "50000", "2.0", "30",
             "0.0", "", "0", "0.0", "0"],
            ["04003", "Pima", "Arizona", "60.0", "Relatively High",
             "800000", "200000", "70.0", "Relatively High",
             "40.0", "Relatively Moderate", "70.0", "Relatively High",
             "70.0", "Relatively High", "100000", "3.0", "50",
             "80.0", "Very High", "150000", "6.0", "80",
             "0.0", "", "0", "0.0", "0"],
        ])
        _make_tribal_relational_csv(nri_dir, [
            ("0400001", "04001"),
            ("0400002", "04003"),
        ])

        config = self._make_config(fix)
        builder = HazardProfileBuilder(config)
        county_data = builder._load_nri_county_data()
        tribal_counties = builder._load_nri_tribal_relational()

        tribe = {"tribe_id": "epa_001", "name": "Test Tribe Alpha", "states": ["AZ"]}
        profile = builder._build_tribe_nri_profile("epa_001", tribe, county_data, tribal_counties)

        # WFIR and DRGT have non-zero scores; HRCN has zero score but
        # is still present in all_hazards (all 18 types always included)
        assert "WFIR" in profile["all_hazards"]
        assert "DRGT" in profile["all_hazards"]
        assert "HRCN" in profile["all_hazards"], (
            "Zero-score HRCN should still be present in all_hazards"
        )
        assert profile["all_hazards"]["HRCN"]["risk_score"] == 0.0
        # All 18 NRI hazard types are always present for schema consistency
        assert len(profile["all_hazards"]) == 18

    def test_top_5_extraction(self, base_fixture: dict) -> None:
        """With >5 non-zero hazards, only top 5 by risk_score appear in top_hazards."""
        fix = base_fixture
        nri_dir = fix["nri_dir"]

        # Build CSV with all 18 hazard types having data
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

        # Single county with ascending risk scores per hazard type
        row = ["40001", "Adair", "Oklahoma", "60.0", "Relatively High",
               "500000", "250000", "65.0", "Relatively High",
               "55.0", "Relatively Moderate", "45.0", "Relatively Moderate"]
        for i, code in enumerate(NRI_HAZARD_CODES):
            risk = (i + 1) * 5.0  # 5, 10, 15, ..., 90
            row.extend([str(risk), "", str(risk * 100), "1.0", "10"])

        nri_csv = nri_dir / "NRI_Table_Counties.csv"
        with open(nri_csv, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            writer.writerow(row)

        _make_tribal_relational_csv(nri_dir, [("4000001", "40001")])

        config = self._make_config(fix)
        builder = HazardProfileBuilder(config)
        county_data = builder._load_nri_county_data()
        tribal_counties = builder._load_nri_tribal_relational()

        tribe = {"tribe_id": "epa_002", "name": "Test Tribe Beta", "states": ["OK"]}
        profile = builder._build_tribe_nri_profile("epa_002", tribe, county_data, tribal_counties)

        # All 18 non-zero hazards should be in all_hazards
        assert len(profile["all_hazards"]) == 18
        # Only top 5 in top_hazards
        top = profile["top_hazards"]
        assert len(top) == 5
        # Descending order
        for i in range(len(top) - 1):
            assert top[i]["risk_score"] >= top[i + 1]["risk_score"]
        # Highest risk_score should be 90.0 (last hazard type * 5)
        assert top[0]["risk_score"] == 90.0

    def test_eal_dollar_weighted_sum(self, base_fixture: dict) -> None:
        """EAL dollar amounts use weighted sum, not average."""
        fix = base_fixture
        nri_dir = fix["nri_dir"]
        weights_path = nri_dir / "tribal_county_area_weights.json"

        _make_nri_csv(nri_dir, [
            # County 1: eal_total=1000000
            ["04001", "Maricopa", "Arizona", "80.0", "Very High",
             "1000000", "1000000", "90.0", "Very High",
             "60.0", "Relatively High", "50.0", "Relatively Moderate",
             "90.0", "Very High", "500000", "5.0", "100",
             "40.0", "Relatively Moderate", "50000", "2.0", "30",
             "10.0", "Very Low", "1000", "0.1", "1"],
            # County 2: eal_total=500000
            ["04003", "Pima", "Arizona", "60.0", "Relatively High",
             "800000", "500000", "70.0", "Relatively High",
             "40.0", "Relatively Moderate", "70.0", "Relatively High",
             "70.0", "Relatively High", "200000", "3.0", "50",
             "80.0", "Very High", "150000", "6.0", "80",
             "20.0", "Relatively Low", "5000", "0.5", "5"],
        ])
        _make_tribal_relational_csv(nri_dir, [
            ("0400001", "04001"),
            ("0400002", "04003"),
        ])

        # 60% overlap with county 1, 40% with county 2
        _make_area_weights(weights_path, {
            "0400001": [{"county_fips": "04001", "weight": 0.6, "overlap_area_sqkm": 60}],
            "0400002": [{"county_fips": "04003", "weight": 0.4, "overlap_area_sqkm": 40}],
        })

        config = self._make_config(fix)
        with patch("src.packets.hazards.TRIBAL_COUNTY_WEIGHTS_PATH", weights_path):
            builder = HazardProfileBuilder(config)

        county_data = builder._load_nri_county_data()
        tribal_counties = builder._load_nri_tribal_relational()

        tribe = {"tribe_id": "epa_001", "name": "Test Tribe Alpha", "states": ["AZ"]}
        profile = builder._build_tribe_nri_profile("epa_001", tribe, county_data, tribal_counties)

        # EAL total: weighted sum = 0.6*1000000 + 0.4*500000 = 600000 + 200000 = 800000
        assert profile["composite"]["eal_total"] == 800000.0
        # WFIR EAL: 0.6*500000 + 0.4*200000 = 300000 + 80000 = 380000
        assert profile["all_hazards"]["WFIR"]["eal_total"] == 380000.0

    def test_ratings_rederived_from_weighted_scores(self, base_fixture: dict) -> None:
        """Rating strings are re-derived from weighted scores, not taken from source data."""
        fix = base_fixture
        nri_dir = fix["nri_dir"]

        # Two counties: both "Very High" risk rating, but average score = 75 -> "Relatively High"
        _make_nri_csv(nri_dir, [
            ["04001", "Maricopa", "Arizona", "85.0", "Very High",
             "1000000", "100000", "90.0", "Very High",
             "60.0", "Relatively High", "50.0", "Relatively Moderate",
             "90.0", "Very High", "200000", "5.0", "100",
             "40.0", "Relatively Moderate", "50000", "2.0", "30",
             "10.0", "Very Low", "1000", "0.1", "1"],
            ["04003", "Pima", "Arizona", "65.0", "Relatively High",
             "800000", "200000", "70.0", "Relatively High",
             "40.0", "Relatively Moderate", "70.0", "Relatively High",
             "70.0", "Relatively High", "100000", "3.0", "50",
             "80.0", "Very High", "150000", "6.0", "80",
             "20.0", "Relatively Low", "5000", "0.5", "5"],
        ])
        _make_tribal_relational_csv(nri_dir, [
            ("0400001", "04001"),
            ("0400002", "04003"),
        ])

        config = self._make_config(fix)
        builder = HazardProfileBuilder(config)
        county_data = builder._load_nri_county_data()
        tribal_counties = builder._load_nri_tribal_relational()

        tribe = {"tribe_id": "epa_001", "name": "Test Tribe Alpha", "states": ["AZ"]}
        profile = builder._build_tribe_nri_profile("epa_001", tribe, county_data, tribal_counties)

        # Average risk: (85+65)/2 = 75 -> "Relatively High" (not "Very High")
        assert profile["composite"]["risk_score"] == 75.0
        assert profile["composite"]["risk_rating"] == "Relatively High"

        # WFIR: (90+70)/2 = 80 -> "Very High"
        assert profile["all_hazards"]["WFIR"]["risk_score"] == 80.0
        assert profile["all_hazards"]["WFIR"]["risk_rating"] == "Very High"

        # DRGT: (40+80)/2 = 60 -> "Relatively High"
        assert profile["all_hazards"]["DRGT"]["risk_score"] == 60.0
        assert profile["all_hazards"]["DRGT"]["risk_rating"] == "Relatively High"

    def test_empty_profile_has_all_18_zero_hazards(self, base_fixture: dict) -> None:
        """Empty profiles (no county data) have all 18 hazard types with zeros."""
        fix = base_fixture
        nri_dir = fix["nri_dir"]

        # Create empty NRI CSV
        _make_nri_csv(nri_dir, [])

        config = self._make_config(fix)
        builder = HazardProfileBuilder(config)

        profile = builder._build_tribe_nri_profile(
            "epa_999",
            {"tribe_id": "epa_999", "name": "No Data Tribe", "states": ["GU"]},
            {},
            {},
        )
        # All 18 hazard types present with zero values for schema consistency
        assert len(profile["all_hazards"]) == 18
        for code, data in profile["all_hazards"].items():
            assert data["risk_score"] == 0.0, f"{code} should have zero risk_score"
        assert profile["top_hazards"] == []
        assert profile["composite"]["risk_score"] == 0.0

    def test_composite_has_eal_rating(self, base_fixture: dict) -> None:
        """Composite includes eal_rating field (was missing in old code)."""
        fix = base_fixture
        nri_dir = fix["nri_dir"]

        _make_nri_csv(nri_dir, [
            ["40001", "Adair", "Oklahoma", "50.0", "Relatively Moderate",
             "300000", "150000", "85.0", "Very High",
             "80.0", "Very High", "30.0", "Relatively Low",
             "20.0", "Relatively Low", "10000", "1.0", "10",
             "70.0", "Relatively High", "200000", "4.0", "60",
             "40.0", "Relatively Moderate", "50000", "1.5", "20"],
        ])
        _make_tribal_relational_csv(nri_dir, [("4000001", "40001")])

        config = self._make_config(fix)
        builder = HazardProfileBuilder(config)
        county_data = builder._load_nri_county_data()
        tribal_counties = builder._load_nri_tribal_relational()

        tribe = {"tribe_id": "epa_002", "name": "Test Tribe Beta", "states": ["OK"]}
        profile = builder._build_tribe_nri_profile("epa_002", tribe, county_data, tribal_counties)

        assert "eal_rating" in profile["composite"]
        assert profile["composite"]["eal_rating"] == "Very High"  # eal_score=85 -> Very High

    def test_version_string_format(self, base_fixture: dict) -> None:
        """Version string uses 'NRI_v1.20' format."""
        fix = base_fixture
        nri_dir = fix["nri_dir"]

        _make_nri_csv(nri_dir, [
            ["40001", "Adair", "Oklahoma", "50.0", "Relatively Moderate",
             "300000", "150000", "55.0", "Relatively Moderate",
             "80.0", "Very High", "30.0", "Relatively Low",
             "20.0", "Relatively Low", "10000", "1.0", "10",
             "70.0", "Relatively High", "200000", "4.0", "60",
             "40.0", "Relatively Moderate", "50000", "1.5", "20"],
        ])
        _make_tribal_relational_csv(nri_dir, [("4000001", "40001")])

        config = self._make_config(fix)
        builder = HazardProfileBuilder(config)
        county_data = builder._load_nri_county_data()
        tribal_counties = builder._load_nri_tribal_relational()

        tribe = {"tribe_id": "epa_002", "name": "Test Tribe Beta", "states": ["OK"]}
        profile = builder._build_tribe_nri_profile("epa_002", tribe, county_data, tribal_counties)

        assert profile["version"] == "NRI_v1.20"

    def test_area_weights_fallback_to_relational(self, base_fixture: dict) -> None:
        """When area weights are unavailable, falls back to equal weights via relational CSV."""
        fix = base_fixture
        nri_dir = fix["nri_dir"]

        _make_nri_csv(nri_dir, [
            ["04001", "Maricopa", "Arizona", "80.0", "Very High",
             "1000000", "100000", "90.0", "Very High",
             "60.0", "Relatively High", "50.0", "Relatively Moderate",
             "90.0", "Very High", "200000", "5.0", "100",
             "40.0", "Relatively Moderate", "50000", "2.0", "30",
             "10.0", "Very Low", "1000", "0.1", "1"],
            ["04003", "Pima", "Arizona", "40.0", "Relatively Moderate",
             "800000", "300000", "50.0", "Relatively Moderate",
             "40.0", "Relatively Moderate", "70.0", "Relatively High",
             "50.0", "Relatively Moderate", "100000", "3.0", "50",
             "60.0", "Relatively High", "150000", "6.0", "80",
             "0.0", "", "0", "0.0", "0"],
        ])
        _make_tribal_relational_csv(nri_dir, [
            ("0400001", "04001"),
            ("0400002", "04003"),
        ])
        # No area weights file created -> falls back to equal weights

        config = self._make_config(fix)
        builder = HazardProfileBuilder(config)
        county_data = builder._load_nri_county_data()
        tribal_counties = builder._load_nri_tribal_relational()

        tribe = {"tribe_id": "epa_001", "name": "Test Tribe Alpha", "states": ["AZ"]}
        profile = builder._build_tribe_nri_profile("epa_001", tribe, county_data, tribal_counties)

        # Equal weights (0.5 each): risk = (80+40)/2 = 60
        assert profile["composite"]["risk_score"] == 60.0
        assert profile["counties_analyzed"] == 2


# ============================================================================
# GRIBBLE-03: Atomic writes for profile cache files
# ============================================================================


class TestAtomicProfileWrites:
    """Verify build_all_profiles uses atomic write pattern for cache files."""

    def test_cache_file_written_atomically(self, tmp_path: Path) -> None:
        """Cache files should use tmp + os.replace, not direct write.

        We verify by checking the source code uses atomic_write_json from
        _geo_common, which implements the os.replace() pattern internally.
        """
        import inspect
        source = inspect.getsource(HazardProfileBuilder.build_all_profiles)
        assert "atomic_write_json" in source, (
            "build_all_profiles must use atomic_write_json for atomic writes"
        )


# ============================================================================
# GRIBBLE-09: Path traversal guard for tribe_id
# ============================================================================


class TestPathTraversalGuard:
    """Verify tribe_id path sanitization in build_all_profiles."""

    def test_source_contains_path_sanitization(self) -> None:
        """build_all_profiles must sanitize tribe_id before file write."""
        import inspect
        source = inspect.getsource(HazardProfileBuilder.build_all_profiles)
        assert "Path(" in source and ".name" in source, (
            "build_all_profiles must sanitize tribe_id with Path().name"
        )


# ============================================================================
# GRIBBLE-01: ZIP Slip path traversal in download script
# ============================================================================


class TestZipSlipGuard:
    """Verify _extract_zip validates member paths."""

    def test_extract_zip_validates_paths(self) -> None:
        """_extract_zip must validate all member paths resolve within extract_dir."""
        import inspect
        from scripts.download_nri_data import _extract_zip
        source = inspect.getsource(_extract_zip)
        assert "resolve" in source or "is_relative_to" in source, (
            "_extract_zip must validate extracted paths resolve within extract_dir"
        )
