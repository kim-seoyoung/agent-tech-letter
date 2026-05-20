# US0002: Implement arXiv source adapter

> **Status:** Draft
> **Epic:** [EP0001: Content Ingestion](../epics/EP0001-content-ingestion.md)
> **Owner:** HYL
> **Reviewer:** HYL
> **Created:** 2026-05-19

## User Story

**As** HYL (Author/Editor)
**I want** an arXiv adapter that pulls recent `cs.AI` and `cs.CL` submissions filtered by LLM-agent keywords
**So that** every weekly issue can surface papers from the venue where most LLM-agent research first appears, without me hand-searching arXiv.

## Context

### Persona Reference
**HYL (Author/Editor)** — wants the system to fetch papers reliably from arXiv week after week with zero hand-intervention. Will also push back if the keyword filter is so loose that the LLM has to wade through unrelated papers in the cluster step.
[Full persona details](../personas/stakeholders/users/hyl-author.md)

### Background
arXiv is the canonical source for the Researcher Subscriber. The `arxiv` Python library wraps the arXiv query API and handles pagination + a polite 3-second delay between calls. This story produces a concrete `SourceAdapter` named `arxiv` that returns `Item`s with `item_kind = "paper"`.

---

## Inherited Constraints

| Source | Type | Constraint | AC Implication |
|--------|------|------------|----------------|
| Epic | Architecture | Implements `SourceAdapter` protocol from US0001 | Adapter must be type-conformant; pyright checks at PR time |
| Epic | Reliability | Per-source isolation; tenacity retries | All arXiv API calls wrapped in tenacity decorator |
| PRD | Source | arXiv `cs.AI` + `cs.CL`, filterable by LLM-agent keywords | Keyword list is configurable; default list ships with the adapter |
| PRD | Performance | Whole draft completes in <5 min | Adapter must not block the run for >60s under normal conditions |
| TRD | Library | `arxiv` library | No alternative client without an ADR |

---

## Acceptance Criteria

### AC1: Adapter is discoverable and conformant
- **Given** the package `techletter.sources.arxiv` exists
- **When** an engineer imports `from techletter.sources.arxiv import ArxivAdapter` and calls `ArxivAdapter()`
- **Then** the instance has `name == "arxiv"` and `fetch(window_days)` returns `list[Item]`
- **And** pyright type-checks the instance as a valid `SourceAdapter`

### AC2: Fetch returns recent items from configured categories
- **Given** the adapter is configured with default categories `["cs.AI", "cs.CL"]` and a default keyword list including "agent", "tool-use", "LLM"
- **When** `fetch(window_days=7)` is called against a mocked arXiv API that returns 10 papers spanning both categories
- **Then** the returned list contains only papers whose `published_at` is within the last 7 days
- **And** each returned `Item` has `source = "arxiv"`, `item_kind = "paper"`, `source_subtype` set to the originating category (e.g., `"cs.AI"`), and `url` pointing to the arXiv abstract page

### AC3: Keyword filter is applied
- **Given** the adapter is configured with keywords `["agent", "tool-use"]`
- **When** `fetch(window_days=7)` is called against fixture data with 3 LLM-agent papers and 2 unrelated papers (e.g., computer-vision)
- **Then** the returned list contains only the 3 LLM-agent papers
- **And** matching is case-insensitive against title and abstract

### AC4: Empty result is valid
- **Given** the API returns no papers matching the window or keyword filter
- **When** `fetch(window_days=7)` is called
- **Then** the adapter returns `[]` (an empty list)
- **And** no exception is raised; the run continues

### AC5: Retry on transient failure
- **Given** the arXiv API returns HTTP 503 on the first two attempts and HTTP 200 on the third
- **When** `fetch(window_days=7)` is called
- **Then** tenacity retries with exponential backoff
- **And** the adapter ultimately returns the items from the successful response
- **And** the total number of attempts is logged

### AC6: Permanent failure isolates per-source
- **Given** the arXiv API returns HTTP 503 on all retry attempts (max 5)
- **When** `fetch(window_days=7)` is called
- **Then** the adapter raises a `SourceFetchError` (or equivalent named exception) after exhausting retries
- **And** the exception is caught at the registry level (US0005), logged, and the run continues with other sources

---

## Scope

