"""Build tribal_registry.json from EPA Tribes Names Service API.

One-time script that fetches all ~574 federally recognized Tribes from the
EPA Tribes Names Service API and writes a standardized JSON registry to
data/tribal_registry.json.

Usage:
    python scripts/build_registry.py                   # Default output
    python scripts/build_registry.py --verbose          # Debug logging
    python scripts/build_registry.py --output path.json # Custom path
"""

import argparse
import asyncio
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

import aiohttp

logger = logging.getLogger("tcr_scanner.build_registry")

# EPA Tribes Names Service API
EPA_API_URL = (
    "https://cdxapi.epa.gov/oms-tribes-rest-services/api/v1/tribeDetails"
)
EPA_PARAMS = {"tribalBandFilter": "AllTribes"}

# Retry configuration
MAX_RETRIES = 2
RETRY_DELAY_SECONDS = 5

# Expected counts for validation
MIN_EXPECTED_TRIBES = 570
EXPECTED_LUMBEE_NAME = "Lumbee"

# State name -> abbreviation mapping for state extraction from tribe names
STATE_NAME_TO_ABBR: dict[str, str] = {
    "alabama": "AL", "alaska": "AK", "arizona": "AZ", "arkansas": "AR",
    "california": "CA", "colorado": "CO", "connecticut": "CT",
    "delaware": "DE", "florida": "FL", "georgia": "GA", "hawaii": "HI",
    "idaho": "ID", "illinois": "IL", "indiana": "IN", "iowa": "IA",
    "kansas": "KS", "kentucky": "KY", "louisiana": "LA", "maine": "ME",
    "maryland": "MD", "massachusetts": "MA", "michigan": "MI",
    "minnesota": "MN", "mississippi": "MS", "missouri": "MO",
    "montana": "MT", "nebraska": "NE", "nevada": "NV",
    "new hampshire": "NH", "new jersey": "NJ", "new mexico": "NM",
    "new york": "NY", "north carolina": "NC", "north dakota": "ND",
    "ohio": "OH", "oklahoma": "OK", "oregon": "OR", "pennsylvania": "PA",
    "rhode island": "RI", "south carolina": "SC", "south dakota": "SD",
    "tennessee": "TN", "texas": "TX", "utah": "UT", "vermont": "VT",
    "virginia": "VA", "washington": "WA", "west virginia": "WV",
    "wisconsin": "WI", "wyoming": "WY",
}


def extract_states(record: dict) -> list[str]:
    """Extract state abbreviations from EPA record.

    Uses the epaLocations array (preferred, structured data) with fallback
    to parsing state names from the tribe name field.
    """
    states: list[str] = []
    seen: set[str] = set()

    # Primary: structured epaLocations array
    locations = record.get("epaLocations") or []
    for loc in locations:
        code = (loc.get("stateCode") or "").strip().upper()
        if code and len(code) == 2 and code not in seen:
            states.append(code)
            seen.add(code)

    # If we got states from structured data, use those
    if states:
        return sorted(states)

    # Fallback: parse state names from the tribe name after the last comma group
    # e.g. "Navajo Nation, Arizona, New Mexico, & Utah" -> ["AZ", "NM", "UT"]
    name = record.get("currentName") or ""
    # Split on commas and "&" to find state name candidates
    parts = name.replace("&", ",").split(",")
    for part in parts:
        candidate = part.strip().lower()
        if candidate in STATE_NAME_TO_ABBR:
            abbr = STATE_NAME_TO_ABBR[candidate]
            if abbr not in seen:
                states.append(abbr)
                seen.add(abbr)

    return sorted(states)


def extract_alternate_names(record: dict) -> list[str]:
    """Extract historical and alternate name variants for search corpus.

    Pulls from the names[] array in tribeDetails response. Both current
    and historical names are included for fuzzy matching.
    """
    alternates: list[str] = []
    seen: set[str] = set()
    current_name = (record.get("currentName") or "").strip()

    names_list = record.get("names") or []
    for entry in names_list:
        name = (entry.get("name") or "").strip()
        if name and name != current_name and name.lower() not in seen:
            alternates.append(name)
            seen.add(name.lower())

    return alternates


def extract_epa_region(record: dict) -> str:
    """Extract EPA region number from epaLocations.

    For multi-state tribes, returns the first (lead) region.
    """
    locations = record.get("epaLocations") or []
    for loc in locations:
        region_name = loc.get("epaRegionName") or ""
        # Format: "Region 9" -> "9"
        if region_name.startswith("Region "):
            return region_name.replace("Region ", "").strip()
    return ""


