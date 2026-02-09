"""Grants.gov API scraper.

Collects open and recently posted grant opportunities from the Grants.gov
REST API (no API key required).

Integration strategy: queries by CFDA number for known programs, plus
keyword searches for broad coverage. Parses eligibility fields to
force-include grants where Tribal governments are eligible even when
keyword density is low. Tracks zombie CFDAs.
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path

from src.scrapers.base import BaseScraper, check_zombie_cfda, CFDA_TRACKER_PATH

logger = logging.getLogger(__name__)

# CFDA numbers for tracked programs (Assistance Listings)
CFDA_NUMBERS = {
    "15.156": "bia_tcr",        # BIA Tribal Climate Resilience
    "15.124": "bia_tcr_awards",  # BIA Tribal Community Resilience Annual Awards
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

# Eligibility codes that indicate Tribal government eligibility
TRIBAL_ELIGIBILITY_CODES = [
    "00",   # State governments (often includes Tribal)
    "06",   # Native American tribal governments (Federally recognized)
    "07",   # Native American tribal organizations
    "11",   # Native American organizations
]


class GrantsGovScraper(BaseScraper):
    """Scrapes the Grants.gov API for grant opportunities."""

    def __init__(self, config: dict):
        super().__init__("grants_gov")
        self.base_url = config["sources"]["grants_gov"]["base_url"]
        self.authority_weight = config["sources"]["grants_gov"]["authority_weight"]
        self.search_queries = config.get("search_queries", [])
        self.scan_window = config.get("scan_window_days", 14)
        self._zombie_warnings: list[dict] = []

    async def scan(self) -> list[dict]:
        """Run CFDA + keyword searches against Grants.gov."""
        all_items = []
        seen_ids = set()

        # Load zombie tracker
        cfda_tracker = self._load_cfda_tracker()

        async with self._create_session() as session:
            # CFDA-based targeted queries
            for cfda, program_id in CFDA_NUMBERS.items():
                try:
                    items = await self._search_cfda(session, cfda, program_id)
                    for item in items:
                        if item["source_id"] not in seen_ids:
                            seen_ids.add(item["source_id"])
                            all_items.append(item)
                    # Zombie CFDA check
                    warning = check_zombie_cfda(cfda, len(items), cfda_tracker)
                    if warning:
                        self._zombie_warnings.append(warning)
                        logger.warning("ZOMBIE CFDA: %s", warning["warning"])
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

        # Save tracker
        self._save_cfda_tracker(cfda_tracker)

        logger.info("Grants.gov: collected %d unique items", len(all_items))
        if self._zombie_warnings:
            logger.warning("Grants.gov: %d zombie CFDA warnings", len(self._zombie_warnings))
        return all_items

    @property
    def zombie_warnings(self) -> list[dict]:
        return self._zombie_warnings

    async def _search_cfda(self, session, cfda: str, program_id: str) -> list[dict]:
        """Search by CFDA / Assistance Listing number."""
        payload = {
            "aln": cfda,
            "oppStatuses": "forecasted|posted",
            "sortBy": "openDate|desc",
            "rows": 25,
        }
        url = f"{self.base_url}/api/search2"
        resp = await self._request_with_retry(session, "POST", url, json=payload)
        data = resp.get("data", resp)
        results = data.get("oppHits", [])
        return [self._normalize(item, cfda=cfda, matched_program=program_id) for item in results]

    async def _search(self, session, query: str) -> list[dict]:
        """Execute a keyword search query."""
        posted_from = (datetime.utcnow() - timedelta(days=self.scan_window)).strftime("%m/%d/%Y")
        payload = {
            "keyword": query,
            "oppStatuses": "forecasted|posted",
            "sortBy": "openDate|desc",
            "rows": 50,
            "postedFrom": posted_from,
        }
        url = f"{self.base_url}/api/search2"
        resp = await self._request_with_retry(session, "POST", url, json=payload)
        data = resp.get("data", resp)
        results = data.get("oppHits", [])
        return [self._normalize(item) for item in results]

    def _normalize(self, item: dict, cfda: str = "", matched_program: str = "") -> dict:
        """Map Grants.gov fields to the standard schema.

        Parses the eligibility field to detect Tribal-eligible grants that
        might otherwise fall below the keyword relevance threshold.
        """
        # Parse eligibility for Tribal force-include
        eligibility_codes = item.get("eligibleApplicants", []) or []
        if isinstance(eligibility_codes, str):
            eligibility_codes = [eligibility_codes]
        tribal_eligible = any(
            code in TRIBAL_ELIGIBILITY_CODES for code in eligibility_codes
        )

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
            "tribal_eligible": tribal_eligible,
            "eligibility_codes": eligibility_codes,
            "authority_weight": self.authority_weight,
        }
        if cfda:
            normalized["cfda"] = cfda
        if matched_program:
            normalized["cfda_program_match"] = matched_program
        # Force high authority weight for Tribal-eligible grants
        if tribal_eligible and not cfda:
            normalized["tribal_eligibility_override"] = True
        return normalized

    @staticmethod
    def _load_cfda_tracker() -> dict:
        if CFDA_TRACKER_PATH.exists():
            try:
                with open(CFDA_TRACKER_PATH) as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        return {}

    @staticmethod
    def _save_cfda_tracker(tracker: dict) -> None:
        CFDA_TRACKER_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(CFDA_TRACKER_PATH, "w") as f:
            json.dump(tracker, f, indent=2)
