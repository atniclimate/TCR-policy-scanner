"""Congress.gov API scraper.

Collects bills, resolutions, and committee reports related to Tribal climate
resilience from the Congress.gov API (requires free API key).

Integration strategy: filters for 119th Congress, searches for Tribal AND
(Resilience OR Climate OR Adaptation). Populates FundingVehicle nodes
(amounts, dates) and detects legislative actions.
"""

import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

from src.scrapers.base import BaseScraper

logger = logging.getLogger(__name__)

# Targeted legislative queries per the spec
LEGISLATIVE_QUERIES = [
    {"term": "tribal resilience", "type": "hr"},
    {"term": "tribal climate", "type": "hr"},
    {"term": "tribal adaptation", "type": "hr"},
    {"term": "indian tribe climate", "type": "hr"},
    {"term": "tribal resilience", "type": "s"},
    {"term": "tribal climate", "type": "s"},
    {"term": "tribal adaptation", "type": "s"},
    {"term": "tribal hazard mitigation", "type": "hr"},
    {"term": "tribal hazard mitigation", "type": "s"},
    {"term": "tribal energy", "type": "hr"},
    {"term": "tribal energy", "type": "s"},
]


class CongressGovScraper(BaseScraper):
    """Scrapes the Congress.gov API for legislative items."""

    def __init__(self, config: dict):
        super().__init__("congress_gov")
        src = config["sources"]["congress_gov"]
        self.base_url = src["base_url"]
        self.authority_weight = src["authority_weight"]
        self.api_key = os.environ.get(src.get("key_env_var", "CONGRESS_API_KEY"), "")
        self.search_queries = config.get("search_queries", [])
        self.scan_window = config.get("scan_window_days", 14)
        if self.api_key:
            self._headers["X-Api-Key"] = self.api_key

    async def scan(self) -> list[dict]:
        """Run targeted + broad queries against Congress.gov."""
        if not self.api_key:
            logger.warning("Congress.gov: CONGRESS_API_KEY not set, skipping")
            return []

        all_items = []
        seen_keys = set()

        async with self._create_session() as session:
            # Targeted 119th Congress queries by bill type
            for lq in LEGISLATIVE_QUERIES:
                try:
                    items = await self._search_congress(
                        session, lq["term"], bill_type=lq["type"], congress=119
                    )
                    for item in items:
                        key = item["source_id"]
                        if key not in seen_keys:
                            seen_keys.add(key)
                            all_items.append(item)
                except Exception:
                    logger.exception(
                        "Error searching Congress.gov for '%s' (%s)",
                        lq["term"], lq["type"],
                    )
                await asyncio.sleep(0.3)

            # Broad keyword queries
            for query in self.search_queries:
                try:
                    items = await self._search(session, query)
                    for item in items:
                        key = item["source_id"]
                        if key not in seen_keys:
                            seen_keys.add(key)
                            all_items.append(item)
                except Exception:
                    logger.exception("Error searching Congress.gov for '%s'", query)
                await asyncio.sleep(0.3)

        logger.info("Congress.gov: collected %d unique items", len(all_items))
        return all_items

    async def _search_congress(
        self, session, term: str,
        bill_type: str = "", congress: int = 119,
    ) -> list[dict]:
        """Search for bills in a specific Congress and bill type."""
        from_date = (datetime.now(timezone.utc) - timedelta(days=self.scan_window)).strftime("%Y-%m-%dT00:00:00Z")
        params = {
            "query": term,
            "fromDateTime": from_date,
            "sort": "updateDate+desc",
            "limit": 50,
        }

        # Congress-specific bill endpoint
        endpoint = f"{self.base_url}/bill/{congress}"
        if bill_type:
            endpoint = f"{endpoint}/{bill_type}"
        url = f"{endpoint}?{urlencode(params)}"

        data = await self._request_with_retry(session, "GET", url)
        bills = data.get("bills", [])
        return [self._normalize(bill) for bill in bills]

    async def _search(self, session, query: str) -> list[dict]:
        """Execute a broad search query against the bill endpoint."""
        from_date = (datetime.now(timezone.utc) - timedelta(days=self.scan_window)).strftime("%Y-%m-%dT00:00:00Z")
        params = {
            "query": query,
            "fromDateTime": from_date,
            "sort": "updateDate+desc",
            "limit": 50,
        }
        url = f"{self.base_url}/bill?{urlencode(params)}"

        data = await self._request_with_retry(session, "GET", url)
        bills = data.get("bills", [])
        return [self._normalize(bill) for bill in bills]

    def _normalize(self, item: dict) -> dict:
        """Map Congress.gov fields to the standard schema."""
        bill_type = item.get("type", "")
        bill_number = item.get("number", "")
        congress = item.get("congress", "")
        title = item.get("title", "")
        latest_action = item.get("latestAction", {})

        return {
            "source": "congress_gov",
            "source_id": f"{congress}-{bill_type}-{bill_number}",
            "title": title,
            "abstract": latest_action.get("text", ""),
            "url": item.get("url", f"https://www.congress.gov/bill/{congress}th-congress/{bill_type.lower()}/{bill_number}"),
            "pdf_url": "",
            "published_date": item.get("updateDate", ""),
            "document_type": f"{bill_type} {bill_number}",
            "congress": congress,
            "bill_type": bill_type,
            "bill_number": bill_number,
            "agencies": [],
            "latest_action": latest_action.get("text", ""),
            "latest_action_date": latest_action.get("actionDate", ""),
            "authority_weight": self.authority_weight,
        }
