#!/usr/bin/env python3
"""Round 3: Add more curated housing authority aliases for remaining unmatched."""

import json
from datetime import datetime, timezone
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
HA_PATH = _PROJECT_ROOT / "data" / "housing_authority_aliases.json"
REG_PATH = _PROJECT_ROOT / "data" / "tribal_registry.json"

# Load existing data
ha_data = json.load(open(HA_PATH, "r", encoding="utf-8"))
aliases = ha_data["aliases"]
curated_before = ha_data["_metadata"]["curated_count"]

reg = json.load(open(REG_PATH, "r", encoding="utf-8"))
valid_ids = {t["tribe_id"] for t in reg["tribes"]}

# Round 3 curated mappings from remaining unmatched
additional_curated = {
    # Name variants with "inc" suffix
    "fort berthold housing authority inc": "epa_100000301",
    "fort berthold housing authority, inc": "epa_100000301",
    "fort berthold housing authority, inc.": "epa_100000301",
    # Hyphenated name variants
    "sisseton-wahpeton housing authority": "epa_100000278",
    # "Nation" in housing authority name
    "lummi nation housing authority": "epa_100000145",
    # Tribe name variants in USASpending
    "shoshone bannock tribes": "epa_100000273",
    "shoshone-bannock tribes": "epa_100000273",
    # "Indian" in housing authority name
    "round valley indian housing authority": "epa_100000246",
    "spokane indian housing authority": "epa_100000282",
    # Transportation authorities
    "ho-chunk nation transportation authority": "epa_100000101",
    # DOI prefix names (common in USASpending for FHWA grants)
    "doi trb wa upper skagit indian tribe": "epa_100000317",
    # Traditional Tribe names used as entity names
    "apsaalooke nation housing authority": "epa_100000069",  # Apsaalooke = Crow Tribe
    "apsaalooke nation": "epa_100000069",
    # "Residential management corporation" variants
    "colorado river residential management corporation": "epa_100000049",
    # More Alaska-specific patterns
    "aleutian housing authority": "epa_100000514",  # Pribilof Islands Aleut Communities
    # Common DOI TRB prefix patterns for FHWA grants
    "doi trb az navajo nation": "epa_100000171",
    "doi trb az tohono o'odham nation": "epa_100000302",
    "doi trb az gila river indian community": "epa_100000094",
    "doi trb az salt river pima-maricopa indian community": "epa_100000252",
    "doi trb az white mountain apache tribe": "epa_100000324",
    "doi trb az san carlos apache tribe": "epa_100000254",
    "doi trb az hopi tribe": "epa_100000104",
    "doi trb az pascua yaqui tribe": "epa_100000200",
    "doi trb wa tulalip tribes": "epa_100000312",
    "doi trb wa muckleshoot indian tribe": "epa_100000165",
    "doi trb wa yakama nation": "epa_100000062",
    "doi trb wa quinault indian nation": "epa_100000231",
    "doi trb wa lummi tribe": "epa_100000145",
    "doi trb wa swinomish indian tribal community": "epa_100000294",
    "doi trb wa puyallup tribe": "epa_100000228",
    "doi trb wa colville tribes": "epa_100000055",
    "doi trb wa confederated tribes of the colville reservation": "epa_100000055",
    "doi trb or warm springs": "epa_100000058",
    "doi trb or confederated tribes of warm springs": "epa_100000058",
    "doi trb mt crow tribe": "epa_100000069",
    "doi trb mt blackfeet tribe": "epa_100000020",
    "doi trb mt northern cheyenne tribe": "epa_100000177",
    "doi trb sd oglala sioux tribe": "epa_100000179",
    "doi trb sd rosebud sioux tribe": "epa_100000244",
    "doi trb sd cheyenne river sioux tribe": "epa_100000040",
    "doi trb sd standing rock sioux tribe": "epa_100000289",
    "doi trb nd turtle mountain band": "epa_100000311",
    "doi trb mn red lake band": "epa_100000237",
    "doi trb mn mille lacs band": "epa_100000575",
    "doi trb mn leech lake band": "epa_100000574",
    "doi trb mn white earth band": "epa_100000576",
    "doi trb wi ho-chunk nation": "epa_100000101",
    "doi trb wi menominee indian tribe": "epa_100000155",
    "doi trb wi oneida nation": "epa_100000186",
    "doi trb ok cherokee nation": "epa_100000039",
    "doi trb ok chickasaw nation": "epa_100000041",
    "doi trb ok choctaw nation": "epa_100000045",
    "doi trb ok muscogee nation": "epa_100000168",
    "doi trb nc eastern band of cherokee indians": "epa_100000076",
    "doi trb fl seminole tribe": "epa_100000268",
    "doi trb ms mississippi band of choctaw indians": "epa_100000162",
}

# Verify and add
added_curated = 0
skipped_invalid = []
for name, tid in additional_curated.items():
    if tid not in valid_ids:
        skipped_invalid.append((name, tid))
        continue
    if name not in aliases:
        aliases[name] = tid
        added_curated += 1

if skipped_invalid:
    print(f"Skipped (invalid tribe_id): {skipped_invalid}")

print(f"Added {added_curated} new curated aliases")
print(f"Total aliases now: {len(aliases)}")

# Update metadata
ha_data["_metadata"]["curated_count"] = curated_before + added_curated
ha_data["_metadata"]["total_count"] = len(aliases)
ha_data["_metadata"]["last_updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")

# Add more skipped entries
existing_skipped = set(s.upper() for s in ha_data["_metadata"].get("skipped_regional", []))
new_skipped = [
    "ALEUTIAN HOUSING AUTHORITY",  # Regional Alaska
]
for s in new_skipped:
    if s.upper() not in existing_skipped:
        ha_data["_metadata"]["skipped_regional"].append(s)

ha_data["aliases"] = dict(sorted(aliases.items()))

with open(HA_PATH, "w", encoding="utf-8") as f:
    json.dump(ha_data, f, indent=2, ensure_ascii=False)

print(f"Updated {HA_PATH}")
