# US0008: Rank prompt + step (`item_kind`-aware significance)

> **Status:** Draft
> **Epic:** [EP0002: Composition Pipeline](../epics/EP0002-composition-pipeline.md)
> **Owner:** HYL
> **Reviewer:** HYL
> **Created:** 2026-05-19

## User Story

**As** HYL (Author/Editor)
**I want** a rank step that scores clusters by `item_kind`-aware significance and (hedged) novelty, then selects the top N for deep dives and the next M for quick mentions
**So that** each issue covers what genuinely mattered this week — papers judged on methodological substance, repos on shipping evidence, blogs on author authority — rather than whatever scored highest on a single homogeneous rubric.

## Context

### Persona Reference
**HYL (Author/Editor)** — wants ranking decisions to be inspectable, not a black box. The rank prompt's rationale output is the explanation HYL reads when wondering "why did this make the cut and that didn't?"
[Full persona details](../personas/stakeholders/users/hyl-author.md)

**Researcher Subscriber** (downstream beneficiary) — their objection to the original PRD was specifically about ranking heterogeneity. This story is the fix.

### Background
The PRD (v0.4.0) explicitly requires `item_kind`-aware ranking. The rank prompt scores each cluster on a rubric appropriate to the kinds of items in it. Novelty stays hedged in v1 (no prior-issue state), but the prompt still asks "is this novel relative to the model's general knowledge?" as a partial signal.

---

## Inherited Constraints

| Source | Type | Constraint | AC Implication |
|--------|------|------------|----------------|
| Epic | Output shape | 3 deep dives + 10 quick mentions (deep flex 2–5) | Rank step selects top 3 for deep, next 10 for quick |
| Epic | Ranking | `item_kind`-aware rubrics; papers, blogs, repos scored differently | Prompt instructions vary by kind composition of each cluster |
| Epic | Cost | Single LLM call for the rank step | Output is structured; clusters are passed as compact representation |
| Epic | Hedge | "Novelty" caveat: v1 is stateless | Novelty score includes the LLM's note about confidence (low-confidence by default) |

---

## Acceptance Criteria

### AC1: `rank_clusters` step is defined
- **Given** the module `techletter.pipeline.rank` exists
- **When** an engineer imports `from techletter.pipeline.rank import rank_clusters, RankedClusters`
- **Then** `rank_clusters(clusters: list[Cluster], llm: LlmClient, *, top_deep: int = 3, top_quick: int = 10) -> RankedClusters` is the public step
- **And** `RankedClusters` is a pydantic model with fields `deep: list[Cluster]` (ordered, length ≤ `top_deep`), `quick: list[Cluster]` (ordered, length ≤ `top_quick`), `unselected: list[Cluster]`, `rationale_by_cluster_id: dict[str, str]`

### AC2: Each cluster gets significance + novelty scores
- **Given** N input clusters
- **When** the rank step runs
- **Then** each returned cluster has `significance: float` ∈ [0, 1] and `novelty: float` ∈ [0, 1] populated (filling in the fields US0007 left as None)
- **And** higher score = more significant / more novel

### AC3: Ranking is `item_kind`-aware
- **Given** the rank prompt loaded from `prompts/rank.md`
- **When** the prompt is built for a given cluster
- **Then** the prompt explicitly tells the LLM:
  - For clusters dominated by `paper` items: score on methodological substance, cross-citation signal, contribution clarity
  - For clusters dominated by `repo` items: score on shipping signals (`maturity`, recent activity, releases, hosted demo) and adoption signal (stars)
  - For clusters dominated by `blog_post` items: score on author authority and cross-source corroboration
  - For mixed clusters: combine the rubrics, weighted by item composition

### AC4: Top selection is deterministic given scores
- **Given** scored clusters
- **When** the step selects the top N and next M
- **Then** selection is by `significance` score descending, with `novelty` as a tiebreaker
- **And** `deep` is the top `top_deep` by combined score; `quick` is the next `top_quick`; `unselected` is the rest
- **And** the sort is stable (clusters with equal scores keep input order)

### AC5: Per-cluster rationale is captured
- **Given** the rank LLM response
- **When** the step builds `RankedClusters`
- **Then** `rationale_by_cluster_id` contains one entry per scored cluster, mapping cluster id → 1–3 sentence explanation
- **And** the rationale is used downstream by compose prompts as input context

### AC6: Novelty is hedged in v1
- **Given** v1 has no prior-issue state
- **When** the rank prompt asks for novelty
- **Then** the prompt instructs: "Score novelty against your general LLM-agent knowledge as of the model's training cutoff. Use low confidence; a cluster is 'novel' only if it represents a genuinely new direction, not just a recent paper on an established topic. Default to 0.3–0.5 if unsure."
- **And** the rationale for novelty explicitly states the basis ("vs. training cutoff" or "appears to be incremental")

