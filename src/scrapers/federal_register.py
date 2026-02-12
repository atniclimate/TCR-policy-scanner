"""Federal Register API scraper.

Collects proposed rules, final rules, notices, and presidential documents
from the Federal Register API (no API key required).

Integration strategy: queries by agency ID + term to populate Authority
and Barrier nodes in the knowledge graph. Also detects Information
Collection Requests (ICR/PRA) as bureaucratic friction signals.
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

from src.scrapers.base import BaseScraper

logger = logging.getLogger(__name__)

# Federal Register document type codes
DOC_TYPES = ["RULE", "PRORULE", "NOTICE", "PRESDOCU"]

# Agency slugs for the Federal Register API (uses slugs, not numeric IDs)
# BIA, FEMA, EPA, DOE, HUD, DOT, USDA, Commerce, Treasury, Interior, Reclamation
AGENCY_SLUGS = [
    "indian-affairs-bureau",
    "federal-emergency-management-agency",
    "environmental-protection-agency",
    "energy-department",
    "housing-and-urban-development-department",
    "transportation-department",
    "agriculture-department",
    "commerce-department",
    "treasury-department",
    "interior-department",
    "reclamation-bureau",
]


class FederalRegisterScraper(BaseScraper):
    """Scrapes the Federal Register API for policy documents."""

    # Pagination constants
    _PER_PAGE = 50           # Federal Register default page size
    _MAX_PAGES = 20          # Safety cap: 20 pages = 1,000 results max
    _PAGE_DELAY = 0.3        # seconds between page fetches

    def __init__(self, config: dict):
        super().__init__("federal_register", config=config)
        self.base_url = config["sources"]["federal_register"]["base_url"]
        self.authority_weight = config["sources"]["federal_register"]["authority_weight"]
        self.search_queries = config.get("search_queries", [])
        self.scan_window = config.get("scan_window_days", 14)

    async def scan(self) -> list[dict]:
        """Run all search queries against the Federal Register API."""
        start_date = (datetime.now(timezone.utc) - timedelta(days=self.scan_window)).strftime("%Y-%m-%d")
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
        """Execute a single search query with full pagination.

        Loops through all pages returned by the Federal Register API.
        Safety cap at 20 pages (1,000 results) to prevent runaway queries.
        """
        all_items: list[dict] = []
        page = 1
        total_pages = None
        total_count = None

        while True:
            params = {
                "conditions[term]": query,
                "conditions[publication_date][gte]": start_date,
                "conditions[type][]": DOC_TYPES,
                "per_page": self._PER_PAGE,
                "page": page,
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
            all_items.extend(self._normalize(item) for item in results)

            # Extract pagination metadata from response
            if total_pages is None:
                total_pages = data.get("total_pages", 1)
                total_count = data.get("count", len(results))

            logger.info(
                "Federal Register: fetched %d/%d items (page %d/%d) for '%s'",
                len(all_items), total_count or len(all_items),
                page, total_pages or 1, query,
            )

            # Safety cap check
            if page >= self._MAX_PAGES:
                logger.warning(
                    "Federal Register: safety cap %d pages reached for '%s', "
                    "truncating %d -> %d",
                    self._MAX_PAGES, query,
                    total_count or len(all_items), len(all_items),
                )
                break

            # Check if more pages exist
            if page >= (total_pages or 1) or not results:
                break

            page += 1
            await asyncio.sleep(self._PAGE_DELAY)

        if total_count and len(all_items) < total_count and page < self._MAX_PAGES:
            logger.warning(
                "Federal Register: truncated %d -> %d for '%s'",
                total_count, len(all_items), query,
            )

        return all_items

    async def _search_by_agencies(self, session, start_date: str) -> list[dict]:
        """Sweep key agencies for any Rule/Notice mentioning Tribal terms.

        Paginates through all pages. Safety cap at 20 pages (1,000 results).
        """
        all_items: list[dict] = []
        page = 1
        total_pages = None
        total_count = None

        while True:
            params = {
                "conditions[term]": "tribal",
                "conditions[agencies][]": AGENCY_SLUGS,
                "conditions[publication_date][gte]": start_date,
                "conditions[type][]": ["RULE", "PRORULE", "NOTICE"],
                "per_page": self._PER_PAGE,
                "page": page,
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
            all_items.extend(self._normalize(item) for item in results)

            # Extract pagination metadata from response
            if total_pages is None:
                total_pages = data.get("total_pages", 1)
                total_count = data.get("count", len(results))

            logger.info(
                "Federal Register: fetched %d/%d agency-sweep items (page %d/%d)",
                len(all_items), total_count or len(all_items),
                page, total_pages or 1,
            )

            # Safety cap check
            if page >= self._MAX_PAGES:
                logger.warning(
                    "Federal Register: safety cap %d pages reached for agency sweep, "
                    "truncating %d -> %d",
                    self._MAX_PAGES,
                    total_count or len(all_items), len(all_items),
                )
                break

            # Check if more pages exist
            if page >= (total_pages or 1) or not results:
                break

            page += 1
            await asyncio.sleep(self._PAGE_DELAY)

        if total_count and len(all_items) < total_count and page < self._MAX_PAGES:
            logger.warning(
                "Federal Register: agency sweep truncated %d -> %d",
                total_count, len(all_items),
            )

        return all_items

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
