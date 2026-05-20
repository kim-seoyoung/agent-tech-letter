# US0005: Source registry + `config/sources.yaml` loader

> **Status:** Draft
> **Epic:** [EP0001: Content Ingestion](../epics/EP0001-content-ingestion.md)
> **Owner:** HYL
> **Reviewer:** HYL
> **Created:** 2026-05-19

## User Story

**As** HYL (Author/Editor)
**I want** a typed config file `config/sources.yaml` that lists which sources are enabled and what arguments they take, plus a registry that constructs the right adapter instances from it
**So that** turning sources on/off, adjusting keyword filters, and adding new RSS feeds requires only a config edit — no code changes.

## Context

### Persona Reference
**HYL (Author/Editor)** — values that "adding a feed is one config edit." This story is the user-facing surface of the adapter pattern. If this is ugly, the adapter pattern's promise is broken.
[Full persona details](../personas/stakeholders/users/hyl-author.md)

### Background
The three adapters (arXiv, GitHub, RSS) live behind a uniform `SourceAdapter` protocol per US0001. The registry/loader is the glue that:
1. Reads `config/sources.yaml`.
2. Validates the config (pydantic).
3. Constructs one adapter instance per enabled source.
4. Exposes a `fetch_all(window_days) -> list[Item]` that calls each adapter, isolates per-source failures, and returns the aggregated item list.

This story closes the loop: with it merged, the pipeline can call `fetch_all` and get items.

---

## Inherited Constraints

| Source | Type | Constraint | AC Implication |
|--------|------|------------|----------------|
| Epic | Reliability | Per-source isolation (ADR-004) | Registry catches per-adapter exceptions; one failure doesn't stop the others |
| PRD | Config-first | Adding a feed requires zero code changes | YAML schema supports parameterised adapter construction |
| PRD | Feed list (initial) | TNS AI, Import AI, Latent Space, Simon Willison | These four feeds are the default `config/sources.yaml` shipped with the project |
| TRD | Tech Stack | `pydantic` for validation, `pyyaml` for parsing | Both used here |
| TRD | Architecture | Adapter pattern (ADR-002) — adapters registered, not hardcoded | Registry uses a mapping `name → adapter class` |

---

## Acceptance Criteria

### AC1: Config file schema is defined and validated
- **Given** a `config/sources.yaml` file
- **When** the loader (`techletter.config.load_sources(path)`) reads it
- **Then** the file conforms to this pydantic schema:
  ```yaml
  arxiv:
    enabled: true
    categories: ["cs.AI", "cs.CL"]
    keywords: ["agent", "tool-use", "LLM", ...]
  github:
    enabled: true
    spoken_language: "en"
    period: "weekly"
  rss:
    enabled: true
    feeds:
      - "https://thenewstack.io/ai/feed/"
      - "https://importai.substack.com/feed"
      - "https://www.latent.space/feed"
      - "https://simonwillison.net/atom/everything/"
  ```
