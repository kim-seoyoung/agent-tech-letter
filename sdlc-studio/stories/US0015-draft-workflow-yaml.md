# US0015: `.github/workflows/draft.yml` — weekly cron, draft PR

> **Status:** Done
> **Epic:** [EP0003: Orchestration & Developer Experience](../epics/EP0003-orchestration-and-dx.md)
> **Owner:** HYL
> **Reviewer:** HYL
> **Created:** 2026-05-19

## User Story

**As** HYL (Author/Editor)
**I want** a `draft.yml` GitHub Actions workflow that fires weekly on Monday 09:00 KST, runs `techletter draft`, and opens a PR with the rendered issue
**So that** every Monday I get a PR in my inbox to approve or edit — without me touching anything.

## Context

### Persona Reference
**HYL (Author/Editor)** — minutes-per-week goal is satisfied or violated by this workflow. If approving the PR takes longer than reading three good newsletters, the system has failed.
[Persona details](../personas/stakeholders/users/hyl-author.md)

### Background
The PR-as-approval-gate is the single most important UX in the whole project. The workflow must be tight: cron triggers, code runs, draft is committed to a branch, `gh pr create` opens the PR. Queue semantics mean: if a previous PR is still open, this run still opens a new PR (additional, not duplicate).

---

## Inherited Constraints

| Source | Type | Constraint | AC Implication |
|--------|------|------------|----------------|
| Epic | Schedule | Weekly cron Monday 09:00 KST = `0 0 * * 1` UTC | Workflow `schedule` block uses exact cron |
| Epic | Manual run | `workflow_dispatch` supported | Workflow declares both triggers |
| Epic | Queue | New scheduled run does not skip when prior draft PR is open | No concurrency cancellation; each run creates a separate branch |
| Epic | Permissions | `contents: write`, `pull-requests: write` | Declared in workflow permissions block |
| Epic | Quality gate | Workflow fails (not silently succeeds) on `BudgetExceededError`, missing secrets, etc. | CLI exit codes from US0012 propagate as workflow failure |

---

## Acceptance Criteria

### AC1: Workflow file exists with both triggers
- **Given** the file `.github/workflows/draft.yml` exists
- **When** GitHub Actions parses it
- **Then** the workflow declares:
  - `on.schedule.cron == "0 0 * * 1"` (Monday 00:00 UTC = 09:00 KST)
  - `on.workflow_dispatch` (empty / no inputs)
- **And** the `permissions:` block grants `contents: write` and `pull-requests: write`

### AC2: Workflow runs `techletter draft` and writes a draft file
- **Given** the workflow steps run on `ubuntu-latest`
- **When** the workflow executes
- **Then** the steps are (in order):
  1. `actions/checkout@v4` (with `fetch-depth: 0` so we can create branches and push)
  2. `astral-sh/setup-uv@v3` (install uv)
  3. `uv sync` (install dependencies)
  4. `uv run techletter draft` — writes `drafts/issue-YYYY-MM-DD.md`
  5. Create branch `draft/issue-YYYY-MM-DD-<run-id>` and commit the draft file
  6. Push the branch
  7. Open a PR via `gh pr create --title "Draft: Tech-Letter Issue YYYY-MM-DD" --body "..."` with the issue's first paragraph as the PR body summary
- **And** the date is computed from `$(date -u +%Y-%m-%d)`

### AC3: Required secrets are documented in workflow
- **Given** the workflow `env:` and `steps[].env:` blocks
- **When** the workflow runs
- **Then** the following secrets are passed to `techletter draft`:
  - `ANTHROPIC_API_KEY` (required)
  - `GITHUB_TOKEN` (provided automatically by Actions; passed to `gh`)
- **And** missing secrets cause an explicit workflow failure with a readable message, not a silent skip

### AC4: Budget breach fails the workflow visibly
- **Given** `techletter draft` exits with code 3 (`BudgetExceededError`)
- **When** the workflow processes the exit code
- **Then** the workflow status is `failure`
- **And** the failure email surfaces the BUDGET_EXCEEDED log line (which the CLI emits to stderr per US0012)
- **And** no PR is opened

### AC5: Source-only-failure scenarios produce a PR with reduced content
- **Given** `techletter draft` exits 0 but with a log line indicating one source (e.g., GitHub trending) failed and was skipped
- **When** the workflow continues
- **Then** the PR is opened normally
- **And** the workflow log retains the per-source failure record (`logs/...` are not yet committed at this point; the workflow log itself is the trace)

### AC6: Queue semantics — additional PR, not skip
- **Given** an unresolved draft PR `draft/issue-2026-05-12-<old-run>` already exists in the repo
- **When** the workflow fires on `2026-05-19`
- **Then** the new run creates branch `draft/issue-2026-05-19-<new-run>` and opens a separate PR
- **And** the old PR is untouched (no force-push, no comment, no merge)

### AC7: Branch naming includes the run id
- **Given** the same Monday could theoretically have two scheduled runs (rare; manual `workflow_dispatch` triggered immediately after a cron run)
- **When** both runs execute
- **Then** branches differ by run id: `draft/issue-2026-05-19-1234567890` vs `draft/issue-2026-05-19-1234567891`
- **And** both produce distinct PRs

