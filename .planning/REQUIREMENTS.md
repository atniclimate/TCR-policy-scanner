# Requirements: TCR Policy Scanner

**Defined:** 2026-02-09
**Core Value:** Tribal Leaders get timely, accurate policy intelligence for FY26 climate resilience advocacy

## v1 Requirements

### Pipeline Validation

- [x] **PIPE-01**: All 4 scrapers (Federal Register, Grants.gov, Congress.gov, USASpending) return valid data from live APIs
- [x] **PIPE-02**: End-to-end pipeline produces LATEST-BRIEFING.md and LATEST-RESULTS.json from real scan data
- [x] **PIPE-03**: GitHub Actions daily-scan.yml runs successfully on schedule (weekday 6 AM Pacific)
- [x] **PIPE-04**: Change detector correctly identifies new/modified/removed items between scan cycles

### Data Model Updates

- [x] **DATA-01**: All 16 programs have CI scores assigned (no gaps) with Hot Sheets-aligned statuses
- [x] **DATA-02**: SECURE, UNCERTAIN, TERMINATED status categories added to policy_tracking.json CI thresholds
- [x] **DATA-03**: IRS Elective Pay reclassified AT_RISK (CI: 0.55); DOT PROTECT reclassified SECURE (CI: 0.93)
- [x] **DATA-04**: Reconciliation/repeal trigger keywords added to scanner_config.json and relevant program entries
- [x] **DATA-05**: BIA TCR Awards and EPA Tribal Air Quality programs present in program_inventory.json with full metadata

### Graph Enhancements

- [x] **GRAPH-01**: Graph builder loads Five Structural Asks from graph_schema.json as AdvocacyLeverNodes
- [x] **GRAPH-02**: ADVANCES edge type connects Structural Asks to program nodes
- [x] **GRAPH-03**: 10 new statutory authorities from Strategic Framework added to graph_schema.json
- [x] **GRAPH-04**: 6 new barriers from Strategic Framework added to graph_schema.json
- [x] **GRAPH-05**: Trust Super-Node (FEDERAL_TRUST_RESPONSIBILITY) implemented with TRUST_OBLIGATION edges to BIA/EPA programs

### Monitoring Capabilities

- [x] **MON-01**: IIJA sunset tracker flags programs approaching FY26 expiration with no reauthorization bill
- [x] **MON-02**: Reconciliation monitor tracks House/Senate bills for IRA section 6417 repeal provisions
- [x] **MON-03**: Tribal consultation tracker detects DTLLs, consultation notices, EO 13175 compliance signals
- [x] **MON-04**: Hot Sheets sync validation compares scanner CI vs Hot Sheets positions after each scan cycle
- [x] **MON-05**: DHS funding cliff tracker surfaces FEMA-related nodes when DHS CR approaches expiration

### Report Enhancements

- [ ] **RPT-01**: Five Structural Asks section in LATEST-BRIEFING.md mapping to barrier mitigation pathways
- [ ] **RPT-02**: Hot Sheets sync status indicator showing alignment/divergence per program
- [ ] **RPT-03**: IIJA Sunset Countdown for affected programs
- [ ] **RPT-04**: Historical CI trend tracking — score trajectories over time
- [ ] **RPT-05**: Reconciliation Watch section when relevant bills detected
- [ ] **RPT-06**: Advocacy goal classification per scanner decision logic (5 rules from FY26 Reference)

### Scanner Decision Logic

- [x] **LOGIC-01**: Rule 1 — Restore/Replace: TERMINATED program + ACTIVE authority triggers restore advocacy
- [x] **LOGIC-02**: Rule 2 — Protect Base: DISCRETIONARY funding + ELIMINATE/REDUCE signal triggers protect advocacy
- [x] **LOGIC-03**: Rule 3 — Direct Access Parity: STATE_PASS_THROUGH access + HIGH burden triggers parity advocacy
- [x] **LOGIC-04**: Rule 4 — Expand and Strengthen: STABLE/SECURE status + DIRECT/SET_ASIDE access triggers growth advocacy
- [x] **LOGIC-05**: Rule 5 — Urgent Stabilization: THREATENS edge within 30 days overrides all other classifications

## v2 Requirements

### Testing

- **TEST-01**: Unit tests for relevance scorer (all 5 factors, critical boost, eligibility override)
- **TEST-02**: Unit tests for graph builder (node creation, edge linking, Five Structural Asks)
- **TEST-03**: Unit tests for each scraper normalizer (Federal Register, Grants.gov, Congress.gov, USASpending)
- **TEST-04**: Integration test for full pipeline (ingest through report generation)
- **TEST-05**: Mock API fixtures for offline testing

### Repository Restructure

- **REPO-01**: Individual program node JSON files in data/programs/
- **REPO-02**: Statutory authority node JSON files in data/authorities/
- **REPO-03**: Time-bound scenario JSON files in data/scenarios/
- **REPO-04**: Schema definitions in schema/ directory (node_types, edge_types, validation_rules)
- **REPO-05**: Markdown-to-graph ingestion from FY26 Reference document

### Advanced Monitoring

- **ADV-01**: Cross-program correlation — detect simultaneous threats to multiple programs
- **ADV-02**: Advocacy effectiveness tracking — correlation between levers and policy changes
- **ADV-03**: Domain adaptability — extend scanner to non-climate Tribal policy domains
- **ADV-04**: 3-tier update cycle (weekly scenario, monthly status, quarterly barrier)

## Out of Scope

| Feature | Reason |
|---------|--------|
| Tribal-specific data collection | T0 (Open) classification — public federal sources only |
| Frontend dashboard | CLI and markdown/JSON output for v1 |
| Real-time streaming | Batch scan architecture |
| Non-climate policy domains | v1 focused on TCR; config supports future expansion |
| Production hosting beyond GitHub Actions | GitHub Actions sufficient for daily scans |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| PIPE-01 | Phase 1 | Complete |
| PIPE-02 | Phase 1 | Complete |
| PIPE-03 | Phase 1 | Complete |
| PIPE-04 | Phase 1 | Complete |
| DATA-01 | Phase 2 | Complete |
| DATA-02 | Phase 2 | Complete |
| DATA-03 | Phase 2 | Complete |
| DATA-04 | Phase 2 | Complete |
| DATA-05 | Phase 2 | Complete |
| GRAPH-01 | Phase 2 | Complete |
| GRAPH-02 | Phase 2 | Complete |
| GRAPH-03 | Phase 2 | Complete |
| GRAPH-04 | Phase 2 | Complete |
| GRAPH-05 | Phase 2 | Complete |
| MON-01 | Phase 3 | Complete |
| MON-02 | Phase 3 | Complete |
| MON-03 | Phase 3 | Complete |
| MON-04 | Phase 3 | Complete |
| MON-05 | Phase 3 | Complete |
| RPT-01 | Phase 4 | Pending |
| RPT-02 | Phase 4 | Pending |
| RPT-03 | Phase 4 | Pending |
| RPT-04 | Phase 4 | Pending |
| RPT-05 | Phase 4 | Pending |
| RPT-06 | Phase 4 | Pending |
| LOGIC-01 | Phase 3 | Complete |
| LOGIC-02 | Phase 3 | Complete |
| LOGIC-03 | Phase 3 | Complete |
| LOGIC-04 | Phase 3 | Complete |
| LOGIC-05 | Phase 3 | Complete |

**Coverage:**
- v1 requirements: 31 total
- Mapped to phases: 31
- Unmapped: 0

---
*Requirements defined: 2026-02-09*
*Last updated: 2026-02-09 after Phase 3 completion*
