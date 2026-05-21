# CR-0002: GitHub Pages Publisher + Telegram Link Mode

> **Status:** Complete -- EP0006 (Done)
> **Priority:** P2
> **Type:** feature-request
> **Requester:** HYL
> **Date:** 2026-05-21
> **Affects:** F-07 Telegram delivery; introduces a new "web archive" capability not currently in F-features
> **Depends on:** CR-0001

## Summary

Introduce a `Publisher` abstraction that emits the `html_web` rendering (from CR-0001) to a public GitHub Pages site, and rewire the Telegram adapter to send a short teaser plus the resulting URL instead of inlining the full issue body. Each weekly issue becomes a permanent page at `https://<user>.github.io/<repo>/issues/<date>-<sha16>.html`; the Telegram message is one screen of summary plus a tappable link with a rich web preview card. The page is public-by-URL (the repo is public on GitHub Free; access control is intentionally out of scope for this CR).

## Problem

Telegram's 4096-char-per-message limit forces the current adapter to split long issues into 2–4 chunks with ugly `[Part 1/3]` prefixes (`techletter/delivery/telegram.py:139-149`), breaking reading flow. There's also no permanent address for an issue — once a Telegram message scrolls past, it's gone, and there's no archive a subscriber can come back to. Publishing each issue as a styled web page solves both problems and creates a low-cost subscriber experience: one tap, full read in browser, shareable URL. GitHub Pages reuses the repo we already operate, costs nothing on GitHub Free with a public repo, and lets us version-control the archive.

---

## Proposed Changes

### Item 1: `Publisher` Protocol + `PublishResult` model

**Priority:** P2
**Effort:** XS (2 pts)

Define `techletter/delivery/publishers/base.py` with `Publisher` Protocol (`name: str`, `publish(issue: RenderedIssue) -> PublishResult`) and a frozen `PublishResult` pydantic model (`url`, `path`, `published_at`, `commit_sha`). Same shape regardless of backend, so a future swap to Cloudflare R2 / Vercel / Telegraph is a localized change.

### Item 2: `GitHubPagesPublisher` (worktree + git push)

**Priority:** P2
**Effort:** M (5 pts)

`techletter/delivery/publishers/github_pages.py` writes `issues/<YYYY-MM-DD>-<sha16>.html` to a `gh-pages` worktree (under `.git/worktrees/gh-pages-publish/`), commits with a deterministic message `publish: <issue_id> <sha8>`, and pushes to `origin/gh-pages`. Idempotent on identical bytes: `git diff --quiet` → no new commit. Seeds `.nojekyll` + `robots.txt` (`User-agent: *` / `Disallow: /`) on first publish. Uses `git` CLI via subprocess (no GitPython dep). Token/SSH key paths never appear in logs.

### Item 3: `telegram_teaser` renderer

**Priority:** P2
**Effort:** XS (2 pts)

`techletter/delivery/renderers/telegram_teaser.py` is a pure function: `RenderedIssue + url → str`. Format: issue title line, summary count line, up to N deep-dive titles, "전문 보기 ▶ <url>". Output always ≤ 4096 chars (single message). HTML-escapes title and URL. Property-tested for length invariant.

### Item 4: Telegram adapter `mode` + publisher wiring

**Priority:** P2
**Effort:** M (3 pts)

`TelegramAdapter.__init__` accepts `mode: Literal["teaser_link", "inline_html"] = "teaser_link"` and `publisher: Publisher | None`. In `teaser_link` mode, `send()` calls `publisher.publish(issue)` exactly once (cached across recipients) before sending; on publish failure → `SendReport.status="failed"` with publisher error in `errors`, no Bot API call. `inline_html` preserves today's behavior bit-for-bit (regression test pins it). `channels.yaml` schema gains a top-level `publishers:` block + per-channel `mode` / `publisher:` reference, pydantic-validated.

### Item 5: `SendRecord.published_url` + README + E2E smoke

**Priority:** P2
**Effort:** S (2 pts)

`techletter/audit.py` `SendRecord` schema gains optional `published_url`. README documents one-time GitHub Pages setup (orphan branch seeding, `Settings → Pages → gh-pages branch / root`, env vars). End-to-end smoke run owned by HYL: real `draft` → real PR merge → real `send` → real Telegram message arrives with link preview card; tap link → styled web page renders.

