"""Tests for NRI expanded metrics extraction pipeline.

Covers:
- CT FIPS mapping completeness, roundtrip, non-CT untouched
- National percentile computation: ranked, single, zero, tied, range
- NRIExpandedBuilder: init, SHA256, mismatch warning, missing headers,
  area-weighted aggregation, weight normalization, zero weight fallback,
  coverage_pct, top hazards, hazard count, path traversal, atomic write
- Integration test: conditional on NRI CSV availability
"""

import csv
import hashlib
import json
import logging
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.packets.nri_expanded import (
    CT_LEGACY_TO_PLANNING,
    CT_PLANNING_TO_LEGACY,
    NRIExpandedBuilder,
    _compute_sha256,
    _REQUIRED_HEADERS,
    validate_nri_checksum,
)
from src.paths import NRI_DIR


# ---------------------------------------------------------------------------
# -- Fixtures --
# ---------------------------------------------------------------------------


@pytest.fixture
def minimal_config():
    """Minimal config dict for NRIExpandedBuilder."""
    return {}


@pytest.fixture
def nri_csv_content():
    """Minimal NRI CSV content with required headers and 3 counties."""
    headers = [
        "STCOFIPS", "COUNTY", "STATE", "RISK_SCORE", "RISK_RATNG",
        "EAL_VALT", "EAL_VALB", "EAL_VALP", "EAL_VALA", "EAL_VALPE",
        "SOVI_SCORE", "RESL_SCORE", "POPULATION", "BUILDVALUE",
    ]
    # Add per-hazard columns for WFIR and HWAV
    for code in ["WFIR", "HWAV"]:
        headers.extend([f"{code}_EALT", f"{code}_RISKS"])

    rows = [
        {
            "STCOFIPS": "06001", "COUNTY": "Alameda", "STATE": "CA",
            "RISK_SCORE": "30.0", "RISK_RATNG": "Relatively Moderate",
            "EAL_VALT": "1000000", "EAL_VALB": "400000", "EAL_VALP": "300000",
            "EAL_VALA": "200000", "EAL_VALPE": "100000",
            "SOVI_SCORE": "45.0", "RESL_SCORE": "55.0",
            "POPULATION": "1500000", "BUILDVALUE": "500000000",
            "WFIR_EALT": "200000", "WFIR_RISKS": "20.0",
            "HWAV_EALT": "150000", "HWAV_RISKS": "15.0",
        },
        {
            "STCOFIPS": "06037", "COUNTY": "Los Angeles", "STATE": "CA",
            "RISK_SCORE": "60.0", "RISK_RATNG": "Relatively High",
            "EAL_VALT": "5000000", "EAL_VALB": "2000000", "EAL_VALP": "1500000",
            "EAL_VALA": "1000000", "EAL_VALPE": "500000",
            "SOVI_SCORE": "65.0", "RESL_SCORE": "35.0",
            "POPULATION": "10000000", "BUILDVALUE": "2000000000",
            "WFIR_EALT": "1000000", "WFIR_RISKS": "50.0",
            "HWAV_EALT": "800000", "HWAV_RISKS": "40.0",
        },
        {
            "STCOFIPS": "06073", "COUNTY": "San Diego", "STATE": "CA",
            "RISK_SCORE": "45.0", "RISK_RATNG": "Relatively Moderate",
            "EAL_VALT": "2000000", "EAL_VALB": "800000", "EAL_VALP": "600000",
            "EAL_VALA": "400000", "EAL_VALPE": "200000",
            "SOVI_SCORE": "50.0", "RESL_SCORE": "48.0",
            "POPULATION": "3000000", "BUILDVALUE": "800000000",
            "WFIR_EALT": "500000", "WFIR_RISKS": "35.0",
            "HWAV_EALT": "300000", "HWAV_RISKS": "25.0",
        },
    ]
    return headers, rows


@pytest.fixture
def nri_csv_file(tmp_path, nri_csv_content):
    """Write a test NRI CSV file and return its path."""
    headers, rows = nri_csv_content
    csv_path = tmp_path / "NRI_Table_Counties.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    return csv_path


@pytest.fixture
def crosswalk_file(tmp_path):
    """Write a test crosswalk JSON and return its path."""
    crosswalk = {
        "mappings": {
            "GEOID_A": "epa_100000001",
            "GEOID_B": "epa_100000002",
        }
    }
    path = tmp_path / "crosswalk.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(crosswalk, f)
    return path


