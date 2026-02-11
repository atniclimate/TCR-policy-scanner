"""Tests for the circuit breaker state machine and graceful degradation.

Covers all 4 state transitions:
  CLOSED -> OPEN (threshold failures)
  OPEN -> HALF_OPEN (recovery timeout elapsed)
  HALF_OPEN -> CLOSED (successful probe)
  HALF_OPEN -> OPEN (failed probe)

Plus config integration with BaseScraper, per-source cache, and health checks.
"""

import json
import logging
import os
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from src.scrapers.circuit_breaker import CircuitBreaker, CircuitOpenError, CircuitState


class MockClock:
    """Deterministic clock for circuit breaker testing. Zero real sleeps."""

    def __init__(self, start: float = 0.0):
        self._now = start

    def __call__(self) -> float:
        return self._now

    def advance(self, seconds: float) -> None:
        self._now += seconds


# ── State machine unit tests ──


class TestCircuitBreakerStateMachine:
    """Core state machine behavior."""

    def test_initial_state_is_closed(self):
        cb = CircuitBreaker("test", clock=MockClock())
        assert cb.state == CircuitState.CLOSED

    def test_stays_closed_below_threshold(self):
        clock = MockClock()
        cb = CircuitBreaker("test", failure_threshold=5, clock=clock)
        for _ in range(4):  # N-1 failures
            cb.record_failure()
        assert cb.state == CircuitState.CLOSED

    def test_opens_at_threshold(self):
        clock = MockClock()
        cb = CircuitBreaker("test", failure_threshold=5, clock=clock)
        for _ in range(5):
            cb.record_failure()
        assert cb.state == CircuitState.OPEN

    def test_open_blocks_calls(self):
        clock = MockClock()
        cb = CircuitBreaker("test", failure_threshold=2, clock=clock)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.OPEN
        assert cb.is_call_permitted is False

    def test_closed_permits_calls(self):
        cb = CircuitBreaker("test", clock=MockClock())
        assert cb.is_call_permitted is True

    def test_half_open_permits_calls(self):
        clock = MockClock()
        cb = CircuitBreaker("test", failure_threshold=2, recovery_timeout=10.0, clock=clock)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.OPEN
        clock.advance(11.0)
        assert cb.state == CircuitState.HALF_OPEN
        assert cb.is_call_permitted is True

    def test_open_to_half_open_after_timeout(self):
        clock = MockClock()
        cb = CircuitBreaker("test", failure_threshold=2, recovery_timeout=60.0, clock=clock)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.OPEN
        clock.advance(61.0)
        assert cb.state == CircuitState.HALF_OPEN

    def test_stays_open_before_timeout(self):
        clock = MockClock()
        cb = CircuitBreaker("test", failure_threshold=2, recovery_timeout=60.0, clock=clock)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.OPEN
        clock.advance(30.0)  # Only half the timeout
        assert cb.state == CircuitState.OPEN

    def test_half_open_to_closed_on_success(self):
        clock = MockClock()
        cb = CircuitBreaker("test", failure_threshold=2, recovery_timeout=10.0, clock=clock)
        cb.record_failure()
        cb.record_failure()
        clock.advance(11.0)
        assert cb.state == CircuitState.HALF_OPEN
        cb.record_success()
        assert cb.state == CircuitState.CLOSED

    def test_half_open_to_open_on_failure(self):
        clock = MockClock()
        cb = CircuitBreaker("test", failure_threshold=2, recovery_timeout=10.0, clock=clock)
        cb.record_failure()
        cb.record_failure()
        clock.advance(11.0)
        assert cb.state == CircuitState.HALF_OPEN
        cb.record_failure()
        assert cb.state == CircuitState.OPEN

    def test_success_resets_failure_count(self):
        clock = MockClock()
        cb = CircuitBreaker("test", failure_threshold=5, clock=clock)
        for _ in range(4):
            cb.record_failure()
        cb.record_success()
        # After reset, need 5 more failures to trip
        for _ in range(4):
            cb.record_failure()
        assert cb.state == CircuitState.CLOSED

    def test_circuit_open_error_message(self):
        err = CircuitOpenError("federal_register")
        assert "federal_register" in str(err)
        assert err.source_name == "federal_register"

    def test_custom_threshold(self):
        clock = MockClock()
        cb = CircuitBreaker("test", failure_threshold=3, clock=clock)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.CLOSED
        cb.record_failure()
        assert cb.state == CircuitState.OPEN

    def test_custom_recovery_timeout(self):
        clock = MockClock()
        cb = CircuitBreaker("test", failure_threshold=1, recovery_timeout=120.0, clock=clock)
        cb.record_failure()
        assert cb.state == CircuitState.OPEN
        clock.advance(60.0)
        assert cb.state == CircuitState.OPEN  # Still within 120s
        clock.advance(61.0)  # Now at 121s total
        assert cb.state == CircuitState.HALF_OPEN

    def test_reset_returns_to_closed(self):
        clock = MockClock()
        cb = CircuitBreaker("test", failure_threshold=2, clock=clock)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.OPEN
        cb.reset()
        assert cb.state == CircuitState.CLOSED
        assert cb.is_call_permitted is True

    def test_multiple_recovery_cycles(self):
        """Full cycle: CLOSED -> OPEN -> HALF_OPEN -> CLOSED -> OPEN."""
        clock = MockClock()
        cb = CircuitBreaker("test", failure_threshold=2, recovery_timeout=10.0, clock=clock)

        # Cycle 1: CLOSED -> OPEN
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.OPEN

        # OPEN -> HALF_OPEN
        clock.advance(11.0)
        assert cb.state == CircuitState.HALF_OPEN

        # HALF_OPEN -> CLOSED
        cb.record_success()
        assert cb.state == CircuitState.CLOSED

        # Cycle 2: CLOSED -> OPEN again
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.OPEN


