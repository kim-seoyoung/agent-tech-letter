# PL0001: `Item` model + `SourceAdapter` protocol — Implementation Plan

> **Status:** Draft
> **Story:** [US0001: `Item` model + `SourceAdapter` protocol](../stories/US0001-item-model-and-source-adapter-protocol.md)
> **Epic:** [EP0001: Content Ingestion](../epics/EP0001-content-ingestion.md)
> **Test Spec:** [TS0005](../test-specs/TS0005-item-model-and-source-adapter-protocol.md) (story view) → canonical TCs in [TS0001](../test-specs/TS0001-content-ingestion.md) TC0001–TC0011
> **Created:** 2026-05-20
> **Last Updated:** 2026-05-20
> **Language:** Python 3.11+
> **Approach:** TDD

## Overview

Foundation story for EP0001. This plan bundles three concerns into a single PR:

1. **Project scaffolding** — uv-managed Python project, ruff + pyright + pytest config, initial package tree. The epic flags scaffolding as "Blocked By: Not started"; absorbing it into PL0001's first task keeps every line of code traceable to a story rather than landing as an untraced infrastructure commit.
2. **The `Item` pydantic v2 model** with all 10 fields (5 required + 5 optional/defaulted), `frozen=True`, tz-aware `published_at` validator, and 1000-char cap on `summary_excerpt`.
3. **The `SourceAdapter` typing.Protocol** (structural, not ABC), plus `SourceFetchError` and the `Maturity` Literal alias — both absorbed from downstream story scope so US0002, US0003, US0005 can `from techletter.sources.base import SourceFetchError` cleanly when they land in later waves (per `reference-agentic-lessons.md` — pre-empts the Wave-2 hub conflict the epic-plan flagged).

## Acceptance Criteria Summary

| AC  | Name                                  | Description                                                                                       |
| --- | ------------------------------------- | ------------------------------------------------------------------------------------------------- |
| AC1 | `Item` model defined and importable   | pydantic v2 BaseModel with 10 fields, frozen config, fields validated per Literal/HttpUrl/length  |
| AC2 | `SourceAdapter` protocol defined      | `typing.Protocol` with `name: str` and `fetch(window_days: int) -> list[Item]`                    |
| AC3 | Trivial test adapter implements it    | pyright accepts a `FakeAdapter` (`name="fake"`, hardcoded `fetch`) as `SourceAdapter`             |
| AC4 | Validation rejects malformed items    | Missing required fields → `ValidationError`; identical for each required field                    |
| AC5 | tz-naive datetimes rejected           | `published_at` without tzinfo → `ValidationError` with tz-awareness message                       |

---

## Technical Context

### Language & Framework

- **Primary Language:** Python 3.11+ (TRD ADR-006)
- **Build & deps:** `uv` (TRD ADR-006)
- **Lint/format:** `ruff` (TRD ADR-006)
- **Typecheck:** `pyright` strict-on-typed (TRD ADR-006)
- **Test:** `pytest` + `hypothesis` (TSD; this story uses TC0011 hypothesis round-trip)

### Library Documentation

| Library | Key Patterns | Notes |
|---------|--------------|-------|
| `pydantic` v2 | `BaseModel`, `ConfigDict(frozen=True)`, `HttpUrl`, `field_validator` | The `frozen=True` form is `model_config = ConfigDict(frozen=True)` (NOT class-level `Config`) |
| `typing.Protocol` | Structural typing; concrete classes do NOT inherit | Pyright checks conformance at static-analysis time |
| `hypothesis` | `@given(strategies)`, `@settings(max_examples=200, deadline=None)` | Use for TC0011 Item round-trip; deadline=None on macOS to avoid CI flake |

### Existing Patterns

This is the first code file in the repo — no patterns exist yet. PL0001 establishes them.
**Codebase patterns the agent must read first:**
- `sdlc-studio/trd.md` §6 Data Models (Item field set, types) — canonical source of truth
- `sdlc-studio/stories/US0001-*.md` (full AC, edge cases)
- `sdlc-studio/test-specs/TS0001-*.md` TC0001–TC0011 (test definitions to satisfy)

---

## Recommended Approach: TDD

