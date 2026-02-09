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

from src.scrapers.base import BaseScraper

logger = logging.getLogger(__name__)

# Map CFDA numbers to program IDs (shared with grants_gov.py)
CFDA_TO_PROGRAM = {
    "15.156": "bia_tcr",
    "97.047": "fema_bric",
    "97.039": "fema_bric",
    "66.926": "epa_gap",
    "66.468": "epa_stag",
    "20.205": "fhwa_ttp_safety",
    "14.867": "hud_ihbg",
    "81.087": "doe_indian_energy",
    "10.691": "usda_wildfire",
    "15.507": "usbr_watersmart",
    "20.934": "dot_protect",
}


class USASpendingScraper(BaseScraper):
    """Scrapes USASpending.gov for actual obligation data by CFDA."""

    def __init__(self, config: dict):
        super().__init__("usaspending")
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

    async def _fetch_obligations(
        self, session: aiohttp.ClientSession, cfda: str, program_id: str,
    ) -> list[dict]:
        """Fetch spending by CFDA using the spending_by_award_count endpoint."""
        payload = {
            "filters": {
                "time_period": [{"start_date": "2025-10-01", "end_date": "2026-09-30"}],
                "award_type_codes": ["02", "03", "04", "05"],  # Grants
                "program_numbers": [cfda],
            },
            "subawards": False,
            "page": 1,
            "limit": 10,
            "sort": "Award Amount",
            "order": "desc",
        }
        url = f"{self.base_url}/search/spending_by_award/"

        try:
            data = await self._request_with_retry(session, "POST", url, json=payload)
        except Exception:
            logger.warning("USASpending: could not fetch CFDA %s, skipping", cfda)
            return []

        results = data.get("results", [])
        return [self._normalize(item, cfda, program_id) for item in results]

    def _normalize(self, item: dict, cfda: str, program_id: str) -> dict:
        """Map USASpending fields to the standard schema."""
        award_amount = item.get("Award Amount") or item.get("Total Obligation") or 0
        recipient = item.get("Recipient Name", "")

        return {
            "source": "usaspending",
            "source_id": f"usa_{cfda}_{item.get('internal_id', '')}",
            "title": f"FY26 Obligation: {item.get('Award ID', cfda)} — {recipient}",
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
