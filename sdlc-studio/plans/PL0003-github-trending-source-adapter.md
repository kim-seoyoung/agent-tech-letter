# PL0003: GitHub Trending source adapter — Implementation Plan

> **Status:** Done
> **Story:** [US0003](../stories/US0003-github-trending-source-adapter.md)
> **Epic:** [EP0001: Content Ingestion](../epics/EP0001-content-ingestion.md)
> **Test Spec:** [TS0008](../test-specs/TS0008-github-trending-source-adapter.md) → TS0001 TC0022–TC0036
> **Created:** 2026-05-20
> **Approach:** TDD

## Approach

TDD. Most complex story in EP0001 (5 pts). HTML scrape + REST enrichment + maturity inference. The maturity rules are deterministic so test-first is straightforward. Scrape selectors are fragile but failure mode is well-specified ("fail soft → return []").

## Implementation Tasks

| # | Task                                                                          | File                                     | Status |
| - | ----------------------------------------------------------------------------- | ---------------------------------------- | ------ |
| 1 | Write failing tests for GitHubTrendingAdapter (TC0022–TC0036)                 | `tests/unit/sources/test_github.py`      | [x]    |
| 2 | Implement `parse_trending_html(html: bytes) -> list[RepoStub]`                | `techletter/sources/github.py`           | [x]    |
| 3 | Implement REST enrichment: `_enrich(owner, name) -> dict`                     | `techletter/sources/github.py`           | [x]    |
| 4 | Implement `infer_maturity(metadata) -> Maturity`                              | `techletter/sources/github.py`           | [x]    |
| 5 | Implement `GitHubTrendingAdapter.fetch(window_days)`                          | `techletter/sources/github.py`           | [x]    |
| 6 | Wire tenacity on both scrape + REST calls                                     | `techletter/sources/github.py`           | [x]    |
| 7 | Run `pytest`, `pyright`, `ruff` — all green                                   | n/a                                      | [x]    |

## AC Coverage

| AC  | Test Scenarios                                                       |
| --- | -------------------------------------------------------------------- |
| AC1 | Adapter conformance (`name="github"`, pyright)                       |
| AC2 | 25-repo trending HTML fixture → 25 items                             |
| AC3 | REST enrichment populates `raw.stars/last_commit_at/has_recent_release/hosted_demo_url` |
| AC4 | `infer_maturity` parametric: 4 cases (production-ready/beta/experimental/unknown) |
| AC5 | Scrape 404 → returns `[]`, warning logged, NO exception              |
| AC6 | `GITHUB_TOKEN` env → Authorization header sent                       |
| AC7 | Per-repo 404 → skipped with warning; other 24 returned               |

## Risks

- HTML selectors may differ from documented; tests use fixture HTML that I author from inspection.
- GitHub REST API has stable v3 contract; safe to mock.
- `selectolax` API surface is small; if it changes between versions, parse logic updates here only.

## Revision History

| Date       | Author | Change                                                       |
| ---------- | ------ | ------------------------------------------------------------ |
| 2026-05-20 | Claude | Initial plan for Wave 3 execution.                           |
