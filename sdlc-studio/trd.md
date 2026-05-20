<!--
Technical Requirements Document
Generated via /sdlc-studio trd create
-->

# Technical Requirements Document

**Project:** Tech-Letter for HYL
**Version:** 0.3.2
**Status:** Ready
**Last Updated:** 2026-05-19
**PRD Reference:** [PRD](./prd.md) (v0.4.1, Ready)

---

## 1. Executive Summary

### Purpose
Define the technical design for **Tech-Letter for HYL** — a Python batch pipeline, run on a weekly GitHub Actions cron, that ingests LLM-agent items from multiple sources, uses Claude (Sonnet-class) to cluster and rank them, drafts an issue (3 deep dives + 10 quick mentions) as a PR for author approval, and on merge fans out to Email/Slack/Telegram.

### Scope
**In scope:** runtime architecture, module boundaries, adapter interfaces, technology choices, retry/failure isolation, observability, dev tooling, GitHub Actions workflow design, security/secrets.

**Out of scope:** persona definitions (TRD has no users), product UX, marketing copy, future migration paths beyond the v1 architecture (those become CRs).

### Key Decisions
- **Project type:** CLI / batch pipeline (no server, no UI, runs on Actions runner).
- **Architecture pattern:** **Layered pipeline with adapter pattern** for sources and delivery channels.
- **Stack:** Python 3.11+, uv (env/deps), ruff (lint+format), pyright (types), tenacity (retries), Jinja2 (email HTML), Anthropic SDK.
- **Reliability:** per-unit isolation — one failing source or recipient does not abort the run; retries via tenacity with exponential backoff.
- **Storage:** git is the durable store. Subscriber list, prompts, drafts, and send log all live in the repo.
- **Approval gate:** non-bypassable — only a merged PR triggers a send.

---

## 2. Project Classification

**Project Type:** Desktop Application — specifically a CLI / scheduled batch tool. [HIGH]

**Classification Rationale:** The system has no UI, no API surface, no persistent server process. It is a Python program invoked on a cron schedule from GitHub Actions; it produces side effects (PRs, emails, messages) and exits. This is the "CLI tool" subtype of Desktop Application in the SDLC Studio taxonomy.

**Architecture Implications:**
- **Default Pattern (per taxonomy):** Layered
- **Pattern Used:** Layered + Adapter (sources and delivery channels behind common interfaces)
- **Deviation Rationale:** The Adapter pattern is layered onto the default to keep the source set and delivery channel set independently extensible. Adding a new RSS feed or a new channel must not touch the core pipeline code.

---

## 3. Architecture Overview

### System Context

```
                    GitHub Actions (cron)
                            │
                            ▼
        ┌─────────────────────────────────┐
        │   Tech-Letter for HYL (Python)  │
        │                                 │
   ┌────┤  fetch ─► cluster ─► compose    ├────┐
   │    │            (Claude)             │    │
   │    └─────────────────────────────────┘    │
   │                                           │
   ▼                                           ▼
External sources                       Delivery channels
- arXiv (cs.AI, cs.CL)                 - SMTP (Gmail/SES)
- GitHub trending                      - Slack (webhook)
- RSS (TNS, Import AI,                 - Telegram (Bot API)
  Latent Space, Willison)
                                       Approval gate:
                                       GitHub PR (draft → merge)
```

### Architecture Pattern
**Layered pipeline** with **adapter pattern** at the I/O boundaries.

**Rationale:** The pipeline is naturally sequential (fetch → cluster → compose → draft → send). Adapters give us replaceable sources and channels without disturbing the pipeline core, supporting Open Question on expanding feeds later and adding new channels post-v1.

### Component Overview

