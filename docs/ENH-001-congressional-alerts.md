# ENH-001: Congressional Alert System Architecture

**Status:** Proposed
**Requirement:** INTEL-12
**Story Points:** 21 (3 sprints)
**Priority:** P2 (after Phase 15 core delivery)
**Author:** Phase 15 Planning
**Date:** 2026-02-12

---

## 1. Overview

The Congressional Alert System detects changes in bill status, committee referrals, and voting activity relevant to Tribal climate resilience programs. It compares successive daily scans of `data/congressional_intel.json` to produce per-Tribe alerts that surface congressional developments requiring attention.

**Design principle:** Tribal Leaders should not have to monitor Congress themselves. The system watches on their behalf and surfaces only what matters to their specific programs, delegation, and geography.

**Trigger:** Each daily pipeline run (GitHub Actions `daily-scan.yml`, weekday 6 AM Pacific) produces a new `congressional_intel.json`. The alert system diffs the current scan against the previous scan and classifies detected changes.

**Data classification:** T0 (Open). No PII is collected, stored, or transmitted. Alerts contain only publicly available congressional data routed by Tribal program relevance.

---

## 2. Change Detection Engine

### 2.1 Diff Strategy

The engine compares two snapshots of `congressional_intel.json` keyed by `bill_id` (e.g., `hr-1234-119`):

```python
@dataclass
class BillDelta:
    bill_id: str
    change_type: ChangeType  # Enum
    old_value: str | None
    new_value: str | None
    timestamp: str  # ISO 8601 UTC
    affected_programs: list[str]  # program IDs from relevance scoring
```

### 2.2 Detectable Change Types

| Change Type | Detection Method | Example |
|-------------|-----------------|---------|
| `NEW_BILL` | bill_id present in current but absent from previous | HR 5678 introduced |
| `STATUS_CHANGE` | `latest_action.action_code` differs | Committee action -> Floor vote |
| `NEW_COSPONSOR` | `cosponsors` list length increased | Senator added as cosponsor |
| `COMMITTEE_REFERRAL` | `committees` list changed | Referred to SLIA |
| `HEARING_SCHEDULED` | `latest_action` contains hearing keywords | Committee hearing set for 3/15 |
| `BILL_AMENDED` | `text_versions` count increased or amendment detected | Amendment adopted |
| `BILL_ENROLLED` | `status` changed to "Enrolled" or "Presented to President" | Passed both chambers |
| `BILL_REMOVED` | bill_id present in previous but absent from current | Bill expired or withdrawn |

### 2.3 Snapshot Management

- Current scan: `data/congressional_intel.json`
- Previous scan: `data/congressional_intel.previous.json` (rotated on each successful scan)
- Rotation is atomic: rename current to previous only after new scan validates via Pydantic models
- First run (no previous file): all bills treated as `NEW_BILL`, classified as LOW priority

---

## 3. Alert Classification

Alerts are classified into four severity levels based on the urgency of action required by Tribal Leaders.

### 3.1 Severity Levels

| Level | Criteria | Action Implication |
|-------|----------|-------------------|
| **CRITICAL** | Bill passed chamber (House or Senate) or enrolled/presented to President | Immediate outreach to delegation; testimony or written comment may be needed within days |
| **HIGH** | Committee markup scheduled, floor vote scheduled, or bill amended with substantive changes | Prepare advocacy materials; coordinate with InterTribal partners |
| **MEDIUM** | New cosponsor from Tribe's delegation, new committee referral to relevant committee | Update delegation tracking; note ally identification |
| **LOW** | New related bill introduced, new text version published | Informational; include in next regular briefing cycle |

### 3.2 Classification Logic

```python
def classify_alert(delta: BillDelta) -> AlertLevel:
    """Classify a bill delta into an alert severity level."""
    if delta.change_type == ChangeType.BILL_ENROLLED:
        return AlertLevel.CRITICAL
    if delta.change_type == ChangeType.STATUS_CHANGE:
        if _is_chamber_passage(delta.new_value):
            return AlertLevel.CRITICAL
        if _is_markup_or_vote(delta.new_value):
            return AlertLevel.HIGH
    if delta.change_type == ChangeType.BILL_AMENDED:
        return AlertLevel.HIGH
    if delta.change_type == ChangeType.NEW_COSPONSOR:
        return AlertLevel.MEDIUM
    if delta.change_type == ChangeType.COMMITTEE_REFERRAL:
        return AlertLevel.MEDIUM
    if delta.change_type == ChangeType.HEARING_SCHEDULED:
        return AlertLevel.HIGH
    return AlertLevel.LOW
```

### 3.3 Escalation Rules

- If a bill has CRITICAL alert AND is sponsored by the Tribe's own delegation member, escalate to **CRITICAL+** (top of digest)
- Multiple MEDIUM alerts for the same bill within 7 days escalate to HIGH (pattern suggests active movement)

---

## 4. Per-Tribe Routing

Not every alert reaches every Tribe. The routing engine determines which Tribal Nations should receive each alert based on three criteria.

### 4.1 Routing Rules

| Rule | Match Condition | Data Source |
|------|----------------|-------------|
| **Delegation Match** | Bill's sponsor or cosponsors include a member of the Tribe's congressional delegation | `congressional_cache.json` delegations + bill sponsor data |
| **Program Match** | Bill affects one or more programs tracked by the Tribe (via AFFECTS_PROGRAM edges in knowledge graph) | `graph_schema.json` program nodes + bill relevance scoring |
| **Geographic Match** | Bill affects the Tribe's state(s) (state-specific legislation, appropriations earmarks) | `tribal_registry.json` state field + bill state references |

