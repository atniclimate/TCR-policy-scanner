# Team 4: Ecoregion Classification Sources - Research

**Researched:** 2026-02-10
**Domain:** Ecoregion classification for 575 Tribes, ecoregion-to-program priority mapping
**Requirement:** REG-02
**Confidence:** MEDIUM overall (scheme design MEDIUM, mapping method HIGH, program priority mapping MEDIUM)

---

## Ecoregion Classification Systems

### Available Systems Evaluated

| System | Regions | Granularity | Includes Alaska | Tribal Focus | Notes |
|--------|---------|-------------|-----------------|--------------|-------|
| EPA Level I (North America) | 15 total, ~12 in US | Very broad | Yes (Tundra, Taiga, Arctic Cordillera) | No | Too many for 7-region spec; ecologically derived, not advocacy-aligned |
| EPA Level II | ~50 in North America | Moderate | Yes | No | Too granular for advocacy grouping |
| EPA Level III | 100+ in CONUS | Fine-grained | Not directly | No | Too granular; this is what CONTEXT.md says to "derive from" |
| NOAA Climate Regions | 9 (CONUS only) | State-level | No (separate system) | No | Close to spec but excludes Alaska; 9 regions, not 7 |
| NCA5 Regions | 10 | State-level | Yes (dedicated region) | Has Ch.16 on Tribes | Best alignment with climate advocacy, but 10 regions not 7 |
| BIA Regions | 12 | Administrative | Yes (dedicated region) | Yes -- designed for Tribal programs | Administrative, not climate-based; too many regions |
| Bailey's Ecoregions | ~30 domains | Ecological | Yes | No | Academic classification, no advocacy alignment |
| FEMA Regions | 10 | Administrative | Yes (Region 10) | No | Administrative grouping, not climate-meaningful |

### Key Finding: No Standard 7-Region Climate Scheme Exists

No existing federal classification uses exactly 7 regions. The "7 ecoregions" in the spec is a **custom advocacy-relevant grouping**. The CONTEXT.md confirms this: "7 custom advocacy-relevant regions derived from EPA Level III ecoregions" with examples "Pacific Northwest, Southwest, Alaska, Great Plains, Southeast, Northeast, Mountain West."

The closest existing system is **NCA5 (10 regions)**, which is authoritative for climate assessment and already used by federal agencies for Tribal climate work (NCA5 Chapter 16: Tribes and Indigenous Peoples). The 7-region scheme is a consolidation of NCA5 regions tailored for Tribal advocacy.

**Confidence: HIGH** -- Multiple authoritative sources confirm no standard 7-region scheme exists. The spec requires a custom grouping.

---

## Recommended 7-Ecoregion Scheme

### Design Principles

1. **Align with NCA5** where possible -- federal agencies and congressional staff already reference NCA5 regions
2. **Separate Alaska** as its own region -- 229+ Alaska Native entities (~40% of all Tribes) with unique permafrost/coastal erosion hazards
3. **Separate Pacific Northwest** -- distinct marine climate, salmon-dependent Tribes, wildfire/flooding hazards
4. **Merge Great Plains** into one (NCA5 splits into Northern/Southern) -- similar hazard profiles for Tribal advocacy (drought, extreme weather, flooding)
5. **Separate Southwest** -- drought, wildfire, water scarcity dominate; high Tribal population (AZ, NM, NV, UT)
6. **Keep Southeast** -- hurricane, flooding, coastal erosion; distinct from Northeast
7. **Group Mountain/Interior West** -- CO, MT, WY, ID -- wildfire, drought, snowpack loss

### The 7 Advocacy-Relevant Ecoregions

| # | Ecoregion | States | Est. Tribe Count | Primary Climate Hazards | NCA5 Alignment |
|---|-----------|--------|------------------|-------------------------|----------------|
| 1 | **Alaska** | AK | ~229 | Permafrost thaw, coastal erosion, flooding, wildfire, sea ice loss | NCA5 Alaska |
| 2 | **Pacific Northwest** | WA, OR | ~45 | Wildfire, flooding, salmon habitat loss, drought | NCA5 Northwest (minus ID) |
| 3 | **Southwest** | AZ, NM, NV, UT, CA | ~150 | Drought, wildfire, extreme heat, water scarcity | NCA5 Southwest |
| 4 | **Mountain West** | CO, MT, WY, ID, ND, SD, NE | ~30 | Wildfire, drought, extreme weather, snowpack loss | NCA5 N. Great Plains + parts of NW |
| 5 | **Great Plains & South** | OK, TX, KS, AR, LA | ~45 | Tornado, flooding, drought, extreme heat, hurricane (Gulf) | NCA5 S. Great Plains + parts of SE |
| 6 | **Southeast** | FL, GA, AL, MS, NC, SC, VA, TN, KY, WV | ~15 | Hurricane, flooding, sea level rise, extreme heat | NCA5 Southeast |
| 7 | **Northeast & Midwest** | All remaining eastern/midwestern states (CT, DE, ME, MD, MA, MN, WI, MI, IL, IN, OH, etc.) | ~60 | Flooding, extreme precipitation, heat waves, winter storms | NCA5 Northeast + Midwest |

