# US0014: `.cache/` helpers — fetch cache + LLM response cache, CI-disabled

> **Status:** Draft
> **Epic:** [EP0003: Orchestration & Developer Experience](../epics/EP0003-orchestration-and-dx.md)
> **Owner:** HYL
> **Reviewer:** HYL
> **Created:** 2026-05-19

## User Story

**As** HYL (Author/Editor)
**I want** a local `.cache/` for fetch results and LLM responses that's enabled only under `--dry-run` and provably disabled in CI
**So that** I can iterate on prompts and templates for a Sunday afternoon without burning LLM tokens or hammering source APIs, and there is no risk of CI accidentally serving stale cached items.

## Context

### Persona Reference
**HYL (Author/Editor)** — explicit frustration: "Prompt iteration loops that burn tokens because there's no cache." This story is the direct response.
[Persona details](../personas/stakeholders/users/hyl-author.md)

### Background
Without a cache, each `dry-run` invocation re-fetches arXiv / GitHub / RSS feeds and re-calls the LLM for the cluster/rank/compose steps. Each iteration is 5+ minutes and a few hundred tokens. With a cache, iteration drops to seconds and zero LLM cost — but only if we're absolutely certain the cache is invisible in CI (a stale cached issue going out as the real Monday newsletter would be a serious bug).

---

## Inherited Constraints

| Source | Type | Constraint | AC Implication |
|--------|------|------------|----------------|
| Epic | Cache | `.cache/` git-ignored; only used under `--dry-run`; never read in CI (ADR-005) | Two-layer guard: `dry-run` flag and `CI`-env-var detection |
| TRD | Cache keys | Fetch: `{source}-{window_days}-{date}`; LLM: SHA-256 of `prompt + model + temperature` | Prompt changes invalidate cache automatically |
| TRD | Dev-only | Cache hard-fails open (returns None) in CI | `CI=true` env var, or `GITHUB_ACTIONS=true`, disables reads |

---

## Acceptance Criteria

### AC1: Cache module is defined
- **Given** the module `techletter.cache` exists
- **When** an engineer imports `from techletter.cache import FetchCache, LlmCache`
- **Then** both classes have:
  - `get(key) -> bytes | None` — returns cached value or `None`
  - `set(key, value: bytes) -> None` — writes to disk
  - `clear() -> None` — wipes the cache namespace

### AC2: Fetch cache uses source + window + date key
- **Given** a `FetchCache` instance
- **When** the same `(source="arxiv", window_days=7, date="2026-05-19")` is set and then retrieved
- **Then** the bytes round-trip correctly
- **And** a different `date` returns `None` (cache miss)
- **And** the key is hashed (SHA-256) to produce a filename like `.cache/fetch/<hash>.bin`

### AC3: LLM cache keys on prompt content
- **Given** an `LlmCache` instance
- **When** `get(prompt="...", model="claude-sonnet-4-6", temperature=0.0)` is called for a prompt that was previously cached with `set(...)`
- **Then** the cached value is returned
- **And** when the prompt text differs by even one character, returns `None` (different SHA-256)
- **And** when only the model id differs, returns `None`
- **And** the cache file name is `.cache/llm/<hash>.bin`

### AC4: CI guard disables reads
- **Given** the environment variable `CI=true` (or `GITHUB_ACTIONS=true`) is set
- **When** `FetchCache.get(...)` or `LlmCache.get(...)` is called
- **Then** the method returns `None` regardless of whether the file exists
- **And** the method logs an INFO line "cache disabled in CI; bypassing"
- **And** `set()` in CI is also a no-op (writes nothing) — defensive: even if a future code path tries to write, CI never produces a cache for someone to read later

### AC5: `.cache/` is git-ignored
- **Given** the repo's `.gitignore`
- **When** the cache writes files under `.cache/`
- **Then** git does not track them (verified by `git status` showing nothing)
- **And** `.gitignore` contains a line `.cache/` at repo root.

### AC6: `dry-run` flag toggles cache on
- **Given** `techletter dry-run` is invoked
- **When** the CLI constructs the source registry and LLM client
- **Then** both are passed cache instances
- **And** when `techletter draft` or `send` are invoked (the production sub-commands), they are passed `None` for the caches (no-op cache, equivalent to disabled)

### AC7: Cache is invalidated when prompts change
- **Given** an LLM response was cached for prompt P1
- **When** the prompt file is edited to produce P2 and the next dry-run runs
- **Then** the cache key changes (different SHA-256) and the LLM is called again
- **And** the old cached value remains on disk (no auto-cleanup; takes minimal space; manual `clear()` is available)

### AC8: Manual cache clear
- **Given** the user wants a clean slate
- **When** they run `techletter dry-run --no-cache`
- **Then** the cache is neither read nor written for that run
- **And** when they run `techletter dry-run --clear-cache`, the cache directory is wiped first, then a fresh dry-run executes

---

## Scope