**Rationale:**
- 5 AC blocks all with concrete Given/When/Then values → easy to encode as failing tests upfront.
- 8 edge cases all expressed as ValidationError outcomes → mechanical to test-first.
- Library code (no UI, no exploratory design) → deterministic, low risk of test churn.
- TS0001 already enumerates TC0001–TC0011 verbatim → 80% of the test content is pre-authored.

### Test Priority (write & fail in this order)

1. TC0001 — Item construct + field set verification (anchors AC1)
2. TC0005 — tz-naive datetime rejected (anchors AC5; load-bearing for downstream adapters)
3. TC0010 — frozen Item mutation raises (anchors immutability invariant)
4. TC0011 — hypothesis round-trip (anchors AC1 + serialisation contract)

---

## Implementation Tasks

| #  | Task                                                                         | File                                                          | Depends On | Status |
| -- | ---------------------------------------------------------------------------- | ------------------------------------------------------------- | ---------- | ------ |
| 1  | Initialise uv project, write `pyproject.toml` (deps + dev-deps + ruff + pytest config) | `pyproject.toml`                                              | —          | [ ]    |
| 2  | Add `pyrightconfig.json` with strict mode for `techletter/`                  | `pyrightconfig.json`                                          | 1          | [ ]    |
| 3  | Create package skeleton (empty `__init__.py` files)                          | `techletter/`, `techletter/models/`, `techletter/sources/`, `tests/`, `tests/unit/`, `tests/unit/models/`, `tests/unit/sources/` | 1 | [ ]    |
| 4  | Pin Python version                                                           | `.python-version` (3.11)                                      | 1          | [ ]    |
| 5  | **TDD:** Write `tests/unit/models/test_item.py` covering TC0001–TC0011       | `tests/unit/models/test_item.py`                              | 3          | [ ]    |
| 6  | **TDD:** Write `tests/unit/sources/test_base.py` covering protocol + `SourceFetchError` | `tests/unit/sources/test_base.py`                             | 3          | [ ]    |
| 7  | Run pytest → confirm all tests fail (red phase)                              | n/a                                                           | 5, 6       | [ ]    |
| 8  | Define `Maturity` Literal alias                                              | `techletter/models/__init__.py`                               | 3          | [ ]    |
| 9  | Define `Item` pydantic model (10 fields, `frozen=True`)                      | `techletter/models/__init__.py`                               | 8          | [ ]    |
| 10 | Add `published_at` tz-aware `field_validator`                                | `techletter/models/__init__.py`                               | 9          | [ ]    |
| 11 | Define `SourceAdapter` typing.Protocol                                       | `techletter/sources/base.py`                                  | 3          | [ ]    |
| 12 | Define `SourceFetchError(Exception)`                                         | `techletter/sources/base.py`                                  | 11         | [ ]    |
| 13 | Run `uv run pytest -q` → confirm green                                       | n/a                                                           | 5–12       | [ ]    |
| 14 | Run `uv run pyright techletter/ tests/` → zero errors                        | n/a                                                           | 9–12       | [ ]    |
| 15 | Run `uv run ruff check . && uv run ruff format --check .`                    | n/a                                                           | 9–12       | [ ]    |
| 16 | Update `README.md` quickstart stub (will be expanded by US0017)              | `README.md`                                                   | 1          | [ ]    |

### Parallel Execution Groups (within this story)

| Group | Tasks            | Prerequisite | Notes |
|-------|------------------|--------------|-------|
| Setup | 1, 2, 3, 4       | —            | Sequential; each unblocks the next |
| Red   | 5 ‖ 6 → 7        | 3            | Tests for models and sources are independent files; can be drafted concurrently |
| Green | 8 → 9 → 10  ‖  11 → 12 | 7 (red confirmed) | models and sources implementation are independent |
| Verify | 13, 14, 15       | 8–12         | All three quality gates run in parallel via `uv run` |

---

## Implementation Phases

### Phase 1: Scaffold (Tasks 1–4)

**Goal:** Working uv environment with ruff/pyright/pytest configured and an empty package tree.

