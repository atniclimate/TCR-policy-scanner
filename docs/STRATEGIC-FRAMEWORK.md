# TCR Policy Scanner — Strategic Framework

## Purpose

This framework bridges the **TCR Policy Scanner** technical architecture to the
**FY26 Tribal Climate Resilience Hot Sheets** congressional advocacy brief. It is
designed to inform a strategic plan that keeps the scanner's data model, scoring
logic, and knowledge graph synchronized with the advocacy positions expressed in
the Hot Sheets — and to identify where the Hot Sheets revise, extend, or supersede
the scanner's current assumptions.

---

## 1. Program Inventory Alignment

### 1.1 Current Scanner Coverage (16 programs)

| ID | Program | Agency | CI | Scanner Status |
|----|---------|--------|----|----------------|
| `bia_tcr` | BIA Tribal Climate Resilience | BIA | 88% | STABLE |
| `bia_tcr_awards` | Tribal Community Resilience Annual Awards | BIA | 85% | STABLE |
| `fema_bric` | FEMA BRIC | FEMA | 12% | FLAGGED |
| `irs_elective_pay` | IRS Elective Pay (§6417) | Treasury/IRS | 55% | AT_RISK |
| `epa_stag` | EPA STAG / DWIG-TSA | EPA | 90% | STABLE |
| `epa_gap` | EPA GAP | EPA | 80% | STABLE |
| `epa_tribal_air` | Tribal Air Quality Management | EPA | 82% | STABLE |
| `fema_tribal_mitigation` | FEMA Tribal Mitigation Plans | FEMA | 65% | AT_RISK |
| `dot_protect` | DOT PROTECT | DOT | 93% | SECURE |
| `usda_wildfire` | USDA Wildfire Defense Grants | USFS | 78% | STABLE_BUT_VULNERABLE |
| `doe_indian_energy` | DOE Indian Energy | DOE | 55% | UNCERTAIN |
| `hud_ihbg` | HUD IHBG | HUD | 85% | STABLE |
| `noaa_tribal` | NOAA Tribal Grants | NOAA | 50% | UNCERTAIN |
| `fhwa_ttp_safety` | FHWA TTP Safety | FHWA | 85% | STABLE |
| `usbr_watersmart` | USBR WaterSMART | Reclamation | 60% | UNCERTAIN |
| `usbr_tap` | USBR TAP | Reclamation | 75% | STABLE |

### 1.2 Hot Sheets Additions (Completed)

Both programs were added to the scanner inventory during Phase 2 implementation.

| ID | Program | Agency | CI | Status | Added |
|----|---------|--------|----|--------|-------|
| `bia_tcr_awards` | Tribal Community Resilience Annual Awards | BIA | 85% | STABLE | Phase 2 |
| `epa_tribal_air` | Tribal Air Quality Management | EPA | 82% | STABLE | Phase 2 |

### 1.3 Status Reclassifications (Hot Sheets vs. Scanner)

All reclassifications identified in the Hot Sheets have been applied during
Phase 2 implementation. The table below reflects the final reconciled state:

| Program | Scanner Status | Hot Sheets Status | Delta | Resolution |
|---------|---------------|-------------------|-------|------------|
| IRS Elective Pay | AT_RISK (CI: 55%) | **AT RISK** | Legislative repeal threat not captured by CI | DONE - CI set to 0.55; reconciliation trigger keywords added |
| DOT PROTECT | SECURE (CI: 93%) | **SECURE** | Statutory set-aside stronger than "STABLE" implies | DONE - CI set to 0.93; SECURE status category introduced |
| USBR WaterSMART | UNCERTAIN (CI: 60%) | **UNCERTAIN** | Missing from CI model | DONE - CI set to 0.60; UNCERTAIN status category added |
| DOE Indian Energy | UNCERTAIN (CI: 55%) | **UNCERTAIN** | Missing from CI model | DONE - CI set to 0.55; status = UNCERTAIN |
| NOAA Tribal Grants | UNCERTAIN (CI: 50%) | **UNCERTAIN** | Missing from CI model | DONE - CI set to 0.50; status = UNCERTAIN |
| FEMA BRIC | FLAGGED (CI: 12%) | **TERMINATED -> REPLACEMENT** | Hot Sheets confirms termination; adds "responsive mitigation" replacement framing | DONE - Kept FLAGGED; replacement program tracking added |
| HUD IHBG | STABLE (CI: 85%) | **STABLE** | Missing from CI model | DONE - CI set to 0.85; status = STABLE |
| EPA GAP | STABLE (CI: 80%) | **STABLE** | Missing from CI model | DONE - CI set to 0.80; status = STABLE |
| FHWA TTP Safety | STABLE (CI: 85%) | **STABLE** | Missing from CI model | DONE - CI set to 0.85; status = STABLE |
| EPA STAG | STABLE (CI: 90%) | **STABLE** | Aligned | No change needed |
| BIA TCR | STABLE (CI: 88%) | **STABLE** | Aligned | No change needed |
| USDA Wildfire | STABLE_BUT_VULNERABLE (CI: 78%) | **VULNERABLE** | Aligned (terminology difference) | No change needed |
| FEMA Tribal Mitigation | AT_RISK (CI: 65%) | **AT RISK** | Aligned | No change needed |

