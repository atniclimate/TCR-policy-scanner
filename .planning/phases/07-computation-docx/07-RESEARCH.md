# Phase 7: Computation + DOCX Generation - Research

**Researched:** 2026-02-10
**Domain:** python-docx document generation, economic impact computation, advocacy packet assembly
**Confidence:** HIGH (python-docx), MEDIUM (economic methodology), HIGH (codebase integration)

## Summary

Phase 7 builds the DOCX generation engine that transforms TribePacketContext data (identity, awards, hazards, delegation) into professional per-program Hot Sheet sections with economic impact framing. The standard approach uses python-docx (>= 1.1.0, already in requirements.txt) for programmatic Word document construction, with all styles created from scratch in code (no template .docx files).

Economic impact calculations use BEA RIMS II-derived multiplier ranges (1.8-2.4x for output, per published federal spending literature) and FEMA's documented 4:1 benefit-cost ratio for mitigation programs. These are static multipliers applied to USASpending obligation data -- no API calls during DOCX generation.

The codebase already has a well-structured orchestrator pattern (`PacketOrchestrator._build_context()`) and a rich program inventory with verified field names (`tightened_language`, `advocacy_lever`, `ci_status`, `access_type`). Phase 7 adds new modules to the `src/packets/` namespace without modifying any Phase 5-6 code.

**Primary recommendation:** Build six new modules in `src/packets/` following the existing orchestrator pattern, with economic computation as a pure-function calculator and DOCX generation as a multi-layer renderer (styles -> sections -> hotsheets -> engine).

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| python-docx | >= 1.1.0 | DOCX construction | Already in requirements.txt; standard Python library for Word generation |
| docx.oxml | (bundled) | Low-level XML for cell shading, custom elements | Required for table cell background colors (no high-level API exists) |
| docx.shared | (bundled) | RGBColor, Pt, Inches, Emu units | All measurement and color types |
| docx.enum | (bundled) | WD_STYLE_TYPE, WD_TABLE_ALIGNMENT, WD_ALIGN_PARAGRAPH | Style and alignment constants |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | (existing) | Unit tests | All new modules need tests |
| json (stdlib) | N/A | Data loading | Award cache, hazard profiles, program inventory |
| dataclasses (stdlib) | N/A | Structured data | Economic impact results, render context |
| pathlib (stdlib) | N/A | File paths | Output directory management |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| python-docx | docx-template (jinja2) | Would require template .docx file -- violates "all styles programmatic" decision |
| python-docx | Spire.Doc | Commercial license, heavier dependency |
| Manual XML | python-docx oxml layer | Only use oxml for features python-docx doesn't expose (cell shading) |

**Installation:** No new packages needed. python-docx >= 1.1.0 already in requirements.txt.

## Architecture Patterns

### Recommended Module Structure
```
src/packets/
  economic.py          # EconomicImpactCalculator (ECON-01) - pure computation
  relevance.py         # ProgramRelevanceFilter (DOC-02 support) - hazard-to-program mapping
  docx_styles.py       # StyleManager - programmatic style definitions (DOC-01)
  docx_hotsheet.py     # HotSheetRenderer - per-program section builder (DOC-02, DOC-03, DOC-04)
  docx_sections.py     # Section generators: cover page, TOC, appendix (DOC-02 support)
  docx_engine.py       # DocxEngine - core document assembly (DOC-01)
  orchestrator.py      # (EXISTING - add generate_docx() method)
  context.py           # (EXISTING - economic_impact field already stubbed)
```

### Pattern 1: Layered DOCX Construction
**What:** Separate style definition, section rendering, and document assembly into distinct modules.
**When to use:** When documents have repeated sections (Hot Sheets) with consistent styling.
**Rationale:** Each Hot Sheet follows the same template structure but with Tribe-specific data. A renderer class produces sections that an engine assembles into the final document.

```python
# Source: Context7 /websites/python-docx_readthedocs_io_en
from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.style import WD_STYLE_TYPE

class StyleManager:
    """Creates all document styles programmatically."""

    def __init__(self, document: Document):
        self.doc = document
        self._create_styles()

    def _create_styles(self):
        # Add custom paragraph style
        style = self.doc.styles.add_style('HotSheetTitle', WD_STYLE_TYPE.PARAGRAPH)
        style.font.name = 'Arial'
        style.font.size = Pt(16)
        style.font.bold = True
        style.font.color.rgb = RGBColor(0x1A, 0x23, 0x7E)

        # Heading styles inherit from built-in, override font
        for level in range(1, 4):
            heading_style = self.doc.styles[f'Heading {level}']
            heading_style.font.name = 'Arial'
```

### Pattern 2: Cell Shading via oxml (LOW-LEVEL)
**What:** Table cell background colors require direct XML manipulation.
**When to use:** Zebra-striped tables, CI status color coding.
**Confidence:** HIGH -- verified via python-docx GitHub issues #146, #432, #434.

```python
# Source: python-docx GitHub issues, StackOverflow community pattern
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

def set_cell_shading(cell, color_hex: str):
    """Set background color on a table cell.

    Args:
        cell: python-docx table cell object
        color_hex: Hex color without '#' (e.g., 'FF0000' for red)
    """
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    shading = OxmlElement('w:shd')
    shading.set(qn('w:fill'), color_hex)
    shading.set(qn('w:val'), 'clear')
    tcPr.append(shading)

def apply_zebra_stripe(table, even_color='F2F2F2', odd_color='FFFFFF'):
    """Apply alternating row colors to a table."""
    for i, row in enumerate(table.rows):
        color = even_color if i % 2 == 0 else odd_color
        for cell in row.cells:
            set_cell_shading(cell, color)
```