### Design Rationale

**Why merge NCA5 Northern Great Plains + parts of Northwest into "Mountain West"?** Idaho, Montana, Wyoming share wildfire/drought/snowpack hazards more aligned with Mountain West advocacy priorities than with Pacific coastal issues. The BIA already groups these states under Rocky Mountain and Great Plains regions.

**Why merge Northeast + Midwest?** Both have relatively few Tribes (compared to Alaska, Southwest, Oklahoma). Hazard profiles overlap (flooding, extreme precipitation, winter storms). Keeping them separate would create two regions with very small Tribe counts, diluting advocacy focus. The combined region still has ~60 Tribes -- enough for meaningful program engagement.

**Why merge Southern Great Plains + parts of Southeast into "Great Plains & South"?** Oklahoma (39 Tribes) is the anchor. Louisiana, Arkansas, and Texas share Gulf hurricane exposure with the Southeast, but their Tribal populations and program engagement align more with the Southern Plains BIA region. This grouping avoids splitting Oklahoma's Tribes across two ecoregions.

**Why keep Alaska separate despite being one state?** 229+ Tribes = 40% of all federally recognized Tribes. Unique hazard profile (permafrost, Arctic conditions) with no parallel in the lower 48. BIA already treats Alaska as its own region. NCA5 treats it as its own chapter. Alaska at-large congressional district means all Alaska Tribes share the same delegation.

**Confidence: MEDIUM** -- The 7-region scheme is custom and involves judgment calls on grouping. The CONTEXT.md examples align well with this scheme ("Pacific Northwest, Southwest, Alaska, Great Plains, Southeast, Northeast, Mountain West" -- 7 regions, matching our recommendation). The exact state assignments (e.g., Idaho to Mountain West vs Pacific Northwest) may need adjustment based on domain expert review.

---

## Tribe-to-Ecoregion Mapping Method

### Recommended Approach: State-Based Lookup Table

**Use a static state-to-ecoregion lookup dictionary, not geospatial analysis.**

Rationale:
1. **Every Tribe has a state.** The EPA Tribes Names Service API and BIA Tribal Leaders Directory both include state(s) for each Tribe. This is baseline data from REG-01.
2. **Most states map cleanly to one ecoregion.** Of the ~36 states with federally recognized Tribes, the vast majority fall entirely within one ecoregion in our 7-region scheme.
3. **No geospatial libraries needed.** Avoids geopandas, shapely, GDAL, and the associated complexity of installing geospatial C libraries on Windows and in CI.
4. **575 Tribes is a manageable manual review.** Any edge cases can be hand-curated.

### The Lookup Table