| Component | Responsibility | Technology |
|-----------|---------------|------------|
| `techletter.sources.*` | One adapter per source (`arxiv.py`, `github.py`, `rss.py`). Implements `SourceAdapter` protocol. | Python, `feedparser`, `arxiv`, `httpx` |
| `techletter.pipeline.cluster` | Group normalised items into topics via LLM | Anthropic SDK |
| `techletter.pipeline.rank` | Rank clusters by significance + novelty | Anthropic SDK |
| `techletter.pipeline.compose` | Render 3 deep dives + 10 quick mentions to canonical Markdown | Anthropic SDK + string formatting |
| `techletter.delivery.*` | One adapter per channel (`email.py`, `slack.py`, `telegram.py`). Implements `ChannelAdapter` protocol. | `smtplib`, `httpx`, Jinja2 |
| `techletter.llm` | Thin wrapper around Anthropic client; tracks token usage + budget enforcement | Anthropic SDK |
| `techletter.config` | Load + validate `config/*.yaml` and `subscribers.yaml` | `pyyaml`, `pydantic` |
| `techletter.cli` | Click-based entry points: `draft`, `send`, `dry-run` | `click` |
| `techletter.audit` | `SendRecord` model, `append_send_record`, `already_sent` (idempotency check), `load_records` over `logs/sends.jsonl` | `pydantic`, stdlib |
| `techletter.cache` | Dev-only fetch + LLM response cache under `.cache/`; hard-disabled in CI via `CI`/`GITHUB_ACTIONS` env guard | stdlib (`hashlib`, `pathlib`, `tempfile`) |
| `.github/workflows/draft.yml` | Weekly cron → run `techletter draft` → open PR | GitHub Actions |
| `.github/workflows/send.yml` | On PR merge → run `techletter send` → append `logs/sends.jsonl` | GitHub Actions |

### Adapter Protocols

```python
# techletter/sources/base.py
class SourceAdapter(Protocol):
    name: str
    def fetch(self, window_days: int) -> list[Item]: ...

# techletter/delivery/base.py
class ChannelAdapter(Protocol):
    name: str
    def send(self, issue: RenderedIssue, recipients: list[str]) -> SendReport: ...
```

`Item` and `RenderedIssue` are pydantic models defined in `techletter.models`.

---

## 4. Technology Stack

### Core Technologies

| Category | Technology | Version | Rationale |
|----------|-----------|---------|-----------|
| Language | Python | 3.11+ | PRD-locked. Best ecosystem for LLM SDKs and feed parsing. |
| Env / deps | uv | latest | 10–100× faster than pip; lockfile (`uv.lock`) is reproducible; single tool replaces venv + pip + pip-tools. |
| Lint + format | ruff | latest | One tool for lint + format (replaces flake8 + isort + black). Fast. |
| Type check | pyright | latest | Stricter and faster than mypy; same checker Pylance uses. |
| LLM SDK | `anthropic` | latest | Official SDK; supports streaming + token counting needed for budget enforcement. |
| Retries | `tenacity` | latest | Composable retry decorators (exponential backoff, jitter, max attempts). |
| Config | `pydantic` v2 | 2.x | YAML → typed config with validation errors at load time, not at use time. |
| HTML email | `jinja2` | 3.x | PRD-locked. Simple, well-known. |
| HTTP | `httpx` | latest | Modern, async-capable (not used in v1 but future-friendly). |
| Feeds | `feedparser` | latest | De-facto standard for RSS/Atom in Python. |
| arXiv | `arxiv` | latest | Wraps the arXiv query API; handles pagination and rate limiting. |
| CLI | `click` | latest | Clean argparse alternative; sub-commands fit our `draft` / `send` / `dry-run` shape. |
| Tests | `pytest` + `pytest-mock` | latest | Industry default. (Test strategy itself goes in TSD.) |

### Build & Development

| Tool | Purpose |
|------|---------|
| `uv sync` | Install/refresh deps from `uv.lock` |
| `uv run techletter ...` | Run the CLI without manually activating a venv |
| `ruff check . && ruff format .` | Lint + format gate |
| `pyright` | Type-check gate |
| `pytest` | Unit + integration tests |
| `pre-commit` | Run ruff + pyright on staged files (optional) |

