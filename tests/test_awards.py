"""Tests for the Tribal award matching pipeline.

Covers:
  - Consortium detection (_is_consortium)
  - Award deduplication (by Award ID and composite fallback)
  - Fiscal year determination (_determine_award_fy)
  - Enhanced cache schema (fiscal_year_range, yearly_obligations, trend)
  - Consortium filtering in match_all_awards()
  - Trend computation (none, new, increasing, decreasing, stable)
"""

import json

from src.packets.awards import (
    TribalAwardMatcher,
    _compute_trend,
    _determine_award_fy,
    _is_consortium,
)


# ── Fixtures ──


def _build_registry_file(tmp_path, tribes):
    """Write a minimal tribal_registry.json for testing."""
    registry_path = tmp_path / "tribal_registry.json"
    registry_path.write_text(
        json.dumps({"tribes": tribes, "metadata": {"placeholder": False}}),
        encoding="utf-8",
    )
    return registry_path


def _build_alias_file(tmp_path, aliases=None):
    """Write a minimal tribal_aliases.json for testing."""
    alias_path = tmp_path / "tribal_aliases.json"
    alias_path.write_text(
        json.dumps({"aliases": aliases or {}}),
        encoding="utf-8",
    )
    return alias_path


def _make_matcher(tmp_path, tribes, aliases=None):
    """Create a TribalAwardMatcher with temp files and custom cache dir."""
    registry_path = _build_registry_file(tmp_path, tribes)
    alias_path = _build_alias_file(tmp_path, aliases or {})
    cache_dir = tmp_path / "award_cache"

    config = {
        "packets": {
            "tribal_registry": {"data_path": str(registry_path)},
            "awards": {
                "alias_path": str(alias_path),
                "cache_dir": str(cache_dir),
            },
        },
    }
    return TribalAwardMatcher(config)


SAMPLE_TRIBES = [
    {
        "tribe_id": "epa_001",
        "name": "Navajo Nation",
        "states": ["AZ", "NM", "UT"],
        "alternate_names": [],
    },
    {
        "tribe_id": "epa_002",
        "name": "Muckleshoot Indian Tribe",
        "states": ["WA"],
        "alternate_names": [],
    },
    {
        "tribe_id": "epa_003",
        "name": "Standing Rock Sioux Tribe",
        "states": ["ND", "SD"],
        "alternate_names": [],
    },
]


# ── Consortium detection ──


class TestIsConsortium:
    """Test consortium/inter-Tribal pattern detection."""

    def test_positive_inter_tribal(self):
        assert _is_consortium("INTER TRIBAL COUNCIL OF ARIZONA")

    def test_positive_health_board(self):
        assert _is_consortium("NORTHWEST PORTLAND AREA INDIAN HEALTH BOARD")

    def test_positive_association(self):
        assert _is_consortium("ASSOCIATION OF VILLAGE COUNCIL PRESIDENTS")

    def test_positive_consortium(self):
        assert _is_consortium("GREAT PLAINS TRIBAL CONSORTIUM")

    def test_positive_united_south_eastern(self):
        assert _is_consortium("UNITED SOUTH AND EASTERN TRIBES INC")

    def test_negative_navajo(self):
        assert not _is_consortium("NAVAJO NATION")

    def test_negative_muckleshoot(self):
        assert not _is_consortium("MUCKLESHOOT INDIAN TRIBE")

    def test_negative_standing_rock(self):
        assert not _is_consortium("STANDING ROCK SIOUX TRIBE")

    def test_case_insensitive(self):
        assert _is_consortium("inter tribal council of arizona")
        assert _is_consortium("Inter Tribal Council Of Arizona")


# ── Deduplication ──