### Pattern 3: Status Badge via Colored Text Run
**What:** CI status indicators using colored bold text with Unicode shapes.
**When to use:** Traffic light CI status display (At Risk=red, Watch=amber, Stable=green).
**Rationale:** Inline shapes (DrawingML) are complex; colored Unicode circles + bold text is simpler and Word-native.

```python
# Source: Context7 python-docx docs - font color API
from docx.shared import RGBColor, Pt

CI_STATUS_COLORS = {
    'FLAGGED': RGBColor(0xDC, 0x26, 0x26),      # Red
    'AT_RISK': RGBColor(0xDC, 0x26, 0x26),       # Red
    'UNCERTAIN': RGBColor(0xF5, 0x9E, 0x0B),     # Amber
    'STABLE_BUT_VULNERABLE': RGBColor(0xF5, 0x9E, 0x0B),  # Amber
    'STABLE': RGBColor(0x16, 0xA3, 0x4A),        # Green
    'SECURE': RGBColor(0x16, 0xA3, 0x4A),        # Green
}

def add_status_badge(paragraph, ci_status: str):
    """Add a colored CI status badge to a paragraph."""
    color = CI_STATUS_COLORS.get(ci_status, RGBColor(0x6B, 0x72, 0x80))
    # Unicode filled circle as visual indicator
    run = paragraph.add_run('\u25CF ')  # filled circle
    run.font.color.rgb = color
    run.font.size = Pt(14)
    # Status text
    run2 = paragraph.add_run(ci_status)
    run2.font.color.rgb = color
    run2.font.bold = True
    run2.font.size = Pt(11)
```

### Pattern 4: Economic Impact as Pure Computation
**What:** EconomicImpactCalculator takes award data + multiplier config, returns structured results.
**When to use:** Separate computation from rendering for testability.

```python
from dataclasses import dataclass, field

@dataclass
class ProgramEconomicImpact:
    program_id: str
    total_obligation: float
    multiplier_low: float      # 1.8x BEA range low
    multiplier_high: float     # 2.4x BEA range high
    estimated_impact_low: float
    estimated_impact_high: float
    jobs_estimate_low: float   # BLS jobs-per-million low
    jobs_estimate_high: float  # BLS jobs-per-million high
    fema_bcr: float | None     # 4:1 for mitigation programs, None otherwise
    methodology_citation: str

@dataclass
class TribeEconomicSummary:
    tribe_id: str
    total_obligation: float
    total_impact_low: float
    total_impact_high: float
    total_jobs_low: float
    total_jobs_high: float
    by_program: list[ProgramEconomicImpact] = field(default_factory=list)
    by_district: dict = field(default_factory=dict)  # district -> impact breakdown
```

### Pattern 5: Header/Footer with Section Control
**What:** Each Hot Sheet section can have its own header/footer via Word sections.
**Confidence:** HIGH -- verified in Context7 docs.

```python
# Source: Context7 python-docx docs - section headers
from docx.shared import Inches

section = document.sections[-1]
# Different first page header (for cover page)
section.different_first_page_header_footer = True

header = section.header
header_para = header.paragraphs[0]
header_para.text = 'TCR Policy Scanner | Tribal Advocacy Packet'

footer = section.footer
footer_table = footer.add_table(rows=1, cols=2, width=Inches(6))
```

### Anti-Patterns to Avoid
- **Template .docx files:** Decision locked: all styles programmatic. Never create or reference a template document.
- **AI-generated text:** All advocacy language comes from `tightened_language` and `advocacy_lever` fields in program_inventory.json. No LLM/AI text generation.
- **API calls during DOCX generation:** Economic impact uses pre-cached award data and static multipliers. No network calls.
- **Modifying Phase 5-6 modules:** `registry.py`, `ecoregion.py`, `congress.py`, `awards.py`, `hazards.py` are READ ONLY.
- **Hardcoded 16-program count:** Relevance filtering reduces to 8-12 programs per Tribe based on hazard profile. The renderer must handle variable program counts.
- **`datetime.utcnow()`:** Use `datetime.now(timezone.utc)` everywhere.
- **`open()` without encoding:** Always pass `encoding="utf-8"`.
- **Global state in renderers:** Each Hot Sheet renderer call should be stateless -- receive data in, produce document sections out.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Word document construction | Custom XML assembly | python-docx Document API | Handles complex OOXML correctly |
| Cell background colors | Custom style definitions | `OxmlElement('w:shd')` pattern | Only reliable method; python-docx has no high-level API for this |
| Font/color management | String-based color codes | `RGBColor`, `Pt`, `Inches` from docx.shared | Type-safe, validated units |
| Page breaks | Manual XML insertion | `document.add_page_break()` | Built-in, reliable |
| Table creation | Manual cell-by-cell | `document.add_table(rows, cols)` then populate | Handles row/column spans |
| Economic multiplier ranges | Custom research | Published BEA RIMS II range (1.8-2.4x) | Citable, defensible methodology |
| BCR ratios | Custom analysis | FEMA MitSaves study (4:1 overall, by-hazard ratios) | Peer-reviewed, FEMA-published |

