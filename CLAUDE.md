# TCR Policy Scanner

## What
Automated policy intelligence and congressional advocacy platform for Tribal
Climate Resilience. Scans 4 federal sources with full pagination and circuit
breaker resilience, scores relevance against 16 tracked programs, runs 5
threat/signal monitors, classifies advocacy goals via a 5-rule decision engine,
enriches with congressional intelligence (bill tracking, CFDA mapping, committee
activity, confidence scoring), and produces 4 document types (Doc A/B/C/D) with
audience-differentiated content for 592 federally recognized Tribal Nations.
Delivered via production website on GitHub Pages. Python 3.12. Apache 2.0.

TSDF Classification: T0 (Open). No Tribal-specific or sensitive data collected.

## Who We Serve
Tribal Nations across the Pacific Northwest and all 592 federally recognized
Tribes. This tool exists because Tribal Leaders advocating for climate resilience
funding deserve current, reliable policy intelligence. Every line of code serves
sovereignty. Every data point serves self-determination.

## Structure
```
config/                  - scanner_config.json, scoring weights
data/                    - program_inventory.json, policy_tracking.json, graph_schema.json
data/award_cache/        - per-Tribe USASpending award histories (592 files)
data/hazard_profiles/    - per-Tribe FEMA NRI + USFS hazard profiles (592 files)
src/
  main.py                - Pipeline orchestrator (6-stage DAG)
  config.py              - Dynamic FY, project-wide configuration
  paths.py               - Centralized path constants (35 constants)
  utils.py               - Shared utilities (format_dollars, etc.)
  scrapers/              - federal_register, grants_gov, congress_gov, usaspending, circuit_breaker, cfda_map
  analysis/              - relevance scorer, change detector, decision engine
  graph/                 - Knowledge graph builder + schema
  monitors/              - IIJA sunset, reconciliation, DHS funding, hot sheets, consultation
  reports/               - Markdown/JSON/DOCX generation
  packets/               - Per-Tribe DOCX packet assembly, DocxEngine, confidence scoring, congressional rendering, quality review
  schemas/               - Pydantic models (congressional intelligence, etc.)
scripts/                 - Data population, web index building, structural validation (14 scripts)
tests/                   - 964 tests (pytest)
outputs/                 - Generated briefings, graphs, monitor data, bug hunt findings
docs/web/                - Production website (Fuse.js search, ARIA combobox, dark mode)
.planning/               - GSD milestone planning (roadmaps, phases, research)
```

## How
- Install: `pip install -r requirements.txt`
- Test: `python -m pytest tests/ -v`
- Lint: `ruff check . && mypy src/`
- Run: `python -m src.main`
- Dry run: `python -m src.main --dry-run`
- Single source: `python -m src.main --source federal_register`
- Report only: `python -m src.main --report-only`
- All tribes: `python -m src.main --prep-packets --all-tribes`
- Build congressional intel: `python scripts/build_congressional_intel.py`
- Build web index: `python scripts/build_web_index.py`
- Validate DOCX structure: `python scripts/validate_docx_structure.py`

## Critical Rules (Non-Negotiable)
1. NEVER hardcode fiscal years. Use config, CLI args, or env vars.
   Wrong: "FY26", "FY2026", "2026" as string literals
   Right: config.FISCAL_YEAR, --fiscal-year arg, FISCAL_YEAR env var
2. ALL dollar formatting through ONE function: utils.format_dollars()
   No _format_dollars(), no local formatting functions. One source of truth.
3. Logger naming: ALWAYS use logging.getLogger(__name__)
   Never hardcode logger names as strings.
4. Graph schema paths: resolve via pathlib relative to project root.
   Never hardcode absolute or relative string paths.
   Right: PROJECT_ROOT = Path(__file__).resolve().parent.parent
5. Validate ALL extracted data against schemas before output.
6. Respect Tribal data sovereignty. T0 data only. No scraping Tribal websites.
7. Always pass encoding="utf-8" to open() and Path.write_text() on Windows.
8. Atomic writes: tmp file + os.replace() pattern for crash safety.

## Language and Values
- Always capitalize: Indigenous, Tribal, Nations, Peoples, Knowledge, Traditional
- Use "Tribal Nations" not "tribes" (lowercase)
- Frame as "relatives not resources"
- Sovereignty is the innovation, not the technical challenge
- Honor, Pride, and Respect guide every decision

## Agent Team Coordination
- .claude/agents/ contains specialist definitions for the TCR Research Team
- Each agent owns specific directories. Do NOT edit files outside your scope.
- Test before committing. Every change must pass existing tests.
- The orchestrator delegates. Teammates implement.
- Use the shared task list for dependency tracking.
- GSD workflow agents (.planning/) handle milestone planning and execution.
  TCR Research Team agents handle domain-specific research and implementation.
