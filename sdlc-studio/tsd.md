<!--
Test Strategy Document
Generated via /sdlc-studio tsd create
-->

# Test Strategy Document

> **Project:** Tech-Letter for HYL
> **Version:** 0.1.1
> **Status:** Ready
> **Last Updated:** 2026-05-19
> **Owner:** HYL

## Overview

Tech-Letter for HYL is a once-weekly batch pipeline: ingest from 6 sources → cluster → rank → compose with Claude Sonnet → render Markdown → ship a PR → on merge, deliver to ≤100 subscribers across Email, Slack, and Telegram. There is no UI, no web server, no database — git is the only durable store; GitHub Actions is the only runtime.

The strategy this implies is unusual on three axes:

1. **Most of the system is pure functions.** Cluster/rank are LLM calls behind a thin client; everything else is parsers, splitters, escapers, renderers, and adapters. Pure code is cheap to test heavily.
2. **External services are heterogeneous and lightly typed.** arXiv (XML), GitHub trending (HTML scrape), RSS (varied flavours), SMTP, two webhook APIs. Each can drift. The biggest test risk isn't logic — it's silent contract drift.
3. **No UI means no traditional E2E.** "End-to-end" here means a pipeline test: synthetic items → ranked → composed → assembled → handed to fake channels. The author-only smoke send in `draft.yml` substitutes for production E2E.

The strategy therefore overweights **unit tests on pure helpers** (splitters, escapers, parsers, model validators) and **integration tests with recorded fixtures** (VCR cassettes for ingestion, `pytest-httpx` + `aiosmtpd` for delivery), while deferring perf/security entirely.

## Test Objectives

- Verify every PRD F-* feature has at least one acceptance-criteria-linked test that exercises its golden path.
- Guarantee that splitter/escaper/parser code paths — the surfaces where subtle bugs corrupt user-visible output — are covered ≥95%.
- Make external-service contract drift loud (cassette mismatches, schema validation failures) rather than silent.
- Keep CI runtime under 3 minutes so feedback is fast and HYL never disables the pipeline out of frustration.
- Ensure no API credentials, bot tokens, or webhook URLs appear in any test artifact, log, or PR diff.

## Scope

### In Scope

- Unit tests for: `Item`/`Cluster`/`RankedClusters`/`DeepDive`/`QuickMention`/`RenderedIssue`/`SendRecord` model validation, `SourceAdapter`/`ChannelAdapter` protocol conformance, all parsers (arXiv XML, GitHub HTML, RSS, sends.jsonl), all converters (CommonMark→mrkdwn, CommonMark→Telegram HTML, markdown-strip→plain-text), both splitters (Slack 3,500-char, Telegram 3,900-char), the LLM client's token-counter + budget-abort logic, idempotency check (`already_sent`), cache helpers.
- Integration tests for: source adapters against recorded VCR cassettes, channel adapters against fake servers (`pytest-httpx` for Slack/Telegram, `aiosmtpd` for Email), source/channel registries with fake adapters, the cluster→rank→compose→render→assemble pipeline with stubbed LLM responses, CLI sub-commands (`techletter draft`, `techletter send`, `techletter dry-run`) against an in-memory pipeline.
- An author-only **smoke send** that runs as part of `draft.yml` — every drafted issue is delivered to HYL's personal email/Slack chat/Telegram chat before the PR is opened, so HYL sees the real rendered output before approving.
- CI quality gates: `ruff check`, `ruff format --check`, `pyright`, `pytest` with coverage gate, secret-leak scan.

### Out of Scope (v1)

- **Performance / load testing.** The pipeline runs once a week; subscriber count ≤100. The PRD's perf targets (draft <5 min, send <2 min) are enforced by GitHub Actions job timeouts, not a load suite. Re-evaluate at >500 subscribers or sub-daily cadence.
- **Security testing beyond secret-leak scanning.** No auth surface, no user input, no database. Threat model is dominated by "did we accidentally print a secret?" — handled by a CI grep. Dependency vulnerability scanning is deferred to Dependabot/Renovate (a future CR, not v1).
- **Live integration tests against arXiv / GitHub / RSS / Anthropic / SMTP / Slack / Telegram in CI.** All recorded via VCR cassettes or fakes. Live tests only run manually via `pytest -m live` and never in CI (rate limits, flakiness, cost).
- **Mutation testing, fuzzing, contract testing across services** — overkill for a single-author CLI.
- **Browser / UI testing** — there is no UI.

