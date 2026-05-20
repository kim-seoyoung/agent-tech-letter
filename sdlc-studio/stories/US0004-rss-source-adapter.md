# US0004: Implement RSS source adapter

> **Status:** Draft
> **Epic:** [EP0001: Content Ingestion](../epics/EP0001-content-ingestion.md)
> **Owner:** HYL
> **Reviewer:** HYL
> **Created:** 2026-05-19

## User Story

**As** HYL (Author/Editor)
**I want** an RSS adapter that consumes a configurable list of feed URLs and produces normalised `Item`s
**So that** the initial four tech-blog feeds (and any future additions) flow into the pipeline through a single adapter without needing a new module per feed.

## Context

### Persona Reference
**HYL (Author/Editor)** — wants RSS to be the path of least resistance for adding sources. Will judge this by whether adding a new feed is a one-line `config/sources.yaml` edit.
[Full persona details](../personas/stakeholders/users/hyl-author.md)

### Background
The initial feed list (PRD v0.4.0): The New Stack AI (`https://thenewstack.io/ai`), Import AI (`https://importai.substack.com/`), Latent Space (`https://www.latent.space/`), Simon Willison (`https://simonwillison.net/atom/everything/`). `feedparser` is the de-facto Python RSS/Atom parser and handles both formats plus malformed inputs gracefully.

---

## Inherited Constraints

| Source | Type | Constraint | AC Implication |
|--------|------|------------|----------------|
| Epic | Architecture | Implements `SourceAdapter` from US0001 | Single adapter class, multiple feed instances at fetch time |
| Epic | Reliability | Per-source isolation | One bad feed must not stop other feeds in the same fetch call |
| PRD | Source list | Feeds in config; adding a feed requires zero code changes | Adapter takes feed URLs from config (loaded by US0005), not from constants |
| TRD | Library | `feedparser` | No alternative parser without an ADR |
| TRD | Architecture | All RSS items have `item_kind = "blog_post"` | Adapter sets this unconditionally |

---

## Acceptance Criteria

### AC1: Adapter is discoverable and conformant
- **Given** the package `techletter.sources.rss` exists
- **When** an engineer imports `from techletter.sources.rss import RssAdapter` and calls `RssAdapter(feeds=["https://example.com/feed"])`
- **Then** the instance has `name == "rss"` and `fetch(window_days)` returns `list[Item]`
- **And** pyright type-checks the instance as a valid `SourceAdapter`

### AC2: Aggregates items from multiple feeds
- **Given** the adapter is constructed with 3 feed URLs
- **When** `fetch(window_days=7)` is called against mock HTTP returning a valid RSS body for each feed
- **Then** the returned list contains all items from all 3 feeds whose `published_at` is within the 7-day window
- **And** items from each feed have `source = "rss"`, `item_kind = "blog_post"`, and `source_subtype` set to the source feed URL (so the LLM can attribute later)

### AC3: Window filter is applied
- **Given** a feed returning 10 items spanning the last 30 days
- **When** `fetch(window_days=7)` is called
- **Then** only items with `published_at` within the last 7 days are included

### AC4: Per-feed failure isolation
- **Given** 3 feed URLs configured, where feed #2 returns HTTP 500 (after retries) and feeds #1 and #3 return valid responses
- **When** `fetch(window_days=7)` is called
- **Then** items from feeds #1 and #3 are returned
- **And** feed #2's failure is logged with the URL and final error
- **And** the adapter does not raise — partial result is the result

### AC5: Tolerates malformed XML
- **Given** a feed whose XML is malformed (e.g., truncated mid-document)
- **When** `feedparser` parses it and surfaces some valid items with a `bozo` flag
- **Then** the adapter returns the valid items and logs a warning containing the feed URL
- **And** does not raise on the `bozo` condition alone

### AC6: Items missing required fields are skipped
- **Given** a feed with 5 items where 2 are missing the `published` field
- **When** the adapter parses the feed
- **Then** the 3 well-formed items are returned
- **And** the 2 skipped items are logged with the feed URL and item title (where available)

---

## Scope

### In Scope
- `techletter/sources/rss.py` defining `RssAdapter`.
- Per-feed fetch wrapped in tenacity (retries + backoff) and try/except (isolation).
- Mapping `feedparser` entry fields → `Item`:
  - `entry.title` → `title`
  - `entry.link` → `url`
  - `entry.summary` (or `entry.description`) → `summary_excerpt` (truncated to 1000 chars)
  - `entry.published_parsed` → `published_at` (converted to tz-aware UTC datetime)
