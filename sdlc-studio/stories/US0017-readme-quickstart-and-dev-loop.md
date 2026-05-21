# US0017: README quickstart + dry-run developer loop docs

> **Status:** Done
> **Epic:** [EP0003: Orchestration & Developer Experience](../epics/EP0003-orchestration-and-dx.md)
> **Owner:** HYL
> **Reviewer:** HYL
> **Created:** 2026-05-19

## User Story

**As** HYL (Author/Editor)
**I want** a README that gets a new developer (or a future-me who has forgotten) from "fresh clone" to "running `techletter dry-run` locally in under 10 minutes"
**So that** I (or any collaborator) can iterate on prompts, fix bugs, or onboard a future contributor without re-deriving setup steps from scratch.

## Context

### Persona Reference
**HYL (Author/Editor)** — values that "boring is good." A clear README is part of the boring-but-essential infrastructure that keeps this project low-friction.
[Persona details](../personas/stakeholders/users/hyl-author.md)

### Background
EP0001–EP0004 deliver the working system. EP0003 finishes the loop with developer experience. The README is the doc that makes the entire pipeline accessible to someone who arrived this morning.

---

## Inherited Constraints

| Source | Type | Constraint | AC Implication |
|--------|------|------------|----------------|
| Epic | Dev experience | Local dry-run loop must be discoverable from README | README has a dedicated "Local development" section |
| TRD | Tooling | uv / ruff / pyright | README documents these as the toolchain |
| PRD | Secrets | All secrets via GitHub Secrets | README explains which secrets are needed and where to set them |

---

## Acceptance Criteria

### AC1: README has the right sections
- **Given** the file `README.md` exists at the repo root
- **When** a reader skims it
- **Then** it contains, in order, sections titled:
  1. What this is — one paragraph project description
  2. How it works — short architecture overview with link to TRD
  3. Quickstart (local) — clone → install → dry-run
  4. Configuration — sources, subscribers, channels
  5. Secrets — list of required and optional secrets, where to set them
  6. Running the workflows — how to trigger draft / what merging does
  7. Development — uv / ruff / pyright commands, testing, prompt iteration
  8. Project structure — short tree of key directories
  9. Links — to PRD, TRD, epics, stories indexes

### AC2: Quickstart works on a fresh clone
- **Given** a fresh git clone (or zip extract) of the repo
- **When** a developer follows the Quickstart steps as written
- **Then** the steps are:
  1. Install `uv` (one curl command, link to docs)
  2. `uv sync`
  3. Copy `.env.example` to `.env` and fill in `ANTHROPIC_API_KEY`
  4. `uv run techletter dry-run`
  5. Open the resulting markdown in `drafts/.local/`
- **And** the steps complete on a clean Ubuntu/macOS machine in under 10 minutes (network-dependent).

### AC3: Secrets section is unambiguous
- **Given** the Secrets section
- **When** a reader looks for a specific secret
- **Then** the section presents a table:
  - Secret name (e.g., `ANTHROPIC_API_KEY`)
  - Required / optional
  - Used by (which workflow / command)
  - Where to get it (e.g., "anthropic.com → console → API keys")
  - Where to set it (`Settings → Secrets and variables → Actions` for CI; `.env` for local)
- **And** the table lists at minimum: `ANTHROPIC_API_KEY`, `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS`, `SMTP_FROM`, `SLACK_WEBHOOK_URLS`, `TELEGRAM_BOT_TOKEN`, `GITHUB_TOKEN`

### AC4: Development section covers prompt iteration loop
- **Given** the Development section
- **When** a reader wants to iterate on a prompt
- **Then** the section explains:
  - Prompts live in `prompts/*.md`.
  - To iterate: edit a prompt, run `uv run techletter dry-run` (cached fetches, no LLM cost for unchanged prompts).
  - Cache lives in `.cache/` (gitignored); `--clear-cache` resets it.
  - Run tests with `uv run pytest`.
  - Run linters with `uv run ruff check . && uv run pyright`.

### AC5: Project structure is current
- **Given** the project structure section
- **When** the reader looks at the tree
- **Then** it accurately reflects the actual directories:
  ```
  techletter/         # the Python package
    sources/          # adapters (arxiv, github, rss)
    pipeline/         # cluster, rank, compose, assemble
    delivery/         # channel adapters (email, slack, telegram)
    audit.py          # sends.jsonl model + idempotency
    cache.py          # dev-only fetch + LLM cache
    cli.py            # techletter entry point
  config/             # sources.yaml, subscribers.yaml, channels.yaml
  prompts/            # *.md prompt templates
  templates/          # email.html.j2 and similar
  drafts/             # generated drafts (PRs branch from here)
  logs/               # sends.jsonl
  tests/              # pytest tests
  sdlc-studio/        # PRD/TRD/personas/epics/stories
  .github/workflows/  # draft.yml, send.yml
  ```