### 1.4 New Status Categories (Completed in v1)

The Hot Sheets introduced status categories that have been added to the scanner's
`ci_thresholds` and status enumeration in `data/policy_tracking.json`:

- **SECURE**: Statutory set-aside or permanent authorization; not subject to annual
  appropriations volatility. Programs: DOT PROTECT, EPA STAG (IIJA lines).
- **UNCERTAIN**: Active program but facing structural ambiguity (agency reorganization,
  unclear reauthorization path). Programs: WaterSMART, DOE Indian Energy, NOAA.
- **TERMINATED**: Program confirmed terminated; advocacy pivots to replacement
  mechanism. Programs: FEMA BRIC (tracked as FLAGGED with replacement framing).

---

## 2. Knowledge Graph Enrichment

### 2.1 New Statutory Authorities from Hot Sheets

The Hot Sheets provided detailed statutory citations. The following have been
added to `data/graph_schema.json` (completed in v1 Phase 2):

| Authority ID | Citation | Type | Durability | Programs | Status |
|-------------|----------|------|-----------|----------|--------|
| `auth_ira_48e` | IRA § 48(e) (Low-Income Community Solar) | Statute | Expires 2032 | `irs_elective_pay` | Added |
| `auth_ira_45_48` | IRA § 45/48 (Production/Investment Tax Credits) | Statute | Expires 2032 | `irs_elective_pay` | Added |
| `auth_caa_105` | Clean Air Act § 105 (Tribal Air Quality) | Statute | Permanent | `epa_tribal_air` | Added |
| `auth_indian_environmental_gap` | Indian Environmental General Assistance Program Act of 1992 | Statute | Permanent | `epa_gap` | Added |
| `auth_iija_watersmart` | IIJA § 40901 (WaterSMART) | Statute | Expires FY26 | `usbr_watersmart` | Added |
| `auth_snyder_act_tcr_awards` | Snyder Act (25 U.S.C. 13) — TCR Annual Awards | Statute | Permanent | `bia_tcr_awards` | Added |

The following authorities from the Hot Sheets remain as **v2 targets** (not yet
in graph_schema.json):

| Authority ID | Citation | Type | Durability | Programs | Status |
|-------------|----------|------|-----------|----------|--------|
| `auth_ira_45w` | IRA § 45W (Clean Vehicle Credits) | Statute | Expires 2032 | `irs_elective_pay` | v2 Target |
| `auth_sdwa` | Safe Drinking Water Act (42 U.S.C. 300j-12) | Statute | Permanent | `epa_stag` | v2 Target (covered by `auth_clean_water_act`) |
| `auth_cwma` | Community Wildfire Management Act (proposed) | Statute | Proposed | `usda_wildfire` | v2 Target |
| `auth_nahasda_reauth` | NAHASDA Reauthorization (pending) | Statute | Pending | `hud_ihbg` | v2 Target (base act covered by `auth_nahasda`) |
| `auth_noaa_cpo` | NOAA Climate Program Office Authority | Statute | Annual | `noaa_tribal` | v2 Target (covered by `auth_magnuson_stevens`) |

### 2.2 New Barriers from Hot Sheets (Completed in v1)

All six barriers have been added to `data/graph_schema.json`:

| Barrier ID | Description | Type | Severity | Programs | Mitigation |
|-----------|-------------|------|----------|----------|------------|
| `bar_reconciliation_repeal` | IRA provisions subject to reconciliation repeal | Statutory | High | `irs_elective_pay` | Congressional defense; bipartisan coalition |
| `bar_agency_capacity` | Tribal set-aside administrative capacity at agencies | Administrative | Med | `dot_protect`, `epa_stag` | TA funding; streamlined application |
| `bar_reauthorization_gap` | NAHASDA reauthorization uncertainty | Statutory | Med | `hud_ihbg` | Advocate for clean reauthorization |
| `bar_data_sovereignty` | Tribal data requirements in federal reporting | Administrative | Med | All programs | Advocate for TSDF-aligned reporting |
| `bar_iija_sunset` | IIJA supplemental funding expires end of FY26 | Statutory | High | `epa_stag`, `dot_protect`, `usbr_watersmart`, `usda_wildfire` | Advocate for baseline incorporation |
| `bar_match_burden` | Cost-share/match requirements across multiple programs | Administrative | High | `usda_wildfire`, `usbr_watersmart`, `fema_tribal_mitigation` | Match waivers; 638 contract flexibility |

### 2.3 Cross-Cutting Advocacy Framework: Five Structural Asks (Completed in v1)

The Hot Sheets introduce a "Five Structural Asks" framework that cuts across all
16 programs. These have been represented as top-level AdvocacyLeverNodes in the
knowledge graph (`data/graph_schema.json`), linked to programs via ADVANCES edges:

1. **Multi-Year Funding Stability** — Shift from annual discretionary to
   multi-year or permanent authorization for core Tribal climate programs
2. **Match/Cost-Share Waivers** — Categorical Tribal exemptions from cost-share
   requirements based on trust responsibility
3. **Direct Tribal Access** — Non-competitive, formula-based, or direct-service
   pathways that bypass state pass-through bottlenecks
4. **Tribal Consultation Compliance** — Enforceable consultation requirements
   (Executive Order 13175) with reporting accountability
5. **Data Sovereignty & Capacity** — Tribal control over climate/environmental
   data with federal TA funding for data infrastructure

These five asks map to specific barriers:

| Structural Ask | Mitigates Barriers |
|---------------|-------------------|
| Multi-Year Funding | `bar_appropriations_volatility`, `bar_iija_sunset` |
| Match Waivers | `bar_cost_share`, `bar_match_burden` |
| Direct Tribal Access | `bar_competitive_only`, `bar_agency_capacity` |
| Consultation Compliance | `bar_plan_requirement` (indirectly) |
| Data Sovereignty | `bar_data_sovereignty` |

---

## 3. Scanner Enhancement Priorities

### 3.1 Immediate — Completed in v1, Phase 2

1. **Add 2 new programs** to `program_inventory.json` -- DONE
   - BIA Tribal Community Resilience Annual Awards
   - EPA Tribal Air Quality Management

2. **Reconcile CI statuses** with Hot Sheets assessments -- DONE
   - IRS Elective Pay: STABLE -> AT_RISK (CI: 0.55)
   - DOT PROTECT: STABLE -> SECURE (CI: 0.93)
   - CI scores assigned for all 16 programs (no gaps)
   - SECURE, UNCERTAIN, TERMINATED status categories introduced

3. **Add reconciliation bill tracking** -- DONE
   - Reconciliation trigger keywords added to `scanner_config.json`
   - Keywords: "reconciliation", "repeal", "Section 6417", "elective pay repeal",
     "IRA repeal", "direct pay termination"

4. **Update graph schema** with Hot Sheets authorities, barriers, and Five
   Structural Asks as cross-cutting lever nodes -- DONE

### 3.2 Near-Term — Completed in v1, Phase 3

5. **IIJA sunset tracker** -- DONE (MON-01: `src/monitors/iija_sunset.py`)
   - Monitors IIJA-funded programs approaching FY26 expiration
   - Produces CRITICAL/WARNING/INFO alerts by days remaining
   - Scans Congress.gov for reauthorization signals (suppresses alert if found)
   - Creates THREATENS edges in knowledge graph

6. **Tribal consultation tracker** -- DONE (MON-03: `src/monitors/tribal_consultation.py`)
   - Detects DTLLs, EO 13175 references, and consultation notices via tiered regex
   - Informational (INFO severity) -- not a threat monitor

7. **Budget reconciliation monitor** -- DONE (MON-02: `src/monitors/reconciliation.py`)
   - Tracks Congress.gov items for reconciliation/repeal keywords
   - Filters out enacted laws (OBBBA / Public Law 119-21) to avoid false positives
   - Creates THREATENS edges for active bills

8. **Hot Sheets sync workflow** -- DONE (MON-04: `src/monitors/hot_sheets.py`)
   - HotSheetsValidator compares scanner CI with Hot Sheets positions each scan
   - Detects divergences, applies in-memory overrides for downstream consistency
   - Tracks staleness of Hot Sheets data (configurable threshold, default 90 days)
   - Persists known divergences to distinguish first-time from repeat alerts