### Infrastructure Services

| Service | Provider | Purpose |
|---------|----------|---------|
| CI / scheduler | GitHub Actions | Both `draft.yml` cron and `send.yml` on-merge workflows |
| LLM | Anthropic API | Cluster, rank, compose |
| Email | SMTP (Gmail or AWS SES) | Newsletter delivery |
| Slack | Incoming Webhook | Channel posts |
| Telegram | Bot API | Channel/chat posts |
| Source: arXiv | arXiv API | Public, no auth |
| Source: GitHub Trending | GitHub Trending HTML / unofficial JSON | Public, no auth |
| Source: RSS feeds | Direct HTTP | Public, no auth |

---

## 5. API Contracts

**Not applicable** — Tech-Letter for HYL has no inbound API. It is a one-shot batch process invoked by GitHub Actions.

**Outbound API usage** is documented in §7 (Integration Patterns) below.

---

## 6. Data Architecture

### Data Models

All data flows are in-process during a run except `logs/sends.jsonl` (persisted in git).

#### `Item` (normalised source item)

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `source` | `Literal["arxiv","github","rss"]` | required | Adapter that produced it |
| `source_subtype` | `str \| None` | optional | e.g., feed URL or arxiv category |
| `title` | `str` | required | Item headline |
| `url` | `str` | required, http(s) | Canonical link |
| `summary_excerpt` | `str` | ≤ ~500 chars | Pre-truncated for LLM context budget |
| `score` | `float \| None` | optional | Upstream popularity score (stars / votes / citations) |
| `published_at` | `datetime` | tz-aware, UTC | When upstream published |
| `item_kind` | `Literal["paper","blog_post","repo"]` | required | Source-provenance class. Adapter sets it: arXiv ⇒ `paper`; GitHub ⇒ `repo`; RSS ⇒ `blog_post`. Drives `item_kind`-aware ranking in F-02 and `item_kind`-conditioned framing in F-03. |
| `maturity` | `Literal["experimental","beta","production-ready","unknown"] \| None` | optional | Inferred from repo activity, release tags, hosted-demo presence, eval framing in papers, etc. Defaults to `unknown` when no inference signal is available. Used by F-03 to render "shipping evidence" framing for the research-aware engineer reader. |
| `raw` | `dict` | required | Raw upstream payload for debugging. For GitHub items, includes shipping/activity signals: `stars`, `last_commit_at`, `has_recent_release`, `hosted_demo_url`. |

#### `Cluster`

| Field | Type | Description |
|-------|------|-------------|
| `id` | `str` | Generated UUID4 |
| `topic` | `str` | LLM-assigned topic name |
| `items` | `list[Item]` | Items grouped into this cluster |
| `significance` | `float` | LLM score 0–1 |
| `novelty` | `float` | LLM score 0–1 |
| `rationale` | `str` | LLM explanation |

#### `RankedClusters`

| Field | Type | Description |
|-------|------|-------------|
| `deep` | `list[Cluster]` | Top-N selected for deep dives (ordered by significance desc; length ≤ `top_deep`) |
| `quick` | `list[Cluster]` | Next-M selected for quick mentions (ordered; length ≤ `top_quick`) |
| `unselected` | `list[Cluster]` | Remaining clusters (kept for diagnostics) |
| `rationale_by_cluster_id` | `dict[str, str]` | Cluster id → 1–3 sentence rationale (LLM output) |

#### `DeepDive`

| Field | Type | Description |
|-------|------|-------------|
| `topic` | `str` | Topic name (from parent `Cluster`) |
| `body_markdown` | `str` | Rendered 1–2 paragraph markdown body, ≤300 words target |
| `cited_urls` | `list[str]` | All contributing item URLs |
| `item_kind` | `Literal["paper","blog_post","repo"]` | Inherits from the cluster's dominant kind; drives which compose prompt was used |
| `maturity_summary` | `str \| None` | Single human-readable sentence for repo dives only; `None` for paper / blog |

