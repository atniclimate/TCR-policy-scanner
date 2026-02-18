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
        super().__init__("congress_gov", config=config)
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

    # Pagination constants
    _PAGE_LIMIT = 250        # Congress.gov API max per page
    _SAFETY_CAP = 2500       # 10 pages max per query
    _PAGE_DELAY = 0.3        # seconds between page fetches

    async def _search_congress(
        self, session, term: str,
        bill_type: str = "", congress: int = 119,
    ) -> list[dict]:
        """Search for bills in a specific Congress and bill type.

        Paginates through all available results using offset-based pagination.
        Safety cap at 2,500 results (10 pages) to prevent runaway queries.
        """
        from_date = (datetime.now(timezone.utc) - timedelta(days=self.scan_window)).strftime("%Y-%m-%dT00:00:00Z")

        # Congress-specific bill endpoint
        endpoint = f"{self.base_url}/bill/{congress}"
        if bill_type:
            endpoint = f"{endpoint}/{bill_type}"

        all_bills: list[dict] = []
        offset = 0
        total_count = None

        while True:
            params = {
                "query": term,
                "fromDateTime": from_date,
                "sort": "updateDate+desc",
                "limit": self._PAGE_LIMIT,
                "offset": offset,
            }
            url = f"{endpoint}?{urlencode(params)}"

            data = await self._request_with_retry(session, "GET", url)
            bills = data.get("bills", [])

            # Extract total count from pagination metadata
            pagination = data.get("pagination", {})
            if total_count is None:
                total_count = pagination.get("count", len(bills))

            all_bills.extend(bills)

            # Safety cap check
            if len(all_bills) >= self._SAFETY_CAP:
                logger.warning(
                    "Congress.gov: safety cap %d reached for '%s' (%s), "
                    "truncating %d -> %d",
                    self._SAFETY_CAP, term, bill_type,
                    total_count or len(all_bills), len(all_bills),
                )
                break

            # Check if more pages exist
            if not pagination.get("next") or len(bills) < self._PAGE_LIMIT:
                break

            offset += self._PAGE_LIMIT
            await asyncio.sleep(self._PAGE_DELAY)

        if total_count is None:
            total_count = len(all_bills)

        logger.info(
            "Congress.gov: fetched %d/%d bills for '%s' (%s)",
            len(all_bills), total_count, term, bill_type or "all",
        )
        if len(all_bills) < total_count and len(all_bills) < self._SAFETY_CAP:
            logger.warning(
                "Congress.gov: truncated %d -> %d for '%s'",
                total_count, len(all_bills), term,
            )

        return [self._normalize(bill) for bill in all_bills]

    async def _search(self, session, query: str) -> list[dict]:
        """Execute a broad search query against the bill endpoint.

        Paginates through all available results using offset-based pagination.
        Safety cap at 2,500 results (10 pages) to prevent runaway queries.
        """
        from_date = (datetime.now(timezone.utc) - timedelta(days=self.scan_window)).strftime("%Y-%m-%dT00:00:00Z")

        all_bills: list[dict] = []
        offset = 0
        total_count = None

        while True:
            params = {
                "query": query,
                "fromDateTime": from_date,
                "sort": "updateDate+desc",
                "limit": self._PAGE_LIMIT,
                "offset": offset,
            }
            url = f"{self.base_url}/bill?{urlencode(params)}"

            data = await self._request_with_retry(session, "GET", url)
            bills = data.get("bills", [])

            # Extract total count from pagination metadata
            pagination = data.get("pagination", {})
            if total_count is None:
                total_count = pagination.get("count", len(bills))

            all_bills.extend(bills)

            # Safety cap check
            if len(all_bills) >= self._SAFETY_CAP:
                logger.warning(
                    "Congress.gov: safety cap %d reached for '%s', "
                    "truncating %d -> %d",
                    self._SAFETY_CAP, query,
                    total_count or len(all_bills), len(all_bills),
                )
                break

            # Check if more pages exist
            if not pagination.get("next") or len(bills) < self._PAGE_LIMIT:
                break

            offset += self._PAGE_LIMIT
            await asyncio.sleep(self._PAGE_DELAY)

        if total_count is None:
            total_count = len(all_bills)

        logger.info(
            "Congress.gov: fetched %d/%d bills for '%s'",
            len(all_bills), total_count, query,
        )
        if len(all_bills) < total_count and len(all_bills) < self._SAFETY_CAP:
            logger.warning(
                "Congress.gov: truncated %d -> %d for '%s'",
                total_count, len(all_bills), query,
            )

        return [self._normalize(bill) for bill in all_bills]

    async def _fetch_bill_detail(
        self, session, congress: int, bill_type: str, bill_number: str,
    ) -> dict:
        """Fetch full bill detail including sponsors, actions, cosponsors, subjects, text.

        Queries 4 sub-endpoints of the Congress.gov API v3 for a specific bill:
        /actions, /cosponsors, /subjects, /text. The main bill record includes
        sponsor info inline.

        Args:
            session: aiohttp ClientSession.
            congress: Congress number (e.g., 119).
            bill_type: Bill type code (hr, s, etc.) -- lowercase for URL.
            bill_number: Bill number as string.

        Returns:
            Dict with keys: bill, actions, cosponsors, subjects, policy_area, text_versions.
        """
        if not str(bill_number).isdigit():
            raise ValueError(f"Invalid bill_number: {bill_number!r} (must be numeric)")
        base = f"{self.base_url}/bill/{congress}/{bill_type.lower()}/{bill_number}"

        # Main bill detail (includes sponsor inline)
        detail = await self._request_with_retry(session, "GET", base)
        bill = detail.get("bill", {})

        # Sub-endpoint fetches with individual error handling
        actions = []
        cosponsors = []
        subjects = []
        policy_area = {}
        text_versions = []

        try:
            actions_data = await self._request_with_retry(
                session, "GET", f"{base}/actions?limit=250"
            )
            actions = actions_data.get("actions", [])
        except Exception:
            logger.warning(
                "Failed to fetch actions for %s-%s-%s",
                congress, bill_type, bill_number,
            )

        await asyncio.sleep(0.3)

        try:
            cosponsors_data = await self._request_with_retry(
                session, "GET", f"{base}/cosponsors?limit=250"
            )
            cosponsors = cosponsors_data.get("cosponsors", [])
        except Exception:
            logger.warning(
                "Failed to fetch cosponsors for %s-%s-%s",
                congress, bill_type, bill_number,
            )

        await asyncio.sleep(0.3)

        try:
            subjects_data = await self._request_with_retry(
                session, "GET", f"{base}/subjects?limit=250"
            )
            subj = subjects_data.get("subjects", {})
            subjects = subj.get("legislativeSubjects", [])
            policy_area = subj.get("policyArea", {})
        except Exception:
            logger.warning(
                "Failed to fetch subjects for %s-%s-%s",
                congress, bill_type, bill_number,
            )

        await asyncio.sleep(0.3)

        try:
            text_data = await self._request_with_retry(
                session, "GET", f"{base}/text?limit=20"
            )
            text_versions = text_data.get("textVersions", [])
        except Exception:
            logger.warning(
                "Failed to fetch text for %s-%s-%s",
                congress, bill_type, bill_number,
            )

        return {
            "bill": bill,
            "actions": actions,
            "cosponsors": cosponsors,
            "subjects": subjects,
            "policy_area": policy_area,
            "text_versions": text_versions,
        }

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
