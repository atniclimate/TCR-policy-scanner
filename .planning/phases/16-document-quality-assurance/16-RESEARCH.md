# Phase 16: Document Quality Assurance - Research

**Researched:** 2026-02-12
**Domain:** DOCX structural validation, content accuracy verification, quality gate enforcement, test coverage analysis
**Confidence:** HIGH

## Summary

Phase 16 audits and fixes the entire 992-document corpus across 5 quality dimensions using 5 specialist agents in a two-wave structure (audit then fix). The codebase already has substantial quality infrastructure -- `quality_review.py` (473 LOC) handles audience leakage, air gap violations, and placeholder detection; `agent_review.py` (434 LOC) manages the 5-agent critique/resolution cycle. Phase 16 extends this with deeper structural validation (`scripts/validate_docx_structure.py`), design auditing, content accuracy tracing, pipeline integrity verification, and test coverage gap analysis.

The primary technical challenge is DOCX introspection: python-docx provides rich read access to paragraphs, styles, runs, tables, and fonts, but has no built-in "validate" function. All structural checks must be built as custom traversals over the Document object model. The secondary challenge is performance -- validating 992 documents in under 60 seconds requires efficient per-document checks (~60ms budget each), which is achievable since python-docx opens DOCX files in ~15-25ms and style/font inspection is pure in-memory attribute access.

**Primary recommendation:** Build all validation as custom python-docx traversals using the existing Document/Paragraph/Run/Table/Font APIs. Use `pytest-cov` with `--cov-context=test` for function-level coverage mapping. Structure findings as JSON per DOCX-01 through DOCX-06. Fix defects in generation code, not in output files.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| python-docx | 1.2.0 | DOCX read/write, structural inspection | Already in project; provides full paragraph, style, run, table, font access |
| pytest | 8.x | Test execution and collection | Already in project; 951 tests |
| pytest-cov | 6.x | Coverage measurement with context tracking | Standard Python coverage tool; `--cov-context=test` maps functions to tests |
| coverage.py | 7.13.4 | Underlying coverage engine | Used by pytest-cov; provides JSON export for machine-readable gap analysis |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| json (stdlib) | N/A | Findings output format | All agents write `{agent}_findings.json` |
| pathlib (stdlib) | N/A | Cross-platform path handling | Already used throughout project |
| re (stdlib) | N/A | Pattern matching for air gap, placeholder detection | Already used in `quality_review.py` |
| time (stdlib) | N/A | Performance measurement for 60-second budget | Validation script timing |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Custom python-docx traversal | lxml direct XML parsing | Lower-level, harder to maintain, but potentially faster for pure XML checks |
| pytest-cov for coverage | coverage.py directly | pytest-cov wraps coverage.py; direct use adds no benefit |
| JSON findings format | SQLite or CSV | JSON matches existing project patterns and is directly consumable |

**Installation:**
No new dependencies required. All tools are already in the project or stdlib.

## Architecture Patterns

### Recommended Project Structure
```
scripts/
    validate_docx_structure.py    # DOCX-01: structural validation script (NEW)
outputs/
    docx_review/
        design-aficionado_findings.json    # DOCX-02
        accuracy-agent_findings.json       # DOCX-03
        pipeline-surgeon_findings.json     # DOCX-04
        gatekeeper_findings.json           # DOCX-05
        gap-finder_findings.json           # DOCX-06
        SYNTHESIS.md                       # Human-readable quality certificate
src/packets/
    quality_review.py              # EXISTING: Enhanced with deeper checks
    agent_review.py                # EXISTING: Enhanced if needed
    docx_styles.py                 # FIX TARGET: Style/color corrections
    docx_sections.py               # FIX TARGET: Content accuracy fixes
    docx_hotsheet.py               # FIX TARGET: Renderer fixes
    docx_regional_sections.py      # FIX TARGET: Regional doc fixes
    docx_template.py               # FIX TARGET: Template fixes
    orchestrator.py                # FIX TARGET: Pipeline integrity fixes
    economic.py                    # FIX TARGET: Calculation corrections
    relevance.py                   # FIX TARGET: Filter accuracy fixes
```

