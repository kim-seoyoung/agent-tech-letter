# US0007: Cluster prompt + step

> **Status:** Draft
> **Epic:** [EP0002: Composition Pipeline](../epics/EP0002-composition-pipeline.md)
> **Owner:** HYL
> **Reviewer:** HYL
> **Created:** 2026-05-19

## User Story

**As** HYL (Author/Editor)
**I want** a cluster step that takes a normalised list of `Item`s and groups them into topic clusters via a single LLM call
**So that** downstream ranking and composition operates on topics — not on a raw stream of items — and a single significant event surfaced from multiple sources is recognised as one story, not three.

## Context

### Persona Reference
**HYL (Author/Editor)** — wants the LLM to do the work that would otherwise be HYL's Monday-morning triage. Will judge by "did clusters reflect what was actually happening that week?"
[Full persona details](../personas/stakeholders/users/hyl-author.md)

### Background
Clustering is the first LLM step in the pipeline. The Researcher Subscriber's concerns directly drive its design: a cluster prompt that conflates a methodologically rigorous paper with a vendor blog post about the same topic is a failure. The prompt must distinguish *what kind* of items are in each cluster.

---

## Inherited Constraints

| Source | Type | Constraint | AC Implication |
|--------|------|------------|----------------|
| Epic | Output shape | Clusters span multiple `item_kind`s | Cluster prompt is told this is expected; ranking step (US0008) downstream uses kinds |
| Epic | Prompts | Live in `prompts/cluster.md`, not inlined | Prompt loaded at runtime |
| Epic | Cost | Cluster is one LLM call per run | Items truncated to fit; output is structured (JSON) |
| TRD | Models | `Cluster` model defined in TRD §6 (`id`, `topic`, `items`, `significance`, `novelty`, `rationale`) | Cluster step populates `id`, `topic`, `items`, `rationale`; `significance` and `novelty` are populated by US0008 (rank step) |

---

## Acceptance Criteria

### AC1: `Cluster` model and step are defined
- **Given** the package `techletter.pipeline.cluster` exists
- **When** an engineer imports `from techletter.pipeline.cluster import cluster_items, Cluster`
- **Then** `Cluster` is a pydantic model with `id: str` (UUID4), `topic: str`, `items: list[Item]`, `rationale: str`, plus `significance: float | None` and `novelty: float | None` (both `None` until US0008 fills them in)
- **And** `cluster_items(items: list[Item], llm: LlmClient) -> list[Cluster]` is the public step

### AC2: Single LLM call produces clusters
- **Given** 50 normalised `Item`s from a mix of arXiv, GitHub, RSS
- **When** `cluster_items(items, llm)` is called
- **Then** exactly one LLM call is made to `llm.generate()`
- **And** the prompt is loaded from `prompts/cluster.md` (template-rendered with the item list)
- **And** the response is parsed as JSON conforming to the cluster output schema

### AC3: Items truncated to fit context
- **Given** the 50 items include several with `summary_excerpt` of 800–1000 chars
- **When** the cluster prompt is built
- **Then** each item's representation in the prompt is bounded: `title` (≤200 chars) + `summary_excerpt` truncated to 300 chars + `source` + `item_kind` + `url`
- **And** the total prompt size is logged for observability

### AC4: Clusters span multiple item kinds
- **Given** the input contains items about, say, "OpenAI Swarm framework" from arXiv (a paper analysing it), GitHub Trending (the repo), and Latent Space (a blog post about it)
- **When** the cluster step runs
- **Then** these three items are clustered together in a single `Cluster` with all three in `items`
- **And** the cluster's `topic` describes the topic in a few words (e.g., "OpenAI Swarm: multi-agent orchestration framework")
- **And** the `rationale` explains why the items belong together (one or two sentences)

### AC5: Each item appears in at most one cluster (no double-counting)
- **Given** the LLM response
- **When** the step parses and validates the response
- **Then** the union of `items` across all clusters equals the input set (no losses)
- **And** the intersection of `items` across any two clusters is empty (no duplicates)
- **And** if the LLM produces a malformed response violating either invariant, the step raises `ClusterParseError` with the violating items listed

### AC6: Empty input is handled
- **Given** the input list is empty
- **When** `cluster_items([], llm)` is called
- **Then** the step returns `[]` without making an LLM call
- **And** logs "no items to cluster; skipping"

### AC7: Cluster count is bounded
- **Given** 50 items input
- **When** the LLM produces clusters
- **Then** the cluster count is in the range `[3, 30]` — a single bucket "all the LLM stuff" or 49 singleton clusters are both equally useless
- **And** if the LLM returns a count outside this range, the step logs a WARN and returns the result anyway (does not raise — let HYL see the bad output and adjust prompts)

