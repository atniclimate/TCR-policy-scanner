# Phase 5 Research Cross-Reference Document

**Purpose:** Index of all research findings with cross-references between teams.
**Created:** 2026-02-10
**Status:** Complete (Pass 1 + Pass 2)

---

## Agent Assignments

| Agent | Domain | Status | Confidence |
|-------|--------|--------|------------|
| Team 1 | EPA Tribes Names Service API (REG-01) | Complete | HIGH |
| Team 2 | CRS R48107 / Census CD119 (CONG-01) | Complete | HIGH |
| Team 3 | Congress.gov API Members & Committees (CONG-02) | Complete | HIGH |
| Team 4 | Ecoregion Classification Sources (REG-02) | Complete | MEDIUM |
| Team 5 | Codebase Architecture & Integration Patterns | Complete | HIGH |
| Team 6 | Data Format, Storage & Downstream Compatibility | Complete | HIGH |

---

## Team 1: EPA Tribes Names Service API
- EPA API live at `cdxapi.epa.gov`, no auth, single call returns ~574 Tribes
- Alaska Native BIA codes all "TBD" — recommends EPA Internal ID as primary key
- Historical name variants in `names[]` array — excellent fuzzy matching corpus
- Lumbee Tribe NOT in EPA data yet (Federal Register 2026-01899)
- **See:** TEAM1-epa-tribes-api.md

## Team 2: CRS R48107 / Census Data
- R48107 is 118th Congress (STALE) — do NOT use for 119th Congress mapping
- Census CD119-AIANNH file is correct source: pipe-delimited, 178KB, 119th Congress
- CLASSFP codes filter for federally recognized entities (D1-D8, E1)
- AIANNH-to-Tribe name matching is a key integration challenge
- **See:** TEAM2-crs-r48107.md

## Team 3: Congress.gov API
- Member endpoints: `/v3/member/congress/119?limit=250` — 3 pages for all 541 members
- Committee membership NOT in Congress.gov API — use unitedstates/congress-legislators YAML
- Two-source strategy: API for members + YAML for committees, linked by bioguideId
- 5,000 req/hr rate limit, ~554 calls for full cache build
- **See:** TEAM3-congress-api.md

## Team 4: Ecoregion Classification
- No standard 7-region scheme exists — custom NCA5-derived grouping designed
- State-based lookup eliminates geospatial dependencies entirely
- 7 regions: Alaska, Pacific NW, Southwest, Mountain West, Great Plains & South, Southeast, NE & Midwest
- Ecoregion-to-program priority mapping (HIGH/MEDIUM/LOW per program per region)
- **See:** TEAM4-ecoregion.md

## Team 5: Codebase Architecture
- CLI: `--prep-packets` flat flag with `--tribe` and `--all-tribes`
- Module: `src/packets/` package (orchestrator, context, registry, congress)
- Dataclasses: TribeNode + CongressionalDistrictNode in schema.py
- Graph integration optional per ROADMAP.md
- **See:** TEAM5-codebase-arch.md

## Team 6: Data Format & Storage
- Registry schema: `{metadata, tribes[]}` with DOCX-aware fields
- Congressional cache: members (by bioguide_id), committees, tribe_delegations, district_index
- ID strategy: `epa_{id}` — filesystem-safe, universal (resolves Alaska BIA gap)
- Phase interface contracts: Phase 5 → 6 (fuzzy corpus), 5 → 7 (DOCX fields), 5 → 8 (batch iteration)
- **See:** TEAM6-data-formats.md

---

## Cross-References & Integration Notes

| Finding | Affects | Resolution |
|---------|---------|------------|
| Alaska BIA codes "TBD" (Team 1) | Team 6 ID strategy | Use `epa_{id}` not `bia_{code}` as primary key |
| R48107 is 118th Congress (Team 2) | ROADMAP.md language | Use Census CD119-AIANNH file instead |
| No committee endpoint (Team 3) | Congressional cache design (Team 6) | Two-source: API + YAML |
| Census AIANNH names differ from EPA (Team 2 + Team 1) | Name linkage pipeline needed | Normalize + fuzzy match + curated aliases |
| Team 4 ecoregion names vs Team 6 enum | Ecoregion config | Standardized in 05-RESEARCH.md |
| Team 5 CLI pattern + Team 6 data contracts | PacketOrchestrator design | Aligned in integration doc |

---

## Open Questions (Compiled)

1. ~~**BIA Code Override:**~~ **RESOLVED** — EPA Internal ID (`epa_{id}`) approved as primary key. See PASS2-integration.md §1. (Teams 1, 6)
2. **AIANNH Linkage:** How many Tribes match automatically vs manual curation? (Teams 1, 2)
3. **California Split:** Should CA be split between PNW and Southwest? (Team 4)
4. ~~**Member Detail Pre-fetch:**~~ **RESOLVED** — Pre-fetch all 541 upfront during cache build. Aligned with CONTEXT.md "pre-cache" decision. (Team 3)
5. **Build Script Location:** `scripts/` vs `src/packets/`? (Team 5)
6. **Geographic Coordinates:** EPA lacks lat/lon. BIA CSV has them. Include? (Teams 1, 6)
7. **Lumbee Timeline:** When will EPA update? (Team 1)

---

## Output Files

| File | Purpose |
|------|---------|
| TEAM1-epa-tribes-api.md | EPA API endpoint, schema, data completeness |
| TEAM2-crs-r48107.md | Census CD119-AIANNH file format, parser code |
| TEAM3-congress-api.md | Congress.gov API endpoints, committee YAML |
| TEAM4-ecoregion.md | 7-region scheme, state mapping, program priorities |
| TEAM5-codebase-arch.md | CLI, module, dataclass, testing patterns |
| TEAM6-data-formats.md | JSON schemas, cache org, DOCX contracts |
| PASS2-integration.md | Conflict resolution, data flow, dependency order |
| 05-RESEARCH.md | Final synthesis for plan-phase consumption |