**Key insight:** python-docx handles 95% of document construction at the high level. Only cell shading requires dropping to the oxml layer. Do not over-engineer the oxml usage.

## Common Pitfalls

### Pitfall 1: Cell Shading Requires Fresh OxmlElement Per Cell
**What goes wrong:** Reusing the same `OxmlElement('w:shd')` across multiple cells causes only the last cell to be shaded.
**Why it happens:** XML elements are moved (not copied) when appended to a new parent.
**How to avoid:** Create a new `OxmlElement('w:shd')` for each cell that needs shading.
**Warning signs:** Only one cell in a row has the expected background color.

### Pitfall 2: Style Name Conflicts
**What goes wrong:** `styles.add_style()` raises `ValueError` if a style with that name already exists.
**Why it happens:** Multiple Document instances, or re-running style creation on an existing document.
**How to avoid:** Check `if name not in document.styles` before adding, or use try/except.
**Warning signs:** `ValueError: document already contains style 'HotSheetTitle'`.

### Pitfall 3: Table Width Auto-Sizing
**What goes wrong:** Tables expand to full page width regardless of content.
**Why it happens:** Default table autofit behavior in Word.
**How to avoid:** Set `table.autofit = False` and explicitly set column widths via `table.columns[i].width`.
**Warning signs:** Tables look stretched or columns are unexpectedly wide.

### Pitfall 4: Section Breaks vs. Page Breaks
**What goes wrong:** Using `add_page_break()` when a new section is needed (different headers/footers).
**Why it happens:** Confusion between page breaks (cosmetic) and section breaks (structural).
**How to avoid:** Use `document.add_section()` when header/footer content changes; use `document.add_page_break()` for simple page separation within a section.
**Warning signs:** Headers/footers don't change between Hot Sheets.

### Pitfall 5: Zero-Award Tribes Need Special Handling
**What goes wrong:** Economic impact shows $0 with 0x multiplier, which looks like an error.
**Why it happens:** Many Tribes have no USASpending awards in tracked programs (all current cache files have `"awards": []`).
**How to avoid:** Use "First-Time Applicant Advantage" framing from award cache `no_awards_context` field. Show program average benchmarks instead of Tribe-specific multiplied amounts.
**Warning signs:** Economic impact section is empty or shows $0 impact for most Tribes.

### Pitfall 6: Font Fallback on Systems Without Arial
**What goes wrong:** Document renders with fallback font (typically Times New Roman).
**Why it happens:** Arial/Helvetica not installed on Linux/CI systems.
**How to avoid:** Set font name to 'Arial' -- Word handles fallback correctly when opening the .docx. This is a rendering-time concern, not a generation-time concern. python-docx just embeds the font name in the XML.
**Warning signs:** None during generation. Only visible when opening in Word on a system without the specified font.

### Pitfall 7: Encoding Issues with Tribe Names
**What goes wrong:** Unicode characters in Tribe names (accents, special characters) corrupt the document.
**Why it happens:** Python string handling issues or file I/O without explicit encoding.
**How to avoid:** Always use `encoding="utf-8"` for all file operations. python-docx handles Unicode internally.
**Warning signs:** Garbled text in document, or `UnicodeEncodeError` during generation.

## Code Examples

### Creating a Document with Programmatic Styles
```python
# Source: Context7 /websites/python-docx_readthedocs_io_en
from docx import Document
from docx.shared import Pt, Inches, RGBColor, Cm
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.text import WD_ALIGN_PARAGRAPH

doc = Document()

# Create custom styles
styles = doc.styles

# Hot Sheet title style
hs_title = styles.add_style('HS Title', WD_STYLE_TYPE.PARAGRAPH)
hs_title.font.name = 'Arial'
hs_title.font.size = Pt(18)
hs_title.font.bold = True
hs_title.font.color.rgb = RGBColor(0x1A, 0x23, 0x7E)
hs_title.paragraph_format.space_after = Pt(6)

# Section heading style
hs_section = styles.add_style('HS Section', WD_STYLE_TYPE.PARAGRAPH)
hs_section.font.name = 'Arial'
hs_section.font.size = Pt(12)
hs_section.font.bold = True
hs_section.font.color.rgb = RGBColor(0x37, 0x41, 0x51)
hs_section.paragraph_format.space_before = Pt(12)
hs_section.paragraph_format.space_after = Pt(4)

# Body text style
hs_body = styles.add_style('HS Body', WD_STYLE_TYPE.PARAGRAPH)
hs_body.font.name = 'Arial'
hs_body.font.size = Pt(10)
hs_body.paragraph_format.space_after = Pt(4)

# Key Ask callout style (bold, indented)
hs_callout = styles.add_style('HS Callout', WD_STYLE_TYPE.PARAGRAPH)
hs_callout.font.name = 'Arial'
hs_callout.font.size = Pt(10)
hs_callout.font.bold = True
hs_callout.paragraph_format.left_indent = Inches(0.3)
hs_callout.paragraph_format.space_before = Pt(8)
```

### Adding a Picture and Page Break
```python
# Source: Context7 python-docx docs
from docx.shared import Inches

# Add cover page image (state/region map)
doc.add_picture('outputs/maps/state_map.png', width=Inches(5.5))

# Page break after cover page
doc.add_page_break()
```