#### `QuickMention`

| Field | Type | Description |
|-------|------|-------------|
| `topic` | `str` | Short topic name |
| `one_liner` | `str` | ≤ 200 chars, single sentence |
| `url` | `str` | Primary item's URL |
| `item_kind` | `Literal["paper","blog_post","repo"]` | — |
| `maturity` | `str \| None` | Optional; rendered only when known |

#### `RenderedIssue`

| Field | Type | Description |
|-------|------|-------------|
| `issue_id` | `str` | `YYYY-MM-DD` (one per scheduled run) |
| `markdown` | `str` | Canonical markdown body |
| `html` | `str` | Rendered HTML (via Jinja2) for email |
| `plaintext` | `str` | Plain-text fallback (also used for Slack/Telegram) |
| `meta` | `dict` | Front-matter: token usage, sources counted, etc. |

#### `SendReport` (adapter return type — not persisted; consumed by registry + CLI)

| Field | Type | Description |
|-------|------|-------------|
| `channel` | `Literal["email","slack","telegram"]` | — |
| `recipients_count` | `int` | ≥ 0 |
| `success_count` | `int` | ≥ 0 |
| `failure_count` | `int` | ≥ 0 |
| `status` | `Literal["ok","partial","failed"]` | Derived from counts via a `model_validator(mode='after')`; consistency enforced |
| `failures` | `list[FailureDetail]` | Per-recipient `{recipient: str, error: str}` records for diagnosis |

`SendReport` is what each `ChannelAdapter.send()` returns; the registry's `send_all` returns `list[SendReport]`. The CLI converts each `SendReport` into a `SendRecord` (below) for persistence.

#### `SendRecord` (one line per channel per merge, appended to `logs/sends.jsonl`)

| Field | Type | Description |
|-------|------|-------------|
| `issue_id` | `str` | Matches `RenderedIssue.issue_id` |
| `channel` | `Literal["email","slack","telegram"]` | — |
| `recipients_count` | `int` | Per channel |
| `success_count` | `int` | Per channel |
| `failure_count` | `int` | Per channel |
| `timestamp` | `str` | ISO-8601 UTC |
| `status` | `Literal["ok","partial","failed"]` | Roll-up |

### Storage Strategy

| Data Type | Storage | Rationale |
|-----------|---------|-----------|
| Config (sources, channels, schedule knobs) | `config/*.yaml` in repo | Version-controlled, code-reviewable |
| Subscriber list | `config/subscribers.yaml` in repo | PRD-decided; small list of personal contacts |
| Prompts | `prompts/*.md` in repo | Reviewable in PR diff; iterate without code changes |
| Drafts | `drafts/issue-YYYY-MM-DD.md` on a branch + PR | Approval gate; merged drafts stay in history |
| Send log | `logs/sends.jsonl` on `main` | PRD-decided; idempotency check reads this |
| Dev cache | `.cache/` (git-ignored) | Local-only; used by `--dry-run` to skip live API calls |

### Migrations
**Not applicable** in v1 — no schema. Future work: if subscriber list moves to SQLite or a managed newsletter platform, migrations are introduced as a CR.

---

## 7. Integration Patterns

### External Services

| Service | Purpose | Protocol | Auth | Rate-limit posture |
|---------|---------|----------|------|--------------------|
| Anthropic Messages API | LLM cluster/rank/compose | HTTPS (REST) | `ANTHROPIC_API_KEY` | SDK handles 429; tenacity wraps for additional backoff |
| arXiv | Recent papers in cs.AI, cs.CL | HTTPS (REST/XML) | None | Built-in delay in `arxiv` lib (3s); single fetch per run |
| GitHub Trending | Trending repos last 7 days | HTTPS (HTML/JSON scrape) | Optional `GITHUB_TOKEN` | Cache for a run; one fetch |
| RSS feeds | Tech blog items | HTTPS (RSS/Atom) | None | One fetch per feed per run |
| SMTP (Gmail/SES) | Email delivery | SMTPS (TLS) | `SMTP_USER` / `SMTP_PASS` | Gmail: 500/day limit; well above v1 list size |
| Slack | Channel post | HTTPS (webhook) | URL itself is the secret | Slack returns 429 on burst; tenacity backoff |
| Telegram | Channel/chat send | HTTPS (Bot API) | `TELEGRAM_BOT_TOKEN` | Bot API rate-limited (30/sec); not a v1 concern |

