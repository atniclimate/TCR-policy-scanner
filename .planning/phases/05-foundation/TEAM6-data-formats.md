# Team 6: Data Format, Storage & Downstream Compatibility

**Researched:** 2026-02-10
**Domain:** JSON schema design, cache organization, python-docx data contracts, encoding safety
**Confidence:** HIGH (based on codebase analysis + official documentation)

---

## Tribal Registry Schema

### Design Rationale

The CONTEXT.md locks several decisions:
- **Primary key:** BIA code (not EPA Tribe ID or NAICS)
- **File structure:** Single `tribal_registry.json` with array of all 575 Tribe objects
- **Ecoregions:** 7 custom advocacy-relevant regions; multi-ecoregion Tribes listed under ALL applicable
- **Extra metadata:** Retain useful EPA API fields (website, population category, etc.)
- **Name variants:** Store for search resolution (Claude's discretion on structure)

### Recommended Schema

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "properties": {
    "metadata": {
      "type": "object",
      "properties": {
        "version": { "type": "string", "example": "1.0.0" },
        "generated": { "type": "string", "format": "date-time" },
        "source": { "type": "string", "example": "EPA Tribes Names Service + BIA Federal Register" },
        "total_tribes": { "type": "integer" },
        "congress": { "type": "string", "example": "119th" }
      },
      "required": ["version", "generated", "source", "total_tribes"]
    },
    "tribes": {
      "type": "array",
      "items": { "$ref": "#/$defs/Tribe" }
    }
  },
  "required": ["metadata", "tribes"],
  "$defs": {
    "Tribe": {
      "type": "object",
      "properties": {
        "tribe_id": {
          "type": "string",
          "description": "Filesystem-safe slug derived from BIA code. Format: bia_{code}. Example: bia_584",
          "pattern": "^bia_[a-z0-9_]+$"
        },
        "bia_code": {
          "type": "string",
          "description": "Official BIA tribal code from EPA Tribes Names Service currentBIATribalCode field"
        },
        "epa_id": {
          "type": "integer",
          "description": "EPA Tribal Internal ID (epaTribalInternalId) for API cross-reference"
        },
        "name": {
          "type": "string",
          "description": "Current official name from BIA recognition. Used in DOCX document title/headers."
        },
        "official_name": {
          "type": "string",
          "description": "Full formal name as published in Federal Register. May differ from 'name' in formality."
        },
        "display_name": {
          "type": "string",
          "description": "Shorter display name for CLI output and table cells. Example: 'Navajo Nation' vs full formal name."
        },
        "historical_names": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "name": { "type": "string" },
              "start_date": { "type": "string", "format": "date" },
              "end_date": { "type": "string", "format": "date" }
            },
            "required": ["name"]
          },
          "description": "Previous names from EPA names[] array. Used for fuzzy match corpus."
        },
        "alternate_names": {
          "type": "array",
          "items": { "type": "string" },
          "description": "Common abbreviations, informal names, and search aliases. Example: ['Navajo', 'Dine', 'Navajo Nation']"
        },
        "states": {
          "type": "array",
          "items": { "type": "string" },
          "description": "Two-letter state codes from EPA epaLocations[].stateCode. Multi-state Tribes have multiple entries."
        },
        "epa_regions": {
          "type": "array",
          "items": { "type": "string" },
          "description": "EPA region names from epaLocations[].epaRegionName"
        },
        "ecoregions": {
          "type": "array",
          "items": {
            "type": "string",
            "enum": [
              "Pacific Northwest",
              "Southwest",
              "Alaska",
              "Great Plains",
              "Southeast",
              "Northeast",
              "Mountain West"
            ]
          },
          "description": "Custom 7-region advocacy classification. Multi-ecoregion Tribes appear in ALL applicable."
        },
        "location": {
          "type": "object",
          "properties": {
            "latitude": { "type": "number" },
            "longitude": { "type": "number" },
            "source": { "type": "string", "description": "Where coordinates came from (BIA GIS, geocoded, etc.)" }
          },
          "description": "Geographic centroid. NOTE: EPA API does NOT provide coordinates; must be sourced separately."
        },
        "bia_recognized": {
          "type": "boolean",
          "description": "From EPA currentBIARecognizedFlag. Should always be true for our registry."
        },
        "recognition_date": {
          "type": "string",
          "format": "date",
          "description": "Date of federal recognition, if available."
        },
        "website": {
          "type": "string",
          "format": "uri",
          "description": "Official tribal website URL, if available from EPA or BIA directory."
        },
        "bia_region": {
          "type": "string",
          "description": "BIA regional office (e.g., 'Eastern Oklahoma', 'Navajo', 'Alaska')"
        },
        "data_quality": {
          "type": "object",
          "properties": {
            "name_verified": { "type": "boolean" },
            "location_verified": { "type": "boolean" },
            "ecoregion_verified": { "type": "boolean" },
            "last_verified": { "type": "string", "format": "date" }
          },
          "description": "Flags for data gap tracking. Missing Tribes flagged as warnings per CONTEXT.md."
        }
      },
      "required": ["tribe_id", "bia_code", "name", "states", "ecoregions", "bia_recognized"]
    }
  }
}
```

### Name Variant Storage for Search Resolution

**Recommendation:** Build a flattened search corpus at load time, not stored separately.

```python
# At registry load time, build the search corpus from the registry data:
search_corpus: list[tuple[str, str]] = []  # (searchable_name, tribe_id)