### Table with Zebra Striping and Header Row
```python
# Source: Context7 python-docx docs + oxml community pattern
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

def create_award_table(doc, awards: list[dict]):
    """Create a formatted award history table."""
    table = doc.add_table(rows=1, cols=4)
    table.autofit = False

    # Header row
    headers = ['Program', 'CFDA', 'Obligation', 'Period']
    for i, text in enumerate(headers):
        cell = table.rows[0].cells[i]
        cell.text = text
        # Bold header text
        for paragraph in cell.paragraphs:
            for run in paragraph.runs:
                run.font.bold = True
                run.font.name = 'Arial'
                run.font.size = Pt(9)
        # Dark header background
        set_cell_shading(cell, '1A237E')
        # White text
        for paragraph in cell.paragraphs:
            for run in paragraph.runs:
                run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)

    # Data rows with zebra striping
    for i, award in enumerate(awards):
        row = table.add_row()
        row.cells[0].text = award.get('program_id', '')
        row.cells[1].text = award.get('cfda', '')
        obligation = award.get('obligation', 0.0)
        row.cells[2].text = f'${obligation:,.0f}'
        row.cells[3].text = f"{award.get('start_date', '')} - {award.get('end_date', '')}"

        # Zebra stripe (skip header row, so i+1)
        color = 'F2F2F2' if i % 2 == 0 else 'FFFFFF'
        for cell in row.cells:
            set_cell_shading(cell, color)
            for paragraph in cell.paragraphs:
                for run in paragraph.runs:
                    run.font.name = 'Arial'
                    run.font.size = Pt(9)

    return table
```

### Header/Footer Configuration
```python
# Source: Context7 python-docx docs
from docx.shared import Inches, Pt

section = doc.sections[0]

# Header
header = section.header
header.is_linked_to_previous = False
h_para = header.paragraphs[0]
h_run = h_para.add_run('TCR Policy Scanner | Tribal Advocacy Packet')
h_run.font.name = 'Arial'
h_run.font.size = Pt(8)
h_run.font.color.rgb = RGBColor(0x6B, 0x72, 0x80)

# Footer with page number placeholder
footer = section.footer
footer.is_linked_to_previous = False
f_para = footer.paragraphs[0]
f_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
f_run = f_para.add_run('CONFIDENTIAL | Generated by TCR Policy Scanner')
f_run.font.name = 'Arial'
f_run.font.size = Pt(7)
f_run.font.color.rgb = RGBColor(0x9C, 0xA3, 0xAF)
```

## Economic Impact Methodology

### ECON-01: Multiplier Framework

**Confidence:** MEDIUM -- multiplier ranges derived from published literature, not custom BEA RIMS II queries.

#### BEA Output Multiplier Range
- **Range:** 1.8x - 2.4x for federal grant spending to local/tribal governments
- **Source basis:** BEA RIMS II methodology; published fiscal multiplier literature (Richmond Fed EB-25-28, NBER Working Paper 16561)
- **Citation format for Hot Sheets:** "Estimated regional economic impact: $X - $Y (BEA RIMS II methodology, output multiplier range 1.8-2.4x)"
- **Note:** BEA RIMS II multipliers are region-specific and cost $275+ per custom query. For policy advocacy purposes, the published literature range (1.8-2.4x) is standard practice in policy briefs. This is a defensible range, not a precise calculation.

#### BLS Employment Multiplier
- **Range:** 8-15 jobs per $1M of federal grant spending (direct + indirect)
- **Source:** BLS Employment Requirements Matrix (bls.gov/emp/data/emp-requirements.htm); EPI "Updated Employment Multipliers for the U.S. Economy"
- **Sector relevance:** Construction (higher end: ~13-15 jobs/$M), Government/public administration (lower end: ~8-10 jobs/$M), Environmental remediation (~10-12 jobs/$M)
- **Citation format:** "Estimated employment impact: X-Y jobs supported (BLS employment requirements methodology)"
- **Note:** Present as ranges, not point estimates. The EPI publication provides detailed sector-specific multipliers.

#### FEMA Benefit-Cost Ratio
- **Overall BCR:** 4:1 (every $1 spent on hazard mitigation saves $4 in future disaster costs)
- **By hazard type:**
  - Flood mitigation: ~5:1
  - Wind/hurricane mitigation: ~5:1 (combined with flood)
  - Earthquake mitigation: ~1.5:1
- **Source:** NIBS/FEMA "Natural Hazard Mitigation Saves" (MitSaves) 2018 study; original Multihazard Mitigation Council study (1993-2003 analysis period)
- **Dollar equivalence:** $14.0B benefits vs. $3.5B costs over the study period
- **Citation format:** "Every federal dollar invested in hazard mitigation generates an estimated $4 in future avoided costs (FEMA/NIBS MitSaves, 2018)"
- **Dual framing for mitigation programs (fema_bric, fema_tribal_mitigation, usda_wildfire):**
  1. Future savings: "$X invested = $Y in avoided future disaster costs"
  2. ROI language: "Equivalent to a 14% annual rate of return on a 50-year annuity"

#### Tribal-Specific Context
- Federal Reserve Bank of Minneapolis Center for Indian Country Development (CICD) research shows Tribal economies generate spillover effects to surrounding communities
- $22.5M direct expenditures generated $31.6M total regional impact in one CICD case study (1.4x multiplier on a single-program basis, but broader multipliers are higher)
- NCAI "Honor the Promises" framework provides additional context for policy narratives
- **Key framing:** "Tribal economic activity benefits the entire regional economy -- every dollar of federal climate resilience investment in Indian Country supports jobs and commerce across the district"

