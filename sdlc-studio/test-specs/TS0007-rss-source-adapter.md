# TS0007: RSS source adapter — Story Test Spec

> **Status:** Done
> **Story:** [US0004](../stories/US0004-rss-source-adapter.md)
> **Plan:** [PL0004](../plans/PL0004-rss-source-adapter.md)
> **Canonical TCs:** [TS0001](TS0001-content-ingestion.md) TC0037–TC0046

## AC Coverage

| AC  | TCs                | Status  |
| --- | ------------------ | ------- |
| AC1 | TC0037             | Done    |
| AC2 | TC0038             | Done    |
| AC3 | TC0039             | Done    |
| AC4 | TC0040, TC0041     | Done    |
| AC5 | TC0042, TC0043     | Done    |
| AC6 | TC0044, TC0045, TC0046 | Done    |

**Coverage:** 6/6 ACs covered by 10 TCs.

## Test Files

- `tests/unit/sources/test_rss.py` — fixture RSS/Atom payloads inlined; `pytest-httpx` mocks the HTTP fetch.

## Revision History

| Date       | Author | Change                                                                 |
| ---------- | ------ | ---------------------------------------------------------------------- |
| 2026-05-20 | Claude | Initial story-scoped TS for US0004. Indexes TS0001 TC0037–TC0046.       |
