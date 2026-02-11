"""Build congressional_cache.json from Census CD119-AIANNH + Congress.gov API + YAML.

One-time build script that assembles the complete congressional delegation cache
for all federally recognized Tribes. Combines three data sources:

1. Census CD119-AIANNH relationship file (Tribe-to-district mapping)
2. Congress.gov API (119th Congress member data)
3. unitedstates/congress-legislators YAML (committee assignments)

Usage:
    python scripts/build_congress_cache.py                     # Full build
    python scripts/build_congress_cache.py --skip-api           # Census-only mode
    python scripts/build_congress_cache.py --verbose            # Debug logging
    python scripts/build_congress_cache.py --output path.json   # Custom output
"""

import argparse
import asyncio
import csv
import json
import logging
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

# Ensure project root is on sys.path for src.paths imports
_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPT_DIR.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import aiohttp
import yaml

from src.paths import (
    AIANNH_CROSSWALK_PATH,
    CENSUS_DATA_PATH,
    CONGRESSIONAL_CACHE_PATH,
    TRIBAL_REGISTRY_PATH,
)

logger = logging.getLogger("tcr_scanner.build_congress_cache")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CENSUS_URL = (
    "https://www2.census.gov/geo/docs/maps-data/data/rel2020/"
    "cd-sld/tab20_cd11920_aiannh20_natl.txt"
)
CENSUS_LOCAL_PATH = CENSUS_DATA_PATH

COMMITTEE_MEMBERSHIP_URL = (
    "https://raw.githubusercontent.com/unitedstates/"
    "congress-legislators/main/committee-membership-current.yaml"
)
COMMITTEES_METADATA_URL = (
    "https://raw.githubusercontent.com/unitedstates/"
    "congress-legislators/main/committees-current.yaml"
)

CONGRESS_API_BASE = "https://api.congress.gov/v3"
CONGRESS_SESSION = "119"

# CLASSFP codes for federally recognized tribal areas
FEDERAL_CLASSFP = {"D1", "D2", "D3", "D5", "D8", "D6", "E1"}

# Target committees for tribal affairs
TARGET_COMMITTEES = {"SLIA", "SSAP", "SSEG", "SSCM", "HSII", "HSAP"}

# State FIPS to abbreviation
FIPS_TO_STATE: dict[str, str] = {
    "01": "AL", "02": "AK", "04": "AZ", "05": "AR", "06": "CA",
    "08": "CO", "09": "CT", "10": "DE", "11": "DC", "12": "FL",
    "13": "GA", "15": "HI", "16": "ID", "17": "IL", "18": "IN",
    "19": "IA", "20": "KS", "21": "KY", "22": "LA", "23": "ME",
    "24": "MD", "25": "MA", "26": "MI", "27": "MN", "28": "MS",
    "29": "MO", "30": "MT", "31": "NE", "32": "NV", "33": "NH",
    "34": "NJ", "35": "NM", "36": "NY", "37": "NC", "38": "ND",
    "39": "OH", "40": "OK", "41": "OR", "42": "PA", "44": "RI",
    "45": "SC", "46": "SD", "47": "TN", "48": "TX", "49": "UT",
    "50": "VT", "51": "VA", "53": "WA", "54": "WV", "55": "WI",
    "56": "WY",
}

# Party name to abbreviation
PARTY_ABBR: dict[str, str] = {
    "Republican": "R",
    "Democrat": "D",
    "Democratic": "D",
    "Independent": "I",
}

# Suffixes to strip when normalizing AIANNH names for crosswalk matching
STRIP_SUFFIXES = [
    " Reservation and Off-Reservation Trust Land",
    " Reservation and Trust Land",
    " Off-Reservation Trust Land",
    " Reservation",
    " Rancheria",
    " Colony",
    " Community",
    " Trust Land",
    " Trust Lands",
    " Pueblo",
    " OTSA",
    " TDSA",
    " ANVSA",
    " (Balance)",
    " Indian Village",
    " Village",
]


# ---------------------------------------------------------------------------
# Step 0: Download Census file
# ---------------------------------------------------------------------------

async def download_census_file(session: aiohttp.ClientSession) -> Path:
    """Download Census CD119-AIANNH relationship file if not already cached."""
    local_path = CENSUS_LOCAL_PATH.resolve()

    if local_path.exists() and local_path.stat().st_size > 0:
        logger.info("Census file already cached at %s", local_path)
        return local_path

    local_path.parent.mkdir(parents=True, exist_ok=True)
    logger.info("Downloading Census CD119-AIANNH file from %s", CENSUS_URL)

    try:
        async with session.get(
            CENSUS_URL,
            timeout=aiohttp.ClientTimeout(total=120),
        ) as resp:
            resp.raise_for_status()
            content = await resp.read()
            # Atomic write
            tmp_path = local_path.with_suffix(".tmp")
            tmp_path.write_bytes(content)
            tmp_path.replace(local_path)
            logger.info(
                "Downloaded Census file: %d bytes -> %s",
                len(content), local_path,
            )
            return local_path
    except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
        logger.error("Failed to download Census file: %s", exc)
        raise