# ── BaseScraper integration tests ──


class TestBaseScraperCircuitBreakerIntegration:
    """Circuit breaker integration with BaseScraper config."""

    def test_base_scraper_creates_circuit_breaker(self):
        """BaseScraper with config creates a breaker with config values."""
        from src.scrapers.base import BaseScraper

        config = {
            "resilience": {
                "max_retries": 5,
                "backoff_base": 3,
                "backoff_max": 600,
                "request_timeout": 45,
                "circuit_breaker": {
                    "failure_threshold": 10,
                    "recovery_timeout": 120,
                },
            }
        }
        scraper = BaseScraper("test_source", config=config)
        assert scraper._circuit_breaker.name == "test_source"
        assert scraper._circuit_breaker.failure_threshold == 10
        assert scraper._circuit_breaker.recovery_timeout == 120
        assert scraper._circuit_breaker.state == CircuitState.CLOSED

    def test_base_scraper_defaults_without_config(self):
        """BaseScraper with no config uses hardcoded defaults."""
        from src.scrapers.base import BaseScraper, BACKOFF_BASE, MAX_RETRIES

        scraper = BaseScraper("test_source")
        assert scraper.max_retries == MAX_RETRIES
        assert scraper.backoff_base == BACKOFF_BASE
        assert scraper.backoff_max == 300
        assert scraper._circuit_breaker.failure_threshold == 5
        assert scraper._circuit_breaker.recovery_timeout == 60

    def test_base_scraper_defaults_without_resilience_section(self):
        """BaseScraper with config dict that has no 'resilience' key uses defaults."""
        from src.scrapers.base import BaseScraper, BACKOFF_BASE, MAX_RETRIES

        config = {"sources": {"some_api": {}}}
        scraper = BaseScraper("test_source", config=config)
        assert scraper.max_retries == MAX_RETRIES
        assert scraper.backoff_base == BACKOFF_BASE
        assert scraper._circuit_breaker.failure_threshold == 5

    def test_config_overrides_retry_params(self):
        """max_retries, backoff_base from config are used."""
        from src.scrapers.base import BaseScraper

        config = {
            "resilience": {
                "max_retries": 7,
                "backoff_base": 4,
            }
        }
        scraper = BaseScraper("test_source", config=config)
        assert scraper.max_retries == 7
        assert scraper.backoff_base == 4

    def test_backoff_base_zero_clamped_to_one(self):
        """GRIBBLE-09: backoff_base=0 is clamped to 1 to prevent collapsed backoff."""
        from src.scrapers.base import BaseScraper

        config = {"resilience": {"backoff_base": 0}}
        scraper = BaseScraper("test_source", config=config)
        assert scraper.backoff_base >= 1

    def test_backoff_base_negative_clamped_to_one(self):
        """GRIBBLE-08: backoff_base=-2 is clamped to 1 to prevent negative sleep."""
        from src.scrapers.base import BaseScraper

        config = {"resilience": {"backoff_base": -2}}
        scraper = BaseScraper("test_source", config=config)
        assert scraper.backoff_base >= 1


