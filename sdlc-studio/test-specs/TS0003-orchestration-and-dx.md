# TS0003: Orchestration & Developer Experience

> **Status:** Ready
> **Epic:** [EP0003: Orchestration & Developer Experience](../epics/EP0003-orchestration-and-dx.md)
> **Created:** 2026-05-19
> **Last Updated:** 2026-05-19
> **TC Range:** TC0126–TC0197

## Overview

Test specification for the wiring epic — the CLI, the audit log, the dev-only cache, and the two GitHub Actions workflows. This is where the project stops being a pile of modules and becomes a runnable system, and it's the test spec with the most heterogeneous surface: Python code, YAML files, prompt files referenced from secrets, on-disk state (`.cache/`, `drafts/`, `logs/`).

Three test surfaces are required and they don't overlap cleanly:

1. **Python unit / integration** for `techletter.cli`, `techletter.audit`, `techletter.cache` — driven by `pytest` + `click.testing.CliRunner` + the `FakeLLMClient` from TS0002 + stubbed channel adapters.
2. **Workflow YAML static checks** — `actionlint` (lints the YAMLs themselves), plus pytest-driven YAML-parse assertions that read the workflow files and assert specific structural properties (cron expression, `if:` predicate, concurrency block, env-var passthrough, step order).
3. **Workflow behavioural checks** — `act`-style local runs that simulate `pull_request.closed` events with the `merged: true|false` predicate to confirm the `send.yml` job is skipped in the non-merge case.

What's **out of scope for this spec**:

- The actual scheduled cron firing on the real repo — that's a manual smoke during release week, not a PR test.
- The author-only smoke send (TSD-mandated, runs at the end of `draft.yml` before the PR opens) — that's a *behavioural* test driven by the real workflow + HYL's own channels, not an automated unit. The smoke-send's *correctness* is what unblocks the production PR, not what gates this spec.
- The first end-to-end real send — covered by the project-level release checklist, not test code.

Per the TSD, the pure-helper tier (≥95% line + branch) applies to:

- **`techletter.audit`** — `SendRecord`, `append_send_record`, `already_sent`, `load_records` are all pure-ish (file I/O at the seam, no LLM, no network) and the failed-vs-partial-vs-ok semantics is exactly the kind of branch density that needs full coverage.
- **`techletter.cache`** — the CI guard is critical correctness; partial coverage would be malpractice.

CLI shell code (`techletter.cli`) is held to the overall ≥85% line floor. YAML files are *not* covered by `coverage` at all; their tests are structural assertions instead.

## Scope

### Stories Covered

| Story | Title | Priority |
|-------|-------|----------|
| [US0012](../stories/US0012-techletter-cli-scaffolding.md) | `techletter` CLI scaffolding | P0 |
| [US0013](../stories/US0013-sends-jsonl-and-idempotency.md) | `logs/sends.jsonl` + idempotency | P0 |
| [US0014](../stories/US0014-cache-helpers.md) | `.cache/` helpers, CI-disabled | P0 |
| [US0015](../stories/US0015-draft-workflow-yaml.md) | `.github/workflows/draft.yml` | P0 |
| [US0016](../stories/US0016-send-workflow-yaml.md) | `.github/workflows/send.yml` | P0 (safety-critical) |
| [US0017](../stories/US0017-readme-quickstart-and-dev-loop.md) | README + dev loop docs | P1 |

### AC Coverage Matrix

| Story | AC | Description | Test Cases | Status |
|-------|-----|-------------|------------|--------|
| US0012 | AC1 | Entry point + 3 sub-commands | TC0126 | Covered |
| US0012 | AC2 | `draft` orchestrates ingest → compose → write | TC0127, TC0128 | Covered |
| US0012 | AC3 | `send` dispatches + idempotency-aware | TC0129, TC0130, TC0131 | Covered |
| US0012 | AC4 | `dry-run` no side effects + `--no-cache` | TC0132, TC0133 | Covered |
| US0012 | AC5 | Common options (`--config`, `--log-level`, `--channel`) | TC0134, TC0135 | Covered |
| US0012 | AC6 | Exit-code mapping | TC0136 | Covered |
| US0012 | AC7 | Structured logging + grep-able markers | TC0137 | Covered |
| US0013 | AC1 | `SendRecord` model definition | TC0141 | Covered |
| US0013 | AC2 | `append_send_record` writes one line, `O_APPEND` | TC0142 | Covered |
| US0013 | AC3 | `already_sent` returns True on ok/partial | TC0143, TC0144 | Covered |
| US0013 | AC4 | `load_records` tolerates corrupt lines | TC0147, TC0148, TC0149 | Covered |
| US0013 | AC5 | Failed sends do NOT block retry | TC0145, TC0150 | Covered |
| US0013 | AC6 | Partial sends are treated as completed | TC0144 | Covered |
| US0013 | AC7 | Schema validation on construct (no half-write) | TC0151, TC0152 | Covered |
| US0014 | AC1 | Cache module surface (`FetchCache`, `LlmCache`) | TC0154 | Covered |
| US0014 | AC2 | Fetch cache key (source, window, date) | TC0155, TC0156 | Covered |
| US0014 | AC3 | LLM cache key (prompt + model + temp) | TC0157, TC0158 | Covered |
| US0014 | AC4 | CI guard disables reads + writes | TC0159, TC0160 | Covered |
| US0014 | AC5 | `.cache/` git-ignored | TC0161 | Covered |
| US0014 | AC6 | `dry-run` toggles cache; `draft`/`send` pass None | TC0162 | Covered |
| US0014 | AC7 | Prompt change invalidates LLM cache | TC0158 | Covered |
| US0014 | AC8 | `--clear-cache` wipes; `--no-cache` skips | TC0163, TC0164 | Covered |
| US0015 | AC1 | `draft.yml` has both triggers + permissions | TC0167 | Covered |
| US0015 | AC2 | Step order: checkout → uv → draft → branch → PR | TC0168 | Covered |
| US0015 | AC3 | Secrets passed via env | TC0169 | Covered |
| US0015 | AC4 | Budget breach fails the workflow visibly | TC0170 | Covered |
| US0015 | AC5 | Source-only-failure still produces PR | TC0171 | Covered |
| US0015 | AC6 | Queue semantics: no `cancel-in-progress` | TC0172 | Covered |
| US0015 | AC7 | Branch name includes run id | TC0173 | Covered |
| US0016 | AC1 | `send.yml` trigger + permissions | TC0178 | Covered |
| US0016 | AC2 | Closed-without-merge is a no-op (`if:` predicate) | TC0179 | Covered |
| US0016 | AC3 | Issue id parsed from branch name | TC0180 | Covered |
| US0016 | AC4 | Step order: send → log commit + push | TC0181 | Covered |
| US0016 | AC5 | Concurrency group serialises sends | TC0182 | Covered |
| US0016 | AC6 | Channel secrets documented in env | TC0183 | Covered |
| US0016 | AC7 | Upstream idempotency respected (no double-send) | TC0184 | Covered |
| US0016 | AC8 | CLI failure → workflow failure | TC0185 | Covered |
| US0017 | AC1 | README has the 9 required sections | TC0190 | Covered |
| US0017 | AC2 | Quickstart sequence ordered correctly | TC0191 | Covered |
| US0017 | AC3 | Secrets table lists all required + optional | TC0192 | Covered |
| US0017 | AC4 | Dev section covers prompt iteration loop | TC0193 | Covered |
| US0017 | AC5 | Project Structure matches actual disk layout | TC0194 | Covered |
| US0017 | AC6 | Cross-links to SDLC artefacts resolve | TC0195 | Covered |
| US0017 | AC7 | `.env.example` exists + `.env` in `.gitignore` | TC0196 | Covered |

**Coverage:** 44 / 44 ACs covered. **Uncovered: 0.** Spec eligible to move Draft → Ready.

### Test Types Required

