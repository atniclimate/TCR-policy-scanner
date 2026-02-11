"""Tests for USASpending batch query engine (per-year, multi-CFDA).

Covers:
- CFDA map completeness (14 entries including 11.483, 66.038)
- Expanded award type codes (grants + direct payments)
- Per-year payload construction with fiscal year boundaries
- Pagination across multiple pages
- Truncation safety at page 100 (10K records)
- Multi-year orchestration with default range
- Per-(CFDA, FY) failure isolation
"""

import asyncio
import logging
from unittest.mock import AsyncMock, MagicMock, patch

from src.config import FISCAL_YEAR_INT
from src.scrapers.usaspending import (
    CFDA_TO_PROGRAM,
    TRIBAL_AWARD_TYPE_CODES,
    USASpendingScraper,
)


def _make_scraper():
    """Create a configured USASpendingScraper instance for testing."""
    config = {
        "sources": {
            "usaspending": {
                "base_url": "https://api.usaspending.gov/api/v2",
            },
        },
    }
    return USASpendingScraper(config)


# ── CFDA map and award type codes ──


class TestCFDAMapCompleteness:
    """Verify all 14 program CFDAs are mapped."""

    def test_cfda_map_has_14_entries(self):
        assert len(CFDA_TO_PROGRAM) == 14

    def test_noaa_tribal_present(self):
        assert "11.483" in CFDA_TO_PROGRAM
        assert CFDA_TO_PROGRAM["11.483"] == "noaa_tribal"

    def test_epa_tribal_air_present(self):
        assert "66.038" in CFDA_TO_PROGRAM
        assert CFDA_TO_PROGRAM["66.038"] == "epa_tribal_air"

    def test_all_values_are_nonempty_strings(self):
        for cfda, program_id in CFDA_TO_PROGRAM.items():
            assert isinstance(program_id, str), f"CFDA {cfda} has non-string value"
            assert len(program_id) > 0, f"CFDA {cfda} has empty program ID"


class TestAwardTypeCodes:
    """Verify expanded award type codes include direct payments."""

    def test_award_type_codes_expanded(self):
        assert TRIBAL_AWARD_TYPE_CODES == ["02", "03", "04", "05", "06", "10"]

    def test_excludes_loans_and_insurance(self):
        for code in ["07", "08", "09", "11"]:
            assert code not in TRIBAL_AWARD_TYPE_CODES


# ── Per-year fetch method ──