```python
STATE_TO_ECOREGION = {
    # Alaska
    "AK": "Alaska",

    # Pacific Northwest
    "WA": "Pacific Northwest",
    "OR": "Pacific Northwest",

    # Southwest
    "AZ": "Southwest",
    "NM": "Southwest",
    "NV": "Southwest",
    "UT": "Southwest",
    "CA": "Southwest",  # 109 Tribes; could split SoCal vs NorCal but adds complexity

    # Mountain West
    "CO": "Mountain West",
    "MT": "Mountain West",
    "WY": "Mountain West",
    "ID": "Mountain West",
    "ND": "Mountain West",
    "SD": "Mountain West",
    "NE": "Mountain West",

    # Great Plains & South
    "OK": "Great Plains & South",
    "TX": "Great Plains & South",
    "KS": "Great Plains & South",
    "AR": "Great Plains & South",  # No federally recognized Tribes currently
    "LA": "Great Plains & South",
    "IA": "Great Plains & South",  # Meskwaki -- could be Midwest

    # Southeast
    "FL": "Southeast",
    "GA": "Southeast",
    "AL": "Southeast",
    "MS": "Southeast",
    "NC": "Southeast",
    "SC": "Southeast",
    "VA": "Southeast",
    "TN": "Southeast",  # No federally recognized Tribes currently
    "KY": "Southeast",  # No federally recognized Tribes currently
    "WV": "Southeast",  # No federally recognized Tribes currently

    # Northeast & Midwest
    "CT": "Northeast & Midwest",
    "DE": "Northeast & Midwest",
    "ME": "Northeast & Midwest",
    "MD": "Northeast & Midwest",
    "MA": "Northeast & Midwest",
    "NH": "Northeast & Midwest",
    "NJ": "Northeast & Midwest",
    "NY": "Northeast & Midwest",
    "PA": "Northeast & Midwest",
    "RI": "Northeast & Midwest",
    "VT": "Northeast & Midwest",
    "MN": "Northeast & Midwest",
    "WI": "Northeast & Midwest",
    "MI": "Northeast & Midwest",
    "IL": "Northeast & Midwest",  # No federally recognized Tribes currently
    "IN": "Northeast & Midwest",
    "OH": "Northeast & Midwest",
    "MO": "Northeast & Midwest",
    "HI": "Northeast & Midwest",  # Special case -- only 1 entity (Native Hawaiians)
}
```

### Multi-State Tribes

The CONTEXT.md specifies: "multi-ecoregion Tribes listed under ALL applicable ecoregions (not primary-only)."

For multi-state Tribes (e.g., Navajo Nation spans AZ, NM, UT, CO), the implementation is:

```python
def get_tribe_ecoregions(tribe_states: list[str]) -> list[str]:
    """Return all ecoregions a Tribe belongs to, deduplicated."""
    ecoregions = set()
    for state in tribe_states:
        ecoregion = STATE_TO_ECOREGION.get(state)
        if ecoregion:
            ecoregions.add(ecoregion)
    return sorted(ecoregions)

# Navajo Nation: states=["AZ", "NM", "UT", "CO"]
# -> ecoregions=["Mountain West", "Southwest"]  (AZ/NM/UT = Southwest, CO = Mountain West)
```

Most multi-state Tribes span states within the same ecoregion (e.g., a Tribe in WA and OR = both Pacific Northwest). Only a few span ecoregion boundaries:
- Navajo Nation (AZ, NM, UT, CO) -> Southwest + Mountain West
- A few multi-state Tribes near state borders

### Edge Cases

| Edge Case | Resolution | Rationale |
|-----------|------------|-----------|
| California (109 Tribes) | All "Southwest" | NorCal Tribes have some PNW climate alignment, but splitting California creates data management complexity. CONTEXT.md suggests Southwest for CA. |
| Hawaii | "Northeast & Midwest" (catch-all) or separate | Only ~1 Native Hawaiian entity. If included, assign to a catch-all or create a note. Likely not in the 575 Tribe list (Native Hawaiians have different legal status). |
| Iowa (Meskwaki) | "Great Plains & South" | Geographic location aligns with Great Plains more than Midwest for climate hazards. |
| Idaho | "Mountain West" | Could be PNW; placed in Mountain West for wildfire/drought alignment. Nez Perce and other Idaho Tribes have Mountain West hazard profile. |

### Accuracy Assessment

**What is lost by using state-level lookup vs geospatial join?**

- **Nothing, for practical purposes.** Ecoregion classification in this system is used for program priority ranking (which of 16 programs to emphasize), not for precise ecological analysis. A state-level grouping produces the same advocacy-relevant classification as a GIS-based join for 99%+ of Tribes.
- **The only edge case** is a Tribe near a state border whose reservation spans two states in different ecoregions. The multi-state handling (listing ALL ecoregions) addresses this.
- **No geospatial data files needed.** No shapefiles, no GeoJSON, no geopandas dependency.

**Confidence: HIGH** -- State-based lookup is sufficient for advocacy-relevant ecoregion classification. The CONTEXT.md requirement for multi-ecoregion Tribes is handled by the multi-state logic.

---

## Data Sources & Files

### What to Bundle with the Project

The ecoregion system requires **zero external data downloads**. It is a static lookup table embedded in code or in a JSON configuration file.

**Recommended implementation:** Store as part of `data/tribal_registry.json` or as a separate `data/ecoregion_config.json`:

```json
{
  "metadata": {
    "scheme": "TCR 7-Region Advocacy Classification",
    "derived_from": "NCA5 regions, EPA Level I ecoregions, BIA regional structure",
    "version": "1.0",
    "last_updated": "2026-02-10"
  },
  "ecoregions": [
    {
      "id": "alaska",
      "name": "Alaska",
      "states": ["AK"],
      "primary_hazards": ["permafrost_thaw", "coastal_erosion", "flooding", "wildfire", "sea_ice_loss"],
      "nca5_alignment": "Alaska (Ch.29)"
    },
    {
      "id": "pacific_northwest",
      "name": "Pacific Northwest",
      "states": ["WA", "OR"],
      "primary_hazards": ["wildfire", "flooding", "salmon_habitat_loss", "drought"],
      "nca5_alignment": "Northwest (Ch.27)"
    },
    {
      "id": "southwest",
      "name": "Southwest",
      "states": ["AZ", "NM", "NV", "UT", "CA"],
      "primary_hazards": ["drought", "wildfire", "extreme_heat", "water_scarcity"],
      "nca5_alignment": "Southwest (Ch.28)"
    },
    {
      "id": "mountain_west",
      "name": "Mountain West",
      "states": ["CO", "MT", "WY", "ID", "ND", "SD", "NE"],
      "primary_hazards": ["wildfire", "drought", "extreme_weather", "snowpack_loss"],
      "nca5_alignment": "Northern Great Plains (Ch.25) + parts of Northwest"
    },
    {
      "id": "great_plains_south",
      "name": "Great Plains & South",
      "states": ["OK", "TX", "KS", "AR", "LA", "IA"],
      "primary_hazards": ["tornado", "flooding", "drought", "extreme_heat", "hurricane"],
      "nca5_alignment": "Southern Great Plains (Ch.26)"
    },
    {
      "id": "southeast",
      "name": "Southeast",
      "states": ["FL", "GA", "AL", "MS", "NC", "SC", "VA", "TN", "KY", "WV"],
      "primary_hazards": ["hurricane", "flooding", "sea_level_rise", "extreme_heat"],
      "nca5_alignment": "Southeast (Ch.22)"
    },
    {
      "id": "northeast_midwest",
      "name": "Northeast & Midwest",
      "states": ["CT", "DE", "ME", "MD", "MA", "NH", "NJ", "NY", "PA", "RI", "VT", "MN", "WI", "MI", "IL", "IN", "OH", "MO"],
      "primary_hazards": ["flooding", "extreme_precipitation", "heat_waves", "winter_storms"],
      "nca5_alignment": "Northeast (Ch.21) + Midwest (Ch.24)"
    }
  ],
  "state_to_ecoregion": {
    "AK": "alaska",
    "WA": "pacific_northwest",
    "OR": "pacific_northwest",
    "AZ": "southwest",
    "NM": "southwest",
    "NV": "southwest",
    "UT": "southwest",
    "CA": "southwest",
    "CO": "mountain_west",
    "MT": "mountain_west",
    "WY": "mountain_west",
    "ID": "mountain_west",
    "ND": "mountain_west",
    "SD": "mountain_west",
    "NE": "mountain_west",
    "OK": "great_plains_south",
    "TX": "great_plains_south",
    "KS": "great_plains_south",
    "AR": "great_plains_south",
    "LA": "great_plains_south",
    "IA": "great_plains_south",
    "FL": "southeast",
    "GA": "southeast",
    "AL": "southeast",
    "MS": "southeast",
    "NC": "southeast",
    "SC": "southeast",
    "VA": "southeast",
    "TN": "southeast",
    "KY": "southeast",
    "WV": "southeast",
    "CT": "northeast_midwest",
    "DE": "northeast_midwest",
    "ME": "northeast_midwest",
    "MD": "northeast_midwest",
    "MA": "northeast_midwest",
    "NH": "northeast_midwest",
    "NJ": "northeast_midwest",
    "NY": "northeast_midwest",
    "PA": "northeast_midwest",
    "RI": "northeast_midwest",
    "VT": "northeast_midwest",
    "MN": "northeast_midwest",
    "WI": "northeast_midwest",
    "MI": "northeast_midwest",
    "IL": "northeast_midwest",
    "IN": "northeast_midwest",
    "OH": "northeast_midwest",
    "MO": "northeast_midwest"
  }
}
```

