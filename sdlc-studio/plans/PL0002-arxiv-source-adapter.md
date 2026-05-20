# PL0002: arXiv source adapter — Implementation Plan

> **Status:** Done
> **Story:** [US0002](../stories/US0002-arxiv-source-adapter.md)
> **Epic:** [EP0001: Content Ingestion](../epics/EP0001-content-ingestion.md)
> **Test Spec:** [TS0006](../test-specs/TS0006-arxiv-source-adapter.md) → TS0001 TC0012–TC0021
> **Created:** 2026-05-20
> **Approach:** TDD

## Approach

TDD. Story has 6 ACs, 10 edge cases, 10 test scenarios — all concrete. arXiv lib does most of the work. Test-first is mechanical.

## Implementation Tasks

| # | Task                                                                    | File                                       | Status |
| - | ----------------------------------------------------------------------- | ------------------------------------------ | ------ |
| 1 | Add `arxiv>=2.1` and `tenacity>=9` to `pyproject.toml` deps             | `pyproject.toml`                           | [x]    |
| 2 | Write failing tests for ArxivAdapter (TC0012–TC0021)                    | `tests/unit/sources/test_arxiv.py`         | [x]    |
| 3 | Implement `ArxivAdapter(categories, keywords)`                          | `techletter/sources/arxiv.py`              | [x]    |
| 4 | Wire tenacity retry decorator (max 5, exp backoff with jitter)          | `techletter/sources/arxiv.py`              | [x]    |
| 5 | Window filter (clamp to 365; ValueError on negative)                    | `techletter/sources/arxiv.py`              | [x]    |
| 6 | Keyword filter (case-insensitive title + abstract)                      | `techletter/sources/arxiv.py`              | [x]    |
| 7 | Map arXiv `entry_id` → `Item.url`, abstract → `summary_excerpt` (≤1000) | `techletter/sources/arxiv.py`              | [x]    |
| 8 | Run `uv sync`, `pytest`, `pyright`, `ruff` — all green                  | n/a                                        | [x]    |

## AC Coverage

| AC  | Test Scenarios                                            |
| --- | --------------------------------------------------------- |
| AC1 | Adapter conformance (`name="arxiv"`, pyright)             |
| AC2 | Fixture: 7 in window from cs.AI/cs.CL → returned 7; `source_subtype` per category |
| AC3 | Keyword filter: 3 match, 2 don't → 3 returned             |
| AC4 | Empty result → `[]`, no exception                         |
| AC5 | 503×2 then 200 → tenacity retries succeed                 |
| AC6 | 503×5 → `SourceFetchError`, caught at registry level      |

## Risks

- arXiv library API surface may have changed between versions — pin minor in pyproject.
- VCR cassette recording requires network; if offline, agent uses `pytest-httpx`-style mocks per TS0001.

## Revision History

| Date       | Author | Change                                                      |
| ---------- | ------ | ----------------------------------------------------------- |
| 2026-05-20 | Claude | Initial lightweight plan for Wave 2 agentic execution.      |