def transform_record(record: dict) -> dict:
    """Transform an EPA API record into a standardized Tribe object."""
    epa_id = record.get("epaTribalInternalId")
    if epa_id is None:
        raise ValueError(f"Record missing epaTribalInternalId: {record}")

    return {
        "tribe_id": f"epa_{epa_id}",
        "bia_code": (record.get("currentBIATribalCode") or "").strip(),
        "name": (record.get("currentName") or "").strip(),
        "states": extract_states(record),
        "alternate_names": extract_alternate_names(record),
        "epa_region": extract_epa_region(record),
        "tribal_band_flag": (record.get("tribalBandFlag") or "").strip(),
        "bia_recognized": record.get("currentBIARecognizedFlag", False),
    }


async def fetch_tribes(session: aiohttp.ClientSession) -> list[dict]:
    """Fetch all tribes from EPA API with retry logic."""
    last_error = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            logger.info(
                "Fetching tribes from EPA API (attempt %d/%d)...",
                attempt, MAX_RETRIES,
            )
            async with session.get(
                EPA_API_URL,
                params=EPA_PARAMS,
                timeout=aiohttp.ClientTimeout(total=60),
            ) as resp:
                resp.raise_for_status()
                # EPA API returns text/plain content type instead of
                # application/json, so we read as text and parse manually
                text = await resp.text(encoding="utf-8")
                data = json.loads(text)

                if not isinstance(data, list):
                    raise ValueError(
                        f"Expected JSON array, got {type(data).__name__}"
                    )

                logger.info("Received %d tribe records from EPA API", len(data))
                return data

        except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as exc:
            last_error = exc
            logger.warning(
                "EPA API attempt %d failed: %s", attempt, exc,
            )
            if attempt < MAX_RETRIES:
                logger.info("Retrying in %d seconds...", RETRY_DELAY_SECONDS)
                await asyncio.sleep(RETRY_DELAY_SECONDS)

    raise RuntimeError(
        f"EPA API unreachable after {MAX_RETRIES} attempts: {last_error}"
    )


def validate_tribes(tribes: list[dict]) -> None:
    """Validate the transformed tribe records."""
    # Check for duplicate tribe_id values
    ids = [t["tribe_id"] for t in tribes]
    duplicates = [tid for tid in ids if ids.count(tid) > 1]
    if duplicates:
        unique_dupes = sorted(set(duplicates))
        raise ValueError(f"Duplicate tribe_id values found: {unique_dupes}")

    # Count and log BIA TBD entries (expected: ~230 for Alaska)
    tbd_count = sum(1 for t in tribes if t["bia_code"] == "TBD")
    logger.info(
        "BIA code 'TBD' count: %d (expected ~230 for Alaska Native entities)",
        tbd_count,
    )

    # Warn if total count is low
    if len(tribes) < MIN_EXPECTED_TRIBES:
        logger.warning(
            "Only %d tribes found (expected >= %d). "
            "Check tribalBandFilter=AllTribes parameter.",
            len(tribes), MIN_EXPECTED_TRIBES,
        )

    # Check for Lumbee Tribe (recently added, may not be in EPA data yet)
    lumbee_found = any(
        EXPECTED_LUMBEE_NAME.lower() in t["name"].lower() for t in tribes
    )
    if not lumbee_found:
        logger.warning(
            "Lumbee Tribe (Federal Register 2026-01899) not found in EPA "
            "Tribes Names Service. Will be added when EPA updates its database."
        )
    else:
        logger.info("Lumbee Tribe found in EPA data.")


def write_registry(tribes: list[dict], output_path: Path, metadata: dict) -> None:
    """Write tribal registry JSON using atomic write pattern."""
    registry = {
        "metadata": metadata,
        "tribes": tribes,
    }

    # Atomic write: write to temp file, then replace
    tmp_path = output_path.with_suffix(".tmp")
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(registry, f, indent=2, ensure_ascii=False)
        tmp_path.replace(output_path)
        logger.info("Wrote %d tribes to %s", len(tribes), output_path)
    except Exception:
        # Clean up temp file on failure
        if tmp_path.exists():
            tmp_path.unlink()
        raise


