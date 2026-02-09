# ATNI TCR Policy Scanner — Strategic Framework

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
| FEMA BRIC | FLAGGED (CI: 12%) | **TERMINATED → REPLACEMENT** | Hot Sheets confirms termination; adds "responsive mitigation" replacement framing | DONE - Kept FLAGGED; replacement program tracking added |
| HUD IHBG | STABLE (CI: 85%) | **STABLE** | Missing from CI model | DONE - CI set to 0.85; status = STABLE |
| EPA GAP | STABLE (CI: 80%) | **STABLE** | Missing from CI model | DONE - CI set to 0.80; status = STABLE |
| FHWA TTP Safety | STABLE (CI: 85%) | **STABLE** | Missing from CI model | DONE - CI set to 0.85; status = STABLE |
| EPA STAG | STABLE (CI: 90%) | **STABLE** | Aligned | No change needed |
| BIA TCR | STABLE (CI: 88%) | **STABLE** | Aligned | No change needed |
| USDA Wildfire | STABLE_BUT_VULNERABLE (CI: 78%) | **VULNERABLE** | Aligned (terminology difference) | No change needed |
| FEMA Tribal Mitigation | AT_RISK (CI: 65%) | **AT RISK** | Aligned | No change needed |

### 1.4 New Status Categories

The Hot Sheets introduce status categories not yet in the scanner:

- **SECURE**: Statutory set-aside or permanent authorization; not subject to annual
  appropriations volatility. Programs: DOT PROTECT, EPA STAG (IIJA lines).
- **UNCERTAIN**: Active program but facing structural ambiguity (agency reorganization,
  unclear reauthorization path). Programs: WaterSMART, DOE Indian Energy, NOAA.
- **TERMINATED → REPLACEMENT**: Program confirmed terminated but replacement
  mechanism is being developed. Programs: FEMA BRIC.

These should be added to the `ci_thresholds` and status enumeration in
`data/policy_tracking.json`.

---

## 2. Knowledge Graph Enrichment

### 2.1 New Statutory Authorities from Hot Sheets

The Hot Sheets provide detailed statutory citations that should be added to
`data/graph_schema.json`:

| Authority ID | Citation | Type | Durability | Programs |
|-------------|----------|------|-----------|----------|
| `auth_ira_48e` | IRA § 48(e) (Low-Income Community Solar) | Statute | Expires 2032 | `irs_elective_pay` |
| `auth_ira_45` | IRA § 45/48 (Production/Investment Tax Credits) | Statute | Expires 2032 | `irs_elective_pay` |
| `auth_ira_45w` | IRA § 45W (Clean Vehicle Credits) | Statute | Expires 2032 | `irs_elective_pay` |
| `auth_sdwa` | Safe Drinking Water Act (42 U.S.C. 300j-12) | Statute | Permanent | `epa_stag` |
| `auth_caa_105` | Clean Air Act § 105 (Tribal Air Quality) | Statute | Permanent | `epa_tribal_air` |
| `auth_indian_environmental` | Indian Environmental General Assistance Program Act of 1992 | Statute | Permanent | `epa_gap` |
| `auth_cwma` | Community Wildfire Management Act (proposed) | Statute | Proposed | `usda_wildfire` |
| `auth_nahasda_reauth` | NAHASDA Reauthorization (pending) | Statute | Pending | `hud_ihbg` |
| `auth_noaa_cpo` | NOAA Climate Program Office Authority | Statute | Annual | `noaa_tribal` |
| `auth_reclamation_iija` | IIJA § 40901 (WaterSMART) | Statute | Expires FY26 | `usbr_watersmart` |

### 2.2 New Barriers from Hot Sheets

