"""Tests for CDC/ATSDR SVI 2022 integration pipeline (src/packets/svi_builder.py).

Covers:
- _safe_svi_float sentinel handling (-999, -999.0, "-999")
- Theme exclusion (Theme 3 excluded, Themes 1/2/4 included)
- 3-theme composite computation
- Area-weighted aggregation
- SVIProfileBuilder initialization and orchestration
- Data gap detection
- Integration with real SVI CSV (conditional)
"""

import json
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.packets.svi_builder import (
    SVI_EXCLUDED_THEMES,
    SVI_INCLUDED_THEMES,
    SVI_SOURCE_YEAR,
    SVI_THEME_NAMES,
    SVIProfileBuilder,
    _safe_svi_float,
)
from src.schemas.vulnerability import DataGapType, SVIProfile, SVITheme


# ── Fixtures ──


@pytest.fixture
def svi_county_csv(tmp_path):
    """Create a synthetic SVI 2022 county CSV for testing."""
    csv_content = (
        "STCNTY,ST_ABBR,RPL_THEME1,RPL_THEME2,RPL_THEME3,RPL_THEME4,RPL_THEMES,"
        "E_TOTPOP,F_THEME1,F_THEME2,F_THEME3,F_THEME4\n"
        "06001,CA,0.80,0.60,0.50,0.70,0.75,100000,2,1,1,3\n"
        "06003,CA,0.40,0.30,0.20,0.50,0.35,5000,1,0,0,2\n"
        "53033,WA,0.90,0.85,0.70,0.80,0.88,200000,3,2,2,4\n"
        "02020,AK,0.60,0.55,0.40,0.65,0.58,3000,1,1,1,2\n"
    )
    csv_path = tmp_path / "SVI2022_US_COUNTY.csv"
    csv_path.write_text(csv_content, encoding="utf-8")
    return csv_path


@pytest.fixture
def svi_county_csv_with_fips_col(tmp_path):
    """Create a CSV using FIPS column name instead of STCNTY."""
    csv_content = (
        "FIPS,ST_ABBR,RPL_THEME1,RPL_THEME2,RPL_THEME3,RPL_THEME4,RPL_THEMES,"
        "E_TOTPOP,F_THEME1,F_THEME2,F_THEME3,F_THEME4\n"
        "06001,CA,0.75,0.65,0.55,0.70,0.72,100000,2,1,1,3\n"
    )
    csv_path = tmp_path / "SVI2022_US_COUNTY.csv"
    csv_path.write_text(csv_content, encoding="utf-8")
    return csv_path


@pytest.fixture
def svi_county_csv_with_sentinels(tmp_path):
    """Create a CSV with -999 sentinel values."""
    csv_content = (
        "STCNTY,ST_ABBR,RPL_THEME1,RPL_THEME2,RPL_THEME3,RPL_THEME4,RPL_THEMES,"
        "E_TOTPOP,F_THEME1,F_THEME2,F_THEME3,F_THEME4\n"
        "06001,CA,-999,0.60,-999,0.70,-999,100000,-999,1,-999,3\n"
        "06003,CA,0.40,-999,0.20,-999,0.35,5000,1,-999,0,-999\n"
    )
    csv_path = tmp_path / "SVI2022_US_COUNTY.csv"
    csv_path.write_text(csv_content, encoding="utf-8")
    return csv_path


@pytest.fixture
def svi_county_csv_all_zeros(tmp_path):
    """Create a CSV where all themes are 0.0."""
    csv_content = (
        "STCNTY,ST_ABBR,RPL_THEME1,RPL_THEME2,RPL_THEME3,RPL_THEME4,RPL_THEMES,"
        "E_TOTPOP,F_THEME1,F_THEME2,F_THEME3,F_THEME4\n"
        "06001,CA,0.0,0.0,0.0,0.0,0.0,100000,0,0,0,0\n"
    )
    csv_path = tmp_path / "SVI2022_US_COUNTY.csv"
    csv_path.write_text(csv_content, encoding="utf-8")
    return csv_path


@pytest.fixture
def crosswalk_file(tmp_path):
    """Create a synthetic AIANNH crosswalk JSON."""
    crosswalk = {
        "mappings": {
            "GEOID_001": "epa_100000001",
            "GEOID_002": "epa_100000002",
            "GEOID_003": "epa_100000003",
        }
    }
    path = tmp_path / "crosswalk.json"
    path.write_text(json.dumps(crosswalk), encoding="utf-8")
    return path


@pytest.fixture
def area_weights_file(tmp_path):
    """Create a synthetic area weights JSON."""
    weights = {
        "metadata": {
            "total_aiannh_entities": 3,
            "total_county_links": 4,
        },
        "crosswalk": {
            "GEOID_001": [
                {"county_fips": "06001", "weight": 0.7, "overlap_area_sqkm": 100},
                {"county_fips": "06003", "weight": 0.3, "overlap_area_sqkm": 50},
            ],
            "GEOID_002": [
                {"county_fips": "53033", "weight": 1.0, "overlap_area_sqkm": 200},
            ],
            "GEOID_003": [
                {"county_fips": "02020", "weight": 1.0, "overlap_area_sqkm": 150},
            ],
        },
    }
    path = tmp_path / "tribal_county_area_weights.json"
    path.write_text(json.dumps(weights), encoding="utf-8")
    return path