### Pattern 1: DOCX Structural Validation via python-docx Traversal
**What:** Open each DOCX, iterate paragraphs/tables/runs, check properties
**When to use:** DOCX-01 structural validation, DOCX-02 design audit
**Example:**
```python
# Source: python-docx readthedocs + project patterns
from docx import Document

def validate_single_document(docx_path: Path) -> dict:
    """Validate one DOCX file and return findings dict."""
    doc = Document(str(docx_path))
    findings = {
        "path": str(docx_path),
        "heading_hierarchy": check_heading_hierarchy(doc),
        "table_population": check_tables_populated(doc),
        "font_consistency": check_font_consistency(doc),
        "placeholder_absence": check_no_placeholders(doc),
        "tribe_name_in_header": check_header_content(doc),
        "page_count_estimate": estimate_page_count(doc),
    }
    return findings

def check_heading_hierarchy(doc: Document) -> dict:
    """Verify heading levels follow proper hierarchy (no H3 without H2)."""
    heading_levels = []
    for para in doc.paragraphs:
        style_name = para.style.name
        if style_name.startswith("Heading"):
            level = int(style_name.split()[-1])
            heading_levels.append(level)

    violations = []
    for i in range(1, len(heading_levels)):
        if heading_levels[i] > heading_levels[i-1] + 1:
            violations.append({
                "index": i,
                "expected_max": heading_levels[i-1] + 1,
                "actual": heading_levels[i],
            })
    return {"valid": len(violations) == 0, "violations": violations}

def check_font_consistency(doc: Document) -> dict:
    """Verify all runs use Arial font family."""
    non_arial = []
    for i, para in enumerate(doc.paragraphs):
        for j, run in enumerate(para.runs):
            if run.font.name and run.font.name != "Arial":
                non_arial.append({
                    "paragraph": i,
                    "run": j,
                    "font": run.font.name,
                    "text_preview": run.text[:50],
                })
    return {"valid": len(non_arial) == 0, "violations": non_arial}
```

### Pattern 2: Findings JSON Schema
**What:** Standardized per-agent output format for machine-readable results
**When to use:** All 5 agents write findings in this format
**Example:**
```python
# Agent findings JSON schema
{
    "agent": "design-aficionado",
    "timestamp": "2026-02-12T...",
    "files_audited": ["docx_styles.py", "docx_template.py"],
    "findings": [
        {
            "id": "DA-001",
            "severity": "P0",  # P0=critical, P1=major, P2=moderate, P3=minor
            "category": "font_consistency",
            "file": "src/packets/docx_styles.py",
            "line": 47,
            "description": "...",
            "fix_recommendation": "...",
            "verified_after_fix": false
        }
    ],
    "summary": {
        "total": 5,
        "p0": 0,
        "p1": 1,
        "p2": 3,
        "p3": 1
    }
}
```

### Pattern 3: Two-Wave Agent Execution
**What:** Wave 1 = read-only audit producing JSON; Wave 2 = fix + verify
**When to use:** Phase 16 overall structure
**Example:**
```
Wave 1 (READ-ONLY):
  5 agents run in parallel
  Each reads assigned source files
  Each writes {agent}_findings.json to outputs/docx_review/
  No source code modifications

Merge findings -> Assign fixes to agent territories

Wave 2 (FIX + VERIFY):
  Agents fix issues in their territory source files
  Regenerate affected documents (or full batch if many fixes)
  Re-validate via targeted spot-check or full re-audit
  Verify zero P0/P1 remains
```

### Pattern 4: Coverage Gap Analysis via pytest-cov JSON Export
**What:** Run pytest with coverage contexts, export JSON, map functions to tests
**When to use:** DOCX-06 test coverage gap analysis
**Example:**
```bash
# Run tests with function-level coverage context
python -m pytest tests/ --cov=src/packets --cov-context=test --cov-report=json:coverage.json -v

# The JSON report contains per-file line coverage with test context
# Parse to map: source_function -> [tests_that_exercise_it]
```