class TestDeduplicateAwards:
    """Test award deduplication by Award ID and composite fallback."""

    def test_deduplicate_by_award_id(self):
        """Duplicate Award IDs across CFDAs should be removed."""
        awards_by_cfda = {
            "15.156": [
                {
                    "Award ID": "AWARD-001",
                    "Recipient Name": "NAVAJO NATION",
                    "Total Obligation": 100000,
                    "Start Date": "2023-01-15",
                },
                {
                    "Award ID": "AWARD-002",
                    "Recipient Name": "NAVAJO NATION",
                    "Total Obligation": 200000,
                    "Start Date": "2023-06-01",
                },
            ],
            "97.047": [
                # Duplicate of AWARD-001 (appears in second CFDA query)
                {
                    "Award ID": "AWARD-001",
                    "Recipient Name": "NAVAJO NATION",
                    "Total Obligation": 100000,
                    "Start Date": "2023-01-15",
                },
                {
                    "Award ID": "AWARD-003",
                    "Recipient Name": "MUCKLESHOOT INDIAN TRIBE",
                    "Total Obligation": 50000,
                    "Start Date": "2024-02-01",
                },
            ],
        }

        result = TribalAwardMatcher.deduplicate_awards(awards_by_cfda)

        # CFDA 15.156 keeps both (no dups within it)
        assert len(result["15.156"]) == 2
        # CFDA 97.047 loses AWARD-001 (already seen), keeps AWARD-003
        assert len(result["97.047"]) == 1
        assert result["97.047"][0]["Award ID"] == "AWARD-003"

    def test_deduplicate_empty_award_id_different_composite(self):
        """Awards with empty Award ID but different composites are kept."""
        awards_by_cfda = {
            "15.156": [
                {
                    "Award ID": "",
                    "Recipient Name": "TRIBE A",
                    "Total Obligation": 100000,
                    "Start Date": "2023-01-15",
                },
                {
                    "Award ID": "",
                    "Recipient Name": "TRIBE B",
                    "Total Obligation": 200000,
                    "Start Date": "2023-06-01",
                },
            ],
        }

        result = TribalAwardMatcher.deduplicate_awards(awards_by_cfda)
        # Different composite keys -> both kept
        assert len(result["15.156"]) == 2

    def test_deduplicate_empty_award_id_same_composite(self):
        """Awards with empty Award ID and same composite are deduplicated."""
        awards_by_cfda = {
            "15.156": [
                {
                    "Award ID": "",
                    "Recipient Name": "TRIBE A",
                    "Total Obligation": 100000,
                    "Start Date": "2023-01-15",
                },
            ],
            "15.156b": [
                # Same composite key (same recipient, cfda part is different
                # but we use the cfda from the outer dict key, so this differs)
            ],
            "97.047": [
                {
                    "Award ID": "",
                    "Recipient Name": "TRIBE A",
                    "Total Obligation": 100000,
                    "Start Date": "2023-01-15",
                },
            ],
        }

        result = TribalAwardMatcher.deduplicate_awards(awards_by_cfda)
        # Different CFDA in composite key -> different keys -> both kept
        assert len(result["15.156"]) == 1
        assert len(result["97.047"]) == 1

    def test_deduplicate_same_cfda_same_composite(self):
        """Two awards with empty ID and identical composite in same CFDA."""
        awards_by_cfda = {
            "15.156": [
                {
                    "Award ID": "",
                    "Recipient Name": "TRIBE A",
                    "Total Obligation": 100000,
                    "Start Date": "2023-01-15",
                },
                {
                    "Award ID": "",
                    "Recipient Name": "TRIBE A",
                    "Total Obligation": 100000,
                    "Start Date": "2023-01-15",
                },
            ],
        }

        result = TribalAwardMatcher.deduplicate_awards(awards_by_cfda)
        # Same composite key in same CFDA -> deduplicated to 1
        assert len(result["15.156"]) == 1

    def test_keeps_first_occurrence(self):
        """Deduplication keeps the FIRST occurrence."""
        awards_by_cfda = {
            "15.156": [
                {
                    "Award ID": "DUP-001",
                    "Recipient Name": "FIRST OCCURRENCE",
                    "Total Obligation": 100000,
                    "Start Date": "2022-01-15",
                },
            ],
            "97.047": [
                {
                    "Award ID": "DUP-001",
                    "Recipient Name": "SECOND OCCURRENCE",
                    "Total Obligation": 200000,
                    "Start Date": "2023-06-01",
                },
            ],
        }

        result = TribalAwardMatcher.deduplicate_awards(awards_by_cfda)
        assert len(result["15.156"]) == 1
        assert result["15.156"][0]["Recipient Name"] == "FIRST OCCURRENCE"
        assert len(result["97.047"]) == 0


# ── Fiscal year determination ──