for tribe in registry["tribes"]:
    # Add current name
    search_corpus.append((tribe["name"].lower(), tribe["tribe_id"]))
    # Add display name
    if tribe.get("display_name"):
        search_corpus.append((tribe["display_name"].lower(), tribe["tribe_id"]))
    # Add historical names
    for hist in tribe.get("historical_names", []):
        search_corpus.append((hist["name"].lower(), tribe["tribe_id"]))
    # Add alternate names
    for alt in tribe.get("alternate_names", []):
        search_corpus.append((alt.lower(), tribe["tribe_id"]))
```

This approach:
- Keeps all name data in one place (the registry JSON)
- Builds the corpus in memory at startup (~3,000 entries for 575 Tribes x ~5 names each)
- Supports both exact substring match and fuzzy fallback (per CONTEXT.md match strategy)
- No separate file to maintain or sync

### Size Estimate

575 Tribes x ~20 fields each x ~500 bytes/tribe = ~280 KB JSON. This is trivially small for in-memory loading.

---

## Congressional Mapping Schema

### Design Rationale

CONTEXT.md locks:
- **Cache structure:** Single `congressional_cache.json` with all members, committees, and Tribe-to-district mappings
- **Cache format:** DOCX-aware structure -- minimize transformation for Phase 7 rendering
- **Congress tagging:** Tag all data with "119th Congress" for staleness detection
- **Party affiliation, leadership roles, committee granularity, contact info:** All required
- **Geographic detail:** Store which reservation/trust land overlaps which district

### Key Modeling Challenge: Many-to-Many

Tribes can span multiple districts (Navajo: 4 districts, 3 states). Districts contain multiple Tribes. This is inherently many-to-many.

**Recommendation:** Primary key by `tribe_id` (the consumer of this data is always "give me delegation for Tribe X"). Include a secondary index by district for reverse lookups.

### Recommended Schema

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "properties": {
    "metadata": {
      "type": "object",
      "properties": {
        "version": { "type": "string" },
        "generated": { "type": "string", "format": "date-time" },
        "congress": { "type": "string", "example": "119th" },
        "congress_session_start": { "type": "string", "format": "date" },
        "data_sources": {
          "type": "array",
          "items": { "type": "string" },
          "example": ["CRS R48107", "Congress.gov API", "BIA GIS"]
        }
      },
      "required": ["version", "generated", "congress"]
    },
    "members": {
      "type": "object",
      "description": "All members of Congress, keyed by bioguide_id. Canonical member data stored once.",
      "additionalProperties": { "$ref": "#/$defs/Member" }
    },
    "committees": {
      "type": "object",
      "description": "Relevant committees, keyed by committee_code (e.g., 'SLIA' for Senate Indian Affairs).",
      "additionalProperties": { "$ref": "#/$defs/Committee" }
    },
    "tribe_delegations": {
      "type": "object",
      "description": "Per-tribe delegation data, keyed by tribe_id. Primary access pattern.",
      "additionalProperties": { "$ref": "#/$defs/TribeDelegation" }
    },
    "district_index": {
      "type": "object",
      "description": "Reverse index: district -> [tribe_ids]. For batch operations and district-centric queries.",
      "additionalProperties": {
        "type": "array",
        "items": { "type": "string" }
      }
    }
  },
  "required": ["metadata", "members", "committees", "tribe_delegations"],
  "$defs": {
    "Member": {
      "type": "object",
      "properties": {
        "bioguide_id": { "type": "string" },
        "name": { "type": "string", "description": "Full name: 'Jane Doe'" },
        "formatted_name": {
          "type": "string",
          "description": "DOCX-ready formatted name: 'Sen. Jane Doe (R-AZ)' or 'Rep. John Smith (D-NM-03)'"
        },
        "chamber": { "type": "string", "enum": ["Senate", "House"] },
        "state": { "type": "string", "description": "Two-letter state code" },
        "district": {
          "type": ["string", "null"],
          "description": "District number for House members. null for Senators. 'AL' for at-large."
        },
        "party": { "type": "string", "description": "R, D, I, etc." },
        "contact": {
          "type": "object",
          "properties": {
            "dc_office": { "type": "string" },
            "dc_phone": { "type": "string" },
            "website": { "type": "string", "format": "uri" }
          },
          "description": "DC office contact info per CONTEXT.md requirement."
        },
        "committee_ids": {
          "type": "array",
          "items": { "type": "string" },
          "description": "Committee codes this member serves on"
        }
      },
      "required": ["bioguide_id", "name", "formatted_name", "chamber", "state", "party"]
    },
    "Committee": {
      "type": "object",
      "properties": {
        "code": { "type": "string" },
        "name": { "type": "string" },
        "chamber": { "type": "string" },
        "is_tribal_relevant": { "type": "boolean", "description": "Flag for committees directly relevant to Tribal policy" },
        "leadership": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "bioguide_id": { "type": "string" },
              "role": { "type": "string", "enum": ["Chair", "Ranking Member", "Vice Chair"] }
            }
          }
        },
        "subcommittees": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "code": { "type": "string" },
              "name": { "type": "string" },
              "leadership": {
                "type": "array",
                "items": {
                  "type": "object",
                  "properties": {
                    "bioguide_id": { "type": "string" },
                    "role": { "type": "string" }
                  }
                }
              }
            }
          }
        }
      },
      "required": ["code", "name", "chamber"]
    },
    "TribeDelegation": {
      "type": "object",
      "description": "Complete delegation data for one Tribe. Designed for direct DOCX rendering with minimal transformation.",
      "properties": {
        "tribe_id": { "type": "string" },
        "tribe_name": { "type": "string", "description": "Denormalized for DOCX rendering convenience" },
        "states": {
          "type": "array",
          "items": { "type": "string" },
          "description": "States this Tribe's lands span"
        },
        "senators": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "bioguide_id": { "type": "string" },
              "state": { "type": "string" }
            }
          },
          "description": "Deduplicated: senators listed once per state, not repeated per district (per CONTEXT.md)"
        },
        "districts": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "state": { "type": "string" },
              "district": { "type": "string", "description": "'AL' for at-large, number otherwise" },
              "district_label": { "type": "string", "example": "AZ-03", "description": "DOCX-ready label" },
              "representative_bioguide_id": { "type": "string" },
              "overlap_description": {
                "type": "string",
                "description": "Which reservation/trust land overlaps this district. Per CONTEXT.md geographic detail requirement."
              },
              "overlap_type": {
                "type": "string",
                "enum": ["full", "partial", "adjacent"],
                "description": "Nature of geographic overlap"
              }
            },
            "required": ["state", "district", "district_label", "representative_bioguide_id"]
          }
        },
        "tribal_relevant_committees": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "committee_code": { "type": "string" },
              "member_bioguide_ids": {
                "type": "array",
                "items": { "type": "string" },
                "description": "Which of THIS Tribe's delegation members sit on this committee"
              }
            }
          },
          "description": "Pre-computed: which committees THIS Tribe's delegation members serve on. DOCX-ready."
        }
      },
      "required": ["tribe_id", "tribe_name", "states", "senators", "districts"]
    }
  }
}
```

