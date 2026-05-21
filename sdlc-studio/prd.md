<!--
Product Requirements Document
Generated via /sdlc-studio prd create
-->

# Product Requirements Document

**Project:** Tech-Letter for HYL
**Version:** 0.4.0
**Last Updated:** 2026-05-19
**Status:** Ready

---

## 1. Project Overview

### Product Name
**Tech-Letter for HYL** — an automated weekly newsletter that surfaces the **major LLM-agent stories** by cross-comparing multiple sources. [HIGH]

### Purpose
Author a curated, low-noise weekly briefing on LLM agents (research, tools, repos, discussions). The system fetches from several sources, uses an LLM to cluster and rank topics by significance and novelty, drafts an issue (3 deep dives + 10 quick mentions), and — after author approval via a GitHub PR — fans the issue out to Email, Slack, and Telegram subscribers. [HIGH]

### Tech Stack
- **Language:** Python 3.11+ [HIGH]
- **LLM:** Anthropic Claude (Sonnet-class, e.g., `claude-sonnet-4-6`); per-run token budget **200,000 tokens** [HIGH]
- **Scheduling/Orchestration:** GitHub Actions (cron workflow) [HIGH]
- **Approval gate:** Git/GitHub (draft committed to branch → PR → merge triggers send) [HIGH]
- **Storage:** Repo-tracked YAML/JSON for subscribers + send log; no database in v1 [HIGH]
- **Email transport:** SMTP (Gmail or AWS SES) [HIGH]
- **Slack:** Incoming Webhook (channel post) [MEDIUM]
- **Telegram:** Bot API (sendMessage) [MEDIUM]

### Architecture Pattern
Two-stage pipeline triggered by GitHub Actions:
1. **`draft` workflow** (scheduled **weekly, Monday 09:00 KST** = `0 0 * * 1` UTC): fetch → cluster/rank → summarize → open PR with draft.
2. **`send` workflow** (triggered on PR merge): read approved draft → fan out to Email/Slack/Telegram → append send log.

---

## 2. Problem Statement

### Problem Being Solved
The LLM-agent space moves fast across disconnected venues (arXiv, GitHub, vendor and independent blogs). It is hard to keep up without either drowning in feeds or relying on hype-driven summaries. A single source rarely captures what is *actually* significant; signal emerges when something appears across multiple sources or is novel and substantive in research terms. [HIGH]

### Target Users
- **Author/Editor (primary user)** — runs the project for themselves and ~10–100 subscribers; needs minimal weekly effort (approve a PR), strong control over what ships. [HIGH]
- **Subscribers (readers)** — research-aware engineers who read papers AND ship LLM-backed features. Single audience tier. They value methodological rigor, provenance (paper vs. blog), and production-reality framing (cost, latency, replicability, shipping evidence). They receive issues via their preferred channel (Email, Slack, or Telegram). [HIGH]
- See `personas/` for full profiles. Non-coder readers are explicitly out of scope as of v0.4.0; see archived `Practitioner Subscriber` persona for context. [HIGH]

### Context
- Personal/side-project scale, not multi-tenant SaaS.
- Subscriber list maintained as a static config file in the repo (low overhead, no signup flow in v1).
- Approval gate is non-negotiable for v1 — author wants final say on every issue.

---

## 3. Feature Inventory

