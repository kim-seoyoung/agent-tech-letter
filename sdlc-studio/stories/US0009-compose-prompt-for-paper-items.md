# US0009: Compose prompt for `paper` items

> **Status:** Done
> **Epic:** [EP0002: Composition Pipeline](../epics/EP0002-composition-pipeline.md)
> **Owner:** HYL
> **Reviewer:** HYL
> **Created:** 2026-05-19

## User Story

**As** HYL (Author/Editor)
**I want** a paper-specific deep-dive compose prompt that produces "what was shown" + "method/eval at a glance" + "caveats" + (when source supports) a "production-reality" line
**So that** when the Researcher Subscriber reads a paper deep dive, they can decide in 60 seconds whether to read the actual paper — including whether the result will survive contact with production constraints.

## Context

### Persona Reference
**Researcher Subscriber** — the direct beneficiary. Their explicit pushback in the stakeholder consult was about paper summaries that flatten methodology and ignore caveats. This story addresses both.
[Persona details](../personas/stakeholders/users/researcher-subscriber.md)

**HYL (Author/Editor)** — runs the system; will judge by whether the rendered paper section gives them the same gist they'd get from reading the abstract themselves, plus the caveats they'd notice.

### Background
This is the first of three `item_kind`-conditioned compose prompts (paper, repo, blog). They share a common code path (`compose_deep_dive` dispatches by kind) but each loads a different prompt file. Paper composition is its own story because the framing (methodology + caveats + production reality) is substantively different from the other two kinds.

---

## Inherited Constraints

| Source | Type | Constraint | AC Implication |
|--------|------|------------|----------------|
| Epic | Framing | Paper deep dives include: "what was shown" + "method/eval at a glance" + "caveats" + (when source supports) "production-reality" | Prompt structure mirrors these four sections |
| Epic | Output shape | 1–2 paragraphs per deep dive | Prompt enforces length bound |
| Epic | Provenance | Each deep dive cites all contributing sources | Prompt receives item list and cites by URL |
| Epic | Voice | No marketing-flavoured writing | Prompt has explicit anti-hype instructions |
| Epic | Cost | One LLM call per deep dive | Self-evident; called from compose orchestrator |

---

## Acceptance Criteria

### AC1: Compose function for paper kind is defined
- **Given** the module `techletter.pipeline.compose` exists
- **When** an engineer imports `from techletter.pipeline.compose import compose_paper_deep_dive`
- **Then** the signature is `compose_paper_deep_dive(cluster: Cluster, rationale: str, llm: LlmClient) -> DeepDive`
- **And** `DeepDive` is a pydantic model with `topic: str`, `body_markdown: str`, `cited_urls: list[str]`, `item_kind: Literal["paper"]`, `maturity_summary: str | None`

### AC2: Prompt lives in `prompts/compose-paper.md`
- **Given** the prompt file `prompts/compose-paper.md`
- **When** the compose function loads it
- **Then** the prompt template includes:
  - System role section instructing the LLM that it is writing for a research-aware engineer audience.
  - Anti-hype instruction list (e.g., no "groundbreaking", "revolutionary", "breakthrough"; prefer specific claims).
  - Four-section structure: "What was shown", "Method/eval at a glance", "Caveats", "Production reality (if applicable)".
  - Instructions to cite each contributing item's URL inline.
  - Length bound: 1–2 paragraphs (≤300 words target).

### AC3: Output has the four-section structure
- **Given** a paper cluster about, e.g., a new agent-evaluation benchmark
- **When** `compose_paper_deep_dive(...)` runs
- **Then** the returned `body_markdown` contains all four section headers (or natural-prose equivalents): "what was shown", "method/eval", "caveats", and either "production reality" *or* an explicit "(no production signal yet)" note
- **And** the markdown is ≤300 words total (excluding citation lines)

### AC4: All contributing items are cited
- **Given** a cluster with 3 paper items
- **When** the compose function returns
- **Then** `cited_urls` contains all 3 URLs (matches `[item.url for item in cluster.items]`)
- **And** each URL appears inline in `body_markdown` as a markdown link

### AC5: Production-reality line is conditional on source
- **Given** a paper cluster where the cluster's items provide signals about cost / latency / replication / deployment
- **When** the compose function runs
- **Then** the output includes a "production reality" sentence
- **And** when no such signal exists, the prompt instructs the LLM to write an explicit "no production signal yet" rather than fabricating one

### AC6: Anti-hype voice is enforced via prompt
- **Given** the prompt instructions explicitly ban marketing language
- **When** the rendered output is inspected
- **Then** the body contains none of these words/phrases: "groundbreaking", "revolutionary", "game-changing", "breakthrough", "state-of-the-art" (use "SOTA" only if cited from the paper), "next-generation"
- **And** a unit test asserts this ban list against generated output (against a stub LLM that has these words in its response — the post-LLM lint catches them and either re-prompts once or surfaces a `ComposeStyleError`)

### AC7: Empty or malformed LLM response
- **Given** the LLM returns an empty string or markdown without any section structure
- **When** the compose function runs
- **Then** it retries once with an explicit "your previous output didn't include the required sections; output a body with four sections..."
- **And** if still malformed, raises `ComposeParseError` — orchestrator aborts run (partial deep dive is worse than no issue)

