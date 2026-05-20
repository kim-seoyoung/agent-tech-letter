# PL0004: RSS source adapter — Implementation Plan

> **Status:** Done
> **Story:** [US0004](../stories/US0004-rss-source-adapter.md)
> **Epic:** [EP0001: Content Ingestion](../epics/EP0001-content-ingestion.md)
> **Test Spec:** [TS0007](../test-specs/TS0007-rss-source-adapter.md) → TS0001 TC0037–TC0046
> **Created:** 2026-05-20
> **Approach:** TDD

## Approach

TDD. Story has 6 ACs, 12 edge cases, 10 test scenarios. `feedparser` does the parsing; the value-add is per-feed error isolation + window filter + tz conversion. Test-first is straightforward.

## Implementation Tasks

| # | Task                                                                    | File                                       | Status |
| - | ----------------------------------------------------------------------- | ------------------------------------------ | ------ |
| 1 | Add `feedparser>=6.0` and `httpx>=0.27` to `pyproject.toml` deps        | `pyproject.toml`                           | [x]    |
| 2 | Write failing tests for RssAdapter (TC0037–TC0046)                      | `tests/unit/sources/test_rss.py`           | [x]    |
| 3 | Implement `RssAdapter(feeds: list[str])`                                | `techletter/sources/rss.py`                | [x]    |
| 4 | Per-feed try/except + tenacity wrap around `httpx.get`                  | `techletter/sources/rss.py`                | [x]    |
| 5 | Convert `entry.published_parsed` (struct_time) → tz-aware datetime UTC  | `techletter/sources/rss.py`                | [x]    |
| 6 | Window filter (`published_at` within last N days)                       | `techletter/sources/rss.py`                | [x]    |
| 7 | Tolerate `bozo` flag; skip items missing `published`                    | `techletter/sources/rss.py`                | [x]    |
| 8 | Run `uv sync`, `pytest`, `pyright`, `ruff` — all green                  | n/a                                        | [x]    |

## AC Coverage

| AC  | Test Scenarios                                                                |
| --- | ----------------------------------------------------------------------------- |
| AC1 | Adapter conformance (`name="rss"`, pyright)                                   |
| AC2 | 3 feeds × items → aggregated; `source_subtype` = feed URL                     |
| AC3 | 10 items / 30 days, window=7 → 7 returned                                     |
| AC4 | 3 feeds, feed #2 500×5 → items from #1+#3, no raise                           |
| AC5 | Malformed XML (bozo) → valid items returned with warning                      |
| AC6 | Items missing `published` → skipped with log                                  |

## Risks

- `feedparser.parse(url)` does its own HTTP; we wrap `httpx.get()` then pass body to `feedparser.parse(text)` for tenacity-controllable retries.
- `published_parsed` is a `time.struct_time`; conversion to `datetime` needs explicit `tzinfo=UTC` assignment.

## Revision History

| Date       | Author | Change                                                      |
| ---------- | ------ | ----------------------------------------------------------- |
| 2026-05-20 | Claude | Initial lightweight plan for Wave 2 agentic execution.      |