> **Note:** Also implemented in Phase 3: DHS Funding Cliff Monitor (MON-05:
> `src/monitors/dhs_funding.py`) tracking CR expiration for FEMA programs.

### 3.3 Strategic (Multi-Cycle)

9. **Historical trend analysis** -- DONE (RPT-04, completed in v1 Phase 4)
   - CI scores persisted per scan cycle in `outputs/.ci_history.json`
   - Report generator renders trend table with per-program trajectory and
     trend indicators (capped at 90 entries, last 10 shown)
   - Stable programs grouped into compact summary line

10. **Cross-program correlation** *(v2 Target)*: Detect when multiple programs
    face simultaneous threats (e.g., IIJA sunset affects 4+ programs)

11. **Advocacy effectiveness tracking** *(v2 Target)*: Monitor whether advocacy
    levers (e.g., match waiver requests) correlate with subsequent policy changes

12. **Domain adaptability** *(v2 Target)*: Leverage config-driven architecture to
    extend scanner to non-climate Tribal policy domains (health, education,
    economic development)

---

## 4. Data Flow: Hot Sheets <-> Scanner Integration

```
Hot Sheets (Advocacy Brief)          TCR Policy Scanner
+------------------------+           +----------------------+
| 16 Program Briefs      |<----------|  Scored Items        |
| Status Assessments     |           |  CI Dashboard        |
| Statutory Authorities  |---------->|  Graph Schema        |
| Advocacy Language      |           |  Program Inventory   |
| Five Structural Asks   |---------->|  Lever Nodes         |
| Funding Data           |---------->|  Funding Vehicles    |
| Barrier Identification |---------->|  Barrier Nodes       |
+------------------------+           +----------------------+
         |                                     |
         v                                     v
+------------------------+           +----------------------+
| Congressional Meetings |           | Daily Briefings      |
| Committee Testimony    |           | Alert Notifications  |
| Agency Consultations   |           | Trend Analysis       |
+------------------------+           +----------------------+
```

**Bidirectional sync:**
- Scanner -> Hot Sheets: Daily scan results inform status updates, identify new
  developments, and validate advocacy positions
- Hot Sheets -> Scanner: Advocacy positions calibrate CI scores, add programs,
  and define trigger keywords for monitoring

---

## 5. Confidence Index Model Updates

### 5.1 Revised CI Threshold Table

These thresholds are implemented in `data/policy_tracking.json`:

| Status | CI Range | Floor Value | Description |
|--------|----------|-------------|-------------|
| SECURE | 0.90-1.00 | 0.90 | Statutory set-aside; permanent authorization; minimal annual risk |
| STABLE | 0.75-0.89 | 0.75 | Funded and active; subject to normal appropriations process |
| STABLE_BUT_VULNERABLE | 0.65-0.74 | 0.65 | Active but exposed to executive/legislative restructuring |
| AT_RISK | 0.40-0.64 | 0.40 | Facing specific threat; advocacy action required |
| UNCERTAIN | 0.25-0.39 | 0.25 | Structural ambiguity; agency reorganization or unclear reauth path |
| FLAGGED | 0.10-0.24 | 0.10 | Terminated, zeroed out, or requires specialist intervention |
| TERMINATED | 0.00-0.09 | 0.00 | Program confirmed terminated; advocacy pivots to replacement mechanism |

> **Note on CI scores vs. thresholds:** In v1, CI scores are manually assigned
> in `data/program_inventory.json` based on expert assessment of each program's
> risk posture. The thresholds above define status category boundaries. Some
> programs (e.g., DOE Indian Energy at CI 0.55 / UNCERTAIN, USBR WaterSMART at
> CI 0.60 / UNCERTAIN) have CI scores above their status category floor because
> the status was set to reflect Hot Sheets advocacy positioning rather than a
> strict threshold-based derivation.

### 5.2 CI Score Inputs *(v2 Target -- Computed CI Model)*

> **Status:** This section describes an aspirational v2 computed CI model. In v1,
> CI scores are manually assigned per program in `data/program_inventory.json`.
> The computed model below is a design target for a future version.

Each program's CI would be computed from:

1. **Statutory durability** (0.0-1.0): Permanent > Multi-year > Annual > Proposed
2. **Appropriations status** (0.0-1.0): Enacted > CR > Proposed > Threatened
3. **Agency implementation** (0.0-1.0): Active > Paused > Under review > Terminated
4. **Political exposure** (0.0-1.0): Bipartisan > Partisan > Targeted for repeal
5. **Tribal access pathway** (0.0-1.0): Direct/formula > Competitive > Pass-through

