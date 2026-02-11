"""Ecoregion classification for Tribes based on state location.

Maps each Tribe to one or more of 7 NCA5-derived advocacy ecoregions
using state-to-ecoregion lookup. No geospatial dependencies.
"""

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Default path relative to project root
_DEFAULT_CONFIG_PATH = "data/ecoregion_config.json"


class EcoregionMapper:
    """Maps state abbreviations to ecoregions and retrieves program priorities.

    Loads ecoregion definitions from a JSON config file. The state-to-ecoregion
    mapping is built lazily on first access.
    """

    def __init__(self, config: dict) -> None:
        """Initialize EcoregionMapper.

        Args:
            config: Application config dict. Reads the ecoregion data path from
                    config["packets"]["ecoregion"]["data_path"], falling back to
                    the default data/ecoregion_config.json.
        """
        packets_cfg = config.get("packets", {})
        eco_cfg = packets_cfg.get("ecoregion", {})
        self._data_path = eco_cfg.get("data_path", _DEFAULT_CONFIG_PATH)
        self._ecoregion_data: dict | None = None
        self._state_to_ecoregion: dict[str, str] | None = None

    def _load(self) -> None:
        """Load ecoregion config JSON and build lookup tables."""
        if self._ecoregion_data is not None:
            return

        path = Path(self._data_path)
        if not path.is_absolute():
            # Resolve relative to this file's grandparent (project root)
            path = Path(__file__).resolve().parent.parent.parent / path

        logger.debug("Loading ecoregion config from %s", path)
        with open(path, encoding="utf-8") as f:
            self._ecoregion_data = json.load(f)

        # Build inverted state -> ecoregion mapping
        self._state_to_ecoregion = {}
        for eco_id, eco_def in self._ecoregion_data["ecoregions"].items():
            for state in eco_def["states"]:
                self._state_to_ecoregion[state.upper()] = eco_id

        logger.debug(
            "Loaded %d ecoregions covering %d states",
            len(self._ecoregion_data["ecoregions"]),
            len(self._state_to_ecoregion),
        )

    def classify(self, states: list[str]) -> list[str]:
        """Classify state abbreviations into ecoregion IDs.

        Args:
            states: List of 2-letter state abbreviations (e.g., ["AZ", "NM"]).

        Returns:
            Sorted, deduplicated list of ecoregion IDs.
            Multi-state Tribes may return multiple ecoregions.
            Unknown states are logged and skipped.
        """
        self._load()
        assert self._state_to_ecoregion is not None

        ecoregions: set[str] = set()
        for state in states:
            upper = state.upper().strip()
            eco = self._state_to_ecoregion.get(upper)
            if eco is not None:
                ecoregions.add(eco)
            else:
                logger.warning("State '%s' not found in ecoregion mapping", upper)

        return sorted(ecoregions)

    def get_priority_programs(self, ecoregion: str) -> list[str]:
        """Get ranked priority program IDs for an ecoregion.

        Args:
            ecoregion: Ecoregion ID (e.g., "southwest").

        Returns:
            List of program IDs in priority order, or empty list if
            the ecoregion is not found.
        """
        self._load()
        assert self._ecoregion_data is not None

        eco_def = self._ecoregion_data["ecoregions"].get(ecoregion)
        if eco_def is None:
            logger.warning("Unknown ecoregion: '%s'", ecoregion)
            return []
        return list(eco_def["priority_programs"])

    def get_all_ecoregions(self) -> dict:
        """Return the full ecoregion config dict.

        Returns:
            Dict with "ecoregions" and "metadata" keys.
        """
        self._load()
        assert self._ecoregion_data is not None
        return dict(self._ecoregion_data)