@pytest.fixture
def area_weights_file(tmp_path):
    """Write a test area weights JSON and return its path."""
    weights = {
        "crosswalk": {
            "GEOID_A": [
                {"county_fips": "06001", "weight": 0.6, "overlap_area_sqkm": 100},
                {"county_fips": "06037", "weight": 0.4, "overlap_area_sqkm": 80},
            ],
            "GEOID_B": [
                {"county_fips": "06073", "weight": 1.0, "overlap_area_sqkm": 200},
            ],
        },
        "metadata": {
            "total_aiannh_entities": 2,
            "total_county_links": 3,
        },
    }
    path = tmp_path / "weights.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(weights, f)
    return path


@pytest.fixture
def builder_with_data(tmp_path, nri_csv_file, crosswalk_file, area_weights_file):
    """Create an NRIExpandedBuilder with all test data loaded."""
    config = {
        "nri_expanded": {
            "nri_csv_path": str(nri_csv_file),
            "output_dir": str(tmp_path / "output"),
        },
    }

    with (
        patch("src.packets.nri_expanded.AIANNH_CROSSWALK_PATH", crosswalk_file),
        patch("src.packets.nri_expanded.TRIBAL_COUNTY_WEIGHTS_PATH", area_weights_file),
    ):
        builder = NRIExpandedBuilder(config)
        builder._load_nri_csv()
        builder.compute_national_percentiles()

    return builder


# ---------------------------------------------------------------------------
# -- TestCTFIPSMapping --
# ---------------------------------------------------------------------------


class TestCTFIPSMapping:
    """Test Connecticut FIPS code mapping completeness and correctness."""

    def test_legacy_to_planning_has_8_entries(self):
        """CT has 8 legacy counties mapped to 8 planning regions."""
        assert len(CT_LEGACY_TO_PLANNING) == 8

    def test_planning_to_legacy_has_8_entries(self):
        """Reverse mapping has same count."""
        assert len(CT_PLANNING_TO_LEGACY) == 8

    def test_roundtrip_legacy_to_planning_to_legacy(self):
        """Every legacy FIPS roundtrips through planning back to itself."""
        for legacy, planning in CT_LEGACY_TO_PLANNING.items():
            assert CT_PLANNING_TO_LEGACY[planning] == legacy

    def test_roundtrip_planning_to_legacy_to_planning(self):
        """Every planning FIPS roundtrips through legacy back to itself."""
        for planning, legacy in CT_PLANNING_TO_LEGACY.items():
            assert CT_LEGACY_TO_PLANNING[legacy] == planning

    def test_all_legacy_start_with_09(self):
        """All legacy CT FIPS start with '09' (CT state prefix)."""
        for fips in CT_LEGACY_TO_PLANNING:
            assert fips.startswith("09"), f"Legacy FIPS {fips} doesn't start with 09"

    def test_all_planning_start_with_09(self):
        """All planning region FIPS start with '09' (CT state prefix)."""
        for fips in CT_PLANNING_TO_LEGACY:
            assert fips.startswith("09"), f"Planning FIPS {fips} doesn't start with 09"

    def test_non_ct_fips_not_in_mapping(self):
        """Non-CT FIPS codes are not affected by mapping."""
        assert "06001" not in CT_LEGACY_TO_PLANNING
        assert "06001" not in CT_PLANNING_TO_LEGACY
        assert "36061" not in CT_LEGACY_TO_PLANNING

    def test_legacy_range(self):
        """Legacy FIPS are odd numbers 09001-09015."""
        for fips in CT_LEGACY_TO_PLANNING:
            num = int(fips)
            assert 9001 <= num <= 9015

    def test_planning_range(self):
        """Planning region FIPS are 09110-09190."""
        for fips in CT_PLANNING_TO_LEGACY:
            num = int(fips)
            assert 9110 <= num <= 9190


# ---------------------------------------------------------------------------
# -- TestNationalPercentile --
# ---------------------------------------------------------------------------


