"""Congressional delegation mapper for Tribe-specific advocacy packets.

Provides the CongressionalMapper class that loads pre-built
congressional_cache.json and delivers delegation lookups (senators,
representatives, committees) for any Tribe by tribe_id.

All lookups are synchronous -- the cache is pre-built by
scripts/build_congress_cache.py so zero API calls happen at runtime.
"""

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Default path relative to project root
_DEFAULT_CACHE_PATH = "data/congressional_cache.json"

# Target committees relevant to tribal affairs
_TARGET_COMMITTEE_PREFIXES = ("SLIA", "SSAP", "SSEG", "SSCM", "HSII", "HSAP")


class CongressionalMapper:
    """Lazy-loading congressional delegation mapper.

    Loads congressional_cache.json on first access and provides
    per-Tribe delegation lookups including districts, senators,
    representatives, and committee assignments.

    Usage::

        mapper = CongressionalMapper(config)
        delegation = mapper.get_delegation("epa_100000171")
        senators = mapper.get_senators("epa_100000171")
        session = mapper.get_congress_session()  # "119"
    """

    def __init__(self, config: dict) -> None:
        """Initialize the mapper.

        Args:
            config: Application config dict. Reads the cache path from
                config["packets"]["congressional_cache"]["data_path"],
                falling back to data/congressional_cache.json.
        """
        packets_cfg = config.get("packets", {})
        cache_cfg = packets_cfg.get("congressional_cache", {})
        self.data_path = Path(
            cache_cfg.get("data_path", _DEFAULT_CACHE_PATH)
        )
        self._cache: dict = {}
        self._loaded: bool = False

    def _load(self) -> None:
        """Lazy-load the congressional cache from JSON.

        Called automatically on first data access. Loads the entire
        cache into memory for fast lookups.
        """
        if self._loaded:
            return

        path = self.data_path
        if not path.exists():
            logger.error("Congressional cache not found: %s", path)
            logger.error(
                "Run 'python scripts/build_congress_cache.py' to generate it."
            )
            self._cache = {
                "metadata": {"congress_session": "119"},
                "members": {},
                "committees": {},
                "delegations": {},
            }
            self._loaded = True
            return

        try:
            with open(path, encoding="utf-8") as f:
                self._cache = json.load(f)
            self._loaded = True

            members_count = len(self._cache.get("members", {}))
            delegations_count = len(self._cache.get("delegations", {}))
            logger.info(
                "Loaded congressional cache: %d members, %d delegations",
                members_count, delegations_count,
            )

            # Warn if placeholder data
            meta = self._cache.get("metadata", {})
            if meta.get("placeholder"):
                logger.warning(
                    "Congressional cache contains placeholder data. "
                    "Run build_congress_cache.py for full data."
                )
            if meta.get("census_only"):
                logger.warning(
                    "Congressional cache was built in Census-only mode "
                    "(no member/committee data). Run full build for complete data."
                )

        except (json.JSONDecodeError, OSError) as exc:
            logger.error("Failed to load congressional cache: %s", exc)
            self._cache = {
                "metadata": {"congress_session": "119"},
                "members": {},
                "committees": {},
                "delegations": {},
            }
            self._loaded = True

    def get_delegation(self, tribe_id: str) -> dict | None:
        """Get the full delegation record for a Tribe.

        Returns the per-Tribe delegation including districts, senators,
        and representatives, or None if the tribe_id is not found.

        Args:
            tribe_id: EPA tribe identifier (e.g., "epa_100000171").

        Returns:
            Delegation dict with keys: tribe_id, districts, states,
            senators, representatives. None if not found.
        """
        self._load()
        return self._cache.get("delegations", {}).get(tribe_id)

    def get_districts(self, tribe_id: str) -> list[dict]:
        """Get congressional districts for a Tribe.

        Returns list of district dicts with keys: district, state,
        aiannh_name, overlap_pct.

        Args:
            tribe_id: EPA tribe identifier.

        Returns:
            List of district records, empty if not found.
        """
        delegation = self.get_delegation(tribe_id)
        if delegation is None:
            return []
        return delegation.get("districts", [])

    def get_senators(self, tribe_id: str) -> list[dict]:
        """Get senators for a Tribe's states (deduplicated).

        Returns one entry per senator, not duplicated across districts.
        Per CONTEXT.md: "senators once per state, not repeated per district."

        Args:
            tribe_id: EPA tribe identifier.

        Returns:
            List of senator records with committee assignments.
        """
        delegation = self.get_delegation(tribe_id)
        if delegation is None:
            return []
        return delegation.get("senators", [])

    def get_representatives(self, tribe_id: str) -> list[dict]:
        """Get House representatives for a Tribe's districts.

        Returns the representative for each congressional district
        that overlaps the Tribe's geographic area.

        Args:
            tribe_id: EPA tribe identifier.

        Returns:
            List of representative records with committee assignments.
        """
        delegation = self.get_delegation(tribe_id)
        if delegation is None:
            return []
        return delegation.get("representatives", [])

    def get_committee_members(self, committee_id: str) -> list[dict]:
        """Get all members of a congressional committee.

        Args:
            committee_id: Committee thomas_id (e.g., "SLIA", "HSII24").

        Returns:
            List of member records for the committee, empty if not found.
        """
        self._load()
        committee = self._cache.get("committees", {}).get(committee_id)
        if committee is None:
            return []
        return committee.get("members", [])

    def get_relevant_committees(self, tribe_id: str) -> list[dict]:
        """Get committees relevant to a Tribe's delegation.

        Returns target committees (SLIA, SSAP, HSII, etc.) where at
        least one of the Tribe's senators or representatives serves.

        Args:
            tribe_id: EPA tribe identifier.

        Returns:
            List of committee dicts with name, id, and relevant members.
        """
        self._load()
        delegation = self.get_delegation(tribe_id)
        if delegation is None:
            return []

        # Collect bioguide_ids for the Tribe's delegation
        member_ids: set[str] = set()
        for s in delegation.get("senators", []):
            member_ids.add(s.get("bioguide_id", ""))
        for r in delegation.get("representatives", []):
            member_ids.add(r.get("bioguide_id", ""))
        member_ids.discard("")

        # Find committees where delegation members serve
        relevant: list[dict] = []
        committees = self._cache.get("committees", {})
        for comm_id, comm_data in committees.items():
            # Only include target committees and their subcommittees
            is_target = any(
                comm_id.startswith(prefix)
                for prefix in _TARGET_COMMITTEE_PREFIXES
            )
            if not is_target:
                continue

            serving_members: list[dict] = []
            for cm in comm_data.get("members", []):
                if cm.get("bioguide_id", "") in member_ids:
                    serving_members.append(cm)

            if serving_members:
                relevant.append({
                    "committee_id": comm_id,
                    "committee_name": comm_data.get("name", comm_id),
                    "chamber": comm_data.get("chamber", ""),
                    "serving_members": serving_members,
                })

        return relevant

    def get_member(self, bioguide_id: str) -> dict | None:
        """Get a congressional member by bioguide ID.

        Args:
            bioguide_id: Congress.gov bioguide identifier (e.g., "M001153").

        Returns:
            Member record dict, or None if not found.
        """
        self._load()
        return self._cache.get("members", {}).get(bioguide_id)

    def get_congress_session(self) -> str:
        """Get the congress session number from cache metadata.

        Returns:
            Congress session string (e.g., "119").
        """
        self._load()
        return self._cache.get("metadata", {}).get("congress_session", "119")