# ---------------------------------------------------------------------------
# Step 1: Parse Census CD119-AIANNH relationship file
# ---------------------------------------------------------------------------

def parse_census_cd119_aiannh(filepath: Path) -> dict[str, list[dict]]:
    """Parse Census CD119-AIANNH relationship file into AIANNH-to-district mapping.

    Returns dict keyed by AIANNH GEOID -> list of district records.
    """
    aiannh_districts: dict[str, list[dict]] = defaultdict(list)
    total_rows = 0
    filtered_rows = 0

    with open(filepath, encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="|")
        for row in reader:
            total_rows += 1
            classfp = row.get("CLASSFP_AIANNH_20", "")
            if classfp not in FEDERAL_CLASSFP:
                continue
            filtered_rows += 1

            cd_geoid = row.get("GEOID_CD119_20", "")
            if len(cd_geoid) < 4:
                logger.warning("Short CD GEOID: %s", cd_geoid)
                continue

            state_fips = cd_geoid[:2]
            district_num = cd_geoid[2:]
            state_abbr = FIPS_TO_STATE.get(state_fips, state_fips)

            # Format district: "AZ-01" or "AK-AL" for at-large
            if district_num == "00":
                district_label = f"{state_abbr}-AL"
            else:
                district_label = f"{state_abbr}-{district_num.zfill(2)}"

            aiannh_geoid = row.get("GEOID_AIANNH_20", "")
            aiannh_name = row.get("NAMELSAD_AIANNH_20", "")

            overlap_land = int(row.get("AREALAND_PART", "0") or "0")
            total_land = int(row.get("AREALAND_AIANNH_20", "0") or "0")
            overlap_pct = (
                round(overlap_land / total_land * 100, 1) if total_land > 0 else 0.0
            )

            aiannh_districts[aiannh_geoid].append({
                "district": district_label,
                "state": state_abbr,
                "aiannh_name": aiannh_name,
                "classfp": classfp,
                "overlap_land_sqm": overlap_land,
                "total_land_sqm": total_land,
                "overlap_pct": overlap_pct,
            })

    logger.info(
        "Parsed Census file: %d total rows, %d federal AIANNH rows, %d entities",
        total_rows, filtered_rows, len(aiannh_districts),
    )
    return dict(aiannh_districts)


# ---------------------------------------------------------------------------
# Step 2: Build AIANNH-to-Tribe crosswalk
# ---------------------------------------------------------------------------

def normalize_aiannh_name(name: str) -> str:
    """Normalize an AIANNH name for crosswalk matching.

    Strips common geographic suffixes (Reservation, Rancheria, etc.)
    and normalizes whitespace/case.
    """
    normalized = name.strip()
    for suffix in STRIP_SUFFIXES:
        if normalized.lower().endswith(suffix.lower()):
            normalized = normalized[: -len(suffix)].strip()
            break  # Only strip one suffix
    return normalized


def _generate_name_variants(name: str) -> list[str]:
    """Generate multiple normalized name variants for matching.

    For Alaska Native entities, Census uses "{Name} ANVSA" while EPA uses
    patterns like "Native Village of {Name}", "Village of {Name}",
    "{Name} Native Community", "{Name} Tribe", etc.

    For Oklahoma entities, Census uses "{Name} OTSA" while EPA uses
    "{Name} Nation", "The {Name} Tribe", etc.
    """
    variants: list[str] = []
    base = normalize_aiannh_name(name).strip()
    variants.append(base.lower())

    # Strip additional prefixes/suffixes from EPA names
    epa_prefixes = [
        "native village of ", "village of ", "organized village of ",
        "native ", "the ", "tribe of ",
    ]
    epa_suffixes = [
        " native community", " native village", " tribe", " nation",
        " band", " indian tribe", " indian community",
        " traditional council", " council", " association",
        " community association",
    ]

    low = base.lower()

    # Add variants by stripping EPA-style prefixes
    for prefix in epa_prefixes:
        if low.startswith(prefix):
            stripped = low[len(prefix):].strip()
            if stripped and stripped not in variants:
                variants.append(stripped)

    # Add variants by stripping EPA-style suffixes
    for suffix in epa_suffixes:
        if low.endswith(suffix):
            stripped = low[: -len(suffix)].strip()
            if stripped and stripped not in variants:
                variants.append(stripped)

    # Strip state names from end (e.g., ", Arizona, New Mexico, & Utah")
    # Handle patterns like "Navajo Nation, Arizona, New Mexico, & Utah"
    parts = base.split(",")
    if len(parts) > 1:
        core = parts[0].strip().lower()
        if core and core not in variants:
            variants.append(core)

    # Remove parenthetical content: "Algaaciq (St. Mary's)" -> "algaaciq"
    import re
    no_paren = re.sub(r"\s*\([^)]*\)", "", low).strip()
    if no_paren and no_paren not in variants:
        variants.append(no_paren)

    return variants


