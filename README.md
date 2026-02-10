# TCR Policy Scanner

Automated policy intelligence pipeline for Tribal Climate Resilience advocacy. Scans federal policy sources, scores relevance against a program inventory, and generates actionable briefings for Tribal Leaders.

**TSDF Classification: T0 (Open)**
All data sourced from public federal documents. No Tribal-specific or sensitive data is collected or stored.

## Purpose

Tribal Leaders advocating for climate resilience funding need current, reliable policy intelligence. This scanner automates the collection and synthesis of federal policy developments across 16 programs tracked for Tribal Climate Resilience advocacy.

The scanner answers the question: *What has changed in the federal policy landscape that is relevant to Tribal Climate Resilience funding, and what can Tribal Leaders do about it?*

## What It Does

1. **Collects** policy documents from federal sources (Federal Register, Grants.gov, Congress.gov, USASpending)
2. **Scores** each item against the tracked program inventory using weighted relevance factors
3. **Builds a knowledge graph** connecting programs to authorities, barriers, and funding vehicles
4. **Monitors** for urgent threats via 5 monitors (IIJA sunset, reconciliation, Tribal consultation, Hot Sheets sync, DHS funding cliff)
5. **Classifies** each program with an advocacy goal using a 5-rule decision engine across 6 advocacy goals
6. **Generates briefings** formatted for Tribal Leaders with advocacy levers attached

## Programs Tracked

| Priority | Program | Federal Home | Advocacy Lever |
|----------|---------|-------------|----------------|
| CRITICAL | BIA Tribal Climate Resilience | BIA | Protect/expand the line; waived match, multi-year stability |
| CRITICAL | FEMA BRIC | FEMA | Restore/replace with Tribal set-aside |
| CRITICAL | IRS Elective Pay | Treasury/IRS | Defend against reconciliation repeal; protect Tribal instrumentality access |
| HIGH | Tribal Community Resilience Annual Awards | BIA | Protect award program; ensure multi-year planning capacity |
| HIGH | EPA STAG | EPA | Direct Tribal capitalization pathways |
| HIGH | EPA GAP | EPA | Increase funding; link to climate resilience readiness |
| HIGH | Tribal Air Quality Management | EPA | Protect Clean Air Act SS105 Tribal funding; link to climate co-benefits |
| HIGH | FEMA Tribal Mitigation Plans | FEMA | Fund planning; accelerate approvals |
| HIGH | DOT PROTECT | DOT | Maintain/expand Tribal set-aside |
| HIGH | USDA Wildfire Defense Grants | USFS | Add match waivers; long-term fuels pathways |
| HIGH | DOE Indian Energy | DOE | Protect FY26 appropriations; reduce burden |
| HIGH | HUD IHBG | HUD | Frame resilient housing as trust responsibility |
| HIGH | NOAA Tribal Grants | NOAA | Protect climate/coastal functions in appropriations |
| MEDIUM | FHWA TTP Safety | FHWA | Increase Tribal formula/discretionary resilience |
| MEDIUM | USBR WaterSMART | Reclamation | Expand Tribal drought access; lower match |
| MEDIUM | USBR TAP | Reclamation | Link TA to pre-award support |

## Quick Start

### Local

```bash
# Clone
git clone <private repository URL>
cd TCR-policy-scanner

# Install
pip install -r requirements.txt

# List tracked programs
python -m src.main --programs

# Dry run (shows what would be scanned)
python -m src.main --dry-run

# Full scan
python -m src.main

# Scan specific source
python -m src.main --source federal_register

# Generate report from cached data
python -m src.main --report-only

# Export knowledge graph from cached data
python -m src.main --graph-only

# Verbose logging
python -m src.main --verbose
```

### GitHub Actions (Automated)

The scanner runs automatically via GitHub Actions. No local computer needed.

**Setup:**

