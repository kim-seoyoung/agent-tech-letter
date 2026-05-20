# TS0001: Content Ingestion

> **Status:** Ready
> **Epic:** [EP0001: Content Ingestion](../epics/EP0001-content-ingestion.md)
> **Created:** 2026-05-19
> **Last Updated:** 2026-05-19
> **TC Range:** TC0001–TC0055

## Overview

Test specification for the source-side of the pipeline: the `Item` model, the `SourceAdapter` protocol, the three concrete adapters (arXiv, GitHub Trending, RSS), and the source registry that wires them together via `config/sources.yaml`.

The spec is grounded in the [Test Strategy Document](../tsd.md) and inherits its tiered coverage targets (≥85% overall line, ≥95% line + branch for pure helpers — which here means `techletter/models/`, `techletter/sources/github.py::infer_maturity`, and any URL/datetime/text helpers used by the adapters).

Three test types are required:

1. **Unit** — pure pydantic validation, FakeAdapter conformance, `infer_maturity` table-driven cases, helper functions. Fast, no I/O.
2. **Integration** — adapter happy paths replayed from **VCR cassettes** for arXiv/GitHub/RSS; adapter failure modes (retries, 4xx/5xx, isolation) driven by **pytest-httpx** with explicit response queues.
3. **Pipeline-light** — the registry's `fetch_all` with three stubbed adapters, exercised for aggregation, dedupe, isolation, and stable ordering. The full draft pipeline E2E lives in `tests/pipeline/test_full_run.py` (TSD-defined) and is not duplicated here.

## Scope

### Stories Covered

| Story | Title | Priority |
|-------|-------|----------|
| [US0001](../stories/US0001-item-model-and-source-adapter-protocol.md) | Item model + SourceAdapter protocol | P0 (foundation) |
| [US0002](../stories/US0002-arxiv-source-adapter.md) | arXiv source adapter | P0 |
| [US0003](../stories/US0003-github-trending-source-adapter.md) | GitHub Trending source adapter | P0 |
| [US0004](../stories/US0004-rss-source-adapter.md) | RSS source adapter | P0 |
| [US0005](../stories/US0005-source-registry-and-config-loader.md) | Source registry + config loader | P0 |

### AC Coverage Matrix

| Story | AC | Description | Test Cases | Status |
|-------|-----|-------------|------------|--------|
| US0001 | AC1 | `Item` model defined and importable, all fields present | TC0001, TC0002 | Covered |
| US0001 | AC2 | `SourceAdapter` protocol defined | TC0009 | Covered |
| US0001 | AC3 | `FakeAdapter` passes pyright protocol check | TC0009, TC0010 | Covered |
| US0001 | AC4 | Validation rejects malformed items | TC0003, TC0006, TC0007, TC0008, TC0011 | Covered |
| US0001 | AC5 | tz-naive `published_at` rejected | TC0004 | Covered |
| US0002 | AC1 | `ArxivAdapter` conformant | TC0012 | Covered |
| US0002 | AC2 | Fetch returns recent items from configured categories | TC0013, TC0014 | Covered |
| US0002 | AC3 | Keyword filter (case-insensitive) | TC0015 | Covered |
| US0002 | AC4 | Empty result valid | TC0016 | Covered |
| US0002 | AC5 | Retry on transient 503 | TC0017 | Covered |
| US0002 | AC6 | Permanent failure → `SourceFetchError` | TC0018 | Covered |
| US0003 | AC1 | `GitHubTrendingAdapter` conformant | TC0021 | Covered |
| US0003 | AC2 | Scrapes trending page, parses repo list | TC0022, TC0023 | Covered |
| US0003 | AC3 | Enriches with shipping signals | TC0024, TC0025 | Covered |
| US0003 | AC4 | `maturity` inferred from signals (4 tiers) | TC0026 | Covered |
| US0003 | AC5 | Scrape failure fails soft (returns `[]`) | TC0027 | Covered |
| US0003 | AC6 | `GITHUB_TOKEN` Auth header on REST | TC0028 | Covered |
| US0003 | AC7 | Per-repo enrichment 404 → omit, keep others | TC0029 | Covered |
| US0004 | AC1 | `RssAdapter` conformant | TC0031 | Covered |
| US0004 | AC2 | Aggregates items from multiple feeds + tags `source_subtype` | TC0032, TC0033 | Covered |
| US0004 | AC3 | Window filter | TC0034 | Covered |
| US0004 | AC4 | Per-feed failure isolation | TC0035 | Covered |
| US0004 | AC5 | Tolerates malformed XML (`bozo`) | TC0036 | Covered |
| US0004 | AC6 | Items missing `published` skipped | TC0037 | Covered |
| US0005 | AC1 | Config schema validated | TC0041, TC0042 | Covered |
| US0005 | AC2 | Registry constructs adapters from config | TC0043, TC0044 | Covered |
| US0005 | AC3 | `fetch_all` aggregates + dedupes by URL | TC0045, TC0046 | Covered |
| US0005 | AC4 | Per-source failure isolation | TC0047 | Covered |
| US0005 | AC5 | All sources fail → `[]` + warning, no exception | TC0048 | Covered |
| US0005 | AC6 | Config-file errors are loud | TC0049, TC0050 | Covered |
| US0005 | AC7 | Adding a feed is a one-line config edit | TC0051 | Covered |

**Coverage:** 31 / 31 ACs covered. **Uncovered: 0.** Spec is eligible to move from Draft → Ready.

### Test Types Required

| Type | Required | Rationale |
|------|----------|-----------|
| Unit | Yes | Item model, `infer_maturity`, helper functions, FakeAdapter protocol conformance — all pure logic with high branch density |
| Integration | Yes | Adapters are I/O-bound; VCR cassettes + pytest-httpx are the only honest way to verify behaviour against real upstream shape |
| E2E | No (covered by TSD pipeline test) | The TSD's `tests/pipeline/test_full_run.py` exercises the full draft path with stubbed sources; this spec stops at the registry boundary |

---

## Environment

| Requirement | Details |
|-------------|---------|
| Prerequisites | Python 3.11+, uv-managed venv per TRD; pytest ≥ 8.0, pytest-cov, vcrpy / pytest-recording, pytest-httpx, hypothesis, freezegun |
| External Services | **None at test time.** arXiv/GitHub/RSS responses replayed from VCR cassettes in `tests/cassettes/{arxiv,github,rss}/`. No live HTTP. |
| Test Data | Cassettes captured 2026-05-19 (refresh manually when upstream shape drifts); JSON/YAML fixtures embedded in this spec for unit tests |
| Clock | Default frozen at `2026-05-19T00:00:00Z` via `freezegun` so window-day filters are deterministic |
| Env vars | `GITHUB_TOKEN` is **never** set in CI; one specific test (TC0028) sets a synthetic value via monkeypatch |

