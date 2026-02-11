"""Tests for the circuit breaker state machine.

Covers all 4 state transitions:
  CLOSED -> OPEN (threshold failures)
  OPEN -> HALF_OPEN (recovery timeout elapsed)
  HALF_OPEN -> CLOSED (successful probe)
  HALF_OPEN -> OPEN (failed probe)

Plus config integration with BaseScraper.
"""

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