### Event Architecture
**Not applicable.** The system is request-response within one run; the only "event" is `pull_request: types: [closed]` in GitHub Actions, which is consumed by `send.yml` to trigger the send workflow.

### Failure Isolation Strategy

| Failure type | Behaviour |
|--------------|-----------|
| One source returns 5xx / throws | Logged, tenacity retries (3 attempts, exp backoff), then skipped for this run. Other sources proceed. |
| LLM call fails | tenacity retries (up to 5 attempts). If still failing, the run aborts before draft commit (no half-finished PRs). |
| LLM budget exceeded | Run aborts before compose step; no PR. Workflow surfaces failure. |
| One email recipient rejects | Logged; other recipients proceed. SendRecord status = `partial`. |
| Slack webhook 4xx | Logged; other channels proceed. |
| Telegram chat invalid | Logged; other recipients proceed. |
| Idempotency hit (already sent this issue on this channel) | Skip channel; log "skipped (already sent)". |

---

## 8. Infrastructure

### Deployment Topology
No deployment in the traditional sense. The "app" is a Python package executed by GitHub Actions runners. No long-running process exists; nothing to deploy beyond merging code to `main`.

### Environments

| Environment | Purpose | Characteristics |
|-------------|---------|-----------------|
| **Local** | Author iterates on prompts, templates, source adapters | `uv run techletter draft --dry-run` writes to `drafts/.local/`; uses `.cache/` for fetches and LLM responses |
| **CI (Actions)** | Production runtime | Scheduled cron + on-merge workflows; secrets injected via GitHub Secrets |

**No staging environment** — the PR-as-draft pattern *is* staging. The author reviews the PR before merge.

### Workflow Definitions

**`.github/workflows/draft.yml`**
- Trigger: `schedule: cron "0 0 * * 1"` (Monday 09:00 KST) + `workflow_dispatch`
- Steps: checkout → `uv sync` → `uv run techletter draft` → `gh pr create`
- Permissions: `contents: write`, `pull-requests: write`
- Concurrency: not constrained — multiple drafts may coexist (queue semantics, per F-04)

**`.github/workflows/send.yml`**
- Trigger: `pull_request: { types: [closed], branches: [main] }`, with `if: github.event.pull_request.merged == true`
- Steps: checkout merged commit → `uv sync` → `uv run techletter send --issue <issue_id>` → commit `logs/sends.jsonl` back to `main`
- Permissions: `contents: write`
- Branch protection: only PRs from trusted committers may merge to `main` (configured in GitHub repo settings).

### Scaling Strategy
**Not a scaling problem in v1.** A weekly job for ≤100 recipients fits comfortably on a free Actions runner (default `ubuntu-latest`, 4 vCPU, 16 GB RAM). Future scale-up is documented as Implementation Constraints (§13).

---

## 9. Security Considerations

### Threat Model