---

## Impact Assessment

### Existing Functionality

- **Telegram delivery (F-07):** default behavior changes from inlined-multi-message to teaser+link. `inline_html` legacy mode preserved (regression-tested) so we can fall back if real-world issues surface.
- **Email delivery (F-05):** untouched (uses `html_email` directly, never via publisher).
- **Slack delivery (F-06):** untouched.
- **Idempotency (EP0003):** Publisher must also be idempotent. Same `content_sha256` → same URL → same file on `gh-pages` → no new commit. `SendRecord` keying unchanged; `published_url` is auxiliary.

### Affected Modules

| Module | Impact | Change Type |
| --- | --- | --- |
| `techletter/delivery/publishers/` | New module: `base.py`, `github_pages.py` | New |
| `techletter/delivery/renderers/telegram_teaser.py` | New | New |
| `techletter/delivery/telegram.py` | `mode` dispatch, publisher hook | Modified |
| `techletter/delivery/config.py` | `publishers:` block parsing | Modified |
| `techletter/delivery/registry.py` | Resolve `publisher: github_pages` reference | Modified |
| `techletter/audit.py` | `SendRecord.published_url` optional field | Modified |
| `config/channels.yaml` | Schema extension example | Modified |
| `README.md` | One-time GH Pages setup section | Modified |
| `tests/` | New: publisher unit + integration, teaser property tests, telegram mode dispatch | New |

### Breaking Changes

- **Telegram subscribers see a different message format.** This is the goal, but worth flagging in the first issue.
- New env vars (`GITHUB_REPO`, optionally PAT) required for publish. Documented in README. CI workflow `send.yml` needs the secret added.
- `gh-pages` orphan branch must exist before first publish. One-time manual seeding required (documented).

---

## Acceptance Criteria

- [ ] `Publisher` Protocol defined; `PublishResult` is a frozen pydantic model with `url`, `path`, `published_at`, `commit_sha`.
- [ ] `GitHubPagesPublisher.publish(issue)` writes file to gh-pages worktree, commits, pushes. Returns valid `PublishResult`.
- [ ] Same `issue.content_sha256` → same URL across runs; no duplicate commit when bytes match (`git diff --quiet`).
- [ ] `.nojekyll` and `robots.txt` (`Disallow: /`) seeded on first publish; idempotent thereafter.
- [ ] HTML page contains `<meta name="robots" content="noindex, nofollow">` (inherited from CR-0001).
- [ ] `telegram_teaser.render(issue, url)` always returns a string ≤ 4096 chars; URL appears verbatim; title escapes `< > &`.
- [ ] `TelegramAdapter` `teaser_link` mode calls publisher exactly once per `send` even with N recipients. On publish failure, `SendReport.status="failed"` and no Bot API calls are made.
- [ ] `inline_html` legacy mode is bit-for-bit equivalent to today's behavior (regression test).
- [ ] `channels.yaml` `publishers:` block parses via pydantic; missing publisher reference fails fast with a clear error.
- [ ] `SendRecord` JSONL line for a teaser-mode send includes `published_url`.
- [ ] Neither `TELEGRAM_BOT_TOKEN` nor any GitHub credential appears in any log record across the full retry path (extends TC0247-style assertion).
- [ ] README documents one-time GitHub Pages setup.
- [ ] HYL has run the full E2E smoke at least once: published page renders in browser; Telegram link preview card visible.

---

## Risks

| Risk | Likelihood | Impact | Mitigation |
| --- | --- | --- | --- |
| `git push origin gh-pages` fails (auth, network, branch protection) | M | M | Publisher errors short-circuit `send` cleanly → `SendReport.status=failed`; idempotent so retry is safe |
| GitHub Pages CDN delay → subscriber taps link before page is live (404) | L | L | Optional configurable post-publish sleep; subsequent re-tap resolves |
| Search engines index pages despite `noindex` + `robots.txt` | L | M | URL slug includes 16 hex chars of `content_sha256` (not enumerable); no index page → no internal links to crawl |
| Subscriber forwards URL publicly | M | M | Acceptable for this CR; auth gate is a future CR if it becomes a problem |
| `gh-pages` worktree state corrupts between runs (manual edits) | L | M | Publisher refuses dirty worktree with clear message; HYL cleans manually |
| Telegram preview card stale after content edit | L | L | Different content → different `content_sha256` → different URL → fresh preview |