### DOCX-Awareness in Schema Design

The schema deliberately denormalizes several fields to minimize transformation in Phase 7:

1. **`formatted_name`** on Member: Pre-formatted as "Sen. Jane Doe (R-AZ)" -- DOCX can render directly
2. **`district_label`** on district entries: Pre-formatted as "AZ-03" -- ready for table cells
3. **`tribe_name`** on TribeDelegation: Denormalized from registry -- DOCX engine does not need to join across files
4. **`tribal_relevant_committees`** pre-computed per Tribe: DOCX engine can render "Your delegation members on Indian Affairs Committee" without graph traversal

### Alaska Handling

Alaska at-large districts use `"district": "AL"` and `"district_label": "AK-AL"`, consistent with all other Tribes. No special format (per CONTEXT.md).

### Navajo Multi-State Example

```json
{
  "tribe_id": "bia_350",
  "tribe_name": "Navajo Nation",
  "states": ["AZ", "NM", "UT"],
  "senators": [
    { "bioguide_id": "S001191", "state": "AZ" },
    { "bioguide_id": "K000377", "state": "AZ" },
    { "bioguide_id": "H001046", "state": "NM" },
    { "bioguide_id": "L000570", "state": "NM" },
    { "bioguide_id": "L000577", "state": "UT" },
    { "bioguide_id": "R000615", "state": "UT" }
  ],
  "districts": [
    {
      "state": "AZ",
      "district": "2",
      "district_label": "AZ-02",
      "representative_bioguide_id": "C001135",
      "overlap_description": "Western Navajo Nation including Tuba City, Kayenta",
      "overlap_type": "partial"
    },
    {
      "state": "AZ",
      "district": "1",
      "district_label": "AZ-01",
      "representative_bioguide_id": "S001211",
      "overlap_description": "Eastern Navajo Nation including Window Rock (capital)",
      "overlap_type": "partial"
    },
    {
      "state": "NM",
      "district": "3",
      "district_label": "NM-03",
      "representative_bioguide_id": "L000273",
      "overlap_description": "Eastern Agency, Checkerboard area",
      "overlap_type": "partial"
    },
    {
      "state": "UT",
      "district": "2",
      "district_label": "UT-02",
      "representative_bioguide_id": "M001209",
      "overlap_description": "Utah strip including Monument Valley",
      "overlap_type": "partial"
    }
  ]
}
```

