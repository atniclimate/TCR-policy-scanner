# Dale Gribble Security and Data Sovereignty Audit Summary

## Agent: Dale Gribble
**Date:** 2026-02-13
**Scope:** Full system -- website (docs/web/), deployment (.github/workflows/), scrapers (src/scrapers/), CSP headers, third-party tracking, data sovereignty

## Methodology

Three simultaneous perspectives: (1) The Attacker -- how to exploit for Tribal data access, (2) The Auditor -- does the system comply with Indigenous Data Sovereignty principles, (3) The Paranoid User -- what data leaks when I use this website.

## Key Findings

### DALE-001 (Important): No SRI hash on Fuse.js
The bundled fuse.min.js has no Subresource Integrity hash. While locally hosted (good), a supply chain compromise during CI/CD could tamper with the file undetected.

### DALE-002 (Important): Manifest enables advocacy monitoring
The publicly accessible manifest.json and tribes.json allow anyone to enumerate all 592 Tribal advocacy packets and monitor deployment timing. Inherent to T0 classification and static hosting.

### DALE-004 (Cosmetic): No Content-Security-Policy
GitHub Pages does not support custom HTTP headers, but a meta CSP tag could be added for defense-in-depth.

## Findings by Severity

| Severity | Count | Finding IDs |
|----------|-------|-------------|
| Critical | 0 | -- |
| Important | 2 | DALE-001, DALE-002 |
| Cosmetic | 16 | DALE-003 through DALE-018 |

## Checklist Coverage

All 18 checklist items inspected:

1. HTTPS/CSP: HTTPS enforced by GitHub Pages; no CSP but meta tag possible (DALE-004, DALE-013)
2. Manifest enumeration: Public manifest + tribes.json enables tracking (DALE-002)
3. Referrer leakage: SquareSpace iframe sandbox correctly configured (DALE-007)
4. Analytics/tracking: ZERO -- fully clean (DALE-006)
5. TSDF enforcement: Pipeline-level, not displayed to users (DALE-011)
6. URL manipulation: GitHub Pages normalizes paths, prevents traversal (DALE-010)
7. CDN dependencies: Fuse.js bundled locally, no external CDN (DALE-001)
8. JavaScript disabled: noscript fallback added, no alternative path (DALE-012)
9. GitHub API rate limits: Not applicable -- static file serving, no API calls from client
10. PII in URLs: None -- EPA IDs only (DALE-014)
11. MITM: Prevented by GitHub Pages TLS (DALE-013)
12. Google Fonts: Not used -- system fonts only (DALE-018)
13. Cookies: Zero (DALE-017)
14. IP exposure: Standard for any web hosting (DALE-003)
15. SquareSpace plugin access: Prevented by same-origin policy (DALE-007)
16. SRI: Missing on fuse.min.js (DALE-001)
17. Hardcoded secrets: None found -- GitHub Secrets used correctly (DALE-008)
18. Source maps: None present -- no build step (DALE-009)

## Data Sovereignty Assessment

The system substantially honors Indigenous Data Sovereignty. Zero tracking, system fonts, no cookies, no client storage, T0 data by design. The gaps (no visible TSDF statement, GitHub access logs, manifest exposure) are inherent to static hosting and do not violate UNDRIP, OCAP, or CARE for T0 data.

## Third-Party Inventory

| Domain | Purpose | Client/Server | Auth |
|--------|---------|---------------|------|
| github.com | Hosting, CI/CD | Both | No (public) |
| api.congress.gov | Legislative data | Server only | API key |
| api.usaspending.gov | Spending data | Server only | None |
| www.grants.gov | Grant opportunities | Server only | None |
| www.federalregister.gov | Policy documents | Server only | None |

**That's what they WANT you to think... but actually, this site is clean. Sh-sh-sha!**