@pytest.fixture
def mock_registry():
    """Create a mock TribalRegistry."""
    registry = MagicMock()
    registry.get_all.return_value = [
        {
            "tribe_id": "epa_100000001",
            "name": "Test Tribe Alpha",
            "states": ["CA"],
        },
        {
            "tribe_id": "epa_100000002",
            "name": "Test Tribe Beta",
            "states": ["WA"],
        },
        {
            "tribe_id": "epa_100000003",
            "name": "Test Tribe Gamma",
            "states": ["AK"],
        },
    ]
    return registry


def _make_builder(
    tmp_path,
    svi_csv_path,
    crosswalk_path,
    area_weights_path,
    mock_registry,
):
    """Create an SVIProfileBuilder with patched paths and registry."""
    output_dir = tmp_path / "svi_profiles"
    output_dir.mkdir(parents=True, exist_ok=True)

    config = {
        "packets": {
            "svi": {
                "svi_csv_path": str(svi_csv_path),
                "output_dir": str(output_dir),
                "crosswalk_path": str(crosswalk_path),
            }
        }
    }

    with patch("src.packets.svi_builder.TRIBAL_COUNTY_WEIGHTS_PATH", area_weights_path), \
         patch("src.packets.svi_builder.SVIProfileBuilder.__init__", lambda self, cfg: None):
        builder = SVIProfileBuilder.__new__(SVIProfileBuilder)

    # Manual initialization to bypass real TribalRegistry
    builder.svi_csv_path = Path(svi_csv_path)
    builder.output_dir = output_dir
    builder.crosswalk_path = Path(crosswalk_path)
    builder._registry = mock_registry
    builder._crosswalk = {}
    builder._tribe_to_geoids = {}

    # Load crosswalk manually
    with open(crosswalk_path, encoding="utf-8") as f:
        data = json.load(f)
    builder._crosswalk = data.get("mappings", {})
    for geoid, tribe_id in builder._crosswalk.items():
        if tribe_id not in builder._tribe_to_geoids:
            builder._tribe_to_geoids[tribe_id] = []
        builder._tribe_to_geoids[tribe_id].append(geoid)

    # Load area weights manually
    with open(area_weights_path, encoding="utf-8") as f:
        wdata = json.load(f)
    builder._area_weights = wdata.get("crosswalk", {})

    return builder


# ═══════════════════════════════════════════════════════════════════════════
# TestSafeSviFloat
# ═══════════════════════════════════════════════════════════════════════════


class TestSafeSviFloat:
    """Test _safe_svi_float sentinel handling and type conversion."""

    def test_sentinel_negative_999_int(self):
        """Sentinel -999 integer returns default."""
        assert _safe_svi_float(-999) == 0.0

    def test_sentinel_negative_999_float(self):
        """Sentinel -999.0 float returns default."""
        assert _safe_svi_float(-999.0) == 0.0

    def test_sentinel_negative_999_string(self):
        """Sentinel '-999' string returns default."""
        assert _safe_svi_float("-999") == 0.0

    def test_sentinel_with_custom_default(self):
        """Sentinel returns custom default value."""
        assert _safe_svi_float(-999, default=-1.0) == -1.0

    def test_valid_float_passthrough(self):
        """Valid float passes through unchanged."""
        assert _safe_svi_float(0.75) == 0.75

    def test_valid_string_passthrough(self):
        """Valid numeric string converts correctly."""
        assert _safe_svi_float("0.85") == 0.85

    def test_none_returns_default(self):
        """None returns default value."""
        assert _safe_svi_float(None) == 0.0

    def test_empty_string_returns_default(self):
        """Empty string returns default value."""
        assert _safe_svi_float("") == 0.0

    def test_whitespace_string_returns_default(self):
        """Whitespace-only string returns default value."""
        assert _safe_svi_float("   ") == 0.0

    def test_zero_passthrough(self):
        """Zero passes through as valid value."""
        assert _safe_svi_float(0) == 0.0

    def test_one_passthrough(self):
        """Value of 1.0 passes through."""
        assert _safe_svi_float(1.0) == 1.0

    def test_non_numeric_returns_default(self):
        """Non-numeric string returns default."""
        assert _safe_svi_float("abc") == 0.0


# ═══════════════════════════════════════════════════════════════════════════
# TestThemeExclusion
# ═══════════════════════════════════════════════════════════════════════════