class TestDetermineAwardFY:
    """Test fiscal year determination from award data."""

    def test_from_fiscal_year_field(self):
        assert _determine_award_fy({"_fiscal_year": 2024}) == 2024

    def test_from_start_date_november(self):
        """November is in the NEXT fiscal year (month >= 10)."""
        assert _determine_award_fy({"start_date": "2023-11-15"}) == 2024

    def test_from_start_date_march(self):
        """March is in the CURRENT fiscal year (month < 10)."""
        assert _determine_award_fy({"start_date": "2024-03-15"}) == 2024

    def test_from_start_date_october(self):
        """October is the start of the NEXT fiscal year (month == 10)."""
        assert _determine_award_fy({"start_date": "2023-10-01"}) == 2024

    def test_from_start_date_september(self):
        """September is the end of the CURRENT fiscal year (month == 9)."""
        assert _determine_award_fy({"start_date": "2024-09-30"}) == 2024

    def test_missing_start_date(self):
        assert _determine_award_fy({}) is None

    def test_empty_start_date(self):
        assert _determine_award_fy({"start_date": ""}) is None

    def test_invalid_start_date(self):
        assert _determine_award_fy({"start_date": "not-a-date"}) is None

    def test_fiscal_year_field_takes_precedence(self):
        """_fiscal_year field should take precedence over start_date."""
        award = {"_fiscal_year": 2025, "start_date": "2023-11-15"}
        assert _determine_award_fy(award) == 2025


# ── Trend computation ──


class TestComputeTrend:
    """Test funding trend computation."""

    def test_trend_none_empty(self):
        obligations = {"2022": 0.0, "2023": 0.0, "2024": 0.0, "2025": 0.0, "2026": 0.0}
        assert _compute_trend(obligations, 2022, 2026) == "none"

    def test_trend_new(self):
        """Awards only in last 2 years -> 'new'."""
        obligations = {
            "2022": 0.0, "2023": 0.0, "2024": 0.0,
            "2025": 50000.0, "2026": 100000.0,
        }
        assert _compute_trend(obligations, 2022, 2026) == "new"

    def test_trend_increasing(self):
        """Second half > first half * 1.2 -> 'increasing'."""
        obligations = {
            "2022": 10000.0, "2023": 10000.0,
            "2024": 50000.0, "2025": 60000.0, "2026": 70000.0,
        }
        # First half (2022, 2023) = 20000
        # Second half (2024, 2025, 2026) = 180000
        # 180000 > 20000 * 1.2 = 24000 -> increasing
        assert _compute_trend(obligations, 2022, 2026) == "increasing"

    def test_trend_decreasing(self):
        """Second half < first half * 0.8 -> 'decreasing'."""
        obligations = {
            "2022": 100000.0, "2023": 100000.0,
            "2024": 5000.0, "2025": 5000.0, "2026": 5000.0,
        }
        # First half (2022, 2023) = 200000
        # Second half (2024, 2025, 2026) = 15000
        # 15000 < 200000 * 0.8 = 160000 -> decreasing
        assert _compute_trend(obligations, 2022, 2026) == "decreasing"

    def test_trend_stable(self):
        """Second half roughly equal to first half -> 'stable'."""
        obligations = {
            "2022": 50000.0, "2023": 50000.0,
            "2024": 40000.0, "2025": 45000.0, "2026": 50000.0,
        }
        # First half = 100000, second half = 135000
        # 135000 > 100000 * 0.8 (80000) and < 100000 * 1.2 (120000)?
        # Actually 135000 > 120000, so this is increasing. Adjust:
        obligations = {
            "2022": 50000.0, "2023": 50000.0,
            "2024": 35000.0, "2025": 35000.0, "2026": 35000.0,
        }
        # First half = 100000, second half = 105000
        # 105000 <= 120000 and >= 80000 -> stable
        assert _compute_trend(obligations, 2022, 2026) == "stable"


# ── Enhanced cache schema ──