### 4.2 Routing Priority

When a bill matches multiple rules for the same Tribe, the highest-priority match determines alert placement in the digest:

1. **Delegation + Program**: Lead item -- "Your representative sponsored a bill affecting your programs"
2. **Program only**: Second tier -- "A bill affecting your programs is moving"
3. **Delegation only**: Third tier -- "Your representative is active on a related bill"
4. **Geographic only**: Fourth tier -- "State-level development to monitor"

### 4.3 De-duplication

A Tribe receives each alert exactly once, even if multiple routing rules match. The routing metadata records all matching rules for context in the digest rendering.

---

## 5. Delivery Mechanism

### 5.1 Primary: DOCX Digest Section (Phase 15+)

Alert digests are appended to the next DOCX packet generation as a new section:

- **Doc A (Internal Strategy):** Full alert digest with recommended actions, talking points, and timing guidance
- **Doc B (Congressional Overview):** Curated subset -- facts only, no strategy (consistent with existing Doc B audience rules)
- **Doc C/D (Regional):** Aggregated alerts across region, highlighting shared legislative interests

Section placement: After the bill intelligence section, before the delegation section. Alert severity badges use the existing confidence_level() visual treatment (HIGH/MEDIUM/LOW colored badges).

### 5.2 Secondary: JSON Alert Feed (Future)

```json
{
  "alerts": [
    {
      "alert_id": "alert_2026_0212_001",
      "bill_id": "hr-5678-119",
      "severity": "CRITICAL",
      "change_type": "STATUS_CHANGE",
      "summary": "HR 5678 passed House, referred to Senate SLIA",
      "affected_tribes": ["epa_100000171", "epa_100000234"],
      "affected_programs": ["bia_tcr", "fema_bric"],
      "timestamp": "2026-02-12T06:00:00Z"
    }
  ],
  "generated_at": "2026-02-12T06:15:00Z",
  "scan_diff": {
    "previous_scan": "2026-02-11T06:00:00Z",
    "current_scan": "2026-02-12T06:00:00Z",
    "bills_added": 2,
    "bills_changed": 5,
    "bills_removed": 0
  }
}
```

This feed can be consumed by the GitHub Pages web widget or SquareSpace iframe for near-real-time alert display.

### 5.3 Excluded: Email/Push Notifications

Per T0 data classification, the system collects no PII (no email addresses, no phone numbers, no user accounts). Alert delivery is pull-based only: Tribal Leaders access alerts through generated documents and the web widget.

---

## 6. Story Points and Sprint Plan

**Total: 21 story points across 3 sprints**

### Sprint 1: Change Detection Engine + Alert Classification (8 points)

| Story | Points | Description |
|-------|--------|-------------|
| S1.1 | 3 | Implement `BillDelta` dataclass and snapshot diff engine |
| S1.2 | 2 | Implement `classify_alert()` with severity levels and escalation rules |
| S1.3 | 2 | Snapshot rotation with atomic file operations |
| S1.4 | 1 | Unit tests for diff engine and classification (target: 20 tests) |

### Sprint 2: Per-Tribe Routing + Digest Generation (8 points)

| Story | Points | Description |
|-------|--------|-------------|
| S2.1 | 3 | Implement routing engine with delegation/program/geographic matching |
| S2.2 | 2 | Build alert digest data structure (per-Tribe filtered, de-duplicated) |
| S2.3 | 2 | Render alert digest section for Doc A (full) and Doc B (curated) |
| S2.4 | 1 | Unit tests for routing and de-duplication (target: 15 tests) |

### Sprint 3: Integration + Testing (5 points)

| Story | Points | Description |
|-------|--------|-------------|
| S3.1 | 2 | Integrate alert digest into PacketOrchestrator.prepare_context() |
| S3.2 | 1 | JSON alert feed generation for web widget |
| S3.3 | 2 | End-to-end integration tests with mock scan data (target: 10 tests) |

### Milestone: 45 new tests, 3 new source files, 1 new data artifact

---

## 7. Dependencies

| Dependency | Source | Status |
|------------|--------|--------|
| `congressional_intel.json` | Phase 15 Plan 01 (CongressGovScraper + BillIntelligence) | In progress |
| BillIntelligence Pydantic model | Phase 15 Plan 01 | In progress |
| Confidence scoring module | Phase 15 Plan 02 | In progress |
| `congressional_cache.json` | Existing (scripts/build_congress_cache.py) | Complete |
| `graph_schema.json` | Existing (src/graph/) | Complete |
| `tribal_registry.json` | Existing (EPA API) | Complete |
| PacketOrchestrator | Existing (src/packets/orchestrator.py) | Complete |
| DocxEngine section rendering | Existing (src/packets/docx_sections.py) | Complete |

---

## 8. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Congress.gov API rate limits prevent frequent scanning | Medium | Medium | Circuit breaker with cache fallback (already implemented) |
| Alert volume overwhelms Tribal Leaders (too many LOW alerts) | Low | High | Default to MEDIUM+ in digest; LOW available in JSON feed only |
| False positives from keyword-based bill relevance | Medium | Medium | Confidence scoring filters out low-relevance matches |
| Snapshot corruption loses diff baseline | Low | High | Atomic rotation with validation; keep 7-day snapshot history |

---

*This specification is part of the TCR Policy Scanner enhancement roadmap. Implementation depends on Phase 15 core delivery completing successfully.*