def _build_tribe_lookup(registry: dict) -> tuple[dict[str, str], dict[str, str]]:
    """Build comprehensive name variant -> tribe_id lookup from registry.

    Returns (tribe_lookup, tribe_names) where both are keyed by normalized
    name variants.
    """
    tribe_lookup: dict[str, str] = {}  # normalized variant -> tribe_id
    tribe_names: dict[str, str] = {}   # normalized variant -> original name

    for tribe in registry.get("tribes", []):
        tid = tribe["tribe_id"]
        name = tribe["name"]

        # Generate all name variants for this tribe
        all_names = [name] + tribe.get("alternate_names", [])
        for n in all_names:
            for variant in _generate_name_variants(n):
                if variant not in tribe_lookup:
                    tribe_lookup[variant] = tid
                    tribe_names[variant] = name

    return tribe_lookup, tribe_names


def build_crosswalk(
    aiannh_districts: dict[str, list[dict]],
    registry_path: Path | None,
    crosswalk_path: Path,
) -> dict:
    """Build AIANNH GEOID to EPA tribe_id crosswalk.

    Multi-tier linkage:
    1. Load existing curated entries from crosswalk file
    2. Exact match on multiple normalized name variants
    3. Substring containment match (AIANNH core name in EPA name)
    4. Fuzzy match using rapidfuzz token_sort_ratio >= 80
    """
    crosswalk: dict[str, str] = {}
    manual_overrides: dict[str, dict] = {}
    auto_matched = 0
    substring_matched = 0
    fuzzy_matched = 0
    unmatched_entries: list[dict] = []

    # Tier 1: Load existing crosswalk (curated entries)
    if crosswalk_path.exists():
        try:
            with open(crosswalk_path, encoding="utf-8") as f:
                existing = json.load(f)
            crosswalk.update(existing.get("mappings", {}))
            manual_overrides.update(existing.get("manual_overrides", {}))
            # Apply manual overrides
            for geoid, override in manual_overrides.items():
                crosswalk[geoid] = override["tribe_id"]
            logger.info(
                "Loaded existing crosswalk: %d mappings, %d manual overrides",
                len(existing.get("mappings", {})), len(manual_overrides),
            )
        except (json.JSONDecodeError, KeyError) as exc:
            logger.warning("Failed to load existing crosswalk: %s", exc)

    # Load tribal registry for matching
    tribe_lookup: dict[str, str] = {}
    tribe_names: dict[str, str] = {}
    registry_tribes: list[dict] = []

    if registry_path and registry_path.exists():
        try:
            with open(registry_path, encoding="utf-8") as f:
                registry = json.load(f)

            registry_tribes = registry.get("tribes", [])
            tribe_lookup, tribe_names = _build_tribe_lookup(registry)

            logger.info(
                "Loaded tribal registry: %d tribes, %d name variants",
                len(registry_tribes), len(tribe_lookup),
            )
        except (json.JSONDecodeError, KeyError) as exc:
            logger.warning("Failed to load tribal registry: %s", exc)
    else:
        logger.warning(
            "No tribal_registry.json found at %s. "
            "Building skeletal crosswalk from Census AIANNH names only.",
            registry_path,
        )

    # Tier 2: Exact match on normalized name variants (both sides)
    unmatched_geoids: list[str] = []

    for geoid, districts in aiannh_districts.items():
        if geoid in crosswalk:
            continue

        aiannh_name = districts[0]["aiannh_name"] if districts else ""
        aiannh_variants = _generate_name_variants(aiannh_name)

        matched = False
        for variant in aiannh_variants:
            if variant in tribe_lookup:
                crosswalk[geoid] = tribe_lookup[variant]
                auto_matched += 1
                matched = True
                break

        if not matched:
            unmatched_geoids.append(geoid)

    logger.info("Tier 2 (exact variant match): %d matched", auto_matched)

    # Tier 3: Substring containment match
    # For each unmatched AIANNH, check if the core name appears in any
    # EPA tribe name (or vice versa). This handles cases like:
    #   Census "Akiachak ANVSA" -> core "akiachak"
    #   EPA "Akiachak Native Community" -> contains "akiachak"
    if unmatched_geoids and registry_tribes:
        still_unmatched: list[str] = []
        # Build a reverse index: tribe_id -> tribe name
        tribe_id_to_name: dict[str, str] = {}
        for tribe in registry_tribes:
            tribe_id_to_name[tribe["tribe_id"]] = tribe["name"]

        for geoid in unmatched_geoids:
            aiannh_name = aiannh_districts[geoid][0]["aiannh_name"]
            aiannh_variants = _generate_name_variants(aiannh_name)
            # Get shortest meaningful variant (the core name)
            core_variants = sorted(aiannh_variants, key=len)

            matched = False
            for core in core_variants:
                if len(core) < 3:
                    continue  # Skip very short names to avoid false matches

                # Check against all tribe name variants
                best_match_tid = ""
                best_match_len = 0
                for variant_key, tid in tribe_lookup.items():
                    # Check if core is a substring of EPA variant
                    if core in variant_key and len(core) > best_match_len:
                        best_match_tid = tid
                        best_match_len = len(core)
                    # Check if EPA variant is a substring of core
                    elif variant_key in core and len(variant_key) > best_match_len:
                        best_match_tid = tid
                        best_match_len = len(variant_key)

                if best_match_tid and best_match_len >= 4:
                    crosswalk[geoid] = best_match_tid
                    substring_matched += 1
                    matched = True
                    logger.debug(
                        "Substring match: '%s' -> '%s'",
                        aiannh_name,
                        tribe_id_to_name.get(best_match_tid, best_match_tid),
                    )
                    break

            if not matched:
                still_unmatched.append(geoid)

        unmatched_geoids = still_unmatched
        logger.info(
            "Tier 3 (substring containment): %d matched", substring_matched,
        )

    # Tier 4: Fuzzy matching with rapidfuzz
    if unmatched_geoids and tribe_lookup:
        try:
            from rapidfuzz import fuzz

            still_unmatched = []
            tribe_keys = list(tribe_lookup.keys())

            for geoid in unmatched_geoids:
                aiannh_name = aiannh_districts[geoid][0]["aiannh_name"]
                aiannh_variants = _generate_name_variants(aiannh_name)

                best_score = 0.0
                best_key = ""
                for variant in aiannh_variants:
                    for tk in tribe_keys:
                        score = fuzz.token_sort_ratio(variant, tk)
                        if score > best_score:
                            best_score = score
                            best_key = tk

                if best_score >= 80:
                    crosswalk[geoid] = tribe_lookup[best_key]
                    fuzzy_matched += 1
                    logger.debug(
                        "Fuzzy match: '%s' -> '%s' (score=%.1f)",
                        aiannh_name, tribe_names.get(best_key, best_key),
                        best_score,
                    )
                else:
                    still_unmatched.append(geoid)
                    unmatched_entries.append({
                        "geoid": geoid,
                        "aiannh_name": aiannh_name,
                        "best_match": tribe_names.get(best_key, best_key),
                        "best_score": round(best_score, 1),
                    })

            unmatched_geoids = still_unmatched

        except ImportError:
            logger.warning(
                "rapidfuzz not installed; skipping fuzzy matching for %d entries",
                len(unmatched_geoids),
            )
            for geoid in unmatched_geoids:
                aiannh_name = aiannh_districts[geoid][0]["aiannh_name"]
                unmatched_entries.append({
                    "geoid": geoid,
                    "aiannh_name": aiannh_name,
                    "best_match": "",
                    "best_score": 0,
                })
    elif unmatched_geoids:
        # No registry available -- log all unmatched
        for geoid in unmatched_geoids:
            aiannh_name = aiannh_districts[geoid][0]["aiannh_name"]
            unmatched_entries.append({
                "geoid": geoid,
                "aiannh_name": aiannh_name,
                "best_match": "",
                "best_score": 0,
            })

    if unmatched_entries:
        logger.info(
            "Unmatched AIANNH entities: %d (see crosswalk file for details)",
            len(unmatched_entries),
        )

    # Write the crosswalk
    crosswalk_data = {
        "metadata": {
            "description": "Census AIANNH GEOID to EPA tribe_id mapping",
            "built_at": datetime.now(timezone.utc).isoformat(),
            "auto_matched": auto_matched,
            "fuzzy_matched": fuzzy_matched,
            "manual_entries": len(manual_overrides),
            "unmatched": len(unmatched_entries),
            "total_aiannh_entities": len(aiannh_districts),
        },
        "mappings": crosswalk,
        "manual_overrides": manual_overrides,
        "unmatched": unmatched_entries,
    }

    tmp_path = crosswalk_path.with_suffix(".tmp")
    try:
        crosswalk_path.parent.mkdir(parents=True, exist_ok=True)
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(crosswalk_data, f, indent=2, ensure_ascii=False)
        tmp_path.replace(crosswalk_path)
        logger.info(
            "Wrote crosswalk: %d mappings (%d auto, %d fuzzy, %d manual, %d unmatched)",
            len(crosswalk), auto_matched, fuzzy_matched,
            len(manual_overrides), len(unmatched_entries),
        )
    except Exception:
        if tmp_path.exists():
            tmp_path.unlink()
        raise

    return crosswalk