def build_placeholder(output_path: Path) -> None:
    """Create a minimal placeholder registry for offline development.

    Used when the EPA API is unreachable (network issues). Contains 5
    representative Tribe entries with the correct schema.
    """
    logger.warning(
        "EPA API unreachable. Creating placeholder tribal_registry.json. "
        "Run 'python scripts/build_registry.py' when connectivity is restored."
    )

    placeholder_tribes = [
        {
            "tribe_id": "epa_100000171",
            "bia_code": "780",
            "name": "Navajo Nation, Arizona, New Mexico, & Utah",
            "states": ["AZ", "NM", "UT"],
            "alternate_names": [
                "Navajo Tribe of Arizona, New Mexico & Utah",
                "Navajo Nation of Arizona, New Mexico & Utah",
            ],
            "epa_region": "9",
            "tribal_band_flag": "",
            "bia_recognized": True,
        },
        {
            "tribe_id": "epa_100000047",
            "bia_code": "400",
            "name": "Cherokee Nation",
            "states": ["OK"],
            "alternate_names": ["Cherokee Nation of Oklahoma"],
            "epa_region": "6",
            "tribal_band_flag": "",
            "bia_recognized": True,
        },
        {
            "tribe_id": "epa_100000050",
            "bia_code": "TBD",
            "name": "Central Council of the Tlingit & Haida Indian Tribes",
            "states": ["AK"],
            "alternate_names": [
                "Central Council of Tlingit and Haida Indian Tribes of Alaska",
            ],
            "epa_region": "10",
            "tribal_band_flag": "",
            "bia_recognized": True,
        },
        {
            "tribe_id": "epa_100000231",
            "bia_code": "545",
            "name": "Seminole Tribe of Florida",
            "states": ["FL"],
            "alternate_names": ["Seminole Tribe of Florida, (Dania, Big Cypress, Brighton, Hollywood & Tampa Reservations)"],
            "epa_region": "4",
            "tribal_band_flag": "",
            "bia_recognized": True,
        },
        {
            "tribe_id": "epa_100000052",
            "bia_code": "409",
            "name": "Choctaw Nation of Oklahoma",
            "states": ["OK"],
            "alternate_names": [],
            "epa_region": "6",
            "tribal_band_flag": "",
            "bia_recognized": True,
        },
    ]

    now = datetime.now(timezone.utc).isoformat()
    metadata = {
        "source": "EPA Tribes Names Service API",
        "source_url": EPA_API_URL,
        "fetched_at": now,
        "total_tribes": len(placeholder_tribes),
        "bia_tbd_count": 1,
        "version": "1.0",
        "placeholder": True,
    }

    write_registry(placeholder_tribes, output_path, metadata)
    logger.warning(
        "Placeholder registry created with %d representative tribes. "
        "Replace by running build_registry.py when API is available.",
        len(placeholder_tribes),
    )


async def main() -> None:
    """Fetch all tribes from EPA API and build tribal_registry.json."""
    parser = argparse.ArgumentParser(
        description="Build tribal_registry.json from EPA Tribes Names Service API",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/tribal_registry.json"),
        help="Output file path (default: data/tribal_registry.json)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable debug logging",
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
    logger.info("Output path: %s", output_path)

    try:
        async with aiohttp.ClientSession() as session:
            raw_records = await fetch_tribes(session)

        # Transform records
        tribes = []
        transform_errors = 0
        for record in raw_records:
            try:
                tribes.append(transform_record(record))
            except (ValueError, KeyError) as exc:
                transform_errors += 1
                logger.warning("Skipping malformed record: %s", exc)

        if transform_errors:
            logger.warning(
                "%d records skipped due to transformation errors",
                transform_errors,
            )

        # Validate
        validate_tribes(tribes)

        # Build metadata
        now = datetime.now(timezone.utc).isoformat()
        tbd_count = sum(1 for t in tribes if t["bia_code"] == "TBD")
        metadata = {
            "source": "EPA Tribes Names Service API",
            "source_url": EPA_API_URL,
            "fetched_at": now,
            "total_tribes": len(tribes),
            "bia_tbd_count": tbd_count,
            "version": "1.0",
        }

        # Write output
        write_registry(tribes, output_path, metadata)

        logger.info(
            "Registry build complete: %d tribes, %d with BIA code TBD",
            len(tribes), tbd_count,
        )

    except RuntimeError as exc:
        logger.error("API fetch failed: %s", exc)
        logger.info("Falling back to placeholder registry...")
        build_placeholder(output_path)


if __name__ == "__main__":
    asyncio.run(main())