| Barrier ID | Description | Type | Severity | Programs | Mitigation |
|-----------|-------------|------|----------|----------|------------|
| `bar_reconciliation_repeal` | IRA provisions subject to reconciliation repeal | Statutory | High | `irs_elective_pay` | Congressional defense; bipartisan coalition |
| `bar_agency_capacity` | Tribal set-aside administrative capacity at agencies | Administrative | Med | `dot_protect`, `epa_stag` | TA funding; streamlined application |
| `bar_reauthorization_gap` | NAHASDA reauthorization uncertainty | Statutory | Med | `hud_ihbg` | Advocate for clean reauthorization |
| `bar_data_sovereignty` | Tribal data requirements in federal reporting | Administrative | Med | All programs | Advocate for TSDF-aligned reporting |
| `bar_iija_sunset` | IIJA supplemental funding expires end of FY26 | Statutory | High | `epa_stag`, `dot_protect`, `usbr_watersmart`, `usda_wildfire` | Advocate for baseline incorporation |
| `bar_match_burden` | Cost-share/match requirements across multiple programs | Administrative | High | `usda_wildfire`, `usbr_watersmart`, `fema_tribal_mitigation` | Match waivers; 638 contract flexibility |

### 2.3 Cross-Cutting Advocacy Framework: Five Structural Asks

The Hot Sheets introduce a "Five Structural Asks" framework that cuts across all
16 programs. These should be represented as top-level AdvocacyLeverNodes in the
knowledge graph, linked to all programs via a new `ADVANCES` edge type:

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

### 3.1 Immediate (Before Next Congressional Session)

1. **Add 2 new programs** to `program_inventory.json`:
   - BIA Tribal Community Resilience Annual Awards
   - EPA Tribal Air Quality Management

2. **Reconcile CI statuses** with Hot Sheets assessments:
   - IRS Elective Pay: STABLE → AT_RISK (CI: 0.55)
   - DOT PROTECT: STABLE → SECURE (CI: 0.93)
   - Add CI scores for all 14+ programs (no gaps)
   - Introduce SECURE, UNCERTAIN, TERMINATED status categories

3. **Add reconciliation bill tracking**: New scanner_trigger_keywords for budget
   reconciliation language that threatens IRA provisions: "reconciliation",
   "repeal", "Section 6417", "elective pay repeal", "IRA repeal"

4. **Update graph schema** with Hot Sheets authorities, barriers, and Five
   Structural Asks as cross-cutting lever nodes

### 3.2 Near-Term (FY26 Cycle)

5. **IIJA sunset tracker**: Monitor IIJA-funded programs approaching FY26
   expiration; flag when no reauthorization bill is introduced

6. **Tribal consultation tracker**: Detect Dear Tribal Leader Letters (DTLLs),
   consultation notices, and Executive Order 13175 compliance signals

7. **Budget reconciliation monitor**: Track House/Senate reconciliation bills
   for provisions that could repeal IRA §6417 or restructure FEMA programs

8. **Hot Sheets sync workflow**: Automated comparison between scanner CI
   assessments and Hot Sheets positions after each scan cycle

### 3.3 Strategic (Multi-Cycle)

9. **Historical trend analysis**: Track CI scores over time to visualize
   program stability trajectories

10. **Cross-program correlation**: Detect when multiple programs face
    simultaneous threats (e.g., IIJA sunset affects 4+ programs)

11. **Advocacy effectiveness tracking**: Monitor whether advocacy levers
    (e.g., match waiver requests) correlate with subsequent policy changes

12. **Domain adaptability**: Leverage config-driven architecture to extend
    scanner to non-climate Tribal policy domains (health, education,
    economic development)

---

## 4. Data Flow: Hot Sheets ↔ Scanner Integration

```
Hot Sheets (Advocacy Brief)          TCR Policy Scanner
┌────────────────────────┐           ┌──────────────────────┐
│ 16 Program Briefs      │◄──────────│ Scored Items         │
│ Status Assessments     │           │ CI Dashboard         │
│ Statutory Authorities  │──────────►│ Graph Schema         │
│ Advocacy Language      │           │ Program Inventory    │
│ Five Structural Asks   │──────────►│ Lever Nodes          │
│ Funding Data           │──────────►│ Funding Vehicles     │
│ Barrier Identification │──────────►│ Barrier Nodes        │
└────────────────────────┘           └──────────────────────┘
         │                                     │
         ▼                                     ▼
┌────────────────────────┐           ┌──────────────────────┐
│ Congressional Meetings │           │ Daily Briefings      │
│ Committee Testimony    │           │ Alert Notifications  │
│ Agency Consultations   │           │ Trend Analysis       │
└────────────────────────┘           └──────────────────────┘
```