class TestWriteCacheEnhancedSchema:
    """Test write_cache produces enhanced JSON schema."""

    def test_cache_schema_with_awards(self, tmp_path):
        """Cache file includes all enhanced fields."""
        matcher = _make_matcher(tmp_path, SAMPLE_TRIBES[:1])
        matched = {
            "epa_001": [
                {
                    "award_id": "A-001",
                    "cfda": "15.156",
                    "program_id": "bia_tcr",
                    "recipient_name_raw": "NAVAJO NATION",
                    "obligation": 500000.0,
                    "start_date": "2024-01-15",
                    "end_date": "2025-01-14",
                    "description": "TCR grant",
                    "awarding_agency": "DOI",
                },
                {
                    "award_id": "A-002",
                    "cfda": "97.047",
                    "program_id": "fema_bric",
                    "recipient_name_raw": "NAVAJO NATION",
                    "obligation": 250000.0,
                    "start_date": "2025-03-01",
                    "end_date": "2026-02-28",
                    "description": "BRIC grant",
                    "awarding_agency": "FEMA",
                },
            ],
        }

        count = matcher.write_cache(matched, fy_start=2022, fy_end=2026)
        assert count == 1

        cache_path = tmp_path / "award_cache" / "epa_001.json"
        assert cache_path.exists()

        with open(cache_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Core fields
        assert data["tribe_id"] == "epa_001"
        assert data["tribe_name"] == "Navajo Nation"
        assert data["award_count"] == 2
        assert data["total_obligation"] == 750000.0

        # Enhanced fields
        assert data["fiscal_year_range"] == {"start": 2022, "end": 2026}
        assert isinstance(data["yearly_obligations"], dict)
        assert "2024" in data["yearly_obligations"]
        assert "2025" in data["yearly_obligations"]

        # Trend should be one of the valid values
        assert data["trend"] in ("none", "new", "increasing", "decreasing", "stable")

        # CFDA summary
        assert "15.156" in data["cfda_summary"]
        assert data["cfda_summary"]["15.156"]["count"] == 1
        assert data["cfda_summary"]["15.156"]["total"] == 500000.0

        # No awards context should NOT be present
        assert "no_awards_context" not in data

    def test_cache_schema_zero_awards(self, tmp_path):
        """Zero-award Tribes get no_awards_context and trend=none."""
        matcher = _make_matcher(tmp_path, SAMPLE_TRIBES[:1])
        matched: dict[str, list[dict]] = {}  # No awards for any Tribe

        count = matcher.write_cache(matched, fy_start=2022, fy_end=2026)
        assert count == 1

        cache_path = tmp_path / "award_cache" / "epa_001.json"
        with open(cache_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert data["award_count"] == 0
        assert data["total_obligation"] == 0.0
        assert data["trend"] == "none"
        assert "no_awards_context" in data
        assert "first-time applicant" in data["no_awards_context"]

        # Enhanced fields still present for zero-award Tribes
        assert "fiscal_year_range" in data
        assert "yearly_obligations" in data

    def test_cache_trend_increasing(self, tmp_path):
        """Awards heavily weighted to later years -> trend=increasing."""
        matcher = _make_matcher(tmp_path, SAMPLE_TRIBES[:1])
        matched = {
            "epa_001": [
                {
                    "award_id": "EARLY",
                    "cfda": "15.156",
                    "obligation": 10000.0,
                    "start_date": "2022-03-01",
                },
                {
                    "award_id": "LATE-1",
                    "cfda": "15.156",
                    "obligation": 200000.0,
                    "start_date": "2025-03-01",
                },
                {
                    "award_id": "LATE-2",
                    "cfda": "97.047",
                    "obligation": 300000.0,
                    "start_date": "2026-01-01",
                },
            ],
        }

        matcher.write_cache(matched, fy_start=2022, fy_end=2026)
        cache_path = tmp_path / "award_cache" / "epa_001.json"
        with open(cache_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert data["trend"] == "increasing"

    def test_cache_trend_none_no_awards(self, tmp_path):
        """No awards for a Tribe -> trend=none."""
        matcher = _make_matcher(tmp_path, SAMPLE_TRIBES[:1])
        matcher.write_cache({}, fy_start=2022, fy_end=2026)

        cache_path = tmp_path / "award_cache" / "epa_001.json"
        with open(cache_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert data["trend"] == "none"

    def test_yearly_obligations_summing(self, tmp_path):
        """Yearly obligations correctly sum awards per FY."""
        matcher = _make_matcher(tmp_path, SAMPLE_TRIBES[:1])
        matched = {
            "epa_001": [
                {
                    "award_id": "FY24-A",
                    "cfda": "15.156",
                    "obligation": 100000.0,
                    "start_date": "2024-01-15",
                },
                {
                    "award_id": "FY24-B",
                    "cfda": "97.047",
                    "obligation": 50000.0,
                    "start_date": "2024-06-01",
                },
                {
                    "award_id": "FY25-A",
                    "cfda": "15.156",
                    "obligation": 200000.0,
                    "start_date": "2025-02-01",
                },
            ],
        }

        matcher.write_cache(matched, fy_start=2022, fy_end=2026)
        cache_path = tmp_path / "award_cache" / "epa_001.json"
        with open(cache_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        yearly = data["yearly_obligations"]
        assert yearly["2024"] == 150000.0  # FY24-A + FY24-B
        assert yearly["2025"] == 200000.0  # FY25-A
        assert yearly["2022"] == 0.0       # No awards in FY22
        assert yearly["2026"] == 0.0       # No awards in FY26

    def test_multiple_tribes_in_cache(self, tmp_path):
        """Multiple Tribes each get their own cache file."""
        matcher = _make_matcher(tmp_path, SAMPLE_TRIBES)
        matched = {
            "epa_001": [
                {
                    "award_id": "N-001",
                    "cfda": "15.156",
                    "obligation": 100000.0,
                    "start_date": "2024-05-01",
                },
            ],
            # epa_002 and epa_003 have no awards
        }

        count = matcher.write_cache(matched, fy_start=2022, fy_end=2026)
        assert count == 3  # One file per Tribe

        # Navajo has awards
        navajo_path = tmp_path / "award_cache" / "epa_001.json"
        with open(navajo_path, "r", encoding="utf-8") as f:
            navajo = json.load(f)
        assert navajo["award_count"] == 1
        assert "no_awards_context" not in navajo

        # Muckleshoot has no awards
        muck_path = tmp_path / "award_cache" / "epa_002.json"
        with open(muck_path, "r", encoding="utf-8") as f:
            muck = json.load(f)
        assert muck["award_count"] == 0
        assert "no_awards_context" in muck


# ── Consortium filtering in match_all_awards ──


class TestMatchAllAwardsConsortium:
    """Test that match_all_awards separates consortium awards."""

    def test_consortium_filtered_from_matched(self, tmp_path):
        """Consortium awards are NOT in matched output."""
        aliases = {"navajo nation": "epa_001"}
        matcher = _make_matcher(tmp_path, SAMPLE_TRIBES, aliases=aliases)

        awards_by_cfda = {
            "15.156": [
                {
                    "Award ID": "REAL-001",
                    "Recipient Name": "NAVAJO NATION",
                    "Total Obligation": 500000,
                    "Start Date": "2024-01-15",
                },
                {
                    "Award ID": "CONSORT-001",
                    "Recipient Name": "INTER TRIBAL COUNCIL OF ARIZONA",
                    "Total Obligation": 1000000,
                    "Start Date": "2024-03-01",
                },
            ],
        }

        matched = matcher.match_all_awards(awards_by_cfda)

        # Navajo's award is matched
        assert "epa_001" in matched
        assert len(matched["epa_001"]) == 1

        # Consortium award is NOT in any Tribe's matched list
        all_matched_names = []
        for tribe_awards in matched.values():
            for award in tribe_awards:
                all_matched_names.append(award.get("recipient_name_raw", ""))
        assert "INTER TRIBAL COUNCIL OF ARIZONA" not in all_matched_names

    def test_consortium_stored_on_instance(self, tmp_path):
        """Consortium awards are accessible via _last_consortium_awards."""
        aliases = {"navajo nation": "epa_001"}
        matcher = _make_matcher(tmp_path, SAMPLE_TRIBES, aliases=aliases)

        awards_by_cfda = {
            "15.156": [
                {
                    "Award ID": "CONSORT-001",
                    "Recipient Name": "INTER TRIBAL COUNCIL OF ARIZONA",
                    "Total Obligation": 1000000,
                    "Start Date": "2024-03-01",
                },
                {
                    "Award ID": "CONSORT-002",
                    "Recipient Name": "NORTHWEST PORTLAND AREA INDIAN HEALTH BOARD",
                    "Total Obligation": 500000,
                    "Start Date": "2024-06-01",
                },
            ],
        }

        matcher.match_all_awards(awards_by_cfda)

        assert hasattr(matcher, "_last_consortium_awards")
        assert len(matcher._last_consortium_awards) == 2
        names = [a["recipient_name"] for a in matcher._last_consortium_awards]
        assert "INTER TRIBAL COUNCIL OF ARIZONA" in names
        assert "NORTHWEST PORTLAND AREA INDIAN HEALTH BOARD" in names

    def test_no_consortium_awards(self, tmp_path):
        """When no consortium awards exist, _last_consortium_awards is empty."""
        aliases = {"navajo nation": "epa_001"}
        matcher = _make_matcher(tmp_path, SAMPLE_TRIBES, aliases=aliases)

        awards_by_cfda = {
            "15.156": [
                {
                    "Award ID": "REAL-001",
                    "Recipient Name": "NAVAJO NATION",
                    "Total Obligation": 500000,
                    "Start Date": "2024-01-15",
                },
            ],
        }

        matcher.match_all_awards(awards_by_cfda)
        assert matcher._last_consortium_awards == []