| Threat | Likelihood | Impact | Mitigation |
|--------|-----------|--------|------------|
| Secret leakage via committed `.env` | L | H | `.gitignore` includes `.env`, `.env.*`; pre-commit hook scans for high-entropy strings; CI uses GitHub Secrets only |
| Untrusted committer triggers a send | L | M | Branch protection on `main`; `send.yml` runs only on merged PRs to `main`; CODEOWNERS reviewed |
| LLM cost runaway (prompt injection or feed flood) | M | M | 200K token budget per run (PRD-locked); abort-before-compose if exceeded |
| Telegram / Slack token compromise | L | M | Stored only in GitHub Secrets; rotateable; revoke + reissue is one-step |
| SMTP credential compromise | L | M | Use a dedicated app-password Gmail account or a scoped SES IAM user; rotate quarterly |
| Subscriber list privacy | L | L | List contains contacts who consented; not commercial PII. Reassess if scope changes (PRD §5). |
| Outbound spam classification | M | M | SPF/DKIM/DMARC configured on the From-domain; opt-out instructions in every issue footer |

### Security Controls

| Control | Implementation |
|---------|----------------|
| Authentication (outbound) | API key / bot token / SMTP creds via GitHub Secrets |
| Authorisation (workflow) | `if: github.event.pull_request.merged == true` + `permissions:` block in each workflow scoped to minimum |
| Encryption at rest | GitHub Secrets are encrypted at rest by GitHub |
| Encryption in transit | All outbound calls are HTTPS / SMTPS |
| Audit log | `logs/sends.jsonl` (committed) records every send |
| Dependency hygiene | Dependabot enabled; `uv.lock` pinned |
| Static analysis | ruff rule set includes `S` (bandit-equivalent security checks) |

---

## 10. Performance Requirements

| Metric | Target | Measurement |
|--------|--------|-------------|
| Draft workflow wall-clock | < 5 min | GitHub Actions step timer |
| Send fan-out (100 recipients) | < 2 min | Wall-clock from start of `techletter send` to last `SendRecord` |
| LLM token usage per run | ≤ 200K | Logged in `RenderedIssue.meta`, asserted before compose |
| Cost per run | ≤ $1 (est., Sonnet-class) | Derived from token usage × current pricing |
| Free-tier Actions minutes per month | ≤ ~30 min/month | 4 runs × ~7 min combined draft+send |

---

## 11. Architecture Decision Records

### ADR-001: Use GitHub Actions as the sole runtime + scheduler
**Status:** Accepted

**Context:** We need a recurring trigger and a place to run a Python pipeline weekly. Options: cron on a VPS, AWS Lambda + EventBridge, a serverless platform, GitHub Actions.

**Decision:** Use GitHub Actions. Free for public repos / generous for private repos at v1 scale; cron + on-PR-merge triggers are first-class; secrets management is built in; the runtime is the same place the code lives.

**Consequences:**
- Positive: zero ops cost; secrets, scheduler, and runtime in one tool; PR-as-approval-gate is native.
- Negative: longer cold-starts than a warm process; coupled to GitHub; per-job 6h limit but our jobs are minutes.
- Future: revisit if usage outgrows free minutes or if we need event triggers GitHub Actions doesn't model.

---

### ADR-002: Adapter pattern for sources and delivery channels
**Status:** Accepted

**Context:** PRD lists 4+ sources and 3 channels for v1, with explicit room to add more later (RSS feeds expand, future Discord/email-platform channels). A pipeline that hardcodes source and channel handling would force core edits for every new I/O endpoint.

**Decision:** Define `SourceAdapter` and `ChannelAdapter` protocols. Each source and each channel is a module under `techletter/sources/` or `techletter/delivery/` implementing the protocol. Pipeline core iterates over a registry.

**Consequences:**
- Positive: adding a feed = one new module + one config line; adding a channel is similar; sources/channels are independently testable with the same harness.
- Negative: slight indirection vs flat code; needs a registry and discovery mechanism (kept simple: explicit imports in `__init__.py`).

---

### ADR-003: Git is the only durable store (no database)
**Status:** Accepted

**Context:** PRD requires subscriber list, drafts, audit log, and prompts to persist across runs. Options: SQLite committed to repo, external DB, GitHub artifacts, plain files in git.

**Decision:** Files in git, committed to `main` (config, prompts, `logs/sends.jsonl`) or on a draft branch (`drafts/`).

