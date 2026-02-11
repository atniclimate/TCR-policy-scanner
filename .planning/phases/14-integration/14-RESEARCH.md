# Phase 14: Integration, Document Generation & Validation - Research

**Researched:** 2026-02-11
**Domain:** Python-based document generation pipeline (python-docx), data integration, batch DOCX production, GitHub Pages deployment
**Confidence:** HIGH (codebase-derived, all findings from reading actual source files)

## Summary

Phase 14 transforms the existing single-document-type per-Tribe packet system into a 4-document-type system (Doc A/B/C/D) covering Tribal internal strategy, Tribal congressional overview, regional internal strategy, and regional congressional overview. The codebase already has a mature, well-structured packet generation pipeline with `PacketOrchestrator`, `DocxEngine`, section renderers, economic impact calculator, and a GitHub Pages deployment workflow. The primary work is: (1) expanding from 1 document type to 4, (2) adding regional document aggregation, (3) integrating hazard data (currently unpopulated), (4) implementing audience-specific content filtering, (5) quality review automation, and (6) production deployment.

The most significant finding is that **all 592 hazard profiles are currently unpopulated** (all show `note: "NRI county data not loaded"` with zero scores). The NRI data directory (`data/nri/`) does not exist on disk. This means Phase 14's hazard integration (INTG-01) requires either running the hazard population pipeline first or treating hazard data as a known gap.

**Primary recommendation:** Build the 4-document-type system by extending the existing `DocxEngine` and section renderers -- do NOT replace them. The architecture is clean and extensible. Add document-type-aware rendering paths rather than building parallel engines.

## Standard Stack

The project stack is already established. Phase 14 uses the same stack, no new libraries needed.

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| python-docx | current | DOCX generation | Already in use, all styles and templates built |
| jinja2 | current | Template rendering (if needed for narrative templates) | Already in requirements.txt |
| pathlib | stdlib | Path management | Centralized in src/paths.py |
| dataclasses | stdlib | Data structures | Used for TribePacketContext, economic summaries |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| rapidfuzz | current | Name matching | Already used by TribalRegistry |
| openpyxl | current | Excel reading (NRI/USFS data) | Already in requirements.txt |
| pytest | current | Testing | 606 tests already in place |

### Not Needed
| Suggestion | Actual Stack | Clarification |
|------------|-------------|---------------|
| docx-js | NOT USED | The PHASE-14-REFERENCE.md mentions docx-js but the project uses python-docx exclusively. The web widget is vanilla JS for search/download only -- it does NOT generate DOCX in the browser. |
| Any new library | python-docx | Everything needed is already installed |

**Installation:** No new packages required. The existing `requirements.txt` covers everything.

## Architecture Patterns

### Current Project Structure (packets/)
```
src/packets/
  __init__.py
  orchestrator.py          # PacketOrchestrator -- coordinates all data assembly
  context.py               # TribePacketContext dataclass -- render-ready data bundle
  docx_engine.py           # DocxEngine -- creates Document, manages styles, saves
  docx_sections.py         # Section renderers (cover, TOC, exec summary, delegation, etc.)
  docx_hotsheet.py         # HotSheetRenderer -- per-program Hot Sheet pages
  docx_styles.py           # StyleManager, COLORS, formatting helpers
  docx_template.py         # TemplateBuilder -- pre-bakes styles into template DOCX
  economic.py              # EconomicImpactCalculator + dataclasses
  hazards.py               # HazardProfileBuilder (ingestion, not rendering)
  awards.py                # Award population/matching
  congress.py              # CongressionalMapper -- loads congressional_cache.json
  registry.py              # TribalRegistry -- loads tribal_registry.json
  ecoregion.py             # EcoregionMapper -- state-to-ecoregion classification
  relevance.py             # ProgramRelevanceFilter -- 8-12 programs per Tribe
  strategic_overview.py    # StrategicOverviewGenerator -- single shared overview doc
  change_tracker.py        # PacketChangeTracker -- diff between generations
  agent_review.py          # AgentReviewOrchestrator -- 3-pass critique cycle
```

### Pattern 1: Document Generation Pipeline
**What:** The existing pipeline follows a clean data-flow pattern:
1. CLI (`--prep-packets`) -> `PacketOrchestrator`
2. Orchestrator resolves Tribe via `TribalRegistry`, classifies ecoregion, gets delegation
3. Loads per-Tribe caches (awards, hazards) from JSON files
4. Builds `TribePacketContext` dataclass with all data
5. Computes economic impact via `EconomicImpactCalculator`
6. Filters relevant programs via `ProgramRelevanceFilter`
7. Creates `DocxEngine`, calls `engine.generate()` with context + computed data
8. `DocxEngine.generate()` calls section renderers in order
9. Atomic save via temp file + `os.replace()`