---

## Scope

### In Scope
- `techletter/pipeline/compose.py` (the file may already exist from US0010/US0011; this story adds `compose_paper_deep_dive`).
- `prompts/compose-paper.md` — system + user prompt template.
- Post-LLM style lint (anti-hype word check) + single retry mechanism.
- `DeepDive` pydantic model (shared across paper/repo/blog stories — first one to introduce it owns it).
- `ComposeParseError`, `ComposeStyleError` exceptions.
- Unit tests with fake LLM returning canned paper-shaped responses.

### Out of Scope
- Repo and blog compose prompts (US0010, US0011).
- Quick-mention composition (US0011).
- Final `RenderedIssue` assembly (US0011).
- LLM-as-judge automation for output quality — manual judgement at PR time is the v1 evaluation.

---

## Technical Notes

- Define `DeepDive` and the shared exception types in this story so US0010 and US0011 can import them.
- The anti-hype lint runs on `body_markdown` post-LLM. It's a deliberate redundancy: prompt asks for no-hype, lint enforces it. If a hyped word slips through the prompt, the lint catches it; if the lint fails twice, we accept the output and surface a WARN (don't crash on style — HYL has merge authority).
- Token budget for one paper compose: target ≤8K tokens (≤4K input cluster context + prompt overhead + ≤2K output). Rank step (US0008) used this estimate in its budget projection.
- The prompt asks the LLM to cite URLs inline using markdown link syntax `[short label](url)`. The compose function extracts these to populate `cited_urls`.

### API Contracts
- `compose_paper_deep_dive(cluster: Cluster, rationale: str, llm: LlmClient) -> DeepDive`
- `DeepDive.model_validate(dict) -> DeepDive`

### Data Requirements
None persistent.

---

## Edge Cases & Error Handling

| Scenario | Expected Behaviour |
|----------|-------------------|
| Cluster contains a mix of `paper` and `blog_post` items | Function still runs; treats as paper-shaped framing. (Mixed-kind clusters are usually routed via different compose paths; this is a safety net.) |
| Cluster has only one item | Compose still produces all four sections; "caveats" may say "few independent corroborations" |
| LLM omits one of the four sections | Single retry with explicit correction prompt; second failure raises `ComposeParseError` |
| LLM body exceeds 500 words | WARN log; truncate to first paragraph break under 500 words; output retained (don't fail HYL's run over a length budget) |
| LLM body contains banned hype words | Single re-prompt; on second failure, log WARN and return the result (HYL edits at PR time) |
| LLM citation list doesn't match cluster items | If the LLM cited URLs not in the cluster: filter them out and use only cluster-item URLs; if the LLM omitted citations: re-prompt once; second failure → `ComposeParseError` |
| Cluster `rationale` is empty | Prompt still works; rationale is a useful context hint, not strictly required |
| LLM produces non-markdown plaintext | Accepted; the compose orchestrator (US0011) handles markdown vs plain in final assembly |
| `compose_paper_deep_dive` called on a cluster with no `paper` items | Logged WARN ("paper compose called for a non-paper cluster"); proceed anyway — the function doesn't gate on item_kind itself; the dispatcher does |
| LLM unavailable | Propagates `LlmUnavailableError`; orchestrator aborts |

---

## Test Scenarios

- [ ] Fake LLM returns a well-structured 4-section response over a paper cluster → `DeepDive` has all four sections, citations match cluster URLs.
- [ ] Fake LLM returns a 3-section response → retry triggered; fixture-supplied retry response is parsed.
- [ ] Fake LLM returns response with "groundbreaking" → style retry; second response without; pass.
- [ ] Fake LLM cites a URL not in the cluster → filtered out of `cited_urls`.
- [ ] Fake LLM omits all citations → re-prompted; second failure → `ComposeParseError`.
- [ ] Cluster with `rationale=""` → function runs without error.
- [ ] LLM body 600 words → truncated to <500 with WARN.
- [ ] `prompts/compose-paper.md` missing → clear startup error.
- [ ] Type check: function signature + `DeepDive` pass pyright.
- [ ] Anti-hype word list is at least 5 words long and enforced in unit test.
- [ ] Production-reality line appears when cluster has signal indicating cost/latency/deployment; absence is noted explicitly when no signal exists (verified via fixture clusters with vs without those fields in `raw`).

---

## Dependencies

### Story Dependencies

| Story | Type | What's Needed | Status |
|-------|------|---------------|--------|
| [US0008](US0008-rank-prompt-and-step.md) | Service | Selected cluster + rationale | Draft |
| [US0006](US0006-llm-client-with-budget-enforcement.md) | Service | `LlmClient` | Draft |

### External Dependencies
None beyond US0006.

---

## Estimation

**Story Points:** 5
**Complexity:** Medium. The prompt itself is iteration-heavy. The compose-time style lint is a small but useful safety net. Sharing `DeepDive` + exception types with US0010 and US0011 requires up-front design choice.

---

## Open Questions

_None._

---

## Revision History

| Date | Author | Change |
|------|--------|--------|
| 2026-05-19 | HYL | Initial story created from EP0002. |
