# US0029: `GitHubPagesPublisher` (worktree + git push)

> **Status:** Done
> **Epic:** [EP0006: GitHub Pages Publisher + Telegram Link Mode](../epics/EP0006-github-pages-and-telegram-link-mode.md)
> **Change Request:** [CR-0002](../change-requests/CR0002-github-pages-and-telegram-link-mode.md) (Item 2)
> **Owner:** HYL
> **Reviewer:** HYL
> **Created:** 2026-05-21

## User Story

**As** the Telegram adapter
**I want** a `Publisher` implementation that writes the rendered HTML page to a `gh-pages` branch and pushes it to `origin`
**So that** each weekly issue lives at a permanent `https://<user>.github.io/<repo>/issues/...` URL that subscribers can tap from the bot message.

## Context

### Persona Reference
**Researcher Subscriber** — indirect. They never interact with git, but every URL they tap was produced by this publisher.
**HYL** — direct. Owns the one-time `gh-pages` orphan branch setup; pays for git auth via `GITHUB_TOKEN` / deploy key.

### Background
EP0006 commits to a single publisher backend for v1.2: GitHub Pages on a public repo. This story does the heavy lifting: drive `git` via subprocess, manage a dedicated worktree, write the file with a deterministic name, commit + push if content changed, return the public URL. Idempotency is critical — re-running `send` for the same issue must NOT produce a new commit (per EP0005 `content_sha256` invariant).

---

## Inherited Constraints

| Source | Type | Constraint | AC Implication |
|--------|------|------------|----------------|
| US0028 | Protocol | Implements `Publisher` (name + publish) | Class is structurally conformant |
| EP0005 | Renderer | Consumes `html_web.render(issue)` verbatim | No template branching inside the publisher |
| EP0006 | Idempotency | Same `content_sha256` → same URL → no new commit | `git diff --quiet` check before commit |
| EP0006 | Security | GitHub token / SSH key path never in logs | Existing TC0247-style scrubber pattern; never log full git URLs |
| EP0006 | Slug | URL contains 16 hex of `content_sha256` (unguessable) | `<YYYY-MM-DD>-<sha16>.html` |
| EP0006 | Seeded files | `.nojekyll` + `robots.txt` (`Disallow: /`) seeded once on `gh-pages` root | First publish creates them if missing; subsequent publishes are no-ops |
| EP0006 | Worktree | Uses `git worktree` under `.git/worktrees/gh-pages-publish/` | Main working tree untouched |

---

## Acceptance Criteria

### AC1: Class signature and Protocol conformance
- **Given** `from techletter.delivery.publishers.github_pages import GitHubPagesPublisher`
- **When** instantiated as `GitHubPagesPublisher(repo_path=Path("."), branch="gh-pages", base_url="https://USER.github.io/REPO", author_name="bot", author_email="bot@example.com")`
- **Then** `instance.name == "github_pages"`
- **And** pyright confirms it satisfies `Publisher`

### AC2: First publish: seeds branch infra + writes file + commits + pushes
- **Given** an `origin/gh-pages` orphan branch with no `.nojekyll` / `robots.txt`
- **When** `publish(issue)` is called
- **Then** the worktree contains `.nojekyll` (empty file), `robots.txt` (`User-agent: *\nDisallow: /\n`), and `issues/<YYYY-MM-DD>-<sha16>.html`
- **And** the commit message is `publish: <issue_id> <sha8>`
- **And** the author is `<author_name> <author_email>`
- **And** `git push origin gh-pages` is invoked
- **And** the returned `PublishResult.url` equals `f"{base_url}/issues/{YYYY-MM-DD}-{sha16}.html"`
- **And** `PublishResult.commit_sha` is the new commit SHA (40 hex)

### AC3: Idempotency — same content, no new commit
- **Given** `publish(issue)` succeeded once for some issue X
- **When** `publish(X)` is called again with byte-identical input
- **Then** `git diff --quiet` reports no change
- **And** **no new commit is made** and **no push is performed**
- **And** `PublishResult.url` matches the prior URL exactly
- **And** `PublishResult.commit_sha` is the existing HEAD on `gh-pages` (not a new one)

### AC4: Worktree provisioned on demand
- **Given** the worktree path does not yet exist
- **When** `publish(issue)` is called
- **Then** the publisher creates the worktree via `git worktree add .git/worktrees/gh-pages-publish gh-pages`
- **And** subsequent publishes reuse it without re-adding

