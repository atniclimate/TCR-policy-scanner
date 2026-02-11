# Enhancement Proposal: Real-Time Congressional Alert Notifications

**Author:** Horizon Walker, TCR Policy Scanner Research Team
**Date:** 2026-02-11
**Status:** Proposed
**Effort:** 21 story points across 3 sprints

---

## Problem

Tribal Leaders learn about congressional actions that affect their climate resilience
funding too late. By the time a bill mentioning their programs is introduced, amended,
or voted on, the advocacy window has narrowed or closed entirely. Committee hearings
on appropriations that determine the next fiscal year's funding for programs like
BIA TCR ($34.291M) or EPA STAG get scheduled, happen, and produce outcomes that
reshape Tribal funding landscapes -- and the people most affected find out days later
through secondhand reports.

Today, our scanner runs on a daily batch cycle (weekday 6 AM Pacific via
`daily-scan.yml`). The Congress.gov scraper (`src/scrapers/congress_gov.py`) queries
11 legislative search terms against the 119th Congress with a 14-day scan window.
This architecture was built for comprehensive scanning, not speed. A bill introduced
at 2 PM on a Tuesday will not appear in the briefing until 6 AM Wednesday at the
earliest -- and only if the batch job runs successfully.

For 592 Tribal Nations tracking 16 federal programs across 20 statutory authorities,
hours matter. When a House subcommittee schedules a markup on Interior appropriations,
every hour of advance notice is an hour a Tribal Leader can use to coordinate testimony,
contact their congressional delegation, or align with partner Tribes.

## Vision

Push notifications within hours, not days. When a bill mentioning "Tribal Climate
Resilience" is introduced, the system detects it and routes an alert to every Tribal
Leader whose programs are affected. When an appropriations markup is scheduled for a
subcommittee with jurisdiction over FEMA BRIC replacement or IRS Elective Pay, the
affected Tribes receive a structured notification with:

- What happened (bill introduced, hearing scheduled, amendment filed, vote taken)
- Which programs are affected (matched against our 16-program inventory)
- What action to consider (from our existing advocacy levers and structural asks)
- Who to contact (from our per-Tribe congressional delegation mapping)

A Tribal climate coordinator in Alaska gets a notification at 3 PM that the Senate
Indian Affairs Committee just scheduled a hearing on IIJA reauthorization. Her
packet already has her senators, their committee assignments, and her Tribe's
IIJA-funded programs. She picks up the phone.

That is what this system enables.

## Technical Approach

### Architecture

```
┌─────────────────────────┐
│  Congress.gov API Poller │  (existing CongressGovScraper, enhanced)
│  - /bill endpoint       │
│  - /committee endpoint  │
│  - /amendment endpoint  │
│  - /nomination endpoint │
└───────────┬─────────────┘
            │ Raw items (every 2 hours)
            v
┌─────────────────────────┐
│   Change Detection      │  (existing ChangeDetector, enhanced)
│   - Dedup against       │
│     last-seen registry  │
│   - Classify event type │
│   - Extract urgency     │
└───────────┬─────────────┘
            │ New/changed items only
            v
┌─────────────────────────┐
│  Program Relevance      │  (existing RelevanceScorer + ProgramRelevanceFilter)
│  Matching               │
│  - Map item to 1-N of   │
│    16 tracked programs  │
│  - Score relevance      │
│  - Extract action type  │
└───────────┬─────────────┘
            │ Matched items + affected programs
            v
┌─────────────────────────┐
│  Tribe Routing Engine   │  (NEW)
│  - For each affected    │
│    program, find Tribes │
│    with that program in │
│    their relevant set   │
│  - Attach congressional │
│    delegation context   │
│  - Deduplicate across   │
│    programs             │
└───────────┬─────────────┘
            │ Per-Tribe alert payloads
            v
┌─────────────────────────┐
│  Dispatch Layer         │  (NEW)
│  - Webhook (POST JSON)  │
│  - Email (SMTP/SES)     │
│  - Digest mode (batch   │
│    low-urgency alerts)  │
└─────────────────────────┘
```

### Congress.gov API Expansion

The existing `CongressGovScraper` hits the `/bill` endpoint with 11 queries. For
real-time alerts, we expand coverage:

| Endpoint | Purpose | Polling Interval |
|----------|---------|-----------------|
| `/bill/{congress}` | New bill introductions and status changes | 2 hours |
| `/bill/{congress}/{type}/{number}/actions` | Specific action events (votes, referrals) | 2 hours |
| `/committee` | Committee hearing schedules | 4 hours |
| `/amendment/{congress}` | Floor and committee amendments | 2 hours |
| `/summaries/{congress}` | CRS summaries (rich context) | 6 hours |

The Congress.gov API rate limit is 5,000 requests/hour per key. At 2-hour intervals
with ~50 queries per cycle, we use approximately 600 requests/day -- well under the
limit.

### Event Classification

Each detected change is classified into one of 6 event types:

```python
class CongressionalEventType(Enum):
    BILL_INTRODUCED = "bill_introduced"          # Urgency: MEDIUM
    BILL_ACTION = "bill_action"                  # Urgency: varies
    COMMITTEE_HEARING = "committee_hearing"      # Urgency: HIGH
    APPROPRIATIONS_MARKUP = "appropriations_markup"  # Urgency: CRITICAL
    AMENDMENT_FILED = "amendment_filed"           # Urgency: HIGH
    VOTE_SCHEDULED = "vote_scheduled"            # Urgency: CRITICAL
```

Urgency determines dispatch behavior:
- **CRITICAL**: Immediate push to all affected Tribes
- **HIGH**: Push within 1 hour
- **MEDIUM**: Include in next digest (every 6 hours)
- **LOW**: Include in daily briefing only

### Relevance Matching Enhancement

The existing `RelevanceScorer` uses 5-factor weighted scoring. For alert matching,
we add a fast-path program matcher:

```python
def match_programs_fast(item: dict, programs: list[dict]) -> list[str]:
    """Quick program match for alert routing.

    Uses keyword overlap + CFDA number matching (no full 5-factor scoring).
    Returns list of matched program IDs.
    """
    text = f"{item['title']} {item.get('abstract', '')}".lower()
    matched = []
    for prog in programs:
        # CFDA match (exact, highest confidence)
        cfda = prog.get("cfda")
        if cfda and str(cfda) in text:
            matched.append(prog["id"])
            continue
        # Keyword match (any keyword hit)
        keywords = prog.get("keywords", [])
        if any(kw.lower() in text for kw in keywords):
            matched.append(prog["id"])
    return matched
```

### Tribe Routing

For each matched program, the router identifies affected Tribes using:

1. **Always-relevant programs** (bia_tcr, irs_elective_pay, epa_gap): Alert all 592 Tribes
2. **Hazard-specific programs**: Cross-reference `HAZARD_PROGRAM_MAP` from
   `src/packets/relevance.py` against each Tribe's hazard profile
3. **Ecoregion-priority programs**: Cross-reference `ecoregion_config.json` against
   each Tribe's ecoregion classification

The routing produces a per-Tribe alert payload:

```json
{
  "tribe_id": "epa_100000123",
  "tribe_name": "Muckleshoot Indian Tribe",
  "event_type": "appropriations_markup",
  "urgency": "CRITICAL",
  "title": "Interior Appropriations Subcommittee Markup Scheduled",
  "summary": "House Interior-Environment Subcommittee scheduled FY27 markup...",
  "affected_programs": [
    {"id": "bia_tcr", "name": "BIA Tribal Climate Resilience", "ci_status": "STABLE"},
    {"id": "epa_stag", "name": "EPA STAG", "ci_status": "STABLE"}
  ],
  "advocacy_context": {
    "recommended_action": "Contact delegation before markup",
    "structural_asks": ["Multi-Year Funding Stability", "Direct Tribal Access"],
    "delegation": [
      {"name": "Sen. Patty Murray", "state": "WA", "committee": "Appropriations"},
      {"name": "Rep. Adam Smith", "district": "WA-09"}
    ]
  },
  "source_url": "https://www.congress.gov/...",
  "detected_at": "2026-03-15T14:23:00Z"
}
```

### Dispatch Layer

Three delivery channels, configurable per Tribe:

| Channel | Use Case | Implementation |
|---------|----------|---------------|
| **Webhook** | Integration with Tribal IT systems, Slack, Teams | POST JSON to registered URL |
| **Email** | Direct notification to Tribal staff | SMTP (self-hosted) or AWS SES |
| **RSS Feed** | Per-Tribe or per-program alert feed | Static JSON feed on GitHub Pages |

The webhook approach respects Tribal data sovereignty -- each Nation controls where
their alerts are delivered and how they are processed. We never store Tribal contact
information; we store webhook URLs that the Tribes provide and control.