### Size Estimate

- 535 members (100 senators + 435 representatives) x ~300 bytes = ~160 KB
- ~50 committees x ~500 bytes = ~25 KB
- 575 Tribe delegations x ~800 bytes = ~460 KB
- Total: ~650 KB -- trivially small for in-memory loading

---

## Cache File Organization

### Current Codebase Patterns

The existing codebase uses:
- `data/*.json` for static reference data (program_inventory.json, graph_schema.json, policy_tracking.json)
- `config/*.json` for configuration (scanner_config.json)
- `outputs/*.json` for computed/generated output (LATEST-GRAPH.json, LATEST-MONITOR-DATA.json, LATEST-BRIEFING.md)
- `outputs/archive/` for timestamped historical outputs

### Recommended Directory Layout for v1.1

```
data/
  program_inventory.json          # Existing: 16 programs (static)
  graph_schema.json               # Existing: authorities, barriers, asks (static)
  policy_tracking.json            # Existing: CI positions (static)
  tribal_registry.json            # NEW: 575 Tribes (static, Phase 5)
  congressional_cache.json        # NEW: delegation data (semi-static, Phase 5)
  ecoregion_mapping.json          # NEW: ecoregion definitions + program priorities (Phase 5)

data/cache/
  awards/
    {tribe_id}.json               # Phase 6: per-Tribe USASpending award matches
  hazard_profiles/
    {tribe_id}.json               # Phase 6: per-Tribe hazard profile data
  cache_manifest.json             # Phase 6: tracks cache freshness per tribe

outputs/
  LATEST-BRIEFING.md              # Existing
  LATEST-RESULTS.json             # Existing
  LATEST-GRAPH.json               # Existing
  LATEST-MONITOR-DATA.json        # Existing
  packets/
    {tribe_id}/
      hot-sheet-{tribe_id}.docx   # Phase 7: generated DOCX packet
      packet-metadata.json        # Phase 7: generation timestamp, data versions
  archive/                        # Existing

templates/
  hot-sheet-template.docx         # Phase 7: style reference document for python-docx
  cover-page-template.docx        # Phase 7: cover page template
  assets/
    logo.png                      # Phase 7: header/cover page logo
    map-placeholder.png           # Phase 7: placeholder for district maps
```

### Why `data/cache/` Instead of `data/tribes/`

- `data/` root level = static reference data that ships with the project
- `data/cache/` = computed per-Tribe data that is regenerated on demand
- This distinction matters for git: `data/cache/` can be gitignored while `data/*.json` is tracked

### Cache Manifest Pattern

```json
{
  "version": "1.0.0",
  "last_full_refresh": "2026-02-10T14:30:00Z",
  "tribes": {
    "bia_584": {
      "awards_cached": "2026-02-10T14:30:00Z",
      "hazard_cached": "2026-02-10T14:35:00Z",
      "awards_count": 12,
      "hazard_sources": ["FEMA NRI", "NOAA Storm Events"]
    }
  }
}
```

### Per-Tribe Cache File Format (Awards)

```json
{
  "tribe_id": "bia_584",
  "tribe_name": "Pueblo of Zuni",
  "cached_at": "2026-02-10T14:30:00Z",
  "awards": [
    {
      "program_id": "bia_tcr",
      "award_id": "A-12345",
      "amount": 150000,
      "fiscal_year": "FY25",
      "description": "Climate adaptation planning grant",
      "source": "usaspending",
      "match_confidence": 0.92,
      "match_method": "exact_recipient_name"
    }
  ],
  "summary": {
    "total_awards": 3,
    "total_amount": 450000,
    "programs_with_awards": ["bia_tcr", "epa_gap"],
    "fiscal_years": ["FY24", "FY25"]
  }
}
```

### Per-Tribe Cache File Format (Hazard Profile)

```json
{
  "tribe_id": "bia_584",
  "tribe_name": "Pueblo of Zuni",
  "cached_at": "2026-02-10T14:35:00Z",
  "hazards": {
    "primary": ["drought", "wildfire"],
    "secondary": ["extreme_heat", "flooding"],
    "fema_nri_score": 42.7,
    "fema_nri_rating": "Relatively Moderate"
  },
  "ecoregion_hazards": {
    "Southwest": ["drought", "wildfire", "extreme_heat", "dust_storms"]
  }
}
```

---

## ID Generation & Path Safety

### tribe_id Strategy

**Decision:** Use `bia_{code}` format where `{code}` is the BIA tribal code from the EPA API.

**Rationale:**
- BIA code is the locked primary key (CONTEXT.md decision)
- BIA codes are already alphanumeric (the EPA API field `currentBIATribalCode` contains short codes like "584", "350")
- The `bia_` prefix makes IDs self-documenting and avoids bare numeric keys
- Already filesystem-safe: no special characters, no spaces, no diacritics
- Stable across name changes (unlike slugified names)