**Bidirectional sync:**
- Scanner → Hot Sheets: Daily scan results inform status updates, identify new
  developments, and validate advocacy positions
- Hot Sheets → Scanner: Advocacy positions calibrate CI scores, add programs,
  and define trigger keywords for monitoring

---

## 5. Confidence Index Model Updates

### 5.1 Revised CI Threshold Table

| Status | CI Range | Description |
|--------|----------|-------------|
| SECURE | 0.90–1.00 | Statutory set-aside; permanent authorization; minimal annual risk |
| STABLE | 0.75–0.89 | Funded and active; subject to normal appropriations process |
| STABLE_BUT_VULNERABLE | 0.65–0.74 | Active but exposed to executive/legislative restructuring |
| AT_RISK | 0.40–0.64 | Facing specific threat; advocacy action required |
| UNCERTAIN | 0.25–0.39 | Structural ambiguity; agency reorganization or unclear reauth path |
| FLAGGED | 0.00–0.24 | Terminated, zeroed out, or requires specialist intervention |

### 5.2 CI Score Inputs

Each program's CI should be computed from:

1. **Statutory durability** (0.0–1.0): Permanent > Multi-year > Annual > Proposed
2. **Appropriations status** (0.0–1.0): Enacted > CR > Proposed > Threatened
3. **Agency implementation** (0.0–1.0): Active > Paused > Under review > Terminated
4. **Political exposure** (0.0–1.0): Bipartisan > Partisan > Targeted for repeal
5. **Tribal access pathway** (0.0–1.0): Direct/formula > Competitive > Pass-through

Weighted composite: `CI = 0.30*statutory + 0.25*appropriations + 0.20*agency + 0.15*political + 0.10*access`

---

## 6. Report Integration Points

### 6.1 Briefing Enhancements

The scanner's `LATEST-BRIEFING.md` should be enhanced to include:

- **Five Structural Asks** section mapping to barrier mitigation pathways
- **Hot Sheets Sync Status** indicator showing alignment/divergence between
  scanner CI and Hot Sheets status for each program
- **IIJA Sunset Countdown** for affected programs
- **Reconciliation Watch** section when relevant bills are detected

### 6.2 JSON Output Schema Extensions

Add to `LATEST-RESULTS.json`:

```json
{
  "hot_sheets_sync": {
    "last_sync_date": "2026-02-09",
    "programs_aligned": 10,
    "programs_divergent": 3,
    "programs_missing_from_scanner": 2,
    "divergences": [
      {
        "program_id": "irs_elective_pay",
        "scanner_status": "STABLE",
        "hot_sheets_status": "AT_RISK",
        "resolution": "pending"
      }
    ]
  },
  "structural_asks": [
    {
      "id": "ask_multi_year",
      "name": "Multi-Year Funding Stability",
      "affected_programs": ["bia_tcr", "epa_gap", "doe_indian_energy"],
      "barriers_mitigated": ["bar_appropriations_volatility", "bar_iija_sunset"],
      "scan_signals": 0
    }
  ]
}
```

---

## 7. Implementation Checklist

- [x] Add `bia_tcr_awards` and `epa_tribal_air` to program_inventory.json
- [x] Assign CI scores to all programs (no gaps)
- [x] Introduce SECURE, UNCERTAIN, TERMINATED status categories
- [x] Reclassify IRS Elective Pay → AT_RISK (CI: 0.55)
- [x] Reclassify DOT PROTECT → SECURE (CI: 0.93)
- [x] Add reconciliation/repeal trigger keywords
- [x] Add 10 new authorities to graph_schema.json
- [x] Add 6 new barriers to graph_schema.json
- [x] Add Five Structural Asks as AdvocacyLeverNodes
- [x] Add ADVANCES edge type to graph schema
- [x] Update scanner_config.json with new search queries
- [x] Update report generator with Hot Sheets sync section
- [x] Add IIJA sunset tracking logic
- [x] Update CI threshold model in policy_tracking.json
- [ ] Create Hot Sheets sync validation script

---

*This framework document is maintained alongside the TCR Policy Scanner codebase
and should be updated each time the Hot Sheets brief is revised.*

*Last updated: 2026-02-09*
*Scanner branch: `main`*
