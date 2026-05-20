# US0001: Define `Item` model + `SourceAdapter` protocol

> **Status:** Planned
> **Epic:** [EP0001: Content Ingestion](../epics/EP0001-content-ingestion.md)
> **Plan:** [PL0001](../plans/PL0001-item-model-and-source-adapter-protocol.md)
> **Test Spec:** [TS0005](../test-specs/TS0005-item-model-and-source-adapter-protocol.md)
> **Owner:** HYL
> **Reviewer:** HYL
> **Created:** 2026-05-19
> **Last Updated:** 2026-05-20

## User Story

**As** HYL (Author/Editor)
**I want** a typed `Item` model and a uniform `SourceAdapter` protocol
**So that** every source — present and future — produces normalised items that the rest of the pipeline can consume without caring where they came from.

## Context

### Persona Reference
**HYL (Author/Editor)** — values simplicity and adapter-pattern extensibility. Will judge this story by whether adding a new source later is a one-module change.
[Full persona details](../personas/stakeholders/users/hyl-author.md)

### Background
This story is the foundation of EP0001. Every other story in this epic (adapters for arXiv, GitHub, RSS, and the source registry) consumes the types defined here. Get this wrong and we either revisit it three times or live with leaky abstractions.

---

## Inherited Constraints

| Source | Type | Constraint | AC Implication |
|--------|------|------------|----------------|
| Epic | Architecture | Adapter pattern (TRD ADR-002); pipeline iterates a registry of `SourceAdapter`s | Protocol must be implementable by every source; no source-specific fields leak into the protocol |
| PRD | Model | `Item` includes `item_kind`, `maturity`, `raw` shipping signals | These fields are part of the model definition |
| TRD | Tech Stack | Python 3.11+, pydantic v2 | `Item` is a pydantic v2 model with strict validation |
| TRD | Audience | Single tier (research-aware engineer) per ADR-008 | `item_kind` enum is `paper \| blog_post \| repo` (no `consumer_product`); no `access` field |

---

## Acceptance Criteria

### AC1: `Item` model is defined and importable
- **Given** the package `techletter.models` exists
- **When** an engineer imports `from techletter.models import Item`
- **Then** `Item` is a pydantic v2 `BaseModel` with these fields (and only these, plus pydantic-internal config):
  - `source: Literal["arxiv","github","rss"]` (required)
  - `source_subtype: str | None` (default `None`)
  - `title: str` (required, min length 1)
  - `url: HttpUrl` (required)
  - `summary_excerpt: str` (required, max length 1000)
  - `score: float | None` (default `None`)
  - `published_at: datetime` (required, tz-aware UTC; naive datetimes are rejected at validation time)
  - `item_kind: Literal["paper","blog_post","repo"]` (required)
  - `maturity: Literal["experimental","beta","production-ready","unknown"] | None` (default `None`)
  - `raw: dict` (required, no type narrowing within the dict)

### AC2: `SourceAdapter` protocol is defined
- **Given** the package `techletter.sources.base` exists
- **When** an engineer imports `from techletter.sources.base import SourceAdapter`
- **Then** `SourceAdapter` is a `typing.Protocol` with these members:
  - `name: str` — class attribute, set per concrete adapter (e.g., `"arxiv"`, `"github"`, `"rss"`)
  - `fetch(self, window_days: int) -> list[Item]` — pure-function semantics, no side effects other than network I/O and logging

### AC3: A trivial test adapter implements the protocol
- **Given** a test fixture adapter `class FakeAdapter` with `name = "fake"` and `fetch(window_days)` returning a hardcoded list of two `Item` instances
- **When** pyright type-checks code that assigns `FakeAdapter()` to a variable typed `SourceAdapter`
- **Then** the assignment passes type-checking with no errors

### AC4: Validation rejects malformed items
- **Given** a dict missing the `url` field
- **When** `Item.model_validate(dict)` is called
- **Then** pydantic raises `ValidationError` mentioning the missing `url` field
- **And** the same holds for any other required field

### AC5: tz-naive datetimes are rejected
- **Given** an otherwise-valid dict with `published_at` as a naive `datetime.datetime(2026, 5, 19, 12, 0, 0)`
- **When** `Item.model_validate(dict)` is called
- **Then** pydantic raises `ValidationError` with a message indicating the datetime must be timezone-aware

---

## Scope

### In Scope
- `techletter/models/__init__.py` exporting `Item`.
- `techletter/sources/base.py` defining the `SourceAdapter` protocol.
- Field validators for `published_at` tz-aware requirement and `summary_excerpt` length cap.
- Unit tests for both modules.

### Out of Scope
- Concrete adapters (US0002–US0004).
- Source registry (US0005).
- `RenderedIssue` model, `Cluster` model (those belong to EP0002).
- The `SendRecord` model and `ChannelAdapter` protocol (those belong to EP0003 / EP0004).
- Migration tooling for `Item` (no versioning yet; project is greenfield).

