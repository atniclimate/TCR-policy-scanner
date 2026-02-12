"""Tests for confidence scoring module (Plan 15-01).

Validates compute_confidence, confidence_level, and section_confidence
with boundary conditions, edge cases, and known-value computations.

30+ tests covering freshness decay, threshold boundaries, and source
weight lookups.
"""

from __future__ import annotations

import math

import pytest

from datetime import datetime, timezone, timedelta

from src.packets.confidence import (
    DEFAULT_SOURCE_WEIGHTS,
    compute_confidence,
    confidence_level,
    section_confidence,
)


# ---------------------------------------------------------------------------
# compute_confidence Tests (~15 tests)
# ---------------------------------------------------------------------------


class TestComputeConfidence:
    """Validate compute_confidence with various inputs."""

    def test_fresh_data_full_weight(self):
        """Same-day data returns source_weight * e^0 = source_weight."""
        ref = datetime(2026, 2, 12, tzinfo=timezone.utc)
        score = compute_confidence(0.80, "2026-02-12", reference_date=ref)
        assert score == 0.80

    def test_stale_data_decays(self):
        """Data 69 days old (half-life) returns ~half the weight."""
        ref = datetime(2026, 2, 12, tzinfo=timezone.utc)
        # 69 days ago
        date_str = (ref - timedelta(days=69)).isoformat()
        score = compute_confidence(1.0, date_str, reference_date=ref)
        # With decay_rate=0.01, e^(-0.01*69) ≈ 0.5016
        assert 0.49 <= score <= 0.51

    def test_very_stale_data(self):
        """Data 365 days old has very low confidence."""
        ref = datetime(2026, 2, 12, tzinfo=timezone.utc)
        date_str = (ref - timedelta(days=365)).isoformat()
        score = compute_confidence(1.0, date_str, reference_date=ref)
        # e^(-0.01*365) ≈ 0.0255
        assert score < 0.03

    def test_invalid_date_string(self):
        """Invalid date string returns very stale score (365 days)."""
        score = compute_confidence(
            0.80,
            "not-a-date",
            reference_date=datetime(2026, 2, 12, tzinfo=timezone.utc),
        )
        # Should use 365 days -> 0.80 * e^(-3.65) ≈ 0.021
        expected = round(0.80 * math.exp(-0.01 * 365), 3)
        assert score == expected

    def test_none_date(self):
        """None date returns very stale score."""
        score = compute_confidence(
            0.80,
            None,
            reference_date=datetime(2026, 2, 12, tzinfo=timezone.utc),
        )
        expected = round(0.80 * math.exp(-0.01 * 365), 3)
        assert score == expected

    def test_custom_decay_rate(self):
        """Custom decay_rate changes decay speed."""
        ref = datetime(2026, 2, 12, tzinfo=timezone.utc)
        date_str = (ref - timedelta(days=30)).isoformat()
        # Default decay: 0.01 -> e^(-0.3) ≈ 0.741
        default_score = compute_confidence(
            1.0, date_str, decay_rate=0.01, reference_date=ref
        )
        # Fast decay: 0.05 -> e^(-1.5) ≈ 0.223
        fast_score = compute_confidence(
            1.0, date_str, decay_rate=0.05, reference_date=ref
        )
        assert fast_score < default_score

    def test_custom_reference_date(self):
        """Custom reference_date changes staleness calculation."""
        # Data from 2026-01-01, ref at 2026-01-01 = 0 days
        score = compute_confidence(
            0.90,
            "2026-01-01",
            reference_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        assert score == 0.90

    def test_future_date(self):
        """Future update date (negative days) clamps to 0 days."""
        ref = datetime(2026, 2, 12, tzinfo=timezone.utc)
        future_str = (ref + timedelta(days=10)).isoformat()
        score = compute_confidence(0.80, future_str, reference_date=ref)
        # max(0, negative_days) = 0 -> e^0 = 1.0 -> 0.80
        assert score == 0.80

    def test_weight_zero(self):
        """Source weight 0.0 always returns 0.0."""
        score = compute_confidence(
            0.0,
            "2026-02-12",
            reference_date=datetime(2026, 2, 12, tzinfo=timezone.utc),
        )
        assert score == 0.0

    def test_weight_one(self):
        """Source weight 1.0 with fresh data returns 1.0."""
        score = compute_confidence(
            1.0,
            "2026-02-12",
            reference_date=datetime(2026, 2, 12, tzinfo=timezone.utc),
        )
        assert score == 1.0

    def test_timezone_aware_date(self):
        """Timezone-aware date string is handled correctly."""
        ref = datetime(2026, 2, 12, tzinfo=timezone.utc)
        score = compute_confidence(
            0.80,
            "2026-02-12T00:00:00+00:00",
            reference_date=ref,
        )
        assert score == 0.80

    def test_timezone_naive_date(self):
        """Timezone-naive date string is treated as UTC."""
        ref = datetime(2026, 2, 12, tzinfo=timezone.utc)
        score = compute_confidence(
            0.80,
            "2026-02-12T00:00:00",
            reference_date=ref,
        )
        assert score == 0.80

    def test_known_value_30_days(self):
        """Known value: 30 days old, weight 0.80, decay 0.01."""
        ref = datetime(2026, 2, 12, tzinfo=timezone.utc)
        date_str = (ref - timedelta(days=30)).isoformat()
        score = compute_confidence(0.80, date_str, reference_date=ref)
        expected = round(0.80 * math.exp(-0.01 * 30), 3)
        assert score == expected

    def test_result_rounded_to_3_decimals(self):
        """Result is rounded to 3 decimal places."""
        ref = datetime(2026, 2, 12, tzinfo=timezone.utc)
        date_str = (ref - timedelta(days=17)).isoformat()
        score = compute_confidence(0.73, date_str, reference_date=ref)
        # Verify rounding: score should have at most 3 decimal places
        assert score == round(score, 3)

    def test_default_reference_date_uses_now(self):
        """When no reference_date, uses current UTC time."""
        # Fresh data should return close to the weight
        now_str = datetime.now(timezone.utc).isoformat()
        score = compute_confidence(0.80, now_str)
        assert 0.79 <= score <= 0.80


# ---------------------------------------------------------------------------
# confidence_level Tests (~8 tests)
# ---------------------------------------------------------------------------


class TestConfidenceLevel:
    """Validate confidence_level threshold boundaries."""

    def test_high_at_0_7(self):
        """Score exactly 0.7 maps to HIGH."""
        assert confidence_level(0.7) == "HIGH"

    def test_high_at_1_0(self):
        """Score 1.0 maps to HIGH."""
        assert confidence_level(1.0) == "HIGH"

    def test_high_at_0_9(self):
        """Score 0.9 maps to HIGH."""
        assert confidence_level(0.9) == "HIGH"

    def test_medium_at_0_4(self):
        """Score exactly 0.4 maps to MEDIUM."""
        assert confidence_level(0.4) == "MEDIUM"

    def test_medium_at_0_69(self):
        """Score 0.69 maps to MEDIUM."""
        assert confidence_level(0.69) == "MEDIUM"

    def test_medium_at_0_5(self):
        """Score 0.5 maps to MEDIUM."""
        assert confidence_level(0.5) == "MEDIUM"

    def test_low_at_0_39(self):
        """Score 0.39 maps to LOW."""
        assert confidence_level(0.39) == "LOW"

    def test_low_at_0_0(self):
        """Score 0.0 maps to LOW."""
        assert confidence_level(0.0) == "LOW"

    def test_low_at_0_1(self):
        """Score 0.1 maps to LOW."""
        assert confidence_level(0.1) == "LOW"


# ---------------------------------------------------------------------------
# section_confidence Tests (~8 tests)
# ---------------------------------------------------------------------------


class TestSectionConfidence:
    """Validate section_confidence convenience wrapper."""

    def test_known_source(self):
        """Known source uses its weight from DEFAULT_SOURCE_WEIGHTS."""
        ref = datetime(2026, 2, 12, tzinfo=timezone.utc)
        result = section_confidence(
            "congress_gov", "2026-02-12", reference_date=ref
        )
        assert result["source"] == "congress_gov"
        assert result["score"] == DEFAULT_SOURCE_WEIGHTS["congress_gov"]
        assert result["level"] == "HIGH"
        assert result["last_updated"] == "2026-02-12"

    def test_unknown_source_uses_fallback(self):
        """Unknown source uses 0.50 fallback weight."""
        ref = datetime(2026, 2, 12, tzinfo=timezone.utc)
        result = section_confidence(
            "unknown_source", "2026-02-12", reference_date=ref
        )
        assert result["score"] == 0.50
        assert result["source"] == "unknown_source"

    def test_dict_structure(self):
        """section_confidence returns dict with expected keys."""
        ref = datetime(2026, 2, 12, tzinfo=timezone.utc)
        result = section_confidence(
            "federal_register", "2026-02-12", reference_date=ref
        )
        assert set(result.keys()) == {"score", "level", "source", "last_updated"}

    def test_fresh_high_confidence(self):
        """Fresh data from high-weight source returns HIGH."""
        ref = datetime(2026, 2, 12, tzinfo=timezone.utc)
        result = section_confidence(
            "federal_register", "2026-02-12", reference_date=ref
        )
        assert result["level"] == "HIGH"
        assert result["score"] == 0.90

    def test_stale_low_confidence(self):
        """Very stale data returns LOW regardless of source weight."""
        ref = datetime(2026, 2, 12, tzinfo=timezone.utc)
        stale_date = (ref - timedelta(days=365)).isoformat()
        result = section_confidence(
            "federal_register", stale_date, reference_date=ref
        )
        assert result["level"] == "LOW"
        assert result["score"] < 0.10

    def test_grants_gov_weight(self):
        """grants_gov uses weight 0.85."""
        ref = datetime(2026, 2, 12, tzinfo=timezone.utc)
        result = section_confidence(
            "grants_gov", "2026-02-12", reference_date=ref
        )
        assert result["score"] == 0.85

    def test_usaspending_weight(self):
        """usaspending uses weight 0.70."""
        ref = datetime(2026, 2, 12, tzinfo=timezone.utc)
        result = section_confidence(
            "usaspending", "2026-02-12", reference_date=ref
        )
        assert result["score"] == 0.70
        assert result["level"] == "HIGH"

    def test_inferred_source_medium(self):
        """inferred source with fresh data returns MEDIUM (weight 0.50)."""
        ref = datetime(2026, 2, 12, tzinfo=timezone.utc)
        result = section_confidence(
            "inferred", "2026-02-12", reference_date=ref
        )
        assert result["score"] == 0.50
        assert result["level"] == "MEDIUM"
