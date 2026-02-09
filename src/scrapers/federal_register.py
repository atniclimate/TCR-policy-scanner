"""Federal Register API scraper.

Collects proposed rules, final rules, notices, and presidential documents
from the Federal Register API (no API key required).

Integration strategy: queries by agency ID + term to populate Authority
and Barrier nodes in the knowledge graph. Also detects Information
Collection Requests (ICR/PRA) as bureaucratic friction signals.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from urllib.parse import urlencode

from src.scrapers.base import BaseScraper

logger = logging.getLogger(__name__)

# Federal Register document type codes
DOC_TYPES = ["RULE", "PRORULE", "NOTICE", "PRESDOCU"]

# Agency IDs per the spec: BIA=438, FEMA=492, EPA=466, DOE=183, HUD=227,
# DOT=228, USDA=12, Commerce=54, Treasury=497, Interior=253, Reclamation=436
AGENCY_IDS = [438, 492, 466, 183, 227, 228, 12, 54, 497, 253, 436]


class FederalRegisterScraper(BaseScraper):
    """Scrapes the Federal Register API for policy documents."""

    def __init__(self, config: dict):
        super().__init__("federal_register")
        self.base_url = config["sources"]["federal_register"]["base_url"]
        self.authority_weight = config["sources"]["federal_register"]["authority_weight"]
        self.search_queries = config.get("search_queries", [])
        self.scan_window = config.get("scan_window_days", 14)

    async def scan(self) -> list[dict]:
        """Run all search queries against the Federal Register API."""
        start_date = (datetime.utcnow() - timedelta(days=self.scan_window)).strftime("%m/%d/%Y")
        all_items = []
        seen_urls = set()

        async with self._create_session() as session:
            # Term-based queries
            for query in self.search_queries:
                try:
                    items = await self._search(session, query, start_date)
                    for item in items:
                        if item["url"] not in seen_urls:
                            seen_urls.add(item["url"])
                            all_items.append(item)
                except Exception:
                    logger.exception("Error searching Federal Register for '%s'", query)
                await asyncio.sleep(0.5)

            # Agency-specific sweep for Tribal-relevant agencies
            try:
                items = await self._search_by_agencies(session, start_date)
                for item in items:
                    if item["url"] not in seen_urls:
                        seen_urls.add(item["url"])
                        all_items.append(item)
            except Exception:
                logger.exception("Error in agency-sweep search")

        logger.info("Federal Register: collected %d unique items", len(all_items))
        return all_items

    async def _search(self, session, query: str, start_date: str) -> list[dict]:
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
                "action", "dates", "cfr_references", "regulation_id_numbers",
            ],
        }
        url = f"{self.base_url}/documents.json?{urlencode(params, doseq=True)}"
        data = await self._request_with_retry(session, "GET", url)
        results = data.get("results", [])
        return [self._normalize(item) for item in results]

    async def _search_by_agencies(self, session, start_date: str) -> list[dict]:
        """Sweep key agencies for any Rule/Notice mentioning Tribal terms."""
        params = {
            "conditions[term]": "tribal",
            "conditions[agencies][]": AGENCY_IDS,
            "conditions[publication_date][gte]": start_date,
            "conditions[type][]": ["RULE", "PRORULE", "NOTICE"],
            "per_page": 50,
            "order": "newest",
            "fields[]": [
                "title", "abstract", "document_number", "type",
                "publication_date", "agencies", "html_url", "pdf_url",
                "action", "dates", "cfr_references", "regulation_id_numbers",
            ],
        }
        url = f"{self.base_url}/documents.json?{urlencode(params, doseq=True)}"
        data = await self._request_with_retry(session, "GET", url)
        results = data.get("results", [])
        return [self._normalize(item) for item in results]

    def _normalize(self, item: dict) -> dict:
        """Map Federal Register fields to the standard schema."""
        agencies = item.get("agencies", [])
        agency_names = [a.get("name", "") for a in agencies if isinstance(a, dict)]
        agency_ids = [a.get("id", 0) for a in agencies if isinstance(a, dict)]

        # Extract CFR references for graph Authority linking
        cfr_refs = item.get("cfr_references", []) or []
        cfr_citations = []
        for ref in cfr_refs:
            if isinstance(ref, dict):
                title = ref.get("title", "")
                part = ref.get("part", "")
                if title and part:
                    cfr_citations.append(f"{title} CFR {part}")

        # Detect document subtype for enhanced classification
        action = item.get("action", "") or ""
        doc_subtype = ""
        action_lower = action.lower()
        if "information collection" in action_lower or "paperwork reduction" in action_lower:
            doc_subtype = "icr"
        elif "guidance" in action_lower or "memorandum" in action_lower or "policy statement" in action_lower:
            doc_subtype = "guidance"
        elif "request for information" in action_lower:
            doc_subtype = "rfi"
        elif "advance notice" in action_lower:
            doc_subtype = "anprm"

        return {
            "source": "federal_register",
            "source_id": item.get("document_number", ""),
            "title": item.get("title", ""),
            "abstract": item.get("abstract", "") or "",
            "url": item.get("html_url", ""),
            "pdf_url": item.get("pdf_url", ""),
            "published_date": item.get("publication_date", ""),
            "document_type": item.get("type", ""),
            "document_subtype": doc_subtype,
            "agencies": agency_names,
            "agency_ids": agency_ids,
            "action": action,
            "dates": item.get("dates", ""),
            "cfr_references": cfr_citations,
            "regulation_ids": item.get("regulation_id_numbers", []) or [],
            "authority_weight": self.authority_weight,
        }