### In Scope
- `techletter/sources/arxiv.py` defining `ArxivAdapter`.
- Default keyword list (configurable via constructor) for LLM-agent relevance.
- Mapping from arXiv API fields → `Item` fields (title, abstract → `summary_excerpt`, `published`, `entry_id` → `url`).
- tenacity-wrapped query call (max 5 attempts, exponential backoff with jitter, starting at 1s).
- `SourceFetchError` exception type for permanent failures.
- Unit tests with fixture arXiv responses.

### Out of Scope
- Full-text PDF download or parsing — only abstract metadata is fetched.
- Per-author / per-affiliation filtering — keyword filter is enough for v1.
- Cross-week deduplication (e.g., paper appears as v1 last week and v2 this week) — defer to clustering layer in EP0002.
- Citation-graph signals (used by F-02 ranker) — those derive from the LLM, not from this adapter.

---

## Technical Notes

- Use the `arxiv` library's `Search` + `Client` API. Pass `sort_by=SubmittedDate, sort_order=Descending` and a category-filtered query string.
- Truncate the abstract to 1000 chars before assignment to `summary_excerpt` to respect the `Item` length cap.
- Set `score = None` for arXiv items — they have no upstream popularity signal.
- Set `maturity = None` initially. Maturity inference for papers is the LLM's job in EP0002, not the adapter's.
- `raw` contains the full arXiv response payload so downstream callers can access anything the adapter didn't surface.

### API Contracts
- Public surface: `ArxivAdapter(categories: list[str] = ["cs.AI","cs.CL"], keywords: list[str] = DEFAULT_KEYWORDS).fetch(window_days: int) -> list[Item]`
- The default keyword list lives in a module-level constant; can be overridden via constructor or via `config/sources.yaml` (loader in US0005).

### Data Requirements
None persistent. Adapter is stateless across calls.

---

## Edge Cases & Error Handling

| Scenario | Expected Behaviour |
|----------|-------------------|
| arXiv returns malformed XML (rare but possible) | `feedparser`/`arxiv` lib raises; tenacity retries; if still failing, surfaces as `SourceFetchError` |
| Paper has no abstract (legacy entries) | Skip the item; log a warning |
| Paper's `published` is in the future (timezone weirdness) | Include the item; downstream filters handle |
| `window_days = 0` | Equivalent to today only; valid input |
| `window_days < 0` | `ValueError` raised by adapter before calling API |
| `window_days > 365` | Clamp to 365 with a warning log; do not hammer the API |
| All papers in window match keyword filter | Returns full list (no upper bound at adapter level) |
| Category list contains an invalid arXiv category (e.g., `"cs.NONEXISTENT"`) | arXiv returns empty result; adapter returns `[]` and logs a warning |
| Network timeout (connection-level) | tenacity retries; logged per attempt |
| Concurrent calls to `fetch()` from the same adapter instance | Adapter is stateless; safe (though not used concurrently in v1) |

---

## Test Scenarios

- [ ] Fixture: 10 papers spanning cs.AI / cs.CL, 7 within window, 3 outside → returns 7.
- [ ] Fixture: 5 papers all within window, 3 match keywords, 2 don't → returns 3.
- [ ] Fixture: empty arXiv response → returns `[]` without error.
- [ ] Mock: 503 × 2 then 200 → tenacity retries succeed, items returned.
- [ ] Mock: 503 × 5 → `SourceFetchError` raised; log mentions all 5 attempts.
- [ ] `window_days = -1` → `ValueError`.
- [ ] `window_days = 1000` → clamped to 365 with warning log.
- [ ] Abstract length 2000 chars → `summary_excerpt` truncated to 1000.
- [ ] Type check: `ArxivAdapter()` assignable to `SourceAdapter` per pyright.

---

## Dependencies

### Story Dependencies

| Story | Type | What's Needed | Status |
|-------|------|---------------|--------|
| [US0001](US0001-item-model-and-source-adapter-protocol.md) | Schema | `Item` model + `SourceAdapter` protocol | Done |

### External Dependencies

| Dependency | Type | Status |
|------------|------|--------|
| `arxiv` library | Python package | Not yet added — added as part of this story |
| `tenacity` library | Python package | Not yet added (will be reused by all source stories) |

---

## Estimation

**Story Points:** 3
**Complexity:** Low-Medium. The `arxiv` library does most of the work. Risk: keyword filter tuning takes a couple of PR iterations before it's good.

---

## Open Questions

_None._

---

## Revision History

| Date | Author | Change |
|------|--------|--------|
| 2026-05-19 | HYL | Initial story created from EP0001. |