---

## Test Levels

### Coverage Targets

| Level | Target | Rationale |
|-------|--------|-----------|
| Unit (overall) | ≥85% line coverage | Realistic floor across all modules including HTTP shells |
| Unit (pure helpers) | ≥95% line + branch coverage | Parsers, splitters, escapers, model validators — cheap to push high, expensive to get wrong |
| Integration | 100% pass on fixtures | Cassettes/fakes are deterministic; flakiness = a bug |
| Pipeline (end-to-end with stubs) | 100% pass | Single test exercises the whole draft → render path |
| Smoke send | 1 successful real send per draft | HYL eyeballs output before merging |

**Why 95% on helpers but 85% overall?** The helper layer (splitters, escapers, parsers) is where the most user-visible bugs live and where coverage is cheapest. The 85% overall target prevents diminishing returns on HTTP-shell glue that's mostly "construct request, call `httpx.post`, parse response" — already heavily covered by integration tests.

Coverage measured by `coverage.py` with `branch = true`. Reports posted as a PR comment via `pytest-cov` + a `gh pr comment` step in CI.

### Unit Testing

| Attribute | Value |
|-----------|-------|
| Coverage Target | ≥85% line (overall), ≥95% line + branch (pure helpers) |
| Framework | `pytest` ≥ 8.0 with `pytest-cov`, `freezegun`, `hypothesis` (property-based for splitters/escapers) |
| Execution | `pytest tests/unit/ -q` — local + CI on every PR |
| Mocking | Stdlib `unittest.mock`; `pytest-httpx` for any HTTP that escapes a helper |
| Naming | `test_<module>.py` mirroring `techletter/<module>.py`; functions named `test_<scenario>_<expected>` |

**Property-based tests** (with `hypothesis`) are required for:
- `split_for_slack` / `split_for_telegram` — invariants: never split mid-tag, never split mid-code-block, chunk count × ≤ limit_chars ≥ input length, concatenation reconstructs input (modulo the `(continued, N/N)` prefix).
- `commonmark_to_mrkdwn` / `commonmark_to_telegram_html` — invariants: escape-first-then-format ordering preserves ill-formed input; round-trip through `html.unescape` recovers original characters.
- `Item` validation — generated valid/invalid payloads exercise pydantic's edge handling.

### Integration Testing

| Attribute | Value |
|-----------|-------|
| Scope | Source adapters ↔ recorded HTTP responses; channel adapters ↔ fake servers; CLI ↔ in-memory pipeline; idempotency check ↔ tmpfile-backed `sends.jsonl` |
| Framework | `pytest` + `vcrpy` (cassettes) + `pytest-httpx` (Slack/Telegram fake) + `aiosmtpd` (Email fake) + `tenacity` mocked clock |
| Execution | `pytest tests/integration/ -q` — local + CI on every PR |
| Fixture storage | `tests/cassettes/<source>/<scenario>.yaml` checked into the repo |
| Cassette refresh | `pytest --record-mode=rewrite tests/integration/sources/` — manual, after upstream changes |

**Why VCR over hand-built mocks:** GitHub's trending HTML is the highest-likelihood failure mode in the system (TRD risk register). A hand-built mock encodes what we *think* the page looks like; a cassette captures what it *actually* looks like at a known point in time. When GitHub redesigns the page, the cassette becomes stale and the test fails — that's the signal we want.

**LLM (Anthropic) is the exception**: VCR-recording real Claude responses would burn budget on every test refresh and produce non-deterministic cassettes (sampling). Anthropic calls are stubbed via a `FakeLLMClient` that returns fixture JSON.

### Pipeline (End-to-End with Stubs)

| Attribute | Value |
|-----------|-------|
| Scope | One full pipeline run: 3 stubbed source adapters → cluster → rank → compose → render → assemble → 3 fake channel adapters |
| Framework | `pytest` orchestrating the real CLI entry point with all I/O behind fakes |
| Execution | `pytest tests/pipeline/test_full_run.py` — local + CI on every PR |
| Assertions | Output `RenderedIssue.markdown_body` is non-empty, ≥3 deep dives and ≤10 quick mentions, no `[INFERRED]` markers, all referenced items have valid URLs |