---

## Test Cases

### TC0001: Item round-trip preserves all fields including tz-aware datetime

**Type:** Unit | **Priority:** P0 | **Story:** US0001 (AC1)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | A valid item dict with every field populated (see Fixture `valid_item`) | dict parses cleanly |
| When | `Item.model_validate(valid_item).model_dump(mode="json")` is fed back into `Item.model_validate` | A new `Item` is produced |
| Then | The reconstructed `Item` equals the original | `published_at` preserves tz offset |

**Assertions:**
- [ ] `item2 == item1`
- [ ] `item2.published_at.tzinfo is not None`
- [ ] `str(item2.url).startswith("https://")`

---

### TC0002: Item constructs from minimum required fields with documented defaults

**Type:** Unit | **Priority:** P0 | **Story:** US0001 (AC1)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | A dict with only required fields (`source`, `title`, `url`, `summary_excerpt`, `published_at`, `item_kind`, `raw`) | n/a |
| When | `Item.model_validate(dict)` is called | Returns an `Item` |
| Then | `source_subtype is None`, `score is None`, `maturity is None` | Defaults match spec |

**Assertions:**
- [ ] `item.source_subtype is None`
- [ ] `item.score is None`
- [ ] `item.maturity is None`

---

### TC0003: Missing required field raises `ValidationError` naming the field

**Type:** Unit | **Priority:** P0 | **Story:** US0001 (AC4)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | The `valid_item` fixture with the `url` key removed | n/a |
| When | `Item.model_validate(dict)` | Raises `pydantic.ValidationError` |
| Then | Error message mentions `"url"` and `"field required"` | Parametrised over every required field |

**Assertions:**
- [ ] Parametrised over `source`, `title`, `url`, `summary_excerpt`, `published_at`, `item_kind`, `raw`
- [ ] Each parametrised case raises `ValidationError` mentioning the missing field

---

### TC0004: tz-naive `published_at` is rejected at validation time

**Type:** Unit | **Priority:** P0 | **Story:** US0001 (AC5)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | The `valid_item` fixture with `published_at = datetime(2026,5,19,12,0,0)` (no tzinfo) | n/a |
| When | `Item.model_validate(dict)` | Raises `pydantic.ValidationError` |
| Then | Error message indicates the datetime must be timezone-aware | Validator name surfaces in message |

**Assertions:**
- [ ] `ValidationError` raised
- [ ] Message contains `"timezone"` or `"tz-aware"`

---

### TC0005: Frozen `Item` rejects mutation after construction

**Type:** Unit | **Priority:** P1 | **Story:** US0001 (technical note, AC1 invariant)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | A valid `Item` instance | n/a |
| When | `item.title = "x"` | Raises `pydantic.ValidationError` (frozen) |
| Then | The original `item.title` is unchanged | n/a |

**Assertions:**
- [ ] Mutation raises
- [ ] `item.title` remains as originally constructed

---

### TC0006: Unknown `item_kind` literal is rejected

**Type:** Unit | **Priority:** P1 | **Story:** US0001 (AC4)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | `valid_item` with `item_kind = "video"` | n/a |
| When | `Item.model_validate(dict)` | Raises `ValidationError` |
| Then | Error message lists allowed values: `paper`, `blog_post`, `repo` | Same for `maturity` outside its enum |

**Assertions:**
- [ ] `ValidationError` mentions allowed `item_kind` values
- [ ] Parallel case for `maturity = "stable"` (outside enum) also raises

---

### TC0007: `summary_excerpt` exceeding 1000 chars is rejected

**Type:** Unit | **Priority:** P1 | **Story:** US0001 (AC4, edge)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | `valid_item` with `summary_excerpt = "a" * 1001` | n/a |
| When | `Item.model_validate(dict)` | Raises `ValidationError` |
| Then | Error message indicates `max_length` constraint | n/a |

**Assertions:**
- [ ] `ValidationError` raised
- [ ] Boundary: `"a" * 1000` validates successfully

---

### TC0008: Non-http URL scheme is rejected

**Type:** Unit | **Priority:** P1 | **Story:** US0001 (AC4)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | `valid_item` with `url = "ftp://example.com/x"` | n/a |
| When | `Item.model_validate(dict)` | Raises `ValidationError` |
| Then | pydantic `HttpUrl` rejects non-http(s) scheme | Boundary: `https://...` validates |

**Assertions:**
- [ ] `ftp://` raises
- [ ] `file:///` raises
- [ ] `https://example.com` validates

---

### TC0009: `FakeAdapter` satisfies the `SourceAdapter` protocol per pyright

**Type:** Unit | **Priority:** P0 | **Story:** US0001 (AC2, AC3)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | `class FakeAdapter` defined with `name = "fake"` and `fetch(self, window_days: int) -> list[Item]` returning 2 valid `Item`s | n/a |
| When | `FakeAdapter()` is assigned to a variable annotated `SourceAdapter` and `pyright --outputjson tests/protocol_assert.py` runs | Zero pyright diagnostics |
| Then | The fetch call at runtime returns 2 items | n/a |

**Assertions:**
- [ ] Pyright reports 0 errors and 0 warnings for the protocol-assert module
- [ ] `adapter.fetch(7)` returns `list[Item]` of length 2

---

### TC0010: `FakeAdapter` returning `[]` is a valid result (no exception)

**Type:** Unit | **Priority:** P2 | **Story:** US0001 (AC3, edge)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | A `FakeAdapter` whose `fetch` returns `[]` | n/a |
| When | `adapter.fetch(window_days=7)` | Returns `[]` |
| Then | No exception raised | The downstream pipeline treats empty as "no items this run" |

**Assertions:**
- [ ] `len(result) == 0`
- [ ] Result is an instance of `list`

---

### TC0011: Hypothesis property — any valid input dict round-trips equal

**Type:** Unit (property-based) | **Priority:** P1 | **Story:** US0001 (AC1, AC4)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | A hypothesis strategy generating valid `Item` dicts (tz-aware datetimes, http urls, in-range excerpts, valid enums) | n/a |
| When | For each generated dict: `Item.model_validate(dict).model_dump(mode="json")` is re-validated | Result equals the first parse |
| Then | No counter-example found within `max_examples=200` | Property holds |

