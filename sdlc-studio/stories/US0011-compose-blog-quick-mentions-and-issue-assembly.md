# US0011: Compose `blog_post` deep dives + quick mentions + `RenderedIssue` assembly

> **Status:** Done
> **Epic:** [EP0002: Composition Pipeline](../epics/EP0002-composition-pipeline.md)
> **Owner:** HYL
> **Reviewer:** HYL
> **Created:** 2026-05-19

## User Story

**As** HYL (Author/Editor)
**I want** a blog-specific deep-dive compose prompt, a batch quick-mention composer, and a `RenderedIssue` assembler that ties everything from EP0002 together into one canonical Markdown issue with front matter
**So that** the pipeline produces a single, ready-to-ship draft that EP0003 can hand off as a PR.

## Context

### Persona Reference
**HYL (Author/Editor)** — the audience-of-one for the assembled `RenderedIssue` (HYL is the first reader, at PR time). The assembly step is what turns a pile of `DeepDive` objects into the thing HYL actually approves.
[Persona details](../personas/stakeholders/users/hyl-author.md)

### Background
This is the capstone story of EP0002. It does three related things — composing blog deep dives, batch-composing the 10 quick mentions, and assembling the final `RenderedIssue` — because each depends on the previous and splitting further would create cross-story coupling. After this story, EP0002 is complete and EP0003 can consume `RenderedIssue` as a stable interface.

---

## Inherited Constraints

| Source | Type | Constraint | AC Implication |
|--------|------|------------|----------------|
| Epic | Framing | Blog deep dives: "what's being argued" + cross-source corroboration + author authority signal | Blog compose prompt structure |
| Epic | Output shape | 10 quick mentions per issue | Quick-mention step produces exactly 10 (or fewer if rank step provided fewer) |
| Epic | Output shape | 3 deep dives total (flex 2–5) across all `item_kind`s | Assembly enforces the count and orders them |
| PRD | Per-item rendering | Each item displays its `item_kind` and `maturity` (when known) | Assembly renders item-kind/maturity indicators for both deep dives and quick mentions |
| PRD | Front matter | `RenderedIssue` has `issue_id`, date, token usage, source counts | Assembly populates these from `LlmClient.usage_report()` and source-count aggregation |
| PRD | Output format | Markdown canonical; convertible to HTML and plain text | Assembly outputs canonical Markdown; HTML/plaintext conversion lives in EP0004 |

---

## Acceptance Criteria

### AC1: Compose function for blog kind is defined
- **Given** the module `techletter.pipeline.compose` exists
- **When** an engineer imports `from techletter.pipeline.compose import compose_blog_deep_dive`
- **Then** the signature matches the existing paper/repo functions: `compose_blog_deep_dive(cluster: Cluster, rationale: str, llm: LlmClient) -> DeepDive`
- **And** returns a `DeepDive` with `item_kind = "blog_post"`, body covering "what's being argued" + cross-source corroboration + author authority signal

### AC2: Blog compose prompt lives in `prompts/compose-blog.md`
- **Given** the prompt file
- **When** the compose function loads it
- **Then** the prompt template includes:
  - System role: writing for research-aware engineer audience.
  - Same anti-hype word list as US0009 / US0010 (shared constant).
  - Three-section structure: "What's being argued", "Cross-source corroboration", "Author authority signal".
  - Instruction: if author authority cannot be determined from context, write "author authority not assessed" rather than fabricating.

