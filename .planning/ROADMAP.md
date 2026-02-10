# Milestone v1.1: Tribe-Specific Advocacy Packets

**Status:** Active
**Phases:** 5-8
**Total Requirements:** 19

## Overview

The v1.1 milestone extends the TCR Policy Scanner from a shared advocacy intelligence briefing to per-Tribe congressional advocacy packets for all 575 federally recognized Tribes. The build order follows the data dependency graph: establish the Tribal registry and congressional mapping foundation first (Phase 5), then tackle the two hardest data acquisition challenges -- fuzzy award matching and multi-source hazard profiling (Phase 6), then compute economic impact and build the DOCX generation engine (Phase 7), and finally assemble the two output documents with operational CLI modes and change tracking (Phase 8). Each phase delivers a verifiable capability: Phase 5 enables `--prep-packets` to run with Tribe identity data, Phase 6 populates per-Tribe award and hazard caches, Phase 7 produces individual DOCX sections, and Phase 8 ships complete packets.

## Phases

### Phase 5: Foundation

**Goal**: The Tribal registry, congressional mapping, and CLI skeleton are in place so that `--prep-packets --tribe <name>` resolves a Tribe, displays its delegation, and routes to the packet generation pathway -- even though actual DOCX output is stubbed.
**Depends on**: v1.0 pipeline (Phases 1-4 complete)
**Plans**: 4 plans

Plans:
- [x] 05-01-PLAN.md -- Module skeleton, ecoregion classification, context dataclass, graph schema [Wave 1]
- [x] 05-02-PLAN.md -- Tribal registry build script + runtime module (EPA API) [Wave 1]
- [x] 05-03-PLAN.md -- Congressional mapping build script + runtime module (Census + Congress.gov + YAML) [Wave 1]
- [x] 05-04-PLAN.md -- PacketOrchestrator, CLI integration, test suite [Wave 2]

**Details:**
- Requirements: REG-01, REG-02, REG-03, CONG-01, CONG-02

**REG-01** delivers the 575-Tribe registry from EPA Tribes Names Service API with BIA codes, states, and historical name variants. **REG-02** adds ecoregion classification for each Tribe with ecoregion-to-program priority mapping. **REG-03** ensures per-Tribe DOCX packets will display Tribe identity in document title, headers, and cover page fields (validated here with a test harness, rendered in Phase 7). **CONG-01** models Tribe-to-congressional-district as many-to-many using the CRS R48107 authoritative table, correctly handling multi-state Tribes (Navajo = 4 districts, 3 states) and Alaska at-large. **CONG-02** pre-caches senators, House representatives, and relevant committee assignments per Tribe from the Congress.gov API for the 119th Congress.

This phase also delivers the `--prep-packets` CLI extension in main.py, the PacketOrchestrator skeleton with TribePacketContext dataclass, and graph schema additions (TribeNode, CongressionalDistrictNode). These are foundational scaffolding that unblock all downstream phases.

**Rationale:** Everything depends on knowing which Tribes exist, where they are, and who represents them. Establishing the data backbone and CLI skeleton with no external API complexity (registry is fetched once, congressional map is pre-computed from CRS table) lets Phase 6 focus entirely on the hard data quality problems. The many-to-many district model must be right from day one -- retrofitting it later would cascade through every downstream module.

**Success Criteria:**
1. `--prep-packets --tribe "Navajo Nation"` resolves the Tribe, displays its name, BIA code, state(s), ecoregion, and congressional delegation (4 districts, 3 states, 2 senators per state, 4 House reps)
2. `--prep-packets --tribe "Tlingit"` performs fuzzy search across 575 Tribe names and historical variants, returning candidate matches
3. All 575 Tribes loaded from registry with no duplicates, each classified into one of 7 ecoregions
4. Alaska at-large district correctly maps all 229 Alaska Native entities to AK-AL with the single at-large representative

---

### Phase 6: Data Acquisition

**Goal**: Per-Tribe USASpending award histories and hazard profiles are cached locally, so that any Tribe's funding track record and top climate risks can be retrieved without API calls at DOCX generation time.
**Depends on**: Phase 5 (Tribal registry provides canonical names for award matching and geographic data for hazard mapping)
**Plans**: 3 plans

Plans:
- [x] 06-01-PLAN.md -- TribalAwardMatcher: batch USASpending queries + two-tier name matching + per-Tribe award cache [Wave 1]
- [x] 06-02-PLAN.md -- HazardProfileBuilder: FEMA NRI + USFS wildfire ingestion + per-Tribe hazard cache [Wave 1]
- [x] 06-03-PLAN.md -- Integration: wire awards + hazards into orchestrator, config, tests [Wave 2]

**Details:**
- Requirements: AWARD-01, AWARD-02, HAZ-01, HAZ-02