| ID | Feature | Description | Status | Priority |
|----|---------|-------------|--------|----------|
| F-01 | Multi-source ingestion | Fetch from arXiv (cs.AI, cs.CL), GitHub trending, and tech-blog RSS feeds: The New Stack AI (`https://thenewstack.io/ai`), Import AI (`https://importai.substack.com/`), Latent Space (`https://www.latent.space/`), Simon Willison (`https://simonwillison.net/atom/everything/`) | Not Started | Must |
| F-02 | LLM topic clustering & ranking | Cluster fetched items by topic, rank by cross-source significance + novelty | Not Started | Must |
| F-03 | Issue composer (3 + 10) | Produce 3 deep-dive summaries and 10 quick mentions in a single issue | Not Started | Must |
| F-04 | Draft-as-PR approval gate | Commit draft markdown to a branch and open a PR; merging signals approval | Not Started | Must |
| F-05 | Email delivery (SMTP) | Send issue to email list via SMTP (Gmail/SES). HTML rendering quality enhanced via [CR-0001](change-requests/CR0001-common-html-rendering.md) (shared Jinja2 renderer, premailer-inlined CSS, replaces `<pre>` wrapping). | Not Started | Must |
| F-06 | Slack delivery | Post issue to a Slack channel via Incoming Webhook | Not Started | Must |
| F-07 | Telegram delivery | Post issue to a Telegram channel/chat via Bot API. Enhanced via [CR-0002](change-requests/CR0002-github-pages-and-telegram-link-mode.md): default mode becomes `teaser_link` — adapter publishes the rendered page to GitHub Pages and sends a one-message teaser with the URL (replaces the multi-part `[Part 1/3]` split). Legacy `inline_html` mode preserved for safety. | Not Started | Must |
| F-08 | Subscriber config (static) | Recipients defined in `subscribers.yaml` (per-channel) | Not Started | Must |
| F-09 | Scheduled execution | GitHub Actions cron triggers weekly draft workflow | Not Started | Must |
| F-10 | Send log / audit trail | Append a record of each send (issue id, channel, recipient count, timestamp) | Not Started | Should |
| F-11 | Local dry-run | Run the pipeline locally without sending (for testing/iteration) | Not Started | Should |

### Feature Details

#### F-01 Multi-source ingestion
**User Story:** As the author, I want the system to pull recent items from arXiv, GitHub trending, and a configured list of tech-blog RSS feeds, so that the LLM has a broad enough input to find genuinely major topics.

**Acceptance Criteria:**
- [ ] Pulls arXiv recent submissions for `cs.AI` and `cs.CL`, filterable by LLM-agent keywords.
- [ ] Pulls GitHub trending repos for the past week, filterable by topic/language.
- [ ] Pulls items from a configurable list of RSS feeds. Initial set: The New Stack AI (`https://thenewstack.io/ai`), Import AI (`https://importai.substack.com/`), Latent Space (`https://www.latent.space/`), Simon Willison (`https://simonwillison.net/atom/everything/`). Additional feeds may be added by editing config only.
- [ ] Each fetched item is normalized to `{source, title, url, summary_excerpt, score, published_at, item_kind, maturity, raw}`.
  - `item_kind` ∈ `paper | blog_post | repo` — set by the adapter from source provenance (arXiv ⇒ `paper`; GitHub trending ⇒ `repo`; RSS ⇒ `blog_post`).
  - `maturity` ∈ `experimental | beta | production-ready | unknown` — inferred from item signals where possible (repo activity, release tags, presence of a hosted demo, eval-result framing in papers); else `unknown`.
- [ ] For GitHub-trending items, the adapter captures additional shipping/activity signals in `raw`: stars, last-commit timestamp, recent-release flag, hosted-demo URL (if discoverable from README badges) — used to inform `maturity` inference and to support "has anyone shipped this?" framing in F-03.
- [ ] Source list is in config; adding a feed does not require code changes.

**Confidence:** [HIGH]

#### F-02 LLM topic clustering & ranking
**User Story:** As the author, I want the LLM to cluster fetched items into topics and rank them by significance and novelty, so that the issue covers what genuinely matters this week — not just what was loudest.

**Acceptance Criteria:**
- [ ] Items are grouped into topic clusters (a topic may span multiple sources/items and multiple `item_kind`s).
- [ ] Each cluster has a rationale (why this is significant; how novel vs. prior weeks if state is available).
- [ ] **Ranking is `item_kind`-aware.** Papers, blog posts, and repos are scored on differentiated significance rubrics — papers weighted by methodological substance and cross-citation signal; blog posts weighted by author authority and cross-source overlap; repos weighted by maturity signals (recent activity, releases, hosted demo). A vendor blog announcement and an arXiv paper are not pooled at equal weight.
- [ ] Top N clusters are selected for deep dives; next M for quick mentions.
- [ ] Token usage per run is bounded by a configurable budget (default **200,000 tokens**) and logged; the run aborts before compose if projected usage would exceed the budget.