**Example mappings:**
| BIA Code | tribe_id | Tribe Name |
|----------|----------|------------|
| 584 | bia_584 | Pueblo of Zuni |
| 350 | bia_350 | Navajo Nation |
| 24 | bia_024 | Agua Caliente Band of Cahuilla Indians |

**Zero-padding:** Pad BIA codes to 3 digits for consistent sorting: `bia_024`, `bia_350`, `bia_584`. This ensures lexicographic sorting matches numeric sorting.

### Why NOT Slugified Names

- Tribe names contain apostrophes: "Coeur d'Alene" -> ambiguous slug
- Tribe names contain diacritics: possible encoding issues
- Tribe names change over time: "Mashpee Wampanoag" vs historical variants
- Tribe names are LONG: "Confederated Tribes of the Grand Ronde Community of Oregon" -> very long filenames
- BIA codes are stable, short, and unique

### Windows Path Length Safety

**Maximum realistic path:**
```
F:\tcr-policy-scanner\data\cache\awards\bia_584.json
```
= ~55 characters. Even with the deepest nesting:
```
F:\tcr-policy-scanner\outputs\packets\bia_584\hot-sheet-bia_584.docx
```
= ~70 characters.

**Verdict:** With BIA-code-based IDs, path lengths stay well under 100 characters. The 260-character Windows limit is NOT a practical concern for this project. No need for `\\?\` prefix or long path registry workaround.

**If tribe names were used as directory names**, the longest federally recognized tribe name is approximately 60+ characters, which combined with nesting could approach 200+ characters. BIA codes eliminate this risk entirely.

### Encoding Requirements

- All JSON files: UTF-8 encoding with BOM-less output
- All `open()` calls: always pass `encoding="utf-8"` (per codebase convention from Windows quirks in MEMORY.md)
- All `Path.write_text()` calls: always pass `encoding="utf-8"`
- Tribe names in JSON: stored as Unicode (JSON natively supports this)
- File paths: use only ASCII characters (BIA codes guarantee this)

---

## Performance Considerations

### Memory Budget for 575 Tribes

| Data File | Estimated Size | Load Strategy |
|-----------|---------------|---------------|
| tribal_registry.json | ~280 KB | Full load at startup |
| congressional_cache.json | ~650 KB | Full load at startup |
| ecoregion_mapping.json | ~10 KB | Full load at startup |
| 575 x awards cache | ~2 MB total | Lazy load per-Tribe OR batch pre-load |
| 575 x hazard profiles | ~1 MB total | Lazy load per-Tribe OR batch pre-load |

**Total static data in memory:** ~1 MB. Negligible.

**Total cached data if fully loaded:** ~4 MB. Still negligible for modern systems.

### Loading Strategy by Phase

**Phase 5 (Foundation):** Load `tribal_registry.json` and `congressional_cache.json` fully at startup. Under 1 MB combined, instant load.

**Phase 6 (Data Acquisition):** Write per-Tribe cache files individually. Load on demand when generating a single Tribe's packet. For `--all-tribes` batch mode, can pre-load all 575 cache files sequentially (~4 MB, under 1 second).

**Phase 8 (Assembly, batch mode):** Pre-load ALL data at startup:
```python
# Batch mode: load everything up front
registry = json.loads(Path("data/tribal_registry.json").read_text(encoding="utf-8"))
congress = json.loads(Path("data/congressional_cache.json").read_text(encoding="utf-8"))

# Pre-load all per-Tribe caches
awards_cache = {}
for tribe in registry["tribes"]:
    tid = tribe["tribe_id"]
    cache_path = Path(f"data/cache/awards/{tid}.json")
    if cache_path.exists():
        awards_cache[tid] = json.loads(cache_path.read_text(encoding="utf-8"))
```

### 575 Tribes x 16 Programs = 9,200 Combinations

This is the "relevance matrix" -- which programs matter to which Tribe. This is NOT 9,200 separate files. The mapping is computed by:
1. Tribe's ecoregion -> relevant programs (from ecoregion_mapping.json)
2. Tribe's awards history -> previously funded programs (from awards cache)
3. All 16 programs are presented for every Tribe, but with relevance scoring

This is a compute operation, not a storage operation. Each Tribe's Hot Sheet includes all 16 programs -- the data is already in `program_inventory.json`.

### Data Class vs Dict

**Recommendation:** Use `@dataclass` for Tribe and Delegation objects in Python code.

Reasons:
- The existing codebase already uses dataclasses extensively (see `src/graph/schema.py`)
- 575 Tribe objects at ~1 KB each = ~575 KB. Dataclass overhead vs dict is ~2x per instance, but at 575 instances the absolute difference is ~575 KB. Irrelevant.
- Dataclasses provide IDE autocomplete, type checking, and clear contracts
- Avoid Pydantic for this use case: Pydantic's validation overhead is unnecessary for pre-validated static JSON (the JSON is generated once, loaded many times)

```python
@dataclass
class TribeRecord:
    tribe_id: str
    bia_code: str
    name: str
    official_name: str
    display_name: str
    states: list[str]
    ecoregions: list[str]
    historical_names: list[dict]
    alternate_names: list[str]
    location: dict | None = None
    epa_id: int | None = None
    website: str | None = None
    bia_region: str | None = None
    bia_recognized: bool = True
