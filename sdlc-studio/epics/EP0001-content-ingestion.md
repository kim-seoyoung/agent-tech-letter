# EP0001: Content Ingestion

> **Status:** Draft
> **Owner:** HYL
> **Reviewer:** HYL
> **Created:** 2026-05-19
> **Target Release:** v1.0 (first issue shipped)

## Summary

Build the source-side of the pipeline: a `SourceAdapter` protocol plus three concrete adapters (arXiv, GitHub Trending, RSS) that normalise upstream items into the `Item` model defined in the TRD. Items carry `item_kind`, `maturity`, and `raw` shipping-signal metadata so downstream ranking and composition can differentiate paper / blog / repo intelligently. Source list is config-driven; adding a feed requires zero code changes.

## Inherited Constraints

| Source | Type | Constraint | Impact |
|--------|------|------------|--------|
| PRD | Source set | arXiv (cs.AI, cs.CL), GitHub trending, 4 RSS feeds (TNS AI, Import AI, Latent Space, Simon Willison) | Defines initial adapter set |
| PRD | Performance | Fetch + downstream draft completes in <5 min | Adapters must run in parallel-safe manner with bounded latency |
| PRD | Model | `Item` includes `item_kind`, `maturity`, `raw` shipping signals | Adapters must populate these, not just the base fields |
| TRD | Architecture | Adapter pattern (ADR-002); SourceAdapter protocol | All sources implement the same protocol; pipeline iterates a registry |
| TRD | Reliability | Per-source isolation (ADR-004); tenacity retries with exp backoff | One source failing must not abort the run |
| TRD | Tech stack | Python 3.11+; `feedparser`, `arxiv`, `httpx` | No alternative libraries unless added as ADR |

---

## Business Context

### Problem Statement
The LLM-agent space moves fast across disconnected venues — arXiv, GitHub, vendor and independent blogs. Tech-Letter for HYL is built around the insight that signal emerges when the same topic shows up across multiple sources, or when something is novel enough to stand on its own. To detect either, the system needs reliable, normalised ingestion from several sources every week.

