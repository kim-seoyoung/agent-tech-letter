# Tech-Letter for HYL

An automated weekly newsletter on LLM agents for research-aware engineers.
Built around a 3-stage pipeline (ingest → compose → deliver) that runs
on GitHub Actions every Monday, opens a draft PR for HYL's review, and
fans out on merge.

> **Status**: EP0001 (ingestion) + EP0002 (composition) + EP0003 (orchestration)
> complete · EP0004 (delivery) pending · 207+ tests passing
> Full spec set: [`sdlc-studio/`](sdlc-studio/) (PRD, TRD, TSD, 4 epics, 22 stories)

## Quickstart

```bash
# 1. Clone and install
git clone https://github.com/kim-seoyoung/agent-tech-letter
cd agent-tech-letter
uv sync --all-extras

# 2. Confirm everything works
uv run pytest -q                              # → 207/207 pass
uv run pyright techletter/ tests/             # → 0 errors
uv run ruff check . && uv run ruff format --check .

# 3. (optional) Set the LLM API key for live runs
export ANTHROPIC_API_KEY="sk-ant-..."

# 4. Dry-run the pipeline locally (writes to drafts/.local/, no PR opened)
uv run techletter dry-run --window-days 7
```

## CLI

The `techletter` command has three sub-commands, each mapped to a
GitHub Actions workflow.

```bash
# Local-only run with cache (for prompt iteration; no PR, no LLM tokens burned twice)
uv run techletter dry-run

# Full pipeline; writes to drafts/ (production: opens PR via draft.yml)
uv run techletter draft --window-days 7

# Send the merged draft to enabled channels (production: triggered by send.yml on merge)
uv run techletter send --issue issue-2026-05-20 --draft-path drafts/issue-2026-05-20.md
```

### Environment variables

| Variable             | Purpose                              | Default                |
| -------------------- | ------------------------------------ | ---------------------- |
| `ANTHROPIC_API_KEY`  | LLM API key (production only)        | unset → live runs fail |
| `LLM_BUDGET_TOKENS`  | Per-run token budget                 | 200000                 |
| `LLM_MODEL`          | Anthropic model id                   | claude-sonnet-4-6      |
| `CI` / `GITHUB_ACTIONS` | Hard-disable the dev cache       | (set by Actions)       |
| `SMTP_HOST` etc.     | Channel credentials (EP0004)         | (from GitHub Secrets)  |

## Dev loop

```bash
# 1. Edit a prompt under prompts/
$EDITOR prompts/cluster.md

# 2. Re-run locally with cache (fetch + compose; LLM may be re-called)
uv run techletter dry-run

# 3. Inspect the result
cat drafts/.local/issue-*.md

# 4. Once happy, open a PR. CI runs the full test suite.
git checkout -b prompt-tuning && git add prompts/ && git commit
git push -u origin prompt-tuning
gh pr create

# 5. After merge to main, the next scheduled run picks up the new prompt
```

The `.cache/` directory speeds up step 2 — re-running with the same
input produces the same output without spending LLM tokens. CI hard-
disables this cache (`CI=true` is set automatically by GitHub Actions)
so no stale cache reads can drift from production behaviour.

## Architecture

```text
                          GitHub Actions cron (Mon 00:00 UTC)
                                    │
                                    ▼
┌─────────────────┐    ┌───────────────────┐    ┌──────────────────┐
│  Source Layer   │    │   Composer Layer  │    │  Delivery Layer  │
│  (EP0001 done)  │    │   (EP0002 done)   │    │  (EP0004 ⏸)      │
│  arxiv + GitHub │ →  │  cluster → rank → │ →  │  Email + Slack + │
│  + RSS adapters │    │  compose (LLM)    │    │  Telegram        │
└─────────────────┘    └───────────────────┘    └──────────────────┘
                                    │
                                    ▼
                          PR opened on `draft/issue-YYYY-MM-DD`
                                    │
                          HYL reviews + merges
                                    │
                                    ▼
                          send.yml fires → fan out → commit sends.jsonl
```

## Project layout

```text
techletter/             # Production code
├── models/             # Item, Maturity (EP0001)
├── sources/            # arxiv, github, rss adapters + registry (EP0001)
├── config/             # sources.yaml schema + loader (EP0001)
├── llm/                # LlmClient + FakeLLMClient + prompt loader (EP0002)
├── pipeline/           # cluster, rank (EP0002)
├── compose/            # deep_dive, quick_mentions, issue assembly (EP0002)
├── audit.py            # logs/sends.jsonl + idempotency (EP0003)
├── cache.py            # FetchCache + LlmCache, CI-disabled (EP0003)
└── orchestration/      # CLI (EP0003)
prompts/                # First-draft prompt templates (iterate in PRs)
config/sources.yaml     # Source configuration (1-line feed adds)
.github/workflows/      # draft.yml (cron), send.yml (PR-merge trigger)
tests/                  # Unit + integration tests (207+ cases)
sdlc-studio/            # PRD, TRD, TSD, epics, stories, test specs
```