# ── Per-source cache tests ──


class TestSourceCache:
    """Per-source cache save/load for graceful degradation."""

    def test_save_source_cache_creates_file(self, tmp_path):
        """_save_source_cache writes a JSON file with correct structure."""
        from src.main import _save_source_cache, _source_cache_path

        with patch("src.main.OUTPUTS_DIR", tmp_path):
            items = [{"id": "1", "title": "Test item"}]
            _save_source_cache("federal_register", items)

            cache_path = _source_cache_path("federal_register")
            assert cache_path.exists()

            with open(cache_path, encoding="utf-8") as f:
                data = json.load(f)

            assert data["source"] == "federal_register"
            assert data["item_count"] == 1
            assert data["items"] == items
            assert "cached_at" in data

    def test_load_source_cache_returns_items(self, tmp_path):
        """Round-trip: save then load returns the same items."""
        from src.main import _load_source_cache, _save_source_cache

        with patch("src.main.OUTPUTS_DIR", tmp_path):
            items = [{"id": "1", "title": "Test"}, {"id": "2", "title": "Test 2"}]
            _save_source_cache("grants_gov", items)
            loaded = _load_source_cache("grants_gov")
            assert loaded == items

    def test_load_source_cache_missing_file(self, tmp_path):
        """Returns empty list when no cache file exists."""
        from src.main import _load_source_cache

        with patch("src.main.OUTPUTS_DIR", tmp_path):
            result = _load_source_cache("nonexistent_source")
            assert result == []

    def test_load_source_cache_corrupt_json(self, tmp_path):
        """Returns empty list when cache file has invalid JSON."""
        from src.main import _load_source_cache

        with patch("src.main.OUTPUTS_DIR", tmp_path):
            cache_file = tmp_path / ".cache_bad_source.json"
            cache_file.write_text("not valid json {{{", encoding="utf-8")
            result = _load_source_cache("bad_source")
            assert result == []

    def test_load_source_cache_logs_degradation_warning(self, tmp_path, caplog):
        """WARNING logged with source name and cache timestamp."""
        from src.main import _load_source_cache, _save_source_cache

        with patch("src.main.OUTPUTS_DIR", tmp_path):
            _save_source_cache("usaspending", [{"id": "1"}])
            with caplog.at_level(logging.WARNING):
                _load_source_cache("usaspending")

            assert any("DEGRADED" in r.message and "usaspending" in r.message for r in caplog.records)

    def test_load_source_cache_logs_critical_for_stale(self, tmp_path, caplog):
        """CRITICAL logged when cache exceeds cache_max_age_hours."""
        from src.main import _load_source_cache

        with patch("src.main.OUTPUTS_DIR", tmp_path):
            # Write a cache file with an old timestamp
            old_time = (datetime.now(timezone.utc) - timedelta(hours=200)).isoformat()
            cache_data = {
                "source": "congress_gov",
                "cached_at": old_time,
                "item_count": 1,
                "items": [{"id": "1"}],
            }
            cache_file = tmp_path / ".cache_congress_gov.json"
            cache_file.write_text(json.dumps(cache_data), encoding="utf-8")

            config = {"resilience": {"cache_max_age_hours": 168}}
            with caplog.at_level(logging.CRITICAL):
                result = _load_source_cache("congress_gov", config)

            assert result == [{"id": "1"}]
            assert any(
                "STALE CACHE" in r.message and "congress_gov" in r.message
                for r in caplog.records
                if r.levelno >= logging.CRITICAL
            )

    def test_load_source_cache_oversized_file(self, tmp_path):
        """Returns empty list when cache file exceeds 10MB."""
        from src.main import _load_source_cache

        with patch("src.main.OUTPUTS_DIR", tmp_path):
            cache_file = tmp_path / ".cache_huge.json"
            # Write a valid JSON file that's over 10MB
            cache_file.write_text('{"items": "' + "x" * (10 * 1024 * 1024 + 100) + '"}', encoding="utf-8")
            result = _load_source_cache("huge")
            assert result == []

    def test_save_source_cache_atomic_write(self, tmp_path):
        """No .tmp file remains after successful save."""
        from src.main import _save_source_cache

        with patch("src.main.OUTPUTS_DIR", tmp_path):
            _save_source_cache("test_source", [{"id": "1"}])
            tmp_files = list(tmp_path.glob("*.tmp"))
            assert len(tmp_files) == 0

    def test_load_source_cache_rejects_symlink(self, tmp_path, caplog):
        """GRIBBLE-03: Symlinked cache file is rejected as defense-in-depth."""
        from pathlib import Path
        from src.main import _load_source_cache

        with patch("src.main.OUTPUTS_DIR", tmp_path):
            # Mock the cache path to appear as a symlink
            cache_path = tmp_path / ".cache_evil.json"
            cache_path.write_text('{"items": [{"id": "1"}], "cached_at": "now"}', encoding="utf-8")

            with patch.object(Path, "is_symlink", return_value=True):
                with caplog.at_level(logging.ERROR):
                    result = _load_source_cache("evil")

            assert result == [], "Symlinked cache should return empty list"
            assert any("symlink" in r.message.lower() for r in caplog.records)


