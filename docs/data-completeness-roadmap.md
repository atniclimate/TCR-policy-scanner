# Data Completeness Roadmap

**Status:** Active
**Requirement:** INTEL-15
**Date:** 2026-02-12
**Scope:** All data sources feeding 592 Tribal Nation advocacy packets

---

## 1. Current Data Sources

The TCR Policy Scanner integrates 8 data sources to produce per-Tribe advocacy packets. Each source has a measured coverage level (percentage of 592 federally recognized Tribal Nations with data), a confidence rating, and a gap remediation plan.

### 1.1 Coverage Summary

| # | Source | Coverage | Confidence | Gap Count | Refresh Cadence | Next Step |
|---|--------|----------|------------|-----------|-----------------|-----------|
| 1 | EPA Tribal Registry | 592/592 (100.0%) | HIGH | 0 | Quarterly | Stable -- authoritative source of truth |
| 2 | Congressional Delegation Cache | 501/592 (84.6%) | HIGH | 91 | Monthly | Improve AIANNH geographic crosswalk |
| 3 | USASpending Awards | 451/592 (76.2%) | HIGH | 141 | Monthly | Housing authority alias curation |
| 4 | FEMA NRI Hazard Profiles | 573/592 (96.8%) | HIGH | 19 | Annual | Manual review of unmatched Tribal Nations |
| 5 | USFS Wildfire Risk | 573/592 (96.8%) | HIGH | 19 | Annual | Shared coverage with NRI (same crosswalk) |
| 6 | Congressional Intelligence | NEW | MEDIUM | TBD | Daily (weekday) | Phase 15 delivery |
| 7 | Federal Register Monitor | N/A (scan-based) | HIGH | 0 | Daily | Pagination hardening (Phase 15) |
| 8 | Grants.gov Monitor | N/A (scan-based) | MEDIUM | 0 | Daily | Pagination hardening (Phase 15) |

### 1.2 Source Details

**1. EPA Tribal Registry** (`data/tribal_registry.json`)
- Authority: EPA Tribal internal registry via API
- Records: 592 Tribal Nations with tribe_id, name, states, BIA code, EPA ID
- Quality: Canonical -- all other sources match against this registry
- Gap: None. This is the authoritative list.

**2. Congressional Delegation Cache** (`data/congressional_cache.json`)
- Authority: Congress.gov API + AIANNH geographic crosswalk
- Records: 501 Tribal Nations mapped to Senators, Representatives, districts
- Quality: High for mapped Tribal Nations; geographic overlap percentages computed from census boundaries
- Gap: 91 Tribal Nations lack delegation mappings due to missing or ambiguous AIANNH boundary polygons (primarily Alaska Native villages with complex land status)

**3. USASpending Awards** (`data/award_cache/*.json`)
- Authority: USASpending.gov API (14 CFDAs x 5 fiscal years)
- Records: 451 Tribal Nations with award history totals
- Quality: High confidence where matched; two-tier matching (alias table O(1) dict + rapidfuzz >= 85 fallback)
- Gap: 141 Tribal Nations with zero awards. Root causes: (a) housing authority name mismatches (60%), (b) no federal awards received (25%), (c) regional Alaska housing authorities serving multiple Nations (15%)

**4. FEMA NRI Hazard Profiles** (`data/hazard_profiles/*.json`)
- Authority: FEMA National Risk Index county-level data + AIANNH geographic crosswalk
- Records: 573 Tribal Nations with multi-hazard risk scores
- Quality: High -- county-level data aggregated to Tribal boundaries
- Gap: 19 Tribal Nations, mostly small Oklahoma Tribal Nations with complex jurisdictional boundaries that don't cleanly map to NRI county data

**5. USFS Wildfire Risk** (integrated into hazard profiles)
- Authority: USFS Wildfire Risk to Communities (conditional risk to structures)
- Records: 573 Tribal Nations (same coverage as NRI, shared crosswalk)
- Quality: High -- USFS wildfire overrides NRI wildfire when both > 0
- Gap: Same 19 Tribal Nations as NRI

**6. Congressional Intelligence** (`data/congressional_intel.json`)
- Authority: Congress.gov API v3 (119th Congress)
- Records: NEW -- being built in Phase 15
- Quality: Medium (new pipeline, relevance scoring not yet validated at scale)
- Gap: TBD -- depends on bill-to-program mapping coverage

**7. Federal Register Monitor** (scan-based, `outputs/`)
- Authority: Federal Register API (federalregister.gov)
- Records: N/A -- scans for Tribal-relevant notices, not per-Tribe data
- Quality: High for detected notices; pagination fix in Phase 15 ensures zero truncation
- Gap: Not applicable (monitors, not per-Tribe)