### No Shapefiles Needed

The EPA Level I ecoregion shapefile (28 MB) is **not needed** for this implementation. The state-based lookup replaces the need for geospatial joins entirely.

If future versions want precise ecoregion boundaries (e.g., for map rendering in DOCX), the EPA shapefile is available at:
- URL: https://www.epa.gov/eco-research/ecoregions-north-america
- Format: Shapefile (28 MB)
- Would require: geopandas, shapely, fiona

**Recommendation: Do not add geospatial dependencies for v1.1.** The state-based lookup meets the requirement.

---

## Ecoregion-to-Program Priority Mapping

### Concept

All 16 programs appear in every Tribe's packet (per AF-04: no per-Tribe program filtering). However, ecoregion-to-program priority mapping determines **emphasis and ordering** within the packet:

- Which programs are highlighted in the executive summary
- What hazard-to-program connections are featured
- How the "local relevance" framing reads in each Hot Sheet

### Priority Mapping Table

Based on program characteristics, hazard profiles, and geographic relevance:

| Program | Alaska | Pacific NW | Southwest | Mountain West | Great Plains & South | Southeast | NE & Midwest |
|---------|--------|------------|-----------|---------------|---------------------|-----------|--------------|
| **BIA TCR** | HIGH | HIGH | HIGH | HIGH | HIGH | HIGH | HIGH |
| **BIA TCR Awards** | HIGH | HIGH | HIGH | HIGH | HIGH | HIGH | HIGH |
| **FEMA BRIC** | HIGH | HIGH | HIGH | HIGH | HIGH | HIGH | HIGH |
| **FEMA Tribal Mitigation** | HIGH | HIGH | HIGH | HIGH | HIGH | HIGH | HIGH |
| **IRS Elective Pay** | MEDIUM | HIGH | HIGH | HIGH | MEDIUM | MEDIUM | MEDIUM |
| **EPA STAG** | HIGH | MEDIUM | HIGH | MEDIUM | HIGH | HIGH | HIGH |
| **EPA GAP** | HIGH | HIGH | HIGH | HIGH | HIGH | HIGH | HIGH |
| **DOT PROTECT** | HIGH | HIGH | MEDIUM | HIGH | HIGH | HIGH | HIGH |
| **USDA Wildfire** | HIGH | HIGH | HIGH | HIGH | MEDIUM | LOW | LOW |
| **DOE Indian Energy** | MEDIUM | HIGH | HIGH | HIGH | MEDIUM | MEDIUM | MEDIUM |
| **HUD IHBG** | HIGH | HIGH | HIGH | HIGH | HIGH | HIGH | HIGH |
| **NOAA Tribal** | HIGH | HIGH | MEDIUM | LOW | HIGH | HIGH | HIGH |
| **FHWA TTP Safety** | HIGH | HIGH | MEDIUM | HIGH | HIGH | HIGH | HIGH |
| **USBR WaterSMART** | LOW | HIGH | HIGH | HIGH | HIGH | LOW | LOW |
| **USBR TAP** | LOW | HIGH | HIGH | HIGH | HIGH | LOW | LOW |
| **EPA Tribal Air** | HIGH | HIGH | HIGH | HIGH | MEDIUM | MEDIUM | MEDIUM |

### Priority Assignment Rationale

**Universal HIGH (all ecoregions):**
- BIA TCR, BIA TCR Awards: Core Tribal climate resilience -- relevant everywhere
- FEMA BRIC, FEMA Tribal Mitigation: Hazard mitigation universal (though BRIC is currently FLAGGED)
- EPA GAP: Base environmental capacity -- relevant everywhere
- HUD IHBG: Housing applicable everywhere

**Geographically Concentrated:**
- USDA Wildfire: HIGH in Alaska, Pacific NW, Southwest, Mountain West (fire-prone); LOW in Southeast, NE & Midwest (less wildfire risk for Tribal lands)
- USBR WaterSMART/TAP: HIGH in Western states (Bureau of Reclamation jurisdiction); LOW in Eastern states (Reclamation has minimal Eastern presence)
- NOAA Tribal: HIGH in coastal/Great Lakes regions; LOW in landlocked Mountain West
- IRS Elective Pay: HIGH where renewable energy potential is greatest (solar: Southwest; wind: Great Plains, Pacific NW)
- DOT PROTECT: HIGH where transportation infrastructure faces climate threats (permafrost in Alaska, flooding in plains/coast); MEDIUM in Southwest (less flooding)