**Assertions:**
- [ ] `assert item_round_trip == item_first`
- [ ] No `ValidationError` raised for any generated valid dict
- [ ] Parallel negative strategy: generated *invalid* dicts always raise `ValidationError`

---

### TC0012: `ArxivAdapter` is protocol-conformant

**Type:** Unit | **Priority:** P0 | **Story:** US0002 (AC1)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | `from techletter.sources.arxiv import ArxivAdapter` | Import succeeds |
| When | `ArxivAdapter()` instantiated | `name == "arxiv"`; pyright sees it as `SourceAdapter` |
| Then | `fetch(0)` returns `list[Item]` (may be empty) | Type-check passes |

**Assertions:**
- [ ] `adapter.name == "arxiv"`
- [ ] Pyright treats the instance as `SourceAdapter`

---

### TC0013: arXiv fetch returns recent items from configured categories (VCR happy path)

**Type:** Integration (VCR) | **Priority:** P0 | **Story:** US0002 (AC2)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | VCR cassette `tests/cassettes/arxiv/recent_cs_ai_cs_cl.yaml` captured 2026-05-19; clock frozen at `2026-05-19T00:00:00Z` | Cassette replays without live HTTP |
| When | `ArxivAdapter(categories=["cs.AI","cs.CL"], keywords=["agent","tool-use","LLM"]).fetch(window_days=7)` | Returns a non-empty `list[Item]` |
| Then | Every item has `source="arxiv"`, `item_kind="paper"`, `source_subtype` in `{"cs.AI","cs.CL"}`, `url` is an arXiv abstract URL, and `published_at` within the last 7 days | Cassette-asserted shape |

**Assertions:**
- [ ] All items: `source == "arxiv"` and `item_kind == "paper"`
- [ ] All items: `source_subtype in {"cs.AI","cs.CL"}`
- [ ] All items: `url.host == "arxiv.org"`
- [ ] All items: `(now - published_at).days <= 7`

---

### TC0014: arXiv excludes papers outside the window even if otherwise matching

**Type:** Unit (fixture-based) | **Priority:** P1 | **Story:** US0002 (AC2)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | Fixture of 10 arXiv-shaped entries: 7 within last 7 days, 3 older than 7 days | n/a |
| When | Adapter's internal `_filter_window(entries, 7)` is called | Returns 7 entries |
| Then | The 3 older entries are excluded by `published_at` comparison | Boundary: an entry exactly `7d - 1s` old is included |

**Assertions:**
- [ ] `len(filtered) == 7`
- [ ] No filtered entry has `published_at < now - timedelta(days=7)`

---

### TC0015: arXiv keyword filter is case-insensitive against title + abstract

**Type:** Unit (fixture-based) | **Priority:** P1 | **Story:** US0002 (AC3)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | Fixture of 5 entries: 3 with `"agent"` or `"Tool-Use"` in title/abstract (mixed case), 2 vision-only | n/a |
| When | Adapter's internal `_keyword_filter(entries, ["agent","tool-use"])` is called | Returns 3 entries |
| Then | Matching ignores case; an entry whose title says `"AGENT"` still matches | n/a |

**Assertions:**
- [ ] `len(matched) == 3`
- [ ] An all-caps title match is kept; a vision-only entry is dropped

---

### TC0016: arXiv empty response returns `[]` without exception

**Type:** Integration (pytest-httpx) | **Priority:** P1 | **Story:** US0002 (AC4)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | pytest-httpx mock returns a valid empty arXiv feed (no entries) | n/a |
| When | `adapter.fetch(window_days=7)` | Returns `[]` |
| Then | No exception raised | Info log mentions "0 items" |

**Assertions:**
- [ ] `result == []`
- [ ] No exception
- [ ] At least one INFO-level log line about the empty result

---

### TC0017: arXiv tenacity retries succeed after 503 × 2 then 200

**Type:** Integration (pytest-httpx) | **Priority:** P0 | **Story:** US0002 (AC5)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | pytest-httpx queue: 503, 503, 200 (with valid feed body) | n/a |
| When | `adapter.fetch(window_days=7)` | Returns the items from the third response |
| Then | Tenacity attempted 3 times; final result non-empty | Total attempts logged |

**Assertions:**
- [ ] `len(result) > 0`
- [ ] Mock observed 3 requests
- [ ] Log message contains "attempt 3" or equivalent

---

### TC0018: arXiv 503 × 5 raises `SourceFetchError` after retries exhausted

**Type:** Integration (pytest-httpx) | **Priority:** P0 | **Story:** US0002 (AC6)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | pytest-httpx returns 503 indefinitely | n/a |
| When | `adapter.fetch(window_days=7)` | Raises `SourceFetchError` |
| Then | Exception is the named `SourceFetchError`, not bare `Exception` | Log lists all 5 attempts |

**Assertions:**
- [ ] `pytest.raises(SourceFetchError)` succeeds
- [ ] Mock observed exactly 5 requests
- [ ] Exception chains the underlying `httpx.HTTPStatusError`

---

### TC0019: arXiv `window_days = -1` raises `ValueError` before any HTTP call

**Type:** Unit | **Priority:** P2 | **Story:** US0002 (edge)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | `adapter = ArxivAdapter()`; no HTTP mock configured | n/a |
| When | `adapter.fetch(window_days=-1)` | Raises `ValueError` |
| Then | No HTTP call was attempted | pytest-httpx records 0 requests |

**Assertions:**
- [ ] `pytest.raises(ValueError)`
- [ ] `httpx_mock.get_requests() == []`

---

### TC0020: arXiv `window_days = 1000` clamps to 365 with warning log

**Type:** Unit | **Priority:** P2 | **Story:** US0002 (edge)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | Stubbed HTTP returning empty feed | n/a |
| When | `adapter.fetch(window_days=1000)` | Internal computed window is 365 |
| Then | A WARNING log line is emitted mentioning the clamp | n/a |

**Assertions:**
- [ ] At least one log record at WARNING level mentions "clamp" or "365"
- [ ] No exception raised

---

### TC0021: `GitHubTrendingAdapter` is protocol-conformant

**Type:** Unit | **Priority:** P0 | **Story:** US0003 (AC1)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | `from techletter.sources.github import GitHubTrendingAdapter` | Import succeeds |
| When | `GitHubTrendingAdapter()` instantiated | `name == "github"`; pyright sees it as `SourceAdapter` |
| Then | `fetch` callable with `int → list[Item]` signature | n/a |

