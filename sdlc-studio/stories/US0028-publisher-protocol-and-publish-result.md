# US0028: `Publisher` Protocol + `PublishResult` model

> **Status:** Done
> **Epic:** [EP0006: GitHub Pages Publisher + Telegram Link Mode](../epics/EP0006-github-pages-and-telegram-link-mode.md)
> **Change Request:** [CR-0002](../change-requests/CR0002-github-pages-and-telegram-link-mode.md) (Item 1)
> **Owner:** HYL
> **Reviewer:** HYL
> **Created:** 2026-05-21

## User Story

**As** the Telegram adapter (and any future channel that wants a permanent link)
**I want** a single, stable abstraction that takes a `RenderedIssue` and returns a public URL
**So that** swapping the backend (GitHub Pages → Telegraph → Cloudflare R2 → etc.) is a one-module change and the rest of the delivery code doesn't have to care which one is configured.

## Context

### Persona Reference
**HYL** — direct. Wants a clean seam for future backend swaps. Pays the abstraction cost (1 small protocol + 1 model) to avoid coupling Telegram to GitHub Pages.
**Researcher Subscriber** — indirect. They benefit when CR-0002's downstream stories produce the link via this contract.

### Background
Per EP0006 architecture, a `Publisher` consumes a `RenderedIssue` and returns a `PublishResult` carrying at least a `url`. The Telegram adapter (US0031) calls `publisher.publish(issue)` once per `send()` and embeds the URL into the teaser message. This story is just the interface — no backend yet. US0029 ships `GitHubPagesPublisher` against it.

---

## Inherited Constraints

| Source | Type | Constraint | AC Implication |
|--------|------|------------|----------------|
| EP0006 | Architecture | `Publisher` is a structural Protocol | Use `typing.Protocol`; not an ABC |
| CR-0002 | Schema | `PublishResult.url` always present; `commit_sha` optional (publisher-backend-specific) | Pydantic field optional, defaults None |
| EP0003 | Audit | `PublishResult.url` flows into `SendRecord.published_url` (US0032) | Result must serialize cleanly to JSON for audit |
| EP0005 | Determinism | Same `RenderedIssue` → same `url` (idempotency) | Publisher implementations are responsible; protocol just specifies the shape |

---

## Acceptance Criteria

### AC1: `Publisher` Protocol shape
- **Given** the module `techletter.delivery.publishers.base`
- **When** an engineer imports `from techletter.delivery.publishers.base import Publisher`
- **Then** `Publisher` is a `typing.Protocol`
- **And** it has `name: str` (class attribute or instance attribute)
- **And** it has `publish(self, issue: RenderedIssue) -> PublishResult`
- **And** `pyright` confirms a class providing both members satisfies the Protocol