---

## Scope

### In Scope
- `.github/workflows/draft.yml`.
- Steps for checkout, uv setup, dependency install, CLI invocation, branch creation, PR open.
- PR body template (markdown — pull from the issue's front matter and first paragraph).
- Documentation comment block at top of the YAML explaining the workflow.

### Out of Scope
- The `send` workflow (US0016).
- A composite action / reusable workflow — the YAML is small enough to inline.
- Slack/Teams notifications on failure — GitHub's default failure email is sufficient for v1.
- Multi-environment deploys (staging/prod) — single environment.
- Self-hosted runners — Ubuntu hosted runner is fine.

---

## Technical Notes

- The PR creation step uses `gh pr create` rather than a third-party action — keeps dependencies in the GitHub ecosystem.
- PR body format: short summary + "see committed file for full draft" link.
- Workflow uses `actions/checkout@v4` with `persist-credentials: true` so subsequent `git push` and `gh pr create` work without manual auth.
- The cron time `0 0 * * 1` is Monday 00:00 UTC, which is Monday 09:00 KST (UTC+9). Document this in a comment in the YAML.

### API Contracts
- Trigger: `schedule.cron = "0 0 * * 1"` or `workflow_dispatch`.
- Output: a new branch `draft/issue-YYYY-MM-DD-<run-id>` and a PR.
- Exit: workflow `success` on PR opened; `failure` on any CLI non-zero exit.

### Data Requirements
- Writes to `drafts/` (new file per run).
- Pushes a new branch.
- Creates a PR.

---

## Edge Cases & Error Handling

| Scenario | Expected Behaviour |
|----------|-------------------|
| `ANTHROPIC_API_KEY` not set | CLI exits 4; workflow fails; clear message |
| `config/sources.yaml` missing | CLI exits 2; workflow fails |
| LLM API down | CLI retries via tenacity; if still failing after retries, exits 4; workflow fails |
| All sources fail (rare) | CLI exits 1; workflow fails |
| Budget exceeded | CLI exits 3; workflow fails; no PR |
| Branch with same name already exists (run id collision — extremely unlikely) | `git push` fails; workflow fails; manually retried |
| `gh pr create` fails (e.g., PR limit) | Workflow fails; branch remains pushed; HYL opens PR manually |
| `actions/checkout` fails | Workflow fails at step 1; no other state changed |
| Cron fires while a previous workflow run of the same name is still in progress | Both run concurrently (default Actions behaviour for cron triggers); each produces its own PR. Acceptable. |
| Workflow run is cancelled mid-execution | Branch may or may not exist; PR may or may not exist; on retry the run id changes, so no collision |
| `uv sync` fails (lockfile corruption or network) | Workflow fails at install step |
| `uv run techletter draft` hangs | Workflow timeout (default 6 hours) catches it; in practice < 5 min per PRD performance target |
| Repo is private and `gh` needs explicit token | `GITHUB_TOKEN` is auto-provided by Actions; `gh` picks it up via the standard env var |
| `gh` not available on `ubuntu-latest` runner | It is, pre-installed; documented assumption |

---

## Test Scenarios

- [ ] Workflow YAML is valid (parse with `actionlint` in pre-merge CI step).
- [ ] Local dry-run of the workflow logic via `act` (or equivalent): cron + workflow_dispatch both invoke the same job.
- [ ] Manual test: trigger `workflow_dispatch` on a feature branch; observe PR creation against a test target branch.
- [ ] Inject a `BudgetExceededError` via prompt manipulation (or env override) → workflow fails with exit 3.
- [ ] Inject missing `ANTHROPIC_API_KEY` → workflow fails with exit 4.
- [ ] Two near-simultaneous `workflow_dispatch` runs → two separate PRs; both contain valid draft content.
- [ ] Cron expression `0 0 * * 1` evaluates to Monday 00:00 UTC (verified in GitHub Actions UI).
- [ ] Permissions block: workflow can `git push` and `gh pr create` without manual PAT.

---

## Dependencies

### Story Dependencies

| Story | Type | What's Needed | Status |
|-------|------|---------------|--------|
| [US0012](US0012-techletter-cli-scaffolding.md) | Service | `techletter draft` CLI command | Draft |

### External Dependencies

| Dependency | Type | Status |
|------------|------|--------|
| GitHub Actions runners (`ubuntu-latest`) | Infrastructure | Provided by GitHub |
| `gh` CLI on runner | Tool | Pre-installed |
| `actions/checkout@v4`, `astral-sh/setup-uv@v3` | Marketplace Actions | Public, version-pinned |
| `ANTHROPIC_API_KEY` GitHub Secret | Secret | Must be configured before first run |

---

## Estimation

**Story Points:** 3
**Complexity:** Low-Medium. YAML is short. Critical-path concerns: cron correctness (one wrong character and it never fires), permissions block correctness, and exit-code propagation. Worth a manual smoke test on a feature branch before letting it run on `main`.

---

## Open Questions

_None._

---

## Revision History

| Date | Author | Change |
|------|--------|--------|
| 2026-05-19 | HYL | Initial story created from EP0003. |