**Implication for Phase 14:** This pipeline needs to be extended to produce 4 document types per Tribe instead of 1. The `generate()` method needs document-type awareness.

### Pattern 2: Section Renderer Pattern
**What:** Each section of the document is rendered by a standalone function (or method) that takes `(document, context, style_manager)` and renders content directly into the python-docx Document object.

```python
# Example from docx_sections.py
def render_cover_page(document, context, style_manager):
    document.add_paragraph("Title", style="Heading 1")
    document.add_paragraph(context.tribe_name, style="HS Title")
    # ... more content ...
    document.add_page_break()
```

**Implication for Phase 14:** New sections for audience-specific content (strategy vs. factual) can follow this same pattern. The content filtering logic (what goes in Doc A vs Doc B) should be implemented as section-level decisions, not document-level duplication.

### Pattern 3: Cache Loading Pattern
**What:** Per-Tribe data is loaded from `data/{cache_type}/{tribe_id}.json` files via `_load_tribe_cache()` in the orchestrator. Each cache file is a self-contained JSON document.

**Implication for Phase 14:** Regional documents (Doc C/D) will need to aggregate data across multiple Tribes. A new `RegionalContext` dataclass and aggregation step will be needed.

### Pattern 4: Template-Based DOCX Generation
**What:** A pre-built template (`templates/hot_sheet_template.docx`) with all HS-* styles baked in is loaded by `DocxEngine.create_document()`. This saves ~0.2s per document vs. creating styles from scratch.

**Implication for Phase 14:** The 4 new document types will likely need either 4 separate templates or a single flexible template. Given the different headers/footers per document type (from CONTEXT.md), separate templates per type are recommended.

### Recommended Phase 14 Structure
```
src/packets/
  # EXISTING (modify)
  orchestrator.py          # Add doc-type routing, regional generation
  context.py               # Add RegionalContext dataclass
  docx_engine.py           # Add document-type-aware generation
  docx_sections.py         # Add audience-filtered variants

  # NEW
  doc_types.py             # Document type definitions (A/B/C/D) + content rules
  regional.py              # Regional aggregation logic (8 regions)
  narrative.py             # Ecoregion narrative templates + per-Tribe narratives
  quality_review.py        # Automated quality checking (or extend agent_review.py)
  validation.py            # Data coverage validation script (INTG-03)
```

