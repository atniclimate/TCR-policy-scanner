"""USASpending.gov API scraper.

Tracks actual federal spending (obligations) for the 14 tracked programs,
closing the gap between authorization/appropriation and execution.

USASpending.gov provides a free, no-key REST API. This scraper queries
by CFDA/Assistance Listing number to get obligated amounts, populating
FundingVehicle nodes in the knowledge graph with real spending data.
"""

import asyncio
import logging

import aiohttp

from src.config import (
    FISCAL_YEAR_END,
    FISCAL_YEAR_INT,
    FISCAL_YEAR_SHORT,
    FISCAL_YEAR_START,
)
from src.scrapers.base import BaseScraper
from src.scrapers.cfda_map import CFDA_TO_PROGRAM

logger = logging.getLogger(__name__)

# Award type code GROUPS for Tribal award queries.
# USASpending API requires award_type_codes from a single group per request.
# Group 1 (grants): 02-05 = grants/cooperative agreements
# Group 2 (other_financial_assistance): 06 = direct payments (unrestricted),
#   10 = direct payments (specified use)
# Excludes loans (07/08), insurance (09), and other (11).
TRIBAL_AWARD_TYPE_CODE_GROUPS = [
    ["02", "03", "04", "05"],       # grants
    ["06", "10"],                    # other_financial_assistance (direct payments)
]

# Derived flat list for backward compatibility and external reference (MK-CODE-06)
TRIBAL_AWARD_TYPE_CODES = [code for group in TRIBAL_AWARD_TYPE_CODE_GROUPS for code in group]