### In Scope
- `techletter/cache.py` defining `FetchCache`, `LlmCache`, helper `_is_ci_environment()` function.
- Disk layout: `.cache/fetch/` and `.cache/llm/`.
- Integration hook: source adapters and LLM client accept an optional cache parameter (default `None`).
- `.gitignore` entry.
- Unit tests covering key collisions, CI guard, set/get round-trip, clear behaviour.

### Out of Scope
- Distributed cache (e.g., Redis) — local disk only, dev-only.
- Cache TTLs — prompt change invalidates LLM cache; date in key handles fetch cache; explicit TTLs are unnecessary.
- A null cache object pattern in production code paths — passing `None` is fine; adapters check `if cache is not None`.

---

## Technical Notes

- Cache values are stored as raw bytes; callers (source adapters / LLM client) decide encoding. Most callers will use `json.dumps(...).encode()` for structured data, or the raw response bytes for LLM responses.
- The CI guard's env-var detection: `CI` is the GitHub Actions–set variable; `GITHUB_ACTIONS` is the more specific one; either positive triggers the bypass. Document this clearly in the module docstring.
- A SHA-256 key over the full prompt text means a 200K-token prompt is hashed in microseconds — negligible.
- The cache writes use `tempfile.NamedTemporaryFile` + atomic `os.replace` so a crashed write doesn't leave a corrupt file.

### API Contracts
- `FetchCache(base_path: Path = Path(".cache/fetch"))` — constructor.
- `FetchCache.get(source: str, window_days: int, date: str) -> bytes | None`
- `FetchCache.set(source, window_days, date, value: bytes) -> None`
- `LlmCache(base_path: Path = Path(".cache/llm"))` — constructor.
- `LlmCache.get(prompt: str, model: str, temperature: float) -> bytes | None`
- `LlmCache.set(prompt, model, temperature, value: bytes) -> None`
- Both: `clear() -> None`.

### Data Requirements
`.cache/` directory at repo root; git-ignored.

---

## Edge Cases & Error Handling

| Scenario | Expected Behaviour |
|----------|-------------------|
| Cache directory doesn't exist | Created on first `set()` |
| Cache file is corrupt / partial (crash mid-write) | `get()` returns `None`, logs WARN, leaves the file (next set replaces it via atomic rename) |
| Disk full during `set()` | `OSError` propagates; caller's choice (the LLM client treats cache failures as best-effort) |
| Same key with different value (race) | Atomic rename ensures last writer wins; no torn reads |
| `CI=true` but user explicitly wants cache (e.g., for local Docker test) | Cache stays disabled — the env-var bypass takes precedence over `--dry-run`. Document this clearly. |
| `--clear-cache` invoked when `.cache/` doesn't exist | No-op; not an error |
| Cache key contains characters unfit for filename (none possible — keys are SHA-256 hex) | Not applicable; hash output is hex chars |
| Hash collision | Negligible for SHA-256; not handled |
| Cache directory path is somehow outside repo (user passes `--cache-dir /tmp/...`) | Supported but not the default; CI guard still applies |
| Cache file written but never read (one-shot dry-run) | Acceptable; cache costs are tiny |
| Cache `set()` called with empty bytes | Stored; `get()` returns empty bytes (truthy distinction: caller treats `None` as miss, `b""` as hit-with-empty) |
| Reading cache file > 100 MB (large LLM response) | Acceptable; no limit imposed |
| Concurrency: two CLI processes writing to same key | Atomic rename ensures consistency; race winner is unspecified |

---

## Test Scenarios

- [ ] `FetchCache.set` + `get` round-trip → same bytes.
- [ ] `FetchCache.get` for never-set key → `None`.
- [ ] Different `date` → cache miss.
- [ ] `LlmCache.get` after `set` with same args → cache hit.
- [ ] One-character prompt change → cache miss (different hash).
- [ ] Model id change → cache miss.
- [ ] Temperature change (0.0 → 0.1) → cache miss.
- [ ] With `CI=true` set in env: `get()` returns `None` even for keys present on disk.
- [ ] With `CI=true`: `set()` writes nothing.
- [ ] `clear()` removes all cache files.
- [ ] Corrupt cache file → `get()` returns None, WARN logged.
- [ ] `.gitignore` includes `.cache/`.
- [ ] Type check: `cache.py` passes pyright.
- [ ] Concurrent `set()` calls with same key → last writer wins; no torn file.

---

## Dependencies

### Story Dependencies

| Story | Type | What's Needed | Status |
|-------|------|---------------|--------|
| [US0012](US0012-techletter-cli-scaffolding.md) | Service | CLI passes cache to adapters / LLM client | Draft |

### External Dependencies
None new. Uses stdlib only (`hashlib`, `pathlib`, `os`, `tempfile`).

---

## Estimation

**Story Points:** 5
**Complexity:** Medium. Simple per-method logic but the CI guard's correctness is critical and worth multiple tests. The `--clear-cache` UX and the atomic write are small details that add up.

---

## Open Questions

_None._

---

## Revision History

| Date | Author | Change |
|------|--------|--------|
| 2026-05-19 | HYL | Initial story created from EP0003. |
