# Milestone Plan: v1.2 Tech Debt Cleanup + Data Foundation

**Author:** Horizon Walker, TCR Policy Scanner Research Team
**Date:** 2026-02-11
**Status:** Planning
**Target:** After v1.2, every Tribal Leader who uses this tool will have an advocacy packet backed by real federal data -- award histories, hazard profiles, and economic impact framing -- not placeholders.

---

## Strategic Context

v1.0 built the pipeline. v1.1 built the packets. v1.2 makes them real.

The TCR Policy Scanner shipped v1.1 on 2026-02-10 with 18,546 LOC across 52 source
files, 287 tests, and the ability to generate per-Tribe DOCX advocacy packets for
all 592 federally recognized Tribal Nations. The architecture is sound. The document
engine works. The web distribution widget is deployed.

But three of five major packet sections are running on placeholder data. The award
caches show zero awards. The hazard profiles show zero risk scores. The economic
impact section has nothing to compute against. A Tribal Leader downloading their
packet today gets excellent identity and delegation data, and three empty sections.

v1.2 closes this gap. It is simultaneously a tech debt cleanup (10 known items)
and a data foundation build (populating the caches that make packets valuable).
The tech debt items are necessary prerequisites: you cannot populate data caches
reliably without config-driven paths, proper error handling, and circuit breakers
for API failures.

**After v1.2:**
- Every Tribe's packet has real USASpending award data (450+ Tribes with awards)
- Every Tribe's packet has FEMA NRI hazard risk scores (550+ Tribes with data)
- Every Tribe's packet has economic impact framing (400+ Tribes with projections)
- The codebase is clean, tested, and ready for the enrichment features of v1.3

## Milestone Objectives

1. **Eliminate all 10 documented tech debt items** -- hardcoded paths, fiscal years,
   duplicated functions, missing tests, documentation gaps
2. **Populate USASpending award caches** for all 592 Tribes against live API data
3. **Populate FEMA NRI hazard profiles** for all 592 Tribes using county-level data
4. **Activate economic impact computation** using real award and hazard data
5. **Add circuit breaker / retry patterns** for all API interactions
6. **Achieve 90%+ packet completeness** across the Tribe population

## Phase Breakdown

### Phase 9: Config Hardening (3 SP, Sprint 1)

**Objective:** Eliminate every hardcoded value that should be configuration-driven.

| Requirement | Description | Files |
|-------------|-------------|-------|
| TD-01 | Config-driven fiscal year (replace all FY26 hardcoding) | scanner_config.json, DOCX output, monitors |
| TD-02 | Config-driven graph_schema.json path (resolve via PROJECT_ROOT) | src/graph/builder.py |
| TD-03 | Config-driven structural asks path | src/graph/builder.py |
| TD-04 | Centralized path constants module | New: src/paths.py |

**Success criteria:**
- `grep -r "FY26" src/` returns zero hardcoded fiscal year strings
- `grep -r "data/graph_schema" src/` returns zero hardcoded path strings
- All paths resolve via `Path(__file__).resolve().parent.parent` pattern
- Existing 287 tests still pass

**How this serves Tribal Nations:** Config hardening means the scanner can be
reconfigured for FY27, FY28, and beyond without code changes. Tribal climate
coordinators who use this tool across fiscal years get continuous value without
waiting for a developer to update hardcoded strings.

---

### Phase 10: Code Quality Sweep (3 SP, Sprint 1)

**Objective:** Clean up duplicated functions, inconsistent naming, and incomplete fields.

| Requirement | Description | Files |
|-------------|-------------|-------|
| TD-05 | Deduplicate _format_dollars (single utils.format_dollars) | All files with local formatting |
| TD-06 | Fix logger naming (all use logging.getLogger(__name__)) | src/packets/relevance.py, others |
| TD-07 | Complete program fields (fill missing cfda, access_type) | data/program_inventory.json |
| TD-08 | Remove dead code and unused imports | Codebase-wide |

**Success criteria:**
- `grep -r "_format_dollars" src/` returns zero results (only format_dollars)
- `grep -r 'getLogger("' src/` returns zero hardcoded logger name strings
- All 16 programs have complete field coverage
- `ruff check .` and `mypy src/` pass clean

**How this serves Tribal Nations:** Code quality is maintenance velocity. Clean code
means faster bug fixes, easier feature additions, and more reliable operation. Every
hour saved on debugging is an hour available for building features that serve Tribes.

---

### Phase 11: API Resilience (5 SP, Sprint 2)

**Objective:** Circuit breaker and retry patterns for all external API calls.

| Requirement | Description | Files |
|-------------|-------------|-------|
| TD-09 | Circuit breaker pattern for transient API failures | src/scrapers/base.py |
| TD-10 | Configurable retry counts and backoff | scanner_config.json |
| TD-11 | Graceful degradation (use cached data if API fails) | All scrapers, packet builders |
| TD-12 | Health check endpoint for API status | New: src/health.py |

**Implementation:**