```

---

## python-docx Data Requirements

### Confidence: HIGH
Based on official python-docx 1.2.0 documentation (readthedocs.io).

### Document Creation Pattern

python-docx uses a style reference document pattern. Phase 7 will create a template `.docx` file with all needed styles pre-defined, then open it as the starting document:

```python
from docx import Document
from docx.shared import Inches, Pt

# Open the style reference template
doc = Document("templates/hot-sheet-template.docx")
```

The template file must contain every style used in generation (Heading 1, Heading 2, custom table styles, etc.) defined at least once, even if the content is deleted.

### Data Format Requirements by Document Element

**1. Cover Page Fields**

python-docx needs plain strings for paragraph text. The cover page data contract:

```python
cover_data = {
    "tribe_name": str,           # "Navajo Nation"
    "official_name": str,        # Full formal name
    "congress": str,             # "119th Congress"
    "generation_date": str,      # "February 10, 2026"
    "ecoregions": list[str],     # ["Southwest", "Mountain West"]
    "states": list[str],         # ["AZ", "NM", "UT"]
}
```

**2. Header/Footer Fields**

Headers support tab-separated zones (left/center/right). Data needed:

```python
header_data = {
    "tribe_display_name": str,   # Short name for header
    "congress": str,             # "119th Congress"
    "page_label": str,           # "Hot Sheet" or section name
    "logo_path": str,            # Path to logo image file
}
```

Adding images to headers (supported since python-docx 0.8.8+):
```python
header = section.header
paragraph = header.paragraphs[0]
run = paragraph.add_run()
run.add_picture("templates/assets/logo.png", width=Inches(0.5))
run.add_text("\tHot Sheet - Navajo Nation\t119th Congress")
```

**3. Table Data**

python-docx tables accept data as cell-by-cell string assignment:

```python
# Program status table
table = doc.add_table(rows=1, cols=5, style="Light Grid Accent 1")
headers = ["Program", "Status", "CI", "Funding", "Advocacy Lever"]
for i, header_text in enumerate(headers):
    table.rows[0].cells[i].text = header_text

for program in programs:
    row = table.add_row()
    row.cells[0].text = program["name"]         # str
    row.cells[1].text = program["ci_status"]     # str
    row.cells[2].text = f"{program['confidence_index'] * 100:.0f}%"  # str
    row.cells[3].text = program.get("fy26_funding", "N/A")  # str
    row.cells[4].text = program["advocacy_lever"]  # str
```

**All cell values must be strings.** Numbers, dates, and percentages must be pre-formatted.

**4. Delegation Table Data**

```python
# The TribeDelegation schema is designed to render directly:
delegation_table_rows = []
for senator in delegation["senators"]:
    member = members[senator["bioguide_id"]]
    delegation_table_rows.append({
        "name": member["formatted_name"],  # Already formatted: "Sen. Jane Doe (R-AZ)"
        "chamber": "Senate",
        "district": senator["state"],
        "contact": member.get("contact", {}).get("dc_phone", ""),
    })
for district in delegation["districts"]:
    member = members[district["representative_bioguide_id"]]
    delegation_table_rows.append({
        "name": member["formatted_name"],  # "Rep. John Smith (D-NM-03)"
        "chamber": "House",
        "district": district["district_label"],  # "NM-03"
        "contact": member.get("contact", {}).get("dc_phone", ""),
    })
```

**5. Images (District Maps)**

```python
from docx.shared import Inches

# District map image -- Phase 7 generates the map image, Phase 5 ensures
# geographic data (lat/lon, district overlaps) supports map generation
doc.add_picture(map_image_path, width=Inches(5.0))
```

python-docx only supports inline pictures (not floating). Images must be provided as file paths or file-like objects. Supported formats: PNG, JPEG, GIF, BMP, TIFF.

### python-docx-template (docxtpl) Consideration

**Recommendation:** Use `python-docx` directly, NOT `python-docx-template` (docxtpl).

Rationale:
- The existing codebase does not use docxtpl
- docxtpl adds Jinja2 tags inside .docx XML, which is fragile and hard to debug
- python-docx gives full programmatic control over document structure
- The Hot Sheet layout is complex enough to warrant programmatic construction (conditional sections, variable-length tables, per-Tribe committee data)
- docxtpl is better for simple mail-merge-style templates with fixed structure; Hot Sheets have dynamic structure

---

## Phase Interface Contracts

### Phase 5 -> Phase 6 Contract

Phase 6 (Data Acquisition) needs from Phase 5:

```python
# Phase 6 AWARD-02: Per-Tribe USASpending fuzzy matching
# Needs: Tribe canonical names for matching against USASpending recipient names