class USASpendingScraper(BaseScraper):
    """Scrapes USASpending.gov for actual obligation data by CFDA."""

    def __init__(self, config: dict):
        super().__init__("usaspending", config=config)
        src = config["sources"].get("usaspending", {})
        self.base_url = src.get("base_url", "https://api.usaspending.gov/api/v2")
        self.authority_weight = src.get("authority_weight", 0.7)

    async def scan(self) -> list[dict]:
        """Query obligations for each tracked CFDA number."""
        all_items = []

        async with self._create_session() as session:
            for cfda, program_id in CFDA_TO_PROGRAM.items():
                try:
                    items = await self._fetch_obligations(session, cfda, program_id)
                    all_items.extend(items)
                except Exception:
                    logger.exception("Error fetching USASpending for CFDA %s", cfda)
                await asyncio.sleep(0.3)

        logger.info("USASpending: collected %d obligation records", len(all_items))
        return all_items

    # Pagination constants for obligation scan
    _OBLIGATION_LIMIT = 100   # Results per page for obligation queries
    _OBLIGATION_SAFETY_CAP = 5000  # Max results per CFDA (50 pages)
    _OBLIGATION_DELAY = 0.3   # seconds between page fetches

    async def _fetch_obligations(
        self, session: aiohttp.ClientSession, cfda: str, program_id: str,
    ) -> list[dict]:
        """Fetch spending by CFDA using the spending_by_award endpoint.

        Paginates through all results using page-based pagination.
        Safety cap at 5,000 results (50 pages) to prevent runaway queries.
        """
        url = f"{self.base_url}/search/spending_by_award/"
        all_results: list[dict] = []
        page = 1

        while True:
            payload = {
                "filters": {
                    "time_period": [{"start_date": FISCAL_YEAR_START, "end_date": FISCAL_YEAR_END}],
                    "award_type_codes": ["02", "03", "04", "05"],  # Grants
                    "program_numbers": [cfda],
                },
                "fields": [
                    "Award ID", "Recipient Name", "Award Amount",
                    "Awarding Agency", "Start Date",
                ],
                "subawards": False,
                "page": page,
                "limit": self._OBLIGATION_LIMIT,
                "sort": "Award Amount",
                "order": "desc",
            }

            try:
                data = await self._request_with_retry(session, "POST", url, json=payload)
            except Exception:
                logger.warning("USASpending: could not fetch CFDA %s page %d, skipping", cfda, page)
                break

            results = data.get("results", [])
            if not results:
                break

            all_results.extend(results)

            # Check for more pages
            page_meta = data.get("page_metadata", {})
            has_next = page_meta.get("hasNext", False)

            if not has_next:
                break

            # Safety cap check
            if len(all_results) >= self._OBLIGATION_SAFETY_CAP:
                logger.warning(
                    "USASpending: safety cap %d reached for CFDA %s obligations, "
                    "results may be truncated",
                    self._OBLIGATION_SAFETY_CAP, cfda,
                )
                break

            page += 1
            await asyncio.sleep(self._OBLIGATION_DELAY)

        logger.info(
            "USASpending: fetched %d obligation records for CFDA %s",
            len(all_results), cfda,
        )

        return [self._normalize(item, cfda, program_id) for item in all_results]

    async def fetch_tribal_awards_for_cfda(
        self, session: aiohttp.ClientSession, cfda: str,
    ) -> list[dict]:
        """Fetch ALL Tribal government awards for a given CFDA with full pagination.

        Queries USASpending spending_by_award endpoint filtered to
        indian_native_american_tribal_government recipients. Issues separate
        queries per award type group (grants vs. direct payments) since the
        API requires award_type_codes from a single group per request.

        Args:
            session: Active aiohttp session.
            cfda: CFDA/Assistance Listing number (e.g., "15.156").

        Returns:
            List of raw award result dicts from USASpending API.
        """
        url = f"{self.base_url}/search/spending_by_award/"
        all_results: list[dict] = []

        for type_group in TRIBAL_AWARD_TYPE_CODE_GROUPS:
            page = 1
            while True:
                payload = {
                    "filters": {
                        "award_type_codes": type_group,
                        "program_numbers": [cfda],
                        "recipient_type_names": [
                            "indian_native_american_tribal_government"
                        ],
                    },
                    "fields": [
                        "Award ID",
                        "Recipient Name",
                        "Award Amount",
                        "Total Obligation",
                        "Start Date",
                        "End Date",
                        "Description",
                        "CFDA Number",
                        "Awarding Agency",
                        "recipient_id",
                    ],
                    "subawards": False,
                    "page": page,
                    "limit": 100,
                    "sort": "Award Amount",
                    "order": "desc",
                }

                try:
                    data = await self._request_with_retry(
                        session, "POST", url, json=payload,
                    )
                except Exception:
                    logger.warning(
                        "USASpending: failed fetching Tribal awards for CFDA %s "
                        "page %d (types %s)",
                        cfda, page, type_group,
                    )
                    break

                results = data.get("results", [])
                if not results:
                    break

                all_results.extend(results)

                page_meta = data.get("page_metadata", {})
                if not page_meta.get("hasNext", False):
                    break

                page += 1

        logger.info(
            "USASpending: fetched %d Tribal awards for CFDA %s",
            len(all_results), cfda,
        )
        return all_results

    async def fetch_all_tribal_awards(self) -> dict[str, list[dict]]:
        """Fetch Tribal awards for all 14 tracked CFDAs.

        Iterates each CFDA in CFDA_TO_PROGRAM, calls
        fetch_tribal_awards_for_cfda for each, with rate limiting
        between requests. Catches exceptions per-CFDA so one failure
        does not abort the entire batch.

        Returns:
            Dict keyed by CFDA number -> list of raw award dicts.
        """
        awards_by_cfda: dict[str, list[dict]] = {}

        async with self._create_session() as session:
            for cfda in CFDA_TO_PROGRAM:
                try:
                    results = await self.fetch_tribal_awards_for_cfda(session, cfda)
                    awards_by_cfda[cfda] = results
                except Exception:
                    logger.exception(
                        "USASpending: error fetching Tribal awards for CFDA %s, "
                        "continuing with empty list",
                        cfda,
                    )
                    awards_by_cfda[cfda] = []
                await asyncio.sleep(0.5)

        total = sum(len(v) for v in awards_by_cfda.values())
        logger.info(
            "USASpending: fetched %d total Tribal awards across %d CFDAs",
            total, len(awards_by_cfda),
        )
        return awards_by_cfda

    async def fetch_tribal_awards_by_year(
        self, session: aiohttp.ClientSession, cfda: str, fy: int,
    ) -> list[dict]:
        """Fetch Tribal government awards for a single CFDA in a single fiscal year.

        Queries the USASpending spending_by_award endpoint filtered to
        indian_native_american_tribal_government recipients. Issues separate
        queries per award type group (grants vs. direct payments) since the
        API requires award_type_codes from a single group per request.

        Federal fiscal year N runs from October 1 of year N-1 through
        September 30 of year N.

        Args:
            session: Active aiohttp session.
            cfda: CFDA/Assistance Listing number (e.g., "15.156").
            fy: Fiscal year as 4-digit integer (e.g., 2024).

        Returns:
            List of raw award dicts, each with an injected ``_fiscal_year`` field.
        """
        url = f"{self.base_url}/search/spending_by_award/"
        start_date = f"{fy - 1}-10-01"
        end_date = f"{fy}-09-30"
        all_results: list[dict] = []

        for type_group in TRIBAL_AWARD_TYPE_CODE_GROUPS:
            page = 1
            while True:
                payload = {
                    "filters": {
                        "award_type_codes": type_group,
                        "program_numbers": [cfda],
                        "recipient_type_names": [
                            "indian_native_american_tribal_government"
                        ],
                        "time_period": [
                            {"start_date": start_date, "end_date": end_date}
                        ],
                    },
                    "fields": [
                        "Award ID",
                        "Recipient Name",
                        "Award Amount",
                        "Total Obligation",
                        "Start Date",
                        "End Date",
                        "Description",
                        "CFDA Number",
                        "Awarding Agency",
                        "recipient_id",
                    ],
                    "subawards": False,
                    "page": page,
                    "limit": 100,
                    "sort": "Award Amount",
                    "order": "desc",
                }

                try:
                    data = await self._request_with_retry(
                        session, "POST", url, json=payload,
                    )
                except Exception:
                    logger.warning(
                        "USASpending: failed fetching Tribal awards for CFDA %s "
                        "FY%d page %d (types %s)",
                        cfda, fy, page, type_group,
                    )
                    break

                results = data.get("results", [])
                if not results:
                    break

                all_results.extend(results)

                page_meta = data.get("page_metadata", {})
                if not page_meta.get("hasNext", False):
                    break

                page += 1

                # Safety: 100 pages * 100 results = 10K records per group
                if page > 100:
                    logger.warning(
                        "USASpending: CFDA %s FY%d reached page 100 (10K records) "
                        "for types %s. Results may be truncated.",
                        cfda, fy, type_group,
                    )
                    break

        # Inject fiscal year into each result for downstream processing
        for result in all_results:
            result["_fiscal_year"] = fy

        logger.info(
            "USASpending: fetched %d Tribal awards for CFDA %s FY%d",
            len(all_results), cfda, fy,
        )
        return all_results

    async def fetch_all_tribal_awards_multi_year(
        self, fy_start: int | None = None, fy_end: int | None = None,
    ) -> dict[str, list[dict]]:
        """Fetch Tribal awards for all CFDAs across a multi-year fiscal year range.

        Queries each (CFDA, fiscal year) pair sequentially with rate limiting
        to respect API limits. Catches exceptions per-(CFDA, FY) so one failure
        does not abort the entire batch.

        Single-writer-per-tribe_id assumption: this method is not designed for
        concurrent invocation with overlapping CFDA sets.

        Args:
            fy_start: First fiscal year (inclusive). Defaults to
                ``FISCAL_YEAR_INT - 4`` (5-year window).
            fy_end: Last fiscal year (inclusive). Defaults to
                ``FISCAL_YEAR_INT``.

        Returns:
            Dict keyed by CFDA number -> flat list of all awards across
            the requested fiscal years for that CFDA.
        """
        if fy_end is None:
            fy_end = FISCAL_YEAR_INT
        if fy_start is None:
            fy_start = FISCAL_YEAR_INT - 4

        awards_by_cfda: dict[str, list[dict]] = {
            cfda: [] for cfda in CFDA_TO_PROGRAM
        }
        query_count = 0

        async with self._create_session() as session:
            for cfda in CFDA_TO_PROGRAM:
                for fy in range(fy_start, fy_end + 1):
                    try:
                        results = await self.fetch_tribal_awards_by_year(
                            session, cfda, fy,
                        )
                        awards_by_cfda[cfda].extend(results)
                    except Exception:
                        logger.exception(
                            "USASpending: error fetching Tribal awards for "
                            "CFDA %s FY%d, continuing",
                            cfda, fy,
                        )
                    query_count += 1
                    await asyncio.sleep(0.5)

        total = sum(len(v) for v in awards_by_cfda.values())
        fy_count = fy_end - fy_start + 1
        logger.info(
            "USASpending: %d awards across %d CFDAs, %d fiscal years, %d queries",
            total, len(CFDA_TO_PROGRAM), fy_count, query_count,
        )
        return awards_by_cfda

    def _normalize(self, item: dict, cfda: str, program_id: str) -> dict:
        """Map USASpending fields to the standard schema."""
        raw_amount = item.get("Award Amount") or item.get("Total Obligation") or 0
        try:
            award_amount = float(raw_amount)
        except (ValueError, TypeError):
            award_amount = 0.0
        recipient = item.get("Recipient Name", "")

        return {
            "source": "usaspending",
            "source_id": f"usa_{cfda}_{item.get('internal_id', '')}",
            "title": f"{FISCAL_YEAR_SHORT} Obligation: {item.get('Award ID', cfda)} — {recipient}",
            "abstract": f"${award_amount:,.0f} obligated under CFDA {cfda} to {recipient}",
            "url": f"https://www.usaspending.gov/award/{item.get('internal_id', '')}",
            "pdf_url": "",
            "published_date": item.get("Start Date", ""),
            "document_type": "obligation",
            "agencies": [item.get("Awarding Agency", "")],
            "award_amount": award_amount,
            "cfda": cfda,
            "cfda_program_match": program_id,
            "recipient": recipient,
            "authority_weight": self.authority_weight,
        }