1. Push this repo to your private repository
2. Add API keys as repository secrets:
   - `CONGRESS_API_KEY`: Free key from [api.congress.gov](https://api.congress.gov/)
   - `SAM_API_KEY` (optional): Key from [SAM.gov](https://sam.gov/content/home)
3. The workflow runs at 6:00 AM Pacific every weekday
4. Reports are committed directly to the `outputs/` directory
5. Trigger a manual scan anytime from Actions > Daily Policy Scan > Run workflow

**Getting API Keys:**

- **Congress.gov**: Free, instant. Visit [api.congress.gov/sign-up](https://api.congress.gov/sign-up/)
- **Federal Register**: No key required (public API)
- **Grants.gov**: No key required (public API)
- **SAM.gov**: Free, may take 1-2 days. Visit [SAM.gov API access](https://sam.gov/content/home)

## Project Structure

```
TCR-policy-scanner/
    config/
        scanner_config.json     # Source definitions, search terms, scoring weights
    data/
        program_inventory.json  # The 16 tracked programs with advocacy levers
        policy_tracking.json    # CI status tracking and history
        graph_schema.json       # Knowledge graph node/edge type definitions
    src/
        main.py                 # Pipeline orchestrator
        scrapers/
            base.py             # Base scraper with retry, backoff, zombie CFDA detection
            federal_register.py # Federal Register API scraper
            grants_gov.py       # Grants.gov API scraper
            congress_gov.py     # Congress.gov API scraper
            usaspending.py      # USASpending API scraper
        analysis/
            relevance.py        # Multi-factor relevance scorer
            change_detector.py  # Scan-to-scan change detection
            decision_engine.py  # 5-rule advocacy goal classification (6 goals)
        graph/
            builder.py          # Knowledge graph construction
            schema.py           # Graph node and edge types
        monitors/
            hot_sheets.py       # Hot Sheets sync validator (CI override, staleness check)
            iija_sunset.py      # IIJA FY26 sunset countdown and reauth detection
            reconciliation.py   # Reconciliation bill threat detection (IRA S6417)
            dhs_funding.py      # DHS Continuing Resolution funding cliff monitor
            tribal_consultation.py # Tribal consultation signal detection (DTLLs, EO 13175)
        reports/
            generator.py        # Markdown and JSON report generation
    tests/
        test_decision_engine.py # 52 tests covering all 5 decision rules
    outputs/
        LATEST-BRIEFING.md      # Most recent policy briefing
        LATEST-RESULTS.json     # Most recent machine-readable results
        LATEST-GRAPH.json       # Most recent knowledge graph export
        LATEST-MONITOR-DATA.json # Most recent monitor alerts and classifications
        .ci_history.json        # CI score snapshots for trend tracking
        .cfda_tracker.json      # Zombie CFDA detection state
        .monitor_state.json     # Hot Sheets divergence tracking state
        archive/                # Historical reports
    validate_data_integrity.py  # Cross-file consistency validator (8 checks)
    .github/
        workflows/
            daily-scan.yml      # Automated daily scan via GitHub Actions
```

## Pipeline

The scanner runs a six-stage DAG pipeline:

```
Ingest -> Normalize -> Graph Construction -> Monitors -> Decision Engine -> Reporting
```

**Monitors** produce alerts and inject THREATENS edges into the knowledge graph. The **Decision Engine** then classifies each program into one of 6 advocacy goals using 5 prioritized rules (LOGIC-05 through LOGIC-04, evaluated in priority order). Programs matching no rule receive the default MONITOR_ENGAGE goal.

| Rule | Advocacy Goal | Trigger |
|------|--------------|---------|
| LOGIC-05 | Urgent Stabilization | THREATENS edge within urgency window |
| LOGIC-01 | Restore/Replace | TERMINATED/FLAGGED program with permanent authority |
| LOGIC-02 | Protect Base | Discretionary funding facing eliminate/reduce signals |
| LOGIC-03 | Direct Access Parity | State pass-through with high administrative barriers |
| LOGIC-04 | Expand and Strengthen | STABLE/SECURE program with direct or set-aside access |
| *(default)* | Monitor and Engage | No specific rule matched |

## Relevance Scoring

Each item is scored using five weighted factors:

| Factor | Weight | Description |
|--------|--------|-------------|
| Program Match | 0.35 | Direct match to a tracked program |
| Tribal Keyword Density | 0.20 | Concentration of Tribal-relevant terms |
| Recency | 0.10 | Publication date proximity |
| Source Authority | 0.15 | Federal source reliability weight |
| Action Relevance | 0.20 | Signals actionable policy change |

Items matching **critical priority programs** receive a 15% score boost. Items below a 0.30 relevance threshold are filtered out.

## Knowledge Graph

The graph schema defines 7 node types and 8 edge types:

**Node types:** ProgramNode, AuthorityNode, FundingVehicleNode, BarrierNode, AdvocacyLeverNode, TrustSuperNode, ObligationNode

**Edge types:**
- AUTHORIZED_BY (Program -> Authority)
- FUNDED_BY (Program -> FundingVehicle)
- BLOCKED_BY (Program -> Barrier)
- MITIGATED_BY (Barrier -> AdvocacyLever)
- OBLIGATED_BY (Program -> Obligation)
- ADVANCES (StructuralAsk -> Program)
- TRUST_OBLIGATION (TrustSuperNode -> Program)
- THREATENS (ThreatNode -> Program)

## Testing

The test suite contains 52 tests covering all 5 decision engine rules, priority ordering, default fallback behavior, secondary rules transparency, classification shape validation, and edge cases.

```bash
# Run all tests
python -m pytest tests/ -v

# Run decision engine tests only
python -m pytest tests/test_decision_engine.py -v
```

## Data Integrity Validation

A standalone validator checks cross-file consistency across all data files:

```bash
python validate_data_integrity.py
```

This runs 8 checks: JSON validity, program ID consistency, CFDA consistency, graph schema references, barrier mitigation references, CI threshold ordering, status consistency, and keyword deduplication.

## Extending the Scanner

### Adding Programs

Edit `data/program_inventory.json` to add new programs to the tracking list. Each program needs:
- Unique `id`
- `keywords` for matching
- `search_queries` for source-specific scanning
- `advocacy_lever` for the report output
- `priority` level (critical, high, medium, low)
- `access_type` (direct, competitive, or tribal_set_aside)
- `funding_type` (Discretionary, Mandatory, or One-Time)
- `cfda` (CFDA/Assistance Listing Number, or null)

### Adding Sources

Create a new scraper in `src/scrapers/` following the pattern of existing scrapers. Each scraper needs:
- An async `scan()` method that returns a list of normalized items
- A `_normalize()` method that maps source-specific fields to the standard schema

### Adding Notification Channels

The GitHub Actions workflow can be extended to send notifications via:
- Email (using GitHub Actions email actions)
- Slack (using the Slack webhook action)
- Microsoft Teams (using the Teams webhook action)

## Data Sovereignty Note

This scanner operates exclusively on **T0 (Open)** data under the Tiered Sovereignty Data Framework. It collects only public federal policy documents. No Tribal-specific data, Traditional Knowledge, or community information is collected, stored, or transmitted.

The scanner is a tool to support Tribal sovereignty in policy advocacy, not a replacement for Tribal decision-making processes.

## License

Apache 2.0

## Maintained By

Project contributors