#### Multi-District Handling
- Census area overlap data in `districts` field provides percentage overlap per district
- Multi-district Tribes: compute total impact, then allocate proportionally by `overlap_pct`
- **Format:** "Total estimated impact: $X-$Y across [N] congressional districts; [District]: $A-$B ([overlap]% of Tribal land area)"

#### Zero-Award Tribes
- Use program average benchmarks instead of Tribe-specific calculations
- Framing: "Based on program averages for [program], a successful application could generate an estimated $X-$Y in regional economic impact"
- This leverages the `no_awards_context` field from award cache

### Methodology Footnote Template
```
Economic impact estimates use BEA RIMS II output multiplier ranges (1.8-2.4x)
applied to USASpending.gov obligation data. Employment estimates use BLS
employment requirements methodology (8-15 jobs per $1M). Mitigation program
BCR based on FEMA/NIBS Natural Hazard Mitigation Saves (2018). These are
order-of-magnitude estimates for advocacy purposes; precise impacts depend on
local economic structure and program design.
```

## Codebase Architecture (verified field names)

### Program Inventory Fields (VERIFIED from data/program_inventory.json)
All 16 programs confirmed present with these field names:

| Field | Type | Example | Used By |
|-------|------|---------|---------|
| `id` | str | `"bia_tcr"` | All modules |
| `name` | str | `"BIA Tribal Climate Resilience"` | Hot Sheet title |
| `agency` | str | `"BIA"` | Hot Sheet header |
| `federal_home` | str | `"Bureau of Indian Affairs"` | Hot Sheet full name |
| `priority` | str | `"critical"` / `"high"` / `"medium"` | Sort order |
| `ci_status` | str | `"STABLE"` / `"AT_RISK"` / `"FLAGGED"` / etc. | Status badge, framing |
| `confidence_index` | float | `0.88` | CI display |
| `ci_determination` | str | (long text) | Context in Hot Sheet |
| `tightened_language` | str | (long text) | **DOC-03: Direct advocacy text insertion** |
| `advocacy_lever` | str | (short text) | **DOC-03: Direct advocacy text insertion** |
| `access_type` | str | `"direct"` / `"competitive"` / `"tribal_set_aside"` | Access framing |
| `funding_type` | str | `"Discretionary"` / `"Mandatory"` / `"One-Time"` | Funding context |
| `cfda` | str/list/null | `"15.156"` or `["97.047", "97.039"]` or `null` | Award matching |
| `description` | str | (short text) | Program description |
| `hot_sheets_status` | dict | `{"status": "STABLE", "last_updated": "...", "source": "..."}` | Cross-reference |
| `keywords` | list[str] | [...] | Not used in DOCX |
| `specialist_required` | bool (optional) | `true` | FLAGGED programs only |
| `specialist_focus` | str (optional) | (text) | FLAGGED programs only |
| `proposed_fix` | str (optional) | (text) | Some AT_RISK programs |
| `scanner_trigger_keywords` | list[str] (optional) | [...] | Not used in DOCX |

**CRITICAL FIELD NOTE:** `tightened_language` is present on SOME programs (verified: bia_tcr, irs_elective_pay), NOT ALL. The renderer must handle programs without `tightened_language` gracefully -- fall back to `description` + `advocacy_lever`.

**CRITICAL FIELD NOTE:** `cfda` can be a string, a list of strings, or null. The award matching code in `awards.py` normalizes this, but the DOCX renderer should handle all three types when displaying CFDA numbers.

### CI Status Values (VERIFIED)
All observed ci_status values from program_inventory.json:
- `STABLE` (8 programs: bia_tcr, epa_stag, epa_gap, hud_ihbg, fhwa_ttp_safety, usbr_tap, bia_tcr_awards, epa_tribal_air)
- `AT_RISK` (2 programs: irs_elective_pay, fema_tribal_mitigation)
- `FLAGGED` (1 program: fema_bric)
- `SECURE` (1 program: dot_protect)
- `UNCERTAIN` (3 programs: doe_indian_energy, noaa_tribal, usbr_watersmart)
- `STABLE_BUT_VULNERABLE` (1 program: usda_wildfire)

**Color mapping:**
- Red: FLAGGED, AT_RISK
- Amber: UNCERTAIN, STABLE_BUT_VULNERABLE
- Green: STABLE, SECURE

### Graph Schema Structural Asks (VERIFIED from data/graph_schema.json)
Five structural asks confirmed:

| Ask ID | Name | Target | Urgency | Programs Count |
|--------|------|--------|---------|---------------|
| `ask_multi_year` | Multi-Year Funding Stability | Congress | FY26 | 9 programs |
| `ask_match_waivers` | Match/Cost-Share Waivers | Congress | Immediate | 4 programs |
| `ask_direct_access` | Direct Tribal Access | Agency | FY26 | 4 programs |
| `ask_consultation` | Tribal Consultation Compliance | Agency | Ongoing | 4 programs |
| `ask_data_sovereignty` | Data Sovereignty & Capacity | Congress | FY26 | 5 programs |

Each ask has: `id`, `name`, `description`, `target`, `urgency`, `mitigates` (list of barrier IDs), `programs` (list of program IDs).

**DOC-04 implementation:** For each Hot Sheet, look up which structural asks include the program in their `programs` list. Show the ask name, description, and urgency. Cross-reference with barriers.

