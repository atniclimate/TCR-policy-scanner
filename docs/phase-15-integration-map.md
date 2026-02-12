# Phase 15: Congressional Intelligence Integration Map

**Phase:** 15-congressional-intelligence
**Date:** 2026-02-12
**Purpose:** Document every data handoff in the congressional intelligence pipeline from API ingestion through Tribal Leader delivery.

---

## 1. End-to-End Data Flow

```
Congress.gov API v3 (api.congress.gov)
  |
  | HTTPS GET /bill/{congress}/{type}?q={term}
  | Rate limited: 0.3s between requests, circuit breaker protected
  |
  v
CongressGovScraper.scan()
  | Paginated bill search across 11 legislative queries
  | 119th Congress, Tribal + (Resilience|Climate|Adaptation|Energy|Hazard)
  | Deduplicates by source_id across query results
  |
  v
CongressGovScraper._fetch_bill_detail()
  | Sub-endpoint fetches: /bill/{id}/cosponsors, /bill/{id}/committees
  | Enriches each bill with sponsor names, committee referrals
  |
  v
BillIntelligence (Pydantic model)
  | Validates: bill_id, title, status, sponsors, committees,
  |   latest_action, relevance_score, introduced_date
  | Rejects malformed records before they enter the cache
  |
  v
bill_relevance_scoring()
  | Matches bills to 16 tracked programs via keyword + committee overlap
  | Assigns relevance_score (0.0-1.0) per bill-program pair
  | Filters: only bills with score >= threshold kept
  |
  v
data/congressional_intel.json
  | Cached bill intelligence (all relevant bills, per-scan snapshot)
  | Format: {"bills": [...], "metadata": {"scan_date": ..., "congress": 119}}
  | Atomic write: tmp file + os.replace()
  |
  v
PacketOrchestrator.prepare_context()
  | Loads congressional_intel.json alongside registry, awards, hazards
  | Filters bills by Tribe's programs and delegation
  | Builds TribePacketContext with congressional_intel field
  |
  v
TribePacketContext.congressional_intel
  | Per-Tribe filtered data: bills affecting this Tribe's programs,
  |   sponsor/cosponsor matches with delegation, committee activity
  | Dataclass field: list[dict] with bill metadata + relevance scores
  |
  v
DocxEngine.generate()
  | Section ordering per DocumentTypeConfig (Doc A/B/C/D)
  | Calls render functions in sequence with TribePacketContext
  |
  v
render_bill_intelligence_section()
  | Doc A: Full briefing (top 2-3 bills) + compact cards (remaining)
  | Doc B: Curated subset, facts only, no strategy
  | Doc C/D: Regional aggregation of shared bills
  |
  v
confidence_level()
  | Assigns HIGH/MEDIUM/LOW badges based on data source confidence
  | Visual treatment: colored badges in DOCX cells
  |
  v
DOCX file on disk
  | outputs/packets/{internal|congressional}/{tribe_id}.docx
  | Atomic save: NamedTemporaryFile + os.replace()
  |
  v
GitHub Pages / SquareSpace iframe
  | Tribal Leader downloads or views via web widget
  | docs/web/ search interface indexes packet metadata
```

---

## 2. File-to-File Handoff Table

| Step | Source | Destination | Data Format | Records | Key Fields |
|------|--------|-------------|-------------|---------|------------|
| 1 | Congress.gov API v3 | CongressGovScraper (memory) | JSON (HTTP response) | ~50-200 bills per scan | bill.number, bill.title, bill.latestAction |
| 2 | CongressGovScraper | BillIntelligence model (memory) | Python dict -> Pydantic | 1 per bill | bill_id, title, status, sponsors, committees |
| 3 | BillIntelligence | `data/congressional_intel.json` | JSON file | All relevant bills | bills[], metadata.scan_date |
| 4 | `data/congressional_intel.json` | PacketOrchestrator (memory) | JSON -> Python dict | All bills loaded | Full bill records |
| 5 | `data/congressional_cache.json` | CongressionalMapper (memory) | JSON -> Python dict | 501 delegations | members, committees, delegations |
| 6 | PacketOrchestrator | TribePacketContext | Python dataclass | 1 per Tribe | congressional_intel: list[dict] |
| 7 | TribePacketContext | DocxEngine | Python dataclass | 1 per document | All context fields |
| 8 | DocxEngine | DOCX file | python-docx Document | 1 per Tribe per doc type | Rendered sections |
| 9 | DOCX file | GitHub Pages | Static file hosting | 992 documents (4 types) | .docx binary |

