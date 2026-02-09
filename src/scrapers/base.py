"""Base scraper with shared resilience patterns.

All scrapers inherit from this class to get:
- Configurable User-Agent header for federal API compliance
- Exponential backoff with retry on transient failures
- Graceful degradation: returns cached data on full failure
- Zombie CFDA detection: flags programs returning 0 results for >30 days
"""

import asyncio
import logging
from datetime import datetime, timedelta
from pathlib import Path

import aiohttp

logger = logging.getLogger(__name__)

USER_AGENT = "TCR-Policy-Scanner/1.0 (Tribal Climate Resilience; automated-scan)"
DEFAULT_TIMEOUT = aiohttp.ClientTimeout(total=30)
MAX_RETRIES = 3
BACKOFF_BASE = 2  # seconds


class BaseScraper:
    """Shared resilience patterns for all scrapers."""

    def __init__(self, source_name: str):
        self.source_name = source_name
        self._headers = {"User-Agent": USER_AGENT}

    def _create_session(self) -> aiohttp.ClientSession:
        """Create an aiohttp session with proper User-Agent."""
        return aiohttp.ClientSession(headers=self._headers)

    async def _request_with_retry(
        self, session: aiohttp.ClientSession, method: str, url: str,
        retries: int = MAX_RETRIES, **kwargs,
    ) -> dict:
        """Make an HTTP request with exponential backoff on transient failures.

        Returns parsed JSON on success, raises on exhausted retries.
        Handles 403 (IP block), 429 (rate limit), 5xx (server errors) gracefully.
        """
        kwargs.setdefault("timeout", DEFAULT_TIMEOUT)
        last_error = None

        for attempt in range(retries):
            try:
                if method == "GET":
                    async with session.get(url, **kwargs) as resp:
                        if resp.status == 403:
                            logger.warning(
                                "%s: 403 Forbidden (possible IP block), attempt %d/%d",
                                self.source_name, attempt + 1, retries,
                            )
                            last_error = aiohttp.ClientResponseError(
                                resp.request_info, resp.history, status=403,
                            )
                        elif resp.status == 429:
                            retry_after = int(resp.headers.get("Retry-After", BACKOFF_BASE ** (attempt + 2)))
                            logger.warning(
                                "%s: 429 rate limited, waiting %ds",
                                self.source_name, retry_after,
                            )
                            await asyncio.sleep(retry_after)
                            continue
                        else:
                            resp.raise_for_status()
                            return await resp.json()
                elif method == "POST":
                    async with session.post(url, **kwargs) as resp:
                        if resp.status == 403:
                            logger.warning(
                                "%s: 403 Forbidden, attempt %d/%d",
                                self.source_name, attempt + 1, retries,
                            )
                            last_error = aiohttp.ClientResponseError(
                                resp.request_info, resp.history, status=403,
                            )
                        elif resp.status == 429:
                            retry_after = int(resp.headers.get("Retry-After", BACKOFF_BASE ** (attempt + 2)))
                            logger.warning(
                                "%s: 429 rate limited, waiting %ds",
                                self.source_name, retry_after,
                            )
                            await asyncio.sleep(retry_after)
                            continue
                        else:
                            resp.raise_for_status()
                            return await resp.json()
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                last_error = e
                logger.warning(
                    "%s: request failed (attempt %d/%d): %s",
                    self.source_name, attempt + 1, retries, e,
                )

            backoff = BACKOFF_BASE ** (attempt + 1)
            logger.info("%s: retrying in %ds...", self.source_name, backoff)
            await asyncio.sleep(backoff)

        # All retries exhausted
        logger.error(
            "%s: all %d retries exhausted, last error: %s",
            self.source_name, retries, last_error,
        )
        raise last_error or RuntimeError(f"{self.source_name}: request failed after {retries} retries")


# ── Zombie CFDA Detection ──

CFDA_TRACKER_PATH = Path("outputs/.cfda_tracker.json")


def check_zombie_cfda(cfda: str, result_count: int, tracker: dict) -> dict | None:
    """Track CFDA query results over time. Returns a warning dict if zombie detected.

    A "zombie CFDA" is one that returns 0 results for >30 consecutive days,
    suggesting the Assistance Listing Number has been archived, migrated, or
    the program has been terminated without the inventory being updated.
    """
    now = datetime.utcnow().isoformat()
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
        days_zero = (datetime.utcnow() - zero_since).days
        if days_zero >= 30:
            return {
                "cfda": cfda,
                "days_zero": days_zero,
                "zero_since": entry["zero_since"],
                "warning": f"CFDA {cfda} has returned 0 results for {days_zero} days. "
                           f"Check SAM.gov for ALN archival or migration.",
            }
    except (ValueError, TypeError):
        pass

    return None
