"""Grants.gov API scraper.

Collects open and recently posted grant opportunities from the Grants.gov
REST API (no API key required).
"""

import asyncio
import logging
from datetime import datetime, timedelta

import aiohttp

logger = logging.getLogger(__name__)


class GrantsGovScraper:
    """Scrapes the Grants.gov API for grant opportunities."""

    def __init__(self, config: dict):
        self.base_url = config["sources"]["grants_gov"]["base_url"]
        self.authority_weight = config["sources"]["grants_gov"]["authority_weight"]
        self.search_queries = config.get("search_queries", [])
        self.scan_window = config.get("scan_window_days", 14)

    async def scan(self) -> list[dict]:
        """Run all search queries against Grants.gov."""
        all_items = []
        seen_ids = set()

        async with aiohttp.ClientSession() as session:
            for query in self.search_queries:
                try:
                    items = await self._search(session, query)
                    for item in items:
                        if item["source_id"] not in seen_ids:
                            seen_ids.add(item["source_id"])
                            all_items.append(item)
                except Exception:
                    logger.exception("Error searching Grants.gov for '%s'", query)
                await asyncio.sleep(0.5)

        logger.info("Grants.gov: collected %d unique items", len(all_items))
        return all_items

    async def _search(self, session: aiohttp.ClientSession, query: str) -> list[dict]:
        """Execute a single search query."""
        posted_from = (datetime.utcnow() - timedelta(days=self.scan_window)).strftime("%m/%d/%Y")
        payload = {
            "keyword": query,
            "oppStatuses": "forecasted|posted",
            "sortBy": "openDate|desc",
            "rows": 50,
            "postedFrom": posted_from,
        }
        url = f"{self.base_url}/opportunities/search"

        async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=30)) as resp:
            resp.raise_for_status()
            data = await resp.json()

        results = data.get("oppHits", [])
        return [self._normalize(item) for item in results]

    def _normalize(self, item: dict) -> dict:
        """Map Grants.gov fields to the standard schema."""
        return {
            "source": "grants_gov",
            "source_id": item.get("id", ""),
            "title": item.get("title", ""),
            "abstract": item.get("synopsis", "") or "",
            "url": f"https://www.grants.gov/search-results-detail/{item.get('id', '')}",
            "pdf_url": "",
            "published_date": item.get("openDate", ""),
            "close_date": item.get("closeDate", ""),
            "document_type": "grant_opportunity",
            "agencies": [item.get("agencyCode", "")],
            "award_ceiling": item.get("awardCeiling", ""),
            "award_floor": item.get("awardFloor", ""),
            "authority_weight": self.authority_weight,
        }
