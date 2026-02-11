#!/usr/bin/env python3
"""Generate data/housing_authority_aliases.json from tribal_registry.json.

Creates housing authority -> tribe_id mappings using:
1. Programmatic patterns from registry short names
2. Curated overrides for known USASpending edge cases
3. Explicit exclusions for regional/multi-Tribe authorities

Usage:
    python scripts/generate_ha_aliases.py
"""

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPT_DIR.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.paths import TRIBAL_REGISTRY_PATH

OUTPUT_PATH = TRIBAL_REGISTRY_PATH.parent / "housing_authority_aliases.json"

US_STATES = {
    "alabama", "alaska", "arizona", "arkansas", "california", "colorado",
    "connecticut", "delaware", "florida", "georgia", "hawaii", "idaho",
    "illinois", "indiana", "iowa", "kansas", "kentucky", "louisiana",
    "maine", "maryland", "massachusetts", "michigan", "minnesota",
    "mississippi", "missouri", "montana", "nebraska", "nevada",
    "new hampshire", "new jersey", "new mexico", "new york",
    "north carolina", "north dakota", "ohio", "oklahoma", "oregon",
    "pennsylvania", "rhode island", "south carolina", "south dakota",
    "tennessee", "texas", "utah", "vermont", "virginia", "washington",
    "west virginia", "wisconsin", "wyoming",
}

# Common suffixes to strip for shorter name variants
_STRIP_SUFFIXES = [
    " nation", " tribe", " band", " community", " council",
    " indians", " indian tribe", " indian community",
    " of indians", " reservation",
]

# Housing authority name patterns to generate for each short name
_HA_PATTERNS = [
    "{name} housing authority",
    "housing authority of {name}",
    "{name} housing program",
    "{name} housing local development",
    "{name} tribal housing authority",
]

# Regional or multi-Tribe authorities that should NOT be in the alias table
_EXCLUDED = [
    "mowa choctaw housing authority",
    "chippewa housing authority",
    "cook inlet housing authority",
    "interior regional housing authority",
    "bering straits regional housing authority",
    "bristol bay housing authority",
    "northwest inupiat housing authority",
    "northern circle indian housing authority",
    "tagiugmiullu nunamiullu housing authority",
    "north pacific rim housing authority",
    "copper river housing authority",
    "all mission indian housing authority",
    "new york state thruway authority",
    "lumbee land development, inc",
    "lumbee land development inc",
    "kodiak island housing authority",
    "kawerak, inc.",
    "kawerak inc",
    "kawerak inc.",
    "aleutian housing authority",
]