class TestNationalPercentile:
    """Test national percentile computation from RISK_SCORE ranking."""

    def test_three_counties_ranked(self, builder_with_data):
        """Three counties with distinct scores: percentiles are 0, 50, 100."""
        b = builder_with_data
        # Scores: 30.0, 45.0, 60.0 -> sorted ascending
        assert b._get_risk_percentile(30.0) == 0.0
        assert b._get_risk_percentile(45.0) == 50.0
        assert b._get_risk_percentile(60.0) == 100.0

    def test_single_county_gives_50(self):
        """Single county in percentile base -> 50.0."""
        builder = MagicMock()
        builder._sorted_risk_scores = [42.0]
        result = NRIExpandedBuilder._get_risk_percentile(builder, 42.0)
        assert result == 50.0

    def test_zero_score_gives_zero(self, builder_with_data):
        """Zero risk score always returns 0.0 percentile."""
        assert builder_with_data._get_risk_percentile(0.0) == 0.0

    def test_negative_score_gives_zero(self, builder_with_data):
        """Negative score (shouldn't happen but defensive) returns 0.0."""
        assert builder_with_data._get_risk_percentile(-5.0) == 0.0

    def test_tied_scores(self):
        """Tied scores get same percentile (bisect_left behavior)."""
        builder = MagicMock()
        builder._sorted_risk_scores = [10.0, 20.0, 20.0, 30.0]
        # bisect_left for 20.0 in [10, 20, 20, 30] -> index 1
        # percentile = 1 / (4-1) * 100 = 33.33
        result = NRIExpandedBuilder._get_risk_percentile(builder, 20.0)
        assert result == pytest.approx(33.33, abs=0.01)

    def test_percentile_range_check(self, builder_with_data):
        """Percentile is always in [0.0, 100.0]."""
        # Score higher than any county
        result = builder_with_data._get_risk_percentile(999.0)
        assert 0.0 <= result <= 100.0

        # Score between existing counties
        result = builder_with_data._get_risk_percentile(40.0)
        assert 0.0 <= result <= 100.0

    def test_empty_percentile_base(self):
        """No counties in percentile base -> 0.0 for any score."""
        builder = MagicMock()
        builder._sorted_risk_scores = []
        result = NRIExpandedBuilder._get_risk_percentile(builder, 50.0)
        assert result == 0.0

    def test_exact_match_highest_score(self, builder_with_data):
        """Score matching the highest county gets 100.0 percentile."""
        # Highest is 60.0 in the fixture
        assert builder_with_data._get_risk_percentile(60.0) == 100.0


# ---------------------------------------------------------------------------
# -- TestNRIExpandedBuilder --
# ---------------------------------------------------------------------------


