"""API health check for TCR Policy Scanner sources.

Probes each external API with a minimal request and reports
UP / DOWN / DEGRADED status per source. Used by the --health-check
CLI command for operator monitoring.
"""

import json
import logging
import os
import time

import aiohttp

from src.paths import OUTPUTS_DIR
from src.scrapers.base import USER_AGENT

logger = logging.getLogger(__name__)

# Probe timeout: quick check, not a full scan
_PROBE_TIMEOUT = aiohttp.ClientTimeout(total=10)


class HealthChecker:
    """Probe all 4 federal APIs and report UP/DOWN/DEGRADED status.

    Args:
        config: Scanner configuration dict (used for API key env var names).
    """

    PROBES = {
        "federal_register": {
            "url": "https://www.federalregister.gov/api/v1/documents.json?per_page=1",
            "method": "GET",
        },
        "grants_gov": {
            "url": "https://api.grants.gov/v1/api/search2",
            "method": "POST",
            "json": {"keyword": "test", "rows": 1},
        },
        "congress_gov": {
            "url": "https://api.congress.gov/v3/bill?limit=1",
            "method": "GET",
            "requires_key": True,
        },
        "usaspending": {
            "url": "https://api.usaspending.gov/api/v2/search/spending_by_award/",
            "method": "POST",
            "json": {"filters": {"award_type_codes": ["02"]}, "limit": 1},
        },
    }

    def __init__(self, config: dict):
        self._config = config

    async def check_all(self) -> dict[str, dict]:
        """Probe all sources and return status dict.

        Returns:
            Dict mapping source name to {"status", "latency_ms", "detail"}.
        """
        results = {}
        for source_name, probe in self.PROBES.items():
            results[source_name] = await self._probe_one(source_name, probe)
        return results

    async def _probe_one(self, source_name: str, probe: dict) -> dict:
        """Probe a single API endpoint.

        Returns:
            {"status": "UP"|"DOWN"|"DEGRADED", "latency_ms": int, "detail": str}
        """
        # Check API key requirement for congress_gov
        if probe.get("requires_key"):
            key_env = self._config.get("sources", {}).get(source_name, {}).get(
                "key_env_var", "CONGRESS_API_KEY"
            )
            api_key = os.environ.get(key_env, "")
            if not api_key:
                return self._check_degraded_or_down(
                    source_name, "API key not configured"
                )
        else:
            api_key = ""

        headers = {"User-Agent": USER_AGENT}
        start = time.monotonic()

        try:
            async with aiohttp.ClientSession(headers=headers, timeout=_PROBE_TIMEOUT) as session:
                method = probe["method"].upper()
                url = probe["url"]
                kwargs: dict = {}

                if probe.get("json"):
                    kwargs["json"] = probe["json"]

                if api_key:
                    # Add API key as query parameter
                    separator = "&" if "?" in url else "?"
                    url = f"{url}{separator}api_key={api_key}"

                if method == "GET":
                    async with session.get(url, **kwargs) as resp:
                        latency_ms = int((time.monotonic() - start) * 1000)
                        if 200 <= resp.status < 300:
                            return {"status": "UP", "latency_ms": latency_ms, "detail": "OK"}
                        return self._check_degraded_or_down(
                            source_name, f"HTTP {resp.status}"
                        )
                elif method == "POST":
                    async with session.post(url, **kwargs) as resp:
                        latency_ms = int((time.monotonic() - start) * 1000)
                        if 200 <= resp.status < 300:
                            return {"status": "UP", "latency_ms": latency_ms, "detail": "OK"}
                        return self._check_degraded_or_down(
                            source_name, f"HTTP {resp.status}"
                        )
                else:
                    return {"status": "DOWN", "latency_ms": 0, "detail": f"Unsupported method: {method}"}

        except (aiohttp.ClientError, TimeoutError, OSError) as e:
            return self._check_degraded_or_down(source_name, str(e))

    def _check_degraded_or_down(self, source_name: str, error_detail: str) -> dict:
        """Check if cached data exists; return DEGRADED if so, DOWN otherwise."""
        cache_path = OUTPUTS_DIR / f".cache_{source_name}.json"
        if cache_path.exists():
            try:
                with open(cache_path, encoding="utf-8") as f:
                    data = json.load(f)
                cached_at = data.get("cached_at", "unknown")
                return {
                    "status": "DEGRADED",
                    "latency_ms": 0,
                    "detail": f"cached data from {cached_at}",
                }
            except (json.JSONDecodeError, IOError):
                pass
        return {"status": "DOWN", "latency_ms": 0, "detail": error_detail}


def format_report(results: dict[str, dict]) -> str:
    """Format health check results as an aligned text table.

    Args:
        results: Dict from HealthChecker.check_all().

    Returns:
        Formatted multi-line string ready for console output.
    """
    lines = [
        "API Health Check",
        "-" * 60,
    ]
    # Find max source name length for alignment
    max_name = max(len(name) for name in results) if results else 0
    for source_name, info in results.items():
        status = info["status"]
        if status == "UP":
            detail = f"({info['latency_ms']}ms)"
        else:
            detail = f"({info['detail']})"
        lines.append(f"  {source_name + ':':<{max_name + 2}} {status:<10} {detail}")
    return "\n".join(lines)
