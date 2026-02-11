"""Base scraper with shared resilience patterns.

All scrapers inherit from this class to get:
- Configurable User-Agent header for federal API compliance
- Exponential backoff with retry on transient failures
- Circuit breaker: fail fast when an API is down (RESL-01)
- Config-driven retry/backoff parameters (RESL-02)
- Graceful degradation: returns cached data on full failure
- Zombie CFDA detection: flags programs returning 0 results for >30 days
"""

import asyncio
import logging
import random
from datetime import datetime, timezone

import aiohttp

from src.scrapers.circuit_breaker import CircuitBreaker, CircuitOpenError  # noqa: F401


logger = logging.getLogger(__name__)

USER_AGENT = "TCR-Policy-Scanner/1.0 (Tribal Climate Resilience; automated-scan)"
DEFAULT_TIMEOUT = aiohttp.ClientTimeout(total=30)
MAX_RETRIES = 3
BACKOFF_BASE = 2  # seconds


class BaseScraper:
    """Shared resilience patterns for all scrapers.

    Args:
        source_name: Identifier for this scraper source (e.g., "federal_register").
        config: Optional scanner_config dict. If provided, reads the "resilience"
                section for retry/backoff/circuit-breaker parameters. If omitted
                or missing "resilience" key, uses module-level defaults for full
                backward compatibility.
    """

    def __init__(self, source_name: str, config: dict | None = None):
        self.source_name = source_name
        self._headers = {"User-Agent": USER_AGENT}

        # Read resilience config (or use hardcoded defaults)
        resilience = (config or {}).get("resilience", {})
        self.max_retries = resilience.get("max_retries", MAX_RETRIES)
        self.backoff_base = resilience.get("backoff_base", BACKOFF_BASE)
        self.backoff_max = resilience.get("backoff_max", 300)
        self.request_timeout = aiohttp.ClientTimeout(
            total=resilience.get("request_timeout", 30)
        )

        # Per-source circuit breaker
        cb_config = resilience.get("circuit_breaker", {})
        self._circuit_breaker = CircuitBreaker(
            name=source_name,
            failure_threshold=cb_config.get("failure_threshold", 5),
            recovery_timeout=cb_config.get("recovery_timeout", 60),
        )

    def _create_session(self) -> aiohttp.ClientSession:
        """Create an aiohttp session with proper User-Agent."""
        return aiohttp.ClientSession(headers=self._headers)

    async def _request_with_retry(
        self, session: aiohttp.ClientSession, method: str, url: str,
        retries: int | None = None, **kwargs,
    ) -> dict:
        """Make an HTTP request with exponential backoff on transient failures.

        The circuit breaker wraps the entire retry loop: it checks once at entry
        and records success/failure based on the final outcome. Retries happen
        inside CLOSED state; the breaker trips when ALL retries are exhausted.
        """
        if retries is None:
            retries = self.max_retries

        # Circuit breaker gate: fail fast if API is known to be down
        if not self._circuit_breaker.is_call_permitted:
            raise CircuitOpenError(self.source_name)

        kwargs.setdefault("timeout", self.request_timeout)
        last_error = None
        method_lower = method.lower()
        if not hasattr(session, method_lower):
            raise ValueError(f"Unsupported HTTP method: {method}")
        request_fn = getattr(session, method_lower)

        attempt = 0
        rate_limit_hits = 0
        while attempt < retries:
            try:
                async with request_fn(url, **kwargs) as resp:
                    if resp.status == 429:
                        rate_limit_hits += 1
                        if rate_limit_hits > retries:
                            logger.error(
                                "%s: too many 429 responses (%d), giving up",
                                self.source_name, rate_limit_hits,
                            )
                            raise aiohttp.ClientResponseError(
                                resp.request_info, resp.history, status=429,
                            )
                        raw_retry = resp.headers.get("Retry-After", "")
                        try:
                            retry_after = max(0, min(int(raw_retry), self.backoff_max))
                        except (ValueError, TypeError):
                            retry_after = min(
                                self.backoff_base ** (attempt + 2), self.backoff_max
                            )
                        logger.warning(
                            "%s: 429 rate limited, waiting %ds",
                            self.source_name, retry_after,
                        )
                        await asyncio.sleep(retry_after)
                        continue  # Do NOT increment attempt for server-requested delay
                    elif resp.status == 403:
                        logger.warning(
                            "%s: 403 Forbidden, attempt %d/%d",
                            self.source_name, attempt + 1, retries,
                        )
                        last_error = aiohttp.ClientResponseError(
                            resp.request_info, resp.history, status=403,
                        )
                    else:
                        resp.raise_for_status()
                        result = await resp.json()
                        self._circuit_breaker.record_success()
                        return result
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                last_error = e
                logger.warning(
                    "%s: request failed (attempt %d/%d): %s",
                    self.source_name, attempt + 1, retries, e,
                )

            attempt += 1
            backoff = self.backoff_base ** attempt + random.uniform(0, 1)
            logger.info("%s: retrying in %.1fs...", self.source_name, backoff)
            await asyncio.sleep(backoff)

        # All retries exhausted -- record failure for circuit breaker
        self._circuit_breaker.record_failure()
        logger.error(
            "%s: all %d retries exhausted, last error: %s",
            self.source_name, retries, last_error,
        )
        raise last_error or RuntimeError(f"{self.source_name}: request failed after {retries} retries")


# ── Zombie CFDA Detection ──


def check_zombie_cfda(cfda: str, result_count: int, tracker: dict) -> dict | None:
    """Track CFDA query results over time. Returns a warning dict if zombie detected.

    A "zombie CFDA" is one that returns 0 results for >30 consecutive days,
    suggesting the Assistance Listing Number has been archived, migrated, or
    the program has been terminated without the inventory being updated.
    """
    now = datetime.now(timezone.utc).isoformat()
    entry = tracker.get(cfda, {})

    if result_count > 0:
        # Reset: this CFDA is alive
        tracker[cfda] = {"last_results": now, "zero_since": None}
        return None

    # Zero results
    if not entry.get("zero_since"):
        tracker[cfda] = {"last_results": entry.get("last_results", ""), "zero_since": now}
        return None

    # Check how long it's been zero
    try:
        zero_since = datetime.fromisoformat(entry["zero_since"])
        days_zero = (datetime.now(timezone.utc) - zero_since).days
        if days_zero >= 30:
            return {
                "cfda": cfda,
                "days_zero": days_zero,
                "zero_since": entry["zero_since"],
                "warning": f"CFDA {cfda} has returned 0 results for {days_zero} days. "
                           f"Check SAM.gov for ALN archival or migration.",
            }
    except (ValueError, TypeError) as e:
        logger.warning("check_zombie_cfda: failed to parse zero_since for %s: %s", cfda, e)

    return None