# ---------------------------------------------------------------------------
# Step 3: Fetch 119th Congress members from Congress.gov API
# ---------------------------------------------------------------------------

def format_member_name(member: dict, chamber: str, state_code: str) -> str:
    """Format a member's display name.

    Examples: "Sen. Lisa Murkowski (R-AK)", "Rep. Mary Peltola (D-AK-AL)"
    """
    name = member.get("name", "Unknown")
    # API returns "LastName, FirstName" -- convert to "FirstName LastName"
    if ", " in name:
        parts = name.split(", ", 1)
        name = f"{parts[1]} {parts[0]}"

    party_full = member.get("partyName", "")
    party = PARTY_ABBR.get(party_full, party_full[:1] if party_full else "?")

    prefix = "Sen." if chamber == "Senate" else "Rep."

    district = member.get("district")
    if chamber == "Senate" or district is None:
        return f"{prefix} {name} ({party}-{state_code})"
    else:
        dist_num = int(district)
        if dist_num == 0:
            dist_label = f"{state_code}-AL"
        else:
            dist_label = f"{state_code}-{dist_num:02d}"
        return f"{prefix} {name} ({party}-{dist_label})"


async def fetch_119th_members(
    session: aiohttp.ClientSession,
    api_key: str,
) -> dict[str, dict]:
    """Fetch all 119th Congress members from Congress.gov API.

    Returns dict keyed by bioguide_id.
    """
    headers = {"X-Api-Key": api_key}
    all_members: dict[str, dict] = {}
    offset = 0

    while True:
        url = (
            f"{CONGRESS_API_BASE}/member/congress/{CONGRESS_SESSION}"
            f"?limit=250&offset={offset}&currentMember=true"
        )
        logger.info("Fetching members: offset=%d", offset)

        try:
            async with session.get(
                url,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=60),
            ) as resp:
                if resp.status == 401:
                    logger.error("Congress.gov API: authentication failed (401)")
                    raise RuntimeError("Invalid CONGRESS_API_KEY")
                if resp.status == 429:
                    logger.warning("Rate limited (429). Waiting 60s...")
                    await asyncio.sleep(60)
                    continue
                resp.raise_for_status()
                data = await resp.json()
        except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
            logger.error("Congress.gov API error at offset %d: %s", offset, exc)
            raise

        members = data.get("members", [])
        if not members:
            break

        for m in members:
            bioguide_id = m.get("bioguideId", "")
            if not bioguide_id:
                continue

            # Determine chamber and state from latest term
            terms = m.get("terms", {})
            term_items = terms.get("item", []) if isinstance(terms, dict) else []
            latest_term = term_items[-1] if term_items else {}

            chamber = latest_term.get("chamber", "")
            if "Senate" in chamber:
                chamber = "Senate"
            elif "House" in chamber:
                chamber = "House"

            state_code = latest_term.get("stateCode", "")
            if not state_code:
                # Fallback: parse from state name
                state_full = m.get("state", "")
                # Try reverse FIPS lookup
                state_code = _state_name_to_abbr(state_full)

            district = m.get("district")

            formatted = format_member_name(m, chamber, state_code)

            member_record = {
                "bioguide_id": bioguide_id,
                "name": m.get("name", ""),
                "state": state_code,
                "district": district,
                "party": m.get("partyName", ""),
                "party_abbr": PARTY_ABBR.get(
                    m.get("partyName", ""), "?"
                ),
                "chamber": chamber,
                "formatted_name": formatted,
                "url": m.get("url", ""),
                "depiction_url": (
                    m.get("depiction", {}).get("imageUrl", "")
                    if m.get("depiction") else ""
                ),
                "office_address": "",
                "phone": "",
                "committees": [],
            }
            all_members[bioguide_id] = member_record

        logger.info(
            "Fetched %d members (total so far: %d)",
            len(members), len(all_members),
        )

        # Check for more pages
        pagination = data.get("pagination", {})
        next_url = pagination.get("next", "")
        if not next_url or len(members) < 250:
            break

        offset += 250
        await asyncio.sleep(0.3)

    logger.info("Total members fetched: %d", len(all_members))
    return all_members


