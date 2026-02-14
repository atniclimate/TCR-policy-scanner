# Website Agent Swarm — Launch Prompt

Copy everything below the `---` line and paste into a fresh Claude Code session at `F:\tcr-policy-scanner`.

---

```
I need you to launch a 4-agent parallel review swarm for the TCR Policy Scanner website interface.
The draft assets are in `.planning/website/` — a React/Vite/Tailwind/shadcn prototype generated
partly by Figma export with significant shortcomings. The goal is to connect this to the real
TCR Policy Scanner pipeline and deploy via SquareSpace.

## Context

The TCR Policy Scanner generates per-Tribe DOCX advocacy packets for 592 federally recognized
Tribal Nations. The Python pipeline lives in this repo. The website needs to:
1. Let users search/select their Tribal Nation from 592 options
2. Let users select a region from 8 ecoregions
3. Download the REAL pre-generated DOCX packet (not a fake text blob)
4. Display data governance framework (TSDF T0/T1 classification)
5. Be embeddable in a SquareSpace website via Code Block or iframe
6. GitHub: https://github.com/atniclimate/TCR-policy-scanner/tree/main

## The Draft Assets (`.planning/website/`)

```
index.html              — Vite entry point
package.json            — 30+ Radix deps, most unused
vite.config.ts          — bizarre version-pinned aliases
src/
  main.tsx              — React entry
  App.tsx               — Main layout (header, 2-col grid, footer)
  index.css             — 1424 lines PRE-COMPILED Tailwind (not source!)
  styles/globals.css    — Actual Tailwind source (14 lines)
  data/mockData.ts      — 46 hardcoded Tribe names, 29 fake regions
  components/
    AnimatedBackground.tsx  — Canvas particle system (40 particles + hex grid)
    TypewriterText.tsx      — Character-by-character text animation
    TribeSelector.tsx       — Search autocomplete (downloads FAKE txt blob)
    RegionSelector.tsx      — Dropdown select (downloads FAKE txt blob)
    DisclaimerModal.tsx     — TSDF governance framework modal
    PurposeSection.tsx      — UNUSED duplicate of modal content
    figma/ImageWithFallback.tsx
    ui/ (45+ shadcn components, ~5 actually used)