This single test serves the role that a "happy-path E2E test suite" plays in a UI-driven app: it proves the wiring is correct end-to-end without depending on any external service.

### Smoke Send (Author-only, runs in draft.yml)

| Attribute | Value |
|-----------|-------|
| Scope | The drafted `RenderedIssue` is sent to HYL's personal email + Slack + Telegram chat |
| When | As the final step of `draft.yml`, before the PR is committed (or as a step on the same job, before `gh pr create`) |
| Recipients | `subscribers.yaml` has an explicit `_smoke:` section with HYL's own three addresses — separate from production recipients |
| Failure handling | Smoke send failure marks the workflow as failed; the PR is NOT created. HYL fixes locally and re-runs. |
| Channel | All three (email + Slack + Telegram) so cross-channel rendering bugs surface |

The smoke send is **not** a substitute for unit tests — it's the human-in-the-loop step that catches "the converter passes its tests but the message reads strangely" class of bugs that no unit test can detect.

### E2E Feature Coverage Matrix

Each PRD feature is covered by at least one named test, addressed through the full chain `PRD F-XX → Epic → Story → AC → TC` (the test specs `TS0001–TS0004` carry the explicit AC↔TC mapping per story). The rows below are **TSD-internal test areas** that summarise the major coverage concerns; they do **not** preserve the PRD's F-XX numbering — for that mapping consult each epic's test plan section, which links to its TS file. "E2E" here means "exercises the feature through the user-facing surface" — the CLI sub-command or the workflow trigger.

| Test Area | Coverage Layer | Test File (planned) | Status |
|-------------|----------------|---------------------|--------|
| F-01 Multi-source ingestion | Integration + Pipeline | `tests/integration/sources/test_all_sources.py` | Not started |
| F-02 LLM-based clustering & ranking | Pipeline + Unit | `tests/pipeline/test_full_run.py`, `tests/unit/test_rank.py` | Not started |
| F-03 Composition with anti-hype style | Unit + Pipeline | `tests/unit/test_compose_*.py`, `tests/pipeline/test_full_run.py` | Not started |
| F-04 Weekly cron trigger | Smoke (manual) | `.github/workflows/draft.yml` cron schedule expression | Not started |
| F-05 Multi-channel delivery | Integration + Smoke | `tests/integration/channels/test_*.py`, `draft.yml` smoke step | Not started |
| F-06 Subscriber config | Unit | `tests/unit/test_subscribers_loader.py` | Not started |
| F-07 Idempotency | Unit + Integration | `tests/unit/test_idempotency.py`, `tests/integration/test_send_workflow.py` | Not started |
| F-08 Failure isolation | Unit + Integration | `tests/unit/test_registry.py`, `tests/integration/channels/test_*.py` | Not started |
| F-09 Draft → approve → send flow | Integration | `tests/integration/test_workflow_yaml.py` (using `act` or a yaml linter) | Not started |
| F-10 Anti-hype style lint | Unit | `tests/unit/test_anti_hype_lint.py` | Not started |
| F-11 Logging & audit | Unit + Integration | `tests/unit/test_sends_jsonl.py`, `tests/integration/test_log_persistence.py` | Not started |

### Performance Testing

| Attribute | Value |
|-----------|-------|
| Scope | **Out of scope for v1.** Job-level timeouts in GitHub Actions YAML enforce the PRD targets (draft <5 min, send <2 min). |
| Re-evaluation trigger | Subscriber count >500, or cadence shifts to sub-daily |

### Security Testing

| Attribute | Value |
|-----------|-------|
| Scope | Secret-leak scanning only |
| Tools | A `pytest` step that greps the test output, log files, and rendered issue artifacts for substrings matching `SMTP_PASS`, `TELEGRAM_BOT_TOKEN`, `ANTHROPIC_API_KEY`, `SLACK_WEBHOOK_URLS` environment values |
| Re-evaluation trigger | Any future feature that accepts external input (subscriber signup API, web UI, etc.) |

