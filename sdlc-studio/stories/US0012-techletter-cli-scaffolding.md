# US0012: `techletter` CLI scaffolding with `draft` / `send` / `dry-run`

> **Status:** Done
> **Epic:** [EP0003: Orchestration & Developer Experience](../epics/EP0003-orchestration-and-dx.md)
> **Owner:** HYL
> **Reviewer:** HYL
> **Created:** 2026-05-19

## User Story

**As** HYL (Author/Editor)
**I want** a `techletter` CLI with three sub-commands — `draft`, `send`, `dry-run` — that orchestrates the source/compose/delivery pieces
**So that** the GitHub Actions workflows have a single, documented entry point and I can run the same commands locally for development.

## Context

### Persona Reference
**HYL (Author/Editor)** — uses the CLI both from CI (via Actions) and locally (via `uv run`). Will judge by whether `techletter dry-run` becomes the natural Sunday-morning iteration loop.
[Persona details](../personas/stakeholders/users/hyl-author.md)

### Background
Without a CLI, every workflow becomes ad-hoc `python -m techletter.x.y` invocations sprinkled across YAML. The CLI is the single seam between Actions and the pipeline. Click is the chosen framework (TRD).

---

## Inherited Constraints

| Source | Type | Constraint | AC Implication |
|--------|------|------------|----------------|
| Epic | Architecture | CLI on `click`; sub-commands `draft`, `send`, `dry-run` | Three commands; one entry point |
| Epic | Cache | `--dry-run` uses `.cache/`; CI does not | Cache is enabled only by the `dry-run` sub-command or an explicit flag |
| TRD | Tooling | `uv` for env / deps | CLI must run cleanly under `uv run techletter ...` |
| TRD | Budget | Compose aborts must surface as workflow failures | CLI returns non-zero exit on `BudgetExceededError` / `LlmUnavailableError` / `ConfigLoadError` |

---

## Acceptance Criteria

### AC1: Entry point and package wiring
- **Given** the package `techletter` is installed (via `uv sync`)
- **When** the user runs `uv run techletter --help`
- **Then** the help text lists exactly three sub-commands: `draft`, `send`, `dry-run`
- **And** the entry point is declared in `pyproject.toml` under `[project.scripts]` as `techletter = "techletter.cli:cli"`

### AC2: `techletter draft` orchestrates ingest → compose → write
- **Given** EP0001 and EP0002 modules are importable
- **When** `techletter draft` is invoked
- **Then** the command:
  1. Loads `config/sources.yaml` via US0005's loader.
  2. Calls `registry.fetch_all(window_days=7)` to get items.
  3. Runs cluster → rank → compose → assemble to produce a `RenderedIssue`.
  4. Writes `drafts/issue-{issue_id}.md` (markdown + front matter).
  5. Prints the path to stdout and exits 0.
- **And** any of these failures: missing config, `BudgetExceededError`, `LlmUnavailableError`, `SourceRegistryError` (only when all sources fail), or `ComposeParseError` exits with non-zero status and a clear error message.

### AC3: `techletter send --issue <issue_id>` dispatches to channels
- **Given** a draft file exists at `drafts/issue-{issue_id}.md` (or, in CI, on the merged commit)
- **When** `techletter send --issue 2026-05-19` is invoked
- **Then** the command:
  1. Reads the draft markdown + front matter.
  2. Loads the channel registry (EP0004).
  3. For each enabled channel: checks idempotency (US0013); if not already sent, calls `channel.send(issue, recipients)`; appends `SendRecord` to `logs/sends.jsonl`.
  4. Exits 0 if all configured sends succeed-or-already-sent.
- **And** if at least one channel returns `failed` (not `partial`), exits non-zero.
- **And** `partial` results do not fail the command — they're recorded and the command exits 0.

### AC4: `techletter dry-run` runs full pipeline without side effects
- **Given** the user is iterating locally
- **When** `techletter dry-run` is invoked
- **Then** the command:
  1. Enables the `.cache/` for fetch + LLM responses (US0014).
  2. Runs the full draft pipeline.
  3. Writes the result to `drafts/.local/issue-{issue_id}.md` (separate path from real drafts; gitignored).
  4. Does NOT commit, open a PR, or send to any channel.
  5. Prints token usage summary and timing.
- **And** an explicit flag `--no-cache` disables the cache for that run.

### AC5: Common options surface
- **Given** all three commands
- **When** the user runs `--help` for any sub-command
- **Then** the following common options are documented:
  - `--config <path>` — override default `config/sources.yaml` location.
  - `--log-level <level>` — set log level (default INFO).
- **And** `send` specifically supports `--issue <issue_id>` (required) and `--channel <name>` (optional; defaults to all enabled).

### AC6: Exit codes are documented
- **Given** a single source of truth for exit codes
- **When** the CLI exits
- **Then** the codes are:
  - `0` — success or "nothing to do" (idempotency hit, dry-run completed)
  - `1` — generic error
  - `2` — config error (e.g., missing file, validation failure)
  - `3` — budget exceeded
  - `4` — LLM unavailable
  - `5` — partial/failed send (only `send` returns this; `partial` is exit 0)
- **And** these codes are referenced in the `--help` output and used consistently by the workflows in US0015/US0016.

### AC7: Logging is structured
- **Given** all commands
- **When** events occur
- **Then** logs go to stderr in a stable format (`{level} {logger.name} {message}`)
- **And** the workflow yamls (US0015/US0016) can grep for `BUDGET_EXCEEDED` and similar markers.

---

## Scope