```

Design aesthetic: Blade Runner-inspired dark UI with cyan/amber palette, scanlines,
hexagonal grid animation, typewriter effects. The intent is good — the execution has
problems documented in TODO comments within the code:
- App.tsx:71 — "Figma can't figure out how to make a decent alignment and need to fix this"
- App.tsx:180 — "Figma cannot figure out how to do this" (footer)
- DisclaimerModal.tsx:13 — "Figma cannot figure out spacing, and needs to be fixed by
  Claude Code; also ensure Claude Code reviews the entire code block that Figma has
  produced as it can't be trusted to have been done correctly"

Also existing: `docs/web/index.html` — a WORKING plain HTML/CSS/JS widget with
Awesomplete autocomplete that was the v1 approach (simpler, accessible, functional).

## The 4 Agents

Read the agent definitions at `.claude/agents/` before launching. Each has:
- A distinct personality and domain expertise
- Non-overlapping file ownership (where applicable)
- A specific review checklist of known issues
- A structured JSON output format

### Agent 1: The Web Wizard (performance & build)
**Agent type**: `feature-dev:code-reviewer`
**Definition**: `.claude/agents/web-wizard.md`
**Prompt**: Read the agent definition at `.claude/agents/web-wizard.md` for your personality,
domain, and review checklist. You are The Web Wizard — performance architect and cutting-edge
web technologist. Audit every file in your domain for performance issues, bundle bloat, font
loading problems, Core Web Vitals risks, and SquareSpace compatibility. Use Context7 to check
latest Vite and Tailwind CSS best practices. Read EVERY file in `.planning/website/` that's in
your domain. Write findings to `outputs/website_review/web-wizard_findings.json`. Be specific
with line numbers and concrete fixes. Focus on: the Canvas particle system performance cost,
the pre-compiled CSS problem, the 30+ unused Radix deps, font loading strategy, and whether
this build will survive inside a SquareSpace iframe.

### Agent 2: The Mind Reader (UX/UI & accessibility)
**Agent type**: `feature-dev:code-reviewer`
**Definition**: `.claude/agents/mind-reader.md`
**Prompt**: Read the agent definition at `.claude/agents/mind-reader.md` for your personality,
domain, and review checklist. You are The Mind Reader — UX/UI intuition specialist and Blade
Runner connoisseur. Audit every file in your domain for accessibility failures (WCAG 2.1 AA),
interaction design problems, information architecture issues, and visual hierarchy mistakes.
The fake data (46 Tribes, 29 regions) must be flagged as critical — the real system has
592 Tribes and 8 regions. Read EVERY component in `.planning/website/src/components/`. Check
all ARIA attributes, keyboard navigation, focus management, and screen reader experience.
Write findings to `outputs/website_review/mind-reader_findings.json`. Channel your inner
Blade Runner: every glow must have purpose, every shadow must create depth.

### Agent 3: The Keen Kerner (typography)
**Agent type**: `feature-dev:code-reviewer`
**Definition**: `.claude/agents/keen-kerner.md`
**Prompt**: Read the agent definition at `.claude/agents/keen-kerner.md` for your personality,
domain, and review checklist. You are The Keen Kerner — typography specialist who knows the
difference between a font and a typeface. Audit EVERY file in `.planning/website/src/` for
typography issues. Check: the dual typeface strategy (Roboto for 1 element, League Spartan
for everything else), the clamp() values that go below 8px minimum, the 0.15em letter-spacing
that destroys character rhythm, the inconsistent line-height approaches (Tailwind vs inline),
and the 100+ character line measure in the modal. Read every inline `style={{ fontFamily, fontSize,
fontWeight, letterSpacing, lineHeight }}` declaration. Write findings to
`outputs/website_review/keen-kerner_findings.json`. Be precise — include current and
recommended values with rationale.

### Agent 4: The Power Pipeline Professor (data & deployment)
**Agent type**: `feature-dev:code-reviewer`
**Definition**: `.claude/agents/pipeline-professor.md`
**Prompt**: Read the agent definition at `.claude/agents/pipeline-professor.md` for your
personality, domain, and review checklist. You are The Power Pipeline Professor — data pipeline
architect and deployment specialist. The CRITICAL issue is that TribeSelector.tsx and
RegionSelector.tsx generate FAKE text blob downloads instead of connecting to real DOCX packets.
Audit the full data flow: mockData.ts -> selectors -> download. Then design the real pipeline:
GitHub Actions -> DOCX generation -> GitHub Pages/Releases -> manifest.json -> website fetch ->
real DOCX download. Also read `.github/workflows/generate-packets.yml` for the existing CI,
`docs/web/index.html` for the working v1 widget, and evaluate 3 SquareSpace integration
approaches (iframe, Code Injection, hybrid). Write findings to
`outputs/website_review/pipeline-professor_findings.json`. Include step-by-step implementation
for the real data pipeline.

## Coordination Rules

1. Create `outputs/website_review/` directory before agents start
2. Each agent writes ONLY to its own `_findings.json` file — no cross-editing
3. This is a READ-ONLY audit — no agent modifies source files in `.planning/website/`
4. Each agent reads its definition file FIRST, then reads its domain files
5. Cross-cutting concerns (typography appears in every component) are noted by the
   Keen Kerner but fixes are proposed as patches, not direct edits

## After All 4 Agents Complete

Synthesize all findings into `outputs/website_review/SYNTHESIS.md` with:

### Priority Matrix
| Priority | Category | Agent | Issue Count | Blocking? |
|----------|----------|-------|-------------|-----------|
| P0 | Pipeline is fake | Professor | 2 | YES — nothing works without real data |
| P1 | Accessibility | Mind Reader | ? | YES — WCAG compliance is non-negotiable |
| P2 | Performance | Wizard | ? | Affects SquareSpace embed viability |
| P3 | Typography | Kerner | ? | Quality of polish |

### Cross-Agent Themes
- Where do agents agree on the same underlying problem?
- Where do agent recommendations conflict?

### Implementation Roadmap
Phase 1: Data pipeline (Professor) — make downloads real
Phase 2: Accessibility fixes (Mind Reader) — WCAG AA compliance
Phase 3: Performance optimization (Wizard) — SquareSpace-safe build
Phase 4: Typography refinement (Kerner) — professional polish

### Architecture Decision: SquareSpace Strategy
Synthesize the Professor's 3 approaches with the Wizard's compatibility findings
and the Mind Reader's UX implications. Recommend ONE approach with justification.

## Available Skills to Use (invoke with /skill-name where helpful)
- `/squarespace-customization` — CSS injection, Code Blocks, LESS, JSON-T patterns
- `/design-system-architecture` — design tokens, type scale, color system
- `/progressive-disclosure-ux` — reducing cognitive load
- `/accessible-dataviz` — WCAG 2.1 AA for data interfaces
- `/visual-perception-psychology` — preattentive processing, Gestalt principles
- `/development-patterns` — coding conventions, PR standards
- `/mcp-browser-automation` — Playwright for visual regression testing
- `/shadcn-vanilla` — shadcn patterns without React dependency (for Code Injection approach)

## Available MCPs
- **Playwright**: browser automation, screenshots, accessibility audits
- **shadcn**: component registry lookup
- **Context7**: library documentation (Vite, React, Tailwind, SquareSpace)
- **GitHub**: repo API, releases, pages, actions workflows

Launch all 4 agents in parallel now. Each should read its agent definition FIRST.
```