Weighted composite: `CI = 0.30*statutory + 0.25*appropriations + 0.20*agency + 0.15*political + 0.10*access`

---

## 6. Report Integration Points

### 6.1 Briefing Sections (Completed in v1)

The scanner's `LATEST-BRIEFING.md` includes the following sections
(implemented in `src/reports/generator.py`):

1. Executive Summary
2. **Reconciliation Watch** -- active when reconciliation monitor detects threats
3. **IIJA Sunset Countdown** -- table with days remaining per affected program
4. New Developments
5. Critical Program Updates
6. **Confidence Index Dashboard** -- with Hot Sheets sync indicator column
7. FLAGGED detail (specialist attention)
8. **Advocacy Goal Classifications** -- per-program decision engine output
9. **Five Structural Asks** -- mapped to barriers and programs from knowledge graph
10. Barriers & Mitigation Pathways
11. Statutory Authority Map
12. Active Advocacy Levers
13. **CI Score Trends** -- historical trajectory table (RPT-04)
14. All Relevant Items (by score)

### 6.2 JSON Output Schema

The `LATEST-RESULTS.json` output uses the following top-level structure
(implemented in `src/reports/generator.py` `_build_json()`):

```json
{
  "scan_date": "2026-02-09",
  "summary": {
    "new_count": 0,
    "updated_count": 0,
    "removed_count": 0,
    "total_current": 0,
    "total_previous": 0
  },
  "scan_results": [],
  "changes": {
    "new_items": [],
    "updated_items": [],
    "removed_items": []
  },
  "knowledge_graph": { "...graph_data..." },
  "monitor_data": {
    "alerts": [
      {
        "monitor": "iija_sunset",
        "severity": "WARNING",
        "program_ids": ["epa_stag"],
        "title": "...",
        "detail": "...",
        "metadata": {},
        "timestamp": "..."
      }
    ],
    "classifications": { "...per-program advocacy goal classifications..." },
    "summary": {
      "total_alerts": 0,
      "critical_count": 0,
      "warning_count": 0,
      "info_count": 0,
      "monitors_run": []
    }
  },
  "classifications": { "...per-program advocacy goal classifications..." }
}
```

> **v2 Target:** A dedicated `hot_sheets_sync` top-level key with aggregated
> alignment/divergence metrics and a `structural_asks` key with per-ask scan
> signal counts. In v1, Hot Sheets sync data is embedded within `monitor_data`
> alerts (monitor="hot_sheets") and structural asks are rendered in the
> knowledge graph and Markdown briefing.

---

## 7. Implementation Checklist

- [x] Add `bia_tcr_awards` and `epa_tribal_air` to program_inventory.json
- [x] Assign CI scores to all programs (no gaps)
- [x] Introduce SECURE, UNCERTAIN, TERMINATED status categories
- [x] Reclassify IRS Elective Pay -> AT_RISK (CI: 0.55)
- [x] Reclassify DOT PROTECT -> SECURE (CI: 0.93)
- [x] Add reconciliation/repeal trigger keywords
- [x] Add new authorities to graph_schema.json (6 added; 5 deferred to v2)
- [x] Add 6 new barriers to graph_schema.json
- [x] Add Five Structural Asks as AdvocacyLeverNodes
- [x] Add ADVANCES edge type to graph schema
- [x] Update scanner_config.json with new search queries
- [x] Update report generator with Hot Sheets sync section
- [x] Add IIJA sunset tracking logic (MON-01)
- [x] Update CI threshold model in policy_tracking.json
- [x] Create Hot Sheets sync validation (MON-04: HotSheetsValidator)

**v2 Checklist:**
- [ ] Add remaining 5 authorities from Hot Sheets (auth_ira_45w, auth_sdwa, auth_cwma, auth_nahasda_reauth, auth_noaa_cpo)
- [ ] Implement computed CI model (Section 5.2)
- [ ] Add dedicated `hot_sheets_sync` key to JSON output
- [ ] Cross-program correlation analysis
- [ ] Advocacy effectiveness tracking
- [ ] Domain adaptability for non-climate policy domains

---

*This framework document is maintained alongside the TCR Policy Scanner codebase
and should be updated each time the Hot Sheets brief is revised.*

*Last updated: 2026-02-09*
*Scanner branch: `main`*