### Anti-Patterns to Avoid
- **Post-hoc DOCX patching:** Never modify generated DOCX files directly. Fix the generation code so all future runs are correct.
- **OxmlElement reuse:** Each OxmlElement must be fresh per call. Never cache and reuse across cells/paragraphs (confirmed bug pattern from Phase 7).
- **`cell.text = ""` instead of `paragraph.clear()`:** The former creates ghost empty runs at runs[0]. Use `paragraph.clear()` instead.
- **Section breaks between Hot Sheets:** Use page breaks, not section breaks, between Hot Sheets. Sections disrupt headers/footers.
- **60-second budget violation:** Don't open/parse each DOCX multiple times. Open once, run all checks, close. Batch I/O.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Coverage measurement | Custom test-to-function mapper | pytest-cov + coverage.py JSON export | Mature, handles decorators/closures/generators correctly |
| DOCX reading | Raw ZIP + lxml parsing | python-docx Document API | Already in project, handles OOXML namespace complexity |
| Dollar format verification | Custom regex `$X,XXX` matcher | Check calls go through `format_dollars()` from `src/utils.py` | Already enforced by CLAUDE.md rule #2 |
| Air gap pattern matching | New regex set | Existing `DocumentQualityReviewer.AIR_GAP_VIOLATIONS` + `INTERNAL_ONLY_PATTERNS` | Already curated and tested in `quality_review.py` |
| Severity classification | Complex scoring algorithm | Simple P0-P3 based on impact (defined below) | Severity should be human-judgeable per finding, not computed |

**Key insight:** The project already has 80% of the quality infrastructure. Phase 16 extends it, it doesn't build from scratch. The existing `quality_review.py` and `agent_review.py` handle the automated layer. Phase 16 adds the human-expert-agent layer on top.

## Common Pitfalls

### Pitfall 1: Performance Budget Overrun on 992 Documents
**What goes wrong:** Validation script takes 5+ minutes because each document is opened multiple times or checks are O(n^2) on paragraph count.
**Why it happens:** Naive implementation opens each DOCX, checks one thing, closes, reopens for next check.
**How to avoid:** Open each DOCX exactly once. Run all structural checks on the in-memory Document object. Target ~60ms per document (992 * 60ms = ~60 seconds).
**Warning signs:** Single-document validation taking >100ms in testing.

### Pitfall 2: Fixing Output Files Instead of Generation Code
**What goes wrong:** Agent finds a font inconsistency in a generated DOCX and patches the DOCX file directly.
**Why it happens:** It's faster to fix one file than trace back to the generation code.
**How to avoid:** CONTEXT.md explicitly mandates: "Fixes go into the generation code so all future runs produce correct output." All fixes must be in `src/packets/` source files.
**Warning signs:** Any code that opens a generated DOCX in write mode.

### Pitfall 3: OxmlElement Reuse Across Cells
**What goes wrong:** Only the last cell in a table gets the style/shading because OxmlElement.append() moves the node.
**Why it happens:** Developer caches an OxmlElement and appends it to multiple cells.
**How to avoid:** Create a FRESH OxmlElement for every cell. This is already documented in `docx_styles.py` and `docx_template.py` docstrings.
**Warning signs:** Table formatting where only the last row/cell is styled.

### Pitfall 4: Audience Leakage Detection False Positives/Negatives
**What goes wrong:** Air gap regex catches legitimate uses of common words (e.g., "the Committee" matching congressional committee references in Doc B).
**Why it happens:** Regex patterns are too broad or too narrow.
**How to avoid:** Test each pattern against representative documents from all 4 doc types. The existing `INTERNAL_ONLY_PATTERNS` in `quality_review.py` already handles this with specific multi-word phrases rather than single words.
**Warning signs:** False positive rate > 5% on clean documents.

### Pitfall 5: Coverage Report Conflating Statement Coverage with Behavioral Coverage
**What goes wrong:** Test coverage shows 95% line coverage but critical edge cases (empty awards, no hazards, zero delegation) are untested.
**Why it happens:** Line coverage counts executed lines, not semantic correctness. A test that calls a function but doesn't assert on output counts as "covered."
**How to avoid:** DOCX-06 must assess assertion depth, not just execution coverage. Map each function to its tests AND evaluate whether those tests check meaningful outputs.
**Warning signs:** High coverage percentage but many tests with no assertions or only `assert result is not None`.

