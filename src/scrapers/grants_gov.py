"""Grants.gov API scraper.

Collects open and recently posted grant opportunities from the Grants.gov
REST API (no API key required).

Integration strategy: queries by CFDA number for known programs, plus
keyword searches for broad coverage. Populates FundingVehicle nodes.
"""

import asyncio
import logging
from datetime import datetime, timedelta

import aiohttp

logger = logging.getLogger(__name__)

# CFDA numbers for tracked programs (Assistance Listings)
CFDA_NUMBERS = {
    "15.156": "bia_tcr",        # BIA Tribal Climate Resilience
    "97.047": "fema_bric",      # FEMA BRIC / Hazard Mitigation
    "97.039": "fema_bric",      # FEMA Hazard Mitigation Grant Program
    "66.926": "epa_gap",        # EPA Indian Environmental GAP
    "66.468": "epa_stag",       # EPA Drinking Water SRF (Tribal set-aside)
    "20.205": "fhwa_ttp_safety",  # FHWA Highway Planning & Construction (includes TTP)
    "14.867": "hud_ihbg",       # HUD IHBG
    "81.087": "doe_indian_energy",  # DOE Indian Energy
    "10.691": "usda_wildfire",  # USDA Community Wildfire Defense
    "15.507": "usbr_watersmart",  # USBR WaterSMART
    "20.934": "dot_protect",    # DOT PROTECT
}


class GrantsGovScraper:
    """Scrapes the Grants.gov API for grant opportunities."""

    def __init__(self, config: dict):
        self.base_url = config["sources"]["grants_gov"]["base_url"]
        self.authority_weight = config["sources"]["grants_gov"]["authority_weight"]
        self.search_queries = config.get("search_queries", [])
        self.scan_window = config.get("scan_window_days", 14)

    async def scan(self) -> list[dict]:
        """Run CFDA + keyword searches against Grants.gov."""
        all_items = []
        seen_ids = set()

        async with aiohttp.ClientSession() as session:
            # CFDA-based targeted queries
            for cfda, program_id in CFDA_NUMBERS.items():
                try:
                    items = await self._search_cfda(session, cfda, program_id)
                    for item in items:
                        if item["source_id"] not in seen_ids:
                            seen_ids.add(item["source_id"])
                            all_items.append(item)
                except Exception:
                    logger.exception("Error searching Grants.gov for CFDA %s", cfda)
                await asyncio.sleep(0.3)

            # Keyword-based broad queries
            for query in self.search_queries:
                try:
                    items = await self._search(session, query)
                    for item in items:
                        if item["source_id"] not in seen_ids:
                            seen_ids.add(item["source_id"])
                            all_items.append(item)
                except Exception:
                    logger.exception("Error searching Grants.gov for '%s'", query)
                await asyncio.sleep(0.3)

        logger.info("Grants.gov: collected %d unique items", len(all_items))
        return all_items

    async def _search_cfda(self, session: aiohttp.ClientSession, cfda: str, program_id: str) -> list[dict]:
        """Search by CFDA / Assistance Listing number."""
        payload = {
            "assistanceListing": cfda,
            "oppStatuses": "forecasted|posted",
            "sortBy": "openDate|desc",
            "rows": 25,
        }
        url = f"{self.base_url}/opportunities/search"

        async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=30)) as resp:
            resp.raise_for_status()
            data = await resp.json()

        results = data.get("oppHits", [])
        return [self._normalize(item, cfda=cfda, matched_program=program_id) for item in results]

    async def _search(self, session: aiohttp.ClientSession, query: str) -> list[dict]:
        """Execute a keyword search query."""
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

    def _normalize(self, item: dict, cfda: str = "", matched_program: str = "") -> dict:
        """Map Grants.gov fields to the standard schema."""
        normalized = {
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
        if cfda:
            normalized["cfda"] = cfda
        if matched_program:
            normalized["cfda_program_match"] = matched_program
        return normalized