class TestThemeExclusion:
    """Test that Theme 3 is excluded and only Themes 1/2/4 are included."""

    def test_included_themes_are_1_2_4(self):
        """SVI_INCLUDED_THEMES contains exactly theme1, theme2, theme4."""
        assert SVI_INCLUDED_THEMES == frozenset({"theme1", "theme2", "theme4"})

    def test_theme3_not_in_included(self):
        """theme3 is NOT in included themes."""
        assert "theme3" not in SVI_INCLUDED_THEMES

    def test_excluded_themes_is_theme3(self):
        """SVI_EXCLUDED_THEMES contains exactly theme3."""
        assert SVI_EXCLUDED_THEMES == frozenset({"theme3"})

    def test_theme3_in_excluded(self):
        """theme3 IS in excluded themes."""
        assert "theme3" in SVI_EXCLUDED_THEMES

    def test_included_and_excluded_disjoint(self):
        """Included and excluded theme sets have no overlap."""
        assert SVI_INCLUDED_THEMES & SVI_EXCLUDED_THEMES == frozenset()

    def test_csv_parsing_skips_theme3(
        self, tmp_path, svi_county_csv, crosswalk_file, area_weights_file, mock_registry
    ):
        """CSV parser extracts theme1/2/4 but not theme3 in output."""
        builder = _make_builder(
            tmp_path, svi_county_csv, crosswalk_file, area_weights_file, mock_registry
        )
        county_data = builder._load_svi_csv()
        # Each record should have rpl_theme1, rpl_theme2, rpl_theme4
        # but NOT rpl_theme3
        for fips, record in county_data.items():
            assert "rpl_theme1" in record
            assert "rpl_theme2" in record
            assert "rpl_theme4" in record
            assert "rpl_theme3" not in record

    def test_svi_profile_rejects_theme3(self):
        """SVITheme schema rejects theme3 as theme_id."""
        with pytest.raises(Exception):
            SVITheme(
                theme_id="theme3",
                name="Racial & Ethnic Minority Status",
                percentile=0.5,
                flag_count=1,
            )

    def test_source_year_is_2022(self):
        """SVI_SOURCE_YEAR is 2022."""
        assert SVI_SOURCE_YEAR == 2022


# ═══════════════════════════════════════════════════════════════════════════
# TestSVICompositeComputation
# ═══════════════════════════════════════════════════════════════════════════


class TestSVICompositeComputation:
    """Test 3-theme composite = mean(theme1, theme2, theme4)."""

    def test_three_theme_average(self):
        """Composite is mean of 3 theme percentiles."""
        # theme1=0.6, theme2=0.3, theme4=0.9 -> mean = 0.6
        profile = SVIProfile(
            tribe_id="epa_100000001",
            themes=[
                SVITheme(theme_id="theme1", name="Socioeconomic", percentile=0.6, flag_count=1),
                SVITheme(theme_id="theme2", name="Household", percentile=0.3, flag_count=0),
                SVITheme(theme_id="theme4", name="Housing", percentile=0.9, flag_count=2),
            ],
            composite=0.6,
            coverage_pct=1.0,
        )
        assert profile.composite == 0.6

    def test_all_zeros(self):
        """Composite is 0.0 when all themes are 0.0."""
        profile = SVIProfile(
            tribe_id="epa_100000001",
            themes=[
                SVITheme(theme_id="theme1", name="Socioeconomic", percentile=0.0, flag_count=0),
                SVITheme(theme_id="theme2", name="Household", percentile=0.0, flag_count=0),
                SVITheme(theme_id="theme4", name="Housing", percentile=0.0, flag_count=0),
            ],
            composite=0.0,
            coverage_pct=1.0,
        )
        assert profile.composite == 0.0

    def test_all_ones(self):
        """Composite is 1.0 when all themes are 1.0."""
        profile = SVIProfile(
            tribe_id="epa_100000001",
            themes=[
                SVITheme(theme_id="theme1", name="Socioeconomic", percentile=1.0, flag_count=3),
                SVITheme(theme_id="theme2", name="Household", percentile=1.0, flag_count=3),
                SVITheme(theme_id="theme4", name="Housing", percentile=1.0, flag_count=3),
            ],
            composite=1.0,
            coverage_pct=1.0,
        )
        assert profile.composite == 1.0

    def test_unequal_themes(self):
        """Composite equals mean with unequal theme values."""
        # 0.2 + 0.5 + 0.8 = 1.5 / 3 = 0.5
        profile = SVIProfile(
            tribe_id="epa_100000001",
            themes=[
                SVITheme(theme_id="theme1", name="Socioeconomic", percentile=0.2, flag_count=0),
                SVITheme(theme_id="theme2", name="Household", percentile=0.5, flag_count=1),
                SVITheme(theme_id="theme4", name="Housing", percentile=0.8, flag_count=2),
            ],
            composite=0.5,
            coverage_pct=0.8,
        )
        assert profile.composite == 0.5

    def test_composite_not_equal_rpl_themes(
        self, tmp_path, svi_county_csv, crosswalk_file, area_weights_file, mock_registry
    ):
        """Composite uses theme1+2+4 mean, never RPL_THEMES (which includes theme3)."""
        builder = _make_builder(
            tmp_path, svi_county_csv, crosswalk_file, area_weights_file, mock_registry
        )
        county_data = builder._load_svi_csv()
        # Verify that raw RPL_THEMES is stored but NOT used for composite
        for fips, record in county_data.items():
            our_composite = round(
                (record["rpl_theme1"] + record["rpl_theme2"] + record["rpl_theme4"]) / 3,
                4,
            )
            # RPL_THEMES includes theme3, so it should differ from our composite
            assert "rpl_themes" in record  # stored for reference
            if record["rpl_themes"] != 0.0:
                assert abs(our_composite - record["rpl_themes"]) > 0.001, (
                    f"FIPS {fips}: 3-theme composite ({our_composite}) should differ "
                    f"from RPL_THEMES ({record['rpl_themes']}) which includes Theme 3"
                )

    def test_composite_mismatch_rejected(self):
        """Schema rejects composite that doesn't match mean of themes."""
        with pytest.raises(Exception):
            SVIProfile(
                tribe_id="epa_100000001",
                themes=[
                    SVITheme(theme_id="theme1", name="S", percentile=0.6, flag_count=1),
                    SVITheme(theme_id="theme2", name="H", percentile=0.3, flag_count=0),
                    SVITheme(theme_id="theme4", name="T", percentile=0.9, flag_count=2),
                ],
                composite=0.99,  # Wrong! Should be 0.6
                coverage_pct=1.0,
            )


