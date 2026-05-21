# Change Request Registry

**Last Updated:** 2026-05-21
**PRD Reference:** [PRD v0.4.0](../prd.md)

## Summary

| Status | Count |
|--------|-------|
| Proposed | 1 |
| Approved | 0 |
| In Progress | 1 |
| Complete | 0 |
| Rejected | 0 |
| Deferred | 0 |
| **Total** | **2** |

## By Priority

| Priority | Count |
|----------|-------|
| P1 | 0 |
| P2 | 2 |
| P3 | 0 |
| P4 | 0 |

## Change Requests

| ID | Title | Priority | Status | Type | Date | Affects |
|----|-------|----------|--------|------|------|---------|
| [CR-0001](CR0001-common-html-rendering.md) | Common HTML Rendering (Web + Email) | P2 | In Progress | feature-request | 2026-05-21 | F-05 (+ enables CR-0002) |
| [CR-0002](CR0002-github-pages-and-telegram-link-mode.md) | GitHub Pages Publisher + Telegram Link Mode | P2 | Proposed | feature-request | 2026-05-21 | F-07 (+ new web archive capability) |

## Actioned CRs → Epics

| CR | Linked Epic | Stories |
|----|-------------|---------|
| CR-0001 | [EP0005](../epics/EP0005-common-html-rendering.md) (Draft) | US0023–US0027 (5 stories, 16 pts) |

## Dependencies

| CR | Depends On | Required Before |
|----|------------|-----------------|
| CR-0002 | CR-0001 | Implementation start (needs `html_web` renderer + sidecar JSON) |

## Notes

- v1.0 shipped on 2026-05-19 with EP0001–EP0004 (PRD v0.4.0 features F-01–F-11). These CRs are post-launch enhancements.
- CR-0001 unblocks CR-0002; do not action CR-0002 before CR-0001 is at least Approved.
- Draft epic content for both CRs is preserved at `sdlc-studio/.local/draft-epic-content/` to seed the `/sdlc-studio cr action` step (the generated epics should track those drafts closely, but `cr action` is authoritative).