### AC3: Quick-mention batch composition is defined
- **Given** the function `compose_quick_mentions(clusters: list[Cluster], llm: LlmClient) -> list[QuickMention]` exists
- **When** called with up to 10 clusters from the rank step's `quick` selection
- **Then** exactly one LLM call produces all 10 quick mentions (batch composition, not 10 separate calls)
- **And** each `QuickMention` has: `topic: str`, `one_liner: str` (≤200 chars), `url: str` (the primary item's URL), `item_kind`, `maturity: str | None`
- **And** the prompt explicitly bounds each one-liner to one sentence with no more than 200 chars

### AC4: `RenderedIssue` model + assembly function defined
- **Given** the module `techletter.pipeline.assemble` exists
- **When** an engineer imports `from techletter.pipeline.assemble import RenderedIssue, assemble_issue`
- **Then** `RenderedIssue` is a pydantic model with fields per TRD §6:
  - `issue_id: str` (format `YYYY-MM-DD`)
  - `markdown: str` — the canonical issue body
  - `html: str | None` (populated by EP0004; can be `None` at assembly time — assembly doesn't render HTML)
  - `plaintext: str | None` (same — EP0004 owns the rendering)
  - `meta: dict` — front matter (token usage, source counts, deep/quick counts, generation date)
- **And** `assemble_issue(deep_dives: list[DeepDive], quick_mentions: list[QuickMention], usage_report: dict, source_counts: dict[str, int]) -> RenderedIssue` is the public function

### AC5: Assembled Markdown is well-formed
- **Given** 3 deep dives (one paper, one repo, one blog) and 10 quick mentions
- **When** `assemble_issue(...)` runs
- **Then** the returned `markdown` contains, in order:
  1. Markdown front matter block (YAML between `---` fences) with `issue_id`, `date`, `tokens_used`, `model`, `sources` keys.
  2. Issue title (e.g., `# Tech-Letter for HYL — Issue {issue_id}`).
  3. A "Deep dives" section with each `DeepDive.body_markdown` rendered as `## {topic}` followed by an `item_kind` + `maturity` indicator line, then the body, then the citations list.
  4. An "Also worth noting" section with each quick mention as a single bullet: `- [{item_kind} · {maturity}] **{topic}** — {one_liner} [link]({url})`.
  5. Issue footer with token usage summary and a "this was generated by Tech-Letter for HYL" attribution line.

### AC6: Issue id and date are recorded
- **Given** the assembler is called on date `2026-05-19`
- **When** the `RenderedIssue` is built
- **Then** `issue_id == "2026-05-19"` (or, more generally, today's date in UTC formatted as ISO date)
- **And** the front matter contains the same value

### AC7: Item-kind + maturity indicators rendered for every item
- **Given** a mix of deep dives and quick mentions
- **When** the markdown is rendered
- **Then** every item (deep or quick) shows its `item_kind` (`paper` / `blog_post` / `repo`) and, when known, its `maturity` (`experimental` / `beta` / `production-ready`)
- **And** unknown maturity is rendered as nothing (not the literal word "unknown") — only show signal that exists

### AC8: Deep-dive count flexes 2–5 honestly
- **Given** the rank step provides 4 selected deep-dive clusters
- **When** assembly runs
- **Then** the issue contains 4 deep dives (not padded to 3, not truncated to 3)
- **And** when fewer than 2 deep dives are provided, the assembler logs a WARN ("quiet week — only N deep dives") but still produces an issue

### AC9: Quick mention count tolerates < 10
- **Given** the rank step provided 6 quick mentions (light week)
- **When** assembly runs
- **Then** the issue contains 6 quick mentions
- **And** the section heading remains "Also worth noting" (does not falsely advertise "10 quick mentions")

---

## Scope

### In Scope
- `compose_blog_deep_dive` function + `prompts/compose-blog.md`.
- `compose_quick_mentions` function + `prompts/compose-quick-mentions.md`.
- `QuickMention` pydantic model.
- `assemble_issue` function + `RenderedIssue` model in `techletter/pipeline/assemble.py`.
- Markdown rendering: deep-dive section, quick-mentions section, front matter, footer.
- Unit tests for: blog compose (fake LLM), quick-mention compose (fake LLM batch response), assembly (with fixture inputs).

### Out of Scope
- HTML rendering (EP0004 — email).
- Plain-text rendering (EP0004 — Slack/Telegram fallback).
- Channel-specific splitting / truncation (EP0004).
- A composition orchestrator that calls all four compose functions in order — that's a thin wrapper that lives most naturally in EP0003's `techletter draft` CLI entry point.

---

## Technical Notes

- `compose_blog_deep_dive` mirrors the structure of US0009/US0010: same signature, same shared types, different prompt. Implementation is mostly the prompt file plus the function body.
- `compose_quick_mentions` is the only batch-prompted compose step. It receives a compact representation of each quick cluster (topic + primary item title + URL + `item_kind` + `maturity`) and returns 10 one-liners in a single response. Token-efficient.
- `assemble_issue` is pure function — no LLM calls. Renders markdown deterministically. This is testable without any LLM in the loop.
- Front matter format is YAML between `---` fences, suitable for GitHub-flavoured Markdown rendering.
- Issue title is templatic: `# Tech-Letter for HYL — Issue {issue_id}`. Title format is a single constant; if HYL wants to rename, one-line change.

### API Contracts
- `compose_blog_deep_dive(cluster, rationale, llm) -> DeepDive`
- `compose_quick_mentions(clusters, llm) -> list[QuickMention]`
- `assemble_issue(deep_dives, quick_mentions, usage_report, source_counts) -> RenderedIssue`
- `QuickMention`, `RenderedIssue` pydantic models.

### Data Requirements
None persistent.

---

## Edge Cases & Error Handling

| Scenario | Expected Behaviour |
|----------|-------------------|
| Zero deep dives provided | WARN logged; `RenderedIssue` produced with empty "Deep dives" section; assembler does not raise |
| Zero quick mentions provided | "Also worth noting" section is omitted entirely from output (cleaner than empty section) |
| `compose_quick_mentions` LLM returns 7 one-liners when 10 clusters were sent | Returned list has 7; assembler renders 7; WARN logged about quick-mention shortfall |
| `compose_quick_mentions` returns more than requested (LLM hallucinates an extra) | Truncate to N input clusters; log WARN |
| One quick-mention one-liner exceeds 200 chars | Truncate to 200 chars + ellipsis; log WARN |
| Blog cluster has only one blog item (no cross-source corroboration possible) | Compose body explicitly says "no cross-source corroboration this week"; assembler renders as-is |
| `maturity` value is unknown for a quick mention | Render as `[blog_post]` (no maturity marker) — never show literal "unknown" |
| `issue_id` collides with a previous issue (same UTC date triggered twice) | Assembler doesn't check uniqueness — idempotency lives in `logs/sends.jsonl` per EP0003. Assembler just uses today's date. |
| Front matter values contain markdown-special characters | YAML-encode them properly; assembler uses `yaml.safe_dump` for the front matter block |
| Deep dive's `body_markdown` contains a YAML fence (`---`) | Escape or reflow; the front matter parser must be unambiguous. Test with a fixture that includes a `---` in a deep dive body. |
| Quick mention's `url` is empty | Skip that quick mention; log WARN |
| Type check: all functions and models pass pyright | Required for merge |
| `assemble_issue` called twice with the same inputs | Output is deterministic (same markdown bytes); enables idempotency testing in EP0003 |

---

## Test Scenarios

- [ ] Blog compose: fake LLM produces 3-section response → `DeepDive` with `item_kind == "blog_post"`.
- [ ] Quick-mention compose: 10 input clusters → single LLM call → 10 `QuickMention`s.
- [ ] Quick-mention compose: 6 input clusters → 6 `QuickMention`s, single LLM call.
- [ ] Quick-mention compose: LLM returns 7 from 10 → list of 7, WARN logged.
- [ ] Quick-mention compose: LLM returns oversized one-liner → truncated.
- [ ] `assemble_issue`: 3 deep dives + 10 quick mentions → markdown with correct sections, front matter, footer.
- [ ] `assemble_issue`: 4 deep dives → no truncation, 4 sections.
- [ ] `assemble_issue`: 0 quick mentions → "Also worth noting" omitted.
- [ ] `assemble_issue`: front matter contains all required keys (`issue_id`, `date`, `tokens_used`, `model`, `sources`).
- [ ] `assemble_issue`: maturity rendered when known, absent when unknown.
- [ ] `assemble_issue`: deterministic — same inputs produce byte-identical output.
- [ ] Deep dive body containing `---` fence: front matter still parseable.
- [ ] Type check: all new functions and models pass pyright.
- [ ] `prompts/compose-blog.md` and `prompts/compose-quick-mentions.md` exist and load without error.

---

## Dependencies

### Story Dependencies

| Story | Type | What's Needed | Status |
|-------|------|---------------|--------|
| [US0008](US0008-rank-prompt-and-step.md) | Service | Ranked clusters (deep + quick) | Draft |
| [US0009](US0009-compose-prompt-for-paper-items.md) | Schema/Shared | `DeepDive`, exceptions, anti-hype list | Draft |
| [US0010](US0010-compose-prompt-for-repo-items.md) | Schema/Shared | Same shared types | Draft |
| [US0006](US0006-llm-client-with-budget-enforcement.md) | Service | `LlmClient` | Draft |

### External Dependencies

| Dependency | Type | Status |
|------------|------|--------|
| `pyyaml` for front-matter rendering | Library | Already added (US0005) |

---

## Estimation

**Story Points:** 8
**Complexity:** Medium-High. Three distinct sub-pieces (blog compose, batch quick-mention compose, assembly) that share types and shape but each have their own gotchas. Assembly tests are the deterministic part; compose tests need fake LLM scaffolding. Capstone of EP0002 — review carefully before merge.

---

## Open Questions

_None._

---

## Revision History

| Date | Author | Change |
|------|--------|--------|
| 2026-05-19 | HYL | Initial story created from EP0002. |