class TestFetchByYear:
    """Tests for fetch_tribal_awards_by_year()."""

    def test_builds_correct_payload(self):
        """Verify time_period, award_type_codes, and recipient filter in payload."""
        scraper = _make_scraper()
        mock_session = MagicMock()

        captured_payloads = []

        async def capture_request(_session, _method, _url, **kwargs):
            captured_payloads.append(kwargs.get("json", {}))
            return {"results": [], "page_metadata": {"hasNext": False}}

        scraper._request_with_retry = capture_request

        async def run():
            return await scraper.fetch_tribal_awards_by_year(
                mock_session, "15.156", 2024,
            )

        results = asyncio.run(run())

        assert len(captured_payloads) == 1
        payload = captured_payloads[0]
        filters = payload["filters"]

        # Fiscal year 2024: Oct 1, 2023 through Sep 30, 2024
        assert filters["time_period"] == [
            {"start_date": "2023-10-01", "end_date": "2024-09-30"}
        ]
        assert filters["award_type_codes"] == [
            "02", "03", "04", "05", "06", "10"
        ]
        assert filters["program_numbers"] == ["15.156"]
        assert filters["recipient_type_names"] == [
            "indian_native_american_tribal_government"
        ]
        assert results == []

    def test_paginates_across_pages(self):
        """Verify pagination collects results from multiple pages."""
        scraper = _make_scraper()
        mock_session = MagicMock()

        page_1_results = [
            {"Award ID": "A001", "Recipient Name": "Tribe A", "Award Amount": 100000},
            {"Award ID": "A002", "Recipient Name": "Tribe B", "Award Amount": 50000},
        ]
        page_2_results = [
            {"Award ID": "A003", "Recipient Name": "Tribe C", "Award Amount": 25000},
        ]

        call_count = 0

        async def mock_request(_session, _method, _url, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return {
                    "results": page_1_results,
                    "page_metadata": {"hasNext": True},
                }
            return {
                "results": page_2_results,
                "page_metadata": {"hasNext": False},
            }

        scraper._request_with_retry = mock_request

        async def run():
            return await scraper.fetch_tribal_awards_by_year(
                mock_session, "97.047", 2025,
            )

        results = asyncio.run(run())

        assert len(results) == 3
        assert call_count == 2

        # Verify _fiscal_year injected into every result
        for r in results:
            assert r["_fiscal_year"] == 2025

    def test_injects_fiscal_year_field(self):
        """Verify _fiscal_year is injected into each result dict."""
        scraper = _make_scraper()
        mock_session = MagicMock()

        async def mock_request(_session, _method, _url, **kwargs):
            return {
                "results": [{"Award ID": "X001"}],
                "page_metadata": {"hasNext": False},
            }

        scraper._request_with_retry = mock_request

        async def run():
            return await scraper.fetch_tribal_awards_by_year(
                mock_session, "15.156", 2023,
            )

        results = asyncio.run(run())

        assert len(results) == 1
        assert results[0]["_fiscal_year"] == 2023

    def test_truncation_warning_at_page_100(self, caplog):
        """Verify method stops at page 100 and logs a warning about truncation."""
        scraper = _make_scraper()
        mock_session = MagicMock()

        call_count = 0

        async def mock_request(_session, _method, _url, **kwargs):
            nonlocal call_count
            call_count += 1
            return {
                "results": [{"Award ID": f"A{call_count:04d}"}],
                "page_metadata": {"hasNext": True},
            }

        scraper._request_with_retry = mock_request

        async def run():
            return await scraper.fetch_tribal_awards_by_year(
                mock_session, "15.156", 2024,
            )

        with caplog.at_level(logging.WARNING):
            results = asyncio.run(run())

        # Should stop at page 100 (100 calls), not loop forever
        assert call_count == 100
        assert len(results) == 100

        # Check truncation warning was logged
        truncation_warnings = [
            r for r in caplog.records
            if "truncated" in r.message.lower() or "page 100" in r.message
        ]
        assert len(truncation_warnings) >= 1

    def test_handles_request_failure_gracefully(self):
        """Verify method returns partial results on mid-pagination failure."""
        scraper = _make_scraper()
        mock_session = MagicMock()

        call_count = 0

        async def mock_request(_session, _method, _url, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return {
                    "results": [{"Award ID": "A001"}],
                    "page_metadata": {"hasNext": True},
                }
            raise Exception("Connection timeout")

        scraper._request_with_retry = mock_request

        async def run():
            return await scraper.fetch_tribal_awards_by_year(
                mock_session, "15.156", 2024,
            )

        results = asyncio.run(run())

        # Should return partial results from page 1
        assert len(results) == 1
        assert results[0]["_fiscal_year"] == 2024


# ── Multi-year orchestration ──


class TestMultiYearFetch:
    """Tests for fetch_all_tribal_awards_multi_year()."""

    def test_default_range_covers_5_years(self):
        """Verify default FY range is (FISCAL_YEAR_INT - 4) to FISCAL_YEAR_INT."""
        scraper = _make_scraper()
        called_with = []

        async def mock_by_year(_session, cfda, fy):
            called_with.append((cfda, fy))
            return []

        scraper.fetch_tribal_awards_by_year = mock_by_year

        async def run():
            with patch("src.scrapers.usaspending.asyncio.sleep", new_callable=AsyncMock):
                return await scraper.fetch_all_tribal_awards_multi_year()

        result = asyncio.run(run())

        # 14 CFDAs x 5 fiscal years = 70 calls
        assert len(called_with) == 70

        # Verify the fiscal year range
        fy_values = sorted(set(fy for _, fy in called_with))
        expected_fys = list(range(FISCAL_YEAR_INT - 4, FISCAL_YEAR_INT + 1))
        assert fy_values == expected_fys

        # Verify all 14 CFDAs were queried
        cfda_values = sorted(set(cfda for cfda, _ in called_with))
        assert len(cfda_values) == 14

        # Result should have all 14 CFDAs as keys
        assert len(result) == 14
        for cfda in CFDA_TO_PROGRAM:
            assert cfda in result

    def test_custom_range(self):
        """Verify custom fy_start/fy_end restricts the query range."""
        scraper = _make_scraper()
        called_with = []

        async def mock_by_year(_session, cfda, fy):
            called_with.append((cfda, fy))
            return [{"Award ID": f"{cfda}-{fy}"}]

        scraper.fetch_tribal_awards_by_year = mock_by_year

        async def run():
            with patch("src.scrapers.usaspending.asyncio.sleep", new_callable=AsyncMock):
                return await scraper.fetch_all_tribal_awards_multi_year(
                    fy_start=2023, fy_end=2024,
                )

        result = asyncio.run(run())

        # 14 CFDAs x 2 fiscal years = 28 calls
        assert len(called_with) == 28
        fy_values = sorted(set(fy for _, fy in called_with))
        assert fy_values == [2023, 2024]

        # Each CFDA should have 2 results (one per year)
        for cfda in CFDA_TO_PROGRAM:
            assert len(result[cfda]) == 2

    def test_per_cfda_failure_isolation(self):
        """Verify one (CFDA, FY) failure doesn't abort the batch."""
        scraper = _make_scraper()
        fail_cfda = "15.156"
        fail_fy = FISCAL_YEAR_INT

        async def mock_by_year(_session, cfda, fy):
            if cfda == fail_cfda and fy == fail_fy:
                raise Exception("API timeout for 15.156")
            return [{"Award ID": f"{cfda}-{fy}", "Recipient Name": "Test Tribe"}]

        scraper.fetch_tribal_awards_by_year = mock_by_year

        async def run():
            with patch("src.scrapers.usaspending.asyncio.sleep", new_callable=AsyncMock):
                return await scraper.fetch_all_tribal_awards_multi_year()

        result = asyncio.run(run())

        # All CFDAs should have entries
        assert len(result) == 14

        # The failed CFDA should still exist with partial results (4 out of 5 years)
        assert fail_cfda in result
        assert len(result[fail_cfda]) == 4  # 5 years minus the 1 that failed

        # Other CFDAs should have all 5 years
        for cfda in CFDA_TO_PROGRAM:
            if cfda != fail_cfda:
                assert len(result[cfda]) == 5

    def test_aggregates_results_by_cfda(self):
        """Verify results from multiple years are aggregated under the CFDA key."""
        scraper = _make_scraper()

        async def mock_by_year(_session, cfda, fy):
            return [
                {"Award ID": f"{cfda}-{fy}-001", "Award Amount": 100000},
                {"Award ID": f"{cfda}-{fy}-002", "Award Amount": 50000},
            ]

        scraper.fetch_tribal_awards_by_year = mock_by_year

        async def run():
            with patch("src.scrapers.usaspending.asyncio.sleep", new_callable=AsyncMock):
                return await scraper.fetch_all_tribal_awards_multi_year(
                    fy_start=2024, fy_end=2025,
                )

        result = asyncio.run(run())

        # 2 results per (CFDA, FY), 2 years = 4 per CFDA
        for cfda in CFDA_TO_PROGRAM:
            assert len(result[cfda]) == 4
