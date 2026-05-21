# US0023: Sidecar JSON persistence for `RenderedIssue` structure

> **Status:** Ready
> **Epic:** [EP0005: Common HTML Rendering (Web + Email)](../epics/EP0005-common-html-rendering.md)
> **Change Request:** [CR-0001](../change-requests/CR0001-common-html-rendering.md) (Item 1)
> **Owner:** HYL
> **Reviewer:** HYL
> **Created:** 2026-05-21
> **Promoted to Ready:** 2026-05-21 (RV0001 — F-1 resolved)

## User Story

**As** the renderer layer (and ultimately the Researcher Subscriber)
**I want** structured `DeepDive` / `QuickMention` data to survive the `draft → PR-merge → send` file boundary
**So that** channel adapters can render typeset HTML from structure instead of regex-parsing the Markdown body string.

## Context

### Persona Reference
**Researcher Subscriber** — indirect beneficiary. They feel this story as "the next email actually looks like a newsletter".
**HYL** — direct beneficiary. Without this story, every downstream renderer is forced into a Markdown-regex pipeline.

### Background
Today, `assemble_issue` produces structured `DeepDive` / `QuickMention` lists, then flattens them into `body_md`. `draft` writes only the `.md` to `drafts/<issue_id>.md` (`techletter/orchestration/cli.py:293-294`). `send` reads the `.md` and builds `RenderedIssue(body_md=text, ...)` with **empty** `deep_dives` / `quick_mentions` (`cli.py:215-220`). Every HTML-bearing channel adapter is therefore forced to re-parse Markdown with regex. The renderer work in US0024–US0027 needs the original structure — this story is the structural prerequisite.

---

## Inherited Constraints

| Source | Type | Constraint | AC Implication |
|--------|------|------------|----------------|
| EP0003 | Idempotency | `content_sha256` is the idempotency key; computed from `body_md` | Sidecar JSON MUST NOT participate in the hash |
| EP0002 | Models | `DeepDive` and `QuickMention` are pydantic frozen models | Sidecar reuses them via `model_dump_json` / `model_validate_json` |
| EP0003 | Draft-as-PR | Reviewer reads `.md` on GitHub | `.json` ships alongside but should not pollute diff (gitattributes) |
| CR-0001 | Schema | Sidecar schema is forward-compatible (will evolve in CR-0002+) | Top-level `version` field; unknown keys ignored on load |

---

## Acceptance Criteria

### AC1: `IssueStructure` pydantic model
- **Given** the module `techletter.compose.issue`
- **When** an engineer imports `from techletter.compose.issue import IssueStructure`
- **Then** `IssueStructure` is a frozen pydantic model with fields:
  - `version: int` (defaults to `1`)
  - `issue_id: str`
  - `issue_date: datetime`
  - `body_md: str` (mirror of the `.md` content for cross-check)
  - `deep_dives: list[DeepDive]`
  - `quick_mentions: list[QuickMention]`
  - `meta: dict[str, Any]`
  - `content_sha256: str`
- **And** `extra="forbid"` is set (typos in sidecar JSON fail loud)

### AC2: `RenderedIssue.to_sidecar_json()` round-trips
- **Given** a `RenderedIssue` with non-empty `deep_dives` and `quick_mentions`
- **When** `json_str = issue.to_sidecar_json()` then `restored = RenderedIssue.from_sidecar_json(json_str, body_md=issue.body_md)`
- **Then** `restored.deep_dives == issue.deep_dives` and `restored.quick_mentions == issue.quick_mentions`
- **And** `restored.content_sha256 == issue.content_sha256`
- **And** `restored.body_md == issue.body_md`

### AC3: `draft` writes both `.md` and `.json`
- **Given** `uv run techletter draft --output-dir drafts/`
- **When** the pipeline succeeds
- **Then** **both** `drafts/<issue_id>.md` and `drafts/<issue_id>.json` exist
- **And** the `.json` parses as a valid `IssueStructure` and its `body_md` matches the `.md` file bytes
- **And** the `.json` is reported in stdout (e.g., `wrote sidecar: drafts/<issue_id>.json`)

### AC4: `send` loads sidecar automatically when present
- **Given** a `drafts/<issue_id>.md` + `drafts/<issue_id>.json` pair
- **When** `uv run techletter send --draft-path drafts/<issue_id>.md ...` runs
- **Then** the constructed `RenderedIssue` has non-empty `deep_dives` and `quick_mentions` matching the sidecar
- **And** stdout includes a line confirming sidecar load (e.g., `send: loaded sidecar drafts/<issue_id>.json (3 deep dives, 10 quick mentions)`)

### AC5: Missing sidecar is a warning, not an error
- **Given** a `drafts/<issue_id>.md` with **no** matching `.json` (legacy draft)
- **When** `send` runs
- **Then** a single WARNING is emitted (`send: no sidecar found for <issue_id>; falling back to body_md only`)
- **And** the `RenderedIssue` is constructed with `deep_dives=[]`, `quick_mentions=[]`
- **And** exit code is `0` (no failure)