class TribalRegistry:
    """Public interface Phase 6 depends on."""

    def get_tribe(self, tribe_id: str) -> TribeRecord | None:
        """Get a single Tribe by ID."""

    def get_all_tribes(self) -> list[TribeRecord]:
        """Get all 575 Tribes for batch processing."""

    def get_fuzzy_match_corpus(self) -> list[tuple[str, str]]:
        """Return (name_variant, tribe_id) pairs for fuzzy matching.
        Includes official names, historical names, and alternate names.
        Phase 6 uses this to match USASpending recipient names to Tribes."""

    def get_tribes_by_ecoregion(self, ecoregion: str) -> list[TribeRecord]:
        """Get Tribes in a given ecoregion for hazard profiling."""

    def get_tribes_by_state(self, state_code: str) -> list[TribeRecord]:
        """Get Tribes in a given state."""
```

**Critical fields Phase 6 reads:**
- `tribe_id` -- for cache file naming
- `name`, `official_name`, `display_name`, `historical_names`, `alternate_names` -- for fuzzy matching corpus
- `states`, `ecoregions`, `location` -- for hazard profiling
- `bia_code` -- for cross-referencing with BIA data sources

### Phase 5 -> Phase 7 Contract

Phase 7 (DOCX Generation) needs from Phase 5:

```python
# Phase 7 DOC-01/REG-03: DOCX rendering
# Needs: Tribe identity for document title, headers, cover page
# Needs: Delegation data for delegation section

class TribalRegistry:
    """Fields Phase 7 reads for DOCX rendering."""

    def get_tribe(self, tribe_id: str) -> TribeRecord | None:
        """Phase 7 reads: name, official_name, display_name, states, ecoregions"""

class CongressionalCache:
    """Public interface Phase 7 depends on."""

    def get_delegation(self, tribe_id: str) -> TribeDelegation | None:
        """Get pre-computed delegation for a Tribe.
        Returns DOCX-ready data: formatted_name, district_label, committee info."""

    def get_member(self, bioguide_id: str) -> Member | None:
        """Get member details including formatted_name and contact info."""

    def get_tribal_committees(self) -> list[Committee]:
        """Get committees flagged as tribal-relevant (Indian Affairs, etc.)."""
```

**Critical fields Phase 7 reads:**
- `TribeRecord.name` -- DOCX document title
- `TribeRecord.display_name` -- DOCX header
- `TribeRecord.official_name` -- cover page
- `TribeRecord.states`, `TribeRecord.ecoregions` -- cover page and narrative
- `Member.formatted_name` -- directly into DOCX table cells (pre-formatted)
- `TribeDelegation.senators`, `.districts` -- delegation table
- `TribeDelegation.tribal_relevant_committees` -- committee section
- `Member.contact.dc_office`, `.dc_phone` -- contact information section

### Phase 5 -> Phase 8 Contract

Phase 8 (Assembly) needs from Phase 5:

```python
class TribalRegistry:
    """Phase 8 batch mode interface."""

    def get_all_tribe_ids(self) -> list[str]:
        """Return all 575 tribe_ids for batch iteration."""

    def get_tribe(self, tribe_id: str) -> TribeRecord | None:
        """Individual Tribe lookup during batch processing."""