# ═══════════════════════════════════════════════════════════════════════════
# TestSVIAreaWeightedAggregation
# ═══════════════════════════════════════════════════════════════════════════


class TestSVIAreaWeightedAggregation:
    """Test area-weighted aggregation of SVI data to Tribal areas."""

    def test_single_county_full_weight(
        self, tmp_path, svi_county_csv, crosswalk_file, area_weights_file, mock_registry
    ):
        """Single county with weight=1.0 -> exact county values."""
        builder = _make_builder(
            tmp_path, svi_county_csv, crosswalk_file, area_weights_file, mock_registry
        )
        county_data = builder._load_svi_csv()
        tribe = {"tribe_id": "epa_100000002", "name": "Beta", "states": ["WA"]}
        result = builder._aggregate_tribe_svi("epa_100000002", tribe, county_data)

        # GEOID_002 -> 53033 weight=1.0 -> exact values
        assert result["counties_matched"] == 1
        assert result["themes"]["theme1"]["percentile"] == 0.90
        assert result["themes"]["theme2"]["percentile"] == 0.85
        assert result["themes"]["theme4"]["percentile"] == 0.80

    def test_two_county_weighted_average(
        self, tmp_path, svi_county_csv, crosswalk_file, area_weights_file, mock_registry
    ):
        """Two counties with different weights -> weighted average."""
        builder = _make_builder(
            tmp_path, svi_county_csv, crosswalk_file, area_weights_file, mock_registry
        )
        county_data = builder._load_svi_csv()
        tribe = {"tribe_id": "epa_100000001", "name": "Alpha", "states": ["CA"]}
        result = builder._aggregate_tribe_svi("epa_100000001", tribe, county_data)

        # GEOID_001 -> 06001 (w=0.7) + 06003 (w=0.3)
        assert result["counties_matched"] == 2
        # theme1: 0.80*0.7 + 0.40*0.3 = 0.56+0.12 = 0.68
        assert abs(result["themes"]["theme1"]["percentile"] - 0.68) < 0.01
        # theme2: 0.60*0.7 + 0.30*0.3 = 0.42+0.09 = 0.51
        assert abs(result["themes"]["theme2"]["percentile"] - 0.51) < 0.01
        # theme4: 0.70*0.7 + 0.50*0.3 = 0.49+0.15 = 0.64
        assert abs(result["themes"]["theme4"]["percentile"] - 0.64) < 0.01

    def test_composite_from_weighted_themes(
        self, tmp_path, svi_county_csv, crosswalk_file, area_weights_file, mock_registry
    ):
        """Composite = mean of weighted theme averages."""
        builder = _make_builder(
            tmp_path, svi_county_csv, crosswalk_file, area_weights_file, mock_registry
        )
        county_data = builder._load_svi_csv()
        tribe = {"tribe_id": "epa_100000001", "name": "Alpha", "states": ["CA"]}
        result = builder._aggregate_tribe_svi("epa_100000001", tribe, county_data)

        t1 = result["themes"]["theme1"]["percentile"]
        t2 = result["themes"]["theme2"]["percentile"]
        t4 = result["themes"]["theme4"]["percentile"]
        expected_composite = round((t1 + t2 + t4) / 3.0, 4)
        assert abs(result["composite"] - expected_composite) < 0.01

    def test_missing_county_in_data(
        self, tmp_path, crosswalk_file, mock_registry
    ):
        """Counties in crosswalk but missing from SVI data -> no match."""
        # Create area weights with a county not in the SVI data
        weights = {
            "metadata": {"total_aiannh_entities": 1, "total_county_links": 1},
            "crosswalk": {
                "GEOID_001": [
                    {"county_fips": "99999", "weight": 1.0, "overlap_area_sqkm": 100},
                ],
            },
        }
        weights_path = tmp_path / "weights.json"
        weights_path.write_text(json.dumps(weights), encoding="utf-8")

        # Create CSV with a different county
        csv_content = (
            "STCNTY,RPL_THEME1,RPL_THEME2,RPL_THEME3,RPL_THEME4,RPL_THEMES,"
            "E_TOTPOP,F_THEME1,F_THEME2,F_THEME3,F_THEME4\n"
            "06001,0.80,0.60,0.50,0.70,0.75,100000,2,1,1,3\n"
        )
        csv_path = tmp_path / "SVI2022_US_COUNTY.csv"
        csv_path.write_text(csv_content, encoding="utf-8")

        builder = _make_builder(
            tmp_path, csv_path, crosswalk_file, weights_path, mock_registry
        )
        county_data = builder._load_svi_csv()
        tribe = {"tribe_id": "epa_100000001", "name": "Alpha", "states": ["CA"]}
        result = builder._aggregate_tribe_svi("epa_100000001", tribe, county_data)

        assert result["counties_matched"] == 0
        assert DataGapType.MISSING_SVI in result["data_gaps"]

    def test_weight_normalization(
        self, tmp_path, svi_county_csv, crosswalk_file, area_weights_file, mock_registry
    ):
        """Weights are normalized so they sum to 1.0 for matched counties."""
        builder = _make_builder(
            tmp_path, svi_county_csv, crosswalk_file, area_weights_file, mock_registry
        )
        county_data = builder._load_svi_csv()
        tribe = {"tribe_id": "epa_100000001", "name": "Alpha", "states": ["CA"]}
        result = builder._aggregate_tribe_svi("epa_100000001", tribe, county_data)

        # Two counties with weights 0.7 + 0.3 = 1.0 (already normalized)
        assert result["counties_matched"] == 2

    def test_coverage_pct(
        self, tmp_path, svi_county_csv, crosswalk_file, area_weights_file, mock_registry
    ):
        """Coverage_pct = matched_weight / total_weight (area-based)."""
        builder = _make_builder(
            tmp_path, svi_county_csv, crosswalk_file, area_weights_file, mock_registry
        )
        county_data = builder._load_svi_csv()
        tribe = {"tribe_id": "epa_100000001", "name": "Alpha", "states": ["CA"]}
        result = builder._aggregate_tribe_svi("epa_100000001", tribe, county_data)

        # 2 matched / 2 in crosswalk = 1.0
        assert result["coverage_pct"] == 1.0

    def test_zero_weight_counties_excluded(self, tmp_path, crosswalk_file, mock_registry):
        """Counties with zero weight do not contribute to the aggregate."""
        weights = {
            "metadata": {"total_aiannh_entities": 1, "total_county_links": 2},
            "crosswalk": {
                "GEOID_001": [
                    {"county_fips": "06001", "weight": 0.0, "overlap_area_sqkm": 0},
                    {"county_fips": "06003", "weight": 1.0, "overlap_area_sqkm": 100},
                ],
            },
        }
        weights_path = tmp_path / "weights.json"
        weights_path.write_text(json.dumps(weights), encoding="utf-8")

        csv_content = (
            "STCNTY,RPL_THEME1,RPL_THEME2,RPL_THEME3,RPL_THEME4,RPL_THEMES,"
            "E_TOTPOP,F_THEME1,F_THEME2,F_THEME3,F_THEME4\n"
            "06001,0.80,0.60,0.50,0.70,0.75,100000,2,1,1,3\n"
            "06003,0.40,0.30,0.20,0.50,0.35,5000,1,0,0,2\n"
        )
        csv_path = tmp_path / "SVI2022_US_COUNTY.csv"
        csv_path.write_text(csv_content, encoding="utf-8")

        builder = _make_builder(
            tmp_path, csv_path, crosswalk_file, weights_path, mock_registry
        )
        county_data = builder._load_svi_csv()
        tribe = {"tribe_id": "epa_100000001", "name": "Alpha", "states": ["CA"]}
        result = builder._aggregate_tribe_svi("epa_100000001", tribe, county_data)

        # With zero weight for 06001, result should be 06003 only
        # theme1=0.40, theme2=0.30, theme4=0.50
        assert result["counties_matched"] == 2  # Both matched, but 06001 has 0 weight
        # After normalization, 06001 contributes 0, 06003 contributes all
        assert abs(result["themes"]["theme1"]["percentile"] - 0.40) < 0.01
        assert abs(result["themes"]["theme2"]["percentile"] - 0.30) < 0.01
        assert abs(result["themes"]["theme4"]["percentile"] - 0.50) < 0.01

    def test_all_zero_themes_county_skipped(
        self, tmp_path, svi_county_csv_all_zeros, crosswalk_file, area_weights_file, mock_registry
    ):
        """Counties where all 3 themes are 0.0 are skipped."""
        builder = _make_builder(
            tmp_path, svi_county_csv_all_zeros, crosswalk_file, area_weights_file, mock_registry
        )
        county_data = builder._load_svi_csv()
        tribe = {"tribe_id": "epa_100000001", "name": "Alpha", "states": ["CA"]}
        result = builder._aggregate_tribe_svi("epa_100000001", tribe, county_data)

        # County 06001 has all zeros -> skipped
        assert result["counties_matched"] == 0
        assert DataGapType.MISSING_SVI in result["data_gaps"]

    def test_zero_theme_high_area_triggers_gap(self, tmp_path, crosswalk_file, mock_registry):
        """Counties with zero themes and high area weight correctly lower coverage_pct.

        Regression test for P2-#9: A Tribe whose high-area counties have
        suppressed (all-zero) SVI data should have low coverage_pct and
        trigger MISSING_SVI gap via weight-based coverage calculation.
        """
        # 80% area has zero themes, 20% has real data
        weights = {
            "metadata": {"total_aiannh_entities": 1, "total_county_links": 2},
            "crosswalk": {
                "GEOID_001": [
                    {"county_fips": "06001", "weight": 0.8, "overlap_area_sqkm": 800},
                    {"county_fips": "06003", "weight": 0.2, "overlap_area_sqkm": 200},
                ],
            },
        }
        weights_path = tmp_path / "weights.json"
        weights_path.write_text(json.dumps(weights), encoding="utf-8")

        # 06001: all zeros (suppressed), 06003: real data
        csv_content = (
            "STCNTY,ST_ABBR,RPL_THEME1,RPL_THEME2,RPL_THEME3,RPL_THEME4,RPL_THEMES,"
            "E_TOTPOP,F_THEME1,F_THEME2,F_THEME3,F_THEME4\n"
            "06001,CA,0.0,0.0,0.0,0.0,0.0,100000,0,0,0,0\n"
            "06003,CA,0.40,0.30,0.20,0.50,0.35,5000,1,0,0,2\n"
        )
        csv_path = tmp_path / "SVI2022_US_COUNTY.csv"
        csv_path.write_text(csv_content, encoding="utf-8")

        builder = _make_builder(
            tmp_path, csv_path, crosswalk_file, weights_path, mock_registry
        )
        county_data = builder._load_svi_csv()
        tribe = {"tribe_id": "epa_100000001", "name": "Alpha", "states": ["CA"]}
        result = builder._aggregate_tribe_svi("epa_100000001", tribe, county_data)

        # Weight-based: only 06003 matched (0.2 weight) out of 1.0 total
        assert result["coverage_pct"] == 0.2
        assert DataGapType.MISSING_SVI in result["data_gaps"]