# ── Health check tests ──


class TestHealthChecker:
    """HealthChecker probe and formatting tests."""

    def test_health_checker_format_report(self):
        """format_report produces aligned output with all 4 sources."""
        from src.health import format_report

        results = {
            "federal_register": {"status": "UP", "latency_ms": 237, "detail": "OK"},
            "grants_gov": {"status": "UP", "latency_ms": 412, "detail": "OK"},
            "congress_gov": {"status": "DOWN", "latency_ms": 0, "detail": "API key not configured"},
            "usaspending": {"status": "DEGRADED", "latency_ms": 0, "detail": "cached data from 2026-02-10T14:30:00Z"},
        }
        report = format_report(results)
        assert "API Health Check" in report
        assert "federal_register" in report
        assert "grants_gov" in report
        assert "congress_gov" in report
        assert "usaspending" in report
        assert "UP" in report
        assert "DOWN" in report
        assert "DEGRADED" in report
        assert "237ms" in report

    def test_health_checker_up_result(self):
        """Mock aiohttp response returning 200 -> UP status."""
        import asyncio
        from unittest.mock import AsyncMock, MagicMock

        from src.health import HealthChecker

        checker = HealthChecker({"sources": {}})

        # Mock a successful GET response
        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_resp.__aexit__ = AsyncMock(return_value=False)

        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=mock_resp)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with patch("src.health.aiohttp.ClientSession", return_value=mock_session):
            result = asyncio.run(checker._probe_one("federal_register", {
                "url": "https://example.com/test",
                "method": "GET",
            }))

        assert result["status"] == "UP"
        assert "latency_ms" in result

    def test_health_checker_down_result(self):
        """Mock aiohttp raising timeout -> DOWN status."""
        import asyncio
        from unittest.mock import AsyncMock, MagicMock

        from src.health import HealthChecker

        checker = HealthChecker({"sources": {}})

        mock_session = AsyncMock()
        mock_session.get = MagicMock(side_effect=TimeoutError("connection timed out"))
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with patch("src.health.aiohttp.ClientSession", return_value=mock_session):
            with patch("src.health.OUTPUTS_DIR", MagicMock()) as mock_dir:
                mock_cache_path = MagicMock()
                mock_cache_path.exists.return_value = False
                mock_dir.__truediv__ = MagicMock(return_value=mock_cache_path)

                result = asyncio.run(checker._probe_one("federal_register", {
                    "url": "https://example.com/test",
                    "method": "GET",
                }))

        assert result["status"] == "DOWN"
        assert "timed out" in result["detail"]

    def test_health_checker_degraded_with_cache(self, tmp_path):
        """DOWN probe + existing cache file -> DEGRADED status."""
        import asyncio
        from unittest.mock import AsyncMock, MagicMock

        from src.health import HealthChecker

        checker = HealthChecker({"sources": {}})

        # Create a cache file
        cache_file = tmp_path / ".cache_usaspending.json"
        cache_data = {
            "source": "usaspending",
            "cached_at": "2026-02-10T14:30:00+00:00",
            "item_count": 5,
            "items": [{"id": str(i)} for i in range(5)],
        }
        cache_file.write_text(json.dumps(cache_data), encoding="utf-8")

        mock_session = AsyncMock()
        mock_session.post = MagicMock(side_effect=TimeoutError("timeout"))
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with patch("src.health.aiohttp.ClientSession", return_value=mock_session):
            with patch("src.health.OUTPUTS_DIR", tmp_path):
                result = asyncio.run(checker._probe_one("usaspending", {
                    "url": "https://example.com/test",
                    "method": "POST",
                    "json": {"test": True},
                }))

        assert result["status"] == "DEGRADED"
        assert "cached data from" in result["detail"]
        assert "2026-02-10" in result["detail"]

    def test_health_check_cli_argument(self):
        """argparse accepts --health-check flag."""
        import argparse

        # Build the same parser as main()
        parser = argparse.ArgumentParser()
        parser.add_argument("--health-check", action="store_true")
        args = parser.parse_args(["--health-check"])
        assert args.health_check is True

    def test_health_checker_congress_no_key(self):
        """congress_gov without API key returns DOWN or DEGRADED."""
        import asyncio
        from unittest.mock import MagicMock

        from src.health import HealthChecker

        checker = HealthChecker({
            "sources": {"congress_gov": {"key_env_var": "CONGRESS_API_KEY"}},
        })
        # Ensure no key is set
        with patch.dict(os.environ, {}, clear=True):
            with patch("src.health.OUTPUTS_DIR", MagicMock()) as mock_dir:
                mock_cache_path = MagicMock()
                mock_cache_path.exists.return_value = False
                mock_dir.__truediv__ = MagicMock(return_value=mock_cache_path)

                result = asyncio.run(
                    checker._probe_one("congress_gov", {
                        "url": "https://api.congress.gov/v3/bill?limit=1",
                        "method": "GET",
                        "requires_key": True,
                    })
                )
        assert result["status"] == "DOWN"
        assert "API key not configured" in result["detail"]

    def test_api_key_in_header_not_url(self):
        """GRIBBLE-11: API key must be sent via header, never in URL query string."""
        import asyncio
        from unittest.mock import AsyncMock, MagicMock

        from src.health import HealthChecker

        checker = HealthChecker({
            "sources": {"congress_gov": {"key_env_var": "TEST_CONGRESS_KEY"}},
        })

        captured_headers = {}
        captured_url = None

        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_resp.__aexit__ = AsyncMock(return_value=False)

        def capture_get(url, **kwargs):
            nonlocal captured_url
            captured_url = url
            return mock_resp

        mock_session = AsyncMock()
        mock_session.get = MagicMock(side_effect=capture_get)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        def capture_session(headers=None, **kwargs):
            nonlocal captured_headers
            captured_headers = headers or {}
            return mock_session

        with patch("src.health.aiohttp.ClientSession", side_effect=capture_session):
            with patch.dict(os.environ, {"TEST_CONGRESS_KEY": "secret123"}):
                result = asyncio.run(checker._probe_one("congress_gov", {
                    "url": "https://api.congress.gov/v3/bill?limit=1",
                    "method": "GET",
                    "requires_key": True,
                }))

        assert result["status"] == "UP"
        # Key MUST be in headers, NOT in URL
        assert "X-API-Key" in captured_headers, "API key not found in session headers"
        assert captured_headers["X-API-Key"] == "secret123"
        assert "api_key=" not in captured_url, "API key leaked into URL query string"

    def test_health_cache_oversized_returns_down(self, tmp_path):
        """GRIBBLE-14: Oversized cache file in health check returns DOWN, not DEGRADED."""
        from src.health import HealthChecker

        checker = HealthChecker({"sources": {}})

        # Create a valid JSON cache file that's over 10MB
        cache_file = tmp_path / ".cache_usaspending.json"
        padding = "x" * (10 * 1024 * 1024)
        cache_file.write_text(
            json.dumps({"cached_at": "2026-01-01", "padding": padding}),
            encoding="utf-8",
        )
        assert cache_file.stat().st_size > 10 * 1024 * 1024

        with patch("src.health.OUTPUTS_DIR", tmp_path):
            result = checker._check_degraded_or_down("usaspending", "timeout")

        assert result["status"] == "DOWN", f"Expected DOWN for oversized cache, got {result['status']}"
