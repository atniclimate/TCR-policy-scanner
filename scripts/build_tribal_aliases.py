#!/usr/bin/env python3
"""Build the curated tribal alias table from tribal_registry.json.

Generates data/tribal_aliases.json with lowercased name -> tribe_id
mappings for all official names, alternate names, and common
USASpending naming patterns.

Usage:
    python scripts/build_tribal_aliases.py
"""

import json
import re
from datetime import datetime, timezone
from pathlib import Path

REGISTRY_PATH = Path("data/tribal_registry.json")
OUTPUT_PATH = Path("data/tribal_aliases.json")

# US state names for suffix stripping
_US_STATES = {
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


def _strip_multi_state_suffix(name: str) -> str:
    """Strip trailing multi-state suffix from a tribe name.

    Handles patterns like:
      "Navajo Nation, Arizona, New Mexico, & Utah" -> "Navajo Nation"
      "Tribe Name of Arizona, New Mexico & Utah" -> "Tribe Name"

    Returns the stripped name, or the original if no state suffix found.
    """
    # Try stripping from first comma
    comma_idx = name.find(",")
    if comma_idx > 0:
        prefix = name[:comma_idx].strip()
        suffix = name[comma_idx + 1:].strip()
        # Check if suffix is all states + conjunctions/punctuation
        # Remove &, commas, "and" from suffix, then check remaining words
        cleaned = suffix.replace("&", " ").replace(",", " ").replace(" and ", " ")
        tokens = [t.strip() for t in cleaned.split() if t.strip()]
        # Reassemble tokens into potential state names (handle "new mexico" etc.)
        if _all_tokens_are_states(tokens) and prefix:
            return prefix

    # Try stripping "of State" or "of State, State, & State" at end
    of_state_match = re.search(r'\bof\s+((?:the\s+)?(?:' + '|'.join(
        re.escape(s) for s in sorted(_US_STATES, key=len, reverse=True)
    ) + r')(?:\s*[,&]\s*(?:' + '|'.join(
        re.escape(s) for s in sorted(_US_STATES, key=len, reverse=True)
    ) + r'))*)\s*$', name, re.IGNORECASE)
    if of_state_match:
        prefix = name[:of_state_match.start()].strip()
        if prefix:
            return prefix

    return name


def _all_tokens_are_states(tokens: list[str]) -> bool:
    """Check if a list of tokens represents state names.

    Handles multi-word state names like 'new mexico' by consuming
    tokens greedily.
    """
    i = 0
    found_any = False
    while i < len(tokens):
        # Try two-word state first
        if i + 1 < len(tokens):
            two_word = f"{tokens[i]} {tokens[i+1]}"
            if two_word.lower() in _US_STATES:
                found_any = True
                i += 2
                continue
        # Try single-word state
        if tokens[i].lower() in _US_STATES:
            found_any = True
            i += 1
            continue
        # Not a state -- fail
        return False
    return found_any


def build_aliases() -> dict[str, str]:
    """Build alias -> tribe_id mapping from the tribal registry."""
    with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
        registry = json.load(f)

    tribes = registry.get("tribes", [])
    aliases: dict[str, str] = {}

    for tribe in tribes:
        tribe_id = tribe["tribe_id"]
        name = tribe["name"]
        alt_names = tribe.get("alternate_names", [])

        # Tier 1: Official name (lowercased)
        add_alias(aliases, name.lower().strip(), tribe_id)

        # Tier 2: All alternate names (lowercased)
        for alt in alt_names:
            add_alias(aliases, alt.lower().strip(), tribe_id)

        # Tier 3: Common USASpending patterns

        # "THE {name}" variant
        the_variant = f"the {name.lower().strip()}"
        add_alias(aliases, the_variant, tribe_id)

        # All-caps variant (lowered, so same as official -- but useful
        # for documenting that we handle it)
        # Actually add the uppercase version lowered with no extra spaces
        stripped = re.sub(r'\s+', ' ', name.strip())
        add_alias(aliases, stripped.lower(), tribe_id)

        # Remove state suffixes for matching
        # Many USASpending entries drop the state suffix
        # e.g. "Alpha Tribe of Arizona" -> "Alpha Tribe"
        # e.g. "Navajo Nation, Arizona, New Mexico, & Utah" -> "Navajo Nation"
        _STATES_RE = (
            r'alabama|alaska|arizona|arkansas|california|colorado|connecticut|'
            r'delaware|florida|georgia|hawaii|idaho|illinois|indiana|iowa|kansas|'
            r'kentucky|louisiana|maine|maryland|massachusetts|michigan|minnesota|'
            r'mississippi|missouri|montana|nebraska|nevada|new hampshire|new jersey|'
            r'new mexico|new york|north carolina|north dakota|ohio|oklahoma|oregon|'
            r'pennsylvania|rhode island|south carolina|south dakota|tennessee|texas|'
            r'utah|vermont|virginia|washington|west virginia|wisconsin|wyoming'
        )

        # Single trailing state: ", California" or ", Oklahoma"
        state_patterns = [
            r',\s*(' + _STATES_RE + r')$',
        ]

        name_lower = name.lower().strip()

        # Multi-state suffix: ", Arizona, New Mexico, & Utah" or
        # "Arizona, New Mexico & Utah" etc.
        # Strip everything from first comma if remainder is all states/conjunctions
        multi_state_stripped = _strip_multi_state_suffix(name_lower)
        if multi_state_stripped and multi_state_stripped != name_lower:
            add_alias(aliases, multi_state_stripped, tribe_id)
            # Also "the" variant of stripped form
            add_alias(aliases, f"the {multi_state_stripped}", tribe_id)

        # Single state patterns (for names with just one trailing state)
        for pattern in state_patterns:
            shortened = re.sub(pattern, '', name_lower, flags=re.IGNORECASE).strip()
            if shortened and shortened != name_lower:
                add_alias(aliases, shortened, tribe_id)

        # Strip leading "the " for names that start with it
        # "The Muscogee (Creek) Nation" -> "muscogee (creek) nation"
        if name_lower.startswith("the "):
            without_the = name_lower[4:].strip()
            if without_the:
                add_alias(aliases, without_the, tribe_id)

        # Handle parenthetical variants:
        # "Muscogee (Creek) Nation" -> also match "Muscogee Creek Nation"
        # Apply to both original name and state-stripped variant
        names_to_deparenthesize = [name_lower]
        if multi_state_stripped and multi_state_stripped != name_lower:
            names_to_deparenthesize.append(multi_state_stripped)
        # Also try without leading "the"
        for n in list(names_to_deparenthesize):
            if n.startswith("the "):
                names_to_deparenthesize.append(n[4:].strip())

        for candidate in names_to_deparenthesize:
            if '(' in candidate and ')' in candidate:
                no_parens = re.sub(r'\(([^)]+)\)', r'\1', candidate)
                no_parens = re.sub(r'\s+', ' ', no_parens).strip()
                add_alias(aliases, no_parens, tribe_id)

                # Also version with parens content removed entirely
                no_parens_content = re.sub(r'\([^)]+\)\s*', '', candidate)
                no_parens_content = re.sub(r'\s+', ' ', no_parens_content).strip()
                if no_parens_content:
                    add_alias(aliases, no_parens_content, tribe_id)

        # Handle "of the" / "of" variants:
        # "Bad River Band of the Lake Superior Tribe..." -> "Bad River Band"
        # Just add first part before "of the" or "of" if it's substantive
        of_match = re.match(r'^(.+?)\s+of\s+(the\s+)?', name_lower)
        if of_match:
            short = of_match.group(1).strip()
            # Only add if the short form is at least 3 words or 15 chars
            # to avoid overly generic matches
            if len(short.split()) >= 3 or len(short) >= 15:
                add_alias(aliases, short, tribe_id)

        # Do the same for alternate names
        for alt in alt_names:
            alt_lower = alt.lower().strip()
            the_var = f"the {alt_lower}"
            add_alias(aliases, the_var, tribe_id)

            if '(' in alt_lower and ')' in alt_lower:
                no_parens = re.sub(r'\(([^)]+)\)', r'\1', alt_lower)
                no_parens = re.sub(r'\s+', ' ', no_parens).strip()
                add_alias(aliases, no_parens, tribe_id)

            # Multi-state suffix stripping for alternate names
            alt_stripped = _strip_multi_state_suffix(alt_lower)
            if alt_stripped and alt_stripped != alt_lower:
                add_alias(aliases, alt_stripped, tribe_id)
                add_alias(aliases, f"the {alt_stripped}", tribe_id)

            for pattern in state_patterns:
                shortened = re.sub(pattern, '', alt_lower, flags=re.IGNORECASE).strip()
                if shortened and shortened != alt_lower:
                    add_alias(aliases, shortened, tribe_id)

    return aliases


def add_alias(aliases: dict[str, str], key: str, tribe_id: str) -> None:
    """Add an alias, preferring first registration (official name wins)."""
    if not key:
        return
    if key not in aliases:
        aliases[key] = tribe_id


def main() -> None:
    """Build and write the tribal aliases file."""
    aliases = build_aliases()

    data = {
        "_metadata": {
            "description": (
                "Curated mapping: USASpending recipient name "
                "(lowercased, stripped) -> tribe_id"
            ),
            "version": "1.0",
            "last_updated": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "total_aliases": len(aliases),
            "source": "Generated from data/tribal_registry.json by scripts/build_tribal_aliases.py",
        },
        "aliases": dict(sorted(aliases.items())),
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"Built {len(aliases)} aliases -> {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
