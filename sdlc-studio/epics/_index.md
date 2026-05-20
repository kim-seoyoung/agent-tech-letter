# Epic Registry

**Last Updated:** 2026-05-19
**PRD Reference:** [PRD v0.4.0](../prd.md)
**TRD Reference:** [TRD v0.3.0](../trd.md)

## Summary

| Status | Count |
|--------|-------|
| Draft | 4 |
| Ready | 0 |
| Approved | 0 |
| In Progress | 0 |
| Done | 0 |
| **Total** | **4** |

## Epics

| ID | Title | Status | Owner | Stories (est.) | PRD Features |
|----|-------|--------|-------|----------------|--------------|
| [EP0001](EP0001-content-ingestion.md) | Content Ingestion | Draft | HYL | 5 | F-01 |
| [EP0002](EP0002-composition-pipeline.md) | Composition Pipeline | Draft | HYL | 6 | F-02, F-03 |
| [EP0003](EP0003-orchestration-and-dx.md) | Orchestration & Developer Experience | Draft | HYL | 6 | F-04, F-09, F-10, F-11 |
| [EP0004](EP0004-multichannel-delivery.md) | Multi-channel Delivery | Draft | HYL | 5 | F-05, F-06, F-07, F-08 |

**Total estimated stories:** ~22

## Dependency Graph

```
EP0001 (Ingestion) ─┬─► EP0002 (Composition) ─┐
                    │                          │
                    └──────────────────────────┴─► EP0003 (Orchestration)
                                                      ▲
                    ┌─► EP0004 (Delivery) ─────────────┘
                    │
EP0001 ─────────────┘
EP0002 ─────────────► EP0004
```

**Suggested implementation order:**
1. **EP0001** (Ingestion) — foundational; produces `Item`s for everything downstream.
2. **EP0002** (Composition) — consumes `Item`s, produces `RenderedIssue`s.
3. **EP0004** (Delivery) — consumes `RenderedIssue`s. Can begin in parallel with EP0002 once `RenderedIssue` model is defined.
4. **EP0003** (Orchestration) — wires the above into the CLI + GitHub Actions workflows. Has internal dependencies on stable models from EP0001/02/04.

## Feature → Epic Mapping

| PRD Feature | Epic |
|-------------|------|
| F-01 Multi-source ingestion | EP0001 |
| F-02 LLM topic clustering & ranking | EP0002 |
| F-03 Issue composer (3 + 10) | EP0002 |
| F-04 Draft-as-PR approval gate | EP0003 |
| F-05 Email delivery (SMTP) | EP0004 |
| F-06 Slack delivery | EP0004 |
| F-07 Telegram delivery | EP0004 |
| F-08 Subscriber config (static) | EP0004 |
| F-09 Scheduled execution | EP0003 |
| F-10 Send log / audit trail | EP0003 |
| F-11 Local dry-run | EP0003 |

## Notes

- All four epics inherit the same audience scope (single-tier research-aware engineer per PRD v0.4.0 / ADR-008).
- EP0001 and EP0004 both use the adapter pattern (TRD ADR-002) — source-side and delivery-side respectively. They are structurally symmetric.
- EP0002 is the highest-uncertainty epic (LLM prompt iteration); EP0001 / EP0004 are mostly mechanical.
- EP0003 has the largest GitHub Actions surface area — secrets, permissions, merge predicates, concurrency groups all live here.
