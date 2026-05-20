# US0003: Implement GitHub Trending source adapter

> **Status:** Done
> **Plan:** [PL0003](../plans/PL0003-github-trending-source-adapter.md)
> **Test Spec:** [TS0008](../test-specs/TS0008-github-trending-source-adapter.md)
> **Last Updated:** 2026-05-20
> **Epic:** [EP0001: Content Ingestion](../epics/EP0001-content-ingestion.md)
> **Owner:** HYL
> **Reviewer:** HYL
> **Created:** 2026-05-19

## User Story

**As** HYL (Author/Editor)
**I want** a GitHub Trending adapter that fetches trending repos in the past week and captures shipping signals (stars, last-commit, recent-release, hosted-demo URL)
**So that** the Researcher Subscriber can see, in each issue, whether a trending repo is just hyped or actually has signs of being shipped.

## Context

### Persona Reference
**HYL (Author/Editor)** — needs this signal for the issue to be useful. Will be skeptical of an adapter that captures stars but nothing about whether a repo is actually maintained.
[Full persona details](../personas/stakeholders/users/hyl-author.md)

**Researcher Subscriber (downstream)** — wants to know "has anyone shipped this?" The shipping signals captured here flow into F-03 deep-dive framing.

### Background
GitHub Trending has no official API, which makes this the most fragile of the three adapters. We accept that fragility because the signal is uniquely valuable: GitHub trending captures attention in a way that arXiv and RSS do not. Strategy: scrape the trending HTML page, then enrich each repo via the GitHub REST API for shipping signals.

---

## Inherited Constraints

| Source | Type | Constraint | AC Implication |
|--------|------|------------|----------------|
| Epic | Architecture | Implements `SourceAdapter` protocol from US0001 | Must be protocol-conformant |
| Epic | Risk | "GitHub trending scrape breaks" is the highest-likelihood failure mode | Fixture-based tests are mandatory; adapter must fail soft (return `[]` and log) on scrape failure, not abort the run |
| PRD | Metadata | `raw` must include `stars`, `last_commit_at`, `has_recent_release`, `hosted_demo_url` | Adapter enriches each item via GitHub REST API after scraping |
| PRD | Maturity inference | `maturity` is inferred from repo signals | Adapter sets `maturity` based on rules below |
| TRD | Tech Stack | `httpx`, optionally `GITHUB_TOKEN` for higher rate limits | All HTTP calls use `httpx` |

---

## Acceptance Criteria

### AC1: Adapter is discoverable and conformant
- **Given** the package `techletter.sources.github` exists
- **When** an engineer imports `from techletter.sources.github import GitHubTrendingAdapter` and calls `GitHubTrendingAdapter()`
- **Then** the instance has `name == "github"` and `fetch(window_days)` returns `list[Item]`
- **And** pyright type-checks the instance as a valid `SourceAdapter`

### AC2: Scrapes trending page and parses repo list
- **Given** the adapter is configured with `spoken_language="en"` and `period="weekly"` (defaults)
- **When** `fetch(window_days=7)` is called against a fixture HTML response containing 25 trending repos
- **Then** the adapter returns up to 25 `Item`s
- **And** each `Item` has `source = "github"`, `item_kind = "repo"`, `url` pointing to the repo, and `title` matching the repo's `owner/name`

### AC3: Enriches each repo with shipping signals
- **Given** a list of repo URLs parsed from the trending page
- **When** the adapter calls the GitHub REST API (`GET /repos/{owner}/{name}` and `GET /repos/{owner}/{name}/releases?per_page=1`)
- **Then** `raw` for each item contains:
  - `stars: int` — from the `stargazers_count` field
  - `last_commit_at: str` (ISO-8601 UTC) — from the `pushed_at` field
  - `has_recent_release: bool` — `True` if the most recent release was within the last 90 days
  - `hosted_demo_url: str | None` — from `homepage` if it's a non-empty URL, else `None`

### AC4: `maturity` is inferred from signals
- **Given** the enriched repo metadata
- **When** the adapter constructs each `Item`
- **Then** `maturity` is set as follows:
  - `"production-ready"` if `has_recent_release == True` AND `last_commit_at` within last 30 days AND `stars >= 500`
  - `"beta"` if `last_commit_at` within last 30 days AND `stars >= 50`
  - `"experimental"` if `last_commit_at` older than 90 days OR `stars < 50`
  - `"unknown"` if any input field is missing
- **And** the rule is a single function `infer_maturity(metadata) -> Maturity` for ease of iteration

### AC5: Scrape failure fails soft
- **Given** the trending page returns HTTP 404 (or 503 after retries) — the most likely future failure mode
- **When** `fetch(window_days=7)` is called and tenacity retries are exhausted
- **Then** the adapter returns `[]` (not an exception)
- **And** a warning is logged with the response code and URL
- **And** the registry (US0005) does not abort the run

### AC6: REST-API rate limiting is respected
- **Given** `GITHUB_TOKEN` is provided via environment variable (optional)
- **When** the adapter makes REST API calls
- **Then** the `Authorization: Bearer {token}` header is included
- **And** if no token is provided, calls go unauthenticated (acceptable for small batch sizes; tenacity handles 429 with backoff)

### AC7: Per-repo enrichment failure does not skip the repo
- **Given** the trending scrape returns 25 repos but the REST API call for one repo returns 404 (repo deleted between scrape and enrichment)
- **When** the adapter processes the batch
- **Then** the deleted repo is omitted from results with a warning log
- **And** the remaining 24 are returned with full enrichment