### AC7: Fewer clusters than selection target is handled
- **Given** the input is 4 clusters (fewer than `top_deep=3 + top_quick=10 = 13`)
- **When** the step runs
- **Then** `deep` has the top 3, `quick` has the remaining 1, `unselected` is empty
- **And** no error is raised; this is a normal "quiet week" outcome

---

## Scope

### In Scope
- `techletter/pipeline/rank.py` with `rank_clusters` function and `RankedClusters` model.
- `prompts/rank.md` — the rank prompt with `item_kind`-aware rubric instructions.
- JSON parse + validation of the LLM response.
- Mutation of input cluster objects to fill in `significance` and `novelty` (or return new copies — implementer's choice, but documented).
- Unit tests against fake LLM with canned scoring responses.

### Out of Scope
- Prior-week state for true novelty detection (deferred to a future CR).
- Per-source weighting beyond what the `item_kind`-aware rubric already implies.
- Re-ranking based on diversity (e.g., "don't put two paper clusters in deep dives") — the LLM is free to assemble whatever it wants; HYL has final say at PR time.
- Composition (US0009–US0011).

---

## Technical Notes

- The rank prompt receives clusters in a compact form: cluster id, topic, rationale, item count by `item_kind`, and 1–2 representative item titles. Full item content is not re-sent (it was in the cluster prompt; would blow the budget).
- Tiebreaker order: significance DESC → novelty DESC → original insertion order. Documented in the function docstring.
- After ranking, the step calls `llm.check_budget(projected_additional_tokens=COMPOSE_BUDGET_ESTIMATE)` before returning. This is where the pre-compose abort is *actually* triggered. `COMPOSE_BUDGET_ESTIMATE` is computed from `top_deep × deep_dive_cost + top_quick × quick_mention_cost`, with conservative per-item estimates documented in code.

### API Contracts
- `rank_clusters(clusters: list[Cluster], llm: LlmClient, *, top_deep: int = 3, top_quick: int = 10) -> RankedClusters`
- `RankedClusters.model_validate(dict) -> RankedClusters`

### Data Requirements
None persistent.

---

## Edge Cases & Error Handling

| Scenario | Expected Behaviour |
|----------|-------------------|
| Empty cluster list | Return `RankedClusters(deep=[], quick=[], unselected=[], rationale_by_cluster_id={})`; no LLM call |
| All clusters get identical scores | Stable sort preserves input order; deterministic selection |
| LLM returns scores outside [0, 1] | Clamp to [0, 1] with a WARN log; do not raise |
| LLM omits a cluster id in scoring response | `RankParseError`; orchestrator aborts run |
| LLM scores a cluster id that doesn't exist | `RankParseError` |
| `top_deep` or `top_quick` is 0 | Valid; the corresponding output list is empty |
| `top_deep + top_quick > len(clusters)` | All clusters distributed; `unselected` empty; normal behaviour |
| Pre-compose budget check fails (`projected > budget`) | `BudgetExceededError` propagates; orchestrator aborts before compose |
| LLM unavailable after retries | `LlmUnavailableError`; orchestrator aborts run |
| Rationale missing for some clusters | If the cluster is in deep or quick, raise `RankParseError`; if unselected, log a WARN and use an empty rationale (only deep/quick rationales feed downstream) |

---

## Test Scenarios

- [ ] 10 clusters, fake LLM returns valid scores → top 3 in `deep`, next 7 in `quick`, none unselected (since 10 < 13).
- [ ] 20 clusters → top 3 in `deep`, next 10 in `quick`, 7 in `unselected`.
- [ ] Empty cluster list → empty `RankedClusters`, no LLM call.
- [ ] Scores out of range (`1.5`) → clamped to 1.0, WARN logged.
- [ ] LLM omits cluster id → `RankParseError`.
- [ ] Pre-compose budget projection too high → `BudgetExceededError`.
- [ ] Stable sort: clusters with identical scores keep input order.
- [ ] Prompt instructions verified to reference all three `item_kind` rubrics (string match in `prompts/rank.md`).
- [ ] `top_deep=0, top_quick=10` with 20 clusters → 0 deep, 10 quick, 10 unselected.
- [ ] Cluster with only `paper` items vs. only `repo` items — rationale strings reference appropriate rubric for each (manual inspection / integration test).

---

## Dependencies

### Story Dependencies

| Story | Type | What's Needed | Status |
|-------|------|---------------|--------|
| [US0007](US0007-cluster-prompt-and-step.md) | Schema/Service | `Cluster` model + clusters in hand | Draft |
| [US0006](US0006-llm-client-with-budget-enforcement.md) | Service | `LlmClient` + `check_budget` | Draft |

### External Dependencies
None beyond what US0006 introduces.

---

## Estimation

**Story Points:** 5
**Complexity:** Medium. The rank prompt is the most-iterated artifact in EP0002 — getting the three rubrics balanced is fiddly. Pre-compose budget check timing is the critical-path correctness item.

---

## Open Questions

_None._

---

## Revision History

| Date | Author | Change |
|------|--------|--------|
| 2026-05-19 | HYL | Initial story created from EP0002. |