### AC6: Cross-links to SDLC artefacts
- **Given** the Links section
- **When** a reader wants to dig deeper
- **Then** the section links to:
  - `sdlc-studio/prd.md`
  - `sdlc-studio/trd.md`
  - `sdlc-studio/personas/index.md`
  - `sdlc-studio/epics/_index.md`
  - `sdlc-studio/stories/_index.md`

### AC7: `.env.example` exists
- **Given** the repo's root
- **When** a developer copies `.env.example` to `.env`
- **Then** the example file lists all required + optional env vars with placeholder values and a one-line comment per entry
- **And** `.env` is in `.gitignore`

---

## Scope

### In Scope
- `README.md` at repo root with the sections specified.
- `.env.example` at repo root with placeholder values.
- `.gitignore` entry for `.env`.
- A brief CONTRIBUTING.md is optional — not required for v1; the README's Development section covers it.

### Out of Scope
- A full GitHub Pages doc site — overkill for a personal project.
- Translated docs — repo is English-only in v1.
- Tutorial-style walkthrough (e.g., "build your own newsletter") — README is a quickstart, not a tutorial.
- Architecture diagrams (Mermaid C4) in README — the TRD has them; README links to the TRD.

---

## Technical Notes

- The README is reviewed at PR time for accuracy whenever a directory or command changes — soft gate, not enforced by CI.
- The "under 10 minutes" claim is rough; we don't measure it in CI. It's the spirit, not a contract.

### API Contracts
N/A — documentation only.

### Data Requirements
N/A.

---

## Edge Cases & Error Handling

| Scenario | Expected Behaviour |
|----------|-------------------|
| Developer skips `uv sync` and tries to run | `uv run techletter` fails with a clear message; README quickstart explicitly orders the steps |
| `.env` exists but is missing `ANTHROPIC_API_KEY` | CLI exits 4 with "ANTHROPIC_API_KEY not set"; documented as a common error in README "Troubleshooting" subsection |
| Developer has Python 3.10 instead of 3.11+ | `uv sync` reports the version mismatch; README states minimum version |
| `.env` accidentally committed | `.gitignore` prevents it; if it happens anyway, document a `git rm --cached .env` recipe in README |
| Project structure changes after README is written | PR review catches the drift; reviewer updates the README in the same PR |
| Links to SDLC artefacts break (file moves) | PR review catches; SDLC paths are stable so this is rare |
| New developer is on Windows | Note: project supports macOS/Linux; Windows requires WSL2; documented as a known limitation |
| Quickstart steps depend on `gh` CLI for some local dev | `gh` is *not* required for local dry-run; only required if a developer wants to test PR creation locally |

---

## Test Scenarios

- [ ] Markdown lints clean (no broken syntax) via a markdownlint pre-commit hook (optional).
- [ ] All section headers exist (verified by a grep-style unit-test asserting `## What this is`, `## Quickstart`, etc.).
- [ ] All listed secrets are referenced somewhere in the code or workflows (verified by a grep test).
- [ ] All listed files in the Project Structure section exist on disk (verified by a tiny doctor script).
- [ ] All cross-links resolve (verified by `markdown-link-check` or equivalent).
- [ ] Manual: fresh-clone a checkout of the repo; follow Quickstart; reach a successful `dry-run` output.
- [ ] `.env.example` includes all required secrets from the AC3 table.

---

## Dependencies

### Story Dependencies

| Story | Type | What's Needed | Status |
|-------|------|---------------|--------|
| [US0012](US0012-techletter-cli-scaffolding.md) | Service | CLI commands documented in README | Draft |
| [US0014](US0014-cache-helpers.md) | Service | Cache behaviour documented | Draft |
| [US0015](US0015-draft-workflow-yaml.md) | Service | Workflow trigger documented | Draft |
| [US0016](US0016-send-workflow-yaml.md) | Service | Workflow trigger documented | Draft |

This story should be the last one in EP0003 — it documents what the others built.

### External Dependencies
None.

---

## Estimation

**Story Points:** 2
**Complexity:** Low. The work is writing prose, not designing systems. Time-sink: keeping it accurate as the rest of the system changes.

---

## Open Questions

_None._

---

## Revision History

| Date | Author | Change |
|------|--------|--------|
| 2026-05-19 | HYL | Initial story created from EP0003. |
