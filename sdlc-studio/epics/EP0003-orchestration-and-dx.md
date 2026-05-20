# EP0003: Orchestration & Developer Experience

> **Status:** Draft
> **Owner:** HYL
> **Reviewer:** HYL
> **Created:** 2026-05-19
> **Target Release:** v1.0 (first issue shipped)

## Summary

Stitch the source/composer/delivery pieces into a runnable system. Two GitHub Actions workflows (`draft.yml` weekly cron → opens PR; `send.yml` on PR merge → fans out to channels), a CLI (`techletter draft | send | dry-run`), the append-only `logs/sends.jsonl` audit + idempotency log, and a developer-only `.cache/` so prompt iteration doesn't burn LLM tokens. This is where the system stops being a pile of modules and becomes a working pipeline.

## Inherited Constraints

| Source | Type | Constraint | Impact |
|--------|------|------------|--------|
| PRD | Schedule | Weekly cron Monday 09:00 KST (`0 0 * * 1` UTC) | Hard-coded into `draft.yml` |
| PRD | Approval | Draft is a PR; merge = send signal; close-without-merge = no-op; queue (don't skip) on collision | `send.yml` trigger is `pull_request.closed` filtered by `merged == true` |
| PRD | Idempotency | Same issue id never sends twice on same channel | Check `logs/sends.jsonl` before each channel send |
| PRD | Audit | `logs/sends.jsonl` committed to `main` | `send.yml` commits back to main after fan-out |
| PRD | Cost guardrail | LLM budget enforced before compose | The CLI must surface budget aborts as workflow failures, not silent success |
| TRD | Runtime | GitHub Actions only; no other deployment surface (ADR-001) | All orchestration glue is YAML + CLI; no daemon |
| TRD | Tooling | uv + ruff + pyright (ADR-006); `pytest` for tests | CI workflows install via `uv sync` |
| TRD | Dev cache | `.cache/` git-ignored; only used by `--dry-run`; never read in CI (ADR-005) | Cache implementation must hard-fail open in CI |

---

## Business Context

### Problem Statement
A pipeline that produces a `RenderedIssue` in memory is not a newsletter — there needs to be a thing that runs it every week, lets HYL approve it, and sends it out. There also needs to be a way for HYL to iterate on prompts and templates locally without burning LLM tokens. Both concerns live here.

**PRD Reference:** [§3 Feature Inventory — F-04, F-09, F-10, F-11](../prd.md#3-feature-inventory)

### Value Proposition
Without this epic, the project never ships an issue. This epic also delivers HYL's primary constraint: minutes-per-week effort instead of curating-from-scratch effort. The PR-as-approval-gate is the single user-facing UX of the whole project.

### Success Metrics

| Metric | Current | Target | Measurement |
|--------|---------|--------|-------------|
| Successful scheduled runs / scheduled runs | n/a | ≥ 95% (industry-acceptable cron reliability) | GitHub Actions run history |
| Send workflows skipping due to idempotency hit | n/a | 0 in normal operation; ≥1 means something is wrong | `logs/sends.jsonl` audit |
| HYL weekly approval time | n/a | ≤ 10 min (PRD goal) | HYL self-report |
| Local `--dry-run` end-to-end (with cache warm) | n/a | < 30 seconds | CLI timing |

---

## Scope

### In Scope
- `techletter` CLI built on `click`, with `draft`, `send`, `dry-run` sub-commands.
- `.github/workflows/draft.yml` — scheduled (weekly cron) + `workflow_dispatch`; opens PR with draft.
- `.github/workflows/send.yml` — triggered on PR merge to `main`; fans out to channels; commits `logs/sends.jsonl`.
- `logs/sends.jsonl` schema and append helper.
- Idempotency check (read `logs/sends.jsonl`, skip already-sent (issue, channel) pairs).
- `.cache/` directory + cache helpers for fetch results (per source/window) and LLM responses (by prompt SHA-256 + model + temperature).
- Cache disabled outside `--dry-run` (no accidental cache reads in CI).
- README quickstart for local development.

### Out of Scope
- Sources (EP0001), composer (EP0002), delivery (EP0004).
- Subscriber config (EP0004 — owned by delivery).
- A queue server / scheduler other than GitHub Actions.

### Affected Personas
- **HYL (Author/Editor):** primary — this epic is essentially HYL's user interface to the system. The PR workflow, the approval gate, the dry-run loop, the cache speedup — all aimed at HYL's weekly experience.

---

## Acceptance Criteria (Epic Level)

- [ ] `techletter draft` produces a `RenderedIssue`, writes it to `drafts/issue-YYYY-MM-DD.md` on a branch, and opens a PR via `gh`.
- [ ] `techletter send --issue <id>` reads the merged draft, dispatches to enabled channels, appends `SendRecord`s to `logs/sends.jsonl`, and commits the log.
- [ ] `techletter dry-run` runs the full pipeline (with cache) but writes the draft locally to `drafts/.local/` and does not open a PR or send.
- [ ] `draft.yml` runs on cron `0 0 * * 1` UTC and on `workflow_dispatch`; if the workflow fails, GitHub's default failure email reaches HYL.
- [ ] `send.yml` runs only on `pull_request.closed` with `merged == true` on `main`; never on close-without-merge.
- [ ] Queue semantics: if a draft PR already exists when the scheduled run fires, the new draft opens an additional PR (not a comment, not a skip).
- [ ] Idempotency: re-running `send` for the same (issue_id, channel) is a no-op with a logged "already sent" line.
- [ ] `.cache/` is git-ignored; cache reads only happen under `--dry-run`; in CI, cache reads return None even if the cache exists.
- [ ] Budget abort: if the composer signals a token-budget breach, `draft.yml` fails the workflow with a clear log line; no half-finished PR is opened.

---

## Dependencies

### Blocked By

| Dependency | Type | Status | Owner |
|------------|------|--------|-------|
| EP0001 Content Ingestion | Epic | Draft | HYL |
| EP0002 Composition Pipeline | Epic | Draft | HYL |
| EP0004 Multi-channel Delivery | Epic | Draft | HYL |

### Blocking

| Item | Type | Impact |
|------|------|--------|
| First scheduled run | Release milestone | Cannot ship a real issue without this epic complete |

---

## Risks & Assumptions

### Assumptions
- GitHub Actions cron triggers are reliable enough at weekly granularity (~95% on time, occasionally delayed). Acceptable.
- GitHub's `pull_request.closed` event with `merged == true` is the right trigger pattern (well-documented; widely used).
- The repo has a `GITHUB_TOKEN` with `contents: write` + `pull-requests: write` permissions — standard for Actions.

### Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| `send.yml` accidentally triggered by non-merge close events | L | H | Strict `if: github.event.pull_request.merged == true` guard; documented in PR template |
| `send.yml` runs but `logs/sends.jsonl` commit fails (race with another send) | L | M | Use `git pull --rebase` before append; serialise via concurrency group |
| Draft PR collision (multiple unresolved drafts) causes confusion | M | L | Queue semantics chosen explicitly per PRD; PR title encodes issue date; HYL merges chronologically |
| Cron drift (cron actually runs 5–30 min late on busy Actions infra) | M | L | Acceptable — weekly newsletter, not pager rotation |
| Budget-abort message gets buried in workflow logs | M | M | Emit a structured "BUDGET_EXCEEDED" log line + set step output; the failure email will surface it |

---

## Technical Considerations

### Architecture Impact
This epic implements ADR-001 (Actions as runtime), ADR-003 (git as store), and ADR-005 (dev cache). It introduces no new pattern; it's the wiring layer.

### Integration Points
- **GitHub Actions** runtime + scheduler + secrets.
- **`gh` CLI** for PR creation inside the workflow.
- **Filesystem** for `drafts/`, `logs/`, `.cache/`.
- **Click** as CLI framework.

---

## Sizing

**Story Points:** ~13
**Estimated Story Count:** 6

**Complexity Factors:**
- GitHub Actions YAML has many gotchas (permission scopes, concurrency groups, the merge-event predicate, committing back to the same branch the workflow ran on).
- Idempotency interacts with the audit log — both reads and writes hit the same file.
- The cache hard-fail-in-CI behaviour requires an explicit "am I in CI?" check that needs testing.

---

## Story Breakdown

Stories generated 2026-05-19. See [Story Index](../stories/_index.md) for full details.

- [ ] [US0012](../stories/US0012-techletter-cli-scaffolding.md) — `techletter` CLI scaffolding (3 pts)
- [ ] [US0013](../stories/US0013-sends-jsonl-and-idempotency.md) — `logs/sends.jsonl` + idempotency (3 pts)
- [ ] [US0014](../stories/US0014-cache-helpers.md) — `.cache/` helpers, CI-disabled (5 pts)
- [ ] [US0015](../stories/US0015-draft-workflow-yaml.md) — `.github/workflows/draft.yml` (3 pts)
- [ ] [US0016](../stories/US0016-send-workflow-yaml.md) — `.github/workflows/send.yml` (5 pts)
- [ ] [US0017](../stories/US0017-readme-quickstart-and-dev-loop.md) — README quickstart + dev loop docs (2 pts)

**Total:** 21 story points across 6 stories.

---

## Test Plan

**Test Spec:** [TS0003](../test-specs/TS0003-orchestration-and-dx.md) — 72 test cases (TC0126–TC0197), 44/44 ACs covered.

- Unit: `SendRecord` model + `already_sent` semantics (US0013) with full ok/partial/failed/missing branch coverage; cache key derivation + the CI-guard parametric (US0014); CLI command wiring with `click.testing.CliRunner` (US0012); exit-code mapping parametric.
- Integration: full `techletter dry-run` through fake pipeline + spied channel adapters; cache wiring verified (dry-run passes cache, draft/send pass None).
- Workflow YAML static checks: `actionlint` on both workflow files; pyyaml-parse assertions on cron expression, the load-bearing `if: merged == true` predicate, concurrency group, env-var pass-through, step order, branch-name pattern.
- Workflow behavioural simulation: `act` (skip-if-not-installed) simulates `pull_request.closed` events with `merged: true|false` to confirm the predicate.
- Manual (out of scope for TS0003, documented in TSD): the first scheduled cron run, plus the author-only smoke send inside `draft.yml`, are the production E2E — neither is a unit test.

---

## Open Questions

_None._ All design decisions inherited from PRD v0.4.0 and TRD v0.3.0.

---

## Revision History

| Date | Author | Change |
|------|--------|--------|
| 2026-05-19 | HYL | Initial epic created from PRD v0.4.0 F-04, F-09, F-10, F-11. |
| 2026-05-19 | HYL | Story breakdown linked: 6 stories (US0012–US0017, 21 pts total). |
| 2026-05-19 | HYL | Test plan linked to [TS0003](../test-specs/TS0003-orchestration-and-dx.md) — 72 TCs, 44/44 ACs covered. |