- Unit tests with fixture RSS/Atom payloads.

### Out of Scope
- Full-content fetch (we only use the feed-provided summary).
- HTML stripping from `summary_excerpt` (downstream LLM tolerates light HTML; if it becomes a problem, add a strip step here later).
- Per-feed authentication or custom headers (none of the initial feeds require it).
- Feed-discovery via `<link rel="alternate">` parsing — the feed URL is given explicitly.
- Maintaining feed-level state (last-seen-guid) — window filtering is sufficient for v1.

---

## Technical Notes

- Use `feedparser.parse(url)`. It handles HTTP fetching internally, but for tenacity control we'll wrap an `httpx.get()` call to fetch the body and pass it to `feedparser.parse(text)`.
- Convert `entry.published_parsed` (a `struct_time`) to `datetime.datetime(*..., tzinfo=timezone.utc)`. Document that feeds without `published` are skipped (per AC6).
- Set `item_kind = "blog_post"` and `maturity = None` for all RSS items.
- `raw` contains the full `feedparser` entry dict.

### API Contracts
- Public surface: `RssAdapter(feeds: list[str]).fetch(window_days: int) -> list[Item]`
- `feeds` is the list of feed URLs; provided by the config layer (US0005).

### Data Requirements
None persistent.

---

## Edge Cases & Error Handling

| Scenario | Expected Behaviour |
|----------|-------------------|
| Feed list is empty | Returns `[]` without error |
| Feed URL is malformed (e.g., not a URL) | `ValueError` raised at adapter construction (validated against pydantic `HttpUrl` if we want strict) — or per-feed failure log if validated later |
| Feed returns 200 but body is empty | `feedparser` produces no entries; adapter returns `[]` for that feed |
| Feed returns 200 with HTML page (no XML) | `feedparser` `bozo` flag set, no entries; warning log, returns `[]` for that feed |
| Feed redirects (3xx) | `httpx` follows redirects by default; no special handling |
| Feed is exceptionally slow (>30s) | `httpx` timeout (default 10s) raises; tenacity retries; eventually logged as per-feed failure |
| Same item appears in two different feeds | Both are returned; dedupe happens downstream in EP0002 |
| Item's `published` is in the future | Included; downstream layers tolerate |
| Item title is empty | Skipped (would fail pydantic min-length check on `Item`) |
| Item summary > 1000 chars | Truncated to 1000 with ellipsis |
| `published_parsed` is `None` | Skipped (per AC6) |

---

## Test Scenarios

- [ ] Fixture: 3 feeds returning 4, 5, 3 items respectively, all within window → returns 12 items, each tagged with its source feed in `source_subtype`.
- [ ] Fixture: feed with 10 items, 7 within window → returns 7.
- [ ] Fixture: 3 feeds, feed #2 returns 500 × 5 → returns items from #1 and #3; failure logged.
- [ ] Fixture: Atom-format feed (vs RSS 2.0) → both parse equivalently.
- [ ] Fixture: feed with `<bozo>` (malformed but partially parseable) → valid items returned, warning logged.
- [ ] Fixture: feed where 2 items lack `published` → those 2 skipped.
- [ ] Empty feed list → returns `[]`.
- [ ] Item summary 1500 chars → `summary_excerpt` is exactly 1000 chars (with truncation marker).
- [ ] Type check: `RssAdapter(feeds=[])` is a valid `SourceAdapter` per pyright.

---

## Dependencies

### Story Dependencies

| Story | Type | What's Needed | Status |
|-------|------|---------------|--------|
| [US0001](US0001-item-model-and-source-adapter-protocol.md) | Schema | `Item` model + `SourceAdapter` protocol | Done |

### External Dependencies

| Dependency | Type | Status |
|------------|------|--------|
| `feedparser` library | Python package | Added in this story |
| `httpx` library | Python package | Shared with US0003; available |

---

## Estimation

**Story Points:** 2
**Complexity:** Low. `feedparser` does the heavy lifting; the main work is wiring up per-feed error isolation and the window filter.

---

## Open Questions

_None._

---

## Revision History

| Date | Author | Change |
|------|--------|--------|
| 2026-05-19 | HYL | Initial story created from EP0001. |