### Anti-Patterns to Avoid
- **Duplicating DocxEngine per document type:** Don't create `DocAEngine`, `DocBEngine`, etc. Use a single engine with document-type configuration.
- **Embedding content rules in renderers:** Keep the audience-classification line (what's internal-only vs. congressional-safe) as a data structure, not scattered `if` statements in renderers.
- **Building regional docs from scratch:** Regional docs should aggregate from the same data caches and economic calculations used for Tribal docs -- don't re-implement data loading.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| DOCX generation | Custom XML builder | python-docx (already in use) | Existing styles, templates, and renderers work well |
| Fuzzy name matching | Custom string matching | rapidfuzz (already in use) | TribalRegistry already handles this |
| Economic calculations | New calculator | EconomicImpactCalculator (already works) | Already uses BEA/BLS/FEMA multipliers correctly |
| Data validation | Ad-hoc scripts | Extend validate_data_integrity.py (14 checks already) | Pydantic schemas already validate all cache types |
| Web index building | Manual JSON construction | scripts/build_web_index.py (already exists) | Just needs doc-type awareness added |
| CI/CD | New workflow | Extend .github/workflows/generate-packets.yml | Already handles batch generation + Pages deployment |

**Key insight:** The codebase is mature (606 tests, ~25K LOC). Phase 14 is about EXTENDING, not REPLACING.

## Current Codebase State (Section-by-Section)

### 1. DocxEngine & PacketOrchestrator

**Entry point:** `python -m src.main --prep-packets --all-tribes` (or `--tribe "Name"`)

**PacketOrchestrator** (`src/packets/orchestrator.py`, 616 lines):
- `run_single_tribe(tribe_name)` -- resolves name, builds context, generates DOCX
- `run_all_tribes()` -- iterates all 592 Tribes, generates DOCX + strategic overview
- `_build_context(tribe)` -- assembles TribePacketContext from all data sources
- `generate_packet_from_context(context, tribe)` -- computes economic impact, filters programs, creates DocxEngine, calls `engine.generate()`
- `generate_strategic_overview()` -- creates the shared overview document (Document 2)
- Supports `--enable-agent-review` flag for 3-pass review cycle
- Memory management: `gc.collect()` every 25 Tribes in batch mode

**DocxEngine** (`src/packets/docx_engine.py`, 306 lines):
- Opens pre-built template or creates blank document
- `generate()` assembles 9 sections in order:
  1. Cover page
  2. Table of contents
  3. Executive summary
  4. Congressional delegation table
  5. Hot Sheets (8-12 per Tribe, one per relevant program)
  6. Hazard profile summary
  7. Structural policy asks
  8. Change tracking (if changes exist)
  9. Appendix (omitted programs)
- Atomic save via `os.replace()`
- Single template: `templates/hot_sheet_template.docx`

**Current document output:** Single per-Tribe DOCX that is a hybrid -- contains both strategic/advocacy content AND factual data. Phase 14 splits this into 4 specialized documents.

**What needs to change:**
- `DocxEngine.generate()` needs a `doc_type` parameter to select which sections to render and how
- Headers/footers must change per document type (from CONTEXT.md)
- Cover page content differs per document type
- Section renderers need audience-aware variants (assertive vs. factual)
- New regional document generation flow needed

### 2. Economic Impact Computation

**File:** `src/packets/economic.py` (383 lines)

**Status: FULLY FUNCTIONAL with real data.** This is NOT placeholder.

**How it works:**
- Groups awards by `program_id`
- Applies BEA RIMS II multiplier range (1.8-2.4x) to each program's total obligation
- Applies BLS employment estimates (8-15 jobs per $1M)
- Applies FEMA BCR (4:1) for mitigation programs (fema_bric, fema_tribal_mitigation, usda_wildfire)
- For Tribes WITHOUT awards in a program, uses benchmark averages (`PROGRAM_BENCHMARK_AVERAGES`)
- Allocates impact proportionally across congressional districts by `overlap_pct`
- Returns `TribeEconomicSummary` dataclass with per-program and per-district breakdowns

**What it uses:** Real award amounts from `data/award_cache/{tribe_id}.json` + published federal multipliers (constants in source).

**INTG-01 requirement:** "Economic impact section auto-computes using real award amounts and hazard scores (no placeholder fallbacks)"
- **Current state:** Economic impact already computes using real award amounts. The "hazard scores" part is the gap -- hazard data is unpopulated.
- **What needs to change:** The economic narrative should incorporate hazard context (e.g., "Given [Tribe]'s high wildfire risk, mitigation investment yields estimated $4 return per $1"). Currently, the hazard data flows separately through `render_hazard_summary()` and `_add_hazard_relevance()` but isn't woven into the economic narrative itself.
- **Benchmark path concern:** For Tribes without awards, the calculator uses `PROGRAM_BENCHMARK_AVERAGES` (hardcoded estimates). INTG-01 says "no placeholder fallbacks" -- this benchmark path may need to be removed or clearly labeled for congressional docs.

### 3. Award Cache Structure

**Location:** `data/award_cache/{tribe_id}.json` (592 files)
**Coverage:** 451 of 592 Tribes have at least one award (76.2%)

**Sample structure:**
```json
{
  "tribe_id": "epa_100000001",
  "tribe_name": "Absentee-Shawnee Tribe of Indians of Oklahoma",
  "fiscal_year_range": {"start": 2022, "end": 2026},
  "awards": [
    {
      "award_id": "55IH4000040",
      "cfda": "14.867",
      "program_id": "hud_ihbg",
      "recipient_name_raw": "HOUSING AUTHORITY OF ...",
      "obligation": 49690590.0,
      "start_date": "2012-01-06",
      "end_date": "2034-09-30",
      "description": "INDIAN HSG BLOCK GR",
      "awarding_agency": "Department of Housing and Urban Development"
    }
  ],
  "total_obligation": 49690590.0,
  "award_count": 1,
  "cfda_summary": {"14.867": {"count": 1, "total": 49690590.0}},
  "yearly_obligations": {"2022": 0.0, ...},
  "trend": "none"
}
```

**Key fields per award:** `award_id`, `cfda`, `program_id`, `recipient_name_raw`, `obligation`, `start_date`, `end_date`, `description`, `awarding_agency`.

**Aggregates:** `total_obligation`, `award_count`, `cfda_summary`, `yearly_obligations`, `trend`.

**Gap:** 141 Tribes (23.8%) have zero awards. These will be "abbreviated data summary" candidates.

### 4. Hazard Cache Structure

**Location:** `data/hazard_profiles/{tribe_id}.json` (592 files)
**Coverage:** ALL 592 files exist but ALL are UNPOPULATED.

**Current state:** Every hazard profile has `"note": "NRI county data not loaded"` with all scores at 0.0. The `data/nri/` directory does not exist on disk.

**Sample structure (unpopulated):**
```json
{
  "tribe_id": "epa_100000001",
  "tribe_name": "...",
  "sources": {
    "fema_nri": {
      "version": "1.20",
      "counties_analyzed": 0,
      "note": "NRI county data not loaded",
      "composite": {
        "risk_score": 0.0,
        "risk_rating": "",
        "eal_total": 0.0,
        "sovi_score": 0.0,
        "sovi_rating": "",
        "resl_score": 0.0,
        "resl_rating": ""
      },
      "top_hazards": [],
      "all_hazards": {
        "AVLN": {"risk_score": 0.0, "risk_rating": "", "eal_total": 0.0, ...},
        // 18 hazard types, all zeros
      }
    },
    "usfs_wildfire": {}
  },
  "generated_at": "2026-02-10T17:35:21..."
}
```

**Expected populated structure** (based on code in `hazards.py`):
- `sources.fema_nri.composite` -- overall risk score, rating, EAL, social vulnerability
- `sources.fema_nri.top_hazards[]` -- ranked by risk_score, each with type, risk_score, risk_rating, eal_total
- `sources.fema_nri.all_hazards.{CODE}` -- per-hazard details (18 hazard types)
- `sources.usfs_wildfire` -- risk_to_homes, wildfire_likelihood (when USFS data loaded)

**CRITICAL FINDING:** The Phase 13 context says "hazard population for 550+ Tribes" is complete, but the actual files on disk show zero population. This is either:
1. Work was done in a different branch/environment not reflected in this workspace
2. The NRI source data needs to be downloaded first (`scripts/download_nri_data.py`)
3. The population needs to be re-run

**Impact on Phase 14:** Without populated hazard data, INTG-01 ("auto-computes using real award amounts and hazard scores") cannot be fully met. The document generation will produce hazard-empty sections.

### 5. Congressional & Registry Cache Structure

**Congressional Cache** (`data/congressional_cache.json`, single file):
- **Coverage:** 501 of 592 Tribes mapped (84.6%)
- **Structure:** `{metadata, members, committees, delegations}`
- `members` -- 538 entries keyed by bioguide_id, with name, state, district, party, chamber, committees[]
- `committees` -- 46 entries
- `delegations` -- per-Tribe: `{tribe_id, districts[], states[], senators[], representatives[]}`
- Each district includes `overlap_pct` (Census AIANNH-to-CD crosswalk)
- All 501 delegations have at least some members
- **Gap:** 91 Tribes without delegation data (15.4%)

**Tribal Registry** (`data/tribal_registry.json`, single file):
- **Coverage:** 592 Tribes (complete)
- **Structure:** `{metadata, tribes[]}`
- Each Tribe: `{tribe_id, bia_code, name, states[], alternate_names[], epa_region, bia_recognized}`
- Metadata: source is EPA Tribes Names Service API, 235 BIA codes TBD

### 6. Program Inventory

**File:** `data/program_inventory.json`
**Count:** 16 programs

**Programs by priority:**
- **Critical (3):** bia_tcr, fema_bric, irs_elective_pay
- **High (9):** epa_stag, epa_gap, fema_tribal_mitigation, dot_protect, usda_wildfire, doe_indian_energy, hud_ihbg, noaa_tribal, bia_tcr_awards, epa_tribal_air
- **Medium (2):** fhwa_ttp_safety, usbr_watersmart, usbr_tap

**CI Status distribution:**
- FLAGGED: fema_bric (CI: 0.12)
- AT_RISK: irs_elective_pay (0.55), fema_tribal_mitigation (0.65)
- UNCERTAIN: doe_indian_energy (0.55), noaa_tribal (0.50), usbr_watersmart (0.60)
- STABLE_BUT_VULNERABLE: usda_wildfire (0.78)
- STABLE: bia_tcr (0.88), epa_stag (0.90), epa_gap (0.80), hud_ihbg (0.85), fhwa_ttp_safety (0.85), usbr_tap (0.75), bia_tcr_awards (0.85), epa_tribal_air (0.82)
- SECURE: dot_protect (0.93)

**Each program has:** id, name, agency, federal_home, priority, keywords, search_queries, advocacy_lever, description, access_type, funding_type, cfda, confidence_index, ci_status, ci_determination, tightened_language (some), proposed_fix (some), specialist_focus (some).

### 7. Ecoregion Configuration

**File:** `data/ecoregion_config.json`
**Current regions:** 7 (NCA5-derived)
- alaska, pacific_northwest, southwest, mountain_west, great_plains_south, southeast, northeast_midwest

**CONTEXT.md defines 8 regions:**
- Pacific NW / Columbia River Basin (pnw)
- Alaska (alaska)
- Great Plains / Northern Plains (plains)
- Southwest / Great Basin (southwest)
- Great Lakes / Midwest (greatlakes)
- Southeast / Gulf Coast / Five Tribes (southeast)
- Northeast / Mid-Atlantic / South and Eastern Tribes (northeast)
- Cross-Cutting -- all regions (crosscutting)

**Gap:** The ecoregion_config.json has 7 regions with different naming/grouping than the 8 regions in CONTEXT.md. Phase 14 needs to either:
1. Update ecoregion_config.json to match the 8-region scheme, OR
2. Create a separate regional grouping config for Doc C/D that maps to the 8 CONTEXT.md regions

The "Cross-Cutting" region is new and not in the current config at all. It's described as getting standalone Doc C/D plus appearing as appendices in every other region.

### 8. GitHub Pages / Deployment

**Current state:** Functional but single-document-type.

**Docs/web structure:**
```
docs/web/
  index.html          # Search widget (Awesomplete autocomplete)
  css/                # awesomplete.css, style.css
  js/                 # app.js, awesomplete.min.js
  data/               # tribes.json (search index, built by script)
  tribes/             # DOCX files served for download
```

**GitHub Actions workflow** (`.github/workflows/generate-packets.yml`):
1. Weekly (Sunday 8AM Pacific) or manual trigger
2. Runs `python -m src.main --prep-packets --all-tribes`
3. Runs `python scripts/build_web_index.py`
4. Copies packets to `docs/web/tribes/`
5. Commits and pushes

**GitHub Pages:** Served from `docs/web/` directory. URL structure: `https://atniclimate.github.io/TCR-policy-scanner/`

**SquareSpace placeholder:** `docs/web/index.html` line 45 has `https://yourusername.github.io/tcr-policy-scanner/` in the iframe embed comment. The README already has `https://atniclimate.github.io/TCR-policy-scanner/` as the production URL.

**What needs to change for Phase 14:**
- URL paths need `/internal/` and `/congressional/` separation (per CONTEXT.md)
- Web widget needs document-type selection (currently just a single "Download Report" button)
- `build_web_index.py` needs to track 4 document types per Tribe + regional docs
- `generate-packets.yml` workflow needs to handle new output structure
- Strategic overview may be replaced or supplemented by regional docs
- INTG-06: Replace `yourusername` placeholder with `atniclimate` in the iframe comment

### 9. Existing Tests

**Location:** `tests/` (22 test files)
**Count:** 606 tests
**Framework:** pytest with tmp_path fixtures

**Relevant test files:**
- `test_doc_assembly.py` -- Full DocxEngine.generate() with all 8 sections
- `test_docx_hotsheet.py` -- HotSheetRenderer unit tests
- `test_docx_integration.py` -- Integration tests for DOCX generation
- `test_docx_styles.py` -- StyleManager and formatting
- `test_docx_template.py` -- Template building
- `test_economic.py` -- EconomicImpactCalculator
- `test_hazard_aggregation.py` -- Hazard profile building
- `test_packets.py` -- PacketOrchestrator
- `test_batch_generation.py` -- Batch run_all_tribes
- `test_strategic_overview.py` -- Strategic overview generation
- `test_web_index.py` -- build_web_index.py

**Test pattern:** Tests use mock data builders (e.g., `_mock_programs()`, `_mock_context()`), tmp_path for file system isolation, and verify DOCX content by reading back paragraphs/tables from the generated document.

**Example pattern from test_doc_assembly.py:**
```python
def _mock_programs():
    return [{"id": "bia_tcr", "name": "BIA TCR", ...}, ...]

def test_full_document_assembly(tmp_path):
    programs = _mock_programs()
    config = {"packets": {"output_dir": str(tmp_path)}}
    engine = DocxEngine(config, {p["id"]: p for p in programs}, template_path=False)
    # ... build context, compute economic impact ...
    path = engine.generate(context, relevant_programs, economic_summary, ...)
    doc = DocxDocument(str(path))
    paragraphs = [p.text for p in doc.paragraphs]
    # Assert sections exist in order
    assert "Executive Summary" in paragraphs
    assert "Congressional Delegation" in paragraphs
```

### 10. python-docx vs. docx-js

**Clarification:** The project uses **python-docx** exclusively. There is no JavaScript DOCX generation anywhere. The PHASE-14-REFERENCE.md mentions docx-js as a potential approach, but this was never implemented.

The web widget (`docs/web/js/app.js`) is a pure search/download UI using vanilla JS + Awesomplete for autocomplete. It fetches `tribes.json` for the search index and links to pre-generated `.docx` files. No client-side document generation.

**Implication:** All 4 document types will be generated server-side (Python) and served as static DOCX files via GitHub Pages.

## Common Pitfalls

### Pitfall 1: Content Leakage Between Audience Tiers
**What goes wrong:** Strategic/advocacy content from Doc A/C leaks into congressional-safe Doc B/D.
**Why it happens:** When content filtering is scattered across renderers rather than centralized, edge cases slip through.
**How to avoid:** Define the classification line as a data structure (e.g., a dict mapping content types to audience permissions). Each renderer checks the classification before including content.
**Warning signs:** "advocacy_lever" or "tightened_language" appearing in Doc B/D text.

### Pitfall 2: Hazard Data Absence Causing Empty Sections
**What goes wrong:** Documents generate with "Hazard profile data pending" messages everywhere.
**Why it happens:** All hazard profiles are currently unpopulated (0/592).
**How to avoid:** Either populate hazard data first, or implement graceful degradation that generates meaningful content even without hazard scores (e.g., ecoregion-based hazard context from the configuration).
**Warning signs:** All test Tribes showing identical hazard sections.

### Pitfall 3: Regional Document Data Aggregation Performance
**What goes wrong:** Generating 8 regional docs requires iterating all Tribes multiple times, making batch generation slow.
**Why it happens:** Naive approach loads each Tribe's caches independently for each regional doc.
**How to avoid:** Pre-aggregate regional data in a single pass before generating regional documents. Store aggregated data in memory.
**Warning signs:** Regional doc generation taking longer than all per-Tribe docs combined.

### Pitfall 4: Air Gap Violations in Generated Content
**What goes wrong:** Organizational names (ATNI, NCAI, etc.) appear in document metadata, headers, or body text.
**Why it happens:** Current code has "TCR Policy Scanner" in headers/footers. The CONTEXT.md says no organizational attribution.
**How to avoid:** Current headers say "TCR Policy Scanner | Tribal Advocacy Packet" and footer says "CONFIDENTIAL | Generated by TCR Policy Scanner". These need to be replaced with the doc-type-specific headers from CONTEXT.md.
**Warning signs:** `grep -ri "TCR Policy Scanner"` in generated DOCX content.

### Pitfall 5: Template Bloat from 4 Document Types
**What goes wrong:** Creating 4 separate DocxEngine variants with duplicated code.
**Why it happens:** Easier to copy-paste than to design a good abstraction.
**How to avoid:** Use a document type configuration object that defines headers, footers, included sections, and content filters. Pass it to the existing engine.
**Warning signs:** Multiple `DocxEngine` subclasses or separate `generate_doc_a()`, `generate_doc_b()` methods.

## Code Examples

### Current: How a Packet is Generated (from orchestrator.py)
```python
# In PacketOrchestrator.generate_packet_from_context():
economic_summary = self.economic_calculator.compute(
    tribe_id=context.tribe_id,
    tribe_name=context.tribe_name,
    awards=context.awards,
    districts=context.districts,
    programs=self.programs,
)
context.economic_impact = asdict(economic_summary)

relevant = self.relevance_filter.filter_for_tribe(
    hazard_profile=context.hazard_profile,
    ecoregions=context.ecoregions,
    ecoregion_mapper=self.ecoregion,
)

engine = DocxEngine(self.config, self.programs)
path = engine.generate(
    context=context,
    relevant_programs=relevant,
    economic_summary=economic_summary,
    structural_asks=structural_asks,
    omitted_programs=omitted,
    changes=changes,
    previous_date=previous_date,
)
```

### Recommended: Document Type Configuration Pattern
```python
# New: doc_types.py
from dataclasses import dataclass

@dataclass
class DocumentTypeConfig:
    """Configuration for a specific document type."""
    doc_type: str  # "A", "B", "C", "D"
    audience: str  # "internal", "congressional"
    scope: str  # "tribal", "regional"
    header_template: str
    footer_template: str
    confidential: bool
    include_strategy: bool  # advocacy language, leverage, approach
    include_advocacy_lever: bool
    include_member_approach: bool
    include_structural_asks_framing: str  # "strategic" or "policy_recommendation"
    narrative_voice: str  # "assertive" or "objective"

DOC_A = DocumentTypeConfig(
    doc_type="A",
    audience="internal",
    scope="tribal",
    header_template="{tribe_name} | Internal Strategy | CONFIDENTIAL",
    footer_template="Confidential: For Internal Use Only",
    confidential=True,
    include_strategy=True,
    include_advocacy_lever=True,
    include_member_approach=True,
    include_structural_asks_framing="strategic",
    narrative_voice="assertive",
)

DOC_B = DocumentTypeConfig(
    doc_type="B",
    audience="congressional",
    scope="tribal",
    header_template="{tribe_name} | FY26 Climate Resilience Program Priorities",
    footer_template="For Congressional Office Use",
    confidential=False,
    include_strategy=False,
    include_advocacy_lever=False,
    include_member_approach=False,
    include_structural_asks_framing="policy_recommendation",
    narrative_voice="objective",
)
# Similarly for DOC_C, DOC_D
```

### Current: How Tests Verify DOCX Content
```python
# From test_doc_assembly.py
def test_full_document_assembly(tmp_path):
    config = {"packets": {"output_dir": str(tmp_path)}}
    engine = DocxEngine(config, programs_dict, template_path=False)
    path = engine.generate(context, relevant_programs, economic_summary, ...)

    doc = DocxDocument(str(path))
    paragraphs = [p.text for p in doc.paragraphs]

    # Verify section ordering
    assert "Executive Summary" in paragraphs
    assert "Congressional Delegation" in paragraphs
    assert paragraphs.index("Executive Summary") < paragraphs.index("Congressional Delegation")
```

## Data Coverage Summary

| Cache Type | Files | Populated | Coverage | Gap |
|-----------|-------|-----------|----------|-----|
| Tribal Registry | 1 file | 592 Tribes | 100% | 235 BIA codes TBD |
| Award Cache | 592 files | 451 with awards | 76.2% | 141 Tribes no awards |
| Hazard Profiles | 592 files | 0 populated | 0% | NRI data not loaded |
| Congressional Cache | 1 file | 501 Tribes | 84.6% | 91 Tribes unmapped |

**INTG-02 goal:** "Complete packets for 400+" -- Based on award coverage (451) and congressional coverage (501), roughly 400+ Tribes have BOTH awards AND delegation data. Hazard data would increase completeness further if populated.

## Risks & Unknowns

### Risk 1: Hazard Data Not Populated (HIGH)
**What:** All 592 hazard profiles show zero data. The NRI data directory doesn't exist.
**Impact:** INTG-01 cannot be fully met ("auto-computes using real award amounts and hazard scores"). Documents will have empty hazard sections.
**Mitigation options:**
1. Run `scripts/download_nri_data.py` + `scripts/populate_hazards.py` before Phase 14 execution
2. Use ecoregion-based hazard context as fallback (less specific but not empty)
3. Accept hazard gaps and document them in VERIFICATION.md (INTG-04)

### Risk 2: Ecoregion Mismatch (MEDIUM)
**What:** Current 7 ecoregions don't match the 8 defined in CONTEXT.md.
**Impact:** Regional docs (C/D) may not group Tribes correctly.
**Mitigation:** Update ecoregion_config.json to the 8-region scheme before generating regional docs. Add "crosscutting" as a virtual region.

### Risk 3: Batch Generation Time (LOW)
**What:** Generating ~1,200 documents (4 types x ~300 Tribes + 8 regional x 2 types) may take significant time.
**Impact:** CI workflow has 30-minute timeout.
**Mitigation:** Current single-type batch takes roughly 1-2 minutes for 592 Tribes. 4x volume should still be under 10 minutes. gc.collect() every 25 is already in place.

### Risk 4: Content Classification Correctness (HIGH)
**What:** Ensuring strategic content never appears in congressional documents.
**Impact:** Air gap violation could undermine document credibility.
**Mitigation:** Build automated quality review that checks every Doc B/D for prohibited content patterns (from CONTEXT.md classification line). Include in INTG-03 validation.

### Risk 5: Air Gap Compliance (MEDIUM)
**What:** Current code has "TCR Policy Scanner" branding in headers/footers and "Generated by TCR Policy Scanner" text.
**Impact:** Violates the "no organizational attribution" rule.
**Mitigation:** Replace all branding with doc-type-specific headers from CONTEXT.md. Scrub document metadata (Author, Creator fields in DOCX XML).

## Open Questions

1. **Hazard Data Timeline**
   - What we know: Files exist but are empty. Phase 13 context says population was done.
   - What's unclear: Whether hazard population was completed in a different environment or needs to be re-run.
   - Recommendation: Verify by running `scripts/populate_hazards.py` or checking if NRI source data needs downloading first.

2. **Ecoregion Remapping**
   - What we know: Current 7 regions vs. CONTEXT.md's 8 regions have different groupings.
   - What's unclear: Whether the existing ecoregion assignments in the pipeline need to change or just the regional doc groupings.
   - Recommendation: Create a separate `regional_config.json` for Doc C/D that maps the 8 CONTEXT.md regions, leaving the existing 7-ecoregion system for per-Tribe relevance filtering.

3. **Prototype Text Location**
   - What we know: CONTEXT.md mentions "ecoregion narrative templates from prototype" and "structural asks scrubbed and reframed."
   - What's unclear: Where the prototype text lives. It's not in the current codebase.
   - Recommendation: These narrative templates will need to be authored as part of Phase 14, not found in the codebase.

4. **Document Sizing**
   - What we know: Current packets are ~20-30 pages. CONTEXT.md says "any section readable in under 2 minutes."
   - What's unclear: Target page count per document type.
   - Recommendation: Doc B (congressional) should be 3-5 pages (briefing memo length). Doc A (internal) can be longer (10-15 pages). Regional docs (C/D) will vary by region size.

## Planning Implications

### Wave 1: Data Integration & Economic Impact (14-01)
**Starting point:** EconomicImpactCalculator already works with real award data. Hazard integration is blocked by empty profiles.
**Key work:**
- Verify/populate hazard data (or accept gap)
- Wire hazard context into economic narratives
- Remove or clearly flag benchmark fallbacks for congressional docs
- Update ecoregion config to 8-region scheme

### Wave 2: Document Generation (14-02a through 14-02d)
**Starting point:** DocxEngine produces single doc type with all content. Section renderers are modular.
**Key work:**
- Create `DocumentTypeConfig` system
- Build audience-filtered section renderer variants
- Create 4 template DOCX files with correct headers/footers
- Implement per-Tribe 4-doc generation flow
- Build regional aggregation and Doc C/D generation
- Author ecoregion narrative templates
- Implement tiered generation (full vs. abbreviated)

### Wave 3: Quality Review (14-03)
**Starting point:** `agent_review.py` has the review framework (5 agents, priority hierarchy, quality gate).
**Key work:**
- Implement automated content classification checking
- Build audience leakage detection
- Implement air gap scrubbing verification
- Build spot-check report generator (35 Tribes)
- Add auto-regeneration for failing documents

### Wave 4: Data Validation & Documentation (14-04)
**Starting point:** `validate_data_integrity.py` has 14 checks with Pydantic schemas.
**Key work:**
- Build coverage reporting script (awards, hazards, congressional, registry)
- Write VERIFICATION.md documenting methodology and gaps
- Add INTG-03 coverage percentage calculations

### Wave 5: Deployment (14-05)
**Starting point:** GitHub Pages workflow exists, web widget functional.
**Key work:**
- Add `/internal/` and `/congressional/` URL paths
- Update web widget for 4-document-type selection
- Update `build_web_index.py` for multi-doc-type tracking
- Replace SquareSpace placeholder URL
- Update `generate-packets.yml` for new output structure

## Sources

### Primary (HIGH confidence)
All findings derived from direct reading of source files in `F:\tcr-policy-scanner\`:
- `src/packets/orchestrator.py` -- Pipeline flow and data integration
- `src/packets/docx_engine.py` -- Document assembly
- `src/packets/docx_sections.py` -- Section renderers
- `src/packets/docx_hotsheet.py` -- Hot Sheet renderer
- `src/packets/economic.py` -- Economic impact calculator
- `src/packets/context.py` -- TribePacketContext dataclass
- `src/packets/hazards.py` -- Hazard profile builder
- `src/packets/congress.py` -- Congressional mapper
- `src/packets/ecoregion.py` -- Ecoregion classifier
- `src/packets/relevance.py` -- Program relevance filter
- `src/packets/strategic_overview.py` -- Strategic overview generator
- `src/packets/agent_review.py` -- Agent review framework
- `src/main.py` -- CLI entry point
- `data/award_cache/*.json` -- 592 award cache files examined
- `data/hazard_profiles/*.json` -- 592 hazard profile files examined
- `data/congressional_cache.json` -- Congressional delegation data
- `data/tribal_registry.json` -- Tribal registry
- `data/program_inventory.json` -- 16-program inventory
- `data/ecoregion_config.json` -- 7-ecoregion configuration
- `validate_data_integrity.py` -- Existing validation framework
- `.github/workflows/generate-packets.yml` -- CI/CD workflow
- `docs/web/` -- GitHub Pages widget
- `scripts/build_web_index.py` -- Web index builder
- `tests/` -- 606 tests across 22 files

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- directly verified from source code and requirements.txt
- Architecture: HIGH -- all patterns derived from reading actual implementation
- Data coverage: HIGH -- counted actual files and parsed JSON structures
- Pitfalls: HIGH -- identified from codebase gaps and CONTEXT.md requirements
- Hazard data gap: HIGH -- verified by examining all 592 hazard profile files

**Research date:** 2026-02-11
**Valid until:** Indefinite (codebase-based findings don't expire, but data coverage will change as pipelines run)