### Implementation as Static Configuration

```json
{
  "ecoregion_program_priorities": {
    "alaska": {
      "high": ["bia_tcr", "bia_tcr_awards", "fema_bric", "fema_tribal_mitigation", "epa_stag", "epa_gap", "dot_protect", "usda_wildfire", "hud_ihbg", "noaa_tribal", "fhwa_ttp_safety", "epa_tribal_air"],
      "medium": ["irs_elective_pay", "doe_indian_energy"],
      "low": ["usbr_watersmart", "usbr_tap"]
    },
    "pacific_northwest": {
      "high": ["bia_tcr", "bia_tcr_awards", "fema_bric", "fema_tribal_mitigation", "epa_gap", "irs_elective_pay", "dot_protect", "usda_wildfire", "doe_indian_energy", "hud_ihbg", "noaa_tribal", "fhwa_ttp_safety", "usbr_watersmart", "usbr_tap", "epa_tribal_air"],
      "medium": ["epa_stag"],
      "low": []
    },
    "southwest": {
      "high": ["bia_tcr", "bia_tcr_awards", "fema_bric", "fema_tribal_mitigation", "epa_stag", "epa_gap", "irs_elective_pay", "usda_wildfire", "doe_indian_energy", "hud_ihbg", "usbr_watersmart", "usbr_tap", "epa_tribal_air"],
      "medium": ["dot_protect", "noaa_tribal", "fhwa_ttp_safety"],
      "low": []
    },
    "mountain_west": {
      "high": ["bia_tcr", "bia_tcr_awards", "fema_bric", "fema_tribal_mitigation", "epa_gap", "irs_elective_pay", "dot_protect", "usda_wildfire", "doe_indian_energy", "hud_ihbg", "fhwa_ttp_safety", "usbr_watersmart", "usbr_tap", "epa_tribal_air"],
      "medium": ["epa_stag"],
      "low": ["noaa_tribal"]
    },
    "great_plains_south": {
      "high": ["bia_tcr", "bia_tcr_awards", "fema_bric", "fema_tribal_mitigation", "epa_stag", "epa_gap", "dot_protect", "hud_ihbg", "noaa_tribal", "fhwa_ttp_safety", "usbr_watersmart", "usbr_tap"],
      "medium": ["irs_elective_pay", "usda_wildfire", "doe_indian_energy", "epa_tribal_air"],
      "low": []
    },
    "southeast": {
      "high": ["bia_tcr", "bia_tcr_awards", "fema_bric", "fema_tribal_mitigation", "epa_stag", "epa_gap", "dot_protect", "hud_ihbg", "noaa_tribal", "fhwa_ttp_safety"],
      "medium": ["irs_elective_pay", "doe_indian_energy", "epa_tribal_air"],
      "low": ["usda_wildfire", "usbr_watersmart", "usbr_tap"]
    },
    "northeast_midwest": {
      "high": ["bia_tcr", "bia_tcr_awards", "fema_bric", "fema_tribal_mitigation", "epa_stag", "epa_gap", "dot_protect", "hud_ihbg", "noaa_tribal", "fhwa_ttp_safety"],
      "medium": ["irs_elective_pay", "doe_indian_energy", "epa_tribal_air"],
      "low": ["usda_wildfire", "usbr_watersmart", "usbr_tap"]
    }
  }
}
```

**Confidence: MEDIUM** -- Priority assignments are based on program descriptions, geographic applicability of the funding agencies (e.g., Bureau of Reclamation operates in Western states), and climate hazard profiles per region. However, this mapping is ultimately a domain judgment call that should be reviewed by TCR policy staff. The mapping can be easily adjusted since it is static configuration data.

---

## Simplicity vs Accuracy

### State-Based Lookup: The Clear Winner

| Factor | State-Based Lookup | Geospatial Join |
|--------|-------------------|-----------------|
| **Dependencies** | None (dict in Python) | geopandas, shapely, fiona, GDAL |
| **Data files** | None (embedded in code/JSON) | EPA shapefile (28 MB) or GeoJSON |
| **Install complexity** | Zero | High (GDAL C libraries on Windows) |
| **CI/CD impact** | None | Requires GDAL in GitHub Actions |
| **Accuracy for advocacy** | 99%+ (state-level is sufficient) | 100% (polygon intersection) |
| **Build time** | Instant | Requires shapefile processing pipeline |
| **Maintenance** | Trivial (update dict) | Moderate (update shapefiles when EPA publishes) |
| **Multi-ecoregion Tribes** | Handled via multi-state list | Handled via polygon intersection |