**Assertions:**
- [ ] `adapter.name == "github"`
- [ ] Pyright treats the instance as `SourceAdapter`

---

### TC0022: GitHub Trending parses 25 trending repos from fixture HTML

**Type:** Integration (VCR) | **Priority:** P0 | **Story:** US0003 (AC2)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | VCR cassette `tests/cassettes/github/trending_weekly_en.yaml` (HTML body + REST enrichment responses) | Cassette replays without live HTTP |
| When | `adapter.fetch(window_days=7)` | Returns up to 25 `Item`s |
| Then | Every item: `source="github"`, `item_kind="repo"`, `url` is `https://github.com/{owner}/{name}`, `title` matches `owner/name` | n/a |

**Assertions:**
- [ ] `1 <= len(result) <= 25`
- [ ] Every item: `source == "github"` and `item_kind == "repo"`
- [ ] Every item: `url.path` matches `/{owner}/{name}` shape

---

### TC0023: GitHub Trending skips a corrupted row, returns rest, logs the skip

**Type:** Unit (fixture-based) | **Priority:** P1 | **Story:** US0003 (AC2, edge)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | Fixture HTML with 25 valid trending rows and 1 row missing the repo-link `<a>` | n/a |
| When | `parse_trending_html(html)` is called | Returns 25 `RepoStub`s |
| Then | A WARNING log line mentions "1 unparseable row" | n/a |

**Assertions:**
- [ ] `len(stubs) == 25`
- [ ] WARNING log emitted with skip count of 1

---

### TC0024: GitHub Trending enriches each repo with all four shipping signals

**Type:** Integration (VCR) | **Priority:** P0 | **Story:** US0003 (AC3)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | VCR cassette with REST `GET /repos/{owner}/{name}` and `GET /repos/{owner}/{name}/releases?per_page=1` responses | n/a |
| When | Adapter constructs each `Item` | `raw` dict has keys `stars`, `last_commit_at`, `has_recent_release`, `hosted_demo_url` |
| Then | `stars` is int, `last_commit_at` is ISO-8601 UTC string, `has_recent_release` is bool, `hosted_demo_url` is str or None | n/a |

**Assertions:**
- [ ] For every item: `set(item.raw) >= {"stars","last_commit_at","has_recent_release","hosted_demo_url"}`
- [ ] `isinstance(item.raw["stars"], int)`
- [ ] `isinstance(item.raw["has_recent_release"], bool)`

---

### TC0025: GitHub `homepage` whitespace-only → `hosted_demo_url = None`

**Type:** Unit (fixture-based) | **Priority:** P2 | **Story:** US0003 (AC3, edge)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | REST response with `homepage = "   "` | n/a |
| When | Adapter's `_extract_demo_url(response)` is called | Returns `None` |
| Then | Parallel case: `homepage = "not-a-url"` → also `None`; `homepage = "https://x.com"` → kept | n/a |

**Assertions:**
- [ ] Whitespace → `None`
- [ ] Non-URL string → `None`
- [ ] Valid http(s) URL → kept as string

---

### TC0026: `infer_maturity` returns the correct tier for each input combination

**Type:** Unit (parametric) | **Priority:** P0 | **Story:** US0003 (AC4)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | Parametrised cases over `(stars, last_commit_age_days, has_recent_release, missing_field)` | n/a |
| When | `infer_maturity(metadata)` is called | Returns the expected `Maturity` literal |
| Then | All 4 tiers + the `unknown` fallback are exercised | See parametrisation below |

**Parametrisation (selected):**

| stars | last_commit_age | has_recent_release | Expected |
|------:|----------------:|:------------------:|----------|
| 1000  | 5 days          | True               | `production-ready` |
| 500   | 30 days         | True               | `production-ready` (boundary) |
| 499   | 30 days         | True               | `beta` (below stars threshold) |
| 75    | 10 days         | False              | `beta` |
| 75    | 31 days         | True               | `experimental` (commit too old) |
| 10    | 5 days          | False              | `experimental` (stars too few) |
| 100   | 100 days        | False              | `experimental` (commit > 90d) |
| any   | (missing pushed_at) | any            | `unknown` |

**Assertions:**
- [ ] All 8 parametrised rows pass
- [ ] No `Maturity` value other than the four documented literals is ever returned

---

### TC0027: Scrape 404 after retries exhausted → `fetch` returns `[]` (fails soft)

**Type:** Integration (pytest-httpx) | **Priority:** P0 | **Story:** US0003 (AC5)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | pytest-httpx returns 404 on the trending URL for all attempts | n/a |
| When | `adapter.fetch(window_days=7)` | Returns `[]` |
| Then | **No exception raised** (this is the critical invariant); WARNING log mentions URL and final status | The registry must not need to catch here |

**Assertions:**
- [ ] `result == []`
- [ ] No exception
- [ ] WARNING log mentions `404` and the trending URL

---

### TC0028: `GITHUB_TOKEN` env var → `Authorization: Bearer` header on REST calls

**Type:** Integration (pytest-httpx) | **Priority:** P1 | **Story:** US0003 (AC6)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | `monkeypatch.setenv("GITHUB_TOKEN", "ghp_fake_synthetic_value")`; pytest-httpx mocks scrape + REST | n/a |
| When | `adapter.fetch(window_days=7)` triggers REST enrichment | Captured REST request has `Authorization: Bearer ghp_fake_synthetic_value` header |
| Then | Without the env var, no `Authorization` header is sent | Parallel case asserts unauthenticated path |

**Assertions:**
- [ ] With token: REST request has `Authorization: Bearer ghp_fake_synthetic_value`
- [ ] Without token: REST request has no `Authorization` header
- [ ] **Secret-leak check:** token value does not appear in any captured log output

---

### TC0029: One repo's REST returns 404 → that repo is omitted; the rest are returned

**Type:** Integration (pytest-httpx) | **Priority:** P1 | **Story:** US0003 (AC7)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | Scrape returns 25 repos; REST returns 404 for one specific repo and 200 for the other 24 | n/a |
| When | `adapter.fetch(window_days=7)` | Returns 24 `Item`s |
| Then | The deleted repo's slug appears in a WARNING log | No exception |

**Assertions:**
- [ ] `len(result) == 24`
- [ ] The omitted repo's owner/name appears in a WARNING log line

---

### TC0030: REST 429 × 5 → `SourceFetchError` (persistent rate limit)

