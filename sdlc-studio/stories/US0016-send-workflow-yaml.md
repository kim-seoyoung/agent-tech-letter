# US0016: `.github/workflows/send.yml` — on PR merge, fan out, commit log

> **Status:** Done
> **Epic:** [EP0003: Orchestration & Developer Experience](../epics/EP0003-orchestration-and-dx.md)
> **Owner:** HYL
> **Reviewer:** HYL
> **Created:** 2026-05-19

## User Story

**As** HYL (Author/Editor)
**I want** a `send.yml` GitHub Actions workflow that fires only on PR merge to `main`, dispatches the merged draft to all enabled channels, and commits the audit log back to `main`
**So that** merging a draft PR is the single, irreversible action that ships an issue to subscribers — with a permanent record of what went out.

## Context

### Persona Reference
**HYL (Author/Editor)** — explicit red flag: "Anything that auto-sends without a human merge." This workflow is the implementation of HYL's approval gate. Getting the trigger predicate wrong (e.g., firing on close-without-merge) would violate the persona's primary trust requirement.
[Persona details](../personas/stakeholders/users/hyl-author.md)

### Background
The send workflow is the most safety-critical YAML in the project. Three things matter: (1) it only fires on actual merges, not closes; (2) it respects idempotency (US0013) so retriggering can't double-send; (3) it commits the audit log back to `main` so the next run knows what's been sent.

---

## Inherited Constraints

| Source | Type | Constraint | AC Implication |
|--------|------|------------|----------------|
| Epic | Trigger | Only on PR merge to `main` | `if: github.event.pull_request.merged == true` |
| Epic | Idempotency | Re-run on same (issue, channel) is a no-op | Calls `already_sent` from US0013 via the CLI |
| Epic | Log | `logs/sends.jsonl` committed to `main` after send | Workflow commits + pushes after CLI exits |
| Epic | Concurrency | Two send workflows must not race writes to `logs/sends.jsonl` | `concurrency` block serialises send workflows on a shared key |
| PRD | Failure isolation | Per-recipient failure doesn't abort the run | `techletter send` exits 0 on partial; workflow doesn't fail |
| PRD | Branch protection | Merging is restricted to trusted committers (configured via repo settings) | Workflow trusts that any merge to `main` is legitimate |

---

## Acceptance Criteria

