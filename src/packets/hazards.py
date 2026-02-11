"""Hazard profiling pipeline: FEMA NRI + USFS Wildfire Risk ingestion.

Builds per-Tribe hazard profiles by:
  1. Parsing FEMA National Risk Index (NRI) county-level CSV data
  2. Bridging NRI counties to Tribal areas via AIANNH crosswalk
  3. Parsing USFS Wildfire Risk to Communities XLSX data
  4. Aggregating and caching per-Tribe hazard profiles as JSON

The NRI does NOT have Tribal areas as a primary geographic unit. FEMA provides
a "Tribal County Relational Database" CSV that maps AIANNH boundaries to
overlapping NRI counties. The existing aiannh_tribe_crosswalk.json bridges
Census AIANNH GEOIDs to EPA tribe_ids.

Usage:
    builder = HazardProfileBuilder(config)
    count = builder.build_all_profiles()
    print(f"Built {count} hazard profiles")
"""

import csv
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from src.paths import (
    AIANNH_CROSSWALK_PATH,
    HAZARD_PROFILES_DIR,
    NRI_DIR,
    PROJECT_ROOT,
    USFS_DIR,
)

logger = logging.getLogger(__name__)

# All 18 NRI hazard type codes and their display names
NRI_HAZARD_CODES = {
    "AVLN": "Avalanche",
    "CFLD": "Coastal Flooding",
    "CWAV": "Cold Wave",
    "DRGT": "Drought",
    "ERQK": "Earthquake",
    "HAIL": "Hail",
    "HWAV": "Heat Wave",
    "HRCN": "Hurricane",
    "ISTM": "Ice Storm",
    "IFLD": "Inland Flooding",
    "LNDS": "Landslide",
    "LTNG": "Lightning",
    "SWND": "Strong Wind",
    "TRND": "Tornado",
    "TSUN": "Tsunami",
    "VLCN": "Volcanic Activity",
    "WFIR": "Wildfire",
    "WNTW": "Winter Weather",
}

# US state abbreviation to FIPS prefix mapping for state-level fallback
_STATE_FIPS_PREFIX = {
    "AL": "01", "AK": "02", "AZ": "04", "AR": "05", "CA": "06",
    "CO": "08", "CT": "09", "DE": "10", "DC": "11", "FL": "12",
    "GA": "13", "HI": "15", "ID": "16", "IL": "17", "IN": "18",
    "IA": "19", "KS": "20", "KY": "21", "LA": "22", "ME": "23",
    "MD": "24", "MA": "25", "MI": "26", "MN": "27", "MS": "28",
    "MO": "29", "MT": "30", "NE": "31", "NV": "32", "NH": "33",
    "NJ": "34", "NM": "35", "NY": "36", "NC": "37", "ND": "38",
    "OH": "39", "OK": "40", "OR": "41", "PA": "42", "RI": "44",
    "SC": "45", "SD": "46", "TN": "47", "TX": "48", "UT": "49",
    "VT": "50", "VA": "51", "WA": "53", "WV": "54", "WI": "55",
    "WY": "56",
}


def _safe_float(value, default: float = 0.0) -> float:
    """Convert a value to float, returning default for empty/None/non-numeric.

    Args:
        value: The value to convert. May be str, None, int, float, or empty.
        default: Fallback value if conversion fails.

    Returns:
        Float value or default.
    """
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).strip()
    if not s:
        return default
    try:
        return float(s)
    except (ValueError, TypeError):
        return default


def _resolve_path(raw_path: str) -> Path:
    """Resolve a path relative to project root if not absolute.

    Args:
        raw_path: File or directory path (absolute or relative).

    Returns:
        Resolved Path object.
    """
    p = Path(raw_path)
    if not p.is_absolute():
        p = PROJECT_ROOT / p
    return p