**PRD Reference:** [§3 Feature Inventory — F-01](../prd.md#3-feature-inventory)

### Value Proposition
Without this epic, there is no newsletter. Every other epic depends on a stream of normalised `Item`s. This epic is the load-bearing input layer.

### Success Metrics

| Metric | Current | Target | Measurement |
|--------|---------|--------|-------------|
| Sources reachable per scheduled run | 0 (no code) | ≥ 3 of 3 (arXiv + GitHub + RSS) | Adapter logs at end of fetch stage |
| Items normalised per run | 0 | 50–500 (window-dependent) | Length of normalised item list |
| Per-source failures aborting the run | n/a | 0 (failure is isolated, not fatal) | Workflow-level audit |

---

## Scope

### In Scope
- `Item` pydantic model with all fields per TRD §6.
- `SourceAdapter` protocol (`name`, `fetch(window_days) -> list[Item]`).
- Adapter for arXiv (`cs.AI`, `cs.CL`, LLM-agent keyword filter).
- Adapter for GitHub Trending (last 7 days), with `raw` containing stars / last-commit / recent-release / hosted-demo URL.
- Adapter for RSS feeds, working off the 4 initial feeds plus arbitrary additions via config.
- Config-driven source registry: `config/sources.yaml`.
- tenacity-wrapped HTTP/SDK calls.
- Adapter-level dry-run cache hook (the cache itself lives in EP0003; this epic just exposes the seam).

### Out of Scope
- Clustering, ranking, composition — EP0002.
- Reddit ingestion — explicitly dropped in PRD v0.2.0.
- Consumer-product source — explicitly dropped in PRD v0.4.0.
- Persistent state across runs (no "prior week" memory) — future CR.

### Affected Personas
- **HYL (Author/Editor):** indirect — needs adapters to be reliable enough that drafts arrive on schedule.
- **Researcher Subscriber:** indirect — relies on this epic to deliver papers from arXiv with correct `item_kind = paper`, and repos from GitHub with shipping signals attached.

---

## Acceptance Criteria (Epic Level)

- [ ] `Item` model is defined and importable; instances round-trip through pydantic validation.
- [ ] `SourceAdapter` protocol is defined; all three adapters implement it.
- [ ] arXiv adapter returns recent submissions from `cs.AI` and `cs.CL`, filtered by an LLM-agent keyword list (configurable), with `item_kind = paper`.
- [ ] GitHub Trending adapter returns trending repos in the past week, with `item_kind = repo` and `raw` populated with stars / last_commit_at / has_recent_release / hosted_demo_url (when discoverable).
- [ ] RSS adapter pulls items from each feed in `config/sources.yaml`, with `item_kind = blog_post`.
- [ ] Source list lives in `config/sources.yaml`; adding a feed requires only a config edit.
- [ ] tenacity decorators applied to each network call; per-source failure isolates (failure of one does not abort the run); per-source success/failure is logged.
- [ ] All adapters can be exercised against fixture data without making network calls (testability requirement).

---

## Dependencies

### Blocked By

| Dependency | Type | Status | Owner |
|------------|------|--------|-------|
| Repo scaffolding (uv project, ruff, pyright config) | Engineering | Not started | HYL |

### Blocking

| Item | Type | Impact |
|------|------|--------|
| EP0002 Composition Pipeline | Epic | Cannot cluster/rank/compose without normalised items |
| EP0003 Orchestration | Epic | Draft workflow needs fetch step to produce input |

---

## Risks & Assumptions

### Assumptions
- GitHub Trending remains accessible via its current HTML or unofficial JSON path. If it becomes captcha-gated, an alternative repo-trending signal (e.g., star delta from the GitHub REST API) is the fallback.
- arXiv API rate limits are non-binding at our query volume (one query per category per run).
- The 4 RSS feeds remain valid feed URLs; if a feed migrates, it's a config edit.

### Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| GitHub Trending scrape breaks | M | M | Wrap in tenacity; treat scrape failure as a skipped source, not a fatal error. Document an alternative-source fallback path in EP0001 retrospective if it happens. |
| RSS feed returns malformed XML | L | L | `feedparser` is tolerant; log and skip individual malformed items, don't abort the feed. |
| arXiv returns no items (empty week in cs.AI/CL) | L | L | Empty result is valid; downstream handles "few items" gracefully. |
| `maturity` inference for repos is too generous / too strict | M | L | Tune inference rules in PR review; keep them in one function for easy iteration. |

---

## Technical Considerations

### Architecture Impact
This epic establishes the **source-side adapter pattern** (ADR-002 in TRD). Each adapter is a separate module under `techletter/sources/` implementing `SourceAdapter`. Adding a future source (e.g., a new RSS feed, ProductHunt, etc.) follows the same recipe: drop a new module in, register it, add a config entry.

### Integration Points
- **arXiv API** via `arxiv` library (no auth, public).
- **GitHub Trending** via HTTPS scrape or unofficial JSON endpoint (no auth required for read; `GITHUB_TOKEN` optional for higher rate limits).
- **RSS feeds** via `feedparser` over HTTPS (no auth).
- **Config layer** via `pyyaml` + `pydantic` (validation at load time).

---

## Sizing

**Story Points:** ~13
**Estimated Story Count:** 5

**Complexity Factors:**
- Three adapters, each with its own quirks (arXiv query syntax, GitHub Trending HTML structure, RSS variability).
- `maturity` inference is fuzzy work — needs explicit rules and a test harness with fixture HTML/XML.
- The "GitHub Trending may break" risk implies investment in fixture-based tests so changes to upstream don't silently break the adapter.

---

## Story Breakdown

Stories generated 2026-05-19. See [Story Index](../stories/_index.md) for full details.

- [x] [US0001](../stories/US0001-item-model-and-source-adapter-protocol.md) — `Item` model + `SourceAdapter` protocol (3 pts) **Done**
- [x] [US0002](../stories/US0002-arxiv-source-adapter.md) — arXiv source adapter (3 pts) **Done**
- [ ] [US0003](../stories/US0003-github-trending-source-adapter.md) — GitHub Trending source adapter (5 pts)
- [x] [US0004](../stories/US0004-rss-source-adapter.md) — RSS source adapter (2 pts) **Done**
- [ ] [US0005](../stories/US0005-source-registry-and-config-loader.md) — Source registry + `config/sources.yaml` loader (3 pts)

**Total:** 16 story points across 5 stories.

---

## Test Plan

**Test Spec:** [TS0001](../test-specs/TS0001-content-ingestion.md) — 55 test cases (TC0001–TC0055), 31/31 ACs covered.

- Unit: each adapter parses fixture upstream data into expected `Item`s; `infer_maturity` is parametric (TC0026); `Item` validation is property-tested via hypothesis (TC0011).
- Integration: source registry loads `config/sources.yaml` and dispatches each adapter end-to-end with VCR cassettes (arXiv/GitHub/RSS) and pytest-httpx for failure-mode control.
- Failure mode: each adapter's tenacity-wrapped call is exercised with simulated 5xx / connection-reset to confirm retry + isolation behaviour; registry's `fetch_all` is tested with one and all adapters raising.

---

## Open Questions

_None._ All decisions inherited from PRD v0.4.0 and TRD v0.3.0.

---

## Revision History

| Date | Author | Change |
|------|--------|--------|
| 2026-05-19 | HYL | Initial epic created from PRD v0.4.0 F-01. |
| 2026-05-19 | HYL | Story breakdown linked: 5 stories (US0001–US0005, 16 pts total). |
| 2026-05-19 | HYL | Test plan linked to [TS0001](../test-specs/TS0001-content-ingestion.md) — 55 TCs, 31/31 ACs covered. |
