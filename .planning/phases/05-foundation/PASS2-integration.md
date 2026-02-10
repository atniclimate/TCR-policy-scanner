# Pass 2: Integration Architecture & Conflict Resolution

**Date:** 2026-02-10
**Input:** 6 team research files from Pass 1

---

## Conflicts & Resolutions

### 1. Primary Key: BIA Code vs EPA Internal ID

**Conflict:** CONTEXT.md says "Primary key: BIA code." Team 1 discovered ~230 Alaska Native entities have BIA code "TBD" (not assigned). Team 6 designed `bia_{code}` ID strategy around BIA codes.

**Resolution:** Use a **dual-key strategy**:
- `tribe_id`: Use `epa_{epaTribalInternalId}` as the universal primary key (e.g., `epa_100000171`). Every Tribe has one — no gaps.
- `bia_code`: Store as a searchable secondary field. For Alaska Natives with "TBD", store `null`.
- **Rationale:** 40% of Tribes (Alaska Natives) lack BIA codes. Using BIA code as PK would require synthetic keys for 230 Tribes. EPA Internal ID is designed for this exact purpose.
- **Impact on Team 6 schema:** Change `tribe_id` pattern from `bia_{code}` to `epa_{id}`. All file paths, cache keys, and cross-references use this format.
- **Override CONTEXT.md:** Flag this as a necessary deviation in the plan.

### 2. Ecoregion Naming Inconsistency

**Conflict:** Team 4 uses "Great Plains & South" and "Northeast & Midwest". Team 6 enum uses "Great Plains" and "Northeast".

**Resolution:** Use Team 4's full names consistently:
- `alaska`, `pacific_northwest`, `southwest`, `mountain_west`, `great_plains_south`, `southeast`, `northeast_midwest`
- Display names: "Alaska", "Pacific Northwest", "Southwest", "Mountain West", "Great Plains & South", "Southeast", "Northeast & Midwest"

### 3. Census AIANNH ↔ EPA Tribe Linkage

**Conflict:** Team 2 outputs Census AIANNH GEOIDs. Team 1 outputs EPA Tribal Internal IDs. No direct crosswalk exists between them.

**Resolution:** Three-tier linkage pipeline:
1. **Name matching (primary):** Normalize both Census `NAMELSAD_AIANNH_20` and EPA `currentName` — strip suffixes like "Reservation and Off-Reservation Trust Land", then match.
2. **Curated alias table (secondary):** For known mismatches (e.g., Census "Cherokee OTSA" → EPA "Cherokee Nation"), maintain a static JSON mapping in `data/aiannh_tribe_crosswalk.json`.
3. **Manual fallback (tertiary):** For Tribes without Census geographic areas, use BIA office location geocoded to congressional district.
- **Estimated coverage:** ~90% automated, ~10% manual curation (50-60 Tribes).

### 4. Congressional Data: CRS R48107 Abandoned

**Conflict:** ROADMAP.md says "CRS R48107 authoritative table." Team 2 found R48107 is **118th Congress** (expired).

**Resolution:** Use Census CD119-AIANNH relationship file instead. Same underlying data, correct Congress, machine-readable. Update ROADMAP.md language to reference Census source.

---

## Data Flow Architecture

```
Phase 5 Data Build Pipeline:
==========================

1. EPA Tribes Names Service API
   GET /api/v1/tribeDetails?tribalBandFilter=AllTribes
   → ~574 Tribe records with names, states, BIA codes, historical names
   → Write: data/tribal_registry.json

2. State-to-Ecoregion Lookup
   Static mapping (embedded in ecoregion_config.json)
   → Enriches each Tribe in registry with ecoregion(s)
   → Write: data/ecoregion_config.json (program priorities)

3. Census CD119-AIANNH Relationship File
   Download: tab20_cd11920_aiannh20_natl.txt (178KB)
   Parse: pipe-delimited CSV, filter by CLASSFP
   → Tribe-to-district crosswalk (many-to-many)

4. Congress.gov API + unitedstates/congress-legislators
   Fetch: /member/congress/119 (3 pages, ~541 members)
   Fetch: /member/{bioguideId} (541 detail calls)
   Download: committee-membership-current.yaml
   → Write: data/congressional_cache.json

5. AIANNH-to-Tribe Linkage
   Match Census AIANNH names to EPA Tribe names
   Curated fallback: data/aiannh_tribe_crosswalk.json
   → Merge into congressional_cache.json tribe_delegations

Runtime Data Flow:
================

main.py --prep-packets --tribe "Navajo"
  → PacketOrchestrator.__init__()
    → TribalRegistry.load(data/tribal_registry.json)
    → CongressionalMapper.load(data/congressional_cache.json)
  → TribalRegistry.resolve("Navajo")
    → exact match → substring → fuzzy (rapidfuzz)
    → returns TribeRecord
  → CongressionalMapper.get_delegation(tribe_id)
    → returns senators, reps, committees
  → PacketOrchestrator._build_context()
    → assembles TribePacketContext
  → PacketOrchestrator._display_tribe_info()
    → CLI output (Phase 5 stub; DOCX in Phase 7)
```

---

## Dependency Order

| Order | Component | Depends On | Blocks |
|-------|-----------|------------|--------|
| 1 | Ecoregion config JSON | Nothing | Registry build |
| 2 | EPA API → tribal_registry.json | Ecoregion config | Everything |
| 3 | Census file download + parse | Nothing (parallel with 1-2) | Congressional cache |
| 4 | Congress.gov API + YAML | Nothing (parallel with 1-3) | Congressional cache |
| 5 | AIANNH-to-Tribe linkage | Registry (2) + Census parse (3) | Congressional cache |
| 6 | Congressional cache assembly | Linkage (5) + Congress.gov (4) | CongressionalMapper |
| 7 | Graph schema additions | Nothing | Optional graph seed |
| 8 | src/packets/ modules | Registry + Congress cache | CLI integration |
| 9 | CLI --prep-packets | src/packets/ modules | Success criteria |
| 10 | Tests | All modules | Verification |

---

## Risk Assessment

| Risk | Severity | Likelihood | Mitigation |
|------|----------|------------|------------|
| AIANNH-to-Tribe name matching fails for many Tribes | HIGH | MEDIUM | Curated alias table + manual review |
| EPA API down during registry build | MEDIUM | LOW | Bundled XLSX fallback |
| Congress.gov rate limiting during 541 detail fetches | MEDIUM | LOW | Existing BaseScraper retry + 0.3s delay |
| Lumbee Tribe missing from EPA data | LOW | HIGH (confirmed) | Log warning, skip gracefully |
| Alaska BIA code "TBD" breaks downstream | HIGH | HIGH (confirmed) | EPA ID as primary key (resolved above) |
| Census file format changes | LOW | LOW | Static file bundled with project |