class TestNRIExpandedBuilder:
    """Test NRIExpandedBuilder initialization and core methods."""

    def test_init_defaults(self, tmp_path):
        """Builder initializes with default paths when no config provided."""
        with (
            patch("src.packets.nri_expanded.AIANNH_CROSSWALK_PATH", tmp_path / "no_crosswalk.json"),
            patch("src.packets.nri_expanded.TRIBAL_COUNTY_WEIGHTS_PATH", tmp_path / "no_weights.json"),
        ):
            builder = NRIExpandedBuilder({})

        assert builder.nri_csv_path == NRI_DIR / "NRI_Table_Counties.csv"
        assert builder.expected_sha256 is None

    def test_init_with_config(self, tmp_path, crosswalk_file, area_weights_file):
        """Builder reads config overrides for paths and SHA256."""
        config = {
            "nri_expanded": {
                "nri_csv_path": str(tmp_path / "custom.csv"),
                "expected_sha256": "abc123",
                "output_dir": str(tmp_path / "custom_out"),
            }
        }
        with (
            patch("src.packets.nri_expanded.AIANNH_CROSSWALK_PATH", crosswalk_file),
            patch("src.packets.nri_expanded.TRIBAL_COUNTY_WEIGHTS_PATH", area_weights_file),
        ):
            builder = NRIExpandedBuilder(config)

        assert builder.nri_csv_path == tmp_path / "custom.csv"
        assert builder.expected_sha256 == "abc123"
        assert builder.output_dir == tmp_path / "custom_out"

    def test_sha256_computation(self, nri_csv_file):
        """SHA256 is computed correctly for a known file."""
        computed = _compute_sha256(nri_csv_file)
        # Verify manually
        sha256 = hashlib.sha256()
        with open(nri_csv_file, "rb") as f:
            while chunk := f.read(65536):
                sha256.update(chunk)
        expected = sha256.hexdigest()
        assert computed == expected

    def test_sha256_mismatch_warning(
        self, tmp_path, nri_csv_file, crosswalk_file, area_weights_file, caplog
    ):
        """SHA256 mismatch logs WARNING but does not error."""
        config = {
            "nri_expanded": {
                "nri_csv_path": str(nri_csv_file),
                "expected_sha256": "0000000000000000000000000000000000000000000000000000000000000000",
                "output_dir": str(tmp_path / "output"),
            }
        }
        with (
            patch("src.packets.nri_expanded.AIANNH_CROSSWALK_PATH", crosswalk_file),
            patch("src.packets.nri_expanded.TRIBAL_COUNTY_WEIGHTS_PATH", area_weights_file),
            caplog.at_level(logging.WARNING, logger="src.packets.nri_expanded"),
        ):
            builder = NRIExpandedBuilder(config)
            builder._load_nri_csv()

        assert "SHA256 mismatch" in caplog.text

    def test_sha256_match_no_warning(
        self, tmp_path, nri_csv_file, crosswalk_file, area_weights_file, caplog
    ):
        """SHA256 match logs INFO, no mismatch warning."""
        actual_sha = _compute_sha256(nri_csv_file)
        config = {
            "nri_expanded": {
                "nri_csv_path": str(nri_csv_file),
                "expected_sha256": actual_sha,
                "output_dir": str(tmp_path / "output"),
            }
        }
        with (
            patch("src.packets.nri_expanded.AIANNH_CROSSWALK_PATH", crosswalk_file),
            patch("src.packets.nri_expanded.TRIBAL_COUNTY_WEIGHTS_PATH", area_weights_file),
            caplog.at_level(logging.WARNING, logger="src.packets.nri_expanded"),
        ):
            builder = NRIExpandedBuilder(config)
            builder._load_nri_csv()

        assert "SHA256 mismatch" not in caplog.text

    def test_missing_header_warning(
        self, tmp_path, crosswalk_file, area_weights_file, caplog
    ):
        """Missing required headers logged as WARNING."""
        # Write CSV with incomplete headers
        csv_path = tmp_path / "incomplete.csv"
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["STCOFIPS", "RISK_SCORE"])
            writer.writeheader()
            writer.writerow({"STCOFIPS": "06001", "RISK_SCORE": "30.0"})

        config = {
            "nri_expanded": {
                "nri_csv_path": str(csv_path),
                "output_dir": str(tmp_path / "output"),
            }
        }
        with (
            patch("src.packets.nri_expanded.AIANNH_CROSSWALK_PATH", crosswalk_file),
            patch("src.packets.nri_expanded.TRIBAL_COUNTY_WEIGHTS_PATH", area_weights_file),
            caplog.at_level(logging.WARNING, logger="src.packets.nri_expanded"),
        ):
            builder = NRIExpandedBuilder(config)
            builder._load_nri_csv()

        assert "missing required headers" in caplog.text

    def test_area_weighted_aggregation(self, builder_with_data):
        """Area-weighted aggregation produces correct values for Tribe 1."""
        b = builder_with_data
        # Tribe 1 (epa_100000001) has GEOID_A -> 06001 (w=0.6) + 06037 (w=0.4)
        profile = b._aggregate_tribe_nri("epa_100000001", ["GEOID_A"])

        # risk_score = 30.0 * 0.6 + 60.0 * 0.4 = 18.0 + 24.0 = 42.0
        assert profile["risk_score"] == pytest.approx(42.0, abs=0.01)

        # eal_total = 1000000 * 0.6 + 5000000 * 0.4 = 600000 + 2000000 = 2600000
        assert profile["eal_total"] == pytest.approx(2600000.0, abs=0.01)

        # eal_buildings = 400000 * 0.6 + 2000000 * 0.4 = 240000 + 800000 = 1040000
        assert profile["eal_buildings"] == pytest.approx(1040000.0, abs=0.01)

    def test_weight_normalization(self, builder_with_data):
        """Weights sum to 1.0 after normalization."""
        b = builder_with_data
        profile = b._aggregate_tribe_nri("epa_100000001", ["GEOID_A"])
        # community_resilience = 55.0 * 0.6 + 35.0 * 0.4 = 33.0 + 14.0 = 47.0
        assert profile["community_resilience"] == pytest.approx(47.0, abs=0.01)

    def test_zero_weight_fallback(self, tmp_path, crosswalk_file):
        """Zero total weight falls back to equal weighting."""
        # Area weights with 0 weight
        weights = {
            "crosswalk": {
                "GEOID_Z": [
                    {"county_fips": "06001", "weight": 0.0, "overlap_area_sqkm": 0},
                ],
            },
        }
        weights_path = tmp_path / "zero_weights.json"
        with open(weights_path, "w", encoding="utf-8") as f:
            json.dump(weights, f)

        # Write a CSV with county 06001
        csv_path = tmp_path / "NRI_Table_Counties.csv"
        headers = list(_REQUIRED_HEADERS) + ["COUNTY", "STATE"]
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerow({
                "STCOFIPS": "06001", "RISK_SCORE": "40.0", "RISK_RATNG": "Moderate",
                "EAL_VALT": "100", "EAL_VALB": "50", "EAL_VALP": "30",
                "EAL_VALA": "10", "EAL_VALPE": "10",
                "SOVI_SCORE": "30", "RESL_SCORE": "60",
                "POPULATION": "1000", "BUILDVALUE": "5000",
                "COUNTY": "Test", "STATE": "CA",
            })

        # Build crosswalk that maps GEOID_Z -> epa_100000001
        cw = {"mappings": {"GEOID_Z": "epa_100000001"}}
        cw_path = tmp_path / "crosswalk.json"
        with open(cw_path, "w", encoding="utf-8") as f:
            json.dump(cw, f)

        config = {
            "nri_expanded": {
                "nri_csv_path": str(csv_path),
                "output_dir": str(tmp_path / "output"),
            }
        }
        with (
            patch("src.packets.nri_expanded.AIANNH_CROSSWALK_PATH", cw_path),
            patch("src.packets.nri_expanded.TRIBAL_COUNTY_WEIGHTS_PATH", weights_path),
        ):
            builder = NRIExpandedBuilder(config)
            builder._load_nri_csv()
            builder.compute_national_percentiles()

        profile = builder._aggregate_tribe_nri("epa_100000001", ["GEOID_Z"])
        # With zero weight fallback, should use equal weight (1/1 = 1.0)
        assert profile["risk_score"] == pytest.approx(40.0, abs=0.01)
        assert profile["coverage_pct"] == 0.0

    def test_coverage_pct(self, builder_with_data):
        """Coverage percent reflects matched vs total weight."""
        b = builder_with_data
        # Tribe 2 has GEOID_B -> 06073 (w=1.0), all matched
        profile = b._aggregate_tribe_nri("epa_100000002", ["GEOID_B"])
        assert profile["coverage_pct"] == pytest.approx(1.0, abs=0.001)

    def test_top_hazards_sorted(self, builder_with_data):
        """Top hazards are sorted by EAL descending."""
        b = builder_with_data
        profile = b._aggregate_tribe_nri("epa_100000001", ["GEOID_A"])
        if len(profile["top_hazards"]) >= 2:
            eals = [h["eal_total"] for h in profile["top_hazards"]]
            assert eals == sorted(eals, reverse=True)

    def test_top_hazards_max_five(self, builder_with_data):
        """Top hazards list contains at most 5 entries."""
        b = builder_with_data
        profile = b._aggregate_tribe_nri("epa_100000001", ["GEOID_A"])
        assert len(profile["top_hazards"]) <= 5

    def test_hazard_count(self, builder_with_data):
        """Hazard count equals number of non-zero EAL hazards."""
        b = builder_with_data
        profile = b._aggregate_tribe_nri("epa_100000001", ["GEOID_A"])
        # WFIR and HWAV both have non-zero EAL in test data
        assert profile["hazard_count"] >= 2

    def test_path_traversal_rejection(self, builder_with_data, tmp_path):
        """Atomic write rejects path traversal attempts."""
        b = builder_with_data
        bad_path = tmp_path / ".." / "escape" / "malicious.json"
        with pytest.raises(ValueError, match="Path traversal"):
            b._atomic_write(bad_path, {"test": True})

    def test_atomic_write_creates_file(self, builder_with_data, tmp_path):
        """Atomic write creates the target JSON file."""
        b = builder_with_data
        output_path = tmp_path / "test_output.json"
        test_data = {"tribe_id": "epa_100000001", "test": True}
        b._atomic_write(output_path, test_data)

        assert output_path.exists()
        with open(output_path, encoding="utf-8") as f:
            loaded = json.load(f)
        assert loaded["tribe_id"] == "epa_100000001"

    def test_atomic_write_cleanup_on_error(self, builder_with_data, tmp_path):
        """Atomic write cleans up temp file on serialization error."""
        b = builder_with_data
        output_path = tmp_path / "will_fail.json"

        # Object that can't be serialized
        class NonSerializable:
            pass

        with pytest.raises(TypeError):
            b._atomic_write(output_path, {"bad": NonSerializable()})

        # Target file should not exist
        assert not output_path.exists()
        # Temp files should be cleaned up
        tmp_files = list(tmp_path.glob("will_fail_*.tmp"))
        assert len(tmp_files) == 0

    def test_empty_profile_structure(self, builder_with_data):
        """Empty profile has all required fields with zero/empty values."""
        b = builder_with_data
        profile = b._empty_profile("epa_100000099", "test note")
        assert profile["tribe_id"] == "epa_100000099"
        assert profile["risk_score"] == 0.0
        assert profile["risk_percentile"] == 0.0
        assert profile["eal_total"] == 0.0
        assert profile["eal_buildings"] == 0.0
        assert profile["eal_population"] == 0.0
        assert profile["eal_agriculture"] == 0.0
        assert profile["eal_population_equivalence"] == 0.0
        assert profile["community_resilience"] == 0.0
        assert profile["social_vulnerability_nri"] == 0.0
        assert profile["hazard_count"] == 0
        assert profile["top_hazards"] == []
        assert profile["coverage_pct"] == 0.0
        assert profile["note"] == "test note"

    def test_no_geoids_gives_empty_profile(self, builder_with_data):
        """Tribe with no GEOIDs gets empty profile."""
        b = builder_with_data
        profile = b._aggregate_tribe_nri("epa_100000099", [])
        assert profile["risk_score"] == 0.0
        assert "note" in profile

    def test_no_county_data_gives_empty_profile(self, tmp_path, crosswalk_file):
        """Builder with no county data gives empty profiles."""
        weights = {"crosswalk": {}, "metadata": {}}
        weights_path = tmp_path / "empty_weights.json"
        with open(weights_path, "w", encoding="utf-8") as f:
            json.dump(weights, f)

        with (
            patch("src.packets.nri_expanded.AIANNH_CROSSWALK_PATH", crosswalk_file),
            patch("src.packets.nri_expanded.TRIBAL_COUNTY_WEIGHTS_PATH", weights_path),
        ):
            builder = NRIExpandedBuilder({})

        profile = builder._aggregate_tribe_nri("epa_100000001", ["GEOID_A"])
        assert profile["risk_score"] == 0.0
        assert "NRI county data not loaded" in profile.get("note", "")

    def test_social_vulnerability_nri_extracted(self, builder_with_data):
        """SOVI_SCORE is extracted and weighted correctly."""
        b = builder_with_data
        profile = b._aggregate_tribe_nri("epa_100000002", ["GEOID_B"])
        # Tribe 2: only county 06073, weight 1.0, SOVI_SCORE = 50.0
        assert profile["social_vulnerability_nri"] == pytest.approx(50.0, abs=0.01)

    def test_community_resilience_extracted(self, builder_with_data):
        """RESL_SCORE is extracted and weighted correctly."""
        b = builder_with_data
        profile = b._aggregate_tribe_nri("epa_100000002", ["GEOID_B"])
        # Tribe 2: only county 06073, RESL_SCORE = 48.0
        assert profile["community_resilience"] == pytest.approx(48.0, abs=0.01)

    def test_eal_breakdown_sums(self, builder_with_data):
        """Individual EAL components sum approximately to eal_total."""
        b = builder_with_data
        profile = b._aggregate_tribe_nri("epa_100000002", ["GEOID_B"])
        # 06073 only: total=2000000, buildings=800000, pop=600000, ag=400000, pe=200000
        # Sum of parts = 800000+600000+400000+200000 = 2000000 = total
        components_sum = (
            profile["eal_buildings"]
            + profile["eal_population"]
            + profile["eal_agriculture"]
            + profile["eal_population_equivalence"]
        )
        assert components_sum == pytest.approx(profile["eal_total"], rel=0.01)