---

## Scope

### In Scope
- `techletter/sources/github.py` defining `GitHubTrendingAdapter`.
- HTML scraper for the trending page (using a known stable selector pattern; document the selector with a comment so future drift is locatable).
- REST API enrichment helper.
- `infer_maturity` function with explicit rules.
- tenacity retries on both the scrape and the REST calls.
- Unit tests with fixture HTML and fixture API responses.

### Out of Scope
- Trending pages for specific languages or topics (could add via constructor args in a future story).
- Issue/PR activity signals beyond `last_commit_at` and releases.
- Repo content analysis (README parsing, dependency analysis, etc.).
- Failover to a different signal (e.g., GitHub Search trending) if scraping breaks — that's a future risk-response, not v1 scope.

---

## Technical Notes

- The trending page URL: `https://github.com/trending?since=weekly&spoken_language_code=en` — document this as a constant in the module.
- Use `httpx` for all HTTP calls. Set a sensible `User-Agent` header so we look like a real client.
- Pin the HTML selector pattern in a single function `parse_trending_html(html: str) -> list[RepoStub]`. If GitHub redesigns the page, this is the only function to change.
- `RepoStub` is an internal pydantic model (or dataclass) with `owner`, `name`, `description` — local to this module.
- The enrichment phase is sequential in v1 (≤25 repos × ~100ms each = ~2.5s); no async required.

### API Contracts
- Public surface: `GitHubTrendingAdapter(spoken_language: str = "en", period: str = "weekly").fetch(window_days: int) -> list[Item]`
- `window_days` is informational only — GitHub trending's own "weekly" granularity defines the actual window. Document this in the docstring.

### Data Requirements
None persistent. Adapter is stateless.

---

## Edge Cases & Error Handling

| Scenario | Expected Behaviour |
|----------|-------------------|
| Trending HTML structure changes (selectors no longer match) | `parse_trending_html` returns `[]`; warning logged; adapter returns `[]` |
| Trending page is empty (e.g., quiet week with no qualifying repos) | Returns `[]` without error |
| Repo deleted between scrape and enrichment | Omit from result with warning |
| Repo is private (404 on enrichment) | Treat as deleted — omit with warning |
| `homepage` field is whitespace or a non-URL string | `hosted_demo_url = None` |
| `pushed_at` missing | `maturity = "unknown"` |
| GitHub REST API returns 429 (rate limit) | tenacity backoff; eventually surfaces as `SourceFetchError` if persistent |
| `GITHUB_TOKEN` is set but invalid | REST calls return 401 → tenacity retries → eventually `SourceFetchError` |
| `window_days < 0` | `ValueError` |
| Selector matches partial / corrupted HTML | Skip the unparseable row; continue with others; log count of skipped rows |
| `stars` field is missing in REST response | Treat as 0; maturity may become `"experimental"` |

---

## Test Scenarios

- [ ] Fixture HTML with 25 valid rows + 1 corrupted row → returns 25 items, logs 1 skipped row.
- [ ] Fixture HTML with 0 rows → returns `[]` without error.
- [ ] Fixture HTML with selector mismatch (random other GitHub page) → returns `[]` with warning log.
- [ ] Mock REST: repo with 1000 stars, recent release, recent push → `maturity = "production-ready"`.
- [ ] Mock REST: repo with 75 stars, recent push, no recent release → `maturity = "beta"`.
- [ ] Mock REST: repo with 10 stars, push >90 days ago → `maturity = "experimental"`.
- [ ] Mock REST: missing `pushed_at` → `maturity = "unknown"`.
- [ ] Mock REST: one repo returns 404 → omitted from result; others returned.
- [ ] Mock: trending page 503 × 5 → `fetch()` returns `[]` (fails soft).
- [ ] Mock: REST 429 × 5 → `SourceFetchError`.
- [ ] `GITHUB_TOKEN` env set → Authorization header sent on REST calls.

---

## Dependencies

### Story Dependencies

| Story | Type | What's Needed | Status |
|-------|------|---------------|--------|
| [US0001](US0001-item-model-and-source-adapter-protocol.md) | Schema | `Item` model + `SourceAdapter` protocol | Done |

### External Dependencies

| Dependency | Type | Status |
|------------|------|--------|
| `httpx` library | Python package | Will be added in this story |
| `selectolax` or `beautifulsoup4` for HTML parsing | Python package | Pick one; lean to `selectolax` (faster, simpler API) |
| Optional `GITHUB_TOKEN` GitHub secret | Secret | Optional; not required for adapter to function |

---

## Estimation

**Story Points:** 5
**Complexity:** Medium. The scraping + enrichment combination is more code than the other adapters. Maturity-inference rules will be tuned in PR review. Highest fragility risk in the epic.

---

## Open Questions

_None._

---

## Revision History

| Date | Author | Change |
|------|--------|--------|
| 2026-05-19 | HYL | Initial story created from EP0001. |
| 2026-05-20 | Claude | `/sdlc-studio epic implement --epic EP0001 --agentic` Wave 3: GitHubTrendingAdapter implemented (`techletter/sources/github.py`, ~230 LOC) with HTML scrape via selectolax, REST enrichment, `infer_maturity` rules (production-ready/beta/experimental/unknown), GITHUB_TOKEN auth header support, fail-soft on scrape failure, per-repo enrichment 404 skipped. 15 tests in `tests/unit/sources/test_github.py` mirroring TC0022-TC0036 — all green. pyright 0/0/0, ruff clean. Status Draft → Ready → Planned → **Done**. |