- [ ] `uv init --python 3.11` (or manual `pyproject.toml` if uv version locks differ)
- [ ] Add deps to `pyproject.toml`: `pydantic>=2.6,<3`
- [ ] Add dev-deps: `pytest>=8`, `pytest-cov`, `hypothesis>=6`, `ruff>=0.4`, `pyright>=1.1.350`
- [ ] Write `[tool.ruff]` config (line-length 100, `select = ["E","F","I","UP","B","SIM","RUF"]`)
- [ ] Write `[tool.pytest.ini_options]` with `testpaths = ["tests"]`, `addopts = "-q --strict-markers"`
- [ ] Write `pyrightconfig.json` with `"strict": ["techletter"]`
- [ ] Create empty `__init__.py` in 7 directories per Task 3
- [ ] `.python-version` containing `3.11`

**Files:** `pyproject.toml`, `pyrightconfig.json`, 7× `__init__.py`, `.python-version`

### Phase 2: Red (Tasks 5–7)

**Goal:** All TC0001–TC0011 tests written and failing.

- [ ] `tests/unit/models/test_item.py` — 11 tests mirroring TS0001 TC0001–TC0011 verbatim
- [ ] `tests/unit/sources/test_base.py` — Protocol-conformance tests using `FakeAdapter` fixture + `SourceFetchError` smoke test
- [ ] `uv run pytest -q` should show: 13 errors (ImportError for `techletter.models.Item`, `techletter.sources.base.SourceAdapter`, etc.)

### Phase 3: Green (Tasks 8–12)

**Goal:** Minimal code to flip every test from red to green.

- [ ] `techletter/models/__init__.py`:
  ```python
  from datetime import datetime
  from typing import Literal
  from pydantic import BaseModel, ConfigDict, HttpUrl, field_validator

  Maturity = Literal["experimental", "beta", "production-ready", "unknown"]

  class Item(BaseModel):
      model_config = ConfigDict(frozen=True)
      source: Literal["arxiv", "github", "rss"]
      source_subtype: str | None = None
      title: str = ...        # min_length=1 enforced via field
      url: HttpUrl
      summary_excerpt: str    # max_length=1000 enforced via field
      score: float | None = None
      published_at: datetime
      item_kind: Literal["paper", "blog_post", "repo"]
      maturity: Maturity | None = None
      raw: dict

      @field_validator("published_at")
      @classmethod
      def _must_be_tz_aware(cls, v: datetime) -> datetime:
          if v.tzinfo is None:
              raise ValueError("published_at must be timezone-aware (UTC)")
          return v
  ```
  Use `Field(min_length=1)` / `Field(max_length=1000)` for `title` / `summary_excerpt`.

- [ ] `techletter/sources/base.py`:
  ```python
  from typing import Protocol
  from techletter.models import Item

  class SourceFetchError(Exception):
      """Raised when a source adapter exhausts retries on a transient/permanent failure."""

  class SourceAdapter(Protocol):
      name: str
      def fetch(self, window_days: int) -> list[Item]: ...
  ```

### Phase 4: Verify (Tasks 13–16)

**Goal:** All quality gates green; minimal README stub committed.

| AC  | Verification Method                       | File Evidence                              | Status  |
| --- | ----------------------------------------- | ------------------------------------------ | ------- |
| AC1 | TC0001, TC0011 pass                       | `tests/unit/models/test_item.py:test_*`    | Pending |
| AC2 | TC0009/Protocol-conformance test passes   | `tests/unit/sources/test_base.py`          | Pending |
| AC3 | FakeAdapter assigned to `SourceAdapter` — pyright passes | `tests/unit/sources/test_base.py` (pyright-asserted via `reveal_type` or explicit annotation) | Pending |
| AC4 | TC0002, TC0003 pass                       | `tests/unit/models/test_item.py`           | Pending |
| AC5 | TC0005 passes (tz-naive rejection)        | `tests/unit/models/test_item.py`           | Pending |

---

## Edge Case Handling

All 8 edge cases from US0001's Edge Case table:

| #  | Edge Case (from Story)                       | Handling Strategy                                                  | Phase |
| -- | -------------------------------------------- | ------------------------------------------------------------------ | ----- |
| 1  | Empty `title` string                         | `Field(min_length=1)` on `title` → pydantic raises ValidationError | 3     |
| 2  | Non-http URL (`ftp://...`)                   | `HttpUrl` field type rejects non-http(s) schemes natively          | 3     |
| 3  | `summary_excerpt` > 1000 chars               | `Field(max_length=1000)` → ValidationError                         | 3     |
| 4  | Unknown `item_kind` value                    | `Literal["paper","blog_post","repo"]` → ValidationError            | 3     |
| 5  | `maturity` outside allowed set               | `Maturity` Literal → ValidationError                               | 3     |
| 6  | Naive datetime for `published_at`            | `@field_validator` raises ValueError → wrapped as ValidationError  | 3     |
| 7  | `raw` is non-dict                            | `dict` type annotation → pydantic ValidationError                  | 3     |
| 8  | Mutation attempt on frozen Item              | `ConfigDict(frozen=True)` → pydantic ValidationError on `__setattr__` | 3     |