---

## Dependencies

### CR Dependencies

| CR | Title | Status | Required Before |
| --- | --- | --- | --- |
| [CR-0001](CR0001-common-html-rendering.md) | Common HTML Rendering (Web + Email) | Proposed | Implementation start (needs `html_web` renderer + sidecar JSON) |

### External Dependencies

| Dependency | Type | Status |
| --- | --- | --- |
| GitHub Pages enabled on the repo (`Settings → Pages → gh-pages branch`) | one-time setup | manual, documented |
| `gh-pages` orphan branch exists on `origin` | one-time setup | manual, documented |
| Push credentials available (`GITHUB_TOKEN` in CI, SSH key locally) | runtime | env-supplied |
| `git` CLI available at runtime | runtime | assumed (CI image + local) |

---

## Linked Epics

| Epic | Title | Status |
| --- | --- | --- |
| [EP0006](../epics/EP0006-github-pages-and-telegram-link-mode.md) | GitHub Pages Publisher + Telegram Link Mode | Done |

**Linked Stories:** US0028 (Publisher Protocol), US0029 (GitHubPagesPublisher), US0030 (telegram_teaser), US0031 (Telegram mode + wiring), US0032 (SendRecord + README + E2E).

---

## Out of Scope

- Authentication / access gate on the public pages (Cloudflare Access, Vercel password protection). Future CR if needed.
- Site-wide index, RSS feed, sitemap. Discoverability is by Telegram/email link only.
- Slack Block Kit upgrade (separate CR).
- Image hosting (cover art, social cards).
- Telegraph, Substack, or other third-party publishers — Protocol leaves room, only `GitHubPagesPublisher` ships in this CR.
- Custom domain. `<user>.github.io/<repo>` is fine.
- Edit-a-published-issue UI. Different content → different hash → new URL; old URL still serves the old version.

---

## Open Questions

- [ ] `git` subprocess vs `GitPython`? Lean subprocess for no-new-dep + easier secret scrubbing in logs. — Owner: HYL
- [ ] Default sleep between publish and Telegram send? Start at 0; measure CDN latency in first smoke; bump to 30–60s if 404s observed. — Owner: HYL
- [ ] `gh-pages` worktree path under `.git/worktrees/` (invisible) vs top-level `dist/` (visible)? Lean invisible. — Owner: HYL
- [ ] Should we add an explicit "what gets published is public" warning to `uv run techletter send` first-run output? — Owner: HYL

---

## Close Reason

**Outcome:** Complete
**Rationale:** EP0006 reached Done on 2026-05-21. All 5 stories (US0028–US0032) implemented and tested (49 new tests, all green). `Publisher` Protocol + `PublisherError` shipped, `GitHubPagesPublisher` with idempotent push + secret scrubbing landed, `telegram_teaser` renderer with property-tested length invariant added, `TelegramAdapter` gained `teaser_link` mode (default for new installs) while preserving `inline_html` legacy path bit-equivalent. `SendRecord.published_url` flows from publisher → adapter → audit log. README updated with one-time `gh-pages` setup. AC9 manual cross-client E2E smoke (US0032) remains HYL-owned (needs real `TELEGRAM_BOT_TOKEN` + `gh-pages` branch + subscriber `chat_id`).

---

## Revision History

| Date | Author | Change |
| --- | --- | --- |
| 2026-05-21 | HYL | CR proposed. Depends on CR-0001. Draft epic content preserved at `sdlc-studio/.local/draft-epic-content/EP0006-github-pages-and-telegram-link-mode.md` for reference when `cr action` generates the formal epic. |
| 2026-05-21 | HYL | CR actioned via `/sdlc-studio cr action --cr CR-0002` — 1 epic (EP0006), 5 stories (US0028–US0032) created. Status: Proposed → In Progress. PRD F-07 description updated with CR reference. |
| 2026-05-21 | Claude (via /sdlc-studio epic implement --epic EP0006) | EP0006 cascaded to Done; all AC verified by tests (modulo HYL-owned manual E2E). CR closed Complete. |
