# TS0008: GitHub Trending source adapter — Story Test Spec

> **Status:** Done
> **Story:** [US0003](../stories/US0003-github-trending-source-adapter.md)
> **Plan:** [PL0003](../plans/PL0003-github-trending-source-adapter.md)
> **Canonical TCs:** [TS0001](TS0001-content-ingestion.md) TC0022–TC0036

## AC Coverage

| AC  | TCs                | Status  |
| --- | ------------------ | ------- |
| AC1 | TC0022             | Done    |
| AC2 | TC0023, TC0024     | Done    |
| AC3 | TC0025             | Done    |
| AC4 | TC0026 (parametric)| Done    |
| AC5 | TC0027             | Done    |
| AC6 | TC0028             | Done    |
| AC7 | TC0029             | Done    |

**Coverage:** 7/7 ACs covered by 15 TCs (incl. parametric expansions).

## Test Files

- `tests/unit/sources/test_github.py` — fixture HTML inlined; REST API mocked via injected `rest_client` callable.

## Revision History

| Date       | Author | Change                                                       |
| ---------- | ------ | ------------------------------------------------------------ |
| 2026-05-20 | Claude | Initial story-scoped TS for US0003.                           |
