# Test Specs Index

> Registry of test specifications for Tech-Letter for HYL. Each spec covers one epic.

## Project Targets (from [TSD](../tsd.md))

| Level | Target |
|-------|--------|
| Unit (overall) | ≥85% line coverage |
| Unit (pure helpers — `models/`, `parsers/`, `splitters/`, `converters/`) | ≥95% line + branch |
| Integration | 100% pass on every PR |
| Pipeline E2E | 100% pass on every PR (single `tests/pipeline/test_full_run.py`) |
| Smoke send | 1 successful real send to HYL's own channels per draft |

## Specs

| ID | Title | Epic | Stories Covered | TC Range | Status |
|----|-------|------|-----------------|----------|--------|
| [TS0001](TS0001-content-ingestion.md) | Content Ingestion | [EP0001](../epics/EP0001-content-ingestion.md) | US0001–US0005 | TC0001–TC0055 | **Ready** |
| [TS0002](TS0002-composition-pipeline.md) | Composition Pipeline | [EP0002](../epics/EP0002-composition-pipeline.md) | US0006–US0011 | TC0056–TC0125 | **Ready** |
| [TS0003](TS0003-orchestration-and-dx.md) | Orchestration & DX | [EP0003](../epics/EP0003-orchestration-and-dx.md) | US0012–US0017 | TC0126–TC0197 | **Ready** |
| [TS0004](TS0004-multichannel-delivery.md) | Multichannel Delivery | [EP0004](../epics/EP0004-multichannel-delivery.md) | US0018–US0022 | TC0198–TC0260 | **Ready** |
| [TS0005](TS0005-item-model-and-source-adapter-protocol.md) | _Story view:_ `Item` + `SourceAdapter` protocol | [EP0001](../epics/EP0001-content-ingestion.md) | US0001 only | indexes TC0001–TC0011 (canonical in TS0001) | **Done** |
| [TS0006](TS0006-arxiv-source-adapter.md) | _Story view:_ arXiv source adapter | [EP0001](../epics/EP0001-content-ingestion.md) | US0002 only | indexes TC0012–TC0021 (canonical in TS0001) | **Done** |
| [TS0007](TS0007-rss-source-adapter.md) | _Story view:_ RSS source adapter | [EP0001](../epics/EP0001-content-ingestion.md) | US0004 only | indexes TC0037–TC0046 (canonical in TS0001) | **Done** |
| [TS0008](TS0008-github-trending-source-adapter.md) | _Story view:_ GitHub Trending source adapter | [EP0001](../epics/EP0001-content-ingestion.md) | US0003 only | indexes TC0022–TC0036 (canonical in TS0001) | **Done** |
| [TS0009](TS0009-source-registry-and-config-loader.md) | _Story view:_ Source registry + config loader | [EP0001](../epics/EP0001-content-ingestion.md) | US0005 only | indexes TC0047–TC0055 (canonical in TS0001) | **Done** |

## Statistics

| Metric | Value |
|--------|-------|
| Specs created | **4 / 4** ✅ |
| Test cases defined | **260** |
| ACs covered | **157 / 157** (all 4 epics — full coverage) |
| Specs in Ready status | **4 / 4** ✅ (all specs reviewed 2026-05-19) |
| Automation status | All Pending (no code yet) |

## TC Numbering

Test Case IDs are globally sequential across all specs. The next available TC is **TC0261**.

## Generated

- 2026-05-19 — TS0001 via `/sdlc-studio test-spec --epic EP0001`.
- 2026-05-19 — TS0002 via `/sdlc-studio test-spec --epic EP0002`.
- 2026-05-19 — TS0003 via `/sdlc-studio test-spec --epic EP0003`.
- 2026-05-19 — TS0004 via `/sdlc-studio test-spec --epic EP0004`. **Spec set complete.**
- 2026-05-19 — All four specs reviewed via `/sdlc-studio test-spec review` and promoted Draft → Ready. Implementation-time follow-ups recorded in each spec's revision history. |