# State name -> abbreviation helper
_STATE_NAME_MAP: dict[str, str] = {
    "alabama": "AL", "alaska": "AK", "arizona": "AZ", "arkansas": "AR",
    "california": "CA", "colorado": "CO", "connecticut": "CT",
    "delaware": "DE", "district of columbia": "DC", "florida": "FL",
    "georgia": "GA", "hawaii": "HI", "idaho": "ID", "illinois": "IL",
    "indiana": "IN", "iowa": "IA", "kansas": "KS", "kentucky": "KY",
    "louisiana": "LA", "maine": "ME", "maryland": "MD",
    "massachusetts": "MA", "michigan": "MI", "minnesota": "MN",
    "mississippi": "MS", "missouri": "MO", "montana": "MT",
    "nebraska": "NE", "nevada": "NV", "new hampshire": "NH",
    "new jersey": "NJ", "new mexico": "NM", "new york": "NY",
    "north carolina": "NC", "north dakota": "ND", "ohio": "OH",
    "oklahoma": "OK", "oregon": "OR", "pennsylvania": "PA",
    "rhode island": "RI", "south carolina": "SC", "south dakota": "SD",
    "tennessee": "TN", "texas": "TX", "utah": "UT", "vermont": "VT",
    "virginia": "VA", "washington": "WA", "west virginia": "WV",
    "wisconsin": "WI", "wyoming": "WY",
    # Territories
    "american samoa": "AS", "guam": "GU", "northern mariana islands": "MP",
    "puerto rico": "PR", "u.s. virgin islands": "VI",
    "virgin islands": "VI",
}