## Testing the foundation

```bash
# Full suite (~5 seconds)
uv run pytest -q

# Specific subsystem
uv run pytest tests/unit/sources/      # adapters
uv run pytest tests/unit/compose/      # composition + determinism
uv run pytest tests/unit/orchestration/ # CLI
uv run pytest tests/unit/workflows/    # YAML structural checks

# Coverage
uv run pytest --cov=techletter --cov-report=term-missing
```

## GitHub Pages setup (EP0006 — for `teaser_link` Telegram mode)

The Telegram adapter's `teaser_link` mode (default for new installs)
publishes each issue to a GitHub Pages site and sends a short Telegram
message with the URL. **The published pages are world-readable** on
GitHub Free + public-repo plans — the URL contains a 16-hex
`content_sha256` slug, but it is NOT authenticated. If your subscriber
list must be private, swap the publisher (see `Publisher` Protocol).

### First-time setup (one operator action)

1. **Create the `gh-pages` orphan branch:**

   ```bash
   git switch --orphan gh-pages
   git commit --allow-empty -m "init gh-pages"
   git push -u origin gh-pages
   git switch -                                 # back to your working branch
   ```

   > `git switch --orphan` already empties the index, so **no `git rm -rf .`
   > step is needed**. Files from your previous branch remain in the working
   > tree as untracked during this flow; `git commit --allow-empty` ignores
   > them (the new root commit on `gh-pages` has zero tracked files), and
   > `git switch -` reconciles them when you return.
   >
   > Older guides that include `git rm -rf .` were written for
   > `git checkout --orphan`, which leaves the index full of "to-be-deleted"
   > entries. With `git switch --orphan`, that step errors out
   > (`fatal: pathspec '.' did not match any files`) and is redundant.

2. **Enable Pages in the GitHub UI:** `Settings → Pages → Build and deployment →
   Source: gh-pages branch / root`.

3. **Verify the base URL resolves:** `https://<user>.github.io/<repo>/`
   (404 until the first publish, which is expected).

4. **Set runtime env vars** (or GitHub Actions Secrets for CI):
   - `TELEGRAM_BOT_TOKEN` — your bot's API token.
   - `GITHUB_TOKEN` — push credentials; locally an SSH key in `~/.ssh/` works.
   - `SMTP_HOST` / `SMTP_USER` / `SMTP_PASS` / `SMTP_FROM` if email is enabled.

5. **Update `config/channels.yaml`** to opt in:

   ```yaml
   publishers:
     github_pages:
       enabled: true
       repo_path: "."
       branch: "gh-pages"
       base_url: "https://<user>.github.io/<repo>"
       author_name: "tech-letter-bot"
       author_email: "bot@example.com"

   telegram:
     enabled: true
     mode: teaser_link        # or "inline_html" for the legacy split-message path
     publisher: github_pages
   ```

   Old `channels.yaml` files without these blocks load cleanly and
   default `telegram.mode` to `inline_html`, so the upgrade is opt-in.

### End-to-end smoke (HYL-runnable)

```bash
uv run techletter draft --output-dir drafts/                    # writes drafts/<id>.md + .json
# (merge PR or copy directly into your "approved" location)
uv run techletter send --issue <id> --draft-path drafts/<id>.md

# verify
grep published_url logs/sends.jsonl                              # latest line has the URL
open "$(jq -r 'select(.channel=="telegram") | .published_url' logs/sends.jsonl | tail -1)"
# then check your Telegram bot inbox: a single message with a preview card
```

### Audit log schema

`logs/sends.jsonl` is append-only; one record per `(issue_id, channel)`
send attempt. Fields:

| Field | Type | Notes |
|-------|------|-------|
| `timestamp` | ISO-8601 datetime | UTC |
| `issue_id` | string | e.g. `issue-2026-05-21` |
| `channel` | string | `email` / `slack` / `telegram` |
| `status` | enum | `ok` / `partial` / `failed` |
| `recipient_count` | int | per channel |
| `error` | string \| null | joined error messages on failure |
| `published_url` | **string \| null** | populated for publisher-backed sends (Telegram `teaser_link`); `null` otherwise |

## Caveats

- **First-draft prompts.** Every `prompts/*.md` was authored to satisfy
  structural tests (banned-word filter, JSON shape, byte determinism)
  but voice has NOT been tuned against real LLM output yet. HYL has
  merge authority on prompt content; iteration happens in subsequent PRs.

- **No live LLM call has happened in CI.** All tests use the
  `FakeLLMClient` fixture. To exercise the real Anthropic API locally:
  `ANTHROPIC_API_KEY=sk-ant-... uv run techletter dry-run`.

- **Telegram `teaser_link` AC9 manual smoke** is HYL-owned (US0032 AC7).
  Real `TELEGRAM_BOT_TOKEN` + real `gh-pages` branch + real subscriber
  `chat_id` are required to verify the preview card renders correctly.

## License

MIT