**Consequences:**
- Positive: zero ops; everything is reviewable in PR diffs; recoverable from git history; no separate backup story.
- Negative: writes contend on `main` (acceptable: 1 commit per send, 1 per merge); won't scale past a few hundred subscribers; log files grow over years (acceptable for years before action needed).

---

### ADR-004: tenacity for retries; per-unit failure isolation
**Status:** Accepted

**Context:** Sources and channels each fail in different ways; LLM calls are 429-prone at peak times. PRD requires per-recipient failure isolation. We need a uniform retry policy without sprinkling try/except trees.

**Decision:** Wrap each source fetch, each LLM call, and each delivery call in tenacity decorators with exponential backoff + jitter. Catch-and-log at the *unit* boundary (one source, one recipient) so partial failures roll up to `partial` status instead of aborting the run.

**Consequences:**
- Positive: consistent retry behaviour; clear "blast radius" of each failure (one source, one recipient); status reports are accurate.
- Negative: tenacity adds a small dependency; backoff math needs occasional tuning if Anthropic or upstream sources change rate-limit shapes.

---

### ADR-005: Local cache for `--dry-run` development
**Status:** Accepted

**Context:** Iterating on prompts and templates without a cache would cost LLM tokens and hit upstream sources repeatedly during development.

**Decision:** `--dry-run` uses a JSON-on-disk cache under `.cache/` (git-ignored). Fetch results cached by `{source, window_days, date}`. LLM responses cached by SHA-256 of the prompt + model + temperature. Cache is invalidated automatically when prompts change (because the hash changes).

**Consequences:**
- Positive: prompt iteration is free and instant; no accidental API usage during dev.
- Negative: stale cache can mask issues (mitigated: cache is disabled outside `--dry-run`; CI never reads it).

---

### ADR-007: Multi-tier audience with audience-aware composer
**Status:** Superseded by ADR-008

**Context:** Stakeholder consultation v2 surfaced that the two subscriber personas pull the composer in opposite directions: the research-aware engineer wants richer methodology + production-reality framings; the non-coder knowledge worker wants plain language and explicit "can I try this without code?" indicators. Sitting silently in the middle left the audience ambiguous; either explicit single-tier scope or explicit multi-tier serving were both viable.

**Decision (now superseded):** Multi-tier audience. Both subscriber profiles in scope; `Item` model carries `item_kind`, `maturity`, and `access` to serve both from one pipeline.

**Why superseded:** Author elected to narrow the audience to research-aware engineers only (PRD v0.4.0). The non-coder Practitioner persona was archived. The complexity of audience-aware composition was no longer earning its keep when only one tier was being served. See ADR-008 for the replacement decision.

---

### ADR-008: Narrow audience to research-aware engineer (single tier)
**Status:** Accepted

**Context:** PRD v0.3.0 declared multi-tier audience (engineers + non-coders) and added `access` to the `Item` model to serve the non-coder reader (see ADR-007). Subsequent product reflection narrowed the audience: the Practitioner persona was archived; only the Researcher Subscriber remains in scope. Maintaining audience-aware composer logic for a single audience is dead weight.

**Decision:** Single-tier audience — research-aware engineer who reads papers and ships LLM-backed features. Composer is designed for that one reader. Drop the `access` field from `Item`. Keep `item_kind` (still useful for differentiated ranking and framing across paper / blog / repo). Keep `maturity` (research-aware engineers care about shipping evidence). Trim `item_kind` enum: drop `consumer_product` since no consumer-facing source is planned.

**Consequences:**
- Positive: composer prompts are simpler (3 `item_kind` × 1 reader-tier framings instead of 4 × 2 = 8). PRD §2 has a sharp, defensible audience scope. Operational cost stays at ~1.0x what was first costed.
- Negative: if a non-coder reader audience is reintroduced later, ADR-007 will need to be reinstated (or replaced again) and the `access` field re-added. Archived persona file is preserved to make that path cheap.
- Future: if subscriber feedback suggests a meaningfully different audience is reading the issues, revisit. The data model addition for `access` is small enough that resurrecting it later is a 30-minute change, not an architectural overhaul.