# ---------------------------------------------------------------------------
# -- TestValidateNRIChecksum --
# ---------------------------------------------------------------------------


class TestValidateNRIChecksum:
    """Test the public validate_nri_checksum function."""

    def test_valid_checksum(self, nri_csv_file):
        """Returns True for matching checksum."""
        actual_sha = _compute_sha256(nri_csv_file)
        assert validate_nri_checksum(nri_csv_file, actual_sha) is True

    def test_invalid_checksum(self, nri_csv_file):
        """Returns False for non-matching checksum."""
        assert validate_nri_checksum(nri_csv_file, "0" * 64) is False

    def test_case_insensitive(self, nri_csv_file):
        """Checksum comparison is case-insensitive."""
        actual_sha = _compute_sha256(nri_csv_file)
        assert validate_nri_checksum(nri_csv_file, actual_sha.upper()) is True


# ---------------------------------------------------------------------------
# -- TestBuildAllProfiles --
# ---------------------------------------------------------------------------


class TestBuildAllProfiles:
    """Test the full build_all_profiles orchestration."""

    def test_build_all_profiles_writes_files(
        self, tmp_path, nri_csv_file, crosswalk_file, area_weights_file
    ):
        """build_all_profiles writes NRI expanded JSON files."""
        output_dir = tmp_path / "nri_output"
        config = {
            "nri_expanded": {
                "nri_csv_path": str(nri_csv_file),
                "output_dir": str(output_dir),
            }
        }
        with (
            patch("src.packets.nri_expanded.AIANNH_CROSSWALK_PATH", crosswalk_file),
            patch("src.packets.nri_expanded.TRIBAL_COUNTY_WEIGHTS_PATH", area_weights_file),
            patch("src.packets.nri_expanded.OUTPUTS_DIR", tmp_path / "outputs"),
        ):
            builder = NRIExpandedBuilder(config)
            count = builder.build_all_profiles()

        assert count == 2  # Two tribes in crosswalk
        assert (output_dir / "epa_100000001_nri_expanded.json").exists()
        assert (output_dir / "epa_100000002_nri_expanded.json").exists()

    def test_build_all_profiles_content_valid(
        self, tmp_path, nri_csv_file, crosswalk_file, area_weights_file
    ):
        """Built profiles contain valid NRI expanded data."""
        output_dir = tmp_path / "nri_output"
        config = {
            "nri_expanded": {
                "nri_csv_path": str(nri_csv_file),
                "output_dir": str(output_dir),
            }
        }
        with (
            patch("src.packets.nri_expanded.AIANNH_CROSSWALK_PATH", crosswalk_file),
            patch("src.packets.nri_expanded.TRIBAL_COUNTY_WEIGHTS_PATH", area_weights_file),
            patch("src.packets.nri_expanded.OUTPUTS_DIR", tmp_path / "outputs"),
        ):
            builder = NRIExpandedBuilder(config)
            builder.build_all_profiles()

        with open(output_dir / "epa_100000001_nri_expanded.json", encoding="utf-8") as f:
            profile = json.load(f)

        assert profile["tribe_id"] == "epa_100000001"
        assert profile["risk_score"] > 0
        assert profile["nri_sha256"] != ""
        assert "generated_at" in profile
        assert profile["risk_percentile"] >= 0
        assert profile["risk_percentile"] <= 100

    def test_build_all_profiles_no_csv(self, tmp_path, crosswalk_file, area_weights_file):
        """build_all_profiles returns 0 when CSV doesn't exist."""
        config = {
            "nri_expanded": {
                "nri_csv_path": str(tmp_path / "nonexistent.csv"),
                "output_dir": str(tmp_path / "nri_output"),
            }
        }
        with (
            patch("src.packets.nri_expanded.AIANNH_CROSSWALK_PATH", crosswalk_file),
            patch("src.packets.nri_expanded.TRIBAL_COUNTY_WEIGHTS_PATH", area_weights_file),
        ):
            builder = NRIExpandedBuilder(config)
            count = builder.build_all_profiles()

        assert count == 0

    def test_coverage_report_generated(
        self, tmp_path, nri_csv_file, crosswalk_file, area_weights_file
    ):
        """build_all_profiles generates a coverage report."""
        output_dir = tmp_path / "nri_output"
        outputs_dir = tmp_path / "outputs"
        config = {
            "nri_expanded": {
                "nri_csv_path": str(nri_csv_file),
                "output_dir": str(output_dir),
            }
        }
        with (
            patch("src.packets.nri_expanded.AIANNH_CROSSWALK_PATH", crosswalk_file),
            patch("src.packets.nri_expanded.TRIBAL_COUNTY_WEIGHTS_PATH", area_weights_file),
            patch("src.packets.nri_expanded.OUTPUTS_DIR", outputs_dir),
        ):
            builder = NRIExpandedBuilder(config)
            builder.build_all_profiles()

        report_path = outputs_dir / "nri_expanded_coverage_report.json"
        assert report_path.exists()
        with open(report_path, encoding="utf-8") as f:
            report = json.load(f)
        assert report["summary"]["profiles_written"] == 2
        assert report["nri_sha256"] != ""


