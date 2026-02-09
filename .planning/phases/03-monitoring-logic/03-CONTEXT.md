# Phase 3: Monitoring Capabilities and Decision Logic - Context

**Gathered:** 2026-02-09
**Status:** Ready for planning

<domain>
## Phase Boundary

The scanner detects legislative threats (IIJA sunsets, reconciliation bills, funding cliffs), Tribal consultation signals, and classifies each program into an advocacy goal using 5 decision rules. This phase adds monitoring capabilities and decision logic to the existing pipeline. Report enhancements that surface these outputs are Phase 4.

</domain>

<decisions>
## Implementation Decisions

### Hot Sheets divergence handling
- Hot Sheets positions are ground truth -- scanner auto-adjusts CI status to match Hot Sheets when they diverge
- First time a new divergence is detected, alert prominently in output so the team notices the override
- Subsequent runs log the override silently (original CI status, Hot Sheets status, that Hot Sheets took precedence)
- Hot Sheets status embedded directly in program_inventory.json as a `hot_sheets_status` field alongside CI score (not a separate file)
- Each `hot_sheets_status` entry carries a `last_updated` timestamp; scanner warns when positions are older than a configurable threshold (stale data warning)

### Claude's Discretion
- Alert sensitivity and time windows for IIJA sunset warnings (how many days before expiration to start flagging)
- Pattern matching breadth for Tribal consultation signals (DTLLs, EO 13175 references, consultation notices)
- DHS funding cliff detection thresholds
- Advocacy goal priority ordering when a program matches multiple decision rules
- Staleness threshold default (e.g., 90 days, 180 days) for Hot Sheets positions
- Internal data structures for monitor state tracking

</decisions>

<specifics>
## Specific Ideas

No specific requirements beyond what the Strategic Framework and requirements define -- open to standard approaches for the monitoring and decision logic implementation.

</specifics>

<deferred>
## Deferred Ideas

None -- discussion stayed within phase scope.

</deferred>

---

*Phase: 03-monitoring-logic*
*Context gathered: 2026-02-09*
