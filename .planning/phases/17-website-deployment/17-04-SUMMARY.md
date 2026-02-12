# Phase 17 Plan 04: CI/CD Pipeline Summary

**One-liner:** deploy-website.yml for path-triggered GitHub Pages deployment + manifest.json generation in both workflows

## What Was Done

### Task 1: Create deploy-website.yml workflow
- Created `.github/workflows/deploy-website.yml` with path-filtered push trigger on main branch
- Triggers on changes to `docs/web/**`, `scripts/build_web_index.py`, `data/tribal_registry.json`, `data/tribal_aliases.json`, `config/regional_config.json`
- Also supports `workflow_dispatch` for manual triggering
- Steps: checkout, Python 3.12 setup, install deps, build web index (tribes.json with aliases), copy DOCX files to docs/web/tribes/, generate manifest.json, commit and push
- Manifest.json includes deployment timestamp (ISO 8601), per-category document counts, and total documents
- 15-minute timeout (lighter than the full 45-minute generate-packets workflow)
- **Commit:** `54b3657`

### Task 2: Update generate-packets.yml with manifest generation
- Added "Generate deployment manifest" step after "Deploy to docs/web" (so counts reflect actual copied files)
- Updated `git add` line from `docs/web/data/tribes.json` to `docs/web/data/` to capture both tribes.json and manifest.json
- Added comment on "Build web index" step noting automatic alias embedding from `data/tribal_aliases.json`
- No changes to workflow triggers, schedule, or any other existing steps
- **Commit:** `897b32a`

## Verification Results

| Check | Status |
|-------|--------|
| deploy-website.yml YAML syntax valid | PASS |
| Triggers on push to main with correct paths | PASS |
| Calls build_web_index.py | PASS |
| Generates manifest.json with timestamp + counts | PASS |
| Copies DOCX files to docs/web/tribes/ | PASS |
| Commits and pushes changes | PASS |
| generate-packets.yml YAML syntax valid | PASS |
| Manifest step after Deploy step, before Commit step | PASS |
| git add includes docs/web/data/ directory | PASS |
| Alias comment present on Build web index step | PASS |

## Deviations from Plan

None -- plan executed exactly as written.

## Key Files

### Created
- `.github/workflows/deploy-website.yml` -- GitHub Actions workflow for website deployment on push to main

### Modified
- `.github/workflows/generate-packets.yml` -- Added manifest generation step, updated git add scope, added alias comment

## Decisions Made

_No new decisions required. Plan was straightforward workflow configuration._

## Duration

~2 minutes