### AC2: `PublishResult` model
- **Given** the same module
- **When** `PublishResult` is imported
- **Then** it is a frozen pydantic `BaseModel` with:
  - `url: str` (required; minimum length 1)
  - `path: str` (required — backend-specific identifier, e.g., `issues/2026-05-21-abc123.html`)
  - `published_at: datetime` (required; ISO-8601 with timezone)
  - `commit_sha: str | None` (optional; only set when the backend is git-based)
  - `publisher_name: str` (echoes the publisher's `name`; non-empty)
- **And** `model_config = ConfigDict(frozen=True, extra="forbid")`

### AC3: `PublishResult` JSON round-trip
- **Given** a `PublishResult` instance
- **When** `result.model_dump_json()` is parsed and validated via `PublishResult.model_validate_json(...)`
- **Then** the round-tripped object is equal to the original
- **And** `published_at` is serialized as ISO-8601 with `Z` (UTC) or `+00:00`

### AC4: `__init__.py` re-exports
- **Given** `from techletter.delivery.publishers import Publisher, PublishResult, PublisherError`
- **When** the import runs
- **Then** all three symbols resolve (top-level package exports for convenience)

### AC4b: `PublisherError` exception class (per RV0002 F-1)
- **Given** the module `techletter.delivery.publishers.base`
- **When** `PublisherError` is imported
- **Then** it is a subclass of `Exception`
- **And** all future `Publisher` implementations (starting with `GitHubPagesPublisher` in US0029) raise this class to signal backend-side failures (dirty worktree, push failure, missing branch, etc.)
- **And** it is re-exported from `techletter.delivery.publishers` (top-level)

### AC5: No backend yet
- **Given** the `publishers/` package
- **When** listed
- **Then** **only** `__init__.py` and `base.py` exist after this story
- **And** US0029 adds `github_pages.py` in a follow-up

---

## Scope

### In Scope
- `techletter/delivery/publishers/__init__.py` (re-exports `Publisher`, `PublishResult`, `PublisherError`).
- `techletter/delivery/publishers/base.py` (`Publisher` Protocol, `PublishResult` model, `PublisherError` exception class).
- `tests/unit/delivery/publishers/test_base.py` (Protocol conformance, model construction, round-trip, `PublisherError` is a subclass of Exception and importable from both `base` and the package root).

### Out of Scope
- `GitHubPagesPublisher` (US0029).
- Telegram adapter integration (US0031).
- `SendRecord.published_url` field (US0032).
- Pluggable publisher registry — keep it simple; one publisher reference per channel resolved in `channels.yaml`.

---

## Technical Notes

- Protocol vs ABC: Use `typing.Protocol`. ABCs require explicit inheritance, which leaks the abstraction; protocols match by shape and stay invisible at the call site.
- `runtime_checkable`: optional — only needed if we want `isinstance(x, Publisher)` to work at runtime. Keep it off in this story to avoid the cost; revisit if a real need shows up.
- `PublishResult.publisher_name`: used by `SendRecord.published_url` audit logging (US0032) so the operator can see which publisher emitted a given URL.

### Sample API (illustrative)

```python
from typing import Protocol
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

from techletter.compose.issue import RenderedIssue


class PublishResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    url: str = Field(min_length=1)
    path: str = Field(min_length=1)
    published_at: datetime
    publisher_name: str = Field(min_length=1)
    commit_sha: str | None = None


class Publisher(Protocol):
    name: str

    def publish(self, issue: RenderedIssue) -> PublishResult: ...
```

---

## Edge Cases & Error Handling

| Scenario | Expected Behaviour |
|----------|-------------------|
| `url` empty string | pydantic validation error at construction |
| `commit_sha` not provided | `None` (acceptable for non-git publishers) |
| Concrete publisher doesn't define `name` | pyright flags it; runtime: AttributeError at first access |
| Publisher raises a real exception inside `publish` (e.g., git push fail) | The adapter wrapping the call decides what to do (US0031 maps it to `SendReport.status=failed`); this story does not define publisher exception classes |

---

## Test Scenarios

- [ ] `PublishResult(url="https://e.com", path="x", published_at=..., publisher_name="p")` constructs.
- [ ] `PublishResult(url="")` raises ValidationError.
- [ ] Frozen: `result.url = "y"` raises.
- [ ] Round-trip via `model_dump_json` / `model_validate_json`.
- [ ] A test stub class providing `name` + `publish` satisfies `Publisher` (pyright via cast-and-assign in a typing test, or via `runtime_checkable` if added later).
- [ ] Top-level imports from `techletter.delivery.publishers` resolve.

---

## Dependencies

### Story Dependencies

None upstream. US0029 / US0031 / US0032 all consume this.

### External Dependencies

None new.

---

## Estimation

**Story Points:** 2
**Complexity:** Trivial. Pure schema work. The judgment call is the field set on `PublishResult` — once locked, US0029 onward are fully constrained.

---

## Open Questions

None.

---

## Revision History

| Date | Author | Change |
|------|--------|--------|
| 2026-05-21 | HYL | Story created from CR-0002 (Item 1) via `/sdlc-studio cr action`. |