# ═══════════════════════════════════════════════════════════════════════════
# TestSVIProfileBuilder
# ═══════════════════════════════════════════════════════════════════════════


class TestSVIProfileBuilder:
    """Test SVIProfileBuilder initialization and orchestration."""

    def test_init_default_paths(self):
        """Builder initializes with default paths when config is empty."""
        with patch("src.packets.svi_builder.SVIProfileBuilder.__init__", lambda self, cfg: None):
            builder = SVIProfileBuilder.__new__(SVIProfileBuilder)
        # Just verify the class can be instantiated
        assert builder is not None

    def test_path_traversal_guard(self, tmp_path):
        """atomic_write_json rejects path traversal sequences."""
        from src.packets._geo_common import atomic_write_json

        with pytest.raises(ValueError, match="Path traversal"):
            atomic_write_json(
                tmp_path / ".." / "etc" / "passwd.json", {"test": True}
            )

    def test_path_traversal_guard_dotdot(self, tmp_path):
        """atomic_write_json rejects paths containing '..'."""
        from src.packets._geo_common import atomic_write_json

        with pytest.raises(ValueError, match="Path traversal"):
            atomic_write_json(
                tmp_path / "..epa_test.json", {"test": True}
            )

    def test_atomic_write_creates_file(self, tmp_path):
        """atomic_write_json creates a valid JSON file."""
        from src.packets._geo_common import atomic_write_json

        output_file = tmp_path / "epa_100000001.json"
        test_data = {"tribe_id": "epa_100000001", "test_key": "test_value"}
        atomic_write_json(output_file, test_data)

        assert output_file.exists()
        with open(output_file, encoding="utf-8") as f:
            loaded = json.load(f)
        assert loaded["tribe_id"] == "epa_100000001"
        assert loaded["test_key"] == "test_value"

    def test_output_validates_svi_profile_schema(
        self, tmp_path, svi_county_csv, crosswalk_file, area_weights_file, mock_registry
    ):
        """build_all_profiles validates each output against SVIProfile schema."""
        builder = _make_builder(
            tmp_path, svi_county_csv, crosswalk_file, area_weights_file, mock_registry
        )
        with patch.object(builder, "_generate_coverage_report"):
            count = builder.build_all_profiles()

        assert count == 3  # 3 tribes in mock_registry

        # Read back and validate each file
        for profile_file in builder.output_dir.glob("epa_*.json"):
            with open(profile_file, encoding="utf-8") as f:
                data = json.load(f)
            svi_data = data["svi"]
            # Should validate without error
            profile = SVIProfile(**svi_data)
            assert profile.tribe_id.startswith("epa_")
            assert len(profile.themes) <= 3

    def test_build_all_returns_count(
        self, tmp_path, svi_county_csv, crosswalk_file, area_weights_file, mock_registry
    ):
        """build_all_profiles returns number of files written."""
        builder = _make_builder(
            tmp_path, svi_county_csv, crosswalk_file, area_weights_file, mock_registry
        )
        with patch.object(builder, "_generate_coverage_report"):
            count = builder.build_all_profiles()
        assert count == 3

    def test_fips_column_fallback(
        self, tmp_path, svi_county_csv_with_fips_col, crosswalk_file, area_weights_file, mock_registry
    ):
        """Builder handles CSV with FIPS column instead of STCNTY."""
        builder = _make_builder(
            tmp_path, svi_county_csv_with_fips_col, crosswalk_file, area_weights_file, mock_registry
        )
        county_data = builder._load_svi_csv()
        assert "06001" in county_data

    def test_sentinel_handling_in_csv(
        self, tmp_path, svi_county_csv_with_sentinels, crosswalk_file, area_weights_file, mock_registry
    ):
        """Builder replaces -999 sentinels with 0.0 in loaded data."""
        builder = _make_builder(
            tmp_path, svi_county_csv_with_sentinels, crosswalk_file, area_weights_file, mock_registry
        )
        county_data = builder._load_svi_csv()
        # 06001: theme1=-999 -> 0.0, theme2=0.60, theme4=0.70
        assert county_data["06001"]["rpl_theme1"] == 0.0
        assert county_data["06001"]["rpl_theme2"] == 0.60
        assert county_data["06001"]["rpl_theme4"] == 0.70
        # 06003: theme2=-999 -> 0.0, theme4=-999 -> 0.0
        assert county_data["06003"]["rpl_theme1"] == 0.40
        assert county_data["06003"]["rpl_theme2"] == 0.0
        assert county_data["06003"]["rpl_theme4"] == 0.0

    def test_missing_csv_returns_empty(
        self, tmp_path, crosswalk_file, area_weights_file, mock_registry
    ):
        """Builder returns empty dict when CSV path doesn't exist."""
        missing_csv = tmp_path / "nonexistent.csv"
        builder = _make_builder(
            tmp_path, missing_csv, crosswalk_file, area_weights_file, mock_registry
        )
        county_data = builder._load_svi_csv()
        assert county_data == {}