def _state_name_to_abbr(name: str) -> str:
    """Convert full state name to 2-letter abbreviation."""
    return _STATE_NAME_MAP.get(name.strip().lower(), "")


# ---------------------------------------------------------------------------
# Step 4: Load committee assignments from unitedstates YAML
# ---------------------------------------------------------------------------

async def fetch_committee_data(
    session: aiohttp.ClientSession,
) -> tuple[dict, dict]:
    """Download and parse committee membership and metadata YAML files.

    Returns (membership_data, committees_metadata).
    """
    membership_data: dict = {}
    committees_meta: dict = {}

    try:
        logger.info("Downloading committee-membership-current.yaml...")
        async with session.get(
            COMMITTEE_MEMBERSHIP_URL,
            timeout=aiohttp.ClientTimeout(total=60),
        ) as resp:
            resp.raise_for_status()
            text = await resp.text()
            membership_data = yaml.safe_load(text) or {}
            logger.info(
                "Loaded committee membership: %d committees",
                len(membership_data),
            )
    except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
        logger.warning("Failed to download committee membership YAML: %s", exc)

    try:
        logger.info("Downloading committees-current.yaml...")
        async with session.get(
            COMMITTEES_METADATA_URL,
            timeout=aiohttp.ClientTimeout(total=60),
        ) as resp:
            resp.raise_for_status()
            text = await resp.text()
            raw_committees = yaml.safe_load(text) or []
            # Transform list to dict keyed by thomas_id
            for comm in raw_committees:
                thomas_id = comm.get("thomas_id", "")
                if thomas_id:
                    committees_meta[thomas_id] = comm
                    # Also index subcommittees
                    for sub in comm.get("subcommittees", []):
                        sub_id = f"{thomas_id}{sub.get('thomas_id', '')}"
                        committees_meta[sub_id] = {
                            **sub,
                            "parent": thomas_id,
                            "parent_name": comm.get("name", ""),
                        }
            logger.info(
                "Loaded committee metadata: %d committees/subcommittees",
                len(committees_meta),
            )
    except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
        logger.warning("Failed to download committees metadata YAML: %s", exc)

    return membership_data, committees_meta


def build_committee_index(
    membership_data: dict,
    committees_meta: dict,
) -> tuple[dict, dict[str, list[dict]]]:
    """Build committee records and per-member committee assignment index.

    Returns (committees_dict, member_committees).
    - committees_dict: committee_id -> committee record with member list
    - member_committees: bioguide_id -> list of committee assignments
    """
    committees_dict: dict[str, dict] = {}
    member_committees: dict[str, list[dict]] = defaultdict(list)

    for comm_id, members_list in membership_data.items():
        if not isinstance(members_list, list):
            continue

        # Determine if this is a target committee or subcommittee thereof
        is_subcommittee = False
        for target in TARGET_COMMITTEES:
            if comm_id.startswith(target) and comm_id != target:
                is_subcommittee = True
                break

        # Check if this is a target committee or a subcommittee of one
        is_target = comm_id in TARGET_COMMITTEES or any(
            comm_id.startswith(t) and len(comm_id) > len(t)
            for t in TARGET_COMMITTEES
        )

        if not is_target:
            continue

        # Get committee metadata
        meta = committees_meta.get(comm_id, {})
        comm_name = meta.get("name", comm_id)
        chamber = ""
        if comm_id.startswith("S"):
            chamber = "senate"
        elif comm_id.startswith("H"):
            chamber = "house"

        comm_members: list[dict] = []
        for member_entry in members_list:
            bioguide = member_entry.get("bioguide", "")
            if not bioguide:
                continue

            role = "member"
            title = member_entry.get("title", "")
            if title:
                if "chairman" in title.lower() or "chair" in title.lower():
                    role = "chair"
                elif "ranking" in title.lower():
                    role = "ranking_member"
                elif "vice" in title.lower():
                    role = "vice_chair"

            member_record = {
                "bioguide_id": bioguide,
                "party_role": member_entry.get("party", ""),
                "rank": member_entry.get("rank", 0),
                "title": title,
                "role": role,
            }
            comm_members.append(member_record)

            # Index by bioguide for per-member lookup
            member_committees[bioguide].append({
                "committee_id": comm_id,
                "committee_name": comm_name,
                "role": role,
                "title": title,
                "rank": member_entry.get("rank", 0),
            })

        committees_dict[comm_id] = {
            "name": comm_name,
            "chamber": chamber,
            "parent": meta.get("parent", None) if is_subcommittee else None,
            "url": meta.get("url", ""),
            "members": comm_members,
        }

    logger.info(
        "Built committee index: %d target committees, %d member assignments",
        len(committees_dict),
        sum(len(v) for v in member_committees.values()),
    )
    return committees_dict, dict(member_committees)