```

**Critical for Phase 8:**
- Efficient iteration over all 575 Tribes
- Per-Tribe data loading from cache files
- Previous state comparison for change tracking (compare current vs cached `packet-metadata.json`)

---

## Recommendations

### 1. Use BIA Code as Primary Key (LOCKED)

Format: `bia_{zero_padded_code}`. Examples: `bia_024`, `bia_350`, `bia_584`.
- Filesystem-safe, short, stable, unique
- Zero-pad to 3 digits for sort consistency

### 2. Single Registry File, Single Congress Cache (LOCKED)

Both files load entirely into memory at startup. Combined size under 1 MB.
- `data/tribal_registry.json` -- 575 Tribes
- `data/congressional_cache.json` -- all members, committees, Tribe delegations

### 3. DOCX-Aware Denormalization in Congress Cache

Pre-format display strings (`formatted_name`, `district_label`) in the cache so Phase 7 does not need to compute them. This is the "minimize transformation for DOCX rendering" requirement from CONTEXT.md.

### 4. Per-Tribe Cache Under `data/cache/`

- `data/cache/awards/{tribe_id}.json` for Phase 6 award matching
- `data/cache/hazard_profiles/{tribe_id}.json` for Phase 6 hazard data
- Gitignore `data/cache/` -- these are computed artifacts
- Use `cache_manifest.json` for freshness tracking

### 5. Use python-docx Directly (Not docxtpl)

python-docx with a style reference template document gives full control. Hot Sheets have dynamic structure that benefits from programmatic construction.

### 6. Dataclass-Based Python Objects

Follow existing codebase pattern (`src/graph/schema.py`). Use `@dataclass` for TribeRecord, Member, Committee, TribeDelegation. Avoid Pydantic overhead for pre-validated static data.

### 7. Build Fuzzy Match Corpus at Load Time

Do not store a separate search index file. Build from registry data at startup:
- ~3,000 name/tribe_id pairs for 575 Tribes
- Supports exact substring match (primary) and rapidfuzz fallback (secondary)
- Use `rapidfuzz` (not `thefuzz`) for fuzzy matching -- faster C++ implementation

### 8. All File I/O Uses UTF-8 Explicitly

Per codebase convention and Windows quirks from MEMORY.md:
```python
# Always explicit encoding
with open(path, encoding="utf-8") as f: ...
Path(path).write_text(content, encoding="utf-8")
```

---

## Open Questions

### 1. Geographic Coordinates Source
- **What we know:** EPA Tribes Names Service does NOT provide lat/lon coordinates
- **What is unclear:** Where to source geographic centroids for 575 Tribes
- **Options:** BIA GIS data (geopub.epa.gov ArcGIS service has Tribal boundary layers), geocoding from state/reservation name, or manual curation
- **Impact:** Phase 7 district map generation requires coordinates. Phase 5 schema supports the field but population may be deferred to Phase 6 data acquisition.
- **Recommendation:** Include the `location` field in schema as optional. Populate from BIA GIS ArcGIS service if accessible, otherwise flag as data gap.

### 2. BIA Code Coverage for All 575 Tribes
- **What we know:** EPA API uses `currentBIATribalCode` but may not cover all 575 Tribes (Lumbee added very recently via FY2026 NDAA)
- **What is unclear:** Whether EPA API has been updated to include Lumbee Tribe
- **Impact:** If any Tribe lacks a BIA code, the `bia_{code}` ID strategy needs a fallback
- **Recommendation:** For Tribes without BIA codes, use `manual_{sequential_number}` as tribe_id and flag in `data_quality`. Expect 0-5 Tribes in this category.

### 3. CRS Report Table Extraction Format
- **What we know:** CRS R48107 maps Tribes to congressional districts (Team 2 researching)
- **What is unclear:** Whether the extracted data will provide overlap descriptions or just Tribe/district pairings
- **Impact:** The `overlap_description` and `overlap_type` fields in TribeDelegation depend on CRS data richness
- **Recommendation:** Make these fields optional in schema. Populate with available data, use "See CRS R48107" as fallback description.

### 4. Committee Relevance Criteria
- **What we know:** CONTEXT.md says track full committee + subcommittee assignments
- **What is unclear:** Which committees are "tribal-relevant" (Indian Affairs is obvious, but Natural Resources? Appropriations Interior subcommittee?)
- **Impact:** The `is_tribal_relevant` flag on Committee and the `tribal_relevant_committees` list on TribeDelegation depend on this
- **Recommendation:** Start with a curated list: Senate Indian Affairs, House Natural Resources (Subcommittee on Indian and Insular Affairs), Senate/House Appropriations Interior subcommittees. Configurable for expansion.

---

## Sources

### Primary (HIGH confidence)
- python-docx 1.2.0 official documentation (readthedocs.io) -- Document API, Table API, Header/Footer API, Styles
- EPA Tribes Names Service documentation (epa.gov/data/tribes-names-service) -- API fields, BIA code availability
- Existing codebase analysis (`src/graph/schema.py`, `src/main.py`, `src/reports/generator.py`, `src/scrapers/usaspending.py`) -- current patterns, data shapes, encoding conventions

### Secondary (MEDIUM confidence)
- python-docx GitHub issue #407 -- image in header support confirmed for 0.8.8+
- RapidFuzz documentation (github.com/rapidfuzz/RapidFuzz) -- fuzzy matching performance characteristics
- python-slugify PyPI documentation -- filesystem-safe identifier generation patterns

### Tertiary (LOW confidence)
- BIA GIS ArcGIS service availability for geographic coordinates -- not verified, endpoint may require authentication
- BIA code coverage for most recently recognized Tribes -- not verified against current EPA API response

---

## Confidence Assessment

| Area | Level | Reason |
|------|-------|--------|
| Tribal Registry Schema | HIGH | Based on locked CONTEXT.md decisions + verified EPA API field documentation |
| Congressional Mapping Schema | HIGH | Based on locked CONTEXT.md decisions + clear requirements for DOCX rendering |
| Cache File Organization | HIGH | Follows existing codebase patterns, straightforward filesystem design |
| ID Generation | HIGH | BIA code strategy eliminates all encoding/path-safety concerns |
| Performance | HIGH | 575 Tribes x sub-KB records = trivially small dataset; no optimization needed |
| python-docx Requirements | HIGH | Verified against official 1.2.0 documentation |
| Phase Interface Contracts | MEDIUM | Contracts derived from requirement descriptions; may evolve during Phase 6-8 planning |
| Geographic Coordinates | LOW | Source not identified; EPA API confirmed to NOT provide lat/lon |