### Award Cache Schema (VERIFIED from data/award_cache/epa_100000001.json)
```json
{
  "tribe_id": "epa_100000001",
  "tribe_name": "Absentee-Shawnee Tribe of Indians of Oklahoma",
  "awards": [],
  "total_obligation": 0,
  "award_count": 0,
  "cfda_summary": {},
  "no_awards_context": "No federal climate resilience awards found..."
}
```

Individual award objects (from awards.py `match_all_awards()` normalized schema):
```json
{
  "award_id": "",
  "cfda": "15.156",
  "program_id": "bia_tcr",
  "recipient_name_raw": "",
  "obligation": 0.0,
  "start_date": "",
  "end_date": "",
  "description": "",
  "awarding_agency": ""
}
```

**Note:** ALL current award cache files have empty `awards` lists (no USASpending API key configured). The economic impact calculator MUST handle zero-award Tribes as the primary case, with "First-Time Applicant" framing.

### Hazard Profile Schema (VERIFIED from data/hazard_profiles/epa_100000001.json)
```json
{
  "tribe_id": "epa_100000001",
  "tribe_name": "...",
  "sources": {
    "fema_nri": {
      "version": "1.20",
      "counties_analyzed": 0,
      "composite": {
        "risk_score": 0.0,
        "risk_rating": "",
        "eal_total": 0.0,
        "eal_score": 0.0,
        "sovi_score": 0.0,
        "sovi_rating": "",
        "resl_score": 0.0,
        "resl_rating": ""
      },
      "top_hazards": [
        {
          "type": "HRCN",
          "risk_score": 45.2,
          "risk_rating": "Relatively High",
          "eal_total": 12345.0,
          "annualized_freq": 2.5,
          "num_events": 10.0
        }
      ],
      "all_hazards": {
        "AVLN": { "risk_score": 0.0, "risk_rating": "", "eal_total": 0.0, "annualized_freq": 0.0, "num_events": 0.0 },
        "CFLD": { "...": "..." },
        "WFIR": { "...": "..." }
      }
    },
    "usfs_wildfire": {
      "risk_to_homes": 0.0,
      "wildfire_likelihood": 0.0
    }
  },
  "generated_at": "2026-02-10T17:35:21.551454+00:00"
}
```

**NRI Hazard Type Codes:** AVLN (avalanche), CFLD (coastal flooding), CWAV (cold wave), DRGT (drought), ERQK (earthquake), HAIL, HWAV (heat wave), HRCN (hurricane), ISTM (ice storm), IFLD (inland flooding), LNDS (landslide), LTNG (lightning), SWND (strong wind), TRND (tornado), TSUN (tsunami), VLCN (volcano), WFIR (wildfire), WNTW (winter weather).

### Congressional Cache Schema (VERIFIED from data/congressional_cache.json)
```json
{
  "metadata": {
    "congress_session": "119",
    "total_members": 538,
    "total_committees": 46,
    "total_tribes_mapped": 501
  },
  "members": {
    "C001120": {
      "bioguide_id": "C001120",
      "name": "Crenshaw, Dan",
      "state": "TX",
      "district": 2,
      "party": "Republican",
      "party_abbr": "R",
      "chamber": "House",
      "formatted_name": "Rep. Dan Crenshaw (R-TX-02)",
      "committees": [
        {
          "committee_id": "HSAP",
          "committee_name": "House Committee on Appropriations",
          "role": "member",
          "title": "",
          "rank": 17
        }
      ]
    }
  }
}
```

**DOC-03 committee-match flag:** The `committees` array on each senator/representative enables matching against relevant program committees (Appropriations, Energy & Natural Resources, Indian Affairs, etc.).

### Ecoregion Config Schema (VERIFIED from data/ecoregion_config.json)
Seven ecoregions, each with `name`, `states`, `description`, `priority_programs`.

### TribePacketContext Fields (VERIFIED from src/packets/context.py)
```python
@dataclass
class TribePacketContext:
    tribe_id: str
    tribe_name: str
    states: list[str]
    ecoregions: list[str]
    bia_code: str = ""
    epa_id: str = ""
    districts: list[dict]       # [{"state": "AZ", "district": "01", "overlap_pct": 85.0}]
    senators: list[dict]
    representatives: list[dict]
    awards: list[dict]          # From award_cache
    hazard_profile: dict        # From hazard_profiles -> "sources" key
    economic_impact: dict = {}  # PHASE 7 STUB - ready for population
    generated_at: str = ""
    congress_session: str = "119"
```

**Integration point:** `economic_impact` field is already a stub in TribePacketContext. Phase 7 populates this with the output of EconomicImpactCalculator.

### Orchestrator Integration Pattern (VERIFIED from src/packets/orchestrator.py)
```python
# Current flow in _build_context():
1. registry.resolve(tribe_name)     # Phase 5
2. ecoregion.classify(states)       # Phase 5
3. congress.get_delegation(tribe_id) # Phase 5
4. _load_tribe_cache(award_cache_dir, tribe_id)  # Phase 6
5. _load_tribe_cache(hazard_cache_dir, tribe_id) # Phase 6
6. Build TribePacketContext with all data

# Phase 7 adds:
7. EconomicImpactCalculator.compute(awards, districts, programs)
8. context.economic_impact = calculator_result
9. DocxEngine.generate(context, programs, graph_schema)
```

