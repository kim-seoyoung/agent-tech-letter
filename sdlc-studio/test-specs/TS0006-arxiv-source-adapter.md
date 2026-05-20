# TS0006: arXiv source adapter — Story Test Spec

> **Status:** Done
> **Story:** [US0002](../stories/US0002-arxiv-source-adapter.md)
> **Plan:** [PL0002](../plans/PL0002-arxiv-source-adapter.md)
> **Canonical TCs:** [TS0001](TS0001-content-ingestion.md) TC0012–TC0021

## AC Coverage

| AC  | TCs                | Status  |
| --- | ------------------ | ------- |
| AC1 | TC0012             | Done    |
| AC2 | TC0013, TC0014     | Done    |
| AC3 | TC0015, TC0016     | Done    |
| AC4 | TC0017             | Done    |
| AC5 | TC0018             | Done    |
| AC6 | TC0019, TC0020, TC0021 | Done    |

**Coverage:** 6/6 ACs covered by 10 TCs.

## Test Files

- `tests/unit/sources/test_arxiv.py` — unit/integration tests with `pytest-httpx` for failure injection
- Fixtures: inline-constructed arXiv response payloads (XML strings). VCR cassettes for happy-path are recorded on first run if network is available; otherwise the agent uses pytest-httpx mocks.

## Revision History

| Date       | Author | Change                                                                 |
| ---------- | ------ | ---------------------------------------------------------------------- |
| 2026-05-20 | Claude | Initial story-scoped TS for US0002. Indexes TS0001 TC0012–TC0021.       |
