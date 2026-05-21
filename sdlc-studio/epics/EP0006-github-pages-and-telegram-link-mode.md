# EP0006: GitHub Pages Publisher + Telegram Link Mode

> **Status:** Done
> **Owner:** HYL
> **Reviewer:** HYL
> **Created:** 2026-05-21
> **Target Release:** v1.2 (Telegram becomes a teaser channel; web archive lives at github.io)
> **Change Request:** [CR-0002: GitHub Pages Publisher + Telegram Link Mode](../change-requests/CR0002-github-pages-and-telegram-link-mode.md)

## Summary

Introduce a `Publisher` abstraction that emits the `html_web` rendering (from EP0005) to a public GitHub Pages site, and rewire the Telegram adapter to send a short teaser plus the resulting URL instead of inlining the full issue body. Each weekly issue becomes a permanent page at `https://<user>.github.io/<repo>/issues/<date>-<sha16>.html`; the Telegram message is one screen of summary plus a tappable link with a rich web-page preview. The page is *public by URL* (the repo is public on GitHub Free; access control is intentionally out of scope for v1.2). Slack continues on its existing path. Email is unaffected.

## Inherited Constraints

| Source | Type | Constraint | Impact |
|--------|------|------------|--------|
| EP0005 | Renderer | `html_web.render(issue) -> str` is the single source of truth for the published page | Publisher consumes its output verbatim — no per-publisher template forking |
| EP0005 | Sidecar JSON | `send` reconstructs `RenderedIssue.deep_dives` / `quick_mentions` from sidecar | Publisher relies on these; no `body_md`-only fallback |
| EP0003 | Idempotency | `SendRecord` keyed by `(issue_id, channel)`; same issue → no duplicate send | Publisher must also be idempotent (same `content_sha256` → same URL, no duplicate commit) |
| EP0004 | ChannelAdapter | `send(issue, recipients) -> SendReport` unchanged | Telegram adapter's external contract preserved; internal modes added |
| EP0004 | Telegram | Bot token never appears in logs (TC0247) | Continues to hold; new code paths inherit the same scrubber |
| TRD | Secrets | All credentials via env / GitHub Actions Secrets | Publisher needs `GITHUB_TOKEN` (or deploy key) — sourced from secrets, never committed |
| TRD | Tooling | `uv` for deps; `git` CLI available at runtime | Publisher shells to `git` via subprocess (no extra service dependencies, easier secret scrubbing) |
| CR-0002 | Access | Free plan + public repo accepted; no auth gate on pages | Pages are world-readable; rely on `noindex,nofollow` + unguessable URL slug (16-hex `content_sha256` prefix) |

---

## Business Context

### Problem Statement
Telegram's 4096-char-per-message limit forces the current adapter to split long issues into 2–4 chunks, breaking flow and producing ugly part numbering (`techletter/delivery/telegram.py:139-149`). There's also no permanent address for an issue — once a Telegram message scrolls past, it's gone, and there's no archive a subscriber can come back to. Publishing each issue as a styled web page solves both problems and creates a low-cost subscriber experience: one tap, full read in browser, shareable URL. GitHub Pages reuses the repo we already operate, costs nothing on GitHub Free with a public repo, and lets us version-control the archive.

