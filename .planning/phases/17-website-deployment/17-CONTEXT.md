# Phase 17: Website Deployment - Context

**Gathered:** 2026-02-12
**Status:** Ready for planning

<domain>
## Phase Boundary

Public website where any of 592 Tribal Nations can search for their Nation by name (with typo tolerance and alias matching), browse by state, and download real DOCX advocacy packets. Served from GitHub Pages, embeddable in SquareSpace iframe, accessible via keyboard and screen reader, performant on mobile. Enhances the existing vanilla HTML/JS/CSS site at `docs/web/` rather than rewriting in React.

</domain>

<decisions>
## Implementation Decisions

### Stack approach
- Enhanced vanilla HTML/JS/CSS -- no React, no Vite, no Tailwind, no shadcn/ui
- Fuse.js (~7KB) for fuzzy search with typo tolerance across 592 Tribe names + 18,776 aliases
- Keep existing CSS custom properties approach (--tcr-primary, etc.) and extend as needed
- No build step -- static files served directly from `docs/web/` via GitHub Pages

### Search combobox
- Claude's discretion on whether to replace Awesomplete with a custom ARIA combobox or layer Fuse.js on top
- Decision should optimize for WCAG 2.1 AA compliance (combobox role, listbox, keyboard navigation)

### Search and discovery UX
- Search box + state filter dropdown -- two discovery paths
- Fuzzy search powered by Fuse.js, ranked dropdown list showing top 10-15 matches by score
- Search matches across official EPA names AND aliases from `data/tribal_aliases.json` (18,776 entries including self-designation names like Apsaalooke, Sicangu Wicoti)
- State dropdown: selecting a state displays all Tribes in that state as a browsable list below the search
- Tribes without generated documents still appear in search with a "coming soon" disabled state

### Document presentation
- Per-Tribe card: Doc A ("Internal Strategy (Confidential)") + Doc B ("Congressional Overview") + "Download Both" button
- Regional section: separate area with region selector for Doc C + Doc D downloads
- Regional document UX: Claude's discretion on dropdown vs. card-list pattern
- Descriptive download filenames: `Navajo_Nation_Internal_Strategy.docx`, `Navajo_Nation_Congressional_Overview.docx` (sanitized for filesystem safety)
- Data freshness badges: Green (<7 days), Yellow (7-30 days), Red (>30 days) based on packet generation date
- Missing documents: card appears with disabled buttons and "Documents are being prepared. Check back soon." message

### Visual design
- Polish existing design -- refine spacing, typography, subtle improvements. Don't reinvent
- CSS scan-line / CRT effect over full page background at very low opacity (decorative)
- No canvas particle system -- remove particle JS entirely
- Minimal transitions: fade-in for search results and card appearance, respects `prefers-reduced-motion`
- Auto dark mode via `prefers-color-scheme` media query (no manual toggle)
- Always show header and footer, even when embedded in SquareSpace iframe

### Claude's Discretion
- Awesomplete replacement vs. Fuse.js layering decision (optimize for WCAG 2.1 AA)
- Regional documents layout (dropdown selector vs. visible card list)
- Exact dark mode color palette (derive from existing CSS variables)
- Scan-line opacity and animation timing
- Freshness badge placement within the tribe card
- State dropdown positioning and styling relative to search box

</decisions>

<specifics>
## Specific Ideas

- "The scrolling TV-like pattern is cool, but the little particles can go" -- keep CRT scan-line CSS effect, remove canvas particle system
- Search should leverage existing `data/tribal_aliases.json` (18,776 aliases) for matching alternate/self-designation names
- Current site structure (search -> card -> download buttons) works well -- enhance rather than redesign
- Download buttons already have good color coding: green for internal, blue for congressional, purple for both
- Regional documents section already exists in current HTML -- extend it for Doc C/D with region selection

</specifics>

<deferred>
## Deferred Ideas

None -- discussion stayed within phase scope

</deferred>

---

*Phase: 17-website-deployment*
*Context gathered: 2026-02-12*