### AC5: Dirty worktree → refuse to publish
- **Given** the `gh-pages` worktree contains uncommitted manual edits (e.g., HYL was poking around)
- **When** `publish(issue)` is called
- **Then** the publisher raises a clear `PublisherError` with a message naming the dirty worktree path
- **And** **no commit/push happens**
- **And** the error message does NOT include any token/credential

### AC6: Push failure surfaces with all credential patterns scrubbed (per RV0002 F-4)
- **Given** `git push` fails (e.g., auth error, branch protection rule, network)
- **When** the failure occurs
- **Then** `publish(issue)` raises `PublisherError`
- **And** the exception message AND any captured log records do NOT contain ANY of:
  - The literal value of `os.environ["GITHUB_TOKEN"]` (if set in the runtime env)
  - Any URL of the form `https?://[^@\s]+@github\.com/...` (token-embedded HTTPS push URLs — the user-info part is replaced with `[REDACTED]`)
  - Any string matching `ghs_[A-Za-z0-9]{36,}` or `ghp_[A-Za-z0-9]{36,}` (GitHub installation token / PAT prefixes)
  - The value of `SSH_AUTH_SOCK` or any expanded `~/.ssh/...` path
- **And** the scrub is a single regex-based filter applied to git's stderr before bubbling up — implementation MUST go through this filter, not concatenate stderr into messages by hand
- **And** a separate test asserts each of the four patterns above is scrubbed

### AC7: HTML body equals `html_web.render(issue)` byte-for-byte
- **Given** the file written under `issues/...`
- **When** read back
- **Then** its bytes equal `html_web.render(issue)` exactly (no extra newline, no BOM)

### AC8: `.nojekyll` and `robots.txt` are written only when missing (per RV0002 F-3)
- **Given** these files exist from a prior publish
- **When** `publish(issue)` runs again
- **Then** the publisher does NOT call `Path.write_text` / `Path.write_bytes` on either file (verified by a `monkeypatch`-based spy on the writes)
- **And** their content is left exactly as it was on disk
- **And** they do NOT contribute to the per-publish `git diff --quiet` check (i.e., even if a future change altered `robots.txt` outside the publisher, that change would not be a publish trigger by itself)

---

## Scope

### In Scope
- `techletter/delivery/publishers/github_pages.py` with `GitHubPagesPublisher` and `PublisherError` (or reuses a shared exception class if introduced).
- Internal helpers (private functions, not part of the public API):
  - `_ensure_worktree(repo_path, worktree_path, branch)`
  - `_seed_pages_infra(worktree_path)` (`.nojekyll`, `robots.txt`)
  - `_assert_worktree_clean(worktree_path)`
  - `_git(...)` wrapper that scrubs sensitive args from any raised exception message.
- Unit tests under `tests/unit/delivery/publishers/test_github_pages.py` with `git` subprocess mocked.
- One integration test that runs against a local bare repo (temp dir, `origin` = local file path) to verify the end-to-end behavior with real git.

### Out of Scope
- Telegram adapter integration (US0031).
- `channels.yaml` config schema for `publishers:` (US0031).
- README setup docs (US0032).
- `published_url` in `SendRecord` (US0032).
- Telegraph or any non-GitHub publisher.

---

## Technical Notes

- **`git` via subprocess**: No `GitPython`. Easier to scrub secrets (we know exactly what args we pass) and avoids a dep.
- **Worktree path**: `repo_path / ".git" / "worktrees" / "gh-pages-publish"` — invisible by virtue of `.git/`.
- **Author identity**: Passed in explicitly; never read `~/.gitconfig` (operator runtime might not be the right identity, especially in CI).
- **Diff check**: `git diff --quiet` returns 0 if no diff, 1 if diff. We branch on that exit code (no string parsing).
- **Push**: `git push origin gh-pages` — single command, no force, no upstream tracking changes.
- **CI environment**: `GITHUB_TOKEN` is typically exposed; subprocess `env=os.environ.copy()` is fine. SSH path: assumes `~/.ssh/known_hosts` is populated or `StrictHostKeyChecking=accept-new` is configured by the operator — out of scope for the publisher.
- **Error class**: Define `PublisherError` in `publishers/base.py` (or a sibling) and re-export. Used for both dirty-worktree refusal and push failure.

