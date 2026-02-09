"""Federal Register API scraper.

Collects proposed rules, final rules, notices, and presidential documents
from the Federal Register API (no API key required).
"""

import asyncio
import logging
from datetime import datetime, timedelta
from urllib.parse import urlencode

import aiohttp

logger = logging.getLogger(__name__)

# Federal Register document type codes
DOC_TYPES = ["RULE", "PRORULE", "NOTICE", "PRESDOCU"]


class FederalRegisterScraper:
    """Scrapes the Federal Register API for policy documents."""

    def __init__(self, config: dict):
        self.base_url = config["sources"]["federal_register"]["base_url"]
        self.authority_weight = config["sources"]["federal_register"]["authority_weight"]
        self.search_queries = config.get("search_queries", [])
        self.scan_window = config.get("scan_window_days", 14)

    async def scan(self) -> list[dict]:
        """Run all search queries against the Federal Register API."""
        start_date = (datetime.utcnow() - timedelta(days=self.scan_window)).strftime("%m/%d/%Y")
        all_items = []
        seen_urls = set()

        async with aiohttp.ClientSession() as session:
            for query in self.search_queries:
                try:
                    items = await self._search(session, query, start_date)
                    for item in items:
                        if item["url"] not in seen_urls:
                            seen_urls.add(item["url"])
                            all_items.append(item)
                except Exception:
                    logger.exception("Error searching Federal Register for '%s'", query)
                await asyncio.sleep(0.5)  # rate-limit courtesy

        logger.info("Federal Register: collected %d unique items", len(all_items))
        return all_items

    async def _search(self, session: aiohttp.ClientSession, query: str, start_date: str) -> list[dict]:
        """Execute a single search query."""
        params = {
            "conditions[term]": query,
            "conditions[publication_date][gte]": start_date,
            "conditions[type][]": DOC_TYPES,
            "per_page": 50,
            "order": "newest",
            "fields[]": [
                "title", "abstract", "document_number", "type",
                "publication_date", "agencies", "html_url", "pdf_url",
                "action", "dates",
            ],
        }
        url = f"{self.base_url}/documents.json?{urlencode(params, doseq=True)}"

        async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as resp:
            resp.raise_for_status()
            data = await resp.json()

        results = data.get("results", [])
        return [self._normalize(item) for item in results]

    def _normalize(self, item: dict) -> dict:
        """Map Federal Register fields to the standard schema."""
        agencies = item.get("agencies", [])
        agency_names = [a.get("name", "") for a in agencies if isinstance(a, dict)]

        return {
            "source": "federal_register",
            "source_id": item.get("document_number", ""),
            "title": item.get("title", ""),
            "abstract": item.get("abstract", "") or "",
            "url": item.get("html_url", ""),
            "pdf_url": item.get("pdf_url", ""),
            "published_date": item.get("publication_date", ""),
            "document_type": item.get("type", ""),
            "agencies": agency_names,
            "action": item.get("action", ""),
            "dates": item.get("dates", ""),
            "authority_weight": self.authority_weight,
        }
