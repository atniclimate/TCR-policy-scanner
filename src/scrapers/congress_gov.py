"""Congress.gov API scraper.

Collects bills, resolutions, and committee reports related to Tribal climate
resilience from the Congress.gov API (requires free API key).
"""

import asyncio
import logging
import os
from datetime import datetime, timedelta
from urllib.parse import urlencode

import aiohttp

logger = logging.getLogger(__name__)


class CongressGovScraper:
    """Scrapes the Congress.gov API for legislative items."""

    def __init__(self, config: dict):
        src = config["sources"]["congress_gov"]
        self.base_url = src["base_url"]
        self.authority_weight = src["authority_weight"]
        self.api_key = os.environ.get(src.get("key_env_var", "CONGRESS_API_KEY"), "")
        self.search_queries = config.get("search_queries", [])
        self.scan_window = config.get("scan_window_days", 14)

    async def scan(self) -> list[dict]:
        """Run all search queries against Congress.gov."""
        if not self.api_key:
            logger.warning("Congress.gov: CONGRESS_API_KEY not set, skipping")
            return []

        all_items = []
        seen_urls = set()

        async with aiohttp.ClientSession() as session:
            for query in self.search_queries:
                try:
                    items = await self._search(session, query)
                    for item in items:
                        if item["url"] not in seen_urls:
                            seen_urls.add(item["url"])
                            all_items.append(item)
                except Exception:
                    logger.exception("Error searching Congress.gov for '%s'", query)
                await asyncio.sleep(0.5)

        logger.info("Congress.gov: collected %d unique items", len(all_items))
        return all_items

    async def _search(self, session: aiohttp.ClientSession, query: str) -> list[dict]:
        """Execute a single search query against the bill endpoint."""
        from_date = (datetime.utcnow() - timedelta(days=self.scan_window)).strftime("%Y-%m-%dT00:00:00Z")
        params = {
            "query": query,
            "fromDateTime": from_date,
            "sort": "updateDate+desc",
            "limit": 50,
            "api_key": self.api_key,
        }
        url = f"{self.base_url}/bill?{urlencode(params)}"

        async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as resp:
            resp.raise_for_status()
            data = await resp.json()

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
            "agencies": [],
            "latest_action": latest_action.get("text", ""),
            "latest_action_date": latest_action.get("actionDate", ""),
            "authority_weight": self.authority_weight,
        }
