#!/usr/bin/env python3
"""Temporary script to add additional curated housing authority aliases.

This script is run once during plan 12-04 execution and should be deleted after.
"""

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

# Additional curated mappings from the remaining unmatched + common patterns
additional_curated = {
    # From the new top 20 unmatched after first run
    "red lake reservation housing": "epa_100000237",
    "colville indian housing authority": "epa_100000055",
    "yurok indian housing authority": "epa_100000338",
    "fort peck housing authority": "epa_100000010",
    "sault tribe housing authority": "epa_100000263",
    "kodiak island housing authority": "epa_100000541",
    "salish & kootenai housing authority": "epa_100000053",
    "salish and kootenai housing authority": "epa_100000053",
    "fond du lac reservation": "epa_100000572",
    "fond du lac housing authority": "epa_100000572",
    "ho-chunk housing & community development agency": "epa_100000101",
    "ho-chunk housing and community development agency": "epa_100000101",
    "leech lake band of ojibwe housing authority": "epa_100000574",
    "leech lake housing authority": "epa_100000574",
    "confederated tribes siletz indians": "epa_100000059",
    "confederated tribes of siletz indians": "epa_100000059",
    # Major Tribes with known housing authority name patterns
    "pine ridge housing authority": "epa_100000179",
    "rosebud housing authority": "epa_100000244",
    "crow creek housing authority": "epa_100000070",
    "fort belknap housing authority": "epa_100000086",
    "fort berthold housing authority": "epa_100000301",
    "sisseton wahpeton housing authority": "epa_100000278",
    "lower brule housing authority": "epa_100000143",
    "spirit lake housing authority": "epa_100000286",
    "winnebago housing authority": "epa_100000327",
    "wind river housing authority": "epa_100000008",
    "mille lacs band housing authority": "epa_100000575",
    "white earth housing authority": "epa_100000576",
    "white earth reservation housing authority": "epa_100000576",
    # Pacific Northwest
    "flathead indian housing authority": "epa_100000053",
    "flathead housing authority": "epa_100000053",
    "muckleshoot housing authority": "epa_100000165",
    "tulalip housing authority": "epa_100000312",
    "quinault housing authority": "epa_100000231",
    "makah housing authority": "epa_100000152",
    "swinomish housing authority": "epa_100000294",
    "lummi housing authority": "epa_100000145",
    "nez perce housing authority": "epa_100000175",
    "warm springs housing authority": "epa_100000058",
    "grand ronde housing authority": "epa_100000056",
    "puyallup housing authority": "epa_100000228",
    "spokane housing authority": "epa_100000282",
    "coeur d\u2019alene housing authority": "epa_100000047",
    "coeur d'alene housing authority": "epa_100000047",
    # Northern Plains
    "crow housing authority": "epa_100000069",
    "northern cheyenne housing authority": "epa_100000177",
    "rocky boy housing authority": "epa_100000042",
    "shoshone-bannock housing authority": "epa_100000273",
    # Southwest
    "uintah and ouray housing authority": "epa_100000314",
    "southern ute housing authority": "epa_100000281",
    "ute mountain housing authority": "epa_100000315",
    "jicarilla apache housing authority": "epa_100000117",
    "mescalero apache housing authority": "epa_100000159",
    "zuni housing authority": "epa_100000341",
    "laguna housing authority": "epa_100000232",
    "acoma housing authority": "epa_100000219",
    "isleta housing authority": "epa_100000225",
    "gila river housing authority": "epa_100000094",
    "salt river housing authority": "epa_100000252",
    "pascua yaqui housing authority": "epa_100000200",
    "ak-chin housing authority": "epa_100000003",
    "fort mojave housing authority": "epa_100000090",
    "colorado river housing authority": "epa_100000049",
    "chemehuevi housing authority": "epa_100000038",
    # California
    "morongo housing authority": "epa_100000164",
    "pechanga housing authority": "epa_100000203",
    "cabazon housing authority": "epa_100000025",
    "agua caliente housing authority": "epa_100000002",
    "tule river housing authority": "epa_100000310",
    "hoopa valley housing authority": "epa_100000103",
    "round valley housing authority": "epa_100000246",
    "karuk housing authority": "epa_100000121",
    # Southeast
    "seminole housing authority": "epa_100000268",
    "miccosukee housing authority": "epa_100000160",
    "poarch creek housing authority": "epa_100000217",
    "eastern cherokee housing authority": "epa_100000076",
    "mississippi choctaw housing authority": "epa_100000162",
    # Oklahoma
    "chickasaw housing authority": "epa_100000041",
    "cherokee nation housing authority": "epa_100000039",
    "muscogee housing authority": "epa_100000168",
    "creek nation housing authority": "epa_100000168",
    "choctaw housing authority": "epa_100000045",
    "osage housing authority": "epa_100000191",
    "quapaw housing authority": "epa_100000230",
    # Great Lakes
    "oneida housing authority": "epa_100000186",
    "menominee housing authority": "epa_100000155",
    "stockbridge munsee housing authority": "epa_100000291",
    "lac courte oreilles housing authority": "epa_100000128",
    "lac du flambeau housing authority": "epa_100000135",
    "bad river housing authority": "epa_100000012",
    "red cliff housing authority": "epa_100000236",
    "mole lake housing authority": "epa_100000280",
    "potawatomi housing authority": "epa_100000087",
    # Minnesota
    "shakopee mdewakanton housing authority": "epa_100000271",
    "prairie island housing authority": "epa_100000218",
    "upper sioux housing authority": "epa_100000316",
    "lower sioux housing authority": "epa_100000144",
    # Dakotas
    "flandreau housing authority": "epa_100000083",
    "yankton housing authority": "epa_100000337",
    "santee sioux housing authority": "epa_100000260",
    # Nebraska
    "omaha housing authority": "epa_100000185",
    "ponca housing authority": "epa_100000216",
    # Kansas/Iowa
    "kickapoo housing authority": "epa_100000122",
    "sac and fox housing authority": "epa_100000250",
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

# Add more skipped regional authorities
existing_skipped = set(s.upper() for s in ha_data["_metadata"].get("skipped_regional", []))
new_skipped = [
    "BRISTOL BAY HOUSING AUTHORITY",
    "NORTHWEST INUPIAT HOUSING AUTHORITY",
    "NORTHERN CIRCLE INDIAN HOUSING AUTHORITY",
    "TAGIUGMIULLU NUNAMIULLU HOUSING AUTHORITY",
    "KAWERAK, INC.",
]
for s in new_skipped:
    if s.upper() not in existing_skipped:
        ha_data["_metadata"]["skipped_regional"].append(s)

ha_data["aliases"] = dict(sorted(aliases.items()))

with open(HA_PATH, "w", encoding="utf-8") as f:
    json.dump(ha_data, f, indent=2, ensure_ascii=False)

print(f"Updated {HA_PATH}")