# Curated overrides for names that cannot be derived programmatically
_CURATED = {
    # Navajo variants (USASpending drops "Nation")
    "navajo housing authority": "epa_100000171",
    "navajo nation tribal government": "epa_100000171",
    "navajo tribal government": "epa_100000171",
    # Choctaw "Nations" (plural) vs registry "Nation" (singular)
    "housing authority of choctaw nations": "epa_100000045",
    "choctaw nations housing authority": "epa_100000045",
    # Oglala Lakota (Lakota is the preferred self-designation)
    "oglala lakota housing authority": "epa_100000179",
    "oglala lakota housing": "epa_100000179",
    "oglala housing authority": "epa_100000179",
    # Tohono O'odham Ki Ki Association (unique HUD-era name)
    "tohono o\u2019odham ki ki association": "epa_100000302",
    "tohono o'odham ki ki association": "epa_100000302",
    "tohono o odham ki ki association": "epa_100000302",
    # White Mountain Apache (short form)
    "white mountain apache housing authority": "epa_100000324",
    # Hopi "Tribal" Housing Authority (Tribal instead of Tribe)
    "hopi tribal housing authority": "epa_100000104",
    # Turtle Mountain (shortened, dropping "Band of Chippewa Indians")
    "turtle mountain housing authority": "epa_100000311",
    # Tlingit Haida Regional - attributable to Central Council
    "tlingit haida regional housing authority": "epa_100000551",
    "tlingit-haida regional housing authority": "epa_100000551",
    # Sicangu Wicoti (Rosebud Sioux Tribe's Lakota name)
    "sicangu wicoti awayankape corporation": "epa_100000244",
    "sicangu wicoti awayankapi corporation": "epa_100000244",
    # Blackfeet "program" not "authority"
    "blackfeet housing program": "epa_100000020",
    "blackfeet housing": "epa_100000020",
    # San Carlos (short form)
    "san carlos housing authority": "epa_100000254",
    "san carlos apache housing authority": "epa_100000254",
    # Yakama Nation
    "yakama nation housing authority": "epa_100000062",
    "yakama housing authority": "epa_100000062",
    # Cheyenne River
    "cheyenne river housing authority": "epa_100000040",
    "cheyenne river sioux housing authority": "epa_100000040",
    # Umatilla Indian Reservation (just reservation name)
    "umatilla indian reservation": "epa_100000060",
    # Standing Rock
    "standing rock housing local development": "epa_100000289",
    "standing rock housing authority": "epa_100000289",
    # Direct name variants (not housing authorities)
    "crow tribe of indians": "epa_100000069",
    "united keetoowah band of cherokee": "epa_100000315",
    "orutsararmuit native council, incorporated": "epa_100000496",
    "orutsararmuit native council incorporated": "epa_100000496",
    "orutsararmuit native council": "epa_100000496",
    # Truncated names from USASpending
    "tule river indian housing auth": "epa_100000307",
    "sac & fox housing authority inc": "epa_100000248",
    "sac and fox housing authority": "epa_100000248",
    "sac & fox housing authority": "epa_100000248",
    # --- Round 2 curated overrides (from 433/592 top_unmatched) ---
    # Red Lake (USASpending uses "Reservation Housing" not band name)
    "red lake reservation housing": "epa_100000237",
    "red lake housing authority": "epa_100000237",
    # Colville (USASpending uses "Indian Housing Authority")
    "colville indian housing authority": "epa_100000055",
    "colville housing authority": "epa_100000055",
    # Yurok (USASpending uses "Indian Housing Authority")
    "yurok indian housing authority": "epa_100000338",
    "yurok housing authority": "epa_100000338",
    # Fort Peck (Assiniboine and Sioux Tribes)
    "fort peck housing authority": "epa_100000010",
    "fort peck tribes housing authority": "epa_100000010",
    # Sault Ste. Marie (USASpending uses "Sault Tribe")
    "sault tribe housing authority": "epa_100000263",
    "sault ste. marie tribe housing authority": "epa_100000263",
    "sault ste marie tribe housing authority": "epa_100000263",
    # Salish & Kootenai (ampersand variant)
    "salish & kootenai housing authority": "epa_100000053",
    "salish and kootenai housing authority": "epa_100000053",
    # Fond du Lac (USASpending uses just "Reservation")
    "fond du lac reservation": "epa_100000572",
    "fond du lac housing authority": "epa_100000572",
    "fond du lac band housing authority": "epa_100000572",
    # Ho-Chunk (USASpending uses "Housing & Community Development Agency")
    "ho-chunk housing & community development agency": "epa_100000101",
    "ho-chunk housing and community development agency": "epa_100000101",
    "ho-chunk housing authority": "epa_100000101",
    # Leech Lake (USASpending uses "Ojibwe" not registry "Chippewa")
    "leech lake band of ojibwe housing authority": "epa_100000574",
    "leech lake housing authority": "epa_100000574",
    "leech lake band housing authority": "epa_100000574",
    # Confederated Tribes of Siletz (USASpending truncates "of")
    "confederated tribes siletz indians": "epa_100000059",
    "confederated tribes of siletz indians": "epa_100000059",
    "siletz housing authority": "epa_100000059",
    # --- Round 3 curated overrides (from 439/592 top_unmatched) ---
    # Fort Berthold (Three Affiliated Tribes)
    "fort berthold housing authority inc": "epa_100000301",
    "fort berthold housing authority": "epa_100000301",
    # Sisseton-Wahpeton (Oyate dropped in USASpending)
    "sisseton-wahpeton housing authority": "epa_100000278",
    "sisseton wahpeton housing authority": "epa_100000278",
    # Lummi Nation Housing Authority
    "lummi nation housing authority": "epa_100000146",
    "lummi housing authority": "epa_100000146",
    # Shoshone Bannock (direct Tribe name in USASpending)
    "shoshone bannock tribes": "epa_100000276",
    "shoshone-bannock tribes": "epa_100000276",
    "shoshone bannock housing authority": "epa_100000276",
    # Round Valley Indian Housing Authority
    "round valley indian housing authority": "epa_100000245",
    "round valley housing authority": "epa_100000245",
    # Ho-Chunk Nation Transportation Authority (different entity type)
    "ho-chunk nation transportation authority": "epa_100000101",
    # White Earth Reservation Housing (component of MN Chippewa)
    "white earth reservation housing authority": "epa_100000161",
    "white earth housing authority": "epa_100000161",
    # Spokane Indian Housing Authority
    "spokane indian housing authority": "epa_100000287",
    "spokane housing authority": "epa_100000287",
    # Colorado River Residential Management Corporation (unique name)
    "colorado river residential management corporation": "epa_100000051",
    "colorado river indian tribes housing authority": "epa_100000051",
    # --- Round 4 curated overrides (from 444/592 top_unmatched) ---
    # DOI TRB WA UPPER SKAGIT (USASpending BIA prefix)
    "doi trb wa upper skagit indian tribe": "epa_100000317",
    # Apsaalooke Nation (Crow Tribe's self-designation)
    "apsaalooke nation housing authority": "epa_100000069",
    "apsaalooke housing authority": "epa_100000069",
    "apsaalooke nation": "epa_100000069",
    # Absentee Shawnee (USASpending uses full name with "of Indians of Oklahoma")
    "housing authority of the absentee shawnee tribe of indians of oklahoma": "epa_100000001",
    "absentee shawnee housing authority": "epa_100000001",
    "absentee-shawnee housing authority": "epa_100000001",
    # Pokagon Band (USASpending drops "Indians, Michigan and Indiana")
    "pokagon band of potawatomi": "epa_100000205",
    "pokagon band housing authority": "epa_100000205",
    # Spirit Lake Housing Corp (uses "Corp" not "Authority")
    "spirit lake housing corp": "epa_100000286",
    "spirit lake housing corporation": "epa_100000286",
    "spirit lake housing authority": "epa_100000286",
    # Confederated Tribes of Grand Ronde (USASpending drops "Community of Oregon")
    "confederated tribes of grand ronde": "epa_100000058",
    "grand ronde housing authority": "epa_100000058",
    # Duck Valley Housing Authority (Shoshone-Paiute)
    "duck valley housing authority": "epa_100000277",
    # Yurok Tribe (USASpending uses short form without reservation)
    "yurok tribe": "epa_100000338",
    # Pine Ridge Housing Authority (Oglala Sioux)
    "pine ridge housing authority": "epa_100000179",
    # Mille Lacs Band Housing (component of MN Chippewa)
    "mille lacs band housing authority": "epa_100000161",
    "mille lacs housing authority": "epa_100000161",
    # --- Round 5 curated overrides (from 448/592, need 2 more) ---
    # San Carlos Apache Tribal Council (USASpending uses "Tribal Council")
    "san carlos apache tribal council": "epa_100000254",
    # Bois Forte Reservation Tribal Council (component of MN Chippewa)
    "bois forte reservation tribal council": "epa_100000161",
    "bois forte housing authority": "epa_100000161",
    # Puyallup Tribe of Indians (USASpending drops "Reservation")
    "puyallup tribe of indians": "epa_100000228",
    "puyallup housing authority": "epa_100000228",
    # Penobscot Indian Nation
    "penobscot indian nation": "epa_100000199",
    "penobscot housing authority": "epa_100000199",
    # Northern Ponca Housing Authority (Ponca Tribe of Nebraska)
    "northern ponca housing authority": "epa_100000207",
    "ponca tribe of nebraska housing authority": "epa_100000207",
    # Cheyenne and Arapaho Housing Authority
    "cheyenne and arapaho housing authority": "epa_100000039",
    "cheyenne & arapaho housing authority": "epa_100000039",
    # Navajo Engineering & Construction Authority
    "navajo engineering & construction authority": "epa_100000171",
    "navajo engineering and construction authority": "epa_100000171",
}