---

## Technical Notes

- Use pydantic v2 (`pydantic.BaseModel`, `pydantic.HttpUrl`, `pydantic.field_validator`).
- Make `Item` immutable via `model_config = ConfigDict(frozen=True)`. This is cheap insurance against accidental mutation in the pipeline. A frozen pydantic model is still cheap to construct.
- `SourceAdapter` is a `typing.Protocol` (structural typing), not an ABC. Concrete adapters do not inherit from it; pyright checks conformance structurally.

### API Contracts
- `Item.model_validate(dict) -> Item`
- `Item.model_dump(mode="json") -> dict` — for JSON serialisation, with `datetime` and `HttpUrl` rendered as strings.
- `SourceAdapter.fetch(window_days: int) -> list[Item]` — `window_days` is the lookback window. `0` means "today only"; adapters may treat very large values pragmatically (e.g., cap at 30).

### Data Requirements
No persistent storage. Both module files live in the source tree; tests in `tests/test_models.py` and `tests/test_sources_base.py`.

---

## Edge Cases & Error Handling

| Scenario | Expected Behaviour |
|----------|-------------------|
| Empty `title` string | `ValidationError` from pydantic (min-length 1) |
| Non-http URL (e.g., `ftp://...`) | `ValidationError` (pydantic `HttpUrl` rejects non-http/https) |
| `summary_excerpt` exceeding 1000 chars | `ValidationError` (max-length 1000) |
| Unknown `item_kind` value (e.g., `"video"`) | `ValidationError` from `Literal` constraint |
| `maturity` set to a string outside the allowed set | `ValidationError` |
| Naive `datetime` for `published_at` | `ValidationError` from custom validator |
| `raw` is a non-dict (e.g., a list) | `ValidationError` (type mismatch) |
| Attempting to mutate an `Item` after construction (e.g., `item.title = "x"`) | `ValidationError` (frozen model) |
| Adapter declared but missing `name` attribute | pyright reports protocol mismatch |
| Adapter `fetch()` returns `None` | pyright reports return-type mismatch (`None` is not `list[Item]`) |

---

## Test Scenarios

> Canonical test cases live in [TS0001](../test-specs/TS0001-content-ingestion.md) TC0001–TC0011. The list below is the high-level coverage sketch this story commits to.

- [ ] Round-trip: construct `Item` via `model_validate(dict)` → `model_dump(mode="json")` → reconstruct via `model_validate` produces an equal `Item`.
- [ ] All edge cases above raise `ValidationError` with a sensible message.
- [ ] A `FakeAdapter` fixture passes pyright protocol conformance.
- [ ] A `FakeAdapter` whose `fetch` returns `[]` is treated as a valid (empty) result.
- [ ] A frozen `Item` cannot be mutated; attempted mutation raises.
- [ ] `Item` JSON round-trip preserves tz info on `published_at`.
- [ ] `Item.url` rejects schemes other than `http`/`https` (e.g., `ftp://`, `file://`) — pydantic `HttpUrl` constraint, AC1.
- [ ] A `FakeAdapter` declared without a `name` class attribute is reported by pyright as a `SourceAdapter` protocol mismatch — AC3 inverse case.

---

## Dependencies

### Story Dependencies
_None._ This is the foundational story for the epic.

### External Dependencies

| Dependency | Type | Status |
|------------|------|--------|
| pydantic v2 in `pyproject.toml` | Library | Not yet added — added as part of this story |
| Project scaffolding (`uv` env, `pyproject.toml`, `ruff`, `pyright` config) | Tooling | Required before this story can start |

---

## Estimation

**Story Points:** 3
**Complexity:** Low. Mostly model + protocol definition + tests. Risk lives in getting the field set right the first time so downstream stories don't churn.

---

## Open Questions

_None._

---

## Revision History

| Date | Author | Change |
|------|--------|--------|
| 2026-05-19 | HYL | Initial story created from EP0001. |
| 2026-05-20 | Claude | `/sdlc-studio story review`: Ready-criteria check passed (5 AC in G/W/T ✓, 8 edge cases ✓, no ambiguous language ✓, no Open Questions ✓, deps identified ✓). Mechanical fix: added 2 test scenarios (HttpUrl scheme rejection, pyright protocol-mismatch detection) to reach the 8-minimum for library stories. Pointed test list at TS0001 TC0001–TC0011 as canonical. Status promoted **Draft → Ready**. |
| 2026-05-20 | Claude | `/sdlc-studio story plan`: Created [PL0001](../plans/PL0001-item-model-and-source-adapter-protocol.md) (16-task TDD plan; absorbs scaffolding + `SourceFetchError` + `Maturity` Literal alias to pre-empt Wave-2 hub conflicts per `epic plan --agentic` analysis) and [TS0005](../test-specs/TS0005-item-model-and-source-adapter-protocol.md) (story-scoped index into TS0001 TC0001–TC0011). Status promoted **Ready → Planned**. |