**Coverage:** 8/8 edge cases mapped (100%)

Additional pyright-only edge cases from story (caught at static analysis, not runtime):

| #  | Edge Case                                    | Handling Strategy                                                  |
| -- | -------------------------------------------- | ------------------------------------------------------------------ |
| 9  | Adapter declared missing `name` attribute    | `SourceAdapter` Protocol requires `name: str` → pyright flags conformance violation |
| 10 | Adapter `fetch()` returns `None`             | Protocol signature `-> list[Item]` → pyright flags return-type mismatch |

---

## Risks & Mitigations

| Risk                                                                       | Impact  | Mitigation                                                                                          |
| -------------------------------------------------------------------------- | ------- | --------------------------------------------------------------------------------------------------- |
| pydantic v2 `Field(min_length=1, max_length=1000)` syntax differs from v1  | Low     | Use the v2 form (`Annotated[str, Field(...)]`) explicitly; TC0007 will catch a wrong syntax        |
| `typing.Protocol` runtime-checkability — agent may add `@runtime_checkable` unnecessarily | Low | We do NOT need `@runtime_checkable`; pyright handles conformance at static-analysis time. Note this in the agent prompt. |
| Hypothesis test flake on slow CI (default `deadline=200ms`)                | Medium  | Set `@settings(deadline=None, max_examples=200)` on TC0011 — already documented in TS0001         |
| `uv` not installed in dev environment                                      | Low     | Phase 1 task 1 includes `uv` installation check; fall back to `pip install uv` if absent          |
| `pyright` strict mode trips on `**raw: dict` (untyped dict)                | Low     | Use `dict[str, object]` instead of bare `dict`; verify pyright accepts                            |

---

## Definition of Done

- [ ] All 5 AC verified by tests (Phase 4 evidence column)
- [ ] All 8 runtime edge cases tested + passing
- [ ] All 2 pyright-only edge cases verified by static-analysis test setup
- [ ] `uv run pytest -q` → green
- [ ] `uv run pyright techletter/ tests/` → 0 errors, 0 warnings
- [ ] `uv run ruff check . && uv run ruff format --check .` → green
- [ ] `Item` is `frozen=True` (mutation attempt raises)
- [ ] `SourceFetchError` importable from `techletter.sources.base` (pre-empts US0002 hub conflict)
- [ ] `Maturity` Literal alias importable from `techletter.models` (pre-empts US0003 hub conflict)
- [ ] `README.md` quickstart stub created (expanded later by US0017)
- [ ] `pyproject.toml`, `pyrightconfig.json`, `.python-version`, `uv.lock` committed

---

## Notes

- **Why scaffolding lives inside PL0001:** Every commit traces to a story. Scaffolding as a separate infra commit would break that invariant and create a story-less commit on `main`. Cost: PL0001 is ~16 tasks instead of ~8. Benefit: full provenance.
- **Why `SourceFetchError` and `Maturity` are absorbed here:** The `epic plan --agentic` analysis flagged these as Wave-2 hub-conflict risks. Defining them in US0001's foundation prevents three downstream stories (US0002, US0003, US0005) from racing to define them mid-wave.
- **What this plan does NOT do:** No concrete adapters (those are US0002–US0004). No registry (US0005). No CI workflow files (US0015/US0016 — EP0003).
- **Test surface:** TS0001 TC0001–TC0011 are canonical; this plan's tests mirror them. The per-story TS0005 is a thin index pointing to TS0001 for the actual TC definitions.

---

## Revision History

| Date       | Author | Change                                                          |
| ---------- | ------ | --------------------------------------------------------------- |
| 2026-05-20 | Claude | Initial plan created from US0001 via `/sdlc-studio story plan`. |
