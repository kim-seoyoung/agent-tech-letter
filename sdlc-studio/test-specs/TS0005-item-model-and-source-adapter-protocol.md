# TS0005: `Item` model + `SourceAdapter` protocol — Story Test Spec

> **Status:** Ready
> **Story:** [US0001](../stories/US0001-item-model-and-source-adapter-protocol.md)
> **Epic:** [EP0001: Content Ingestion](../epics/EP0001-content-ingestion.md)
> **Plan:** [PL0001](../plans/PL0001-item-model-and-source-adapter-protocol.md)
> **Created:** 2026-05-20
> **Last Updated:** 2026-05-20

## Purpose

This file is a **story-scoped index** into the canonical epic-level spec
[TS0001 — Content Ingestion](TS0001-content-ingestion.md). All TC definitions
(setup, assertions, fixtures, hypothesis strategies) live in TS0001. This file
exists to satisfy the `story plan` workflow's requirement for a
`TS*-{story-slug}.md` artifact per the SDLC Studio skill and to give US0001's
implementer (and reviewers) a tight, story-scoped view of test coverage.

**Canonical TC range for US0001:** TC0001 → TC0011 (11 test cases, all defined in TS0001).

---

## Scope

### Story Covered

| Story | Title | Priority |
|-------|-------|----------|
| [US0001](../stories/US0001-item-model-and-source-adapter-protocol.md) | `Item` model + `SourceAdapter` protocol | P0 (epic foundation) |

### AC Coverage Matrix

| AC  | Description                              | Test Cases (in TS0001) | Status  |
| --- | ---------------------------------------- | ---------------------- | ------- |
| AC1 | `Item` model defined and importable      | TC0001, TC0006, TC0007, TC0008, TC0009, TC0011 | Pending |
| AC2 | `SourceAdapter` protocol defined         | TC0009 (link)*         | Pending |
| AC3 | Trivial test adapter implements protocol | TC0009 (pyright conformance) | Pending |
| AC4 | Validation rejects malformed items       | TC0002, TC0003         | Pending |
| AC5 | tz-naive datetimes rejected              | TC0004, TC0005         | Pending |

\* TS0001's TC0009 covers both the `maturity` Literal AND the Protocol conformance check; if disentangling helps downstream tracing, add a TC0011-bis case during automation. Flagged but not blocking.

**Coverage:** 5/5 ACs covered. 11/11 TCs map to AC clauses. No UNCOVERED status.

### Test Types Required

| Type        | Required | Rationale                                                                                |
| ----------- | -------- | ---------------------------------------------------------------------------------------- |
| Unit        | Yes      | Pure pydantic model + typing.Protocol — unit tests are the natural fit                    |
| Property    | Yes      | TC0011 is hypothesis-based (`@given` round-trip); guards serialisation contract           |
| Integration | No       | No external systems; no I/O; no concurrency in this story                                 |
| E2E         | No       | Library-internal contract; first E2E test surfaces in EP0003 (`tests/pipeline/`)         |
| pyright     | Yes      | AC3 explicitly requires pyright to accept `FakeAdapter` as `SourceAdapter`                |

---

## Environment

| Requirement       | Details                                                                              |
| ----------------- | ------------------------------------------------------------------------------------ |
| Prerequisites     | uv environment from PL0001 Phase 1; pydantic>=2.6, pytest>=8, hypothesis>=6 installed |
| External Services | None                                                                                  |
| Test Data         | All test data is constructed inline per TC. No fixture files required.               |
| Pyright config    | `pyrightconfig.json` with `"strict": ["techletter"]` per PL0001                       |

---

## Test Cases