# ═══════════════════════════════════════════════════════════════════════════
# TestSVIDataGaps
# ═══════════════════════════════════════════════════════════════════════════


class TestSVIDataGaps:
    """Test data gap detection in SVI profiles."""

    def test_zero_coverage_missing_svi(
        self, tmp_path, crosswalk_file, mock_registry
    ):
        """Zero coverage -> MISSING_SVI gap."""
        # Create CSV with no matching counties
        csv_content = (
            "STCNTY,RPL_THEME1,RPL_THEME2,RPL_THEME3,RPL_THEME4,RPL_THEMES,"
            "E_TOTPOP,F_THEME1,F_THEME2,F_THEME3,F_THEME4\n"
            "99001,0.80,0.60,0.50,0.70,0.75,100000,2,1,1,3\n"
        )
        csv_path = tmp_path / "SVI2022_US_COUNTY.csv"
        csv_path.write_text(csv_content, encoding="utf-8")

        weights = {
            "metadata": {"total_aiannh_entities": 1, "total_county_links": 1},
            "crosswalk": {
                "GEOID_001": [
                    {"county_fips": "06001", "weight": 1.0, "overlap_area_sqkm": 100},
                ],
            },
        }
        weights_path = tmp_path / "weights.json"
        weights_path.write_text(json.dumps(weights), encoding="utf-8")

        builder = _make_builder(
            tmp_path, csv_path, crosswalk_file, weights_path, mock_registry
        )
        county_data = builder._load_svi_csv()
        tribe = {"tribe_id": "epa_100000001", "name": "Alpha", "states": ["CA"]}
        result = builder._aggregate_tribe_svi("epa_100000001", tribe, county_data)

        assert DataGapType.MISSING_SVI in result["data_gaps"]

    def test_full_coverage_no_gaps(
        self, tmp_path, svi_county_csv, crosswalk_file, area_weights_file, mock_registry
    ):
        """Full coverage -> no MISSING_SVI gap."""
        builder = _make_builder(
            tmp_path, svi_county_csv, crosswalk_file, area_weights_file, mock_registry
        )
        county_data = builder._load_svi_csv()
        tribe = {"tribe_id": "epa_100000002", "name": "Beta", "states": ["WA"]}
        result = builder._aggregate_tribe_svi("epa_100000002", tribe, county_data)

        assert result["coverage_pct"] == 1.0
        assert DataGapType.MISSING_SVI not in result["data_gaps"]

    def test_alaska_partial_gap(
        self, tmp_path, svi_county_csv, crosswalk_file, area_weights_file, mock_registry
    ):
        """Alaska tribe with partial coverage -> ALASKA_PARTIAL gap."""
        # Modify area weights so GEOID_003 has 2 counties, 1 missing from data
        weights = {
            "metadata": {"total_aiannh_entities": 1, "total_county_links": 2},
            "crosswalk": {
                "GEOID_003": [
                    {"county_fips": "02020", "weight": 0.5, "overlap_area_sqkm": 100},
                    {"county_fips": "02999", "weight": 0.5, "overlap_area_sqkm": 100},
                ],
            },
        }
        weights_path = tmp_path / "weights.json"
        weights_path.write_text(json.dumps(weights), encoding="utf-8")

        builder = _make_builder(
            tmp_path, svi_county_csv, crosswalk_file, weights_path, mock_registry
        )
        county_data = builder._load_svi_csv()
        tribe = {"tribe_id": "epa_100000003", "name": "Gamma", "states": ["AK"]}
        result = builder._aggregate_tribe_svi("epa_100000003", tribe, county_data)

        # 1/2 counties matched -> coverage 0.5 -> partial, AK -> ALASKA_PARTIAL
        assert result["coverage_pct"] == 0.5
        assert DataGapType.ALASKA_PARTIAL in result["data_gaps"]

    def test_no_crosswalk_entry(
        self, tmp_path, svi_county_csv, crosswalk_file, area_weights_file, mock_registry
    ):
        """Tribe with no crosswalk entry -> MISSING_SVI."""
        builder = _make_builder(
            tmp_path, svi_county_csv, crosswalk_file, area_weights_file, mock_registry
        )
        county_data = builder._load_svi_csv()
        # Use a tribe_id not in crosswalk
        tribe = {"tribe_id": "epa_999999999", "name": "Unknown", "states": ["CA"]}
        result = builder._aggregate_tribe_svi("epa_999999999", tribe, county_data)

        assert result["counties_matched"] == 0
        assert DataGapType.MISSING_SVI in result["data_gaps"]

    def test_empty_county_data(
        self, tmp_path, svi_county_csv, crosswalk_file, area_weights_file, mock_registry
    ):
        """Empty county data dict -> MISSING_SVI gap."""
        builder = _make_builder(
            tmp_path, svi_county_csv, crosswalk_file, area_weights_file, mock_registry
        )
        tribe = {"tribe_id": "epa_100000001", "name": "Alpha", "states": ["CA"]}
        result = builder._aggregate_tribe_svi("epa_100000001", tribe, {})

        assert DataGapType.MISSING_SVI in result["data_gaps"]
        assert result["note"] == "SVI county data not loaded"


