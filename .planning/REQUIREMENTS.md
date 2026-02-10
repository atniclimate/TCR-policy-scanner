# Requirements: v1.1 Tribe-Specific Advocacy Packets

**Milestone:** v1.1
**Created:** 2026-02-10
**Status:** Active
**Total:** 19 requirements

---

## Tribal Registry

- [x] **REG-01**: 592 federally recognized Tribes loaded from EPA Tribes Names Service API with BIA codes, states, and historical name variants for fuzzy matching corpus
- [x] **REG-02**: Ecoregion classification for each Tribe (7 ecoregions) with ecoregion-to-program priority mapping
- [x] **REG-03**: Per-Tribe DOCX packets display Tribe identity in document title, headers, and cover page fields (Tribe name, state(s), ecoregion, congressional district(s), delegation, primary hazards)

## Congressional Mapping

- [x] **CONG-01**: Tribe-to-congressional-district mapping modeled as many-to-many (CRS R48107 authoritative table), correctly handling multi-state Tribes (e.g., Navajo = 4 districts, 3 states) and Alaska at-large
- [x] **CONG-02**: Senators, House representatives, and relevant committee assignments (Indian Affairs, Appropriations, Natural Resources) per Tribe from Congress.gov API, pre-cached for 119th Congress

## Award Matching

- [x] **AWARD-01**: Per-CFDA USASpending Tribal award queries with full pagination and `recipient_type_names: ["tribal"]` filter — not limited to top 10
- [x] **AWARD-02**: Two-tier Tribal name matching: curated alias table (primary) + rapidfuzz token_sort_ratio >= 85 fallback, with state-overlap validation and match confidence scoring

## Hazard Profiling

- [x] **HAZ-01**: FEMA National Risk Index (NRI v1.20) risk ratings for 18 hazard types mapped to Tribal areas from pre-downloaded CSV, with overall risk score, top hazards, expected annual loss, and social vulnerability
- [x] **HAZ-02**: USFS Wildfire Risk to Communities data integrated per Tribe from pre-downloaded tabular data

## Economic Impact

- [x] **ECON-01**: District-level economic impact framing per Tribe per program: USASpending obligations x published multiplier ranges (~2.0x), plus FEMA 4:1 benefit-cost ratio for mitigation programs, with citable methodology

## DOCX Generation

- [x] **DOC-01**: python-docx programmatic DOCX construction engine with professional formatting — tables, headers/footers, page breaks, consistent styles via style reference document
- [x] **DOC-02**: 16 per-program Hot Sheets per Tribe, each containing: program status (CI, advocacy goal), Tribe-specific award history, local hazard relevance, district economic impact, and congressional delegation
- [x] **DOC-03**: Advocacy language per program assembled from decision engine classifications, program inventory tightened_language, and advocacy_lever fields — template-based, not AI-generated
- [x] **DOC-04**: Five Structural Asks woven into per-program Hot Sheets showing which asks advance which programs, with Tribe-specific evidence from award and hazard data
- [ ] **DOC-05**: Document 1 — FY26 [Tribe Name] Climate Resilience Program Priorities: per-Tribe DOCX (592 variants) with cover page, executive summary, delegation section, 16 Hot Sheets, hazard profile, structural asks, and appendix
- [ ] **DOC-06**: Document 2 — FY26 Federal Funding Overview & Strategy: shared DOCX with appropriations landscape, ecoregion strategic priorities, science infrastructure threats, FEMA analysis, cross-cutting framework, and messaging guidance

## Operations

- [ ] **OPS-01**: `--prep-packets --all-tribes` CLI mode for batch generation of all 592 Tribe packets plus strategic overview
- [ ] **OPS-02**: `--prep-packets --tribe <name>` CLI mode for ad-hoc single-Tribe packet generation
- [ ] **OPS-03**: Change tracking — "Since Last Packet" section in each DOCX showing CI status changes, new awards, advocacy goal shifts, and new legislative threats since previous generation

## Traceability

| Requirement | Source | Complexity | Phase | Status |
|-------------|--------|------------|-------|--------|
| REG-01 | TS-01 | Low | Phase 5 | Complete |
| REG-02 | DF-04 | Medium | Phase 5 | Complete |
| REG-03 | TS-01 | Low | Phase 5 | Complete |
| CONG-01 | TS-03, C-4 | Medium | Phase 5 | Complete |
| CONG-02 | TS-03 | Medium | Phase 5 | Complete |
| AWARD-01 | TS-04, C-5 | Medium | Phase 6 | Complete |
| AWARD-02 | TS-04, C-1 | High | Phase 6 | Complete |
| HAZ-01 | DF-01 | High | Phase 6 | Complete |
| HAZ-02 | DF-01 | Medium | Phase 6 | Complete |
| ECON-01 | DF-02, C-3 | Medium | Phase 7 | Complete |
| DOC-01 | TS-06 | Medium | Phase 7 | Complete |
| DOC-02 | TS-02 | High | Phase 7 | Complete |
| DOC-03 | TS-05 | Medium | Phase 7 | Complete |
| DOC-04 | DF-05 | Low | Phase 7 | Complete |
| DOC-05 | TS-01+TS-02 | High | Phase 8 | Pending |
| DOC-06 | TS-07 | Medium | Phase 8 | Pending |
| OPS-01 | TS-08 | Low | Phase 8 | Pending |
| OPS-02 | TS-08 | Low | Phase 8 | Pending |
| OPS-03 | DF-03 | Medium | Phase 8 | Pending |

## Coverage

- Research Table Stakes (8): All 8 covered (TS-01->REG-01/REG-03, TS-02->DOC-02, TS-03->CONG-01/CONG-02, TS-04->AWARD-01/AWARD-02, TS-05->DOC-03, TS-06->DOC-01, TS-07->DOC-06, TS-08->OPS-01/OPS-02)
- Research Differentiators (5): All 5 covered (DF-01->HAZ-01/HAZ-02, DF-02->ECON-01, DF-03->OPS-03, DF-04->REG-02, DF-05->DOC-04)
- Research Anti-Features (6): All 6 respected as out-of-scope constraints
- Research Critical Pitfalls (5): All 5 addressed (C-1->AWARD-02, C-2->HAZ design, C-3->ECON-01, C-4->CONG-01, C-5->AWARD-01 pre-cache)

## Out of Scope (Anti-Features)

- **AF-01**: No Tribal-specific sensitive data collection (enrollment, governance, cultural sites) -- T0 only
- **AF-02**: No AI/LLM text generation for advocacy language -- template-based assembly only
- **AF-03**: No real-time document editing or collaboration features
- **AF-04**: ~~No per-Tribe program filtering~~ **Superseded** -- ProgramRelevanceFilter returns 8-12 relevant programs per Tribe based on hazard profile, ecoregion, and priority; omitted programs appear in appendix
- **AF-05**: No web UI or frontend dashboard
- **AF-06**: No BEA RIMS II purchase -- use FEMA BCR + published multipliers

---
*Created: 2026-02-10 from research/FEATURES.md, research/ARCHITECTURE.md, research/PITFALLS.md*
*Traceability updated: 2026-02-10 after roadmap creation*