def _strip_state_suffixes(name: str) -> str:
    """Strip trailing state name(s) from a tribe name."""
    for state in sorted(US_STATES, key=len, reverse=True):
        pattern = rf",\s*{re.escape(state)}\s*$"
        new = re.sub(pattern, "", name, flags=re.IGNORECASE).strip()
        if new != name:
            return new
    comma_idx = name.find(",")
    if comma_idx > 0:
        prefix = name[:comma_idx].strip()
        suffix = name[comma_idx + 1 :].strip()
        cleaned = suffix.replace("&", " ").replace(",", " ").replace(" and ", " ")
        tokens = [t for t in cleaned.split() if t]
        i = 0
        all_states = bool(tokens)
        while i < len(tokens):
            if (
                i + 1 < len(tokens)
                and f"{tokens[i]} {tokens[i + 1]}".lower() in US_STATES
            ):
                i += 2
            elif tokens[i].lower() in US_STATES:
                i += 1
            else:
                all_states = False
                break
        if all_states and prefix:
            return prefix
    return name


def _get_short_names(name: str) -> set[str]:
    """Derive all useful short name variants for HA pattern generation."""
    variants: set[str] = set()
    name_lower = name.lower().strip()
    variants.add(name_lower)

    # State-stripped
    stripped = _strip_state_suffixes(name_lower)
    if stripped != name_lower:
        variants.add(stripped)

    # Strip "the " prefix
    for v in list(variants):
        if v.startswith("the "):
            variants.add(v[4:].strip())

    # Strip parenthetical content
    for v in list(variants):
        if "(" in v:
            no_parens = re.sub(r"\([^)]+\)\s*", "", v).strip()
            no_parens = re.sub(r"\s+", " ", no_parens)
            if no_parens:
                variants.add(no_parens)
            exposed = re.sub(r"\(([^)]+)\)", r"\1", v)
            exposed = re.sub(r"\s+", " ", exposed).strip()
            if exposed:
                variants.add(exposed)

    # Strip "of the X" / "of X" prefixes
    for v in list(variants):
        of_match = re.match(r"^(.+?)\s+of\s+(the\s+)?", v)
        if of_match:
            short = of_match.group(1).strip()
            if len(short) > 5:
                variants.add(short)

    # Strip common entity-type suffixes for even shorter names
    for v in list(variants):
        for suffix in _STRIP_SUFFIXES:
            if v.endswith(suffix):
                shorter = v[: -len(suffix)].strip().rstrip(",")
                if len(shorter) >= 4:
                    variants.add(shorter)

    return variants