### API Contracts

```python
class GitHubPagesPublisher:
    name: str = "github_pages"

    def __init__(
        self,
        *,
        repo_path: Path,
        branch: str = "gh-pages",
        base_url: str,
        author_name: str,
        author_email: str,
        worktree_path: Path | None = None,  # defaults to repo_path / .git / worktrees / gh-pages-publish
    ) -> None: ...

    def publish(self, issue: RenderedIssue) -> PublishResult: ...
```

---

## Edge Cases & Error Handling

| Scenario | Expected Behaviour |
|----------|-------------------|
| `gh-pages` branch doesn't exist on `origin` | Raise `PublisherError("gh-pages branch not found; seed with: git switch --orphan gh-pages && ...")` |
| Network error during push | Raise `PublisherError`; the publisher does NOT retry internally — retries happen at the adapter level (US0031 maps to SendReport failure) |
| `repo_path` is not a git repo | Raise `PublisherError` early |
| `worktree_path` exists but is a non-worktree directory | Refuse with clear message |
| `base_url` doesn't end with the repo path | URL is `{base_url}/issues/...` — caller is responsible for the slash boundary; the publisher inserts one |
| `content_sha256` is shorter than 16 chars | Pad with `0` (defensive; should never happen since SHA-256 is always 64 hex) |
| Multiple `publish()` calls in the same process | Worktree is reused; each call performs the full check-write-(maybe-commit)-(maybe-push) cycle |
| Concurrent publishes (two processes writing the same worktree) | Out of scope; if it happens, git's `index.lock` will surface as a `PublisherError` |

---

## Test Scenarios

- [ ] **Happy path (mocked git)**: file written, commit made, push invoked, URL returned.
- [ ] **Idempotency**: second call with same input → no `git commit` invocation, no `git push` invocation, same URL/commit_sha returned.
- [ ] **First publish seeds `.nojekyll` + `robots.txt`**.
- [ ] **Second publish does NOT modify the seed files**.
- [ ] **Worktree provisioned on first call when missing**.
- [ ] **Dirty worktree raises `PublisherError`**; no commit/push.
- [ ] **Push failure raises `PublisherError`**; error message does NOT contain `GITHUB_TOKEN` from env.
- [ ] **Issue with `body_md` containing `<script>...`** → HTML on disk equals `html_web.render(issue)` and has the script escaped (inherited from EP0005).
- [ ] **`PublishResult.path` is the relative path under the worktree** (e.g., `issues/2026-05-21-abc...html`).
- [ ] **Integration (real bare repo as origin)**: temp dir contains both a "source" repo and a `--bare` "origin"; publisher pushes; assert the new commit exists on the bare repo's `gh-pages`.

---

## Dependencies

### Story Dependencies

| Story | Type | What's Needed | Status |
|-------|------|---------------|--------|
| [US0028](US0028-publisher-protocol-and-publish-result.md) | Schema | `Publisher` Protocol + `PublishResult` model | Draft |
| [US0023](US0023-sidecar-json-persistence.md) | Pipeline | `RenderedIssue.deep_dives`/`.quick_mentions` populated when adapter receives the issue | Done |
| [US0025](US0025-html-web-renderer-and-golden-fixture.md) | Renderer | `html_web.render(issue)` | Done |

### External Dependencies

| Dependency | Type | Status |
|------------|------|--------|
| `git` CLI | Runtime tool | assumed present (Mac dev / GitHub Actions runners both have it) |
| `gh-pages` orphan branch on origin | One-time setup | manual (documented in US0032) |
| Push credentials (`GITHUB_TOKEN` or SSH key) | Runtime secret | env-supplied; never logged |

---

## Estimation

**Story Points:** 5
**Complexity:** Medium. The git plumbing is mechanical, but the test infrastructure (mocked git for unit + real bare repo for integration) is real work, and the edge cases (dirty worktree, missing branch, push fail) each need a deliberate test.

---

## Open Questions

- [ ] Should the worktree be cleaned up after each publish (`git worktree remove`)? Lean **no** — provisioning has measurable cost; persistent worktree is fine since it's under `.git/`. Decide during implementation if it surfaces issues.

---

## Revision History

| Date | Author | Change |
|------|--------|--------|
| 2026-05-21 | HYL | Story created from CR-0002 (Item 2) via `/sdlc-studio cr action`. |