**8. Grants.gov Monitor** (scan-based, `outputs/`)
- Authority: Grants.gov API
- Records: N/A -- scans for Tribal-relevant grant opportunities
- Quality: Medium (API occasionally returns incomplete results)
- Gap: Not applicable (monitors, not per-Tribe)

---

## 2. Gap Prioritization

Gaps are prioritized by impact on Tribal Leader advocacy effectiveness.

### P1: Congressional Intelligence Bill-to-Program Mapping (NEW)

**Impact:** HIGH -- This is a new capability that directly enables Tribal Leaders to track legislation affecting their programs.

**Current state:** Phase 15 is building the pipeline. Once delivered, every Tribe with a delegation mapping (501/592) will receive bill intelligence matched to their tracked programs.

**Action items:**
1. Complete CongressGovScraper bill detail fetching (Plan 01)
2. Implement bill_relevance_scoring() matching against 16 programs (Plan 01)
3. Validate relevance scores against manually curated test set (Plan 02)
4. Integrate into DOCX packet generation (Plan 04-07)

**Target:** 501/592 Tribal Nations with congressional intelligence in packets (constrained by delegation coverage)

### P2: USASpending Award Coverage (141 Gaps)

**Impact:** MEDIUM-HIGH -- Award data demonstrates federal investment history, strengthening funding arguments in advocacy packets.

**Current state:** 451/592 (76.2%) Tribal Nations matched. Target of 450+ achieved.

**Root cause analysis:**
| Cause | Count | % of Gaps | Remediation |
|-------|-------|-----------|-------------|
| Housing authority name mismatch | ~85 | 60% | Curate additional aliases in `data/housing_authority_aliases.json` |
| No federal awards received | ~35 | 25% | Legitimate -- Tribal Nation has not received awards under tracked CFDAs |
| Regional Alaska HA (multi-Nation) | ~21 | 15% | Excluded by design (Cook Inlet, Bering Straits, Interior, etc.) |

**Action items:**
1. Audit remaining unmatched housing authority names against USASpending recipient data
2. Add curated overrides to `scripts/generate_ha_aliases.py`
3. Regenerate `data/tribal_aliases.json` and re-run pipeline
4. Accept ~35 legitimate zeros (no awards to match)

**Target:** 475/592 (80.2%) -- additional 24 matches from alias curation

### P3: Congressional Delegation Coverage (91 Gaps)

**Impact:** MEDIUM -- Delegation data enables congressional section in packets and alert routing.

**Current state:** 501/592 (84.6%) Tribal Nations mapped to their congressional delegation.

**Root cause:** 91 Tribal Nations (primarily Alaska Native villages) lack AIANNH boundary polygons in the Census TIGER/Line dataset, preventing geographic intersection with congressional districts.

**Action items:**
1. Cross-reference unmatched Tribal Nations against Alaska Native village coordinates (lat/lon)
2. Use point-in-polygon with congressional district shapefiles as fallback
3. For villages with PO Box-only addresses, map to the at-large Alaska delegation (2 Senators + 1 Representative)
4. Manual curation for remaining edge cases

**Target:** 560/592 (94.6%) -- Alaska at-large delegation mapping covers most gaps

### P4: Hazard Profile Gaps (19 Gaps)

**Impact:** LOW-MEDIUM -- Hazard profiles inform program relevance filtering and packet hazard sections.

**Current state:** 573/592 (96.8%) Tribal Nations with hazard profiles.

**Root cause:** 19 Tribal Nations (mostly small Oklahoma Tribal jurisdictions) have boundaries that don't cleanly intersect with FEMA NRI county-level data.

