---
phase: 03-monitoring-logic
plan: 01
subsystem: monitors
tags: [monitors, iija-sunset, reconciliation, dhs-funding, threatens-edges, monitor-framework]
requires:
  - phase-02 (enriched graph with authorities, barriers, structural asks)
provides:
  - MonitorAlert dataclass for standardized alert output
  - BaseMonitor ABC for consistent monitor interface
  - MonitorRunner orchestrator with THREATENS edge creation
  - IIJASunsetMonitor (MON-01) for FY26 expiration tracking
  - ReconciliationMonitor (MON-02) for Section 6417 threat detection
  - DHSFundingCliffMonitor (MON-05) for DHS CR expiration tracking
  - THREATENS edge type documented in schema
  - Monitor configuration section in scanner_config.json
affects:
  - 03-02 (decision engine consumes THREATENS edges for LOGIC-05)
  - 03-03 (signal monitors extend the framework, pipeline integration)
  - phase-04 (reports surface monitor alerts and sunset countdowns)
tech-stack:
  added: []
  patterns: [BaseMonitor-ABC, MonitorAlert-dataclass, MonitorRunner-orchestrator, THREATENS-edge-protocol]
key-files:
  created:
    - src/monitors/__init__.py
    - src/monitors/iija_sunset.py
    - src/monitors/reconciliation.py
    - src/monitors/dhs_funding.py
  modified:
    - config/scanner_config.json
    - src/graph/schema.py
key-decisions:
  - THREATENS edges regenerated each scan (ephemeral, not persisted in graph_schema.json)
  - Fund-exhaustion programs get separate INFO alerts (no calendar deadline)
  - Reconciliation monitor uses urgency_threshold_days for days_remaining (unpredictable timeline)
  - OBBBA filtered by enacted_laws_exclude config list (extensible)
duration: ~15 minutes
completed: 2026-02-09
---

# Phase 3 Plan 1: Monitor Framework and Threat Monitors Summary

Monitor framework with BaseMonitor ABC, MonitorAlert dataclass, and MonitorRunner orchestrator plus three threat monitors (IIJA sunset, reconciliation, DHS funding cliff) producing THREATENS edges for decision engine consumption.

## Performance

All monitors execute synchronously on in-memory data structures. No external API calls. Sub-second execution for the full monitor suite on the current graph (79 nodes, 118 edges).

## Accomplishments

1. **Monitor Framework** -- Created `src/monitors/` package with `MonitorAlert` dataclass (severity/program_ids/metadata), `BaseMonitor` ABC with `check()` interface, and `MonitorRunner` orchestrator that collects alerts and converts THREATENS metadata into graph edges.

2. **IIJA Sunset Monitor (MON-01)** -- Tracks 3 FY26-expiration programs (epa_stag, dot_protect, usbr_watersmart) with configurable warning/critical day thresholds. Scans Congress.gov items for reauthorization signals to suppress false positives. Separately handles fund-exhaustion programs (usda_wildfire) with appropriate INFO-level alerts.

3. **Reconciliation Monitor (MON-02)** -- Detects active bills threatening IRA Section 6417 from Congress.gov items. Filters out the already-enacted OBBBA (Public Law 119-21) via configurable exclusion list AND latest_action status checking. Uses urgency_threshold_days (30) for days_remaining since reconciliation timelines are unpredictable.

4. **DHS Funding Cliff Monitor (MON-05)** -- Uses configurable CR expiration date (2026-02-13). Produces CRITICAL alerts when expired, WARNING when approaching. Also scans for new DHS appropriations/CR bills to note legislative activity.

5. **THREATENS Edge Protocol** -- Monitors embed `creates_threatens_edge: true` in alert metadata. MonitorRunner scans all alerts and adds THREATENS edges to `graph_data["edges"]` with threat_node_id as source and program_id as target. Decision engine (Plan 03-02) will query these for LOGIC-05 classification.

6. **Configuration** -- Added `monitors` section to scanner_config.json with 6 sub-keys (iija_sunset, reconciliation, tribal_consultation, hot_sheets, dhs_funding, decision_engine). All thresholds are configurable.

## Task Commits

| # | Task | Commit | Key Changes |
|---|------|--------|-------------|
| 1 | Create monitor infrastructure and config | d47c4b1 | MonitorAlert/BaseMonitor/MonitorRunner, config monitors section, THREATENS in Edge docstring |
| 2 | Implement three threat monitors | 33fe098 | IIJASunsetMonitor, ReconciliationMonitor, DHSFundingCliffMonitor |

## Files Created

| File | Purpose |
|------|---------|
| `src/monitors/__init__.py` | MonitorAlert, BaseMonitor, MonitorRunner |
| `src/monitors/iija_sunset.py` | IIJA FY26 sunset tracker (MON-01) |
| `src/monitors/reconciliation.py` | Reconciliation bill detector (MON-02) |
| `src/monitors/dhs_funding.py` | DHS funding cliff tracker (MON-05) |

## Files Modified

| File | Change |
|------|--------|
| `config/scanner_config.json` | Added `monitors` top-level section with 6 sub-keys |
| `src/graph/schema.py` | Added THREATENS to Edge docstring |

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| THREATENS edges are ephemeral (regenerated each scan) | Days_remaining changes daily; persisting would create stale data |
| Fund-exhaustion programs get INFO alerts, no THREATENS edge | No calendar deadline means no days_remaining for urgency calculation |
| Reconciliation monitor uses urgency_threshold_days (30) for days_remaining | Reconciliation timelines are unpredictable; setting to threshold ensures LOGIC-05 triggers |
| Enacted laws filtered by config list + latest_action status | Double filtering prevents both OBBBA false positives and any future enacted bills |
| MonitorRunner uses lazy imports with try/except | Allows individual monitor development without blocking the runner |

## Deviations from Plan

None -- plan executed exactly as written.

## Issues Encountered

None.

## Next Phase Readiness

**Plan 03-02 (Decision Engine) is unblocked.** The THREATENS edges are now available in graph_data for the decision engine's LOGIC-05 (Urgent Stabilization) rule. The MonitorRunner.run_all() method returns sorted alerts and mutates graph_data with THREATENS edges, exactly the interface the decision engine needs.

**Plan 03-03 (Signal Monitors + Pipeline Integration) is unblocked.** The BaseMonitor ABC and MonitorRunner lazy-import pattern are ready for TribalConsultationMonitor (MON-03) and HotSheetsValidator (MON-04) to be added.

**Current monitor output (empty scan, Feb 9 2026):**
- 3 IIJA sunset INFO alerts (233 days to FY26 end)
- 1 IIJA fund-exhaustion INFO alert
- 2 DHS funding WARNING alerts (4 days to CR expiration)
- 5 THREATENS edges in graph_data