### In Scope
- `techletter/cli.py` defining the `cli` group with three sub-commands.
- `pyproject.toml` entry point declaration.
- Common options + exit codes.
- Wiring to EP0001 (sources registry), EP0002 (compose pipeline), EP0004 (delivery registry) — calling existing functions, not reimplementing them.
- Help text and option documentation.
- Unit tests using `click.testing.CliRunner`.

### Out of Scope
- The actual implementations of cache, sends.jsonl, workflow YAMLs — those are separate stories.
- Pretty terminal output / progress bars — minimal CLI ergonomics; logs are good enough.
- Configuration via env-var overrides beyond what individual modules already accept.
- Multi-issue batch operations (e.g., "send all unsent issues") — not in v1.

---

## Technical Notes

- Click sub-commands are simple. The hard part is keeping `cli.py` thin — it should orchestrate, not implement. Each sub-command is ~20–40 lines.
- Exit codes are mapped via a tiny `_handle_exception` helper that catches the named exceptions from upstream modules and exits with the appropriate code.
- The `--issue` argument to `send` is a date string (`YYYY-MM-DD`); validated against `datetime.date.fromisoformat`.
- For test isolation, each sub-command takes the registry / LLM client as injectable parameters (default to module-level construction); tests inject fakes.

### API Contracts
- `techletter draft [--config <path>] [--log-level <level>]`
- `techletter send --issue <YYYY-MM-DD> [--channel <name>] [--config <path>]`
- `techletter dry-run [--no-cache] [--config <path>]`

### Data Requirements
Reads `config/sources.yaml`, `config/subscribers.yaml`, `config/channels.yaml`. Writes `drafts/issue-*.md`, `drafts/.local/issue-*.md`, `logs/sends.jsonl`.

---

## Edge Cases & Error Handling

| Scenario | Expected Behaviour |
|----------|-------------------|
| `techletter draft` invoked when no config files exist | Exit 2 with "config/sources.yaml not found at <path>" |
| `techletter draft` invoked when LLM API key missing | Exit 4 with "ANTHROPIC_API_KEY not set" |
| `techletter draft` produces an issue that exceeds the token budget | Exit 3 with "BUDGET_EXCEEDED: projected X > budget Y"; no draft file written |
| `techletter draft` when all sources fail | Exit 1; no draft file; log lists per-source failures |
| `techletter draft` when at least one source succeeds | Exits 0; draft contains items from successful sources |
| `techletter send --issue 2099-01-01` (no such draft) | Exit 2 "draft for issue 2099-01-01 not found" |
| `techletter send` with all (issue, channel) pairs already in `logs/sends.jsonl` | Exit 0 with "all channels already sent; nothing to do" |
| `techletter send` with one channel returning `failed` | Exit 5 with summary; other channels still attempted |
| `techletter send --channel slack` | Only Slack adapter called; email + telegram skipped |
| `techletter dry-run` writes to `drafts/.local/` even if that directory doesn't exist | Directory auto-created |
| User passes `--log-level=DEBUG` | All loggers respect it |
| User runs CLI without any args | Prints `--help` and exits 0 |
| `KeyboardInterrupt` (Ctrl-C) during run | Clean exit with code 130; partial state may remain (drafts, cache) |
| `--config` points to a directory instead of a file | Exit 2 with clear error |
| `--issue` with malformed date (e.g., "today") | Exit 2 with "invalid date format" |

---

## Test Scenarios

- [ ] `techletter --help` lists three sub-commands.
- [ ] `techletter draft --help` shows common + draft-specific options.
- [ ] Mock pipeline: `techletter draft` writes a markdown file and exits 0.
- [ ] Mock pipeline raising `BudgetExceededError`: exit code 3, no draft file.
- [ ] Mock pipeline raising `LlmUnavailableError`: exit code 4.
- [ ] Mock pipeline raising `ConfigLoadError`: exit code 2.
- [ ] Mock send: success on all channels → exit 0; one `SendReport.status="failed"` → exit 5.
- [ ] `techletter send` with idempotency hits → exit 0, no channel calls made.
- [ ] `techletter dry-run` writes to `drafts/.local/`, not `drafts/`.
- [ ] `techletter dry-run --no-cache` runs without reading or writing the cache.
- [ ] `--issue 2099-13-45` (invalid) → exit 2.
- [ ] Type check: `cli.py` passes pyright.

---

## Dependencies

### Story Dependencies

| Story | Type | What's Needed | Status |
|-------|------|---------------|--------|
| [US0005](US0005-source-registry-and-config-loader.md) | Service | Sources registry + config loader | Draft |
| [US0011](US0011-compose-blog-quick-mentions-and-issue-assembly.md) | Service | `RenderedIssue` model + `assemble_issue` | Draft |
| [US0013](US0013-sends-jsonl-and-idempotency.md) | Schema | `SendRecord`, append helper, idempotency check (`send` sub-command depends on it; `draft` and `dry-run` do not) | Draft |
| [US0014](US0014-cache-helpers.md) | Service | Cache helpers (`dry-run` depends on it) | Draft |

(For practical sequencing: scaffold the CLI early with stubs; fill in real wiring as the dependent stories merge.)

### External Dependencies

| Dependency | Type | Status |
|------------|------|--------|
| `click` library | Library | Added in this story |

---

## Estimation

**Story Points:** 3
**Complexity:** Low. Mostly wiring. Quality lever: clean exit-code semantics and clear error messages.

---

## Open Questions

_None._

---

## Revision History

| Date | Author | Change |
|------|--------|--------|
| 2026-05-19 | HYL | Initial story created from EP0003. |