class HazardProfileBuilder:
    """Builds per-Tribe hazard profiles from FEMA NRI and USFS data.

    Loads NRI county-level CSV data, bridges to Tribal areas via the
    AIANNH crosswalk, adds USFS wildfire metrics, and writes per-Tribe
    JSON cache files to data/hazard_profiles/.

    Attributes:
        crosswalk_path: Path to aiannh_tribe_crosswalk.json.
        nri_dir: Path to directory containing NRI CSV files.
        usfs_dir: Path to directory containing USFS XLSX files.
        cache_dir: Path to output directory for per-Tribe cache files.
    """

    def __init__(self, config: dict) -> None:
        """Initialize the builder.

        Args:
            config: Application configuration dict. Reads paths from
                config["packets"]["hazards"][*], falling back to defaults.
        """
        from src.packets.registry import TribalRegistry

        packets_cfg = config.get("packets", {})
        hazards_cfg = packets_cfg.get("hazards", {})

        raw = hazards_cfg.get("crosswalk_path")
        self.crosswalk_path = _resolve_path(raw) if raw else AIANNH_CROSSWALK_PATH

        raw = hazards_cfg.get("nri_dir")
        self.nri_dir = _resolve_path(raw) if raw else NRI_DIR

        raw = hazards_cfg.get("usfs_dir")
        self.usfs_dir = _resolve_path(raw) if raw else USFS_DIR

        raw = hazards_cfg.get("cache_dir")
        self.cache_dir = _resolve_path(raw) if raw else HAZARD_PROFILES_DIR

        # Load registry for tribe enumeration
        self._registry = TribalRegistry(config)

        # Load crosswalk: AIANNH GEOID -> tribe_id
        self._crosswalk: dict[str, str] = {}
        # Reverse crosswalk: tribe_id -> list of AIANNH GEOIDs
        self._tribe_to_geoids: dict[str, list[str]] = {}
        self._load_crosswalk()

    def _load_crosswalk(self) -> None:
        """Load and invert the AIANNH-to-tribe_id crosswalk.

        The crosswalk JSON has structure:
            {"mappings": {"GEOID": "tribe_id", ...}}

        One Tribe may span multiple AIANNH areas, so the reverse mapping
        is tribe_id -> list[GEOID].
        """
        try:
            with open(self.crosswalk_path, encoding="utf-8") as f:
                data = json.load(f)
        except FileNotFoundError:
            logger.warning(
                "AIANNH crosswalk not found at %s -- "
                "all Tribes will get empty hazard profiles",
                self.crosswalk_path,
            )
            return
        except json.JSONDecodeError as exc:
            logger.error(
                "Crosswalk at %s is invalid JSON: %s",
                self.crosswalk_path, exc,
            )
            return

        self._crosswalk = data.get("mappings", {})

        # Build reverse mapping: tribe_id -> [geoid, ...]
        for geoid, tribe_id in self._crosswalk.items():
            if tribe_id not in self._tribe_to_geoids:
                self._tribe_to_geoids[tribe_id] = []
            self._tribe_to_geoids[tribe_id].append(geoid)

        logger.info(
            "Loaded crosswalk: %d AIANNH GEOIDs -> %d unique tribe_ids",
            len(self._crosswalk),
            len(self._tribe_to_geoids),
        )

    def _load_nri_county_data(self) -> dict[str, dict]:
        """Parse the NRI county-level CSV file.

        Reads data/nri/NRI_Table_Counties.csv and extracts composite
        risk metrics plus per-hazard scores for all 18 hazard types.

        Returns:
            Dict keyed by STCOFIPS (state+county FIPS) -> metrics dict.
            Empty dict if the file does not exist.
        """
        csv_path = self.nri_dir / "NRI_Table_Counties.csv"
        if not csv_path.exists():
            logger.warning(
                "NRI county CSV not found at %s -- "
                "NRI hazard data will be unavailable. "
                "Download from https://hazards.fema.gov/nri/data-resources",
                csv_path,
            )
            return {}

        county_data: dict[str, dict] = {}
        logger.info("Loading NRI county data from %s", csv_path)

        with open(csv_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            row_count = 0
            for row in reader:
                fips = row.get("STCOFIPS", "").strip()
                if not fips:
                    continue

                record: dict = {
                    "fips": fips,
                    "county": row.get("COUNTY", ""),
                    "state": row.get("STATE", ""),
                    # Composite risk metrics
                    "risk_score": _safe_float(row.get("RISK_SCORE")),
                    "risk_rating": row.get("RISK_RATNG", "").strip(),
                    "risk_value": _safe_float(row.get("RISK_VALUE")),
                    "eal_total": _safe_float(row.get("EAL_VALT")),
                    "eal_score": _safe_float(row.get("EAL_SCORE")),
                    "eal_rating": row.get("EAL_RATNG", "").strip(),
                    "sovi_score": _safe_float(row.get("SOVI_SCORE")),
                    "sovi_rating": row.get("SOVI_RATNG", "").strip(),
                    "resl_score": _safe_float(row.get("RESL_SCORE")),
                    "resl_rating": row.get("RESL_RATNG", "").strip(),
                    # Per-hazard metrics
                    "hazards": {},
                }

                for code in NRI_HAZARD_CODES:
                    record["hazards"][code] = {
                        "risk_score": _safe_float(row.get(f"{code}_RISKS")),
                        "risk_rating": row.get(f"{code}_RISKR", "").strip(),
                        "eal_total": _safe_float(row.get(f"{code}_EALT")),
                        "annualized_freq": _safe_float(row.get(f"{code}_AFREQ")),
                        "num_events": _safe_float(row.get(f"{code}_EVNTS")),
                    }

                county_data[fips] = record
                row_count += 1

        logger.info("Loaded NRI data for %d counties", row_count)
        return county_data

    def _load_nri_tribal_relational(self) -> dict[str, list[str]]:
        """Parse the NRI Tribal County Relational CSV.

        Maps AIANNH area GEOIDs to lists of overlapping county FIPS codes.
        Searches data/nri/ for CSV files with 'Tribal' and 'Relational'
        in the filename.

        Returns:
            Dict mapping AIANNH GEOID -> list of county FIPS codes.
            Empty dict if the relational CSV is not found.
        """
        # Search for the tribal relational CSV by pattern
        nri_path = self.nri_dir
        if not nri_path.exists():
            logger.warning(
                "NRI data directory %s does not exist -- "
                "tribal-county relational data unavailable",
                nri_path,
            )
            return {}

        candidates = []
        for csv_file in nri_path.iterdir():
            name_lower = csv_file.name.lower()
            if (csv_file.suffix.lower() == ".csv"
                    and "tribal" in name_lower
                    and "relational" in name_lower):
                candidates.append(csv_file)

        if not candidates:
            logger.warning(
                "No NRI Tribal County Relational CSV found in %s -- "
                "will fall back to state-level county matching",
                nri_path,
            )
            return {}

        csv_path = candidates[0]
        if len(candidates) > 1:
            logger.info(
                "Found %d tribal relational CSVs, using: %s",
                len(candidates), csv_path.name,
            )

        logger.info("Loading NRI tribal relational data from %s", csv_path)
        tribal_counties: dict[str, list[str]] = {}

        with open(csv_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames or []
            logger.info("Tribal relational CSV headers: %s", headers)

            # Discover column names -- look for AIANNH GEOID and county FIPS
            geoid_col = None
            fips_col = None
            for h in headers:
                h_upper = h.upper()
                if geoid_col is None and any(
                    kw in h_upper for kw in ["AIESSION", "AESSION", "GEOID", "AIANNH", "TRIBAL_ID"]
                ):
                    geoid_col = h
                if fips_col is None and any(
                    kw in h_upper for kw in ["STCOFIPS", "COUNTYFIPS", "COUNTY_FIPS", "CNTY_FIPS"]
                ):
                    fips_col = h

            if geoid_col is None or fips_col is None:
                # Broader search: any column with 'geoid' or 'fips'
                for h in headers:
                    h_lower = h.lower()
                    if geoid_col is None and "geoid" in h_lower:
                        geoid_col = h
                    if fips_col is None and "fips" in h_lower and "state" not in h_lower:
                        fips_col = h

            if geoid_col is None or fips_col is None:
                logger.error(
                    "Cannot identify GEOID and FIPS columns in %s. "
                    "Headers: %s. Tried GEOID/AIANNH and STCOFIPS/COUNTYFIPS patterns.",
                    csv_path, headers,
                )
                return {}

            logger.info(
                "Using columns: GEOID='%s', FIPS='%s'",
                geoid_col, fips_col,
            )

            for row in reader:
                geoid = row.get(geoid_col, "").strip()
                fips = row.get(fips_col, "").strip()
                if geoid and fips:
                    if geoid not in tribal_counties:
                        tribal_counties[geoid] = []
                    if fips not in tribal_counties[geoid]:
                        tribal_counties[geoid].append(fips)

        logger.info(
            "Loaded tribal-county relations: %d AIANNH areas -> %d total county links",
            len(tribal_counties),
            sum(len(v) for v in tribal_counties.values()),
        )
        return tribal_counties

    def _get_state_county_fips(
        self, states: list[str], county_data: dict[str, dict]
    ) -> list[str]:
        """Fallback: get all county FIPS codes for given states.

        Used when the NRI tribal relational CSV is unavailable. Less precise
        than AIANNH-to-county matching but ensures every Tribe gets some data.

        Args:
            states: List of 2-letter state abbreviations.
            county_data: Full NRI county data dict keyed by STCOFIPS.

        Returns:
            List of county FIPS codes whose state prefix matches.
        """
        state_prefixes = set()
        for st in states:
            prefix = _STATE_FIPS_PREFIX.get(st.upper())
            if prefix:
                state_prefixes.add(prefix)

        if not state_prefixes:
            return []

        return [
            fips for fips in county_data
            if fips[:2] in state_prefixes
        ]

    def _build_tribe_nri_profile(
        self,
        tribe_id: str,
        tribe: dict,
        county_data: dict[str, dict],
        tribal_counties: dict[str, list[str]],
    ) -> dict:
        """Aggregate NRI data for a single Tribe.

        Resolution chain:
          1. tribe_id -> AIANNH GEOIDs (from crosswalk)
          2. AIANNH GEOIDs -> county FIPS (from tribal relational data)
          3. County FIPS -> NRI records (from county data)

        Aggregation strategy:
          - Per-hazard risk_score: MAX across overlapping counties
          - EAL total: SUM across overlapping counties
          - SOVI score: MAX (worst social vulnerability)
          - RESL score: MIN (worst community resilience)
          - Top 3 hazards: ranked by aggregated risk score descending

        Args:
            tribe_id: EPA tribe identifier.
            tribe: Tribe dict from registry.
            county_data: Full NRI county data dict.
            tribal_counties: AIANNH GEOID -> county FIPS mapping.

        Returns:
            NRI profile dict with composite scores, top hazards, and all hazards.
        """
        if not county_data:
            return self._empty_nri_profile("NRI county data not loaded")

        # Step 1: Find AIANNH GEOIDs for this tribe
        geoids = self._tribe_to_geoids.get(tribe_id, [])

        # Step 2: Find county FIPS codes
        county_fips_set: set[str] = set()
        if geoids and tribal_counties:
            for geoid in geoids:
                fips_list = tribal_counties.get(geoid, [])
                county_fips_set.update(fips_list)

        # Fallback: if no tribal relational data or no matches, use state-level
        if not county_fips_set:
            states = tribe.get("states", [])
            if states:
                state_fips = self._get_state_county_fips(states, county_data)
                county_fips_set.update(state_fips)

        if not county_fips_set:
            return self._empty_nri_profile(
                "No county matches found (no crosswalk entry or state data)"
            )

        # Step 3: Collect matching county NRI records
        matched_counties = []
        for fips in county_fips_set:
            if fips in county_data:
                matched_counties.append(county_data[fips])

        if not matched_counties:
            return self._empty_nri_profile(
                f"Counties identified ({len(county_fips_set)}) but none found in NRI data"
            )

        # Step 4: Aggregate composite scores
        composite = {
            "risk_score": max(c["risk_score"] for c in matched_counties),
            "risk_rating": self._max_rating(
                [c["risk_rating"] for c in matched_counties]
            ),
            "eal_total": sum(c["eal_total"] for c in matched_counties),
            "eal_score": max(c["eal_score"] for c in matched_counties),
            "sovi_score": max(c["sovi_score"] for c in matched_counties),
            "sovi_rating": self._max_rating(
                [c["sovi_rating"] for c in matched_counties]
            ),
            "resl_score": min(c["resl_score"] for c in matched_counties),
            "resl_rating": self._min_rating(
                [c["resl_rating"] for c in matched_counties]
            ),
        }

        # Step 5: Aggregate per-hazard scores
        all_hazards: dict[str, dict] = {}
        for code in NRI_HAZARD_CODES:
            hazard_records = [
                c["hazards"][code] for c in matched_counties
                if code in c.get("hazards", {})
            ]
            if hazard_records:
                all_hazards[code] = {
                    "risk_score": max(h["risk_score"] for h in hazard_records),
                    "risk_rating": self._max_rating(
                        [h["risk_rating"] for h in hazard_records]
                    ),
                    "eal_total": sum(h["eal_total"] for h in hazard_records),
                    "annualized_freq": max(
                        h["annualized_freq"] for h in hazard_records
                    ),
                    "num_events": sum(h["num_events"] for h in hazard_records),
                }
            else:
                all_hazards[code] = {
                    "risk_score": 0.0,
                    "risk_rating": "",
                    "eal_total": 0.0,
                    "annualized_freq": 0.0,
                    "num_events": 0.0,
                }

        # Step 6: Top 3 hazards by risk score
        sorted_hazards = sorted(
            all_hazards.items(),
            key=lambda x: x[1]["risk_score"],
            reverse=True,
        )
        top_hazards = [
            {
                "type": NRI_HAZARD_CODES[code],
                "code": code,
                "risk_score": data["risk_score"],
                "risk_rating": data["risk_rating"],
                "eal_total": data["eal_total"],
            }
            for code, data in sorted_hazards[:3]
        ]

        return {
            "version": "1.20",
            "counties_analyzed": len(matched_counties),
            "composite": composite,
            "top_hazards": top_hazards,
            "all_hazards": all_hazards,
        }

    def _empty_nri_profile(self, note: str) -> dict:
        """Return a minimal NRI profile when no data is available.

        Args:
            note: Explanation of why data is unavailable.

        Returns:
            Dict with null/zero values and a note field.
        """
        return {
            "version": "1.20",
            "counties_analyzed": 0,
            "note": note,
            "composite": {
                "risk_score": 0.0,
                "risk_rating": "",
                "eal_total": 0.0,
                "eal_score": 0.0,
                "sovi_score": 0.0,
                "sovi_rating": "",
                "resl_score": 0.0,
                "resl_rating": "",
            },
            "top_hazards": [],
            "all_hazards": {
                code: {
                    "risk_score": 0.0,
                    "risk_rating": "",
                    "eal_total": 0.0,
                    "annualized_freq": 0.0,
                    "num_events": 0.0,
                }
                for code in NRI_HAZARD_CODES
            },
        }

    @staticmethod
    def _max_rating(ratings: list[str]) -> str:
        """Return the highest NRI risk rating from a list.

        NRI ratings: Very Low < Relatively Low < Relatively Moderate
                   < Relatively High < Very High

        Args:
            ratings: List of NRI rating strings.

        Returns:
            The highest rating found, or empty string if none.
        """
        order = [
            "Very Low",
            "Relatively Low",
            "Relatively Moderate",
            "Relatively High",
            "Very High",
        ]
        best_idx = -1
        best_val = ""
        for r in ratings:
            r_stripped = r.strip()
            if r_stripped in order:
                idx = order.index(r_stripped)
                if idx > best_idx:
                    best_idx = idx
                    best_val = r_stripped
        return best_val

    @staticmethod
    def _min_rating(ratings: list[str]) -> str:
        """Return the lowest NRI rating from a list (worst resilience).

        Used for community resilience where lower = worse.

        Args:
            ratings: List of NRI rating strings.

        Returns:
            The lowest rating found, or empty string if none.
        """
        order = [
            "Very Low",
            "Relatively Low",
            "Relatively Moderate",
            "Relatively High",
            "Very High",
        ]
        best_idx = len(order)
        best_val = ""
        for r in ratings:
            r_stripped = r.strip()
            if r_stripped in order:
                idx = order.index(r_stripped)
                if idx < best_idx:
                    best_idx = idx
                    best_val = r_stripped
        return best_val

    def _load_usfs_wildfire_data(self) -> dict[str, dict]:
        """Parse the USFS Wildfire Risk to Communities XLSX.

        Searches data/usfs/ for XLSX files and reads wildfire risk metrics.
        Since exact column names are uncertain, performs schema discovery
        by inspecting headers first.

        Returns:
            Dict keyed by geographic identifier (GEOID or name) -> wildfire
            metrics dict. Empty dict if no XLSX found or parse fails.
        """
        if not self.usfs_dir.exists():
            logger.warning(
                "USFS data directory %s does not exist -- "
                "wildfire risk data will be unavailable. "
                "Download from https://wildfirerisk.org/",
                self.usfs_dir,
            )
            return {}

        # Find XLSX files
        xlsx_files = list(self.usfs_dir.glob("*.xlsx"))
        if not xlsx_files:
            logger.warning(
                "No XLSX files found in %s -- wildfire risk data unavailable",
                self.usfs_dir,
            )
            return {}

        xlsx_path = xlsx_files[0]
        if len(xlsx_files) > 1:
            logger.info(
                "Found %d XLSX files in USFS dir, using: %s",
                len(xlsx_files), xlsx_path.name,
            )

        logger.info("Loading USFS wildfire data from %s", xlsx_path)

        try:
            from openpyxl import load_workbook
        except ImportError:
            logger.error(
                "openpyxl not installed -- cannot parse USFS XLSX. "
                "Install with: pip install openpyxl"
            )
            return {}

        try:
            wb = load_workbook(xlsx_path, read_only=True, data_only=True)
        except Exception as exc:
            logger.error(
                "Failed to open USFS XLSX %s: %s", xlsx_path, exc,
            )
            return {}

        ws = wb.active
        if ws is None:
            logger.error("No active sheet in USFS XLSX %s", xlsx_path)
            wb.close()
            return {}

        # Read headers from first row
        rows = ws.iter_rows(min_row=1, max_row=1, values_only=True)
        header_row = next(rows, None)
        if header_row is None:
            logger.error("Empty USFS XLSX %s", xlsx_path)
            wb.close()
            return {}

        headers = [str(h).strip() if h is not None else "" for h in header_row]
        logger.info("USFS XLSX headers: %s", headers)

        # Discover column indices by keyword matching
        geoid_idx = None
        name_idx = None
        risk_idx = None
        likelihood_idx = None

        for i, h in enumerate(headers):
            h_lower = h.lower()
            if geoid_idx is None and any(
                kw in h_lower for kw in ["geoid", "aiannh", "fips"]
            ):
                geoid_idx = i
            if name_idx is None and any(
                kw in h_lower for kw in ["name", "tribal", "community"]
            ):
                name_idx = i
            if risk_idx is None and any(
                kw in h_lower for kw in ["risk_to_homes", "risk score", "whp", "risk"]
            ):
                risk_idx = i
            if likelihood_idx is None and any(
                kw in h_lower
                for kw in ["likelihood", "burn_prob", "burn probability", "probability"]
            ):
                likelihood_idx = i

        # If we found neither geoid nor name, we can't key the data
        if geoid_idx is None and name_idx is None:
            logger.warning(
                "USFS XLSX headers don't contain recognizable GEOID or name columns. "
                "Headers: %s. Wildfire data will be unavailable.",
                headers,
            )
            wb.close()
            return {}

        logger.info(
            "USFS column mapping: geoid_idx=%s, name_idx=%s, risk_idx=%s, likelihood_idx=%s",
            geoid_idx, name_idx, risk_idx, likelihood_idx,
        )

        usfs_data: dict[str, dict] = {}
        for row in ws.iter_rows(min_row=2, values_only=True):
            if row is None:
                continue

            # Determine the key (prefer GEOID, fallback to name)
            key = None
            geoid_val = None
            name_val = None

            if geoid_idx is not None and geoid_idx < len(row) and row[geoid_idx]:
                geoid_val = str(row[geoid_idx]).strip()
                key = geoid_val
            if name_idx is not None and name_idx < len(row) and row[name_idx]:
                name_val = str(row[name_idx]).strip()
                if key is None:
                    key = name_val

            if not key:
                continue

            record = {
                "geoid": geoid_val,
                "name": name_val,
                "risk_to_homes": _safe_float(
                    row[risk_idx] if risk_idx is not None and risk_idx < len(row) else None
                ),
                "wildfire_likelihood": _safe_float(
                    row[likelihood_idx]
                    if likelihood_idx is not None and likelihood_idx < len(row)
                    else None
                ),
            }

            # Capture all numeric columns as extra metrics
            extras = {}
            for i, h in enumerate(headers):
                if i in (geoid_idx, name_idx, risk_idx, likelihood_idx):
                    continue
                if i < len(row) and row[i] is not None:
                    val = _safe_float(row[i], default=None)
                    if val is not None:
                        extras[h] = val
            if extras:
                record["additional_metrics"] = extras

            usfs_data[key] = record

        wb.close()
        logger.info("Loaded USFS wildfire data for %d areas", len(usfs_data))
        return usfs_data

    def _match_usfs_to_tribe(
        self, usfs_data: dict[str, dict], tribe: dict
    ) -> dict | None:
        """Match USFS wildfire data to a specific Tribe.

        Matching strategy:
          1. AIANNH GEOID match (if USFS data is keyed by GEOID)
          2. Name match using normalized string comparison

        Args:
            usfs_data: Full USFS data dict from _load_usfs_wildfire_data().
            tribe: Tribe dict from registry.

        Returns:
            Matched wildfire metrics dict, or None if no match.
        """
        if not usfs_data:
            return None

        tribe_id = tribe["tribe_id"]
        geoids = self._tribe_to_geoids.get(tribe_id, [])

        # Strategy 1: GEOID match
        for geoid in geoids:
            if geoid in usfs_data:
                return usfs_data[geoid]

        # Strategy 2: Name match via normalized comparison
        tribe_name = tribe["name"].lower().strip()
        alt_names = [n.lower().strip() for n in tribe.get("alternate_names", [])]
        all_names = [tribe_name] + alt_names

        for key, record in usfs_data.items():
            record_name = (record.get("name") or key).lower().strip()
            for name in all_names:
                if name == record_name or name in record_name or record_name in name:
                    return record

        return None

    def build_all_profiles(self) -> int:
        """Build and cache hazard profiles for all 592 Tribes.

        Main orchestration method:
          1. Load NRI county data from CSV
          2. Load NRI tribal relational data (AIANNH -> county mapping)
          3. Load USFS wildfire data from XLSX
          4. For each Tribe: build NRI profile + USFS match -> JSON cache

        Returns:
            Number of profile files written.
        """
        # Ensure cache directory exists
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Load data sources
        county_data = self._load_nri_county_data()
        tribal_counties = self._load_nri_tribal_relational()
        usfs_data = self._load_usfs_wildfire_data()

        all_tribes = self._registry.get_all()
        logger.info(
            "Building hazard profiles for %d Tribes "
            "(NRI counties: %d, tribal relations: %d, USFS areas: %d)",
            len(all_tribes),
            len(county_data),
            len(tribal_counties),
            len(usfs_data),
        )

        files_written = 0
        nri_matched = 0
        usfs_matched = 0
        unmatched_tribes: list[str] = []

        for tribe in all_tribes:
            tribe_id = tribe["tribe_id"]

            # Build NRI profile
            nri_profile = self._build_tribe_nri_profile(
                tribe_id, tribe, county_data, tribal_counties,
            )
            if nri_profile.get("counties_analyzed", 0) > 0:
                nri_matched += 1

            # Match USFS wildfire data
            usfs_match = self._match_usfs_to_tribe(usfs_data, tribe)
            usfs_profile: dict = {}
            if usfs_match:
                usfs_matched += 1
                usfs_profile = {
                    "risk_to_homes": usfs_match.get("risk_to_homes", 0.0),
                    "wildfire_likelihood": usfs_match.get("wildfire_likelihood", 0.0),
                    "source_name": usfs_match.get("name", ""),
                }
                if "additional_metrics" in usfs_match:
                    usfs_profile["additional_metrics"] = usfs_match["additional_metrics"]

            # Track unmatched
            if nri_profile.get("counties_analyzed", 0) == 0 and not usfs_match:
                unmatched_tribes.append(tribe["name"])

            # Combine into full profile
            profile = {
                "tribe_id": tribe_id,
                "tribe_name": tribe["name"],
                "sources": {
                    "fema_nri": nri_profile,
                    "usfs_wildfire": usfs_profile,
                },
                "generated_at": datetime.now(timezone.utc).isoformat(),
            }

            # Write cache file
            cache_file = self.cache_dir / f"{tribe_id}.json"
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(profile, f, indent=2, ensure_ascii=False)
            files_written += 1

        # Log summary
        logger.info(
            "Hazard profile build complete: %d files written, "
            "%d with NRI data, %d with USFS data, %d fully unmatched",
            files_written,
            nri_matched,
            usfs_matched,
            len(unmatched_tribes),
        )

        if unmatched_tribes:
            logger.warning(
                "%d Tribes have no hazard data (no crosswalk entry, "
                "no state match, no USFS match): %s%s",
                len(unmatched_tribes),
                ", ".join(unmatched_tribes[:10]),
                f"... and {len(unmatched_tribes) - 10} more"
                if len(unmatched_tribes) > 10 else "",
            )

        return files_written
