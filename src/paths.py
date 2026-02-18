"""Centralized path constants for the TCR Policy Scanner.

Every file and directory path used by the pipeline is defined here as a
module-level constant. Source files import from this module instead of
constructing ad-hoc ``Path(...)`` literals scattered throughout the codebase.

Design rules:
  1. This module imports ONLY ``pathlib.Path`` -- no project imports, no
     config imports, no runtime validation.  This prevents circular-import
     chains and keeps the module importable at any point.
  2. Constants are grouped by purpose (config, data flat files, data
     subdirectories, outputs, docs, scripts).
  3. Helper functions are provided for per-Tribe paths that require a
     ``tribe_id`` parameter (award cache, hazard profiles, packet state).
  4. No path existence checks at import time.  Callers create directories
     as needed (``mkdir(parents=True, exist_ok=True)``).
"""

from pathlib import Path

# ---------------------------------------------------------------------------
# -- Project Root --
# ---------------------------------------------------------------------------

PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent
"""Absolute path to the project root directory (one level above ``src/``)."""

# ---------------------------------------------------------------------------
# -- Config Paths --
# ---------------------------------------------------------------------------

CONFIG_DIR: Path = PROJECT_ROOT / "config"
"""Directory containing scanner configuration files."""

SCANNER_CONFIG_PATH: Path = CONFIG_DIR / "scanner_config.json"
"""Main scanner configuration (sources, scoring, monitors)."""

# ---------------------------------------------------------------------------
# -- Data Paths (flat files) --
# ---------------------------------------------------------------------------

DATA_DIR: Path = PROJECT_ROOT / "data"
"""Top-level data directory for program inventories and reference files."""

PROGRAM_INVENTORY_PATH: Path = DATA_DIR / "program_inventory.json"
"""The 16-program inventory with CI scores, advocacy levers, and CFDA numbers."""

POLICY_TRACKING_PATH: Path = DATA_DIR / "policy_tracking.json"
"""Policy tracking configuration for change detection baselines."""

GRAPH_SCHEMA_PATH: Path = DATA_DIR / "graph_schema.json"
"""Knowledge graph schema: authorities, funding vehicles, barriers, structural asks."""

TRIBAL_REGISTRY_PATH: Path = DATA_DIR / "tribal_registry.json"
"""592-Tribe registry with BIA codes, names, states, and congressional districts."""

TRIBAL_ALIASES_PATH: Path = DATA_DIR / "tribal_aliases.json"
"""Curated alias table mapping variant Tribal Nation names to canonical IDs."""

CONGRESSIONAL_CACHE_PATH: Path = DATA_DIR / "congressional_cache.json"
"""Cached congressional representative data keyed by state and district."""

ECOREGION_CONFIG_PATH: Path = DATA_DIR / "ecoregion_config.json"
"""Ecoregion-to-Tribe mapping for environmental context in packets."""

REGIONAL_CONFIG_PATH: Path = DATA_DIR / "regional_config.json"
"""8-region definitions for Doc C/D regional document generation."""

AIANNH_CROSSWALK_PATH: Path = DATA_DIR / "aiannh_tribe_crosswalk.json"
"""AIANNH-to-Tribe crosswalk for geographic boundary resolution."""

CONGRESSIONAL_INTEL_PATH: Path = DATA_DIR / "congressional_intel.json"
"""Congressional intelligence cache with bill detail and relevance scores."""

# ---------------------------------------------------------------------------
# -- Data Paths (subdirectories) --
# ---------------------------------------------------------------------------

NRI_DIR: Path = DATA_DIR / "nri"
"""FEMA National Risk Index county-level dataset cache."""

USFS_DIR: Path = DATA_DIR / "usfs"
"""USFS wildfire risk data cache."""

TRIBAL_COUNTY_WEIGHTS_PATH: Path = NRI_DIR / "tribal_county_area_weights.json"
"""Pre-computed area-weighted AIANNH-to-county crosswalk."""

AWARD_CACHE_DIR: Path = DATA_DIR / "award_cache"
"""Per-Tribe USASpending award history JSON files (592 files)."""

HAZARD_PROFILES_DIR: Path = DATA_DIR / "hazard_profiles"
"""Per-Tribe FEMA NRI + USFS hazard profile JSON files (592 files)."""

PACKET_STATE_DIR: Path = DATA_DIR / "packet_state"
"""Per-Tribe packet generation state tracking JSON files."""