# ---------------------------------------------------------------------------
# Step 5: Assemble per-Tribe delegations
# ---------------------------------------------------------------------------

def assemble_delegations(
    aiannh_districts: dict[str, list[dict]],
    crosswalk: dict[str, str],
    members: dict[str, dict],
    member_committees: dict[str, list[dict]],
) -> dict[str, dict]:
    """Assemble per-Tribe congressional delegation records.

    For each Tribe (via AIANNH crosswalk):
    1. Collect all congressional districts
    2. Find House representatives per district
    3. Find senators per state (deduplicated)
    4. Attach committee assignments
    """
    # Build lookup indexes from members
    # district -> list of House members
    district_reps: dict[str, list[dict]] = defaultdict(list)
    # state -> list of senators
    state_senators: dict[str, list[dict]] = defaultdict(list)

    for bioguide_id, member in members.items():
        chamber = member.get("chamber", "")
        state = member.get("state", "")

        if chamber == "Senate":
            state_senators[state].append(member)
        elif chamber == "House":
            dist = member.get("district")
            if dist is not None:
                dist_num = int(dist)
                if dist_num == 0:
                    dist_label = f"{state}-AL"
                else:
                    dist_label = f"{state}-{dist_num:02d}"
                district_reps[dist_label].append(member)

    # Group AIANNH entities by tribe_id
    tribe_aiannh: dict[str, list[str]] = defaultdict(list)
    for geoid, tribe_id in crosswalk.items():
        tribe_aiannh[tribe_id].append(geoid)

    delegations: dict[str, dict] = {}

    for tribe_id, geoids in tribe_aiannh.items():
        # Collect all districts from all AIANNH entities for this tribe
        all_districts: list[dict] = []
        seen_districts: set[str] = set()

        for geoid in geoids:
            for dist_rec in aiannh_districts.get(geoid, []):
                dist_key = dist_rec["district"]
                if dist_key not in seen_districts:
                    seen_districts.add(dist_key)
                    all_districts.append({
                        "district": dist_key,
                        "state": dist_rec["state"],
                        "aiannh_name": dist_rec["aiannh_name"],
                        "overlap_pct": dist_rec["overlap_pct"],
                    })

        if not all_districts:
            continue

        # Sort districts by overlap_pct descending
        all_districts.sort(key=lambda d: d["overlap_pct"], reverse=True)

        # Collect unique states
        states = sorted(set(d["state"] for d in all_districts))

        # Find representatives for each district
        representatives: list[dict] = []
        seen_reps: set[str] = set()
        for dist_rec in all_districts:
            for rep in district_reps.get(dist_rec["district"], []):
                if rep["bioguide_id"] not in seen_reps:
                    seen_reps.add(rep["bioguide_id"])
                    rep_copy = dict(rep)
                    rep_copy["committees"] = member_committees.get(
                        rep["bioguide_id"], []
                    )
                    representatives.append(rep_copy)

        # Find senators for each state (deduplicated per state)
        senators: list[dict] = []
        seen_senators: set[str] = set()
        for state in states:
            for sen in state_senators.get(state, []):
                if sen["bioguide_id"] not in seen_senators:
                    seen_senators.add(sen["bioguide_id"])
                    sen_copy = dict(sen)
                    sen_copy["committees"] = member_committees.get(
                        sen["bioguide_id"], []
                    )
                    senators.append(sen_copy)

        delegations[tribe_id] = {
            "tribe_id": tribe_id,
            "districts": all_districts,
            "states": states,
            "senators": senators,
            "representatives": representatives,
        }

    logger.info(
        "Assembled delegations: %d tribes with delegation data",
        len(delegations),
    )
    return delegations


# ---------------------------------------------------------------------------
# Step 6: Write congressional_cache.json (atomic write)
# ---------------------------------------------------------------------------