```python
class CircuitBreaker:
    """Three-state circuit breaker (CLOSED -> OPEN -> HALF_OPEN).

    CLOSED: Normal operation, requests pass through
    OPEN: API has failed N times, skip requests for cooldown_seconds
    HALF_OPEN: After cooldown, allow one probe request to test recovery
    """
    def __init__(self, failure_threshold: int = 5, cooldown_seconds: int = 300):
        ...
```

**Success criteria:**
- BaseScraper wraps all requests in circuit breaker
- 5 consecutive failures trigger OPEN state (5-minute cooldown)
- Pipeline completes even if one API is down (uses cached data)
- New integration tests verify circuit breaker behavior
- Tests: 15-20 new tests

**How this serves Tribal Nations:** The scanner runs daily via GitHub Actions. If
USASpending is down for maintenance at 6 AM when the scan runs, the current system
fails silently and produces stale data. With circuit breakers, the system fails
gracefully, uses cached data, logs the failure, and retries on the next cycle.
Tribal Leaders get the most current data available, always.

---

### Phase 12: Award Cache Population (5 SP, Sprint 2)

**Objective:** Populate USASpending award data for all 592 Tribes.

| Requirement | Description | Files |
|-------------|-------------|-------|
| DATA-01 | Batch USASpending query by CFDA (11 program CFDAs) | scripts/populate_awards.py |
| DATA-02 | Two-tier Tribe matching (alias table + rapidfuzz) | src/packets/awards.py |
| DATA-03 | Write populated award cache files | data/award_cache/*.json |
| DATA-04 | Validate coverage (target: 450+ Tribes with awards) | scripts/validate_data.py |

**Batch strategy:**
1. Query USASpending by CFDA number (11 queries, not 592)
2. For each result, match recipient to Tribe via alias table
3. Fallback to rapidfuzz matching (score >= 85) for unmatched
4. Aggregate by Tribe, write to cache files
5. Log match statistics (matched, unmatched, ambiguous)

**Success criteria:**
- 450+ of 592 Tribes have at least one award record
- Total obligation amounts are non-zero and plausible
- CFDA summary field populated for each Tribe
- Award count matches between cache files and API query totals
- Tests: 10-15 new tests

**How this serves Tribal Nations:** When a Tribal Leader opens their packet and sees
"Your community has received $2.3M in federal climate resilience funding across 4
programs since FY2020," that number changes the conversation. It transforms the
meeting from "we need help" to "here is the proven return on your investment in our
community, and here is why the next dollar matters even more."

---

### Phase 13: Hazard Profile Population (8 SP, Sprint 3)

**Objective:** Populate FEMA NRI hazard data for all 592 Tribes.

| Requirement | Description | Files |
|-------------|-------------|-------|
| DATA-05 | Download FEMA NRI county-level dataset | scripts/download_nri.py |
| DATA-06 | Build Tribe-to-county geographic crosswalk | scripts/build_county_crosswalk.py |
| DATA-07 | Aggregate county NRI scores to Tribe level | src/packets/hazards.py |
| DATA-08 | Extract top 5 hazards per Tribe | src/packets/hazards.py |
| DATA-09 | Populate USFS wildfire risk data | src/packets/hazards.py |
| DATA-10 | Write populated hazard profile files | data/hazard_profiles/*.json |

**Geographic crosswalk approach:**
1. Census TIGER/Line AIANNH boundaries (existing, used for CD mapping)
2. Census TIGER/Line county boundaries
3. Spatial intersection: which counties overlap each AIANNH area
4. Weight NRI scores by area overlap fraction
5. For Tribes without AIANNH boundaries, fallback to state-level data

**Success criteria:**
- 550+ of 592 Tribes have non-zero NRI risk scores
- Top 5 hazards populated for all Tribes with county data
- Composite risk rating (risk_score, sovi_score, resl_score) populated
- USFS wildfire data populated for Tribes in fire-prone regions (300+)
- Tests: 15-20 new tests

**How this serves Tribal Nations:** Hazard data is the foundation of every climate
resilience funding argument. When a Tribal Leader can point to "FEMA NRI rates our
community as HIGH risk for wildfire with an expected annual loss of $4.2M," that
data carries the weight of the federal government's own risk assessment. It is
not opinion. It is not anecdote. It is quantified risk that demands quantified
investment.

---

### Phase 14: Integration and Validation (5 SP, Sprint 3)

**Objective:** Wire everything together, validate end-to-end, update documentation.

| Requirement | Description | Files |
|-------------|-------------|-------|
| INT-01 | Economic impact auto-activation (uses real data) | src/packets/economic.py |
| INT-02 | End-to-end packet generation with populated data | tests/test_e2e.py |
| INT-03 | Data validation script (coverage report) | scripts/validate_data.py |
| INT-04 | Documentation updates (VERIFICATION.md) | docs/VERIFICATION.md |
| INT-05 | GitHub Pages deployment config cleanup | docs/web/, .github/ |
| INT-06 | SquareSpace placeholder URL replacement | docs/web/js/app.js |

**Validation checklist:**
- [ ] Generate packets for 10 sample Tribes across diverse geographies
- [ ] Verify award data appears in Section 4
- [ ] Verify hazard data appears in Section 3
- [ ] Verify economic impact computes in Section 5
- [ ] Verify DOCX formatting is correct with real data (table widths, page breaks)
- [ ] Verify batch generation (all 592) completes without error
- [ ] Verify web widget serves updated packets
- [ ] Run full test suite (target: 320+ tests, up from 287)

**Success criteria:**
- End-to-end packet generation produces complete packets for 400+ Tribes
- Overall packet completeness rises from ~39% to ~87%
- All documentation gaps closed
- GitHub Actions daily-scan.yml runs cleanly with new data population steps
- Tests: 10-15 new tests (integration + E2E)

**How this serves Tribal Nations:** Integration testing is the final quality gate.
Before v1.2 ships, we verify that real data flows correctly through every stage of
the pipeline and appears correctly in every section of every packet. A Tribal Leader
who downloads their packet on the day v1.2 ships gets a document that has been
validated end-to-end against actual federal data.

## Phase Dependencies

```
Phase 9 (Config Hardening) ──┐
                              ├── Phase 11 (API Resilience) ──┐
Phase 10 (Code Quality) ─────┘                                │
                                                               ├── Phase 14 (Integration)
Phase 12 (Award Population) ──────────────────────────────────┤
                                                               │
Phase 13 (Hazard Population) ─────────────────────────────────┘
```

- Phases 9 + 10 can run in parallel (Sprint 1)
- Phases 11 + 12 can run in parallel (Sprint 2) -- both depend on Phases 9/10
- Phase 13 depends on geographic crosswalk work (Sprint 3)
- Phase 14 depends on all prior phases (Sprint 3, second half)

## Sprint Plan

| Sprint | Phases | SP | Focus |
|--------|--------|-----|-------|
| Sprint 1 (Week 1-2) | Phase 9, Phase 10 | 6 | Config + code quality |
| Sprint 2 (Week 3-4) | Phase 11, Phase 12 | 10 | API resilience + awards |
| Sprint 3 (Week 5-6) | Phase 13, Phase 14 | 13 | Hazards + integration |

**Total: 29 SP across 3 sprints (~6 weeks)**

## Success Metrics

| Metric | Current (v1.1) | Target (v1.2) |
|--------|---------------|---------------|
| Packet completeness (avg) | ~39% | 87%+ |
| Tribes with award data | 0 | 450+ |
| Tribes with hazard data | 0 | 550+ |
| Tribes with economic impact | 0 | 400+ |
| Tech debt items | 10 | 0 |
| Test count | 287 | 320+ |
| API resilience | None | Circuit breaker on all scrapers |
| Config hardcoded values | 10+ | 0 |

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| USASpending API changes | Low | High | Pin API version, add response schema validation |
| NRI data format changes | Low | Medium | Version check on download, schema validation |
| Tribe-to-county crosswalk gaps | Medium | Medium | State-level fallback with reduced confidence |
| GitHub Actions CI minutes | Low | Low | Cache API responses between runs |
| Award matching false positives | Medium | High | Validate sample, require state overlap, manual review flag |
| Hazard score aggregation errors | Medium | Medium | Validate against known high-risk counties |

## What Comes Next (v1.3 Preview)

Once v1.2 establishes the data foundation, v1.3 builds the enrichment layer:

- **Real-Time Congressional Alerts** (see `docs/proposals/congressional-alerts.md`)
- **Interactive Knowledge Graph** (see `docs/proposals/knowledge-graph-interactive.md`)
- **Confidence Scoring** (see `docs/proposals/confidence-scoring.md`)
- **OpenFEMA Disaster Declarations** (Priority 4 from data completeness roadmap)
- **Grants.gov Opportunity Section** (Priority 5 from data completeness roadmap)
- **Committee Assignment Enrichment** (Priority 6 from data completeness roadmap)

The proposals are written. The roadmap is ordered. When v1.2 ships, the team picks
up the next set of enhancements with a solid, data-complete foundation underneath.

## Impact Statement

After v1.2, every Tribal Leader who downloads their advocacy packet will have:

- **Real numbers.** Not placeholders. Federal award amounts pulled from USASpending,
  validated against their Tribe's name aliases, organized by program.

- **Real risk data.** FEMA's own National Risk Index scores for the counties where
  their Tribe lives, with the top 5 hazards ranked and quantified.

- **Real economic arguments.** "Every $1 invested in mitigation for your community
  yields $4 in avoided disaster costs" -- backed by actual FEMA benefit-cost ratios
  applied to actual award amounts.

- **Real delegation intelligence.** Their senators, their representatives, matched
  to their specific geographic and programmatic needs.

- **Real advocacy power.** A complete, data-driven document that transforms a
  congressional meeting from "please help us" to "here is the evidence that investing
  in our resilience is the right choice."

The difference between v1.1 and v1.2 is the difference between a framework and a
tool. v1.1 proved we can build the packet. v1.2 proves the packet can change a
meeting.

592 Tribal Nations. Real data in every packet. That is what v1.2 delivers.

---

*Planned by Horizon Walker. The architecture exists. The data is waiting. Let us connect them.*