**Type:** Integration (pytest-httpx) | **Priority:** P2 | **Story:** US0003 (edge)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | Scrape returns 1 repo successfully; REST returns 429 indefinitely | n/a |
| When | `adapter.fetch(window_days=7)` | Raises `SourceFetchError` |
| Then | The registry catches it (TC0047); this isolation is verified separately | n/a |

**Assertions:**
- [ ] `pytest.raises(SourceFetchError)`
- [ ] REST received 5 attempts before the raise

---

### TC0031: `RssAdapter` is protocol-conformant

**Type:** Unit | **Priority:** P0 | **Story:** US0004 (AC1)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | `from techletter.sources.rss import RssAdapter` | Import succeeds |
| When | `RssAdapter(feeds=["https://example.com/feed"])` instantiated | `name == "rss"`; pyright sees it as `SourceAdapter` |
| Then | `fetch` accepts an int and returns `list[Item]` | n/a |

**Assertions:**
- [ ] `adapter.name == "rss"`
- [ ] Pyright treats the instance as `SourceAdapter`

---

### TC0032: RSS aggregates items from 3 feeds within window

**Type:** Integration (VCR) | **Priority:** P0 | **Story:** US0004 (AC2)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | VCR cassette `tests/cassettes/rss/three_feeds.yaml` with 3 feeds returning 4, 5, 3 items respectively, all within the 7-day window | n/a |
| When | `adapter.fetch(window_days=7)` | Returns 12 `Item`s |
| Then | All items: `source == "rss"`, `item_kind == "blog_post"`, `maturity is None` | n/a |

**Assertions:**
- [ ] `len(result) == 12`
- [ ] All items: `source == "rss"` and `item_kind == "blog_post"`

---

### TC0033: RSS items carry `source_subtype = <feed URL>` for attribution

**Type:** Integration (VCR) | **Priority:** P1 | **Story:** US0004 (AC2)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | Three feeds with distinct URLs (importai, latentspace, simonwillison) | n/a |
| When | `adapter.fetch(window_days=7)` aggregates | Items can be partitioned by `source_subtype` back to their origin feed |
| Then | Each `source_subtype` is one of the three configured feed URLs | n/a |

**Assertions:**
- [ ] `{item.source_subtype for item in result}` is a subset of the configured feed URLs
- [ ] Every item has a non-None `source_subtype`

---

### TC0034: RSS window filter excludes items older than `window_days`

**Type:** Unit (fixture-based) | **Priority:** P1 | **Story:** US0004 (AC3)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | Fixture feed with 10 items spanning the last 30 days; clock frozen at `2026-05-19T00:00:00Z` | n/a |
| When | `adapter.fetch(window_days=7)` | Returns 7 items (those within window) |
| Then | Boundary: item exactly at `7d - 1s` old is included | n/a |

**Assertions:**
- [ ] `len(result) == 7`
- [ ] No result item has `published_at < now - timedelta(days=7)`

---

### TC0035: Per-feed failure isolation — feed #2 fails, #1 and #3 succeed

**Type:** Integration (pytest-httpx) | **Priority:** P0 | **Story:** US0004 (AC4)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | 3 feeds configured; pytest-httpx returns 500 for feed #2 on all attempts, 200 for #1 and #3 | n/a |
| When | `adapter.fetch(window_days=7)` | Returns items from #1 + #3 only |
| Then | Feed #2's failure is logged with its URL and final error | **No exception propagates out of `fetch`** |

**Assertions:**
- [ ] Result contains only items whose `source_subtype` matches feed #1 or feed #3 URL
- [ ] No exception
- [ ] WARNING log line contains feed #2's URL and `500`

---

### TC0036: `feedparser` `bozo` flag with valid items present → items returned + warning

**Type:** Unit (fixture-based) | **Priority:** P1 | **Story:** US0004 (AC5)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | A feed body that triggers `bozo=1` but yields 3 well-formed entries | n/a |
| When | Adapter's per-feed parse step runs | Returns 3 items |
| Then | A WARNING log line mentions the feed URL and "malformed" | No exception |

**Assertions:**
- [ ] `len(result) == 3`
- [ ] WARNING log emitted with the feed URL

---

### TC0037: Items missing `published` field are skipped; others returned

**Type:** Unit (fixture-based) | **Priority:** P1 | **Story:** US0004 (AC6)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | A feed with 5 entries: 3 fully-formed, 2 missing `published_parsed` | n/a |
| When | Adapter's per-feed parse step runs | Returns 3 items |
| Then | 2 WARNING log lines mention the skipped item titles (or `<no title>`) and the feed URL | n/a |

**Assertions:**
- [ ] `len(result) == 3`
- [ ] Exactly 2 WARNING log lines reference skipped entries

---

### TC0038: Atom feed parses equivalently to RSS 2.0