> Full Given/When/Then bodies, assertions, and fixture stubs live in
> [TS0001 §Test Cases](TS0001-content-ingestion.md#test-cases) under their TC numbers.
> Below is the story-scoped automation index.

| TC     | Title                                      | Type      | AC  | Priority |
| ------ | ------------------------------------------ | --------- | --- | -------- |
| TC0001 | `Item` constructs with all required fields | Unit      | AC1 | P0       |
| TC0002 | `ValidationError` on missing `url`         | Unit      | AC4 | P0       |
| TC0003 | `ValidationError` on missing required field (parametric) | Unit | AC4 | P0       |
| TC0004 | tz-aware UTC datetime accepted              | Unit      | AC5 | P0       |
| TC0005 | tz-naive datetime rejected                  | Unit      | AC5 | P0       |
| TC0006 | `HttpUrl` rejects non-http(s) schemes       | Unit      | AC1 | P1       |
| TC0007 | `summary_excerpt` > 1000 chars → `ValidationError` | Unit | AC1 | P1       |
| TC0008 | Unknown `item_kind` value → `ValidationError` | Unit    | AC1 | P1       |
| TC0009 | `maturity` outside allowed set + Protocol conformance | Unit + pyright | AC1, AC2, AC3 | P0 |
| TC0010 | Mutation on frozen `Item` raises             | Unit      | AC1 | P0       |
| TC0011 | hypothesis Item round-trip                   | Property  | AC1 | P0       |

---

## Fixtures

```yaml
# Inline-constructed Item dicts; no external fixture files needed.
# Defined in tests/unit/models/test_item.py and tests/unit/sources/test_base.py

minimal_item_dict:
  source: arxiv
  title: "An LLM Agent Survey"
  url: "https://arxiv.org/abs/2026.01234"
  summary_excerpt: "We survey LLM agents."
  published_at: "2026-05-15T12:00:00Z"
  item_kind: paper
  raw: {}

fake_adapter:
  module: techletter.sources.base
  class: FakeAdapter  # defined in test file
  name: "fake"
  fetch_returns: [<minimal_item_dict>, <minimal_item_dict>]
```

---

## Automation Status

| TC     | Title                                                          | Status  | Implementation |
| ------ | -------------------------------------------------------------- | ------- | -------------- |
| TC0001 | `Item` constructs with all required fields                      | Pending | —              |
| TC0002 | `ValidationError` on missing `url`                              | Pending | —              |
| TC0003 | `ValidationError` on missing required field (parametric)        | Pending | —              |
| TC0004 | tz-aware UTC datetime accepted                                  | Pending | —              |
| TC0005 | tz-naive datetime rejected                                      | Pending | —              |
| TC0006 | `HttpUrl` rejects non-http(s) schemes                           | Pending | —              |
| TC0007 | `summary_excerpt` > 1000 chars → `ValidationError`              | Pending | —              |
| TC0008 | Unknown `item_kind` value → `ValidationError`                   | Pending | —              |
| TC0009 | `maturity` outside allowed set + Protocol conformance           | Pending | —              |
| TC0010 | Mutation on frozen `Item` raises                                | Pending | —              |
| TC0011 | hypothesis Item round-trip                                      | Pending | —              |

---

## Traceability

| Artefact         | Reference                                                                  |
| ---------------- | -------------------------------------------------------------------------- |
| PRD              | [sdlc-studio/prd.md](../prd.md) F-01                                       |
| TRD              | [sdlc-studio/trd.md](../trd.md) §6 Data Models (Item)                       |
| TSD              | [sdlc-studio/tsd.md](../tsd.md) §Test Organisation → `tests/unit/models/`   |
| Epic             | [EP0001](../epics/EP0001-content-ingestion.md)                              |
| Story            | [US0001](../stories/US0001-item-model-and-source-adapter-protocol.md)       |
| Plan             | [PL0001](../plans/PL0001-item-model-and-source-adapter-protocol.md)         |
| Epic-level Spec  | [TS0001](TS0001-content-ingestion.md) TC0001–TC0011 (canonical bodies)      |

---

## Revision History

| Date       | Author | Change                                                                                      |
| ---------- | ------ | ------------------------------------------------------------------------------------------- |
| 2026-05-20 | Claude | Initial story-scoped TS created via `/sdlc-studio story plan --story US0001`. Indexes into TS0001 TC0001–TC0011. Status set to Ready (mirrors the canonical TS0001's Ready status). |