### State Management

Alert state is tracked to prevent duplicate notifications:

```
data/alert_state/
  last_poll.json          # Timestamp of last successful poll per endpoint
  seen_items.json         # Dedup registry (item_id -> first_seen_at)
  delivery_log.json       # Delivery audit trail (no Tribal PII)
```

The `seen_items.json` registry uses a 90-day rolling window (matching the existing
CI history cap) to prevent unbounded growth.

## Data Flow Summary

```
Congress.gov API
    │
    ├── /bill (every 2h) ──────────┐
    ├── /committee (every 4h) ─────┤
    ├── /amendment (every 2h) ─────┤
    └── /summaries (every 6h) ─────┤
                                   v
                          Change Detector
                          (dedup + classify)
                                   │
                                   v
                        Program Matcher (fast-path)
                        (16 programs x keywords + CFDA)
                                   │
                                   v
                          Tribe Router
                          (592 Tribes x relevance filter)
                                   │
                                   v
                        ┌──────────┼──────────┐
                        v          v          v
                    Webhook      Email     RSS Feed
```

## Dependencies

| Dependency | Status | Notes |
|------------|--------|-------|
| `src/scrapers/congress_gov.py` | Exists (v1.0) | Extend with new endpoints |
| `src/analysis/change_detector.py` | Exists (v1.0) | Extend with event classification |
| `src/analysis/relevance.py` | Exists (v1.0) | Add fast-path matcher |
| `src/packets/relevance.py` | Exists (v1.1) | Reuse `HAZARD_PROGRAM_MAP` for routing |
| `data/congressional_cache.json` | Exists (v1.1) | 538 members with committee assignments |
| `data/tribal_registry.json` | Exists (v1.1) | 592 Tribes with states and ecoregions |
| Congress.gov API key | Required | Already handled via `CONGRESS_API_KEY` env var |
| SMTP/SES credentials | New | For email dispatch channel |
| GitHub Actions scheduler | Exists (v1.0) | Add 2-hour alert workflow |

## Effort Estimate

### Phase 1: Polling Infrastructure (8 SP, Sprint 1)

- Extend `CongressGovScraper` with `/committee`, `/amendment`, `/summaries` endpoints
- Implement event type classifier
- Build alert state management (`data/alert_state/`)
- Add 2-hour polling schedule to GitHub Actions
- Tests: 15-20 new tests

### Phase 2: Routing and Matching (8 SP, Sprint 2)

- Build fast-path program matcher
- Build Tribe routing engine (program -> Tribes mapping)
- Integrate congressional delegation context from existing cache
- Build alert payload assembly
- Tests: 15-20 new tests

### Phase 3: Dispatch and Delivery (5 SP, Sprint 3)

- Implement webhook dispatch (POST JSON with retry)
- Implement email dispatch (template + SMTP/SES)
- Implement RSS feed generation (static JSON on GitHub Pages)
- Build delivery logging and dedup
- Per-Tribe subscription configuration
- Tests: 10-15 new tests

**Total: 21 story points across 3 sprints (~6 weeks)**

## Impact Statement: How This Serves Tribal Sovereignty

Today, a Tribal Leader preparing for a congressional meeting must manually track
committee schedules, bill introductions, and appropriations markups across multiple
federal websites. This creates an information asymmetry where well-resourced
lobbyists know about legislative developments hours before the communities most
affected by them.

Real-time congressional alerts directly address this asymmetry. When 592 Tribal
Nations receive structured, actionable intelligence within hours of a relevant
congressional action, the advocacy playing field levels. A Tribal climate
coordinator does not need a K Street lobbyist to tell her that the Interior
Appropriations Subcommittee just scheduled a markup -- she gets a notification
with her Tribe's affected programs, her delegation's contact information, and
the specific advocacy lever to deploy.

This is what data sovereignty looks like in practice: Tribal Nations controlling
their own information flow, on their own timeline, with their own tools.

Every hour of advance notice is an hour of advocacy capacity. If this system notifies
even 50 Tribal Leaders about one critical appropriations markup that they would
otherwise have missed, and even 10 of those Leaders contact their delegation before
the markup, the downstream impact on programs like BIA TCR and EPA STAG could be
measured in millions of preserved funding.

The technology is not the innovation. The sovereignty is. This system exists so that
a Tribal Leader never has to say: "I wish I had known sooner."

---

*Proposed by Horizon Walker. Dream big. Plan small. Ship incrementally.*
