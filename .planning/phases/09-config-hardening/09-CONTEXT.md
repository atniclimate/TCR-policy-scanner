# Phase 9: Config Hardening - Context

**Gathered:** 2026-02-11
**Status:** Ready for planning

<domain>
## Phase Boundary

Eliminate all hardcoded path strings from source code. Every file path resolves through a centralized `src/paths.py` module using pathlib, so changing a data directory location in one place propagates to all consumers. Pure code refactor -- no config file schema changes, no new features.

</domain>

<decisions>
## Implementation Decisions

### Environment flexibility
- Pathlib-relative only -- all paths resolve relative to PROJECT_ROOT via pathlib
- No env var overrides, no config file paths section
- Works on any OS, any clone location (F:\ Windows dev and GitHub Actions Linux)
- paths.py owns PROJECT_ROOT (config.py imports from it if needed)
- No import-time validation -- pure path constants, callers get FileNotFoundError at usage time
- Include helper functions alongside constants (e.g., `award_cache_path(tribe_id)`, `hazard_profile_path(tribe_id)`) to encode naming conventions

### Centralization scope
- Centralize ALL path references: data/, config/, outputs/, docs/web/, scripts/ -- every directory reference goes through paths.py
- Organized by domain internally (project root section, config paths, data paths with sub-caches, output paths, etc.)
- Tests also import from paths.py -- consistent across the whole project
- structural_asks is a normal data path constant, no special treatment (success criteria highlights it as an example of the problem, not a special case)

### Config file changes
- Pure code refactor -- scanner_config.json keeps its current schema unchanged
- config.py and paths.py stay separate: config.py owns non-path config (FISCAL_YEAR, etc.), paths.py owns all path constants
- Full migration: every source file that constructs paths gets updated to import from paths.py. No ad-hoc path construction survives.
- Grep-based verification step to catch regressions (grep for common path anti-patterns like string literals containing 'data/', 'config/', etc.)

### Claude's Discretion
- Exact grouping and naming of path constants (DATA_DIR, CONFIG_DIR, etc.)
- Which helper functions are worth creating vs. leaving as caller-side construction
- How to handle any edge cases in test path references
- Exact grep patterns for the regression verification step

</decisions>

<specifics>
## Specific Ideas

No specific requirements -- open to standard approaches. User accepted all recommended patterns.

</specifics>

<deferred>
## Deferred Ideas

None -- discussion stayed within phase scope

</deferred>

---

*Phase: 09-config-hardening*
*Context gathered: 2026-02-11*