**AWARD-01** delivers per-CFDA USASpending Tribal award queries with full pagination and `recipient_type_names: ["tribal"]` filter -- not limited to top 10. This modifies the existing USASpendingScraper to support batch Tribal queries (12 calls total for all 16 CFDAs, not 575 x 16 individual queries). **AWARD-02** implements the two-tier Tribal name matching system: curated alias table as primary lookup, rapidfuzz token_sort_ratio >= 85 as fallback, with state-overlap validation and match confidence scoring. This is the hardest data quality challenge in the entire milestone -- false positives (attributing wrong Tribe's awards) are worse than false negatives.

**HAZ-01** ingests FEMA National Risk Index (NRI v1.20) tribal-specific CSV data, mapping 18 hazard types to Tribal areas with overall risk score, top hazards, expected annual loss, and social vulnerability. **HAZ-02** integrates USFS Wildfire Risk to Communities tabular data per Tribe from pre-downloaded files. Both hazard sources are cached as per-Tribe JSON files in `data/hazard_profiles/{tribe_id}.json`.

**Rationale:** These are the two hardest data acquisition challenges isolated together. Phase 5's registry provides the test harness (canonical names for matching, geographic data for hazard lookups). Pre-caching all data here prevents Phase 7 from hitting API rate limits during DOCX generation. The fuzzy matching quality calibration (AWARD-02) may require manual alias curation -- better to tackle this before the generation phases depend on it.

**Success Criteria:**
1. For a known Tribe with USASpending history (e.g., Cherokee Nation), the award matcher returns correct per-program award totals with FY breakdown and project descriptions, matching across name variants ("CHEROKEE NATION OF OKLAHOMA" -> "Cherokee Nation")
2. For a Tribe with no USASpending matches, the system returns empty results (not false matches from other Tribes) with zero false positives in a validation sample
3. Hazard profile for a high-risk Tribe (e.g., a Gulf Coast Tribe) shows top 3 hazards from NRI with risk scores, expected annual loss, and social vulnerability rating
4. Wildfire risk data populates for Tribes in fire-prone regions (e.g., California, Pacific Northwest Tribes) with USFS risk rating
5. All 575 Tribe hazard profiles cached as JSON files, loadable without any API calls

---

### Phase 7: Computation and DOCX Generation

**Goal**: The DOCX generation engine produces professional per-program Hot Sheet sections with economic impact framing, advocacy language, and structural asks -- so that a single Tribe's complete packet sections can be rendered and opened in Microsoft Word.
**Depends on**: Phase 6 (award data feeds economic impact calculations; hazard data feeds per-program relevance)
**Plans**: 4 plans

Plans:
- [ ] 07-01-PLAN.md -- Economic impact calculator + program relevance filter (ECON-01) [Wave 1]
- [ ] 07-02-PLAN.md -- DOCX styles + engine skeleton (DOC-01) [Wave 1]
- [ ] 07-03-PLAN.md -- Hot Sheet renderer with advocacy language + structural asks (DOC-02, DOC-03, DOC-04) [Wave 2]
- [ ] 07-04-PLAN.md -- Cover page, appendix, engine completion, orchestrator integration [Wave 3]

**Details:**
- Requirements: ECON-01, DOC-01, DOC-02, DOC-03, DOC-04

**ECON-01** delivers district-level economic impact framing per Tribe per program: USASpending obligations multiplied by published multiplier ranges (~2.0x), plus FEMA 4:1 benefit-cost ratio for mitigation programs, with citable methodology. This uses FEMA BCR and published standard multipliers -- not RIMS II (cost-prohibitive at $500/region).

**DOC-01** builds the python-docx programmatic DOCX construction engine with professional formatting -- tables, headers/footers, page breaks, consistent styles via style reference document. This is the rendering foundation all document sections depend on. **DOC-02** generates 16 per-program Hot Sheets per Tribe, each containing program status (CI, advocacy goal), Tribe-specific award history, local hazard relevance, district economic impact, and congressional delegation. **DOC-03** assembles advocacy language per program from decision engine classifications, program inventory tightened_language, and advocacy_lever fields -- template-based, not AI-generated. **DOC-04** weaves Five Structural Asks into per-program Hot Sheets showing which asks advance which programs, with Tribe-specific evidence from award and hazard data.

**Rationale:** All data flows are now in place from Phases 5-6. This phase transforms raw data into computed outputs (economic impact) and rendered documents (DOCX sections). Building the DOCX engine and Hot Sheet sections together means each section builder can be tested independently before Phase 8 assembles them into complete documents. The style reference document approach (single .docx defining styles) ensures consistent formatting across all 575 packets without template-per-Tribe maintenance burden.

**Success Criteria:**
1. A single Tribe's 16 Hot Sheet sections open correctly in Microsoft Word with professional table formatting, consistent styles, and readable layout
2. Each Hot Sheet shows the Tribe's actual USASpending award history (or "No awards to date" with advocacy framing), local hazard relevance, and district economic impact narrative
3. Economic impact narrative for a Tribe with award history reads naturally: "BIA TCR funding to [Tribe] generated an estimated $X in economic activity in [District], supporting approximately Y jobs"
4. Advocacy language per program is assembled from existing program inventory data (tightened_language, advocacy_lever fields) -- no AI-generated text
5. Structural asks appear in relevant Hot Sheets with Tribe-specific evidence linking the ask to the Tribe's hazard profile and award history

---

### Phase 8: Assembly and Polish

**Goal**: Complete per-Tribe packets (Document 1) and the shared strategic overview (Document 2) are generated via CLI in batch and ad-hoc modes, with change tracking showing what shifted since the last generation -- ready for distribution to congressional offices.
**Depends on**: Phase 7 (Hot Sheet sections and DOCX engine must be working)
**Plans**: TBD

**Details:**
- Requirements: DOC-05, DOC-06, OPS-01, OPS-02, OPS-03

**DOC-05** assembles Document 1 -- FY26 [Tribe Name] Climate Resilience Program Priorities: per-Tribe DOCX (575 variants) with cover page, executive summary, delegation section, 16 Hot Sheets, hazard profile, structural asks, and appendix. This is the final assembly of all sections built in Phase 7 into a complete, print-ready document. **DOC-06** builds Document 2 -- FY26 Federal Funding Overview & Strategy: a single shared DOCX with appropriations landscape, ecoregion strategic priorities, science infrastructure threats, FEMA analysis, cross-cutting framework, and messaging guidance.

**OPS-01** delivers `--prep-packets --all-tribes` CLI mode for batch generation of all 575 Tribe packets plus strategic overview. **OPS-02** delivers `--prep-packets --tribe <name>` CLI mode for ad-hoc single-Tribe packet generation. Both build on the CLI skeleton from Phase 5 but now route to the full PacketOrchestrator with complete data and DOCX generation. **OPS-03** adds change tracking -- a "Since Last Packet" section in each DOCX showing CI status changes, new awards, advocacy goal shifts, and new legislative threats since the previous generation.

**Rationale:** Assembly comes last because it integrates everything: the DOCX engine (Phase 7), all per-Tribe data (Phase 6), the registry and delegation (Phase 5), and existing v1.0 pipeline outputs. The shared strategic overview (DOC-06) aggregates per-Tribe data computed in earlier phases. Change tracking (OPS-03) requires packet state persistence, which is an operational feature that builds on a proven core rather than being part of it. Batch generation at 575 Tribes requires memory management (per-document GC, batch processing) that only makes sense to optimize after single-Tribe generation works.

**Success Criteria:**
1. `--prep-packets --tribe "Cherokee Nation"` generates a complete DOCX packet in `outputs/packets/tribes/` that opens in Word with cover page, executive summary, delegation, 16 Hot Sheets, hazard profile, structural asks, and appendix
2. `--prep-packets --all-tribes` generates 575 Tribe packets plus STRATEGIC-OVERVIEW.docx in under 5 minutes, with progress reporting and no memory errors
3. Document 2 (Strategic Overview) contains appropriations landscape, ecoregion priorities for all 7 ecoregions, FEMA analysis, and cross-cutting framework drawn from existing v1.0 pipeline data
4. Running `--prep-packets` twice for the same Tribe produces a "Since Last Packet" section in the second run showing any CI status changes, new awards, or advocacy goal shifts
5. A generated packet for a multi-state Tribe (e.g., Navajo Nation) correctly lists all representatives across all districts and states in the delegation section

---

## Milestone Summary

**Key Decisions:**
- Phases start at 5 (continuing from v1.0 Phases 1-4)
- Separate CLI command (`--prep-packets`), not integrated into daily scan pipeline -- different cadence, different data dependencies
- Pre-cache all data layers before DOCX generation -- zero API calls during document construction
- Programmatic python-docx construction with style reference document (not template-per-Tribe)
- Two-tier name matching for USASpending (curated alias table + rapidfuzz fallback) -- false negatives preferred over false positives
- FEMA BCR + published multiplier ranges for economic impact (not RIMS II at $500/region)
- Census CD119-AIANNH relationship file for Tribe-to-district mapping (replaces CRS R48107, which maps to 118th Congress; not computed from TIGER shapefiles)
- Many-to-many Tribe-to-district model from day one (multi-state Tribes, Alaska at-large)
- 575 Tribes (Lumbee added via FY2026 NDAA, Federal Register 2026-01899)
- Foundation phase has no external API dependencies -- enables testing with mock data while data acquisition phases progress

**Issues Deferred:**
- EPA EJScreen integration deferred (removed from EPA Feb 2025; FEMA NRI + USFS cover core hazard needs)
- NOAA climate projections deferred (valuable but adds significant data integration complexity beyond NRI)
- Interactive packet preview deferred (CLI-only; Word is the review tool)
- Graph node integration for Tribes/Hazards/Districts optional (PacketOrchestrator works from JSON data files; graph enrichment can come later)
- DOCX styling reference document needs analysis of actual reference files before Phase 7 planning

---

_Created: 2026-02-10_
_For v1.0 history, see .planning/milestones/v1.0-ROADMAP.md_
