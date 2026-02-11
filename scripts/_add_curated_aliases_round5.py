#!/usr/bin/env python3
"""Round 5: Final curated aliases to reach 450+ target."""

import json
from datetime import datetime, timezone
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
HA_PATH = _PROJECT_ROOT / "data" / "housing_authority_aliases.json"
REG_PATH = _PROJECT_ROOT / "data" / "tribal_registry.json"

ha_data = json.load(open(HA_PATH, "r", encoding="utf-8"))
aliases = ha_data["aliases"]
curated_before = ha_data["_metadata"]["curated_count"]

reg = json.load(open(REG_PATH, "r", encoding="utf-8"))
valid_ids = {t["tribe_id"] for t in reg["tribes"]}

additional = {
    # From latest unmatched
    "puyallup tribe of indians": "epa_100000228",
    "penobscot indian nation": "epa_100000199",
    "penobscot nation housing authority": "epa_100000199",
    "northern ponca housing authority": "epa_100000207",
    "cheyenne and arapaho housing authority": "epa_100000039",
    "cheyenne and arapaho tribes": "epa_100000039",
    "navajo engineering & construction authority": "epa_100000171",
    "navajo engineering and construction authority": "epa_100000171",
    "pyramid lake housing authority": "epa_100000229",
    "pyramid lake paiute housing authority": "epa_100000229",
    "oglala sioux tribe of pine ridge indian reservation": "epa_100000179",
    "oglala sioux tribe of the pine ridge reservation": "epa_100000179",
    # More Tribe name variants commonly seen in USASpending
    "three affiliated tribes": "epa_100000301",
    "fort berthold reservation": "epa_100000301",
    "mandan hidatsa arikara nation": "epa_100000301",
    "mha nation": "epa_100000301",
    "eastern shoshone": "epa_100000275",
    "eastern shoshone tribe": "epa_100000275",
    "shoshone-paiute tribes": "epa_100000275",
    "duck valley reservation": "epa_100000275",
    "walker river paiute housing authority": "epa_100000321",
    "walker river paiute tribe": "epa_100000321",
    "yerington paiute housing authority": "epa_100000342",
    "te-moak housing authority": "epa_100000298",
    "duckwater shoshone housing authority": "epa_100000074",
    "ely shoshone housing authority": "epa_100000081",
    "washoe housing authority": "epa_100000323",
    "fallon paiute-shoshone housing authority": "epa_100000082",
    # New England Tribes
    "mashpee wampanoag housing authority": "epa_100000154",
    "mashpee wampanoag tribe": "epa_100000154",
    "wampanoag tribe of gay head (aquinnah)": "epa_100000320",
    "wampanoag tribe of gay head": "epa_100000320",
    "narragansett housing authority": "epa_100000170",
    "mohegan housing authority": "epa_100000576",
    "passamaquoddy housing authority": "epa_100000202",
    "micmac housing authority": "epa_100000009",
    # New York
    "seneca nation housing authority": "epa_100000267",
    "seneca nation": "epa_100000267",
    "tonawanda band of seneca": "epa_100000309",
    "st. regis mohawk housing authority": "epa_100000256",
    "akwesasne housing authority": "epa_100000256",
    "onondaga nation": "epa_100000187",
    "oneida indian nation": "epa_100000186",
    "tuscarora nation": "epa_100000313",
    "cayuga nation": "epa_100000036",
    "shinnecock housing authority": "epa_100000274",
    # Mississippi/Louisiana
    "chitimacha housing authority": "epa_100000044",
    "coushatta housing authority": "epa_100000065",
    "tunica-biloxi housing authority": "epa_100000557",
    "jena band of choctaw housing authority": "epa_100000116",
}

added = 0
skipped = []
for name, tid in additional.items():
    if tid not in valid_ids:
        skipped.append((name, tid))
        continue
    if name not in aliases:
        aliases[name] = tid
        added += 1

if skipped:
    print(f"Skipped (invalid tribe_id): {skipped}")

print(f"Added {added} new curated aliases")
print(f"Total aliases now: {len(aliases)}")

ha_data["_metadata"]["curated_count"] = curated_before + added
ha_data["_metadata"]["total_count"] = len(aliases)
ha_data["_metadata"]["last_updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
ha_data["aliases"] = dict(sorted(aliases.items()))

with open(HA_PATH, "w", encoding="utf-8") as f:
    json.dump(ha_data, f, indent=2, ensure_ascii=False)

print(f"Updated {HA_PATH}")
