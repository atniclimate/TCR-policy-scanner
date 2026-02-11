# Requirements: TCR Policy Scanner v1.2

**Defined:** 2026-02-11
**Core Value:** Tribal Leaders get timely, accurate, machine-scored policy intelligence that surfaces federal developments relevant to their climate resilience programs.

## v1.2 Requirements

### Config Hardening

- [x] **CONF-01**: Structural asks path resolved via config/pathlib (not hardcoded string)
- [x] **CONF-02**: Centralized path constants module (`src/paths.py`) for all data/config file paths

### Code Quality

- [ ] **QUAL-01**: All 16 programs in `program_inventory.json` have complete field coverage (cfda, access_type, funding_type)
- [ ] **QUAL-02**: Dead code and unused imports removed codebase-wide (`ruff check` passes clean)

### API Resilience

- [ ] **RESL-01**: Circuit breaker pattern (CLOSED/OPEN/HALF_OPEN) wraps all external API calls
- [ ] **RESL-02**: Configurable retry counts and backoff multipliers in `scanner_config.json`
- [ ] **RESL-03**: Pipeline completes using cached data when an API is unreachable
- [ ] **RESL-04**: Health check reports API availability status for all 4 sources

### Award Data Population

- [ ] **AWRD-01**: Batch USASpending queries by CFDA number (11 program queries, not 592 Tribe queries)
- [ ] **AWRD-02**: Two-tier Tribe matching (curated alias table primary + rapidfuzz fallback >= 85)
- [ ] **AWRD-03**: Award cache files populated for 592 Tribes with real USASpending data
- [ ] **AWRD-04**: 450+ Tribes have at least one non-zero award record

### Hazard Data Population

- [ ] **HZRD-01**: FEMA NRI county-level dataset downloaded and cached
- [ ] **HZRD-02**: Tribe-to-county geographic crosswalk built (AIANNH + county boundaries)
- [ ] **HZRD-03**: County NRI scores aggregated to Tribe level (area-weighted)
- [ ] **HZRD-04**: Top 5 hazards per Tribe extracted and ranked
- [ ] **HZRD-05**: USFS wildfire risk data populated for fire-prone Tribes (300+)
- [ ] **HZRD-06**: Hazard profile files populated for 592 Tribes with real data

### Integration & Validation

- [ ] **INTG-01**: Economic impact section auto-computes using real award + hazard data
- [ ] **INTG-02**: End-to-end packet generation produces complete packets for 400+ Tribes
- [ ] **INTG-03**: Data validation script reports coverage across all data caches
- [ ] **INTG-04**: VERIFICATION.md documents v1.2 testing methodology
- [ ] **INTG-05**: GitHub Pages deployment config finalized
- [ ] **INTG-06**: SquareSpace placeholder URL replaced with production URL

## Already Completed (Fire Keeper, 2026-02-11)

These tech debt items were resolved during the research phase:

- [x] **TD-01**: Config-driven fiscal year (new `src/config.py` with dynamic fiscal year)
- [x] **TD-02**: Config-driven `graph_schema.json` path (PROJECT_ROOT via pathlib)
- [x] **TD-05**: Deduplicate `_format_dollars` (new `src/utils.py` as single source of truth)
- [x] **TD-06**: Fix logger naming (14 files fixed to `__name__`)

## Future Requirements

### Enrichment Layer (v1.3 candidates)

- **ENRICH-01**: Real-time congressional alert system (21 SP)
- **ENRICH-02**: Confidence scoring for intelligence products
- **ENRICH-03**: Interactive knowledge graph visualization (D3.js)
- **ENRICH-04**: OpenFEMA disaster declarations integration
- **ENRICH-05**: Grants.gov opportunity section in packets
- **ENRICH-06**: Committee assignment enrichment from Congress.gov

### Pipeline Maturity (v1.3+ candidates)

- **PIPE-01**: Scraper pagination (3 of 4 scrapers silently truncate)
- **PIPE-02**: Congress.gov bill detail fetching (sponsors, committees, summaries)
- **PIPE-03**: UEI field for deterministic entity linking

## Out of Scope

| Feature | Reason |
|---------|--------|
| Tribal-specific data collection | T0 data only; public federal sources |
| Real-time streaming | Batch scan architecture |
| Non-climate policy domains | TCR focus; config-driven for future expansion |
| Interactive web dashboard | Static search+download widget shipped v1.1 |
| RIMS II multipliers | Cost-prohibitive ($500/region); published multipliers sufficient |
| Scraper pagination fixes | Important but separate concern; v1.3 candidate |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| CONF-01 | Phase 9 | Complete |
| CONF-02 | Phase 9 | Complete |
| QUAL-01 | Phase 10 | Pending |
| QUAL-02 | Phase 10 | Pending |
| RESL-01 | Phase 11 | Pending |
| RESL-02 | Phase 11 | Pending |
| RESL-03 | Phase 11 | Pending |
| RESL-04 | Phase 11 | Pending |
| AWRD-01 | Phase 12 | Pending |
| AWRD-02 | Phase 12 | Pending |
| AWRD-03 | Phase 12 | Pending |
| AWRD-04 | Phase 12 | Pending |
| HZRD-01 | Phase 13 | Pending |
| HZRD-02 | Phase 13 | Pending |
| HZRD-03 | Phase 13 | Pending |
| HZRD-04 | Phase 13 | Pending |
| HZRD-05 | Phase 13 | Pending |
| HZRD-06 | Phase 13 | Pending |
| INTG-01 | Phase 14 | Pending |
| INTG-02 | Phase 14 | Pending |
| INTG-03 | Phase 14 | Pending |
| INTG-04 | Phase 14 | Pending |
| INTG-05 | Phase 14 | Pending |
| INTG-06 | Phase 14 | Pending |

**Coverage:**
- v1.2 requirements: 24 total (+ 4 already completed by Fire Keeper)
- Mapped to phases: 24/24
- Orphaned: 0

---
*Requirements defined: 2026-02-11*
*Last updated: 2026-02-11 after roadmap creation*