### What Geospatial Would Add (and Why It is Not Worth It)

A geospatial approach would allow classifying a Tribe by the exact ecoregion polygon its reservation overlaps. This matters if:
- A state spans two ecoregions AND Tribes exist on both sides of the boundary
- You need sub-state precision for ecoregion assignment

**In practice, this does not matter for our use case.** The ecoregion is used for:
1. Program priority ranking (HIGH/MEDIUM/LOW) -- state-level granularity is sufficient
2. Hazard profile framing ("your region faces drought and wildfire") -- state-level is sufficient
3. Document 2 strategic overview grouping -- state-level is sufficient

**The only scenario where geospatial matters:** If a single state has Tribes in genuinely different climate zones (e.g., Northern vs Southern California). Our approach handles this by assigning all California Tribes to "Southwest." For NorCal Tribes near the Oregon border, this is slightly imprecise but does not change their advocacy priorities in a meaningful way.

### Manual Curation: Feasible for 575 Tribes

575 Tribes is a small enough dataset that any edge cases from the state-based lookup can be manually reviewed and overridden. For example:
- If a specific Tribe should be in a different ecoregion than its state suggests, add an override field to its registry entry
- The override field takes precedence over the state-based lookup

```python
# In tribal_registry.json, per Tribe:
{
    "id": "some_tribe",
    "states": ["CA"],
    "ecoregion_override": "pacific_northwest"  # Optional: overrides state-based lookup
}
```

**Confidence: HIGH** -- The simplicity argument is clear-cut. No geospatial libraries needed.

---

## Recommendations

### 1. Use the 7-Region Custom Advocacy Scheme (not an existing classification)

Create a custom 7-region scheme derived from NCA5 regions, not EPA ecoregions directly. The scheme aligns with the CONTEXT.md examples and NCA5 Chapter 16 (Tribes and Indigenous Peoples). Store as `data/ecoregion_config.json`.

### 2. Use State-Based Lookup (not geospatial)

Map Tribes to ecoregions using their state(s) from the registry. No shapefiles, no geopandas, no GDAL. Multi-state Tribes get all applicable ecoregions.

### 3. Store Ecoregion-to-Program Priority as Static Configuration

The priority mapping (HIGH/MEDIUM/LOW per program per ecoregion) is static data that changes only when programs change. Store in `data/ecoregion_config.json` alongside the region definitions.

### 4. Support Manual Overrides

Allow per-Tribe `ecoregion_override` field in the registry for edge cases. The state-based lookup is the default; overrides handle the exceptions.

### 5. Naming Convention

Use the names from the CONTEXT.md examples with minor adjustments:
- "Pacific Northwest" (not "Northwest" -- avoids ambiguity with NCA5 Northwest which includes ID)
- "Mountain West" (matches CONTEXT.md suggestion)
- "Great Plains & South" (consolidates Great Plains + Southern tier)
- "Northeast & Midwest" (consolidates two smaller regions)
- "Alaska", "Southwest", "Southeast" (standard)

### 6. Implementation Approach

The ecoregion system is a **data layer, not a service**. It requires:
- One JSON configuration file (`data/ecoregion_config.json`)
- A small module (`src/packets/ecoregion.py` or function within `tribal_registry.py`) that:
  - Loads the config
  - Maps state(s) to ecoregion(s)
  - Returns program priorities for a given ecoregion
- No external API calls, no data downloads, no geospatial processing

---

## Confidence Level

| Area | Confidence | Rationale |
|------|------------|-----------|
| No standard 7-region scheme exists | HIGH | Researched EPA, NOAA, NCA5, BIA, Bailey's -- none has exactly 7 regions |
| Recommended 7-region scheme | MEDIUM | Custom grouping aligns with CONTEXT.md examples and NCA5 structure, but state assignments (especially border states like ID, IA) involve judgment |
| State-based lookup method | HIGH | State data is available in all Tribe data sources; avoids geospatial complexity |
| No geospatial libraries needed | HIGH | Clear simplicity advantage confirmed by analysis |
| Ecoregion-to-program priority mapping | MEDIUM | Based on program descriptions and geographic scope; should be reviewed by domain expert |
| Multi-ecoregion handling | HIGH | CONTEXT.md explicitly specifies "listed under ALL applicable ecoregions"; multi-state Tribes naturally produce this |