### AC6: `body_md` mismatch between `.md` and sidecar is a warning, `.md` wins
- **Given** `.md` body and sidecar `body_md` differ (e.g., reviewer fixed a typo in the `.md` during PR review)
- **When** `send` runs
- **Then** a single WARNING is emitted (`send: sidecar body_md does not match .md file; using .md (sidecar may be stale)`)
- **And** `RenderedIssue.body_md` is the `.md` content (authoritative)
- **And** structured data (`deep_dives`/`quick_mentions`) still loaded from sidecar (best-effort; the reviewer's typo fix is text-only)

### AC7: `content_sha256` value is preserved from EP0004
- **Given** the same `body_md` input across EP0004 and EP0005
- **When** `content_hash(body_md)` is called
- **Then** the hex digest is byte-identical to the EP0004 implementation (regression test pins this against a frozen fixture)

### AC8: `.gitattributes` marks sidecar as generated
- **Given** the repository root `.gitattributes`
- **When** a developer views a draft PR with both `.md` and `.json` changed
- **Then** the GitHub UI collapses the `.json` diff by default (`drafts/*.json linguist-generated`)
- **And** the file can still be expanded on demand

---

## Scope

### In Scope
- `IssueStructure` pydantic model in `techletter/compose/issue.py`.
- `RenderedIssue.to_sidecar_json()` and `RenderedIssue.from_sidecar_json(json_str, body_md=...)` helpers.
- `draft` command writes the sidecar.
- `send` command auto-loads the sidecar by replacing the `.md` extension with `.json`.
- Mismatched / missing sidecar warning logic.
- `.gitattributes` entry for `drafts/*.json linguist-generated`.

### Out of Scope
- Schema versioning beyond `version: 1` (forward-compatibility is structural, not feature-rich yet).
- Encrypting / signing the sidecar (we're a public-by-URL system, not a secret store).
- A `--no-sidecar` opt-out flag (not needed in v1.1).
- Migrating existing `drafts/.local/*` legacy drafts to add sidecars (fallback handles them).

---

## Technical Notes

- Sidecar path derivation: replace trailing `.md` with `.json`. If `--draft-path` is something exotic, fall back to `Path(draft_path).with_suffix('.json')`.
- `to_sidecar_json()` should emit stable JSON: `indent=2`, `sort_keys=True` on the `meta` dict if it isn't already deterministically ordered, ISO-8601 datetimes (`Z` suffix to match `assemble_issue`).
- `from_sidecar_json` takes `body_md` explicitly (the caller already has it from the `.md` file). This makes the cross-check in AC6 explicit and testable.
- The warning emitter is `click.echo(..., err=True)` for consistency with existing `send` error path.

### API Contracts
- `class IssueStructure(BaseModel)` — frozen, extra=forbid.
- `RenderedIssue.to_sidecar_json(self) -> str` — instance method.
- `RenderedIssue.from_sidecar_json(json_str: str, *, body_md: str) -> RenderedIssue` — classmethod.

### Data Requirements
- Reads/writes `drafts/<issue_id>.json` next to `.md`.
- `.gitattributes` updated.

---

## Edge Cases & Error Handling

| Scenario | Expected Behaviour |
|----------|-------------------|
| `.json` is malformed JSON | WARNING, fall back to `body_md` only; do NOT crash |
| `.json` has unknown fields (forward-compatible) | Pydantic `extra="forbid"` strict — schema bump required. For v1, fail loud with a clear error message naming the offending field. |
| `.json` `version` is greater than current | Treat as unknown — WARNING, fall back to `body_md` only (don't risk misinterpreting) |
| `.md` is empty | `body_md` is empty; sidecar `body_md` matches; warning only if `deep_dives` is non-empty |
| `.json` exists but no `.md` | `send --draft-path` errors out as today (file not found); not this story's concern |
| Reviewer edits `.json` instead of `.md` | Cross-check detects mismatch; `.md` wins. Reviewer told to edit `.md` only (documented in CR-0001 risks) |
| Sidecar file is huge (e.g., 100 deep dives) | Not realistic per EP0002 constraints (2–5 deep dives), so no soft limit |

---

## Test Scenarios

- [ ] `IssueStructure.model_dump_json` followed by `model_validate_json` round-trips identically.
- [ ] `RenderedIssue.to_sidecar_json()` → `from_sidecar_json(json_str, body_md=...)` yields equal `RenderedIssue` (all fields).
- [ ] `draft` command writes both `.md` and `.json` in a temp output dir; both parse.
- [ ] `send` with matching pair loads structured data; `deep_dives` and `quick_mentions` non-empty.
- [ ] `send` with `.md` only emits the expected warning and exits 0 with empty structure.
- [ ] `send` with mismatched `body_md` between files emits warning and uses `.md` text.
- [ ] `content_sha256` matches a frozen golden hash across EP0004→EP0005 (regression).
- [ ] `.gitattributes` contains the `drafts/*.json linguist-generated` line.
- [ ] Malformed `.json` → WARNING + fallback (no exception bubbles up).

---

## Dependencies

### Story Dependencies

None internal to EP0005. Depends on existing EP0002 (`DeepDive`/`QuickMention`) and EP0003 (CLI structure).

### External Dependencies

None new. Uses pydantic already in the project.

---

## Estimation

**Story Points:** 4
**Complexity:** Low–Medium. The model + helpers are mechanical, but the cross-check semantics (AC6) and the mismatch warning path need care. The regression test for `content_sha256` (AC7) is the most important guard — get it green before doing anything else.

---

## Open Questions

- [ ] Should `meta` in `IssueStructure` be a strictly-typed `IssueMeta` model (vs `dict[str, Any]`)? Lean dict for now — too many emerging keys across CR-0001/CR-0002 to lock down yet.

_Resolved during RV0001 (2026-05-21): "sidecar `.json` as `linguist-generated`" decision committed — AC8 is binding; no further deliberation needed._

---

## Revision History

| Date | Author | Change |
|------|--------|--------|
| 2026-05-21 | HYL | Story created from CR-0001 (Item 1) via `/sdlc-studio cr action`. |