### AC1: Workflow file exists with correct trigger
- **Given** `.github/workflows/send.yml` exists
- **When** GitHub Actions parses it
- **Then** the trigger is `pull_request` with `types: [closed]` and `branches: [main]`
- **And** the first job-level condition is `if: github.event.pull_request.merged == true`
- **And** the `permissions:` block grants `contents: write` (for log commit) — but NOT `pull-requests: write` (we don't need to mutate PRs from here)

### AC2: Closed-without-merge is a no-op
- **Given** a PR is closed without being merged
- **When** the workflow fires
- **Then** the job is skipped (the `if:` condition is false)
- **And** no steps run; no logs touched; no sends made

### AC3: Workflow extracts issue id from merged branch
- **Given** the merged PR was from branch `draft/issue-2026-05-19-<run-id>`
- **When** the workflow runs
- **Then** the issue id `2026-05-19` is parsed from the branch name (via shell pattern or `gh` API)
- **And** the parsed id is passed to `techletter send --issue 2026-05-19`

### AC4: Workflow runs send and commits the log
- **Given** the steps run on `ubuntu-latest`
- **When** the workflow executes after a valid merge
- **Then** the steps are (in order):
  1. `actions/checkout@v4` (against `main`, fetch-depth 0)
  2. `astral-sh/setup-uv@v3`
  3. `uv sync`
  4. Parse `issue_id` from `github.event.pull_request.head.ref`
  5. `uv run techletter send --issue $ISSUE_ID`
  6. If `logs/sends.jsonl` was modified: `git add logs/sends.jsonl && git commit -m "audit: send for issue $ISSUE_ID" && git push`
  7. Exit reflects the CLI exit code (0 for ok/partial, 5 for any failed channel)

### AC5: Concurrency group serialises sends
- **Given** the workflow's `concurrency` block
- **When** two merges land on `main` in quick succession (rare but possible)
- **Then** the workflow uses `concurrency.group: send-workflow` and `cancel-in-progress: false`
- **And** the second send waits for the first to complete before running
- **And** this prevents `logs/sends.jsonl` write races

### AC6: Required secrets are documented
- **Given** the workflow `env:` and `steps[].env:` blocks
- **When** the workflow runs
- **Then** the following secrets are passed:
  - `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS`, `SMTP_FROM` (for email)
  - `SLACK_WEBHOOK_URLS` (for Slack)
  - `TELEGRAM_BOT_TOKEN` (for Telegram)
  - `GITHUB_TOKEN` (auto-provided, used for commit-and-push)
- **And** missing secrets for a specific channel cause that channel's adapter to log and fail (not abort the run); other channels still attempt

### AC7: Idempotency from upstream is respected
- **Given** a (issue, channel) pair already has `status="ok"` or `status="partial"` in `logs/sends.jsonl`
- **When** `techletter send` is invoked for that pair (e.g., the workflow accidentally fires twice)
- **Then** the CLI sees the existing record via `already_sent()` (US0013), skips the channel, exits 0
- **And** no duplicate send occurs

### AC8: Workflow failure is loud
- **Given** the CLI exits non-zero (e.g., code 5 from a fully-failed channel)
- **When** the workflow reports its status
- **Then** the workflow status is `failure`
- **And** the failure email surfaces the CLI's log output

---

## Scope

### In Scope
- `.github/workflows/send.yml`.
- Trigger configuration (`pull_request.closed` + merged predicate).
- Issue-id extraction from branch name.
- CLI invocation + log commit-push step.
- Concurrency group declaration.
- Documentation comment block at top.

### Out of Scope
- The `draft.yml` workflow (US0015).
- Per-recipient retry orchestration — adapter handles retries; partial failures recorded; manual intervention for retries is a future CR.
- Automatic PR-comment on send result — could be a future enhancement (nice-to-have).
- Notifying subscribers via a different channel about a send failure — out of scope.

---

## Technical Notes

- The `if:` predicate is on the job, not on a step. This way, the entire job is skipped on non-merge close (saves runner minutes).
- Issue id extraction: shell pattern `${REF##draft/issue-}` then `${RESULT%%-*-*}` or similar to drop the `-<run-id>` suffix. Document with a comment.
- The log-commit step uses `git -c user.email=actions@github.com -c user.name="Tech-Letter Bot" commit ...` so commits are attributable.
- The push uses the same `GITHUB_TOKEN` that Actions provides; works for the same repo.

### API Contracts
- Trigger: `pull_request.closed` with `merged == true`.
- Side effects: outbound sends to channels; one commit + push to `main` per send.
- Exit: workflow `success` on CLI exit 0; `failure` on non-zero.

### Data Requirements
- Reads merged draft markdown from `drafts/issue-YYYY-MM-DD.md` (already on `main` after merge).
- Reads `logs/sends.jsonl` for idempotency check.
- Appends to `logs/sends.jsonl` and pushes back.

---

## Edge Cases & Error Handling

| Scenario | Expected Behaviour |
|----------|-------------------|
| PR closed without merge | Job skipped; no side effects |
| PR merged from `main` to `main` (theoretically impossible, but) | Job runs; CLI tries to send; if the merge was a legit re-merge of an old draft, idempotency catches it; otherwise CLI logs "draft not found" exit 2 |
| Branch name doesn't match `draft/issue-*-*` pattern | Issue-id extraction fails; workflow fails at parse step with clear log |
| Two merges land within seconds | Concurrency group queues the second; first completes (commit + push); second runs against the updated `main` |
| Concurrency group conflict with a stuck previous run | `cancel-in-progress: false` means the new run waits indefinitely (up to 6h default); HYL can cancel manually if it stays stuck |
| `git push` of audit log fails (e.g., main moved during workflow) | `git pull --rebase` is attempted once; if still fails, workflow fails. The send has already happened to subscribers; the log loss is bad but recoverable manually |
| One channel adapter completely missing creds (e.g., `TELEGRAM_BOT_TOKEN` unset) | That adapter raises at construction; orchestrator catches; channel reported as `failed`; other channels proceed |
| All channels fully fail | CLI exits 5; workflow fails; failure email surfaces |
| Channel returns `partial` | CLI exits 0; workflow succeeds; log records the partial state; HYL sees it on next audit |
| Merge happens, but draft file doesn't exist on `main` (e.g., merged a different file path) | CLI exits 2; workflow fails; HYL re-merges or creates draft manually |
| Workflow timeout (>6h, default) | Hung run cancelled; partial state in log if some channels ran; recovery via manual `techletter send` |
| `actions/checkout` checks out the merge commit but `logs/sends.jsonl` was updated by a concurrent (rejected by concurrency group, so shouldn't happen) | N/A — concurrency group prevents this |
| Bot user lacks permission to push to `main` (e.g., branch protection disallows direct push) | Failure; HYL configures branch protection to allow `GITHUB_TOKEN` for this specific commit pattern, or relaxes protection for `logs/*` path |

---

## Test Scenarios

- [ ] YAML lints clean via `actionlint`.
- [ ] Local: simulate merge event via `act` (or equivalent); verify the job runs and `if:` predicate is true.
- [ ] Local: simulate close-without-merge; verify job is skipped.
- [ ] Manual end-to-end: open a test PR, merge it, observe send to a test channel + log commit.
- [ ] Idempotency: re-trigger workflow on an already-merged PR (via `workflow_dispatch` if added); verify CLI logs "already sent" for each channel.
- [ ] Concurrency: trigger two manual runs simultaneously; verify second waits for first.
- [ ] Branch name parsing: verify edge cases (`draft/issue-2026-05-19-1234567890`, with and without timestamps).
- [ ] Missing `SMTP_PASS`: email adapter logs failure; other channels still send; workflow does not abort the run (`partial`-flavour failure across channels).
- [ ] All channels fail: workflow exits with `failure`.

---

## Dependencies

### Story Dependencies

| Story | Type | What's Needed | Status |
|-------|------|---------------|--------|
| [US0012](US0012-techletter-cli-scaffolding.md) | Service | `techletter send` CLI command | Draft |
| [US0013](US0013-sends-jsonl-and-idempotency.md) | Service | Idempotency check + log append (called from CLI) | Draft |
| EP0004 (delivery) | Service | Channel adapters | Not started |

### External Dependencies

| Dependency | Type | Status |
|------------|------|--------|
| GitHub Actions runners | Infrastructure | Provided |
| Channel secrets (SMTP, Slack, Telegram) | Secrets | Must be configured |
| Branch protection on `main` configured | Repo settings | Must be configured for safety |

---

## Estimation

**Story Points:** 5
**Complexity:** Medium-High. The trigger predicate, concurrency group, and commit-push pattern are each independent gotchas that need careful reading of GitHub Actions docs. The "merge-only" guarantee is critical. Worth a manual smoke test on a fork before enabling on the real repo.

---

## Open Questions

_None._

---

## Revision History

| Date | Author | Change |
|------|--------|--------|
| 2026-05-19 | HYL | Initial story created from EP0003. |
