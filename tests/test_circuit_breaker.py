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
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

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