---

### ADR-006: uv + ruff + pyright as the tooling baseline
**Status:** Accepted

**Context:** Python tooling has stabilised around a new generation: uv (resolver/env), ruff (lint+format), pyright (types). Alternatives are pip+poetry (slower), flake8+isort+black (3 tools where 1 suffices), mypy (slower, weaker inference).

**Decision:** uv for env/deps, ruff for lint+format, pyright for type checking.

**Consequences:**
- Positive: one fast resolver, one fast linter, one fast type checker. Less config sprawl.
- Negative: ruff and pyright are newer; small risk of behavioural surprises. Mitigation: lock versions in `uv.lock` and `pyproject.toml`.

---

## 12. Open Technical Questions

_None._ All technical decisions required to start implementation are resolved here or in the PRD (v0.4.0 / Ready with zero open questions).

---

## 13. Implementation Constraints

### Must Have
- Python 3.11+ (no earlier version).
- All third-party network calls go through tenacity-wrapped clients.
- Token budget enforcement runs *before* the compose step, not after.
- `logs/sends.jsonl` is the sole source of truth for idempotency.
- No secrets in the repo; only in GitHub Secrets.
- The send workflow runs *only* on merged PRs to `main`.

### Won't Have (This Version)
- Database (SQLite or otherwise).
- Subscriber signup / unsubscribe API (static config file is intentional per PRD).
- Reddit ingestion (PRD-decided drop).
- Real-time / event-driven sends (cron-only).
- Multi-tenant support (this is one author's newsletter).
- Per-subscriber personalisation.
- A staging environment (PR-as-draft replaces it).
- HTML email frameworks beyond a plain Jinja2 template (revisit if rendering complaints arise).

---

## Changelog

| Date | Version | Changes |
|------|---------|---------|
| 2026-05-19 | 0.1.0 | Initial TRD created via `/sdlc-studio trd create`. Six ADRs accepted. Builds on PRD v0.2.0. |
| 2026-05-19 | 0.2.0 | Tracks PRD v0.3.0. `Item` model extended with `item_kind`, `maturity`, `access` fields. GitHub adapter `raw` payload now specified (`stars`, `last_commit_at`, `has_recent_release`, `hosted_demo_url`). ADR-007 added: multi-tier audience with audience-aware composer. |
| 2026-05-19 | 0.3.0 | Tracks PRD v0.4.0. Audience narrowed to single tier (research-aware engineer). `access` field removed from `Item`. `item_kind` enum trimmed to `paper \| blog_post \| repo`. ADR-007 marked **Superseded**; ADR-008 accepted (narrow audience to single tier). `maturity` and GitHub shipping signals retained — they serve the remaining Researcher audience's "has anyone shipped this?" concern. |
| 2026-05-19 | 0.3.1 | Unified `/sdlc-studio review` pass: corrected §12 stale PRD version reference (v0.2.0 → v0.4.0). TRD status remains Draft pending explicit promotion to Ready (flagged for user — TSD and all 4 test specs already consume TRD as locked v0.3.0). |
| 2026-05-19 | 0.3.2 | Focused `/sdlc-studio trd review` pass: (a) added missing components `techletter.audit` and `techletter.cache` to §3 (defined by US0013 and US0014, validated by TS0003 TC0141–TC0166); (b) added 4 missing data models to §6 — `RankedClusters` (US0008), `DeepDive` (US0009), `QuickMention` (US0011), `SendReport` (US0018) — bringing the §6 catalogue from 4 to 8 models and matching the storyfile schemas; (c) bumped PRD reference from v0.4.0 → v0.4.1. **Status promoted Draft → Ready.** ADR ordering anomaly (ADR-006 sits after 007/008) noted but not reordered — cosmetic, deferred. |