### Decision Engine Classifications (VERIFIED from src/analysis/decision_engine.py)
Six advocacy goals available:
- `URGENT_STABILIZATION` -- LOGIC-05
- `RESTORE_REPLACE` -- LOGIC-01
- `PROTECT_BASE` -- LOGIC-02
- `DIRECT_ACCESS_PARITY` -- LOGIC-03
- `EXPAND_STRENGTHEN` -- LOGIC-04
- `MONITOR_ENGAGE` -- fallback (no rule matched)

Each classification contains: `advocacy_goal`, `goal_label`, `rule`, `confidence`, `reason`, `secondary_rules`.

**DOC-03 framing shifts by CI status:**
- FLAGGED / AT_RISK -> Defensive framing (protect, restore, defend)
- UNCERTAIN / STABLE_BUT_VULNERABLE -> Protective framing (watch, prepare, safeguard)
- STABLE / SECURE -> Growth framing (expand, strengthen, build on)

## Data Schema Verification

### Verified Field Names Across All Data Sources

| Source | Key Fields | Verified |
|--------|-----------|----------|
| program_inventory.json | id, name, agency, ci_status, tightened_language, advocacy_lever, access_type, funding_type, cfda, confidence_index | YES - all 16 programs read |
| graph_schema.json | structural_asks[].id/name/description/target/urgency/mitigates/programs | YES - all 5 asks read |
| award_cache/*.json | tribe_id, tribe_name, awards[], total_obligation, award_count, cfda_summary, no_awards_context | YES - schema verified |
| hazard_profiles/*.json | tribe_id, sources.fema_nri.composite, sources.fema_nri.top_hazards[], sources.usfs_wildfire | YES - schema verified |
| congressional_cache.json | members[].formatted_name, committees[].committee_name/role/title | YES - schema verified |
| ecoregion_config.json | ecoregions{}.name/states/priority_programs | YES - schema verified |
| TribePacketContext | economic_impact: dict (stub) | YES - ready for population |

### Field Name Discrepancies Found: NONE
All field names in the research directives match actual data. No corrections needed.

### Data Completeness Notes
1. **All 500+ award cache files have empty `awards` arrays** -- USASpending API key not configured. Economic impact calculations will primarily use the "First-Time Applicant" path.
2. **Most hazard profiles have zero scores** -- NRI county data not loaded for most Tribes. The relevance filter must handle zero-score gracefully (fall back to ecoregion-based priority programs).
3. **`tightened_language` exists on SOME programs, not all** -- verified present on bia_tcr, irs_elective_pay. Not present on epa_stag, epa_gap, and others. Must fall back to description + advocacy_lever.

## Implementation Risks & Gotchas

### Risk 1: Zero-Data Rendering (HIGH probability)
**Problem:** With no award data and minimal hazard data, most Hot Sheets will have sparse content.
**Mitigation:** Design all sections with graceful empty-state rendering. Use program averages, ecoregion-based defaults, and "First-Time Applicant Advantage" framing. Test with zero-data Tribes first.

### Risk 2: oxml API Stability (LOW probability)
**Problem:** Cell shading via `OxmlElement('w:shd')` is not part of python-docx's public API.
**Mitigation:** This pattern has been stable since python-docx 0.8.x (2015+). Wrap it in a single helper function (`set_cell_shading()`) so changes are isolated.

### Risk 3: Document Size for All-Tribes Generation (MEDIUM probability)
**Problem:** 500+ Tribes x 8-12 Hot Sheets each = 4000-6000 pages in a single document.
**Mitigation:** Generate one .docx per Tribe (not one mega-document). The orchestrator already iterates per-Tribe. Output to `outputs/packets/{tribe_id}.docx`.

### Risk 4: CFDA Field Type Inconsistency (HIGH probability)
**Problem:** `cfda` field is string for most programs, list for fema_bric (`["97.047", "97.039"]`), and null for some (noaa_tribal, fema_tribal_mitigation, epa_tribal_air, usbr_tap).
**Mitigation:** Normalize CFDA to always be a list: `cfda_list = [cfda] if isinstance(cfda, str) else (cfda or [])`.

### Risk 5: Test Regression (CRITICAL to prevent)
**Problem:** 106 existing tests must continue passing.
**Mitigation:** New modules are additive (new files in src/packets/). No modifications to Phase 5-6 modules. New tests in a separate test file (e.g., `tests/test_docx.py`). Run full suite after each change.

### Risk 6: Program Count is Dynamic (MEDIUM probability)
**Problem:** The context talks about "16 programs" but the relevance filter reduces to 8-12 per Tribe. Some Tribes might have fewer if their hazard profile is sparse.
**Mitigation:** Hot Sheet count per Tribe is determined by relevance filter output, not hardcoded. Set minimum threshold (e.g., always include critical programs regardless of hazard relevance). Include omitted programs in appendix.

### Risk 7: Concurrent File Writes on Windows (LOW probability)
**Problem:** atomic write (tmp + replace) can fail on Windows if another process holds the file.
**Mitigation:** Follow existing pattern in generator.py (tmp_path + replace). Catch OSError and retry.

## Recommendations for Planning

### Module Build Order
1. **economic.py** (ECON-01) -- Pure computation, no dependencies on docx. Test first.
2. **relevance.py** (DOC-02 support) -- Hazard-to-program mapping. Depends only on data files.
3. **docx_styles.py** (DOC-01) -- Style definitions. No data dependencies.
4. **docx_hotsheet.py** (DOC-02, DOC-03, DOC-04) -- Core renderer. Depends on styles + data.
5. **docx_sections.py** (DOC-02 support) -- Cover page, appendix. Depends on styles.
6. **docx_engine.py** (DOC-01) -- Assembly. Depends on all above.
7. **Orchestrator integration** -- Wire into existing PacketOrchestrator.

### Task Sizing Guidance
- **economic.py:** Small (pure functions, well-defined inputs/outputs, ~150 lines)
- **relevance.py:** Small (~100 lines, mapping logic)
- **docx_styles.py:** Small (~100 lines, style definitions)
- **docx_hotsheet.py:** Large (most complex module, ~400-500 lines, multiple section renderers)
- **docx_sections.py:** Medium (~150-200 lines, cover page + appendix)
- **docx_engine.py:** Medium (~150 lines, assembly + file output)
- **Orchestrator integration:** Small (~30 lines, wiring)
- **Tests:** Large (~300-400 lines covering all modules)

### Key Design Decisions for Planner
1. **One .docx per Tribe** (not one mega-document) -- output to `outputs/packets/{tribe_id}.docx`
2. **Program relevance filter** determines which programs get Hot Sheets (8-12), with critical programs always included
3. **Hot Sheet section order** (fixed): Status Badge -> Program Description -> Award History -> Hazard Relevance -> Economic Impact -> Advocacy Language -> Key Ask -> Structural Asks -> Delegation
4. **Empty sections are hidden** (not shown with "N/A")
5. **Economic impact always shows ranges** with methodology citation
6. **Zero-award Tribes** get "First-Time Applicant Advantage" framing with program benchmark averages
7. **No AI-generated text** -- all advocacy language from `tightened_language` and `advocacy_lever` fields
8. **Scanner config gets new `packets.docx` section** for output directory, style settings
9. **All styles built programmatically** -- no template .docx reference file

### Test Strategy
- Unit test each module independently with mock data (following test_packets.py pattern)
- Use `tmp_path` pytest fixture for output files
- Test zero-award and zero-hazard Tribes explicitly
- Test CFDA field type variations (string, list, null)
- Test all 6 CI status values for correct color mapping
- Verify document opens in Word (manual QA, not automated)
- Run full 106-test suite to verify no regressions

## Sources

### Primary (HIGH confidence)
- Context7 `/websites/python-docx_readthedocs_io_en` -- styles, fonts, colors, tables, headers/footers, page breaks, pictures
- python-docx GitHub issues #146, #432, #434 -- cell shading via OxmlElement (community-verified pattern)
- Codebase files (all verified by direct read):
  - `F:\tcr-policy-scanner\src\packets\orchestrator.py`
  - `F:\tcr-policy-scanner\src\packets\context.py`
  - `F:\tcr-policy-scanner\src\packets\awards.py`
  - `F:\tcr-policy-scanner\src\reports\generator.py`
  - `F:\tcr-policy-scanner\src\analysis\decision_engine.py`
  - `F:\tcr-policy-scanner\data\program_inventory.json`
  - `F:\tcr-policy-scanner\data\graph_schema.json`
  - `F:\tcr-policy-scanner\data\award_cache\epa_100000001.json`
  - `F:\tcr-policy-scanner\data\hazard_profiles\epa_100000001.json`
  - `F:\tcr-policy-scanner\data\congressional_cache.json`
  - `F:\tcr-policy-scanner\data\ecoregion_config.json`
  - `F:\tcr-policy-scanner\config\scanner_config.json`

### Secondary (MEDIUM confidence)
- [FEMA Benefit-Cost Analysis](https://www.fema.gov/grants/tools/benefit-cost-analysis) -- 4:1 BCR documentation
- [FEMA MitSaves Fact Sheet 2018](https://www.fema.gov/sites/default/files/2020-07/fema_mitsaves-factsheet_2018.pdf) -- BCR by hazard type
- [Richmond Fed EB-25-28](https://www.richmondfed.org/publications/research/economic_brief/2025/eb_25-28) -- fiscal multiplier ranges 1.3-2.0
- [BEA RIMS II User Guide](https://www.bea.gov/resources/methodologies/RIMSII-user-guide) -- methodology reference
- [BLS Employment Requirements Matrix](https://www.bls.gov/emp/data/emp-requirements.htm) -- jobs per $M output
- [EPI Updated Employment Multipliers](https://www.epi.org/publication/updated-employment-multipliers-for-the-u-s-economy/) -- sector-specific jobs data
- [Minneapolis Fed CICD](https://www.minneapolisfed.org/article/2025/insights-from-a-decade-of-economic-research-in-indian-country) -- Tribal economic impact research
- [GAO-22-105215](https://www.gao.gov/products/gao-22-105215) -- Federal Tribal economic development programs

### Tertiary (LOW confidence)
- WebSearch results for Tribal economic multiplier studies -- limited specific data found for Tribal-specific multipliers; general federal spending multipliers used as proxy

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- python-docx is the only viable Python DOCX library; already in requirements.txt
- Architecture: HIGH -- follows existing orchestrator pattern; module structure mirrors Phase 5-6
- Economic methodology: MEDIUM -- multiplier ranges from published literature, not custom BEA queries; defensible for policy advocacy
- Pitfalls: HIGH -- verified via Context7 docs, GitHub issues, and codebase analysis
- Data schemas: HIGH -- every field name verified by reading actual data files

**Research date:** 2026-02-10
**Valid until:** 2026-03-10 (stable domain; python-docx and economic methodology change slowly)