---

## 3. Data Sources Feeding Phase 15

| Source | File/API | Refresh Cadence | Used By |
|--------|----------|-----------------|---------|
| Congress.gov API v3 | `api.congress.gov/v3/bill` | Daily scan (weekday) | CongressGovScraper |
| Congressional cache | `data/congressional_cache.json` | Monthly rebuild | CongressionalMapper |
| Tribal registry | `data/tribal_registry.json` | Quarterly (EPA API) | TribalRegistry |
| Program inventory | `data/program_inventory.json` | Manual updates | ProgramRelevanceFilter |
| Graph schema | `data/graph_schema.json` | Updated per phase | Knowledge graph builder |
| Award cache | `data/award_cache/*.json` | Monthly (USASpending) | PacketOrchestrator |
| Hazard profiles | `data/hazard_profiles/*.json` | Annual (FEMA NRI) | PacketOrchestrator |
| Ecoregion config | `data/ecoregion_config.json` | Static | EcoregionMapper |

---

## 4. Module Responsibility Map

| Module | File | Responsibility | Inputs | Outputs |
|--------|------|---------------|--------|---------|
| CongressGovScraper | `src/scrapers/congress_gov.py` | API ingestion, pagination, dedup | API key, search queries | Raw bill dicts |
| BillIntelligence | `src/models/` (Phase 15) | Pydantic validation | Raw bill dicts | Validated bill objects |
| bill_relevance_scoring | `src/analysis/` (Phase 15) | Program-bill matching | Bills, programs | Scored bill-program pairs |
| CongressionalMapper | `src/packets/congress.py` | Delegation lookup | congressional_cache.json | Per-Tribe delegation |
| PacketOrchestrator | `src/packets/orchestrator.py` | Context assembly | All data sources | TribePacketContext |
| DocxEngine | `src/packets/docx_engine.py` | Document assembly | TribePacketContext | DOCX file |
| Section renderers | `src/packets/docx_sections.py` | Section rendering | Context + Document | Paragraphs in DOCX |
| HotSheetRenderer | `src/packets/docx_hotsheet.py` | Hot sheet rendering | Programs, delegation | Hot sheet pages |
| ProgramRelevanceFilter | `src/packets/relevance.py` | Program filtering | Hazards, ecoregions | 8-12 relevant programs |
| Confidence module | `src/analysis/` (Phase 15) | Confidence scoring | Data completeness | HIGH/MEDIUM/LOW |

---

## 5. Error Handling and Resilience

| Failure Point | Detection | Recovery | Fallback |
|---------------|-----------|----------|----------|
| Congress.gov API down | Circuit breaker OPEN after 3 failures | Wait 60s, HALF_OPEN probe | Use cached `congressional_intel.json` |
| API rate limited (429) | HTTP status code | Exponential backoff (0.3s -> 0.6s -> 1.2s) | Partial results from completed queries |
| Malformed bill data | Pydantic validation error | Skip individual bill, log warning | Other bills proceed normally |
| congressional_intel.json missing | FileNotFoundError in PacketOrchestrator | Log error, continue without intel | Packets generated without bill section |
| congressional_cache.json missing | FileNotFoundError in CongressionalMapper | Initialize empty cache structure | Delegation section shows "Data unavailable" |
| DOCX write failure | IOError during atomic save | Retry once, then skip Tribe | Other Tribes proceed normally |

---

## 6. Future Extensions

### 6.1 Alert System (ENH-001)

The alert system extends this pipeline by adding a diff layer between successive `congressional_intel.json` snapshots:

```
congressional_intel.json (current)
  +
congressional_intel.previous.json (rotated)
  |
  v
Change Detection Engine (ENH-001)
  |
  v
Per-Tribe Alert Routing
  |
  v
Alert Digest Section (in DOCX)
  +
JSON Alert Feed (for web widget)
```

See: `docs/ENH-001-congressional-alerts.md`

### 6.2 Knowledge Graph Extension (ENH-002)

Congressional data introduces new node and edge types to the knowledge graph:

```
BillNode --AFFECTS_PROGRAM--> ProgramNode (existing)
BillNode --SPONSORED_BY--> LegislatorNode (new)
BillNode --REFERRED_TO--> CommitteeNode (new)
TribeNode --DELEGATES_TO--> LegislatorNode (new)
```

See: `docs/ENH-002-knowledge-graph-congressional.md`

---

*Phase: 15-congressional-intelligence*
*Integration map generated: 2026-02-12*