**Type:** Unit (fixture-based) | **Priority:** P2 | **Story:** US0004 (edge)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | Same 3 items expressed in both RSS 2.0 and Atom formats (Simon Willison's feed is Atom) | n/a |
| When | Adapter parses each | Result items are equal modulo `raw` |
| Then | `title`, `url`, `published_at`, `summary_excerpt` match across both formats | n/a |

**Assertions:**
- [ ] For each i: `rss_result[i].title == atom_result[i].title`
- [ ] For each i: `rss_result[i].url == atom_result[i].url`
- [ ] For each i: `rss_result[i].published_at == atom_result[i].published_at`

---

### TC0039: Empty `feeds=[]` returns `[]` without error

**Type:** Unit | **Priority:** P2 | **Story:** US0004 (edge)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | `adapter = RssAdapter(feeds=[])`; no HTTP mock | n/a |
| When | `adapter.fetch(window_days=7)` | Returns `[]` |
| Then | No HTTP attempted | n/a |

**Assertions:**
- [ ] `result == []`
- [ ] `httpx_mock.get_requests() == []`

---

### TC0040: `summary_excerpt` length 1500 → truncated to 1000 chars with marker

**Type:** Unit (fixture-based) | **Priority:** P2 | **Story:** US0004 (edge)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | A feed entry whose `summary` is 1500 chars | n/a |
| When | Adapter constructs the `Item` | `summary_excerpt` is exactly 1000 chars |
| Then | The trailing chars include a truncation marker (e.g., `…`) | pydantic validation passes |

**Assertions:**
- [ ] `len(item.summary_excerpt) == 1000`
- [ ] `item.summary_excerpt.endswith("…")` (or the agreed-upon marker)

---

### TC0041: Valid `sources.yaml` loads into a fully-populated `SourcesConfig`

**Type:** Unit | **Priority:** P0 | **Story:** US0005 (AC1)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | The default `config/sources.yaml` shipped with the repo (arxiv + github + rss, 4 feeds) | File exists |
| When | `load_sources(path)` | Returns `SourcesConfig` instance |
| Then | All three sub-configs are populated; `rss.feeds` has 4 entries | n/a |

**Assertions:**
- [ ] `config.arxiv.enabled is True`
- [ ] `config.github.enabled is True`
- [ ] `config.rss.enabled is True`
- [ ] `len(config.rss.feeds) == 4`

---

### TC0042: Missing top-level source key defaults to `enabled=false` for that source

**Type:** Unit | **Priority:** P1 | **Story:** US0005 (AC1)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | A YAML file containing only `arxiv:` block (no `github:`, no `rss:`) | n/a |
| When | `load_sources(path)` | Returns `SourcesConfig` |
| Then | `config.github.enabled is False`; `config.rss.enabled is False` | No `ValidationError` |

**Assertions:**
- [ ] `config.github.enabled is False`
- [ ] `config.rss.enabled is False`

---

### TC0043: `build_registry` constructs only enabled adapters

**Type:** Unit | **Priority:** P0 | **Story:** US0005 (AC2)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | A `SourcesConfig` with `arxiv.enabled=True`, `github.enabled=False`, `rss.enabled=True` | n/a |
| When | `build_registry(config)` is called | Returns a registry whose keys are exactly `{"arxiv","rss"}` |
| Then | No `GitHubTrendingAdapter` instance was constructed | n/a |

**Assertions:**
- [ ] `set(registry.adapters) == {"arxiv","rss"}`
- [ ] `"github" not in registry.adapters`

---

### TC0044: Each adapter receives its config-derived kwargs

**Type:** Unit | **Priority:** P1 | **Story:** US0005 (AC2)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | A config where `arxiv.keywords = ["llm-agent","ReAct"]` and `rss.feeds = ["https://x/feed"]` | Adapter classes patched to record their init kwargs |
| When | `build_registry(config)` | Each adapter's recorded init kwargs match the config |
| Then | `ArxivAdapter` saw `keywords=["llm-agent","ReAct"]`; `RssAdapter` saw `feeds=["https://x/feed"]` | n/a |

**Assertions:**
- [ ] `recorded_arxiv_kwargs["keywords"] == ["llm-agent","ReAct"]`
- [ ] `recorded_rss_kwargs["feeds"] == ["https://x/feed"]`

---

### TC0045: `fetch_all` aggregates items from all three stubbed adapters

**Type:** Integration (pipeline-light) | **Priority:** P0 | **Story:** US0005 (AC3)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | Registry with three stubbed adapters returning 3, 2, 4 unique items respectively | n/a |
| When | `registry.fetch_all(window_days=7)` | Returns 9 items |
| Then | Order is stable: `arxiv` items first, then `github`, then `rss` (or whatever the documented order is) | Repeat call returns same order |

**Assertions:**
- [ ] `len(result) == 9`
- [ ] `[i.source for i in result]` is sorted by the documented adapter order
- [ ] Two consecutive `fetch_all` calls return items in identical order

---

### TC0046: `fetch_all` deduplicates items by URL — first occurrence wins

**Type:** Integration (pipeline-light) | **Priority:** P0 | **Story:** US0005 (AC3)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | Two stubbed adapters returning items where one URL appears in both | n/a |
| When | `registry.fetch_all(window_days=7)` | Result contains the duplicated URL exactly once |
| Then | The retained item is the one from the first adapter in registration order | n/a |

**Assertions:**
- [ ] `len({i.url for i in result}) == len(result)`
- [ ] The retained item's `source` matches the first adapter

---

### TC0047: One stubbed adapter raises `SourceFetchError` → others' items returned, log mentions the failure

**Type:** Integration (pipeline-light) | **Priority:** P0 | **Story:** US0005 (AC4)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | Three stubbed adapters; `github` raises `SourceFetchError("503")` | n/a |
| When | `registry.fetch_all(window_days=7)` | Returns items from `arxiv` + `rss` only |
| Then | **No exception propagates** | Log line: `"source 'github' failed: 503"` |

**Assertions:**
- [ ] No exception raised
- [ ] Result contains no items with `source == "github"`
- [ ] WARNING/ERROR log line contains both `'github'` and the error message

---

### TC0048: All three adapters fail → `fetch_all` returns `[]` with warning, no exception

**Type:** Integration (pipeline-light) | **Priority:** P0 | **Story:** US0005 (AC5)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | All three stubbed adapters raise `SourceFetchError` | n/a |
| When | `registry.fetch_all(window_days=7)` | Returns `[]` |
| Then | A WARNING log: `"all sources failed; no items fetched"` | Decision to abort or continue is the orchestration layer's, not the registry's |

**Assertions:**
- [ ] `result == []`
- [ ] No exception
- [ ] WARNING log line matches the documented "all sources failed" message

---

### TC0049: Malformed YAML → `ConfigLoadError` mentioning file and parser error

**Type:** Unit | **Priority:** P1 | **Story:** US0005 (AC6)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | A YAML file with bad indentation that pyyaml cannot parse | n/a |
| When | `load_sources(path)` | Raises `ConfigLoadError` |
| Then | The exception message references the file path | The underlying `yaml.YAMLError` is `__cause__` |

**Assertions:**
- [ ] `pytest.raises(ConfigLoadError)`
- [ ] Exception message mentions the path
- [ ] `exc.__cause__` is a `yaml.YAMLError` (or pyyaml's parser exception)

---

### TC0050: pydantic validation failure → `ConfigLoadError` with field-level path

**Type:** Unit | **Priority:** P1 | **Story:** US0005 (AC6)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | A YAML file with `arxiv.categories: 42` (wrong type) | n/a |
| When | `load_sources(path)` | Raises `ConfigLoadError` |
| Then | The exception message includes the field path `arxiv.categories` | `__cause__` is `pydantic.ValidationError` |

**Assertions:**
- [ ] `pytest.raises(ConfigLoadError)` with message containing `arxiv.categories`
- [ ] `isinstance(exc.__cause__, pydantic.ValidationError)`

---

### TC0051: Adding a feed URL to `sources.yaml` and re-loading includes it in `fetch_all` results

**Type:** Integration (pipeline-light) | **Priority:** P0 | **Story:** US0005 (AC7)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | `sources.yaml` with 4 RSS feeds; the `RssAdapter` is patched to record which feeds it received | n/a |
| When | Append `"https://example.com/new-feed"` to `rss.feeds`, re-load, re-build registry, call `fetch_all` | The patched `RssAdapter` records 5 feeds, including the new URL |
| Then | **No code changes were required** between the two runs | Adapter class is identical across runs |

**Assertions:**
- [ ] First run: recorded feeds list has 4 entries
- [ ] Second run: recorded feeds list has 5 entries including the new URL
- [ ] No code module was reimported/reloaded between the two runs

---

### TC0052: `sources.yaml` file not found → `ConfigLoadError`

**Type:** Unit | **Priority:** P2 | **Story:** US0005 (edge)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | A path that does not exist on disk | n/a |
| When | `load_sources(missing_path)` | Raises `ConfigLoadError` |
| Then | The message contains the path and "not found" (or platform equivalent) | `__cause__` is `FileNotFoundError` |

**Assertions:**
- [ ] `pytest.raises(ConfigLoadError)`
- [ ] `isinstance(exc.__cause__, FileNotFoundError)`

---

### TC0053: Unknown top-level source key (typo) → `ValidationError` surfacing as `ConfigLoadError`

**Type:** Unit | **Priority:** P1 | **Story:** US0005 (AC1 — `extra="forbid"`)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | YAML containing `reddit:` as a top-level key | n/a |
| When | `load_sources(path)` | Raises `ConfigLoadError` |
| Then | The message mentions `"reddit"` as an unknown key | `__cause__` is `pydantic.ValidationError` |

**Assertions:**
- [ ] `pytest.raises(ConfigLoadError)` with message containing `"reddit"`
- [ ] `isinstance(exc.__cause__, pydantic.ValidationError)`

---

### TC0054: Adapter constructor raises → that source omitted from registry, others proceed

**Type:** Unit | **Priority:** P2 | **Story:** US0005 (edge)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | `ArxivAdapter.__init__` patched to raise on construction; `github` and `rss` enabled | n/a |
| When | `build_registry(config)` | Returns a registry without `arxiv`; `github` and `rss` present |
| Then | WARNING log mentions `arxiv` and the constructor exception | n/a |

**Assertions:**
- [ ] `"arxiv" not in registry.adapters`
- [ ] `"github" in registry.adapters and "rss" in registry.adapters`
- [ ] WARNING log mentions `'arxiv'` and the exception type

---

### TC0055: `fetch_all` ordering is stable across runs with identical inputs

**Type:** Integration (pipeline-light) | **Priority:** P1 | **Story:** US0005 (AC3 reproducibility)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | Three stubbed adapters returning fixed item lists | n/a |
| When | `fetch_all(7)` is called 5 times in succession | All 5 results have identical `[i.url for i in result]` sequences |
| Then | Reproducibility holds — no reliance on dict ordering, set iteration, or wall-clock | n/a |

**Assertions:**
- [ ] All 5 runs produce identical URL sequences
- [ ] Property holds when adapters are re-registered in the same order

---

## Fixtures

```yaml
# tests/fixtures/items/valid_item.yaml — the canonical valid Item dict.
# Used by TC0001–TC0008 for negative parametrisation (removing or mutating one field at a time).
valid_item:
  source: "arxiv"
  source_subtype: "cs.AI"
  title: "Toolformer: Language Models Can Teach Themselves to Use Tools"
  url: "https://arxiv.org/abs/2302.04761"
  summary_excerpt: "We introduce Toolformer, a model trained to decide which APIs to call..."
  score: null
  published_at: "2026-05-15T08:00:00+00:00"
  item_kind: "paper"
  maturity: null
  raw:
    arxiv_id: "2302.04761"
    primary_category: "cs.CL"

# tests/fixtures/sources/arxiv_keyword_fixture.yaml — for TC0014 and TC0015.
arxiv_entries:
  - title: "Agent-based reasoning with tool-use"
    abstract: "We propose an LLM agent that uses tools..."
    published: "2026-05-18T00:00:00Z"
    primary_category: "cs.AI"
  - title: "Vision Transformers at scale"
    abstract: "Pre-training large ViTs..."
    published: "2026-05-18T00:00:00Z"
    primary_category: "cs.CV"
  - title: "ReAct: Reasoning + Acting in Language Models"
    abstract: "We present ReAct, a framework where..."
    published: "2026-05-12T00:00:00Z"
    primary_category: "cs.CL"

# tests/fixtures/sources/github_maturity_table.yaml — drives TC0026.
infer_maturity_cases:
  - { stars: 1000, last_commit_age_days: 5,   has_recent_release: true,  expected: "production-ready" }
  - { stars: 500,  last_commit_age_days: 30,  has_recent_release: true,  expected: "production-ready" }
  - { stars: 499,  last_commit_age_days: 30,  has_recent_release: true,  expected: "beta" }
  - { stars: 75,   last_commit_age_days: 10,  has_recent_release: false, expected: "beta" }
  - { stars: 75,   last_commit_age_days: 31,  has_recent_release: true,  expected: "experimental" }
  - { stars: 10,   last_commit_age_days: 5,   has_recent_release: false, expected: "experimental" }
  - { stars: 100,  last_commit_age_days: 100, has_recent_release: false, expected: "experimental" }
  - { stars: 100,  last_commit_age_days: null, has_recent_release: false, expected: "unknown" }

# tests/fixtures/sources/rss_three_feeds.yaml — drives TC0032 and TC0033.
rss_three_feeds:
  - url: "https://importai.substack.com/feed"
    item_count: 4
  - url: "https://www.latent.space/feed"
    item_count: 5
  - url: "https://simonwillison.net/atom/everything/"
    item_count: 3
```

**Cassettes (binary fixtures, not embedded):**

- `tests/cassettes/arxiv/recent_cs_ai_cs_cl.yaml` — TC0013
- `tests/cassettes/github/trending_weekly_en.yaml` — TC0022, TC0024
- `tests/cassettes/rss/three_feeds.yaml` — TC0032, TC0033

Cassettes are recorded against live upstream once (2026-05-19), then replayed offline. Manual refresh policy per TSD: re-record on upstream shape drift, review the diff in PR.

---

## Automation Status

| TC | Title | Status | Implementation |
|----|-------|--------|----------------|
| TC0001 | Item round-trip preserves fields | Pending | - |
| TC0002 | Item constructs from minimum fields | Pending | - |
| TC0003 | Missing required field raises | Pending | - |
| TC0004 | tz-naive published_at rejected | Pending | - |
| TC0005 | Frozen Item rejects mutation | Pending | - |
| TC0006 | Unknown item_kind rejected | Pending | - |
| TC0007 | summary_excerpt > 1000 rejected | Pending | - |
| TC0008 | Non-http URL rejected | Pending | - |
| TC0009 | FakeAdapter pyright protocol check | Pending | - |
| TC0010 | FakeAdapter empty fetch valid | Pending | - |
| TC0011 | Hypothesis: valid Item round-trip | Pending | - |
| TC0012 | ArxivAdapter protocol conformance | Pending | - |
| TC0013 | arXiv VCR happy path | Pending | - |
| TC0014 | arXiv window filter | Pending | - |
| TC0015 | arXiv keyword filter case-insensitive | Pending | - |
| TC0016 | arXiv empty response → [] | Pending | - |
| TC0017 | arXiv 503×2 then 200 — retries succeed | Pending | - |
| TC0018 | arXiv 503×5 → SourceFetchError | Pending | - |
| TC0019 | arXiv window_days = -1 → ValueError | Pending | - |
| TC0020 | arXiv window_days = 1000 clamped | Pending | - |
| TC0021 | GitHubTrendingAdapter protocol conformance | Pending | - |
| TC0022 | GitHub Trending parses 25 rows | Pending | - |
| TC0023 | GitHub Trending corrupted row skipped | Pending | - |
| TC0024 | GitHub Trending REST enrichment | Pending | - |
| TC0025 | GitHub homepage whitespace → None | Pending | - |
| TC0026 | infer_maturity parametric (8 rows) | Pending | - |
| TC0027 | GitHub scrape 404 → fails soft | Pending | - |
| TC0028 | GITHUB_TOKEN → Auth header | Pending | - |
| TC0029 | One repo 404 on REST → omit, others kept | Pending | - |
| TC0030 | REST 429×5 → SourceFetchError | Pending | - |
| TC0031 | RssAdapter protocol conformance | Pending | - |
| TC0032 | RSS aggregates 3 feeds | Pending | - |
| TC0033 | RSS source_subtype = feed URL | Pending | - |
| TC0034 | RSS window filter | Pending | - |
| TC0035 | RSS per-feed isolation | Pending | - |
| TC0036 | RSS bozo flag tolerated | Pending | - |
| TC0037 | RSS missing `published` skipped | Pending | - |
| TC0038 | RSS / Atom parity | Pending | - |
| TC0039 | RSS empty feeds list | Pending | - |
| TC0040 | RSS summary 1500 → 1000 trunc | Pending | - |
| TC0041 | sources.yaml valid load | Pending | - |
| TC0042 | Missing top-level key defaults to disabled | Pending | - |
| TC0043 | build_registry only enabled sources | Pending | - |
| TC0044 | Adapter receives config kwargs | Pending | - |
| TC0045 | fetch_all aggregates 3 stubbed adapters | Pending | - |
| TC0046 | fetch_all dedupes by URL | Pending | - |
| TC0047 | One adapter raises → others returned | Pending | - |
| TC0048 | All adapters fail → [] + warning | Pending | - |
| TC0049 | Malformed YAML → ConfigLoadError | Pending | - |
| TC0050 | pydantic ValidationError chained | Pending | - |
| TC0051 | Add feed → included without code change | Pending | - |
| TC0052 | File not found → ConfigLoadError | Pending | - |
| TC0053 | Unknown top-level key → ValidationError | Pending | - |
| TC0054 | Adapter constructor raises → omitted | Pending | - |
| TC0055 | fetch_all stable ordering | Pending | - |

---

## Test Files Plan

When `/sdlc-studio test-automation --spec TS0001` runs, the following files will be generated (per TSD directory layout):

```text
tests/
  unit/
    test_models.py              # TC0001–TC0008, TC0011
    test_sources_base.py        # TC0009, TC0010
    sources/
      test_arxiv_helpers.py     # TC0014, TC0015, TC0019, TC0020
      test_github_helpers.py    # TC0023, TC0025, TC0026
      test_rss_helpers.py       # TC0034, TC0036, TC0037, TC0038, TC0039, TC0040
    config/
      test_load_sources.py      # TC0041, TC0042, TC0049, TC0050, TC0052, TC0053
    test_registry.py            # TC0043, TC0044, TC0054
  integration/
    sources/
      test_arxiv_adapter.py     # TC0012, TC0013, TC0016, TC0017, TC0018
      test_github_adapter.py    # TC0021, TC0022, TC0024, TC0027, TC0028, TC0029, TC0030
      test_rss_adapter.py       # TC0031, TC0032, TC0033, TC0035
    test_fetch_all.py           # TC0045, TC0046, TC0047, TC0048, TC0051, TC0055
  cassettes/
    arxiv/recent_cs_ai_cs_cl.yaml
    github/trending_weekly_en.yaml
    rss/three_feeds.yaml
  fixtures/
    items/valid_item.yaml
    sources/{arxiv_keyword_fixture,github_maturity_table,rss_three_feeds}.yaml
```

Per-module coverage gate (TSD): every `tests/unit/test_*.py` listed above must reach **≥95% line + branch** for its target module, enforced by `coverage report --fail-under-by-file`. The integration suite contributes to the **≥85% overall** target but is not held to the per-module floor.

---

## Traceability

| Artefact | Reference |
|----------|-----------|
| PRD | [sdlc-studio/prd.md](../prd.md) |
| Epic | [EP0001](../epics/EP0001-content-ingestion.md) |
| TSD | [sdlc-studio/tsd.md](../tsd.md) |
| Stories | [US0001](../stories/US0001-item-model-and-source-adapter-protocol.md), [US0002](../stories/US0002-arxiv-source-adapter.md), [US0003](../stories/US0003-github-trending-source-adapter.md), [US0004](../stories/US0004-rss-source-adapter.md), [US0005](../stories/US0005-source-registry-and-config-loader.md) |

---

## Open Questions

_None._ Inherits all decisions from the TSD (VCR + stubbed LLM, tiered coverage, no live HTTP in CI).

---

## Revision History

| Date | Author | Change |
|------|--------|--------|
| 2026-05-19 | HYL | Initial spec authored from EP0001 stories US0001–US0005. 55 test cases across 31 ACs (full coverage). |
| 2026-05-19 | HYL | Reviewed and promoted Draft → Ready: 31/31 ACs covered, 55 TCs with explicit assertions, fixtures defined, no placeholder assertions. Note for automation step: expand the inline arXiv keyword fixture sketch from 3 entries to the full 10-entry version (7 within window + 3 outside) per TC0014 AC2 wording. |