**Confidence:** [HIGH] (logic) / [MEDIUM] (exact ranking heuristic)

#### F-03 Issue composer (3 + 10)
**User Story:** As a subscriber, I want each issue to have 3 substantive deep dives plus 10 quick mentions, so that I get both depth and breadth without it being overwhelming.

**Acceptance Criteria:**
- [ ] Issue contains 3 deep-dive sections (~1–2 paragraphs each), each citing all contributing sources. Author may flex this 2–5 in editing.
- [ ] Issue contains 10 "also worth noting" bullets with a 1-line summary and link.
- [ ] **Each item displays its `item_kind`** (paper / blog post / repo) and `maturity` where known, so readers can immediately calibrate what kind of source they're being shown.
- [ ] **Deep-dive framing is conditioned on `item_kind`:**
  - Papers — "what was shown" + "method/eval at a glance" + "caveats" + (when source supports) "production-reality" line (cost, latency, replication status, deployment evidence).
  - Repos — "what it does" + maturity + shipping evidence (recent activity, releases, hosted demo, who's using it).
  - Blog posts — "what's being argued" + cross-source corroboration + author authority signal.
- [ ] Issue renders to clean Markdown (canonical) and is convertible to HTML (email) and plain text (Telegram/Slack fallback).
- [ ] An issue id and date are recorded in the issue front matter.

**Confidence:** [HIGH]

#### F-04 Draft-as-PR approval gate
**User Story:** As the author, I want every issue drafted as a Pull Request, so that I can review/edit it in a familiar interface and merging is the approval signal.

**Acceptance Criteria:**
- [ ] Draft workflow commits the rendered issue to a branch named `draft/issue-YYYY-MM-DD`.
- [ ] Workflow opens a PR with the issue body as the PR description.
- [ ] Merging the PR triggers the send workflow.
- [ ] Closing the PR without merge is a no-op (no send).
- [ ] **Queue behavior:** if one or more unresolved draft PRs already exist when a new scheduled run fires, the new draft is still created as an additional PR (queued alongside the others). Author resolves them in any order; each merge triggers an independent send.

**Confidence:** [HIGH]

#### F-05 Email delivery (SMTP)
**User Story:** As a subscriber, I want to receive the issue by email, so that I can read it in my inbox alongside other newsletters.

**Acceptance Criteria:**
- [ ] Sends HTML + plain-text multipart email via SMTP. HTML is rendered from a **Jinja2 template** under `templates/email.html.j2`.
- [ ] SMTP credentials read from GitHub Secrets (`SMTP_HOST`, `SMTP_USER`, `SMTP_PASS`).
- [ ] Recipients pulled from `subscribers.yaml` under the `email` key.
- [ ] Per-recipient send failure is logged but does not abort the run.

**Confidence:** [HIGH]

#### F-06 Slack delivery
**User Story:** As a subscriber on Slack, I want the issue posted to a configured channel, so that I see it in my normal workflow.

**Acceptance Criteria:**
- [ ] Posts to each configured Slack webhook URL.
- [ ] Long issues are split into multiple messages if they exceed Slack's payload limit.
- [ ] Webhook URLs from GitHub Secrets.

**Confidence:** [MEDIUM]

#### F-07 Telegram delivery
**User Story:** As a Telegram subscriber, I want the issue delivered to my chat/channel, so that I can read it on mobile.

**Acceptance Criteria:**
- [ ] Sends via Telegram Bot API `sendMessage` (with `parse_mode=MarkdownV2` or HTML).
- [ ] Messages are split to respect the 4096-char limit.
- [ ] Bot token from GitHub Secrets; chat IDs from `subscribers.yaml`.

**Confidence:** [MEDIUM]

#### F-08 Subscriber config (static)
**User Story:** As the author, I want subscribers declared in a YAML file in the repo, so that I do not need a database or signup flow in v1.

**Acceptance Criteria:**
- [ ] `subscribers.yaml` has three top-level keys: `email`, `slack`, `telegram`.
- [ ] Adding a recipient is a single edit + commit.
- [ ] The file is loaded and validated at the start of the send workflow.

**Confidence:** [HIGH]

#### F-09 Scheduled execution
**User Story:** As the author, I want the draft to be generated on a weekly cadence automatically, so that I do not have to remember to trigger it.

**Acceptance Criteria:**
- [ ] GitHub Actions workflow runs on `schedule:` cron `0 0 * * 1` (= Monday 09:00 KST, since KST = UTC+9).
- [ ] Workflow is also runnable on-demand via `workflow_dispatch`.
- [ ] A failed scheduled run surfaces a failure notification (GitHub default email is acceptable for v1).

**Confidence:** [HIGH]

#### F-10 Send log / audit trail
**User Story:** As the author, I want a log of what was sent and to whom, so that I can debug delivery issues and avoid duplicate sends.

**Acceptance Criteria:**
- [ ] Each send appends to `logs/sends.jsonl` and is **committed to `main`** by the send workflow with `{issue_id, channel, recipients_count, timestamp, status}`.
- [ ] The same issue id never sends twice on the same channel (idempotency check reads `logs/sends.jsonl` on merge).

**Confidence:** [MEDIUM]

#### F-11 Local dry-run
**User Story:** As the author, I want to run the full pipeline locally with `--dry-run`, so that I can iterate on prompts and formatting without burning LLM tokens or risking accidental sends.

**Acceptance Criteria:**
- [ ] CLI command produces a draft markdown locally without committing or sending.
- [ ] Flag to use cached fetch results to avoid re-hitting sources during iteration.

**Confidence:** [HIGH]

---

## 4. Functional Requirements

### Core Behaviours
- **Fetch:** pull recent items from each configured source within a tunable lookback window (default: 7 days).
- **Normalize & deduplicate:** merge near-duplicates (e.g., same paper linked from arXiv and cross-referenced in an RSS feed) into a single item with `mentions: [...]`.
- **Cluster & rank:** LLM groups items into topics; ranks by significance (cross-source presence + topical importance) and novelty.
- **Compose:** LLM writes 3 deep dives and 10 quick mentions; emits canonical Markdown.
- **Approval:** draft committed to a branch; PR opened; merge triggers send.
- **Send:** fan out to Email (SMTP), Slack (webhook), Telegram (Bot API); log result.

### Input/Output Specifications
- **Input:** source configuration (YAML), subscriber configuration (YAML), GitHub Secrets (API keys).
- **Output (intermediate):** normalized item list (JSON), clustered topics (JSON), draft issue (Markdown).
- **Output (terminal):** delivered messages on each channel; `sends.jsonl` audit entry.

### Business Logic Rules
- A draft is **never** sent without being merged (no auto-send path).
- An issue id is never sent twice on the same channel (idempotency).
- A run partially failing on one channel does not block other channels.
- Token usage is logged per run; runs that exceed a configurable budget abort before composing.

---

## 5. Non-Functional Requirements

### Performance
- Full draft generation (fetch → compose) completes in **< 5 minutes** on a GitHub Actions runner for the v1 source set. [MEDIUM]
- Send fan-out for 100 subscribers completes in **< 2 minutes**. [MEDIUM]

### Security
- All API keys, SMTP credentials, Slack webhooks, and Telegram bot tokens are stored in **GitHub Secrets**; never committed to the repo. [HIGH]
- Subscriber list in repo is acceptable in v1 because it consists of the author's own contacts who have consented; this must be reassessed if scope changes. [MEDIUM]
- The send workflow only runs on PR merges to `main` by trusted committers (use `if: github.event.pull_request.merged == true` + branch protection). [HIGH]

### Scalability
- Designed for **10–100 subscribers** in v1; SMTP via Gmail is rate-limited (~500/day) which is well above this. If list grows past ~500, migrate to a transactional API (Resend/SES). [HIGH]
- Source set may grow; ingestion must be parallel-safe and per-source failures isolated. [MEDIUM]

### Availability
- Best-effort weekly cadence. A missed week is acceptable; a failed run surfaces via GitHub's default workflow-failure email. [HIGH]
- No SLA; this is a personal newsletter.

---

## 6. AI/ML Specifications

### Models and Providers
- **Provider:** Anthropic Claude — Sonnet-class model (e.g., `claude-sonnet-4-6`). [HIGH]
- The LLM client is abstracted behind an internal interface to allow swapping providers later. [MEDIUM]

### Prompt Patterns
- **Cluster prompt:** receives normalized items; returns topic clusters with rationales.
- **Rank prompt:** receives clusters; returns top-N selections with `significance` and `novelty` scores and explanations.
- **Deep-dive prompt:** for each selected cluster, generates a 1–2 paragraph summary citing contributing items.
- **Quick-mention prompt:** generates 1-line summaries for the next M items.
- Prompts live in `prompts/*.md` files (not inlined) so they can be iterated and reviewed in PRs.

### Context Management
- Items passed to clustering are pre-truncated to a budget (title + 1–2 paragraph excerpt).
- No long-term memory in v1; each run is stateless except for the `sends.jsonl` log.

### Cost Guardrails
- Per-run token budget: **200,000 tokens** (configurable); abort before compose if projected usage would exceed. [HIGH]
- Token usage logged per run in `sends.jsonl` for observability.

---

## 7. Data Architecture

### Data Models
All data is file-based; no database in v1.

- **`config/sources.yaml`** — list of feeds/sources to ingest.
- **`config/subscribers.yaml`** — recipients grouped by channel.
- **`drafts/issue-YYYY-MM-DD.md`** — generated drafts (committed to branches).
- **`sends.jsonl`** — append-only audit log of sends.
- **`prompts/*.md`** — versioned LLM prompts.

### Relationships and Constraints
- One draft → one PR → one merge → one set of sends (one per configured channel).
- A subscriber appears under at most one channel section (no cross-channel deduplication needed in v1).

### Storage Mechanisms
- Git itself is the durable store. No external DB. This is intentional for v1 — keeps ops cost at zero.

---

## 8. Integration Map

### External Services
| Service | Purpose | Auth |
|---------|---------|------|
| Anthropic API | LLM for clustering/ranking/composition | API key (`ANTHROPIC_API_KEY`) |
| arXiv API | Recent papers in cs.AI/cs.CL | None (public) |
| GitHub Trending | Trending repos | Scrape or unofficial API |
| RSS feeds | Tech blog feeds | None |
| SMTP (Gmail/SES) | Email delivery | `SMTP_USER` / `SMTP_PASS` |
| Slack | Channel posts | Incoming Webhook URL |
| Telegram | Channel/chat posts | Bot token + chat IDs |
| GitHub Actions | Scheduling + orchestration | Built-in `GITHUB_TOKEN` |

### Authentication Methods
- All third-party secrets via **GitHub Actions Secrets** (encrypted at rest, scoped to repo).
- No OAuth flows for end users — subscribers do not authenticate.

### Third-Party Dependencies (planned)
- `anthropic` (LLM SDK)
- `feedparser` (RSS)
- `arxiv` (arXiv client)
- `pyyaml`, `pydantic` (config + validation)
- `jinja2` (HTML email template rendering)
- `httpx` (HTTP client)
- `python-telegram-bot` or direct HTTP for Telegram

---

## 9. Configuration Reference

### Environment Variables (GitHub Secrets)

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `ANTHROPIC_API_KEY` | LLM provider API key | Yes | — |
| `SMTP_HOST` | SMTP server hostname | Yes | — |
| `SMTP_PORT` | SMTP server port | No | 587 |
| `SMTP_USER` | SMTP username | Yes | — |
| `SMTP_PASS` | SMTP password / app password | Yes | — |
| `SMTP_FROM` | From address | Yes | — |
| `SLACK_WEBHOOK_URLS` | Comma-separated Slack webhook URLs | If Slack enabled | — |
| `TELEGRAM_BOT_TOKEN` | Telegram bot token | If Telegram enabled | — |

### Feature Flags
- `DRY_RUN` (env or CLI flag): generate draft locally without committing or sending.
- Per-channel enable flags in `config/channels.yaml` (default: all enabled).

---

## 10. Quality Assessment

### Tested Functionality
- None yet — greenfield project at the **spec-complete pre-implementation stage**. 4 Epics, 22 Stories, and 4 test specs (TS0001–TS0004, all Ready) are authored; no source code written.

### Untested Areas
- All features pending implementation. Test specs define **260 named test cases (TC0001–TC0260)** covering **157/157 acceptance criteria** across all 4 epics; see [`sdlc-studio/test-specs/_index.md`](test-specs/_index.md).

### Technical Debt
- None yet. Anticipated future debt:
  - GitHub trending scraping is fragile (no official API); revisit.
  - Static subscriber file does not scale past ~100 / lacks unsubscribe link.
  - No long-term memory means novelty detection is approximate.

---

## 11. Open Questions

_All open questions resolved as of v0.4.0. See Changelog for resolution history._

---

## Changelog

| Date | Version | Changes |
|------|---------|---------|
| 2026-05-19 | 0.1.0 | Initial PRD created via `/sdlc-studio prd create` |
| 2026-05-19 | 0.1.1 | `/sdlc-studio prd review`: confirmed initial RSS feeds (The New Stack AI, Import AI, Latent Space); reconciled F-01 acceptance criteria with feature inventory table; narrowed Open Question on feed list. |
| 2026-05-19 | 0.1.2 | Project name confirmed: **Tech-Letter for HYL**. Closed Open Question on project name. |
| 2026-05-19 | 0.1.3 | Cadence locked (Monday 09:00 KST = cron `0 0 * * 1` UTC). LLM = Anthropic Claude Sonnet, 200K token budget per run. Closed 2 Open Questions. |
| 2026-05-19 | 0.2.0 | Scope change: **Reddit dropped as a source**. RSS feed list finalised (TNS AI, Import AI, Latent Space, Simon Willison). `logs/sends.jsonl` committed to `main`. Draft-PR collision = queue. Email HTML rendered via Jinja2 template. **All open questions closed**; status moved Draft → Ready. |
| 2026-05-19 | 0.3.0 | Audience scope made explicit: **multi-tier** (research-aware engineers + non-coder knowledge workers). Item model extended with `item_kind`, `maturity`, `access` (F-01). F-02 ranking is now `item_kind`-aware. F-03 composer is audience-aware: per-item `access` indicator, `item_kind`-conditioned deep-dive framing (papers get caveats + production-reality; repos/products get plain-language + try-it line). "Exactly 3" deep dives softened to 3 with 2–5 flex. Driven by stakeholder consultation v2. |
| 2026-05-19 | 0.4.0 | Audience scope **narrowed to single tier** — research-aware engineer only. Practitioner (non-coder) persona archived. Dropped `access` field from `Item` (specific to non-coder accessibility). `item_kind` enum trimmed: `consumer_product` removed (`paper | blog_post | repo`). F-03 simplified: dropped `access`-indicator AC; deep-dive framing reduces to three `item_kind` cases (paper / repo / blog) all aimed at research-aware engineer. `maturity` field and GitHub shipping signals retained — they serve the Researcher's "has anyone shipped this?" concern. |
| 2026-05-19 | 0.4.1 | Unified `/sdlc-studio review` pass: cleaned 3 stale references — removed "Reddit" example from §4 normalize/dedupe text (Reddit was dropped in v0.2.0); refreshed §10 Quality Assessment from "PRD stage" to spec-complete state with TS counts; corrected §11 open-questions cutoff from v0.2.0 to v0.4.0. No semantic changes. |

---

> **Confidence Markers:** [HIGH] clear from input | [MEDIUM] inferred / reasonable default | [LOW] speculative
>
> **Status Values:** Complete | Partial | Stubbed | Broken | Not Started