**Action items:**
1. Manual geographic review of 19 unmatched Tribal Nations
2. Attempt county-level fallback (assign nearest county's risk scores)
3. For Tribal Nations with overlapping jurisdictions, use weighted average of all intersecting counties
4. Document any Tribal Nations that genuinely have no mappable geography

**Target:** 585/592 (98.8%) -- county fallback should close most gaps

---

## 3. Confidence Scoring Per Program

The confidence module (Phase 15) assigns a composite confidence score to each of the 16 tracked programs for every Tribal Nation. This score reflects how much data the system has for that Tribe-program combination.

### 3.1 Confidence Formula

```
program_confidence(tribe, program) = weighted_average(
    source_confidence(EPA_registry)     * weight_identity,
    source_confidence(congressional)    * weight_delegation,
    source_confidence(awards)           * weight_funding,
    source_confidence(hazards)          * weight_hazard,
    source_confidence(intel)            * weight_intel
)
```

### 3.2 Source Confidence Levels

| Source | Data Present | Data Absent | Weight |
|--------|-------------|-------------|--------|
| EPA Tribal Registry | 1.0 (always present) | N/A | 0.10 |
| Congressional Cache | 0.9 | 0.3 | 0.20 |
| USASpending Awards | 0.9 (matched) | 0.4 (zero awards, may be legitimate) | 0.25 |
| FEMA NRI Hazards | 0.9 | 0.3 | 0.25 |
| Congressional Intel | 0.7 (new pipeline) | 0.5 (no relevant bills, may be normal) | 0.20 |

### 3.3 Program-Specific Weight Adjustments

Not all data sources are equally important to every program. The weight adjustments reflect which data sources matter most for each program's packet sections.

| Program | Awards Weight | Hazards Weight | Delegation Weight | Intel Weight |
|---------|--------------|----------------|-------------------|--------------|
| BIA TCR | 0.30 | 0.25 | 0.20 | 0.15 |
| FEMA BRIC | 0.25 | 0.30 | 0.15 | 0.20 |
| FEMA Tribal Mitigation | 0.25 | 0.30 | 0.15 | 0.20 |
| HUD IHBG | 0.35 | 0.20 | 0.15 | 0.20 |
| DOE Indian Energy | 0.25 | 0.15 | 0.25 | 0.25 |
| USBR WaterSMART | 0.30 | 0.25 | 0.20 | 0.15 |
| EPA SAG | 0.25 | 0.20 | 0.20 | 0.25 |
| USDA Wildfire | 0.20 | 0.35 | 0.15 | 0.20 |

*(Table shows 8 of 16 programs; remaining follow similar patterns based on program focus area.)*

### 3.4 Confidence Display in Packets

| Composite Score | Badge | Meaning |
|----------------|-------|---------|
| >= 0.80 | **HIGH** | Strong data coverage; recommendations well-supported |
| 0.50 - 0.79 | **MEDIUM** | Partial data; some recommendations based on inference |
| < 0.50 | **LOW** | Limited data; recommendations are directional only |

Badges appear in DOCX packets next to program sections. Tribal Leaders can see at a glance which recommendations are backed by strong data versus which are based on limited information.

---

## 4. Composite Coverage Heatmap

This matrix shows data availability across all sources for a representative sample of Tribal Nations.

```
                    EPA  Cong  Awards  Hazards  Intel  Composite
                    Reg  Cache                         Confidence
Warm Springs        [X]  [X]   [X]     [X]      [~]   HIGH
Yakama Nation       [X]  [X]   [X]     [X]      [~]   HIGH
Nez Perce           [X]  [X]   [X]     [X]      [~]   HIGH
Navajo Nation       [X]  [X]   [X]     [X]      [~]   HIGH
Rosebud Sioux       [X]  [X]   [X]     [X]      [~]   HIGH
Bois Forte Band     [X]  [X]   [X]     [X]      [~]   HIGH
Arctic Village      [X]  [ ]   [ ]     [ ]      [~]   LOW
Kaltag Village      [X]  [ ]   [ ]     [ ]      [~]   LOW
Miami Tribe of OK   [X]  [X]   [X]     [ ]      [~]   MEDIUM

Legend: [X] = Data present  [ ] = Gap  [~] = Pending Phase 15
```

---

## 5. Improvement Roadmap Timeline

| Quarter | Focus | Target Coverage Change |
|---------|-------|----------------------|
| Q1 2026 | Phase 15: Congressional intel pipeline | +501 Tribal Nations with bill intelligence |
| Q1 2026 | Phase 15: Pagination hardening | Federal Register + Grants.gov zero-truncation |
| Q2 2026 | P2: USASpending alias curation round 2 | 451 -> 475 awards coverage (+24) |
| Q2 2026 | P3: Alaska delegation fallback | 501 -> 560 delegation coverage (+59) |
| Q3 2026 | P4: Oklahoma hazard manual review | 573 -> 585 hazard coverage (+12) |
| Q3 2026 | ENH-001: Alert system | Continuous monitoring for 501+ Tribal Nations |
| Q4 2026 | ENH-002: Knowledge graph extension | Graph traversals across all data sources |

---

## 6. Data Quality Principles

1. **Coverage over perfection:** A Tribal Leader with 70% confidence data is better served than one with no data at all. Always generate packets for all 592 Tribal Nations, clearly marking confidence levels.

2. **Transparency:** Every data gap is visible. LOW confidence badges tell Tribal Leaders exactly where data is thin, so they can supplement with local knowledge.

3. **Tribal data sovereignty:** T0 classification throughout. We use only publicly available federal data. No Tribal-specific data is scraped, stored, or inferred without public source attribution.

4. **Incremental improvement:** Each phase closes gaps. Coverage trends upward across every source with each quarterly data refresh.

5. **Authoritative sourcing:** Every data point traces to a named federal source (EPA, Congress.gov, USASpending, FEMA NRI, USFS). No data is fabricated or estimated without clear provenance.

---

*This roadmap tracks data completeness for all 592 federally recognized Tribal Nations served by the TCR Policy Scanner. Updated as each phase delivers new coverage improvements.*