CENSUS_DATA_PATH: Path = DATA_DIR / "census" / "tab20_cd11920_aiannh20_natl.txt"
"""Census AIANNH-to-congressional-district crosswalk table."""

# ---------------------------------------------------------------------------
# -- Vulnerability Data Paths --
# ---------------------------------------------------------------------------

SVI_DIR: Path = DATA_DIR / "svi"
"""CDC Social Vulnerability Index data directory."""

SVI_COUNTY_PATH: Path = SVI_DIR / "SVI2022_US_COUNTY.csv"
"""SVI 2022 county-level dataset (RPL_THEMES, individual theme percentiles)."""

CLIMATE_DIR: Path = DATA_DIR / "climate"
"""Climate data directory for temperature, precipitation, and summary files."""

CLIMATE_SUMMARY_PATH: Path = CLIMATE_DIR / "climate_summary.json"
"""Aggregated climate summary with per-Tribe indicators."""

VULNERABILITY_PROFILES_DIR: Path = DATA_DIR / "vulnerability_profiles"
"""Per-Tribe composite vulnerability profile JSON files."""

CLIMATE_RAW_DIR: Path = CLIMATE_DIR / "raw"
"""Raw climate data downloads before processing."""

# ---------------------------------------------------------------------------
# -- Output Paths --
# ---------------------------------------------------------------------------

OUTPUTS_DIR: Path = PROJECT_ROOT / "outputs"
"""Top-level output directory for generated briefings, graphs, and data."""

LATEST_RESULTS_PATH: Path = OUTPUTS_DIR / "LATEST-RESULTS.json"
"""Most recent scan results (baseline for change detection)."""

LATEST_GRAPH_PATH: Path = OUTPUTS_DIR / "LATEST-GRAPH.json"
"""Most recent knowledge graph export."""

LATEST_MONITOR_DATA_PATH: Path = OUTPUTS_DIR / "LATEST-MONITOR-DATA.json"
"""Most recent monitor alerts and classifications."""

CI_HISTORY_PATH: Path = OUTPUTS_DIR / ".ci_history.json"
"""CI score history across scan cycles (capped at 90 entries)."""

CFDA_TRACKER_PATH: Path = OUTPUTS_DIR / ".cfda_tracker.json"
"""Zombie CFDA detection tracker (zero-result counters per CFDA)."""

MONITOR_STATE_PATH: Path = OUTPUTS_DIR / ".monitor_state.json"
"""Hot Sheets divergence state persistence."""

ARCHIVE_DIR: Path = OUTPUTS_DIR / "archive"
"""Archived briefings and results from previous scans."""

PACKETS_OUTPUT_DIR: Path = OUTPUTS_DIR / "packets"
"""Generated per-Tribe DOCX advocacy packets."""

# ---------------------------------------------------------------------------
# -- Docs Paths --
# ---------------------------------------------------------------------------

DOCS_DIR: Path = PROJECT_ROOT / "docs"
"""Documentation root."""

WEB_DIR: Path = DOCS_DIR / "web"
"""GitHub Pages web widget source."""

WEB_DATA_DIR: Path = WEB_DIR / "data"
"""Data directory served by the web widget."""

TRIBES_INDEX_PATH: Path = WEB_DATA_DIR / "tribes.json"
"""JSON index of all Tribes for the web search widget."""

# ---------------------------------------------------------------------------
# -- Scripts Paths --
# ---------------------------------------------------------------------------

SCRIPTS_DIR: Path = PROJECT_ROOT / "scripts"
"""Utility scripts for data ingestion and generation."""


# ---------------------------------------------------------------------------
# -- Helper Functions (per-Tribe paths) --
# ---------------------------------------------------------------------------

def award_cache_path(tribe_id: str) -> Path:
    """Return the award cache JSON path for a specific Tribe."""
    return AWARD_CACHE_DIR / f"{tribe_id}.json"


def hazard_profile_path(tribe_id: str) -> Path:
    """Return the hazard profile JSON path for a specific Tribe."""
    return HAZARD_PROFILES_DIR / f"{tribe_id}.json"


def packet_state_path(tribe_id: str) -> Path:
    """Return the packet state JSON path for a specific Tribe."""
    return PACKET_STATE_DIR / f"{tribe_id}.json"


def vulnerability_profile_path(tribe_id: str) -> Path:
    """Return the vulnerability profile JSON path for a specific Tribe."""
    return VULNERABILITY_PROFILES_DIR / f"{tribe_id}.json"