| Type | Required | Rationale |
|------|----------|-----------|
| Unit | Yes | Audit log semantics (US0013), cache key derivation + CI guard (US0014), CLI command wiring (US0012) — all pure/deterministic |
| Integration | Yes | CLI invoked end-to-end with `CliRunner` against fake pipeline; cache `set` + `get` round-trip with real filesystem under `tmp_path` |
| Workflow YAML static checks | Yes | `actionlint` + pyyaml-parse assertions on both workflow files — the only way to catch a regressed cron / predicate / permissions block before it ships |
| Workflow behavioural simulation | Yes (light) | `act` (or equivalent) simulates `pull_request.closed` events to confirm `if: merged == true` predicate; not a deep test, but the only way to catch a YAML-level bypass |
| E2E (real cron, real send) | **No** | Owned by the manual release checklist; the smoke send (TSD) is the production E2E, not in this spec |

---

## Environment

| Requirement | Details |
|-------------|---------|
| Prerequisites | Python 3.11+, pytest ≥ 8.0, pytest-cov, freezegun, click ≥ 8.1, pyyaml; `actionlint` binary on `PATH` for YAML lint tests |
| External Services | **None.** All channel adapters stubbed; FakeLLMClient stubbed; cassettes from TS0001/TS0002 reused where applicable |
| Test Data | Fixture `logs/sends.jsonl` files under `tests/fixtures/audit/` with curated combinations of ok/partial/failed records |
| Clock | Default frozen at `2026-05-19T00:00:00Z` so `issue_id` extraction, draft branch naming, and audit timestamps are deterministic |
| Filesystem | All on-disk tests scoped to `tmp_path` — no test touches the real `logs/`, `drafts/`, or `.cache/` directories |
| Env vars | `CI` and `GITHUB_ACTIONS` are scrubbed at the start of every cache test, then monkey-patched in/out per case. `ANTHROPIC_API_KEY` never set in CI — TC0136 verifies the CLI surfaces this cleanly |

---

## Test Cases

### TC0126: `techletter --help` lists exactly the three sub-commands

**Type:** Unit (CliRunner) | **Priority:** P0 | **Story:** US0012 (AC1)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | `from click.testing import CliRunner`; `from techletter.cli import cli` | Import succeeds |
| When | `runner.invoke(cli, ["--help"])` | Exit 0; help text returned |
| Then | Help text contains `draft`, `send`, `dry-run` as listed sub-commands; `pyproject.toml`'s `[project.scripts]` declares `techletter = "techletter.cli:cli"` | n/a |

**Assertions:**
- [ ] Help output mentions all three sub-command names
- [ ] No fourth sub-command surfaces
- [ ] `pyproject.toml` static check confirms the entry point declaration

---

### TC0127: `techletter draft` happy path writes `drafts/issue-{date}.md` and exits 0

**Type:** Integration (CliRunner + fake pipeline) | **Priority:** P0 | **Story:** US0012 (AC2)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | Stubbed sources registry + FakeLLMClient + stubbed assembler returning a fixture RenderedIssue; clock frozen at `2026-05-19T00:00:00Z` | n/a |
| When | `runner.invoke(cli, ["draft"], catch_exceptions=False)` | Exit code 0 |
| Then | A file `tmp_path/drafts/issue-2026-05-19.md` exists; first line is YAML front-matter open `---` | stdout contains the written file path |

**Assertions:**
- [ ] Exit code 0
- [ ] File `drafts/issue-2026-05-19.md` exists in `tmp_path`
- [ ] File starts with `---\n`

---

### TC0128: `techletter draft` propagates `BudgetExceededError` → exit 3, no file written

**Type:** Integration (CliRunner) | **Priority:** P0 | **Story:** US0012 (AC2, AC6)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | Fake compose raises `BudgetExceededError("projected 215000 > budget 200000")` | n/a |
| When | `runner.invoke(cli, ["draft"])` | Exit code **3** |
| Then | No file written under `drafts/`; stderr contains `"BUDGET_EXCEEDED"` marker (grep-able by `draft.yml`) | n/a |

**Assertions:**
- [ ] Exit code 3
- [ ] `drafts/` empty
- [ ] `"BUDGET_EXCEEDED"` substring in stderr

---

### TC0129: `techletter send` — all channels return `ok` → exit 0, records appended

**Type:** Integration (CliRunner + stubbed channels) | **Priority:** P0 | **Story:** US0012 (AC3)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | Draft file exists at `drafts/issue-2026-05-19.md`; channel registry stubbed with 3 adapters all returning `SendReport(status="ok")` | n/a |
| When | `runner.invoke(cli, ["send", "--issue", "2026-05-19"])` | Exit code 0 |
| Then | 3 `SendRecord`s appended to `logs/sends.jsonl`, all with `status="ok"` | Channels were called once each |

**Assertions:**
- [ ] Exit code 0
- [ ] `logs/sends.jsonl` has exactly 3 lines, all with `status="ok"`
- [ ] Each stub channel recorded exactly one `send()` call

---

### TC0130: `techletter send` — one channel `failed` → exit 5, others still attempted