---

## Scope

### In Scope
- `techletter/pipeline/cluster.py` defining `Cluster` model and `cluster_items` function.
- `prompts/cluster.md` — the LLM prompt template (Jinja2 syntax for item-list interpolation).
- JSON-schema-based response parsing and validation.
- `ClusterParseError` exception.
- Unit tests against a fake `LlmClient` returning canned responses.

### Out of Scope
- Significance and novelty scoring — that's US0008.
- Prompt tuning experiments — initial prompt is a v0 draft; iteration happens in PRs as issues ship.
- Cross-week deduplication or memory — stateless within a run (per TRD).
- Hierarchical clustering (clusters of clusters) — flat structure only.

---

## Technical Notes

- The prompt instructs the LLM to:
  1. Group items by topic (a topic = the substantive thing being discussed; not the source).
  2. Allow cross-`item_kind` clusters (paper + repo + blog about the same thing).
  3. Output JSON: `{"clusters": [{"topic": "...", "rationale": "...", "item_indices": [0, 3, 7]}, ...]}` — using *indices* rather than item content to keep the response compact.
- After parse, the step maps indices back to the original `Item` objects to build `Cluster` instances.
- `Cluster.id` is generated server-side (UUID4) — the LLM doesn't supply it.
- One LLM call per run, large context — fits comfortably in the 200K budget alongside rank + compose.

### API Contracts
- `cluster_items(items: list[Item], llm: LlmClient) -> list[Cluster]`
- `Cluster.model_validate(dict) -> Cluster`
- `ClusterParseError(Exception)` — raised when LLM output cannot be reconciled with input set.

### Data Requirements
No persistent storage. Result passed to the rank step (US0008) in memory.

---

## Edge Cases & Error Handling

| Scenario | Expected Behaviour |
|----------|-------------------|
| Empty input list | Return `[]` without LLM call |
| Single-item input | Return one cluster with that item (LLM call still happens for the `rationale` field) |
| LLM returns invalid JSON | `ClusterParseError` raised after a single retry (re-prompt with "your output was invalid JSON, return only valid JSON"); if still invalid, abort |
| LLM omits some items from any cluster | `ClusterParseError` (violates AC5 invariant: union must equal input) |
| LLM assigns same item to multiple clusters | `ClusterParseError` (violates AC5 invariant) |
| LLM creates 1 cluster containing all items | Step logs WARN, returns the result (AC7 — non-raising bound check) |
| LLM creates N clusters with N items (one per item) | Step logs WARN, returns the result |
| LLM hallucinates an item index (e.g., index 60 when only 50 items) | `ClusterParseError` (index out of range) |
| LLM call hits `LlmUnavailableError` after retries | Propagates; orchestrator aborts the run (rank/compose can't proceed without clusters) |
| Items are all the same (50 identical entries) | LLM likely produces 1 cluster; valid behaviour (passes AC5; logs WARN on count) |
| Prompt file `prompts/cluster.md` missing | `FileNotFoundError` at startup; descriptive error in workflow log |

---

## Test Scenarios

- [ ] Fake LLM returning a valid cluster JSON over 50 items → exactly 50 items distributed, no duplicates.
- [ ] Fake LLM returning invalid JSON → `ClusterParseError` after retry.
- [ ] Fake LLM omitting one item → `ClusterParseError`.
- [ ] Fake LLM duplicating an item across clusters → `ClusterParseError`.
- [ ] Empty input → returns `[]`, no LLM call.
- [ ] Single-item input → one cluster, one LLM call.
- [ ] 50 items → exactly one LLM call.
- [ ] Cluster count below 3 or above 30 → WARN logged, result still returned.
- [ ] Prompt file missing → clear startup error.
- [ ] Type check: `cluster_items` signature passes pyright.

---

## Dependencies

### Story Dependencies

| Story | Type | What's Needed | Status |
|-------|------|---------------|--------|
| [US0001](US0001-item-model-and-source-adapter-protocol.md) | Schema | `Item` model | Draft |
| [US0006](US0006-llm-client-with-budget-enforcement.md) | Service | `LlmClient` to call | Draft |

### External Dependencies
None beyond what US0006 introduces (`anthropic` SDK).

---

## Estimation

**Story Points:** 5
**Complexity:** Medium. Prompt design is the time-sink; the code is straightforward. Validation invariants (no losses, no duplicates) are non-trivial.

---

## Open Questions

_None._

---

## Revision History

| Date | Author | Change |
|------|--------|--------|
| 2026-05-19 | HYL | Initial story created from EP0002. |