---

## Test Environments

| Environment | Purpose | URL / Location | Data |
|-------------|---------|----------------|------|
| Local dev | Author writes & runs tests | developer machine; `.cache/` populated | VCR cassettes + LLM fixtures |
| GitHub Actions CI | PR validation + cron triggers | `ubuntu-latest` runner | Same fixtures (cached via `actions/cache@v4` keyed on `uv.lock`) |
| Smoke send (in draft.yml) | Human-in-the-loop pre-merge | Real SMTP/Slack/Telegram | `subscribers.yaml` `_smoke:` section only |
| Production (on PR merge) | Real send to subscribers | Real SMTP/Slack/Telegram | `subscribers.yaml` production sections |

There is no "staging" environment — the smoke send is the staging step. There is no `localhost` web server to spin up; the CLI runs to completion and exits.

## Test Data Strategy

### Approach

Three classes of fixture, stored under `tests/fixtures/` (with cassettes under `tests/cassettes/`):

1. **VCR cassettes** — real HTTP responses captured once from arXiv / GitHub / RSS feeds. Re-recorded manually when an upstream change breaks a test. Cassettes are PII-free (these are public APIs).
2. **LLM response fixtures** — JSON files containing canned `Cluster`, `RankedClusters`, `DeepDive`, `QuickMention` payloads consumed by `FakeLLMClient`. One fixture per compose-prompt variant per `item_kind`.
3. **Synthetic `Item` instances** — pydantic-validated test factories using `pydantic-factories` or hand-written builders. Used in unit tests where no real fixture is needed (e.g., testing the splitter).

