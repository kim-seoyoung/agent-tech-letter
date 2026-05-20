# TS0009: Source registry + config loader — Story Test Spec

> **Status:** Done
> **Story:** [US0005](../stories/US0005-source-registry-and-config-loader.md)
> **Plan:** [PL0005](../plans/PL0005-source-registry-and-config-loader.md)
> **Canonical TCs:** [TS0001](TS0001-content-ingestion.md) TC0047–TC0055

## AC Coverage

| AC  | TCs                | Status  |
| --- | ------------------ | ------- |
| AC1 | TC0047, TC0048     | Done    |
| AC2 | TC0049             | Done    |
| AC3 | TC0050             | Done    |
| AC4 | TC0051             | Done    |
| AC5 | TC0052             | Done    |
| AC6 | TC0053             | Done    |
| AC7 | TC0054, TC0055     | Done    |

**Coverage:** 7/7 ACs covered by 9 TCs.

## Test Files

- `tests/unit/config/test_sources.py` — pydantic schema + load_sources tests
- `tests/unit/sources/test_registry.py` — build_registry + fetch_all tests

## Revision History

| Date       | Author | Change                                                        |
| ---------- | ------ | ------------------------------------------------------------- |
| 2026-05-20 | Claude | Initial story-scoped TS for US0005.                            |