# ---------------------------------------------------------------------------
# -- TestCTFIPSInCSV --
# ---------------------------------------------------------------------------


class TestCTFIPSInCSV:
    """Test CT FIPS remapping during CSV loading."""

    def test_ct_legacy_remapped_to_planning(self, tmp_path):
        """Legacy CT FIPS in CSV are remapped when crosswalk uses planning."""
        csv_path = tmp_path / "NRI_Table_Counties.csv"
        headers = list(_REQUIRED_HEADERS) + ["COUNTY", "STATE"]
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerow({
                "STCOFIPS": "09001", "RISK_SCORE": "30.0", "RISK_RATNG": "Moderate",
                "EAL_VALT": "100", "EAL_VALB": "50", "EAL_VALP": "30",
                "EAL_VALA": "10", "EAL_VALPE": "10",
                "SOVI_SCORE": "30", "RESL_SCORE": "60",
                "POPULATION": "1000", "BUILDVALUE": "5000",
                "COUNTY": "Fairfield", "STATE": "CT",
            })

        # Area weights use planning region format
        weights = {
            "crosswalk": {
                "GEOID_CT": [
                    {"county_fips": "09120", "weight": 1.0, "overlap_area_sqkm": 100},
                ],
            },
        }
        weights_path = tmp_path / "weights.json"
        with open(weights_path, "w", encoding="utf-8") as f:
            json.dump(weights, f)

        cw = {"mappings": {"GEOID_CT": "epa_100000099"}}
        cw_path = tmp_path / "crosswalk.json"
        with open(cw_path, "w", encoding="utf-8") as f:
            json.dump(cw, f)

        config = {
            "nri_expanded": {
                "nri_csv_path": str(csv_path),
                "output_dir": str(tmp_path / "output"),
            }
        }
        with (
            patch("src.packets.nri_expanded.AIANNH_CROSSWALK_PATH", cw_path),
            patch("src.packets.nri_expanded.TRIBAL_COUNTY_WEIGHTS_PATH", weights_path),
        ):
            builder = NRIExpandedBuilder(config)
            county_data = builder._load_nri_csv()

        # 09001 should be remapped to 09120
        assert "09120" in county_data
        assert "09001" not in county_data


# ---------------------------------------------------------------------------
# -- TestNRIExpandedIntegration --
# ---------------------------------------------------------------------------


class TestNRIExpandedIntegration:
    """Integration tests conditional on real NRI CSV availability."""

    @pytest.fixture(autouse=True)
    def skip_if_no_data(self):
        """Skip integration tests if NRI CSV is not available."""
        csv_path = NRI_DIR / "NRI_Table_Counties.csv"
        if not csv_path.exists():
            pytest.skip(
                f"NRI CSV not available at {csv_path} -- "
                "skipping integration tests"
            )

    def test_real_csv_loads(self):
        """Real NRI CSV loads without errors."""
        csv_path = NRI_DIR / "NRI_Table_Counties.csv"
        sha = _compute_sha256(csv_path)
        assert len(sha) == 64
        assert all(c in "0123456789abcdef" for c in sha)