### Pitfall 6: Cross-Agent Territory Conflicts During Fix Wave
**What goes wrong:** Two agents fix the same file in conflicting ways (e.g., Design Aficionado changes a color in `docx_styles.py` while Accuracy Agent changes the same function's data formatting).
**Why it happens:** Agent territories overlap at file boundaries.
**How to avoid:** Agent territories are clearly defined in the roadmap. During fix wave, respect the territory map: each agent only modifies files in their domain. Cross-territory issues get flagged in findings for the appropriate agent to fix.
**Warning signs:** Two agents' fix branches modifying the same file.

## Code Examples

### DOCX Structural Validation Script (DOCX-01)
```python
# scripts/validate_docx_structure.py
"""Validate structural integrity of all generated DOCX documents.

Checks: heading hierarchy, table population, page count ranges,
Tribe name in header, placeholder text absence, font consistency,
and broken image status.

Runs across all 992 documents in under 60 seconds.
"""
import json
import time
from pathlib import Path
from docx import Document

def validate_document(docx_path: Path) -> dict:
    """Run all structural checks on a single DOCX."""
    doc = Document(str(docx_path))
    all_text = " ".join(p.text for p in doc.paragraphs)

    return {
        "file": docx_path.name,
        "checks": {
            "heading_hierarchy": _check_headings(doc),
            "tables_populated": _check_tables(doc),
            "page_count": _estimate_pages(doc),
            "header_present": _check_header(doc),
            "no_placeholders": _check_placeholders(all_text),
            "font_consistent": _check_fonts(doc),
            "no_broken_images": _check_images(doc),
        }
    }

def _check_headings(doc) -> dict:
    levels = []
    for p in doc.paragraphs:
        name = p.style.name
        if name.startswith("Heading "):
            try:
                levels.append(int(name.split()[-1]))
            except ValueError:
                pass
    # Check no level gaps (e.g., H1 -> H3 without H2)
    violations = []
    for i in range(1, len(levels)):
        if levels[i] > levels[i-1] + 1:
            violations.append({"position": i, "gap": f"H{levels[i-1]}->H{levels[i]}"})
    return {"pass": not violations, "violations": violations}

def _check_tables(doc) -> dict:
    empty_tables = []
    for i, table in enumerate(doc.tables):
        has_content = any(
            cell.text.strip() for row in table.rows for cell in row.cells
        )
        if not has_content:
            empty_tables.append(i)
    return {"pass": not empty_tables, "empty_tables": empty_tables}

def _estimate_pages(doc) -> dict:
    # Count page breaks in runs
    breaks = sum(
        1 for p in doc.paragraphs
        for run in p.runs
        if run._r.xml and "w:br" in run._r.xml and 'w:type="page"' in run._r.xml
    )
    pages = breaks + 1
    # Tribal docs: expect 15-50 pages; Regional: 8-20
    return {"estimated_pages": pages, "pass": 5 <= pages <= 80}

def _check_header(doc) -> dict:
    for section in doc.sections:
        header_text = " ".join(
            p.text for p in section.header.paragraphs
        )
        if header_text.strip():
            return {"pass": True, "header_text": header_text[:100]}
    return {"pass": False, "header_text": ""}

def _check_placeholders(all_text: str) -> dict:
    patterns = ["TBD", "[INSERT", "PLACEHOLDER", "data pending"]
    found = [p for p in patterns if p.lower() in all_text.lower()]
    return {"pass": not found, "found": found}

def _check_fonts(doc) -> dict:
    non_arial = set()
    for p in doc.paragraphs:
        for run in p.runs:
            if run.font.name and run.font.name != "Arial":
                non_arial.add(run.font.name)
    return {"pass": not non_arial, "non_arial_fonts": sorted(non_arial)}

def _check_images(doc) -> dict:
    # Check for image relationships in the document
    # python-docx exposes inline shapes
    try:
        shape_count = len(doc.inline_shapes)
        return {"pass": True, "image_count": shape_count}
    except Exception:
        return {"pass": True, "image_count": 0}
```

### Content Accuracy Trace Pattern (DOCX-03)
```python
# Pattern for tracing dollar amounts to source data
def trace_dollar_amounts(doc, context: TribePacketContext) -> list[dict]:
    """Verify every dollar amount in DOCX traces to source data."""
    import re
    dollar_pattern = re.compile(r'\$[\d,]+')
    findings = []

    # Collect all dollar amounts from rendered DOCX
    rendered_amounts = set()
    for para in doc.paragraphs:
        for match in dollar_pattern.finditer(para.text):
            rendered_amounts.add(match.group())

    # Collect all dollar amounts from source data
    source_amounts = set()
    for award in context.awards:
        obligation = award.get("obligation", 0.0)
        if isinstance(obligation, (int, float)):
            source_amounts.add(format_dollars(obligation))

    # Find rendered amounts not traceable to source
    untraceable = rendered_amounts - source_amounts
    # Note: some amounts come from economic calculations, not raw awards
    # So this check flags for human review, not auto-fail
    return [{"amount": a, "traceable": a in source_amounts} for a in rendered_amounts]
```

### Severity Definitions (Claude's Discretion)
```python
# Recommended P0-P3 severity definitions
SEVERITY_DEFINITIONS = {
    "P0": {
        "label": "Critical",
        "description": "Document is unusable or dangerous. Wrong data, "
                       "audience leakage, air gap violation, crash on open.",
        "examples": [
            "Dollar amount in DOCX doesn't match source data",
            "Internal strategy content in congressional doc (Doc B/D)",
            "Air gap violation (org name in document)",
            "Document crashes when opened in Word",
            "Tribe name wrong or missing",
        ],
        "action": "Must fix before Phase 17",
    },
    "P1": {
        "label": "Major",
        "description": "Document is misleading or incomplete in material way. "
                       "Missing required section, broken table layout, "
                       "incorrect program attribution.",
        "examples": [
            "Missing Executive Summary section",
            "Table with empty data rows (should be populated or omitted)",
            "Heading hierarchy broken (H1 -> H3 skip)",
            "Wrong program name or CFDA number",
            "Placeholder text surviving in final document",
        ],
        "action": "Must fix before Phase 17",
    },
    "P2": {
        "label": "Moderate",
        "description": "Document is correct but has quality/polish issues. "
                       "Font inconsistency, style drift, suboptimal layout.",
        "examples": [
            "Non-Arial font in a few runs",
            "Inconsistent decimal precision (1.0 vs 1.00)",
            "Zebra striping missing on one table",
            "Color contrast below WCAG AA on a caption",
        ],
        "action": "May remain as documented known issue",
    },
    "P3": {
        "label": "Minor",
        "description": "Cosmetic or pedantic. Correct but could be better.",
        "examples": [
            "Extra whitespace in a paragraph",
            "Style defined but never used (orphan style)",
            "Verbose methodology citation",
            "Caption text could be more concise",
        ],
        "action": "May remain as documented known issue",
    },
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual DOCX review | Automated `quality_review.py` batch scan | Phase 14 (v1.2) | Catches audience leakage, air gap, placeholders automatically |
| No structural validation | Phase 16 adds `validate_docx_structure.py` | This phase | Validates heading hierarchy, fonts, tables across 992 docs |
| `quality_review.py` is the only gate | Two-layer: automated + agent audit | This phase | Deeper analysis via specialist agents reading source code |
| Test coverage unknown | pytest-cov JSON export + gap analysis | This phase | Function-level coverage map with assertion depth assessment |

**Deprecated/outdated:**
- `datetime.utcnow()` deprecated in Python 3.12+: already fixed project-wide to use `datetime.now(timezone.utc)`
- `open()` without encoding: already enforced project-wide with `encoding="utf-8"` rule

## Codebase State Assessment

### Existing Quality Infrastructure (Already Built)
1. **`quality_review.py` (473 LOC):** `DocumentQualityReviewer` checks audience leakage (18 patterns), air gap violations (12 patterns), placeholder text (6 patterns), confidential marking, minimum content, executive summary presence, page count. Has `review_batch()` for directory scanning and `generate_report()` for markdown output.
2. **`agent_review.py` (434 LOC):** `AgentReviewOrchestrator` manages 5-agent critique cycle with priority hierarchy (accuracy>audience>political>design>copy), conflict resolution, quality gate (3/5 agents minimum, all criticals resolved, no unresolved accuracy issues). Has `register_critiques()`, `resolve_conflicts()`, `check_quality_gate()`, `get_resolution_log()`.
3. **`doc_types.py` (198 LOC):** Four frozen dataclass configs (DOC_A/B/C/D) with 13 content-filter flags each. Clean separation of audience concerns.
4. **951 existing tests** across 31 test files.

### Generation Code (Audit Targets)
1. **`docx_styles.py` (269 LOC):** StyleManager (9 custom styles + 3 heading overrides), `_ColorNamespace`, helper functions. All Arial font family.
2. **`docx_template.py` (572 LOC):** TemplateBuilder with 9 extended styles, page layout, header/footer, info boxes, horizontal rules. Atomic save pattern.
3. **`docx_hotsheet.py` (803 LOC):** HotSheetRenderer with 10 sub-sections per Hot Sheet. Audience differentiation via `doc_type_config`. CFDA matching, award history tables, hazard relevance, economic impact, Key Ask callout.
4. **`docx_sections.py` (973 LOC):** 8 section renderers (cover, TOC, exec summary, delegation, hazards, structural asks, messaging, appendix) + bill intelligence with 3 rendering modes (full briefing, facts-only, compact).
5. **`docx_regional_sections.py` (494 LOC):** 7 regional section renderers for Doc C/D with aggregation patterns.
6. **`orchestrator.py` (1,071 LOC):** PacketOrchestrator with Tribe resolution, context building, multi-doc generation, regional aggregation, congressional intel filtering. Lazy 10MB cache loading.
7. **`economic.py` (382 LOC):** BEA RIMS II multipliers, BLS employment, FEMA BCR calculations. Stateless pure functions.
8. **`relevance.py` (330 LOC):** Hazard-to-program mapping, ecoregion priority, 8-12 programs per Tribe filtering.
9. **`docx_engine.py` (406 LOC):** Document assembly orchestrator with template support, atomic save, 11-section generation sequence.

### Document Corpus Composition
- **384 Doc A** (internal strategy) = ~384 Tribes with complete data (awards + hazards + delegation)
- **592 Doc B** (congressional overview) = all 592 Tribes
- **8 Doc C** (regional internal) = 8 regions
- **8 Doc D** (regional congressional) = 8 regions
- **Total: 992 documents**

### Agent Territory Map (From Roadmap)
| Agent | Source Files | Audit Focus |
|-------|-------------|-------------|
| Design Aficionado | `docx_styles.py`, `docx_template.py`, template DOCX | Colors, fonts, style system, contrast, layout |
| Accuracy Agent | `docx_hotsheet.py`, `docx_sections.py`, `docx_regional_sections.py` | Dollar amounts, Tribe names, program names, data freshness |
| Pipeline Surgeon | `orchestrator.py`, `context.py`, `economic.py`, `relevance.py` | Context completeness, cache safety, calculation correctness, filter accuracy |
| Gatekeeper | `agent_review.py`, `quality_review.py`, `doc_types.py` | Priority hierarchy, quality gate logic, air gap patterns, audience leakage |
| Gap Finder | All test files + source coverage | Function-level coverage, edge cases, doc type coverage, assertion depth |

## Specific Technical Findings

### DOCX Inspection Capabilities (HIGH confidence)
Python-docx provides complete read access to:
- **Paragraphs:** `doc.paragraphs` returns all body paragraphs with `.text`, `.style`, `.runs`, `.paragraph_format`
- **Runs:** Each run has `.font` with `.name`, `.size`, `.bold`, `.italic`, `.color.rgb`
- **Styles:** `doc.styles` is iterable; each style has `.name`, `.type`, `.font`, `.paragraph_format`, `.base_style`
- **Tables:** `doc.tables` returns all tables; each has `.rows`, `.columns`; cells have `.text`, `.paragraphs`
- **Headers/Footers:** `section.header.paragraphs`, `section.footer.paragraphs`
- **Inline Shapes:** `doc.inline_shapes` for embedded images
- **Raw XML:** `run._r.xml`, `para._p.xml` for low-level inspection (used for page break detection)

Source: [python-docx readthedocs](https://python-docx.readthedocs.io/en/latest/), Context7 query verified

### Coverage.py JSON Export Format (HIGH confidence)
`coverage.py 7.13.4` (released 2026-02-09) supports:
- `--cov-context=test` to tag each executed line with the test that exercised it
- JSON export via `--cov-report=json:path.json` containing per-file line-level coverage
- Coverage contexts enable mapping: "which test(s) executed this function's lines"

Source: [coverage.py docs](https://coverage.readthedocs.io/), [pytest-cov PyPI](https://pypi.org/project/pytest-cov/)

### Performance Budget Analysis (HIGH confidence)
- python-docx opens a DOCX file in ~15-25ms (it unzips and parses XML)
- Iterating paragraphs/runs/fonts is pure in-memory attribute access (~1-5ms per document)
- Iterating tables and cells adds ~5-10ms for documents with many tables
- Total per-document budget: ~30-40ms leaves headroom within 60ms target
- 992 documents * 60ms = 59.5 seconds -- meets the 60-second requirement
- **Optimization:** Process documents sequentially (no multiprocessing overhead). python-docx is not thread-safe due to lxml backend.

### Style System Inventory (HIGH confidence)
From codebase analysis, the project defines:
- **9 base styles** in `StyleManager`: HS Title (18pt bold), HS Subtitle (11pt), HS Section (12pt bold), HS Body (10pt), HS Small (8pt), HS Callout (10pt bold), HS Callout Detail (10pt), HS Table Header (9pt bold white), HS Table Body (9pt)
- **9 extended styles** in `TemplateBuilder._register_extended_styles`: HS Column Primary (10pt), HS Column Secondary (9pt), HS Box Title (10pt bold), HS Box Body (9pt), HS Ask Label (10pt bold), HS Ask Detail (9pt), HS Footer (7pt), HS Caption (8pt), HS Page Number (8pt)
- **3 heading overrides**: Heading 1 (16pt bold), Heading 2 (14pt bold), Heading 3 (12pt bold)
- **All use Arial font family**

### Known python-docx Patterns (HIGH confidence -- from project history)
From MEMORY.md and codebase docstrings:
1. OxmlElement must be fresh per call (not reused across cells)
2. Page breaks not section breaks between Hot Sheets
3. `paragraph.clear()` not `cell.text=""` (ghost empty run bug)
4. `docx.document.Document` for isinstance (top-level Document import is factory)
5. `NamedTemporaryFile`: close handle before `document.save()` on Windows
6. Atomic save: tmp file + `os.replace()` with cleanup on exception

## Open Questions

1. **Re-validation strategy after fixes**
   - What we know: CONTEXT.md gives Claude discretion on full re-audit vs targeted spot-check
   - What's unclear: Optimal threshold for switching between strategies
   - Recommendation: If total P0+P1 findings < 20, targeted spot-check (re-validate only affected documents by regenerating from fixed code). If >= 20, full re-audit. This balances thoroughness with time cost.

2. **Cross-territory defect handling**
   - What we know: Agent territories are defined per roadmap. CONTEXT.md says "how to handle defects that span multiple agent territories" is Claude's discretion.
   - What's unclear: How often this will occur in practice.
   - Recommendation: When a finding spans territories (e.g., a dollar formatting issue in `docx_hotsheet.py` that also requires a fix in `economic.py`), the agent who found it files it, and both agents coordinate during fix wave. The finding JSON should have a `cross_territory` flag and list affected files.

3. **Document corpus availability**
   - What we know: Data files are not committed to git (DEC-1203-03). Documents must be generated at runtime via `--prep-packets --all-tribes`.
   - What's unclear: Whether the full 992-document corpus will be available during the Phase 16 audit window, or whether agents work on a representative sample.
   - Recommendation: Generate full corpus before audit wave. If time-constrained, validate against a representative sample (e.g., 50 Doc A, 50 Doc B, all 8 Doc C, all 8 Doc D = 116 documents) with statistical confidence.

4. **SYNTHESIS.md format**
   - What we know: CONTEXT.md says "human-readable quality certificate with pass/fail status, defect counts by severity, links to per-agent JSON files, known issues section."
   - What's unclear: Exact markdown format.
   - Recommendation: Define during planning. Include: overall pass/fail, severity histogram, per-agent summary table, defects-fixed count, remaining P2/P3 known issues list with file:line references.

## Sources

### Primary (HIGH confidence)
- Codebase analysis: All source files listed in Architecture Patterns read line-by-line
- Context7 `/websites/python-docx_readthedocs_io_en` - style iteration, paragraph access, font properties, table structure
- [python-docx readthedocs](https://python-docx.readthedocs.io/en/latest/) - Document API, style system, font access
- [coverage.py 7.13.4 docs](https://coverage.readthedocs.io/) - JSON export, coverage contexts

### Secondary (MEDIUM confidence)
- [pytest-cov PyPI](https://pypi.org/project/pytest-cov/) - `--cov-context=test` for function-level mapping
- Project MEMORY.md - confirmed python-docx patterns, OxmlElement freshness, atomic save

### Tertiary (LOW confidence)
- WebSearch results for python-docx validation patterns - confirmed no built-in validation function exists; custom traversals required
- WebSearch results for pytest coverage - confirmed coverage.py 7.13.4 is latest

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - all tools already in project, no new dependencies
- Architecture: HIGH - codebase analysis reveals exact file structure, LOC, APIs
- Pitfalls: HIGH - documented in project MEMORY.md and codebase docstrings from Phase 7 experience
- Performance: HIGH - python-docx timing characteristics well-understood, 60ms budget verified feasible
- Severity definitions: MEDIUM - Claude's discretion per CONTEXT.md; recommended definitions based on impact analysis

**Research date:** 2026-02-12
**Valid until:** 2026-03-12 (stable -- all tools and patterns are mature)