- **And** missing top-level keys default to `enabled: false` for that source
- **And** invalid keys (e.g., a typo'd source name) cause `ValidationError` at load time, not silent ignore

### AC2: Registry constructs adapters from config
- **Given** a valid loaded config
- **When** `build_registry(config) -> dict[str, SourceAdapter]` is called
- **Then** the result is a dict keyed by source name (`"arxiv"`, `"github"`, `"rss"`) containing only the enabled sources
- **And** each adapter instance is constructed with the parameters from its config block

### AC3: `fetch_all` aggregates from all enabled sources
- **Given** a registry with all three sources enabled
- **When** `registry.fetch_all(window_days=7)` is called
- **Then** the returned list contains items from all three adapters, deduplicated by `url` (first occurrence wins)
- **And** the order is stable across calls given the same inputs (for reproducibility)

### AC4: Per-source failure does not abort the run
- **Given** the GitHub adapter raises `SourceFetchError` during `fetch_all`
- **When** `fetch_all(window_days=7)` is called
- **Then** items from arXiv and RSS adapters are still returned
- **And** the failure is logged as `"source 'github' failed: <message>"`
- **And** no exception propagates out of `fetch_all`

### AC5: All sources fail → empty list + warning
- **Given** all three adapters fail
- **When** `fetch_all(window_days=7)` is called
- **Then** the returned list is `[]`
- **And** a warning is logged: `"all sources failed; no items fetched"`
- **And** no exception propagates (the orchestration layer in EP0003 decides whether this aborts the run)

### AC6: Config-file errors are loud
- **Given** a `config/sources.yaml` file with malformed YAML (e.g., bad indentation)
- **When** `load_sources(path)` is called
- **Then** `ConfigLoadError` is raised with a message pointing to the file and the YAML parser error
- **And** the same applies for files that parse but fail pydantic validation (clear field-level error path)

### AC7: Adding an RSS feed is a one-line config edit
- **Given** an existing valid `config/sources.yaml`
- **When** a new URL is appended to `rss.feeds` and the system is re-run
- **Then** the new feed is included in `fetch_all` results without any code changes
- **And** no restart of any service is required (each run reads config fresh)

---

## Scope

### In Scope
- `techletter/config/sources.py` defining the pydantic config schema (`SourcesConfig`, `ArxivConfig`, `GithubConfig`, `RssConfig`).
- `techletter/config/__init__.py` exposing `load_sources(path) -> SourcesConfig` and `ConfigLoadError`.
- `techletter/sources/registry.py` defining `build_registry(config) -> SourceRegistry` and the `SourceRegistry` class with `fetch_all`.
- Default `config/sources.yaml` shipped at repo root.
- Unit tests for config validation, registry construction, and `fetch_all` with mocked adapters.

### Out of Scope
- Hot-reload of config — re-running the CLI loads fresh; no daemon to reload.
- Config schema versioning / migration — greenfield; revisit if schema evolves later.
- Per-adapter override mechanism beyond what's in YAML (e.g., env-var overrides) — `GITHUB_TOKEN` is already an env var read by the adapter itself; no need to pass through config.
- Multi-environment configs (dev/prod variants) — same config for all environments in v1.

---

## Technical Notes

- `SourcesConfig` extends `pydantic.BaseModel` with `extra="forbid"` so typos in keys raise rather than silently no-op.
- The adapter-name → adapter-class mapping in `registry.py` is an explicit dict (not auto-discovery). This is intentional: explicit imports make it grep-able and pyright-checkable.
- Deduplication in `fetch_all` uses `dict.fromkeys(items_by_url)` semantics — preserves order, keeps first occurrence.
- Logging uses the stdlib `logging` module with a `techletter.sources.registry` logger.

### API Contracts
- `load_sources(path: Path) -> SourcesConfig`
- `build_registry(config: SourcesConfig) -> SourceRegistry`
- `SourceRegistry.fetch_all(window_days: int) -> list[Item]`
- `ConfigLoadError(Exception)` — raised on YAML parse failure, file not found, or pydantic validation failure (chained as `__cause__`).

### Data Requirements
`config/sources.yaml` at repo root — committed to git, read at runtime.

---

## Edge Cases & Error Handling

| Scenario | Expected Behaviour |
|----------|-------------------|
| `config/sources.yaml` missing | `ConfigLoadError` ("file not found at <path>") |
| All sources `enabled: false` | `build_registry` returns empty registry; `fetch_all` returns `[]` with info-level log |
| Unknown top-level source key (e.g., `reddit:`) | `ValidationError` from pydantic (`extra="forbid"`); surfaces as `ConfigLoadError` |
| RSS feeds list is empty (`rss.feeds: []`) | RSS adapter constructed but returns `[]` on fetch; not an error |
| Single feed URL is malformed | `ValidationError` (HttpUrl validation); reports the offending URL |
| Multiple sources fail concurrently | All failures logged independently; aggregated items from successful sources still returned |
| Same item URL surfaces from two sources (e.g., arXiv abstract URL appears in an RSS feed citing it) | First occurrence wins; second is silently deduplicated |
| `window_days = 0` | Each adapter gets `window_days=0`; aggregated result reflects whatever they return (could be empty) |
| Adapter constructor itself raises (config-valid but adapter rejects it) | Caught at `build_registry`; logged; that source is omitted from the registry; other sources proceed |
| Two enabled sources but only one defined in `adapter-name → class` map | Unknown adapter name → `ValidationError` from pydantic schema (the `Literal` enum forbids unknowns) |
| Network is entirely unreachable | Each adapter fails per its own retry policy; `fetch_all` returns `[]` with logs |
| Concurrent invocations of `fetch_all` on the same registry instance | Stateless; safe (not used concurrently in v1) |

---

## Test Scenarios

- [ ] Load valid `sources.yaml` → `SourcesConfig` matches expected structure.
- [ ] Load `sources.yaml` with unknown top-level key → `ValidationError`.
- [ ] Load malformed YAML → `ConfigLoadError`.
- [ ] Load with `arxiv: enabled: false` → registry omits arxiv adapter.
- [ ] `build_registry` constructs each adapter with its config-derived kwargs (verified by mocking adapter `__init__`).
- [ ] `fetch_all` with all three adapters mocked returning fixed items → aggregated, deduplicated, stable-ordered.
- [ ] `fetch_all` with one adapter raising → returns items from the other two; log mentions the failed source.
- [ ] `fetch_all` with all three raising → returns `[]`, warning logged.
- [ ] Deduplication: two adapters return items with identical `url` → only one in result.
- [ ] Adding a feed URL to `config/sources.yaml` and re-running `fetch_all` includes the new feed's items without code changes (manual / integration test).

---

## Dependencies

### Story Dependencies

| Story | Type | What's Needed | Status |
|-------|------|---------------|--------|
| [US0001](US0001-item-model-and-source-adapter-protocol.md) | Schema | `Item` model + `SourceAdapter` protocol | Draft |
| [US0002](US0002-arxiv-source-adapter.md) | Service | `ArxivAdapter` to register | Draft |
| [US0003](US0003-github-trending-source-adapter.md) | Service | `GitHubTrendingAdapter` to register | Draft |
| [US0004](US0004-rss-source-adapter.md) | Service | `RssAdapter` to register | Draft |

(Strictly the registry only needs US0001 to exist for type checking. US0002–US0004 only need to be merged before the registry can be exercised end-to-end, but the registry itself can be written against a fake adapter for unit tests.)

### External Dependencies

| Dependency | Type | Status |
|------------|------|--------|
| `pyyaml` library | Python package | Added in this story |
| `pydantic` v2 | Python package | Already added (US0001) |

---

## Estimation

**Story Points:** 3
**Complexity:** Low-Medium. The config schema is simple. The interesting work is `fetch_all` error isolation and dedupe — both of which have unit-test scaffolding from US0001's protocol.

---

## Open Questions

_None._

---

## Revision History

| Date | Author | Change |
|------|--------|--------|
| 2026-05-19 | HYL | Initial story created from EP0001. |