**PRD Reference:** [§3 F-07 Telegram delivery](../prd.md#3-feature-inventory) — current implementation degrades on long issues; this epic resolves that and adds an archive.

### Value Proposition
One renderer (EP0005), two output venues: subscriber inboxes get the email; the web (and Telegram readers) get the same content as a permanent linkable page. Telegram messages become one-screen teasers — readers see the headline in chat, tap once for the full read. No more split-message pagination, no more lost archive.

### Success Metrics

| Metric | Current | Target | Measurement |
|--------|---------|--------|-------------|
| Telegram messages per issue | 2–4 (split) | 1 | Inspect `send` log for chunk count |
| Permanent URL for each issue | 0 | 100% | Each `SendRecord` carries `published_url`; URL resolves with 200 |
| Telegram link preview shows page card | n/a | yes | Manual: open Telegram, verify preview card |
| Re-running `send` for the same `content_sha256` | duplicates a commit | 0 new commits | Git log on `gh-pages` branch |
| End-to-end latency (draft merged → page live → Telegram sent) | n/a | ≤ 3 min | Wall-clock from PR merge to bot message |

---

## Scope

### In Scope
- **`Publisher` Protocol** (`techletter/delivery/publishers/base.py`): `name`, `publish(issue) -> PublishResult`. Same Protocol shape regardless of backend.
- **`PublishResult`** model: `url`, `path`, `published_at`, `commit_sha` (when applicable). Frozen pydantic.
- **`GitHubPagesPublisher`**: writes `issues/<YYYY-MM-DD>-<sha16>.html` to a `gh-pages` worktree, commits with a deterministic message, pushes. Uses an unguessable URL slug (16-hex `content_sha256` prefix).
- **`.nojekyll`** seeded in the `gh-pages` root once; `robots.txt` set to `Disallow: /`.
- **No index page** on `gh-pages` — discoverability comes from Telegram/email, not from the site itself.
- **`telegram_teaser` renderer** (`techletter/delivery/renderers/telegram_teaser.py`): `RenderedIssue` + `url` → HTML string ≤ 4096 chars, single message.
- **Telegram adapter `mode` parameter**: `"teaser_link"` (default, new) | `"inline_html"` (legacy). `teaser_link` calls the configured `Publisher` first, then sends the teaser. `inline_html` keeps today's behavior as a safety net.
- **`channels.yaml` schema extension**: `publishers:` block; per-channel `mode` and `publisher:` reference; pydantic-validated.
- **Idempotent publish**: same `content_sha256` always produces the same URL; bit-equal files → no new commit.
- **`SendRecord` enrichment**: include `published_url` when the channel used a publisher.

### Out of Scope
- Authentication gate on the public pages (Cloudflare Access, Vercel Password Protection). Future CR if subscriber list goes private.
- A site-wide index, RSS feed, or sitemap. Not for v1.2; tracked as a follow-up.
- Slack Block Kit upgrade — separate work; Slack remains on its current splitter path.
- Image hosting (cover art, social cards). Text-only pages.
- Telegraph or other third-party publishers — `Publisher` Protocol leaves room, but only GitHub Pages ships in v1.2.
- Custom domain / DNS configuration. `<user>.github.io/<repo>` is fine for v1.2.
- "Edit a published issue" UI. Re-running `draft` with a different `body_md` produces a new `content_sha256` and therefore a new URL.

### Affected Personas
- **Researcher Subscriber:** primary — receives a short Telegram message they can read in 5 seconds and decides whether to tap through.
- **HYL:** secondary — gains a public archive at zero infra cost; new failure mode (git push failure) lands in `SendReport.status=failed` instead of a silent miss.

---

## Acceptance Criteria (Epic Level)

- [ ] `Publisher` Protocol defined with `name: str` and `publish(issue: RenderedIssue) -> PublishResult`. `PublishResult` is a frozen pydantic model.
- [ ] `GitHubPagesPublisher.publish(issue)` writes `issues/<YYYY-MM-DD>-<sha16>.html` to a `gh-pages` worktree, commits with message `publish: <issue_id> <sha8>`, and pushes to `origin/gh-pages`. Returns `PublishResult(url, path, published_at, commit_sha)`.
- [ ] Same `issue.content_sha256` → same URL across runs. If file is already present with identical bytes, **no new commit is created**.
- [ ] `.nojekyll` and `robots.txt` (`User-agent: *` / `Disallow: /`) are seeded on `gh-pages` root on first publish; idempotent thereafter.
- [ ] HTML page contains `<meta name="robots" content="noindex, nofollow">` (inherited from EP0005's `html_web`).
- [ ] `telegram_teaser.render(issue, url)` returns an HTML string ≤ 4096 chars containing: issue title, summary count line, up to N deep-dive titles, and the URL.
- [ ] `TelegramAdapter` accepts `mode` (`teaser_link` | `inline_html`, default `teaser_link`) and `publisher: Publisher | None`. In `teaser_link` mode, `send()` calls `publisher.publish(issue)` once (cached across recipients) before sending; on publish failure → `SendReport.status="failed"` and no Bot API calls.
- [ ] `inline_html` mode is **bit-for-bit equivalent** to today's behavior (regression-pinned).
- [ ] `channels.yaml` `publishers:` block parses: `name`, `enabled`, `repo_path`, `branch`, `base_url`, `author_name`, `author_email`. Telegram `publisher: github_pages` resolves to the configured instance via the registry.
- [ ] `SendRecord` JSONL line for a teaser-mode send includes `published_url`.
- [ ] Bot token, GitHub PAT, and SSH private key paths never appear in any log output (TC0247-style assertion extended to the new code paths).
- [ ] `README.md` documents: one-time GitHub Pages setup (`Settings → Pages → gh-pages branch`), how to seed `gh-pages` orphan branch, env vars (`GITHUB_REPO`, etc.).
- [ ] End-to-end smoke: HYL runs `uv run techletter draft` → merges PR → `uv run techletter send` → Telegram bot receives one message with a link → link opens a styled web page in browser.

---

## Dependencies

### Blocked By

| Dependency | Type | Status | Owner |
|------------|------|--------|-------|
| EP0005 Common HTML Rendering | Epic | Done | HYL |

(EP0005 shipped on 2026-05-21; `html_web.render` and sidecar JSON are available.)

### Blocking

| Item | Type | Impact |
|------|------|--------|
| (none known) | — | Future CR for site index / RSS would extend this, but is not on the roadmap |

---

## Risks & Assumptions

### Assumptions
- HYL is on GitHub Free with a public repo. Pages are world-readable; we accept that.
- The bot's `GITHUB_TOKEN` (or a deploy key) has `contents:write` on the repo and can push to `gh-pages`.
- The `gh-pages` branch exists as an orphan branch; seeded once manually (documented).
- GitHub Pages CDN propagation is fast enough that the Telegram message's link is live by the time a subscriber taps it (typical: 30–90s).
- The `git` CLI is available in any environment that runs `send` (local + GitHub Actions).

### Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| `git push origin gh-pages` fails (auth, network, branch protection) → entire Telegram send marked failed | M | M | Publisher errors short-circuit `send` cleanly and produce `SendReport.status=failed` with a clear error; idempotency makes retry safe |
| GitHub Pages caching delay → subscriber taps link before page is live (404) | L | L | Optional 60s post-publish sleep configurable in `channels.yaml`; subsequent retry from subscriber resolves naturally |
| Search engines index pages despite `noindex` + `robots.txt` (some crawlers ignore both) | L | M | URL slug includes 16 hex chars of content hash → not enumerable from a directory; no index page means no internal links to crawl |
| Subscriber forwards URL publicly | M | M | Acceptable for v1.2; swap publisher to one with auth if it becomes a problem — `Publisher` Protocol makes this a localized change |
| `gh-pages` worktree state corrupts between runs (e.g., uncommitted manual edits) | L | M | Publisher refuses to push if worktree is dirty; logs a clear instruction; HYL cleans manually |
| Telegram message preview card stale because Telegram caches by URL | L | L | Re-publishing identical content produces the same URL; updated content produces a new URL → fresh preview. Acceptable. |

---

## Technical Considerations

### Architecture Impact
Adds a **publisher** layer parallel to renderers. Channel adapters (Telegram for now; potentially Slack later) may consult a `Publisher` before composing their outbound payload. The composition is:

```
RenderedIssue
    │
    ├──→ html_web.render → str  ──┐
    │                              ├──→ GitHubPagesPublisher → PublishResult(url)
    │                              │              │
    │                              │              ▼
    │                              │      TelegramAdapter.send(issue, recipients)
    │                              │              │
    │                              │              ├── telegram_teaser.render(issue, url)
    │                              │              └── send via Bot API
    │
    └──→ html_email.render → str ──→ EmailAdapter.send  (unchanged from EP0005)
```

### Integration Points
- **`git` CLI** (subprocess): write file to worktree, `git add`, `git diff --quiet`, `git commit`, `git push`.
- **`git worktree`**: keeps `gh-pages` checked out at a fixed path (e.g., `.git/worktrees/gh-pages-publish/`).
- **`channels.yaml`**: add `publishers:` top-level key; per-channel `mode` and `publisher:` reference.
- **`techletter/audit.py`**: `SendRecord` schema gains an optional `published_url` field.

### Directory Layout (post-epic)

```
techletter/
├─ delivery/
│   ├─ publishers/
│   │   ├─ __init__.py
│   │   ├─ base.py                    # Publisher Protocol + PublishResult
│   │   └─ github_pages.py            # GitHubPagesPublisher
│   ├─ renderers/
│   │   ├─ tokens.py                  # (from EP0005)
│   │   ├─ html_web.py                # (from EP0005)
│   │   ├─ html_email.py              # (from EP0005)
│   │   └─ telegram_teaser.py         # NEW
│   ├─ telegram.py                    # mode dispatch; publisher hook
│   ├─ email.py                       # untouched (EP0005)
│   └─ slack.py                       # untouched
└─ audit.py                           # SendRecord.published_url
```

### Git / Repo Setup (one-time, documented in README)
- Create orphan branch: `git switch --orphan gh-pages && git rm -rf . && git commit --allow-empty -m "init gh-pages" && git push -u origin gh-pages`
- GitHub UI: `Settings → Pages → Build and deployment → Source: gh-pages branch / root`
- Confirm `https://<user>.github.io/<repo>/` resolves (will be 404 until first publish, which is fine)
- Local clone gets a worktree on first publish: `git worktree add .git/worktrees/gh-pages-publish gh-pages` (publisher handles this automatically if missing)

---

## Sizing

**Story Points:** 14
**Estimated Story Count:** 5

**Complexity Factors:**
- Git-state edge cases (dirty worktree, conflicting push, missing branch) require careful error mapping into `PublishResult` / `SendReport`.
- One-time GitHub setup documentation is a real story: subscribers/operators will hit this and we want it scripted, not folkloric.
- Two channels' code paths to keep coherent (Telegram `teaser_link` vs legacy `inline_html`); regression test the legacy path.
- Real-world smoke (push to GH Pages, wait for CDN, verify Telegram preview) is a manual step bound to surface timing/secret/PAT-permission surprises the first time.

---

## Story Breakdown

Stories generated 2026-05-21 from CR-0002 via `/sdlc-studio cr action`. See [Story Index](../stories/_index.md) for full details.

- [x] [US0028](../stories/US0028-publisher-protocol-and-publish-result.md) — `Publisher` Protocol + `PublishResult` model (2 pts)
- [x] [US0029](../stories/US0029-github-pages-publisher.md) — `GitHubPagesPublisher` (worktree + git push) (5 pts)
- [x] [US0030](../stories/US0030-telegram-teaser-renderer.md) — `telegram_teaser` renderer (2 pts)
- [x] [US0031](../stories/US0031-telegram-adapter-mode-and-publisher-wiring.md) — Telegram adapter `mode` + publisher wiring (3 pts)
- [x] [US0032](../stories/US0032-send-record-published-url-and-readme-and-e2e.md) — `SendRecord.published_url` + README + E2E smoke (2 pts)

**Total:** 14 story points across 5 stories.

---

## Test Plan

**Test Spec:** TS0006 — GitHub Pages Publishing + Telegram Link Mode (to be authored).

- **Unit (Protocol / PublishResult):** model construction, frozen invariant, JSON round-trip.
- **Unit (`GitHubPagesPublisher`, subprocess-mocked):** happy path; dirty-worktree refusal; missing-branch initialization; same-content-no-commit idempotency; push-failure surfaces as raised exception with token scrubbed.
- **Unit (`telegram_teaser`):** length invariant (`len(out) ≤ 4096`); URL appears verbatim; HTML escape of issue title with `< > &`; deterministic output for same input.
- **Unit (`TelegramAdapter`) mode dispatch:** `teaser_link` calls `publisher.publish` exactly once even with multiple recipients; `inline_html` doesn't call publisher; publisher failure → `SendReport.status=failed` with no Bot API call.
- **Unit (registry / config):** `channels.yaml` parses `publishers:`; missing publisher reference is a load error; pydantic validation errors are clear.
- **Integration (local bare repo as `origin`):** end-to-end publish into a temp bare repo; assert commit landed on `gh-pages`, file present, URL string assembled correctly.
- **Security:** TC0247 extended — across publisher and teaser paths, neither `TELEGRAM_BOT_TOKEN` nor `GITHUB_TOKEN`/PAT appears in any captured log record.
- **Manual smoke (HYL-owned):** real `draft` → real PR merge → real `send` against the real `gh-pages` branch; verify URL renders in browser; verify Telegram link preview card.

---

## Open Questions

- [ ] **Default sleep between publish and Telegram send?** Need real-world latency measurement once the first end-to-end smoke runs. Start at 0; bump to 30–60s if subscribers report 404s on tap. — Owner: HYL
- [ ] **`gh-pages` worktree path**: under `.git/worktrees/gh-pages-publish/` (invisible) vs top-level `dist/` (visible)? Lean invisible. — Owner: HYL
- [ ] **Should `published_url` survive into `SendRecord` even on `inline_html` mode?** No — `inline_html` doesn't publish. Field stays optional. — *Resolved during CR-0002 drafting.*
- [ ] **Should we add an explicit "what gets published is public" warning to `uv run techletter send` first-run output?** — Owner: HYL

---

## Revision History

| Date | Author | Change |
|------|--------|--------|
| 2026-05-21 | HYL | Epic created from CR-0002 via `/sdlc-studio cr action`. 5 stories generated (US0028–US0032), 14 pts total. EP0005 (Done) provides `html_web.render` + sidecar JSON. |
| 2026-05-21 | Claude (via /sdlc-studio epic implement --epic EP0006) | All 5 stories implemented and cascaded to Done. 49 new tests added (0 failing), 389 pass total (1 unrelated pre-existing failure on dirty channels.yaml). Ruff clean. README updated with GitHub Pages setup + audit schema. AC9 manual E2E smoke (US0032) remains HYL-owned. |
