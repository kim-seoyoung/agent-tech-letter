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

## Caveats

- **First-draft prompts.** Every `prompts/*.md` was authored to satisfy
  structural tests (banned-word filter, JSON shape, byte determinism)
  but voice has NOT been tuned against real LLM output yet. HYL has
  merge authority on prompt content; iteration happens in subsequent PRs.

- **No live LLM call has happened in CI.** All tests use the
  `FakeLLMClient` fixture. To exercise the real Anthropic API locally:
  `ANTHROPIC_API_KEY=sk-ant-... uv run techletter dry-run`.

- **Delivery layer (EP0004) not yet implemented.** The `send` command
  currently exits 0 with "no channels registered". The CLI surface is
  stable; concrete channel adapters arrive in the next epic.

## License

MIT