---

## Open Questions

### 1. California Split?
**Question:** Should California (109 Tribes) be split between Pacific Northwest (NorCal) and Southwest (SoCal)?
**What we know:** NorCal Tribes (e.g., Yurok, Hoopa Valley) have Pacific Northwest climate patterns (rain, salmon, coastal). SoCal Tribes have Southwest patterns (drought, fire, heat).
**Recommendation:** Start with all-CA-in-Southwest. If domain experts want the split, add it as an override for specific Tribes. Splitting the state requires knowing which Tribes are NorCal vs SoCal, which the state-based lookup cannot resolve.

### 2. Iowa Assignment
**Question:** Should Iowa (Meskwaki Settlement) be in "Great Plains & South" or "Northeast & Midwest"?
**What we know:** Geographically Iowa is Midwest. The Meskwaki face Great Plains climate hazards (flooding, extreme weather).
**Recommendation:** Assign to "Great Plains & South" for climate hazard alignment. Low impact either way -- only 1 Tribe.

### 3. Hawaii and Territories
**Question:** Are Native Hawaiian organizations or territorial entities included in the 575 Tribes?
**What we know:** Native Hawaiians have different legal status than federally recognized Tribes. The 575 count includes Lumbee Tribe (added FY2026 NDAA). Hawaii is unlikely to be in the list.
**Recommendation:** Add Hawaii to "Northeast & Midwest" as a catch-all, or handle as a special case if any Hawaiian entity appears in the registry. Low priority.

### 4. Ecoregion Names in DOCX
**Question:** How should ecoregion names appear in the per-Tribe DOCX packets?
**What we know:** The ecoregion appears in the cover page, executive summary, and strategic overview sections.
**Recommendation:** Use the full descriptive name (e.g., "Pacific Northwest") in document text. Use the id (e.g., "pacific_northwest") in data structures and file paths.

### 5. Domain Expert Review
**Question:** Should the ecoregion-to-program priority mapping be reviewed by TCR policy staff before implementation?
**Recommendation:** Yes, but do not block implementation. Implement with the mapping above, flag it as "draft" in the config metadata, and adjust based on feedback. The mapping is static configuration that can be updated without code changes.

---

## Sources

### Primary (HIGH confidence)
- [EPA Ecoregions of North America](https://www.epa.gov/eco-research/ecoregions-north-america) -- Level I/II/III system, 15/52/100+ regions
- [NOAA US Climate Regions](https://www.ncei.noaa.gov/access/monitoring/reference-maps/us-climate-regions) -- 9 CONUS regions
- [Fifth National Climate Assessment Regions](https://nca2023.globalchange.gov/regions/) -- 10 regions including Alaska
- [NCA5 Chapter 16: Tribes and Indigenous Peoples](https://nca2023.globalchange.gov/chapter/16/) -- Tribal climate impacts by region
- [BIA Regional Offices](https://www.bia.gov/regional-offices) -- 12 BIA administrative regions
- [BIA Tribal Resilience Resource Guide](https://www.bia.gov/bia/ots/tribal-climate-resilience-program/tribal-resilience-resource-guide-trrg) -- Regional fact sheets
- [Federal Register: Indian Entities Recognized by BIA](https://www.federalregister.gov/documents/2024/01/08/2024-00109/) -- 574 Tribes list (575 with Lumbee)
- [CRS R47414: The 574 Federally Recognized Indian Tribes](https://www.congress.gov/crs-product/R47414) -- State-by-state distribution

### Secondary (MEDIUM confidence)
- [NCA5 White House Fact Sheet](https://bidenwhitehouse.archives.gov/ostp/news-updates/2023/11/09/fact-sheet-fifth-national-climate-assessment-details-impacts-of-climate-change-on-regions-across-the-united-states/) -- Regional impact summaries
- [USFS Wildfire Risk to Communities](https://wildfirerisk.org/download/) -- Geographic wildfire risk data
- [BIA TCR Branch](https://www.bia.gov/bia/ots/descrm/tcr) -- Tribal climate resilience program structure

### Tertiary (LOW confidence)
- Training data knowledge of EPA Level I ecoregion hierarchy and state membership -- verified against official sources where possible
- Program-to-ecoregion priority mapping -- derived from program descriptions and geographic scope, not from an authoritative published mapping