Frozen time for any date-sensitive logic via `freezegun` — default test clock is `2026-05-19T00:00:00Z` (the project's epoch).

### Sensitive Data

There is no PII in the system — sources are public, subscribers are voluntary. The only sensitive values are:

- `ANTHROPIC_API_KEY`, `SMTP_PASS`, `TELEGRAM_BOT_TOKEN`, `SLACK_WEBHOOK_URLS` — only set in GitHub Secrets; tests use placeholders (`"sk-test-fake"`, etc.) and assert no real secret is ever read by tests.
- Subscriber email addresses / chat IDs — in production `subscribers.yaml`. Test fixtures use clearly-synthetic addresses (`alice@example.test`, chat IDs in the negative test range). Real `subscribers.yaml` is **never** checked in to any fixture or test cassette.

A `pytest` collection-level hook fails the run if any cassette or fixture contains a value matching `re.compile(r'(sk-ant|AKIA|xoxb-|SG\.|AIza)')` (common API-key prefixes).

---

## Automation Strategy

### Automation Candidates (all auto in v1)

- Every unit test
- Every integration test (cassettes are committed)
- The pipeline end-to-end test
- The CI quality gate suite
- The PR-merge → send workflow itself (auto-runs when merge predicate is true)

### Manual Testing

- **The smoke send.** HYL reads the rendered output before approving the PR. The system doesn't automate "did it read well?"
- **Cassette refresh.** When `tests/integration/sources/test_arxiv.py` starts failing because arXiv changed their feed format, HYL runs the rewrite-mode command manually, inspects the diff, and commits the updated cassette.
- **Anti-hype style review.** The lint catches obvious "groundbreaking / revolutionary" wording; the human catches subtler hype.

### Automation Framework Stack

| Layer | Tool | Purpose |
|-------|------|---------|
| Test runner | `pytest` ≥ 8.0 | Test discovery, fixtures, parametrisation |
| Coverage | `coverage.py` ≥ 7.0 via `pytest-cov` (`branch = true`) | Line + branch coverage with PR-comment reporting |
| Type check | `pyright` ≥ 1.1.380 (per TRD ADR-006) | Static type safety |
| Lint / format | `ruff` ≥ 0.6 (per TRD ADR-006) | Style + import order + simple bug patterns |
| HTTP mock | `pytest-httpx` ≥ 0.30 | Fake Slack / Telegram / Anthropic endpoints |
| VCR cassettes | `vcrpy` ≥ 6.0 or `pytest-recording` | Record/replay real arXiv / GitHub / RSS responses |
| SMTP fake | `aiosmtpd` (stdlib-adjacent) | Receive emails in tests without a real server |
| Time control | `freezegun` ≥ 1.5 | Deterministic dates for idempotency + issue-date tests |
| Property-based | `hypothesis` ≥ 6.100 | Splitter / escaper invariants |
| Test factories | `pydantic-factories` or hand-rolled builders | Synthetic `Item` / `RenderedIssue` instances |

All test dependencies declared in `pyproject.toml` under `[dependency-groups.test]` (uv convention).

---

## CI/CD Integration

### Pipeline Stages

1. **Pre-commit** (local; optional but recommended): `ruff format`, `ruff check --fix`, `pyright`. Not enforced — but `.pre-commit-config.yaml` is committed for convenience.
2. **On PR open / push to a PR branch:** `ruff check`, `ruff format --check`, `pyright`, `pytest tests/unit/ tests/integration/ tests/pipeline/ --cov --cov-report=xml --cov-report=term`, coverage threshold check, secret-leak scan. PR-comment with coverage summary.
3. **On `draft.yml` cron (Monday 09:00 KST):** Runs the actual pipeline (`techletter draft`), commits the rendered issue, sends the **author-only smoke** to all three channels, opens the PR. Note: the CI test suite is *not* re-run inside `draft.yml` — that's covered by the PR check.
4. **On `send.yml` (PR merged):** `techletter send` runs against the merged issue file. Idempotency check via `sends.jsonl`. Appends a `SendRecord` to `sends.jsonl` and commits it back to `main`.

### Quality Gates

| Gate | Criteria | Blocking | Where Enforced |
|------|----------|----------|----------------|
| `ruff check` clean | 0 errors | Yes | PR CI |
| `ruff format --check` clean | 0 diffs | Yes | PR CI |
| `pyright` clean | 0 errors | Yes | PR CI |
| Unit + integration tests pass | 100% pass | Yes | PR CI |
| Pipeline e2e test passes | 100% pass | Yes | PR CI |
| Coverage overall | ≥ 85% line | Yes | PR CI |
| Coverage on pure helpers — see authoritative list below | ≥ 95% line + branch | Yes | PR CI (per-module check via `coverage report --fail-under-by-file`) |

**Pure-helper modules subject to the ≥ 95% line + branch gate** (aggregated from each test spec's "Per-module coverage floor" section — TS0001–TS0004 are the canonical sources):

- `techletter/models/` — `Item` (TS0001)
- `techletter/audit.py` — `SendRecord`, `append_send_record`, `already_sent`, `load_records` (TS0003)
- `techletter/cache.py` — `FetchCache`, `LlmCache`, CI-guard (TS0003)
- `techletter/delivery/base.py` — `SendReport` consistency validator (TS0004)
- `techletter/delivery/slack.py` — `commonmark_to_mrkdwn`, `split_for_slack` (TS0004)
- `techletter/delivery/telegram.py` — `commonmark_to_telegram_html`, `split_for_telegram` (TS0004)
- `techletter/delivery/email.py` — `markdown_to_plaintext` (TS0004)
- `techletter/pipeline/cluster.py` — JSON parse + AC5 invariants (TS0002)
- `techletter/pipeline/rank.py` — sort + clamp + pre-compose budget projection (TS0002)
- `techletter/pipeline/assemble.py` — pure markdown rendering (TS0002 TC0113–TC0125)
- `techletter/pipeline/compose.py::format_shipping_signals` (TS0002 TC0108)

Adapter shells (the `send()` / `fetch()` methods themselves, HTTP glue, CLI command wiring) are held to the ≥ 85% overall floor, not the per-module ≥ 95% gate.
| Secret-leak scan | 0 matches in test artifacts | Yes | PR CI |
| Smoke send (draft.yml only) | 1 success on each enabled channel | Yes | `draft.yml` |
| Send-job idempotency check (`send.yml`) | `already_sent(issue_id, channel) == False` per channel | Yes | `send.yml` (via `techletter send`) |

A failing gate blocks the PR from merging. The smoke gate blocks the draft PR from being opened (no PR = nothing to merge = nothing sent).

---

## Defect Management

Defects in this project are tracked as `/sdlc-studio bug` artefacts. Because the project has one author and one approval gate (PR merge), severity is mostly about whether subscribers received broken output:

### Severity Definitions

| Severity | Definition | SLA |
|----------|------------|-----|
| Critical | A send went out with corrupt / empty / privacy-leaking content to real subscribers | Same week — issue a correction note in the next issue and revert offending code on `main` |
| High | A send failed silently (sends.jsonl shows `partial`/`failed`, subscribers never received) | Same week — fix and re-run `send.yml` after restoring idempotency state |
| Medium | A pipeline run failed but no send occurred (draft never opened, or smoke caught a bug) | Next week's run |
| Low | Rendering ugliness, minor wording, formatting glitches | Backlog; next issue |

---

## Tools & Infrastructure

| Purpose | Tool |
|---------|------|
| Test management | Markdown test-specs under `sdlc-studio/test-specs/` linked from each user story |
| CI/CD | GitHub Actions (per TRD ADR-001) |
| Browser automation | n/a (no UI) |
| Coverage | `coverage.py` ≥ 7.0 with `branch = true`, `concurrency = ["thread"]` |
| Test runner | `pytest` ≥ 8.0 |
| HTTP mocking | `pytest-httpx` |
| VCR cassettes | `vcrpy` (or `pytest-recording`) |
| SMTP fake | `aiosmtpd` |
| Time freezing | `freezegun` |
| Property-based testing | `hypothesis` |
| Type checking | `pyright` (per TRD ADR-006) |
| Linting | `ruff` (per TRD ADR-006) |
| Secret scan | Custom `pytest` collection-level grep step |

---

## Test Organisation

```text
tests/
  unit/
    models/                  # TS0001 — Item model + protocol conformance
    sources/                 # TS0001 — adapter helpers (arxiv/github/rss)
    config/                  # TS0001 — load_sources, ConfigLoadError
    llm/                     # TS0002 — LlmClient + budget guard + retries
    pipeline/                # TS0002 — cluster/rank/compose/assemble parse + render
    cli/                     # TS0003 — click sub-commands + exit codes
    audit/                   # TS0003 — SendRecord + already_sent + load_records
    cache/                   # TS0003 — FetchCache, LlmCache, CI guard, atomic write
    workflows/               # TS0003 — YAML static checks (pyyaml + actionlint)
    readme/                  # TS0003 — README structure + .env.example
    delivery/                # TS0004 — base + per-channel escapers/splitters + registry
  integration/
    sources/                 # TS0001 — VCR cassettes + pytest-httpx for retry paths
    cli/                     # TS0003 — cache wiring smoke
    workflows/               # TS0003 — act-style local simulation (skip-if-no-act)
    delivery/
      email/                 # TS0004 — aiosmtpd
      slack/                 # TS0004 — pytest-httpx
      telegram/              # TS0004 — pytest-httpx + token-leak guard
  pipeline/
    test_full_run.py         # TSD-defined single full-pipeline test
  cassettes/
    arxiv/recent_cs_ai_cs_cl.yaml          # TS0001 TC0013
    github/trending_weekly_en.yaml         # TS0001 TC0022, TC0024
    rss/three_feeds.yaml                   # TS0001 TC0032, TC0033
  fixtures/
    items/                                 # canonical Item dicts + fixture clusters
    sources/                               # parametric input tables
    llm/                                   # FakeLLMClient response payloads (TS0002)
    audit/                                 # sends_*.jsonl curated histories (TS0003)
    cli/                                   # CLI draft outputs (TS0003)
    workflows/                             # parsed-YAML reference fixtures (TS0003)
    readme/                                # required-sections checklist (TS0003)
    delivery/                              # subscribers/channels configs + issue bodies
    usage/                                 # usage_report samples for assemble_issue
  conftest.py                              # FakeLLMClient (TS0002 contract),
                                           # hypothesis strategies (TS0004 §env),
                                           # frozen clock, CI-env scrubbing,
                                           # spied channel adapters, CliRunner
```

The authoritative per-spec layout — including specific test file names — lives in each TS file's **Test Files Plan** section. This tree summarises the agreed structure at the directory level.

**Naming conventions:**
- Test files mirror the module under test: `tests/unit/test_<module>.py` ↔ `techletter/<module>.py`.
- Test functions: `test_<scenario>_<expected>` (e.g., `test_arxiv_parse_empty_feed_returns_empty_list`).
- Cassette files: `<endpoint>_<scenario>.yaml`.
- Fixtures: snake_case JSON in `tests/fixtures/`.

---

## Anti-Patterns to Avoid

Captured here to prevent the test suite from drifting into low-signal patterns:

1. **No conditional assertions.** `if items: assert items[0].title` silently passes when items is empty. Use `assert len(items) > 0; assert items[0].title == ...`.
2. **No mock-only adapter tests.** A test that mocks `requests.get` and asserts the mock was called proves nothing about the adapter's parsing logic. Use VCR cassettes or fake servers.
3. **No "test that test runs."** A test that asserts `True` or only constructs objects without exercising behaviour is worse than no test — it inflates the count and hides gaps.
4. **No real Anthropic API calls in any automated test.** Always use `FakeLLMClient`. The one exception is a manual smoke script (`scripts/smoke_llm.py`) gated behind `-m live`.
5. **No real SMTP / Slack / Telegram calls in unit or integration tests.** Real sends only happen in `draft.yml`'s smoke step (against HYL's own addresses) and `send.yml` (to subscribers).
6. **No tests that depend on wall-clock time.** Always `freezegun`. Idempotency tests in particular are brittle without frozen time.
7. **No skipping CI gates.** If a test is flaky, fix it or delete it — never `@pytest.mark.skip` and merge.

---

## Related Specifications

- [Product Requirements Document](prd.md) — v0.4.1 (Ready)
- [Technical Requirements Document](trd.md) — v0.3.2 (Ready)
- [User Personas Index](personas/index.md)
- [Epic Index](epics/_index.md)
- [Story Index](stories/_index.md)
- [Test Specs Index](test-specs/_index.md) — TS0001–TS0004 (all Ready)

## Open Questions

_None._ All decisions captured above:

- Coverage targets: tiered (≥85% overall, ≥95% pure helpers) — accepted 2026-05-19.
- External services: VCR cassettes + fake servers — accepted 2026-05-19.
- Smoke send: author-only run inside `draft.yml` — accepted 2026-05-19.
- Perf/security: out of scope for v1, re-evaluate at >500 subscribers — accepted 2026-05-19.

## Revision History

| Date | Author | Change |
|------|--------|--------|
| 2026-05-19 | HYL | Initial Test Strategy Document created from PRD v0.4.0 and TRD v0.3.0. Four key decisions ratified: tiered coverage targets, VCR + fakes for external services, author-only smoke in `draft.yml`, perf/security out of scope. |
| 2026-05-19 | Claude | Unified `/sdlc-studio review` pass: clarified §3 E2E Feature Coverage Matrix header. Renamed column from `PRD Feature` to `Test Area` and added a callout that PRD F-XX → test mapping is resolved through the per-epic test spec chain (TS0001–TS0004). The matrix rows are TSD-internal test areas, **not PRD F-XX features** — earlier wording was misleading for cross-doc traceability. TSD status remains Draft pending explicit promotion to Ready (flagged for user). |
| 2026-05-19 | Claude | Focused `/sdlc-studio tsd review` pass (v0.1.0 → v0.1.1): (a) CI Quality Gate's pure-helper coverage row updated to reference the **actual** module list aggregated from TS0001–TS0004's "Per-module coverage floor" sections — previous list named `techletter/parsers/`, `techletter/converters/`, `techletter/splitters/` directories that don't exist in the proposed layout; (b) §Test Organisation tree regenerated to mirror the subdirectory structure ratified by the 4 Ready test specs (per-domain dirs under `tests/unit/` and `tests/integration/` instead of the prior flat layout); (c) Related Specifications version refs bumped (PRD v0.4.0 → v0.4.1, TRD v0.3.0 → v0.3.2) and Test Specs Index linked; (d) added explicit overview line under the tree pointing to per-spec authoritative Test Files Plan sections. **Status promoted Draft → Ready** — all 4 ratified decisions are referenced by the 4 Ready test specs; the doc has no outstanding work. |