**Type:** Integration (CliRunner + stubbed channels) | **Priority:** P0 | **Story:** US0012 (AC3, AC6)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | 3 channels: email returns `ok`, slack returns `failed`, telegram returns `ok` | n/a |
| When | `runner.invoke(cli, ["send", "--issue", "2026-05-19"])` | Exit code **5** |
| Then | All 3 channels were attempted (failure doesn't short-circuit) | 3 records in `logs/sends.jsonl` |

**Assertions:**
- [ ] Exit code 5
- [ ] All 3 channels' `send()` was called
- [ ] `logs/sends.jsonl` has one record per channel; slack's has `status="failed"`

---

### TC0131: `techletter send` — all pairs already in log → exit 0, channels NOT called

**Type:** Integration (CliRunner + stubbed channels) | **Priority:** P0 | **Story:** US0012 (AC3, idempotency)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | `logs/sends.jsonl` pre-seeded with `ok` records for all (`2026-05-19`, every channel) pairs | n/a |
| When | `runner.invoke(cli, ["send", "--issue", "2026-05-19"])` | Exit code 0 |
| Then | **No channel `send()` was invoked**; stdout/stderr contains "all channels already sent" | No new records appended |

**Assertions:**
- [ ] Exit code 0
- [ ] No stub channel's `send()` was called
- [ ] `logs/sends.jsonl` line count unchanged
- [ ] Log output mentions "already sent"

---

### TC0132: `techletter dry-run` writes to `drafts/.local/`, never to `drafts/`, opens no PR

**Type:** Integration (CliRunner + fake pipeline + spied channels) | **Priority:** P0 | **Story:** US0012 (AC4)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | Fake pipeline; channel adapters that record any call; PR-creator stub | n/a |
| When | `runner.invoke(cli, ["dry-run"])` | Exit code 0 |
| Then | File at `drafts/.local/issue-2026-05-19.md`; **nothing under `drafts/`** (canonical); no channel `send()` called; no PR opener called | Token usage summary printed |

**Assertions:**
- [ ] File at `drafts/.local/issue-2026-05-19.md` exists
- [ ] No file directly under `drafts/` (excluding `.local/` subdir)
- [ ] Zero channel sends
- [ ] Zero PR-opener invocations

---

### TC0133: `techletter dry-run --no-cache` runs without reading or writing the cache

**Type:** Integration (CliRunner + cache spy) | **Priority:** P1 | **Story:** US0012 (AC4)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | Cache directory exists with previously-stored entries; cache instances are spied | n/a |
| When | `runner.invoke(cli, ["dry-run", "--no-cache"])` | Exit code 0 |
| Then | Cache `get()` and `set()` were not called for this run | Cache directory contents unchanged |

**Assertions:**
- [ ] Zero `get()` or `set()` invocations on either cache instance
- [ ] `.cache/` directory unchanged before/after

---

### TC0134: Common options `--config` and `--log-level` route correctly

**Type:** Unit (CliRunner) | **Priority:** P2 | **Story:** US0012 (AC5)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | A non-default config path and a captured logger | n/a |
| When | `runner.invoke(cli, ["draft", "--config", "alt/sources.yaml", "--log-level", "DEBUG"])` | Exit 0 |
| Then | The loader is called with `alt/sources.yaml`; the root logger's level is `DEBUG`; at least one DEBUG log line is emitted | n/a |

**Assertions:**
- [ ] Loader invoked with the override path
- [ ] Root logger level is `DEBUG`
- [ ] At least one DEBUG record captured

---

### TC0135: `techletter send --channel slack` only invokes slack adapter

**Type:** Integration (CliRunner) | **Priority:** P2 | **Story:** US0012 (AC5)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | 3 channels stubbed; all return `ok` | n/a |
| When | `runner.invoke(cli, ["send", "--issue", "2026-05-19", "--channel", "slack"])` | Exit 0 |
| Then | Only slack's `send()` was called; email and telegram were not | 1 record in log |

**Assertions:**
- [ ] Only slack stub called once
- [ ] Email and telegram stubs not called
- [ ] `logs/sends.jsonl` has exactly 1 new line

---

### TC0136: Exit codes match the documented mapping (parametric)

**Type:** Integration (CliRunner, parametric) | **Priority:** P0 | **Story:** US0012 (AC6)

**Parametrisation:**

| Pipeline raises | Expected exit |
|---|---:|
| `ConfigLoadError` | 2 |
| `BudgetExceededError` | 3 |
| `LlmUnavailableError` | 4 |
| Send: one channel `failed` (others ok) | 5 |
| Generic `RuntimeError` | 1 |

**Assertions:**
- [ ] Each parametrised case produces the documented exit code

---

### TC0137: Logs go to stderr in stable format; `BUDGET_EXCEEDED` marker is grep-able

**Type:** Unit (CliRunner + capsys) | **Priority:** P1 | **Story:** US0012 (AC7)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | Fake pipeline raises `BudgetExceededError` | n/a |
| When | `runner.invoke(cli, ["draft"])` with `capfd`-captured streams | Exit 3 |
| Then | The `"BUDGET_EXCEEDED"` substring appears on stderr (NOT stdout) — workflow's `grep` from US0015 depends on this exact stream | Log line format matches `{LEVEL} {logger.name} {message}` |

**Assertions:**
- [ ] `"BUDGET_EXCEEDED"` substring in stderr (case-sensitive)
- [ ] `"BUDGET_EXCEEDED"` NOT in stdout
- [ ] Log line matches the documented pattern (regex)

---

### TC0138: `--issue 2099-13-45` (invalid date) → exit 2 before any work

**Type:** Unit (CliRunner) | **Priority:** P2 | **Story:** US0012 (edge)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | n/a | n/a |
| When | `runner.invoke(cli, ["send", "--issue", "2099-13-45"])` | Exit code 2 |
| Then | No draft file read; no channel send | Error message mentions "invalid date" |

**Assertions:**
- [ ] Exit code 2
- [ ] Error message contains `"invalid"` (case-insensitive)
- [ ] No filesystem reads beyond the validation step

---

### TC0139: `--issue 2099-01-01` (valid date but no draft file) → exit 2

**Type:** Unit (CliRunner) | **Priority:** P2 | **Story:** US0012 (edge)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | `drafts/` directory does not contain `issue-2099-01-01.md` | n/a |
| When | `runner.invoke(cli, ["send", "--issue", "2099-01-01"])` | Exit code 2 |
| Then | Error message names the expected file path | No channel send |

**Assertions:**
- [ ] Exit code 2
- [ ] Message contains `"issue-2099-01-01.md"` (or close paraphrase)

---

### TC0140: `techletter` with no args prints `--help` and exits 0

**Type:** Unit (CliRunner) | **Priority:** P2 | **Story:** US0012 (edge)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | n/a | n/a |
| When | `runner.invoke(cli, [])` | Exit code 0 |
| Then | Help text printed | Three sub-commands listed |

**Assertions:**
- [ ] Exit code 0
- [ ] Output equals `runner.invoke(cli, ["--help"]).output`

---

### TC0141: `SendRecord` model matches the documented schema

**Type:** Unit | **Priority:** P0 | **Story:** US0013 (AC1)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | `from techletter.audit import SendRecord` | Import succeeds |
| When | A valid `SendRecord` constructed via `model_validate` | Validates |
| Then | All documented fields present; `model_config.frozen is True`; default `timestamp` is tz-aware UTC | n/a |

**Assertions:**
- [ ] Fields `issue_id`, `channel`, `recipients_count`, `success_count`, `failure_count`, `status`, `timestamp` all present
- [ ] `SendRecord.model_config["frozen"] is True`
- [ ] Default-constructed `timestamp.tzinfo == datetime.timezone.utc`

---

### TC0142: `append_send_record` writes one line; creates parent dir; mode is `O_APPEND`

**Type:** Unit | **Priority:** P0 | **Story:** US0013 (AC2)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | `log_path = tmp_path / "logs" / "sends.jsonl"`; parent `logs/` doesn't exist yet | n/a |
| When | `append_send_record(record, log_path)` is called twice with different records | Both succeed |
| Then | Parent dir was created; the file has exactly 2 lines; both parse as valid `SendRecord`s | Each line ends with `\n` |

**Assertions:**
- [ ] `log_path.parent.is_dir()` becomes True
- [ ] `log_path.read_text().count("\n") == 2`
- [ ] Both lines re-parse as `SendRecord` correctly

---

### TC0143: `already_sent` — `ok` record → True

**Type:** Unit | **Priority:** P0 | **Story:** US0013 (AC3)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | Log file with one `SendRecord(issue_id="2026-05-19", channel="email", status="ok", ...)` | n/a |
| When | `already_sent("2026-05-19", "email", log_path)` | Returns `True` |
| Then | Returns `True` for the matching pair, `False` for a mismatched channel | n/a |

**Assertions:**
- [ ] `already_sent("2026-05-19", "email", log_path) is True`
- [ ] `already_sent("2026-05-19", "slack", log_path) is False`

---

### TC0144: `already_sent` — `partial` record → True (do NOT retry partials)

**Type:** Unit | **Priority:** P0 | **Story:** US0013 (AC3, AC6)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | Log with one `partial` record for (2026-05-19, slack) | n/a |
| When | `already_sent("2026-05-19", "slack", log_path)` | Returns `True` |
| Then | This is the critical "partial = don't re-send" branch | n/a |

**Assertions:**
- [ ] `already_sent(...) is True` for the partial case

---

### TC0145: `already_sent` — only `failed` records → False (retry allowed)

**Type:** Unit | **Priority:** P0 | **Story:** US0013 (AC3, AC5)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | Log with two records for (2026-05-19, telegram), both `status="failed"` | n/a |
| When | `already_sent("2026-05-19", "telegram", log_path)` | Returns `False` |
| Then | Critical: failed sends do not block a retry | n/a |

**Assertions:**
- [ ] `already_sent(...) is False`

---

### TC0146: `already_sent` — empty / missing file → False

**Type:** Unit | **Priority:** P1 | **Story:** US0013 (AC3, edge)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | `log_path` does not exist | n/a |
| When | `already_sent("2026-05-19", "email", log_path)` | Returns `False` |
| Then | No exception; no file created | n/a |

**Assertions:**
- [ ] Returns `False`
- [ ] `log_path.exists() is False` afterwards

---

### TC0147: `load_records` full round-trip — append → load → compare

**Type:** Unit | **Priority:** P0 | **Story:** US0013 (AC4)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | 3 distinct `SendRecord`s | n/a |
| When | All appended via `append_send_record`, then `load_records(log_path)` | Returns 3 records |
| Then | Each loaded record `==` its original (timestamps preserved) | n/a |

**Assertions:**
- [ ] `len(loaded) == 3`
- [ ] `loaded[i] == originals[i]` for every i

---

### TC0148: `load_records` skips a corrupt line, returns the rest + WARN

**Type:** Unit | **Priority:** P1 | **Story:** US0013 (AC4)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | Log file with 3 lines: line 1 valid, line 2 truncated JSON, line 3 valid | n/a |
| When | `load_records(log_path)` | Returns 2 valid records |
| Then | A WARN log mentions line 2 was unparseable | No exception |

**Assertions:**
- [ ] `len(loaded) == 2`
- [ ] At least one WARN record mentions a parse failure on line 2

---

### TC0149: `load_records` — missing file returns `[]` (not an error)

**Type:** Unit | **Priority:** P1 | **Story:** US0013 (AC4, edge)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | `log_path` does not exist | n/a |
| When | `load_records(log_path)` | Returns `[]` |
| Then | No exception; no file created | n/a |

**Assertions:**
- [ ] `load_records(log_path) == []`

---

### TC0150: After a `failed` record, a successful retry appends without removing the prior

**Type:** Unit | **Priority:** P1 | **Story:** US0013 (AC5)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | Log file with one `failed` record for (2026-05-19, email) | n/a |
| When | A new `ok` record for the same pair is appended | Log now has 2 lines |
| Then | `already_sent(...)` is now True; first line (failed) is preserved as history | n/a |

**Assertions:**
- [ ] `log_path.read_text().count("\n") == 2`
- [ ] First line still has `"status":"failed"`
- [ ] Second line has `"status":"ok"`

---

### TC0151: Constructing `SendRecord` with `recipients_count=-1` → `ValidationError` and **no half-write**

**Type:** Unit | **Priority:** P1 | **Story:** US0013 (AC7)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | An attempted `SendRecord` with `recipients_count=-1` | n/a |
| When | `SendRecord(...)` is called | Raises `pydantic.ValidationError` |
| Then | If a caller wraps this in `append_send_record`, the file is never opened (because the model fails before the call) | n/a |

**Assertions:**
- [ ] `pytest.raises(pydantic.ValidationError)`
- [ ] `log_path` does not exist afterwards (the append was never reached)

---

### TC0152: Frozen mutation — `record.status = "ok"` → `ValidationError`

**Type:** Unit | **Priority:** P2 | **Story:** US0013 (AC1, frozen)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | A valid `SendRecord` with `status="failed"` | n/a |
| When | `record.status = "ok"` | Raises |
| Then | Original `record.status == "failed"` unchanged | n/a |

**Assertions:**
- [ ] Mutation raises
- [ ] `record.status == "failed"` still holds

---

### TC0153: Many records for same pair → `already_sent` finds the most-recent ok/partial

**Type:** Unit | **Priority:** P2 | **Story:** US0013 (edge — retry history)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | Log file with 5 records for (2026-05-19, slack): failed, failed, ok, failed, failed (in that chronological order) | n/a |
| When | `already_sent("2026-05-19", "slack", log_path)` | Returns `True` |
| Then | A single `ok` anywhere in the history is sufficient | n/a |

**Assertions:**
- [ ] `already_sent(...) is True`

---

### TC0154: Cache module surface — `FetchCache`, `LlmCache`, both expose `get`/`set`/`clear`

**Type:** Unit | **Priority:** P0 | **Story:** US0014 (AC1)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | `from techletter.cache import FetchCache, LlmCache` | Import succeeds |
| When | Both classes instantiated with `tmp_path` subdirs | Constructors succeed |
| Then | Each instance has `get`, `set`, `clear` callable | n/a |

**Assertions:**
- [ ] Both classes have all three methods
- [ ] Pyright accepts the documented signatures

---

### TC0155: FetchCache — same key → round-trip identical bytes

**Type:** Unit | **Priority:** P0 | **Story:** US0014 (AC2)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | `cache = FetchCache(tmp_path / "fetch")`; key = `("arxiv", 7, "2026-05-19")` | n/a |
| When | `cache.set(*key, value=b"payload"); cache.get(*key)` | Returns `b"payload"` |
| Then | Cache file lands at `tmp_path / "fetch" / "<sha256>.bin"` | n/a |

**Assertions:**
- [ ] `cache.get(*key) == b"payload"`
- [ ] A file matching `<sha256>.bin` exists in the cache dir

---

### TC0156: FetchCache — different `date` → cache miss

**Type:** Unit | **Priority:** P1 | **Story:** US0014 (AC2)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | Cached value for `("arxiv", 7, "2026-05-19")` | n/a |
| When | `cache.get("arxiv", 7, "2026-05-26")` | Returns `None` |
| Then | Different date → different hash → miss | n/a |

**Assertions:**
- [ ] `cache.get("arxiv", 7, "2026-05-26") is None`

---

### TC0157: LlmCache — same prompt + model + temperature → round-trip

**Type:** Unit | **Priority:** P0 | **Story:** US0014 (AC3)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | `llm_cache.set("prompt text", "claude-sonnet-4-6", 0.0, b"response")` | n/a |
| When | `llm_cache.get("prompt text", "claude-sonnet-4-6", 0.0)` | Returns `b"response"` |
| Then | n/a | n/a |

**Assertions:**
- [ ] Round-trip equality

---

### TC0158: LlmCache misses on any single change — parametric (prompt / model / temperature)

**Type:** Unit (parametric) | **Priority:** P0 | **Story:** US0014 (AC3, AC7)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | Base entry cached for `("base prompt", "claude-sonnet-4-6", 0.0)` | n/a |
| When | `get` called with each of: prompt with one extra char; different model id; temperature 0.1 | Returns `None` for each |
| Then | Critical AC7 invariant: prompt-text change invalidates cache automatically | n/a |

**Parametrisation:**

| Variant | Expected |
|---------|----------|
| `"base prompts"` (extra char) | `None` |
| `"base prompt"` + model `"claude-opus-4-7"` | `None` |
| `"base prompt"` + temperature `0.1` | `None` |

**Assertions:**
- [ ] All 3 parametrised cases return `None`

---

### TC0159: CI guard — `CI=true` and `GITHUB_ACTIONS=true` both disable reads (parametric)

**Type:** Unit (parametric, monkeypatch) | **Priority:** P0 | **Story:** US0014 (AC4 — CRITICAL)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | Cache pre-populated; then env scrubbed and one of `{CI=true, GITHUB_ACTIONS=true, CI=true GITHUB_ACTIONS=true}` set | n/a |
| When | `cache.get(...)` for an existing key | Returns `None` regardless |
| Then | INFO log line says "cache disabled in CI; bypassing" | This is the load-bearing safety check for the whole project |

**Parametrisation:**

| Env | Expected `get()` |
|-----|------------------|
| `CI=true` only | `None` |
| `GITHUB_ACTIONS=true` only | `None` |
| Both set | `None` |
| Neither set | The cached value |

**Assertions:**
- [ ] All 3 CI-enabled cases return `None`
- [ ] The 4th (neither set) returns the cached value
- [ ] INFO log line present in each disabled case

---

### TC0160: CI guard — `set()` is a no-op in CI (defensive write-side)

**Type:** Unit (monkeypatch) | **Priority:** P0 | **Story:** US0014 (AC4)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | `CI=true` set; empty cache dir | n/a |
| When | `cache.set("k", b"v")` | No file created |
| Then | The cache dir remains empty; no exception | Defensive: nothing left behind for a later non-CI run to read |

**Assertions:**
- [ ] Cache dir empty before and after
- [ ] No exception

---

### TC0161: `.cache/` is in `.gitignore` at repo root

**Type:** Unit (static check) | **Priority:** P1 | **Story:** US0014 (AC5)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | The repo's `.gitignore` | File exists |
| When | The file's lines are read | n/a |
| Then | A line `^\.cache/\s*$` (or `^\.cache\s*$`) is present | n/a |

**Assertions:**
- [ ] `.gitignore` contains a line matching `.cache/`

---

### TC0162: CLI wiring — `dry-run` passes cache; `draft`/`send` pass `None`

**Type:** Integration (CliRunner with constructor spies) | **Priority:** P0 | **Story:** US0014 (AC6)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | Sources registry constructor spied to capture its `cache=` kwarg; LLM client similarly spied | n/a |
| When | `runner.invoke(cli, ["dry-run"])` then `runner.invoke(cli, ["draft"])` | Both exit 0 (with fake pipeline) |
| Then | `dry-run` invocation passed non-None cache instances; `draft` invocation passed `cache=None` | n/a |

**Assertions:**
- [ ] On dry-run: captured `cache=` arg is a `FetchCache` / `LlmCache` instance
- [ ] On draft: captured `cache=` arg is `None`

---

### TC0163: `clear()` wipes all cache files

**Type:** Unit | **Priority:** P2 | **Story:** US0014 (AC8)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | Cache with 5 set entries | Files present |
| When | `cache.clear()` | n/a |
| Then | Cache dir is empty (but exists); subsequent `get` returns `None` | n/a |

**Assertions:**
- [ ] Cache dir is empty after `clear()`
- [ ] Cache dir still exists (not deleted)
- [ ] `get(...)` for previously-set keys returns `None`

---

### TC0164: `techletter dry-run --no-cache` runs without reading or writing

**Type:** Integration (CliRunner) | **Priority:** P1 | **Story:** US0014 (AC8)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | Cache spy as in TC0162 | n/a |
| When | `runner.invoke(cli, ["dry-run", "--no-cache"])` | Exit 0 |
| Then | Cache `get` and `set` never invoked during this run | n/a |

**Assertions:**
- [ ] Zero `get()` and `set()` invocations

---

### TC0165: Concurrent `set()` calls with same key — atomic rename, no torn file

**Type:** Unit (threading) | **Priority:** P2 | **Story:** US0014 (edge — concurrency)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | 2 threads each calling `cache.set("k", b"v" * 1024)` with different payloads | n/a |
| When | Both finish | n/a |
| Then | The final file's content is one of the two payloads (last writer wins) — never a mix | No partial / torn write |

**Assertions:**
- [ ] File content is exactly one of `payload_a` or `payload_b`
- [ ] File size matches one of the two payloads

---

### TC0166: Corrupt cache file → `get()` returns `None` + WARN, file left alone

**Type:** Unit | **Priority:** P2 | **Story:** US0014 (edge)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | A cache file written with deliberately corrupt content (e.g., random bytes that aren't the expected payload format) | n/a |
| When | `cache.get(...)` for that key | Returns `None` |
| Then | WARN log mentions the file; the file is not deleted (next `set` replaces atomically) | n/a |

**Assertions:**
- [ ] `cache.get(...) is None`
- [ ] WARN log emitted
- [ ] File still exists after the failed `get`

---

### TC0167: `draft.yml` declares both triggers + correct permissions

**Type:** Unit (YAML parse) | **Priority:** P0 | **Story:** US0015 (AC1)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | `.github/workflows/draft.yml` parsed with `yaml.safe_load` | YAML valid |
| When | Inspected | n/a |
| Then | `on.schedule[0].cron == "0 0 * * 1"`; `on.workflow_dispatch` is present (may be `None` or `{}`); `permissions["contents"] == "write"` and `permissions["pull-requests"] == "write"` | n/a |

**Assertions:**
- [ ] `on.schedule[0].cron == "0 0 * * 1"`
- [ ] `"workflow_dispatch"` is a key under `on`
- [ ] Both `contents: write` and `pull-requests: write` set

---

### TC0168: `draft.yml` step order — checkout → setup-uv → uv sync → draft → branch/commit → push → gh pr create

**Type:** Unit (YAML parse) | **Priority:** P1 | **Story:** US0015 (AC2)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | The job's `steps` list | n/a |
| When | Steps inspected in order | n/a |
| Then | Step `uses:` or `name:` values match the documented order (substring match on each anchor) | `actions/checkout@v4` precedes `astral-sh/setup-uv`; `uv sync` precedes `techletter draft`; the `gh pr create` step is last |

**Assertions:**
- [ ] Steps in order: checkout, setup-uv, uv sync, draft CLI, branch+commit, push, PR open
- [ ] No step omitted

---

### TC0169: `draft.yml` env block exposes `ANTHROPIC_API_KEY` to the draft step

**Type:** Unit (YAML parse) | **Priority:** P0 | **Story:** US0015 (AC3)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | The draft step (the one invoking `techletter draft`) | n/a |
| When | Its `env:` block is inspected | n/a |
| Then | `ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}` is present | `GITHUB_TOKEN` flows automatically and need not be explicit |

**Assertions:**
- [ ] The draft step has `env.ANTHROPIC_API_KEY` referencing `secrets.ANTHROPIC_API_KEY`

---

### TC0170: Simulated `BudgetExceededError` → workflow `failure`

**Type:** Integration (act-style local run, optional) | **Priority:** P1 | **Story:** US0015 (AC4)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | `act` (or equivalent local runner) installed; CLI mocked to exit 3 | n/a |
| When | The workflow is simulated | Job ends with status `failure` |
| Then | The `BUDGET_EXCEEDED` substring is in the captured workflow log | No PR opened |

**Assertions:**
- [ ] Workflow exit/status is `failure`
- [ ] `BUDGET_EXCEEDED` substring in captured log
- [ ] `gh pr create` step did not execute (or executed but errored due to no draft file)

**Note:** If `act` is not available in CI, this TC is documented as "manual smoke", which is acceptable per AC4's "verify visibly" intent.

---

### TC0171: Source-only-failure (CLI exit 0 + partial sources) → PR is opened

**Type:** Integration (act-style or manual) | **Priority:** P2 | **Story:** US0015 (AC5)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | CLI exits 0 with a draft file produced from 2 of 3 sources (one source failed and was logged) | n/a |
| When | The workflow continues past the draft step | n/a |
| Then | `gh pr create` runs and PR-open is recorded; per-source failure preserved in workflow log | n/a |

**Assertions:**
- [ ] PR-open step ran
- [ ] Workflow exit status is `success`
- [ ] Per-source failure substring in workflow log

---

### TC0172: `draft.yml` does NOT use `concurrency.cancel-in-progress` (queue, not skip)

**Type:** Unit (YAML parse) | **Priority:** P1 | **Story:** US0015 (AC6)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | Parsed `draft.yml` | n/a |
| When | The top-level `concurrency:` block is inspected | n/a |
| Then | EITHER the block is absent entirely, OR `cancel-in-progress: false` is set explicitly | A new run must NOT cancel a prior one |

**Assertions:**
- [ ] Either `"concurrency"` key absent, or `concurrency.cancel-in-progress is False`

---

### TC0173: Branch name pattern includes the run id

**Type:** Unit (YAML parse) | **Priority:** P1 | **Story:** US0015 (AC7)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | The branch-creation step in `draft.yml` | n/a |
| When | The shell script that builds the branch name is inspected | n/a |
| Then | Pattern matches `draft/issue-{date}-${{ github.run_id }}` (or `${GITHUB_RUN_ID}`) | n/a |

**Assertions:**
- [ ] Branch-name expression contains `github.run_id` or `GITHUB_RUN_ID`
- [ ] Pattern contains the literal `draft/issue-` prefix

---

### TC0174: `actionlint` passes on both `draft.yml` and `send.yml`

**Type:** Unit (subprocess) | **Priority:** P0 | **Story:** US0015 + US0016 (combined lint)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | `actionlint` on `PATH` | n/a |
| When | `subprocess.run(["actionlint", ".github/workflows/draft.yml", ".github/workflows/send.yml"], check=False)` | Returncode 0 |
| Then | Zero lint findings | n/a |

**Assertions:**
- [ ] Returncode 0
- [ ] Empty stdout/stderr (or only informational lines)

---

### TC0175: Simulated missing `ANTHROPIC_API_KEY` → CLI exit 4 → workflow failure

**Type:** Integration (act-style) | **Priority:** P2 | **Story:** US0015 (edge)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | Secret intentionally not set in the simulated environment | n/a |
| When | Workflow runs | CLI exits 4 |
| Then | Workflow status `failure`; log mentions missing key | n/a |

**Assertions:**
- [ ] CLI exit code 4
- [ ] Workflow status `failure`

---

### TC0176: Cron expression parses to Monday UTC

**Type:** Unit | **Priority:** P2 | **Story:** US0015 (AC1 — semantic check)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | The cron string `"0 0 * * 1"` | n/a |
| When | Parsed with `croniter` (or equivalent), starting from 2026-05-18 (Sunday) | Next fire is `2026-05-18 00:00:00 UTC` (which is Monday in KST? Wait: 0 0 * * 1 is Monday 00:00 UTC; KST is UTC+9, so Mon 09:00 KST) |
| Then | The next fire is on a Monday in UTC | n/a |

**Assertions:**
- [ ] `croniter("0 0 * * 1", base=datetime(2026,5,18,tzinfo=UTC)).get_next(datetime).weekday() == 0`

---

### TC0177: `gh pr create` step uses the documented `--title` pattern

**Type:** Unit (YAML parse) | **Priority:** P2 | **Story:** US0015 (AC2)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | The PR-create step | n/a |
| When | Its `run:` script is inspected | n/a |
| Then | The `--title` argument matches `"Draft: Tech-Letter Issue {date}"` (or close) | n/a |

**Assertions:**
- [ ] PR-create step's run script contains `--title "Draft: Tech-Letter Issue`

---

### TC0178: `send.yml` trigger + permissions

**Type:** Unit (YAML parse) | **Priority:** P0 | **Story:** US0016 (AC1)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | `.github/workflows/send.yml` parsed | n/a |
| When | Inspected | n/a |
| Then | `on.pull_request.types == ["closed"]`; `on.pull_request.branches == ["main"]`; `permissions["contents"] == "write"`; `permissions` does NOT grant `pull-requests` | n/a |

**Assertions:**
- [ ] Trigger matches
- [ ] `contents: write` present
- [ ] `pull-requests` absent or `read` (NOT `write`)

---

### TC0179: `send.yml` job-level `if:` requires `merged == true`

**Type:** Unit (YAML parse) | **Priority:** P0 | **Story:** US0016 (AC2 — load-bearing safety)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | The job's `if:` expression | n/a |
| When | Inspected | n/a |
| Then | Expression contains `github.event.pull_request.merged == true` | This is the single most important assertion in this entire spec — getting this wrong sends an issue to subscribers on any PR close |

**Assertions:**
- [ ] `if:` contains `github.event.pull_request.merged == true`
- [ ] The `if:` is on the **job**, not on a step (so the whole job is skipped, saving runner minutes)

---

### TC0180: Issue-id extraction from branch name

**Type:** Unit (YAML parse + shell) | **Priority:** P1 | **Story:** US0016 (AC3)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | The shell expression in `send.yml` that derives `ISSUE_ID` from `github.event.pull_request.head.ref` | n/a |
| When | Tested with `head.ref = "draft/issue-2026-05-19-1234567890"` (e.g., by simulating the bash expression) | Result: `ISSUE_ID=2026-05-19` |
| Then | Round-trip a few representative branch names | n/a |

**Assertions:**
- [ ] `draft/issue-2026-05-19-{run-id}` → `2026-05-19` for various run-ids
- [ ] Non-matching pattern (e.g., `feature/x`) → empty or fails loudly (the workflow then fails at this step)

---

### TC0181: `send.yml` step order — checkout → uv → CLI send → git add/commit/push

**Type:** Unit (YAML parse) | **Priority:** P1 | **Story:** US0016 (AC4)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | The job's `steps` list | n/a |
| When | Inspected in order | n/a |
| Then | Checkout → setup-uv → uv sync → parse issue id → `techletter send` → git config user → git add logs/sends.jsonl → git commit → git push, all in order | n/a |

**Assertions:**
- [ ] All documented steps present in the documented order

---

### TC0182: `send.yml` concurrency group serialises

**Type:** Unit (YAML parse) | **Priority:** P0 | **Story:** US0016 (AC5 — load-bearing for log integrity)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | The top-level `concurrency:` block | n/a |
| When | Inspected | n/a |
| Then | `concurrency.group == "send-workflow"` (or close); `concurrency.cancel-in-progress is False` | A second send waits for the first, preventing `logs/sends.jsonl` write races |

**Assertions:**
- [ ] `concurrency.group` is a non-empty string
- [ ] `concurrency["cancel-in-progress"] is False`

---

### TC0183: All channel secrets are documented in `send.yml`'s env

**Type:** Unit (YAML parse) | **Priority:** P1 | **Story:** US0016 (AC6)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | The CLI step's `env:` block | n/a |
| When | Inspected | n/a |
| Then | All of: `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS`, `SMTP_FROM`, `SLACK_WEBHOOK_URLS`, `TELEGRAM_BOT_TOKEN` are present | Each references `secrets.<NAME>` |

**Assertions:**
- [ ] All 7 keys present in env
- [ ] Each value is a `${{ secrets.X }}` reference

---

### TC0184: Workflow respects upstream idempotency (no double-send on rerun)

**Type:** Integration (act-style or simulated) | **Priority:** P1 | **Story:** US0016 (AC7)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | `logs/sends.jsonl` pre-seeded with `ok` records for all channels; workflow runs against a merged PR for that issue | n/a |
| When | `techletter send` runs (no real channel calls happen because stubs are used) | Exit 0 |
| Then | No new records appended | No `git commit` of `logs/sends.jsonl` (no change to commit) |

**Assertions:**
- [ ] CLI exit 0
- [ ] `logs/sends.jsonl` line count unchanged
- [ ] The commit-step is skipped (or runs but is a no-op because the working tree is clean)

---

### TC0185: CLI exit 5 → workflow status `failure`

**Type:** Integration (act-style) | **Priority:** P1 | **Story:** US0016 (AC8)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | Stubbed channel that returns `failed` | n/a |
| When | Workflow runs the CLI | CLI exits 5 |
| Then | Workflow status `failure`; the failed-channel record was still committed to the log | n/a |

**Assertions:**
- [ ] Workflow status `failure`
- [ ] `logs/sends.jsonl` has a new line with `status="failed"`

---

### TC0186: Closed-without-merge skip — `act`-simulated event with `merged: false`

**Type:** Integration (act-style) | **Priority:** P0 | **Story:** US0016 (AC2 — behavioural)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | A simulated `pull_request.closed` event with `merged: false` | n/a |
| When | The workflow is invoked | Job is skipped at the `if:` predicate |
| Then | No steps run; no logs touched | This complements TC0179's static check with a behavioural confirmation |

**Assertions:**
- [ ] No steps executed
- [ ] No filesystem mutation

---

### TC0187: Commit message includes issue id

**Type:** Unit (YAML parse) | **Priority:** P2 | **Story:** US0016 (AC4)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | The git-commit step's `run:` script | n/a |
| When | Inspected | n/a |
| Then | The `git commit -m` argument contains `$ISSUE_ID` (or close) | n/a |

**Assertions:**
- [ ] Commit message contains the issue-id variable reference

---

### TC0188: Git author config is set explicitly (no global state dependency)

**Type:** Unit (YAML parse) | **Priority:** P2 | **Story:** US0016 (AC4)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | The git config step | n/a |
| When | Its run script inspected | n/a |
| Then | `user.email` and `user.name` are set explicitly (e.g., `actions@github.com` / `Tech-Letter Bot`) | n/a |

**Assertions:**
- [ ] Both `user.email` and `user.name` set in the step

---

### TC0189: Partial-result CLI exit 0 keeps workflow status `success`

**Type:** Integration (act-style) | **Priority:** P2 | **Story:** US0016 (AC8 reverse)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | Channel returns `partial` (some recipients ok, some failed) | n/a |
| When | CLI runs | Exits 0 |
| Then | Workflow status `success`; partial record committed | The partial details are visible in workflow log but don't fail the run |

**Assertions:**
- [ ] CLI exit 0
- [ ] Workflow status `success`
- [ ] Partial record present in `logs/sends.jsonl`

---

### TC0190: README contains all 9 sections in documented order

**Type:** Unit (markdown grep) | **Priority:** P1 | **Story:** US0017 (AC1)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | `README.md` at repo root | n/a |
| When | Its lines are scanned for the documented section headings | n/a |
| Then | Each of: `## What this is`, `## How it works`, `## Quickstart`, `## Configuration`, `## Secrets`, `## Running the workflows`, `## Development`, `## Project structure`, `## Links` is present, in that relative order | n/a |

**Assertions:**
- [ ] All 9 headings present
- [ ] Relative order matches the documented list

---

### TC0191: Quickstart section orders the commands correctly

**Type:** Unit (markdown text check) | **Priority:** P2 | **Story:** US0017 (AC2)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | The Quickstart section's body | n/a |
| When | Inspected | n/a |
| Then | `uv` install precedes `uv sync`; `uv sync` precedes the `.env.example` copy; `.env.example` copy precedes `uv run techletter dry-run` | n/a |

**Assertions:**
- [ ] Each command's first occurrence is in the documented order
- [ ] All 4 commands present

---

### TC0192: Secrets table lists all required + optional secrets

**Type:** Unit (markdown table parse) | **Priority:** P1 | **Story:** US0017 (AC3)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | The Secrets section's table | n/a |
| When | Its rows are extracted | n/a |
| Then | Rows reference at minimum: `ANTHROPIC_API_KEY`, `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS`, `SMTP_FROM`, `SLACK_WEBHOOK_URLS`, `TELEGRAM_BOT_TOKEN`, `GITHUB_TOKEN` | n/a |

**Assertions:**
- [ ] All 9 secret names present as table rows
- [ ] Each row has at least 4 columns (Name, Required/Optional, Used by, Where to set)

---

### TC0193: Development section covers the prompt-iteration loop

**Type:** Unit (markdown grep) | **Priority:** P2 | **Story:** US0017 (AC4)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | The Development section body | n/a |
| When | Inspected | n/a |
| Then | Contains `prompts/`, `.cache/`, `--clear-cache`, `uv run pytest`, `uv run ruff`, `uv run pyright` | n/a |

**Assertions:**
- [ ] All 6 phrase substrings present

---

### TC0194: Project Structure section lists directories that actually exist on disk

**Type:** Unit (markdown parse + filesystem check) | **Priority:** P1 | **Story:** US0017 (AC5)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | The Project Structure section's code-fenced tree | n/a |
| When | Each directory line is extracted and checked against disk | n/a |
| Then | Every directory listed (e.g., `techletter/sources/`, `prompts/`, `templates/`, `drafts/`, `logs/`, `sdlc-studio/`, `.github/workflows/`) exists | n/a |

**Assertions:**
- [ ] Every listed directory exists on disk (post-implementation)
- [ ] No listed file/dir is missing (false positive in the doc)

---

### TC0195: Cross-links to SDLC artefacts resolve

**Type:** Unit (markdown link check) | **Priority:** P1 | **Story:** US0017 (AC6)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | All markdown links in the Links section | n/a |
| When | Each `[text](path)` link is resolved against the repo | n/a |
| Then | Every linked file exists: `sdlc-studio/prd.md`, `sdlc-studio/trd.md`, `sdlc-studio/personas/index.md`, `sdlc-studio/epics/_index.md`, `sdlc-studio/stories/_index.md` | n/a |

**Assertions:**
- [ ] All 5 links resolve to existing files

---

### TC0196: `.env.example` exists and `.env` is in `.gitignore`

**Type:** Unit | **Priority:** P1 | **Story:** US0017 (AC7)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | The repo root | n/a |
| When | Inspected | n/a |
| Then | `.env.example` exists; lists all required secrets from TC0192 as `NAME=` placeholders; `.gitignore` contains a line `.env` (matching the file but not `.env.example`) | n/a |

**Assertions:**
- [ ] `.env.example` file exists
- [ ] All required secret names appear as keys in `.env.example`
- [ ] `.gitignore` contains `.env` (and does NOT exclude `.env.example`)

---

### TC0197: README markdown lints clean (no broken syntax)

**Type:** Unit (subprocess) | **Priority:** P2 | **Story:** US0017 (edge)

| Step | Action | Expected Result |
|------|--------|-----------------|
| Given | `markdownlint` (or `mdformat --check`) on PATH | n/a |
| When | `subprocess.run([...])` against `README.md` | Returncode 0 |
| Then | No structural lint findings (broken tables, malformed links, etc.) | n/a |

**Assertions:**
- [ ] Returncode 0

---

## Fixtures

```yaml
# tests/fixtures/audit/sends_ok_only.jsonl — drives TC0143, TC0146.
sends_ok_only:
  - {"issue_id":"2026-05-19","channel":"email","recipients_count":12,"success_count":12,"failure_count":0,"status":"ok","timestamp":"2026-05-19T00:05:00+00:00"}

# tests/fixtures/audit/sends_partial.jsonl — drives TC0144.
sends_partial:
  - {"issue_id":"2026-05-19","channel":"slack","recipients_count":3,"success_count":2,"failure_count":1,"status":"partial","timestamp":"2026-05-19T00:06:00+00:00"}

# tests/fixtures/audit/sends_failed_only.jsonl — drives TC0145.
sends_failed_only:
  - {"issue_id":"2026-05-19","channel":"telegram","recipients_count":2,"success_count":0,"failure_count":2,"status":"failed","timestamp":"2026-05-19T00:07:00+00:00"}
  - {"issue_id":"2026-05-19","channel":"telegram","recipients_count":2,"success_count":0,"failure_count":2,"status":"failed","timestamp":"2026-05-19T00:09:00+00:00"}

# tests/fixtures/audit/sends_mixed_history.jsonl — drives TC0153.
sends_mixed_history:
  - failed
  - failed
  - ok       # this single ok flips already_sent to True even though more failures follow
  - failed
  - failed

# tests/fixtures/audit/sends_corrupt_line.jsonl — drives TC0148.
# Hand-crafted with line 2 truncated mid-JSON.
sends_corrupt_line: |
  {"issue_id":"2026-05-19","channel":"email","recipients_count":12,"success_count":12,"failure_count":0,"status":"ok","timestamp":"2026-05-19T00:05:00+00:00"}
  {"issue_id":"2026-05-19","channel":"slac
  {"issue_id":"2026-05-19","channel":"telegram","recipients_count":2,"success_count":2,"failure_count":0,"status":"ok","timestamp":"2026-05-19T00:08:00+00:00"}

# tests/fixtures/cli/draft_outputs/issue-2026-05-19.md — canonical RenderedIssue.markdown fixture.
# Used by send TCs (TC0129–TC0131, TC0135) so they don't need the full pipeline running.

# tests/fixtures/workflows/draft_yml_parsed.yaml — expected YAML structure for TC0167–TC0173, TC0176, TC0177.
# tests/fixtures/workflows/send_yml_parsed.yaml — expected YAML structure for TC0178–TC0183, TC0187, TC0188.
# Both are reference files; tests load the real workflow file and compare to these.

# tests/fixtures/readme/sections_required.yaml — drives TC0190–TC0195.
readme_required_sections:
  - "## What this is"
  - "## How it works"
  - "## Quickstart"
  - "## Configuration"
  - "## Secrets"
  - "## Running the workflows"
  - "## Development"
  - "## Project structure"
  - "## Links"
readme_required_secrets:
  - ANTHROPIC_API_KEY
  - SMTP_HOST
  - SMTP_PORT
  - SMTP_USER
  - SMTP_PASS
  - SMTP_FROM
  - SLACK_WEBHOOK_URLS
  - TELEGRAM_BOT_TOKEN
  - GITHUB_TOKEN
```

---

## Automation Status

| TC | Title | Status | Implementation |
|----|-------|--------|----------------|
| TC0126 | `techletter --help` lists 3 sub-commands | Pending | - |
| TC0127 | draft happy path writes file | Pending | - |
| TC0128 | BudgetExceededError → exit 3, no file | Pending | - |
| TC0129 | send all ok → exit 0, 3 records | Pending | - |
| TC0130 | send 1 failed → exit 5, all attempted | Pending | - |
| TC0131 | send all already-sent → exit 0, no calls | Pending | - |
| TC0132 | dry-run writes to .local/, no side effects | Pending | - |
| TC0133 | dry-run --no-cache bypasses cache | Pending | - |
| TC0134 | --config + --log-level routed | Pending | - |
| TC0135 | send --channel slack only | Pending | - |
| TC0136 | Exit-code mapping parametric | Pending | - |
| TC0137 | BUDGET_EXCEEDED on stderr (not stdout) | Pending | - |
| TC0138 | Invalid --issue date → exit 2 | Pending | - |
| TC0139 | --issue valid but no draft → exit 2 | Pending | - |
| TC0140 | No args → help, exit 0 | Pending | - |
| TC0141 | SendRecord schema | Pending | - |
| TC0142 | append_send_record creates parent dir | Pending | - |
| TC0143 | already_sent ok → True | Pending | - |
| TC0144 | already_sent partial → True (don't retry) | Pending | - |
| TC0145 | already_sent failed-only → False | Pending | - |
| TC0146 | already_sent missing file → False | Pending | - |
| TC0147 | load_records round-trip | Pending | - |
| TC0148 | load_records skips corrupt line | Pending | - |
| TC0149 | load_records missing → [] | Pending | - |
| TC0150 | After failed, ok appended preserves history | Pending | - |
| TC0151 | ValidationError on construct → no half-write | Pending | - |
| TC0152 | Frozen mutation raises | Pending | - |
| TC0153 | Many records: any ok flips already_sent | Pending | - |
| TC0154 | Cache module surface | Pending | - |
| TC0155 | FetchCache round-trip | Pending | - |
| TC0156 | FetchCache different date → miss | Pending | - |
| TC0157 | LlmCache round-trip | Pending | - |
| TC0158 | LlmCache miss on any input change | Pending | - |
| TC0159 | CI guard disables reads (parametric) | Pending | - |
| TC0160 | CI guard makes set() a no-op | Pending | - |
| TC0161 | .cache/ in .gitignore | Pending | - |
| TC0162 | CLI wires cache to dry-run only | Pending | - |
| TC0163 | clear() wipes files | Pending | - |
| TC0164 | --no-cache bypass | Pending | - |
| TC0165 | Concurrent set() — no torn file | Pending | - |
| TC0166 | Corrupt file → None + WARN | Pending | - |
| TC0167 | draft.yml triggers + permissions | Pending | - |
| TC0168 | draft.yml step order | Pending | - |
| TC0169 | draft.yml ANTHROPIC_API_KEY env | Pending | - |
| TC0170 | Budget → workflow failure | Pending | - |
| TC0171 | Source-only-failure still opens PR | Pending | - |
| TC0172 | No cancel-in-progress (queue semantics) | Pending | - |
| TC0173 | Branch name includes run_id | Pending | - |
| TC0174 | actionlint passes on both YAMLs | Pending | - |
| TC0175 | Missing API key → exit 4 → failure | Pending | - |
| TC0176 | Cron expression parses to Monday UTC | Pending | - |
| TC0177 | gh pr create --title pattern | Pending | - |
| TC0178 | send.yml trigger + permissions (contents only) | Pending | - |
| TC0179 | send.yml if: merged == true (CRITICAL) | Pending | - |
| TC0180 | Issue-id extraction from branch | Pending | - |
| TC0181 | send.yml step order | Pending | - |
| TC0182 | send.yml concurrency group serialises | Pending | - |
| TC0183 | All channel secrets in env | Pending | - |
| TC0184 | Idempotency respected (no double-send) | Pending | - |
| TC0185 | CLI exit 5 → workflow failure | Pending | - |
| TC0186 | act-simulated close-without-merge → skip | Pending | - |
| TC0187 | Commit message has issue id | Pending | - |
| TC0188 | git user.email/user.name set explicitly | Pending | - |
| TC0189 | Partial → workflow success | Pending | - |
| TC0190 | README 9 sections in order | Pending | - |
| TC0191 | Quickstart commands in order | Pending | - |
| TC0192 | Secrets table lists all 9 secrets | Pending | - |
| TC0193 | Development section covers iteration loop | Pending | - |
| TC0194 | Project Structure matches disk | Pending | - |
| TC0195 | SDLC cross-links resolve | Pending | - |
| TC0196 | .env.example + .env gitignored | Pending | - |
| TC0197 | README markdown lints clean | Pending | - |

---

## Test Files Plan

```text
tests/
  unit/
    cli/
      test_cli_help.py             # TC0126, TC0140
      test_cli_draft.py            # TC0127, TC0128
      test_cli_send.py             # TC0129–TC0131, TC0135, TC0138, TC0139
      test_cli_dry_run.py          # TC0132, TC0133
      test_cli_options.py          # TC0134, TC0137
      test_cli_exit_codes.py       # TC0136 (parametric)
    audit/
      test_send_record.py          # TC0141, TC0151, TC0152
      test_append.py               # TC0142
      test_already_sent.py         # TC0143–TC0146, TC0153
      test_load_records.py         # TC0147–TC0149
      test_audit_history.py        # TC0150
    cache/
      test_cache_surface.py        # TC0154
      test_fetch_cache.py          # TC0155, TC0156
      test_llm_cache.py            # TC0157, TC0158
      test_ci_guard.py             # TC0159, TC0160 (CRITICAL — load-bearing)
      test_cache_gitignore.py      # TC0161
      test_cache_clear.py          # TC0163
      test_cache_atomic.py         # TC0165
      test_cache_corrupt.py        # TC0166
    workflows/
      test_draft_yml.py            # TC0167–TC0169, TC0172, TC0173, TC0176, TC0177
      test_send_yml.py             # TC0178–TC0183, TC0187, TC0188
      test_actionlint.py           # TC0174
    readme/
      test_readme_structure.py     # TC0190, TC0191, TC0192, TC0193
      test_readme_links.py         # TC0194, TC0195
      test_env_example.py          # TC0196
      test_readme_lint.py          # TC0197
  integration/
    cli/
      test_cache_wiring.py         # TC0162, TC0164
    workflows/
      test_draft_yml_act.py        # TC0170, TC0171, TC0175 (skip-if-no-act)
      test_send_yml_act.py         # TC0184, TC0185, TC0186, TC0189 (skip-if-no-act)
  fixtures/
    audit/sends_*.jsonl
    cli/draft_outputs/issue-2026-05-19.md
    workflows/{draft,send}_yml_parsed.yaml
    readme/sections_required.yaml
  conftest.py                       # CliRunner fixture, fake pipeline, scrubbed CI env, frozen clock
```

**Per-module coverage floor** (TSD ≥95% line + branch):

- `techletter/audit.py` — `test_audit/*.py` exercises every branch of `already_sent` (ok/partial/failed/missing) and append/load (round-trip, corrupt, empty)
- `techletter/cache.py` — `test_cache/*.py` covers the CI guard's positive/negative paths under both env-var triggers, plus atomic write and corrupt-read

**Workflow YAML tests** are not under coverage's purview; the `test_workflows/` directory is its own gate, run alongside the regular pytest suite, and `actionlint` is invoked as a subprocess. The `act`-style behavioural tests (TC0170, TC0171, TC0175, TC0184–TC0186, TC0189) `pytest.skip` if `act` is not on `PATH`; they're documented as "manual smoke OK" in that case.

---

## Traceability

| Artefact | Reference |
|----------|-----------|
| PRD | [sdlc-studio/prd.md](../prd.md) |
| Epic | [EP0003](../epics/EP0003-orchestration-and-dx.md) |
| TSD | [sdlc-studio/tsd.md](../tsd.md) |
| Upstream | [TS0001](TS0001-content-ingestion.md) (sources), [TS0002](TS0002-composition-pipeline.md) (compose) |
| Downstream | TS0004 (delivery) will consume the `SendRecord` model + `already_sent` contract from US0013 |
| Stories | [US0012](../stories/US0012-techletter-cli-scaffolding.md), [US0013](../stories/US0013-sends-jsonl-and-idempotency.md), [US0014](../stories/US0014-cache-helpers.md), [US0015](../stories/US0015-draft-workflow-yaml.md), [US0016](../stories/US0016-send-workflow-yaml.md), [US0017](../stories/US0017-readme-quickstart-and-dev-loop.md) |

---

## Open Questions

_None._ Inherits all decisions from PRD v0.4.0, TRD v0.3.0, TSD v0.1.0, EP0003. The smoke-send step (per TSD) is implemented inside `draft.yml` (US0015) but is itself a behavioural acceptance gate, not a unit test — its failure-blocks-PR behaviour is documented in the TSD's CI Quality Gates table and is the production E2E.

---

## Revision History

| Date | Author | Change |
|------|--------|--------|
| 2026-05-19 | HYL | Initial spec authored from EP0003 stories US0012–US0017. 72 test cases across 44 ACs (full coverage). |
| 2026-05-19 | HYL | Reviewed and promoted Draft → Ready: 44/44 ACs, 72 TCs. **Notes for automation step:** (a) act-style TCs (TC0170/0171/0175/0184–0186/0189) currently `pytest.skip` if `act` is not on `PATH` — convert to `xfail(strict=True)` or require `act` in CI image so the behavioural gate around `if: merged == true` is never silently bypassed; (b) TC0194 (README Project Structure matches disk) depends on US0017 landing after the rest of EP0003. |