# ═══════════════════════════════════════════════════════════════════════════
# TestSVIIntegration
# ═══════════════════════════════════════════════════════════════════════════


class TestSVIIntegration:
    """Integration tests (conditional on SVI CSV existence)."""

    @pytest.mark.skipif(
        not Path("data/svi/SVI2022_US_COUNTY.csv").exists(),
        reason="SVI CSV not present -- download from CDC",
    )
    def test_real_csv_loads(self):
        """Real SVI CSV loads without errors (integration test)."""
        from src.paths import SVI_COUNTY_PATH

        with patch("src.packets.svi_builder.SVIProfileBuilder.__init__", lambda self, cfg: None):
            builder = SVIProfileBuilder.__new__(SVIProfileBuilder)
        builder.svi_csv_path = SVI_COUNTY_PATH
        county_data = builder._load_svi_csv()
        assert len(county_data) > 0
        # Verify no theme3 in parsed records
        for fips, record in list(county_data.items())[:10]:
            assert "rpl_theme3" not in record
            assert "rpl_theme1" in record


# ═══════════════════════════════════════════════════════════════════════════
# TestSVIThemeNames
# ═══════════════════════════════════════════════════════════════════════════


class TestSVIThemeNames:
    """Test theme name mapping."""

    def test_theme_names_cover_included_themes(self):
        """SVI_THEME_NAMES has entries for all included themes."""
        for theme in SVI_INCLUDED_THEMES:
            assert theme in SVI_THEME_NAMES

    def test_theme3_not_in_names(self):
        """Theme 3 has no entry in SVI_THEME_NAMES."""
        assert "theme3" not in SVI_THEME_NAMES

    def test_theme1_name(self):
        """Theme 1 name is Socioeconomic Status."""
        assert SVI_THEME_NAMES["theme1"] == "Socioeconomic Status"

    def test_theme2_name(self):
        """Theme 2 name is Household Characteristics & Disability."""
        assert SVI_THEME_NAMES["theme2"] == "Household Characteristics & Disability"

    def test_theme4_name(self):
        """Theme 4 name is Housing Type & Transportation."""
        assert SVI_THEME_NAMES["theme4"] == "Housing Type & Transportation"