def main() -> None:
    """Generate housing authority aliases and write to JSON."""
    with open(TRIBAL_REGISTRY_PATH, "r", encoding="utf-8") as f:
        registry = json.load(f)

    aliases: dict[str, str] = {}
    tribes = registry.get("tribes", [])

    # Step 1: Programmatic generation from registry
    for tribe in tribes:
        tid = tribe["tribe_id"]
        official_name = tribe["name"]
        all_names = [official_name] + tribe.get("alternate_names", [])

        for raw_name in all_names:
            short_names = _get_short_names(raw_name)
            for sn in short_names:
                for pattern in _HA_PATTERNS:
                    key = pattern.format(name=sn)
                    if key not in aliases:
                        aliases[key] = tid

    # Step 2: Remove excluded regional/multi-Tribe entries
    for key in _EXCLUDED:
        aliases.pop(key, None)

    # Step 3: Add curated overrides (override programmatic if different)
    for key, val in _CURATED.items():
        aliases[key] = val

    # Write output
    data = {
        "_metadata": {
            "description": (
                "Housing authority recipient names mapped to parent "
                "Tribe IDs for USASpending award matching"
            ),
            "version": "1.1",
            "last_updated": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "source": (
                "Programmatic generation from tribal_registry.json "
                "+ manual curation from award_population_report.json"
            ),
            "total_aliases": len(aliases),
            "skipped_regional": _EXCLUDED,
        },
        "aliases": dict(sorted(aliases.items())),
    }

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"Generated {len(aliases)} housing authority aliases -> {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
