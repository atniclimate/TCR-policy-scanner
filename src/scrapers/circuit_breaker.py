"""Circuit breaker pattern for API resilience.

Implements the three-state circuit breaker:
  CLOSED  -- normal operation, requests flow through
  OPEN    -- API is down, fail fast without making requests
  HALF_OPEN -- recovery probe, one request allowed to test the API

State transitions:
  CLOSED -> OPEN: failure_threshold consecutive failures exhausted all retries
  OPEN -> HALF_OPEN: recovery_timeout seconds elapsed since last failure
  HALF_OPEN -> CLOSED: probe request succeeds
  HALF_OPEN -> OPEN: probe request fails

The breaker wraps the entire retry loop in BaseScraper._request_with_retry.
Retries happen inside CLOSED state; the breaker trips only when ALL retries
are exhausted. This prevents cascading failures to downed federal APIs while
still allowing aggressive retry on transient errors.
"""

import enum
import logging
import time
from collections.abc import Callable

logger = logging.getLogger(__name__)


class CircuitState(enum.Enum):
    """Three states of the circuit breaker."""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitOpenError(Exception):
    """Raised when a call is attempted on an OPEN circuit breaker.

    Attributes:
        source_name: The scraper source that tripped the breaker.
    """

    def __init__(self, source_name: str):
        self.source_name = source_name
        super().__init__(
            f"Circuit breaker OPEN for '{source_name}': "
            f"API is down, failing fast to avoid cascading failures"
        )


class CircuitBreaker:
    """Three-state circuit breaker with injectable clock for testing.

    Args:
        name: Identifier for this breaker (typically the scraper source name).
        failure_threshold: Consecutive failures before the circuit opens.
        recovery_timeout: Seconds to wait in OPEN state before probing.
        clock: Callable returning monotonic time in seconds.
               Defaults to time.monotonic. Inject a mock for deterministic tests.
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        clock: Callable[[], float] | None = None,
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self._clock = clock or time.monotonic

        # Internal state
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time = 0.0
        self._success_count = 0

    @property
    def state(self) -> CircuitState:
        """Current state, with automatic OPEN -> HALF_OPEN transition on timeout."""
        if (
            self._state == CircuitState.OPEN
            and (self._clock() - self._last_failure_time) >= self.recovery_timeout
        ):
            self._state = CircuitState.HALF_OPEN
            logger.info(
                "%s: circuit breaker transitioning OPEN -> HALF_OPEN "
                "(%.1fs elapsed since last failure)",
                self.name,
                self._clock() - self._last_failure_time,
            )
        return self._state

    @property
    def is_call_permitted(self) -> bool:
        """Whether a request is allowed through the breaker."""
        return self.state in (CircuitState.CLOSED, CircuitState.HALF_OPEN)

    def record_success(self) -> None:
        """Record a successful API response.

        Resets the failure counter. If in HALF_OPEN state, transitions to CLOSED
        (the API has recovered).
        """
        self._failure_count = 0
        self._success_count += 1
        if self._state == CircuitState.HALF_OPEN:
            self._state = CircuitState.CLOSED
            logger.info(
                "%s: circuit breaker recovered HALF_OPEN -> CLOSED "
                "(probe succeeded after %d successes total)",
                self.name,
                self._success_count,
            )

    def record_failure(self) -> None:
        """Record a failed API call (all retries exhausted).

        Increments the failure counter. If in HALF_OPEN state, immediately
        transitions back to OPEN. If failure count reaches threshold,
        transitions CLOSED -> OPEN.
        """
        self._failure_count += 1
        self._last_failure_time = self._clock()

        if self._state == CircuitState.HALF_OPEN:
            self._state = CircuitState.OPEN
            logger.warning(
                "%s: circuit breaker tripped HALF_OPEN -> OPEN "
                "(probe failed, resetting recovery timer)",
                self.name,
            )
        elif self._failure_count >= self.failure_threshold:
            self._state = CircuitState.OPEN
            logger.warning(
                "%s: circuit breaker tripped CLOSED -> OPEN "
                "(%d consecutive failures >= threshold %d)",
                self.name,
                self._failure_count,
                self.failure_threshold,
            )

    def reset(self) -> None:
        """Reset the breaker to CLOSED state with zero counters.

        Useful for testing, health checks, and manual recovery.
        """
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time = 0.0
        self._success_count = 0
        logger.info("%s: circuit breaker manually reset to CLOSED", self.name)