def write_cache(
    output_path: Path,
    members: dict[str, dict],
    committees: dict[str, dict],
    delegations: dict[str, dict],
    *,
    placeholder: bool = False,
    census_only: bool = False,
) -> None:
    """Write the assembled congressional cache to JSON (atomic write)."""
    cache = {
        "metadata": {
            "congress_session": CONGRESS_SESSION,
            "built_at": datetime.now(timezone.utc).isoformat(),
            "total_members": len(members),
            "total_committees": len(committees),
            "total_tribes_mapped": len(delegations),
            "census_source": "tab20_cd11920_aiannh20_natl.txt",
            "committee_source": "unitedstates/congress-legislators",
            "placeholder": placeholder,
            "census_only": census_only,
        },
        "members": members,
        "committees": committees,
        "delegations": delegations,
    }

    tmp_path = output_path.with_suffix(".tmp")
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(cache, f, indent=2, ensure_ascii=False)
        tmp_path.replace(output_path)
        logger.info(
            "Wrote congressional cache: %d members, %d committees, "
            "%d tribe delegations -> %s",
            len(members), len(committees), len(delegations), output_path,
        )
    except Exception:
        if tmp_path.exists():
            tmp_path.unlink()
        raise


# ---------------------------------------------------------------------------
# Main build pipeline
# ---------------------------------------------------------------------------

async def main() -> None:
    """Run the full congressional cache build pipeline."""
    parser = argparse.ArgumentParser(
        description="Build congressional_cache.json from Census + Congress.gov + YAML",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=CONGRESSIONAL_CACHE_PATH,
        help=f"Output cache file path (default: {CONGRESSIONAL_CACHE_PATH})",
    )
    parser.add_argument(
        "--crosswalk-output",
        type=Path,
        default=AIANNH_CROSSWALK_PATH,
        help=f"Output crosswalk file path (default: {AIANNH_CROSSWALK_PATH})",
    )
    parser.add_argument(
        "--registry-path",
        type=Path,
        default=TRIBAL_REGISTRY_PATH,
        help=f"Path to tribal_registry.json for crosswalk matching (default: {TRIBAL_REGISTRY_PATH})",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable debug logging",
    )
    parser.add_argument(
        "--skip-api",
        action="store_true",
        help="Skip Congress.gov API and YAML downloads (Census-only mode)",
    )
    args = parser.parse_args()

    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    output_path = args.output.resolve()
    crosswalk_path = args.crosswalk_output.resolve()
    registry_path = args.registry_path.resolve()
    logger.info("Output: %s", output_path)
    logger.info("Crosswalk: %s", crosswalk_path)
    logger.info("Skip API: %s", args.skip_api)

    # Check API key
    api_key = os.environ.get("CONGRESS_API_KEY", "")
    if not api_key and not args.skip_api:
        logger.warning(
            "CONGRESS_API_KEY not set. Use --skip-api for Census-only mode."
        )
        logger.info("Falling back to --skip-api mode.")
        args.skip_api = True

    async with aiohttp.ClientSession() as session:
        # Step 0: Download Census file
        try:
            census_path = await download_census_file(session)
        except Exception as exc:
            logger.error("Census file download failed: %s", exc)
            logger.error(
                "Cannot proceed without Census data. "
                "Manually download from %s to %s",
                CENSUS_URL, CENSUS_LOCAL_PATH,
            )
            sys.exit(1)

        # Step 1: Parse Census file
        aiannh_districts = parse_census_cd119_aiannh(census_path)

        # Step 2: Build crosswalk
        crosswalk = build_crosswalk(
            aiannh_districts, registry_path, crosswalk_path,
        )

        # Step 3: Fetch Congress members (or skip)
        members: dict[str, dict] = {}
        if not args.skip_api:
            try:
                members = await fetch_119th_members(session, api_key)
            except Exception as exc:
                logger.error("Congress.gov API fetch failed: %s", exc)
                logger.info("Continuing with Census-only data...")
        else:
            logger.info("Skipping Congress.gov API (--skip-api mode)")

        # Step 4: Fetch committee assignments (or skip)
        committees: dict[str, dict] = {}
        member_committees: dict[str, list[dict]] = {}
        if not args.skip_api:
            try:
                membership_data, committees_meta = await fetch_committee_data(
                    session,
                )
                committees, member_committees = build_committee_index(
                    membership_data, committees_meta,
                )
                # Merge committee assignments into member records
                for bioguide_id, comms in member_committees.items():
                    if bioguide_id in members:
                        members[bioguide_id]["committees"] = comms
            except Exception as exc:
                logger.warning("Committee data fetch failed: %s", exc)
        else:
            logger.info("Skipping committee data (--skip-api mode)")

        # Step 5: Assemble delegations
        delegations = assemble_delegations(
            aiannh_districts, crosswalk, members, member_committees,
        )

        # Step 6: Write cache
        write_cache(
            output_path,
            members,
            committees,
            delegations,
            census_only=args.skip_api,
        )

    logger.info("Congressional cache build complete.")


if __name__ == "__main__":
    asyncio.run(main())
