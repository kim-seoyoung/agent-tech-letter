# Stakeholder Consultation — PRD v0.2.0 (Re-consult)

**Artefact:** [sdlc-studio/prd.md](../prd.md) (Tech-Letter for HYL, v0.2.0, Ready)
**Date:** 2026-05-19
**Command:** `/sdlc-studio consult stakeholders sdlc-studio/prd.md`
**Personas consulted:** HYL (Author/Editor), Researcher Subscriber **[refined]**, Practitioner Subscriber **[refined]**
**Prior review:** [prd-stakeholder-review-2026-05-19.md](./prd-stakeholder-review-2026-05-19.md)
**Reason for re-consult:** PRD unchanged. Both subscriber personas were refined — Researcher is now a hybrid (research-aware engineer who also ships features); Practitioner is now a non-coder knowledge worker who uses LLM agents on papers/text/Excel.

---

## Summary

| Persona | Verdict (was) | Verdict (now) | Δ |
|---------|---------------|---------------|---|
| HYL (Author/Editor) | ✅ Approve | ✅ Approve | — |
| Researcher Subscriber | ⚠️ Concerns | ⚠️ Concerns | concerns *shifted* — old concerns hold, plus new production-reality concerns |
| Practitioner Subscriber | ⚠️ Concerns | ⚠️ **Concerns (escalated)** | the persona is now substantively less served by the PRD as written |

**Aggregate:** The PRD is still shippable into epic decomposition, but the new Practitioner reveals a real design question the old persona masked: **who is the audience?** The PRD currently assumes the reader has at least an engineering-adjacent technical background. The new Practitioner does not. Either (a) the PRD should explicitly scope the audience as engineering-fluent (in which case the Practitioner persona is on the edge of being out-of-scope, and we should say so), or (b) the issue composer needs to handle audience tiers.

---

## HYL (Author/Editor)
**Verdict:** ✅ Approve

> Same verdict as before. PRD respects my approval gate, bounds my cost surface, and assumes minimal weekly effort. The one previously-noted concern about "exactly 3 deep dives" remains — I'd want flex (2–5) in practice — but that's a story-writing detail, not a PRD blocker.

**Questions:**
- Should the PRD say anything about *who* the issues are written for? Right now F-03 says "3 deep-dives + 10 quick mentions" but is silent on voice/audience.

**Conditions for approval:** None. Still shippable.

---

## Researcher Subscriber [refined: research-aware engineer who also ships]
**Verdict:** ⚠️ Concerns

> All my earlier concerns about provenance scoring and "novelty" still hold — papers and blog posts shouldn't be pooled at the same significance weight, and "novelty" without prior-issue state is just "recency." But now that I'm also evaluating this as someone who ships, I have an additional concern: deep-dive summaries don't address production reality. An agentic-RAG paper that costs $40/query to eval is materially different from one that runs at $0.02/query, but the PRD's composer treats both identically. Same for latency, eval-on-real-data, and whether anyone has actually deployed it. If the newsletter exists partly so that *I* can decide what to ship, the summaries need a "would this survive contact with production?" beat — at least for items where the source enables that judgment.

**Questions:**
- Will deep dives surface cost / latency / eval-cost numbers when the source paper provides them?
- Will the composer flag items where the eval setup is suspect (synthetic data, no human eval, contamination concerns)?
- Will tool/repo items get a "has anyone shipped this?" line (e.g., based on GitHub repo signals: real users, recent releases, contributors)?

**Conditions for approval (carry-over + new):**
- *(Carry-over)* F-02 prompt: differentiate paper-vs-blog provenance in significance scoring.
- *(Carry-over)* F-03 deep-dive template for paper-shaped items should include a "what was actually shown" + "caveats" structure.
- *(Carry-over)* "Novelty" criterion in F-02 should either be backed by prior-issue state, or the word should be dropped.
- *(New)* Deep dives should include production-reality framing — cost/latency/replicability/shipping-evidence — when the source supports it. This is part of "significance" for a hybrid research-engineer reader.

---

## Practitioner Subscriber [refined: non-coder knowledge worker]
**Verdict:** ⚠️ Concerns (escalated)

> I want to be careful here — I might not be the intended audience for this newsletter, and that's a legitimate scope choice. But if I *am* an intended audience, the PRD has problems for me.
>
> Look at the source list: arXiv (papers — I read them but I need plain-language summaries), GitHub trending (mostly unusable for me — if the only access path is `git clone && pip install`, I can't actually use the thing), and four RSS feeds that are mostly written by and for engineers. Latent Space and Simon Willison's blog assume the reader can talk about RAG, function-calling, and agent loops; that's not me.
>
> The composer (F-03) is silent on audience. It says "3 deep-dive sections, 1–2 paragraphs each." It doesn't say whether those paragraphs are written for an engineer or for someone like me. In practice this means the rendered issue will inherit the voice of the sources — which is engineering-heavy.
>
> What's missing isn't more sources; it's *labels* and *framing*. If an item is a research paper, I want a paragraph that tells me what the paper enables for someone doing my kind of work, in plain language, *and* whether there's a product I can actually try without writing code. If an item is a GitHub repo, I want to know: is there a hosted demo? a consumer product built on this? Or is it source-code-only? If it's source-code-only, I'd rather it stayed in the quick mentions than be a deep dive that wastes my reading time.

**Questions:**
- Is the intended audience for this newsletter "engineering-fluent readers only," or also non-coder knowledge workers?
- Does the composer have a notion of "access tier" per item — source code only / hosted demo / consumer product?
- Will quick mentions / deep dives use plain language where possible, or inherit the technical voice of the sources?
- Would adding a consumer-facing source (e.g., AI product launches, ProductHunt AI section, agent app directories) be in scope?

**Conditions for approval:**
- **The PRD should explicitly state the intended audience.** If it's engineering-fluent only, write that down and I'll know to expect a higher bar of technical fluency from the issues (and I'll be a marginal reader, not a primary one). If the audience includes non-coders, the composer needs an audience-aware framing.
- F-01 `Item` model (or composer prompt) should track an **access tier**: `code-only | hosted-demo | consumer-product | research-paper`. This is the single most important attribute for whether an item is useful to me.
- F-03 composer should produce deep dives that, where applicable, include a "what to try if you're not a coder" line — even if it's just "no consumer-facing implementation exists yet."

---

## Cross-Cutting Findings

### New finding: audience scope is ambiguous

Both subscribers raised audience questions, but from opposite directions:
- The **Researcher (hybrid)** wants the composer to be technically *richer* (cost, eval, methodology, shipping signal) — i.e., more for serious technical readers.
- The **Practitioner (non-coder)** wants the composer to be technically *plainer*, with an "access tier" label and "what can I actually try?" framing.

These are in tension. The PRD currently sits in the middle without acknowledging the tension. **Either explicitly scope (engineering-fluent only, with the Practitioner accepted as a marginal reader), or design the composer to serve both tiers.**

### Carry-over finding: source-type heterogeneity

The original cross-cutting finding still stands — the PRD treats papers, blog posts, and repos as homogeneous in ranking and rendering. The refined personas make this more obvious, not less:
- Researcher wants paper / blog / repo distinguished for **significance scoring** and **methodology framing**.
- Practitioner wants paper / blog / repo distinguished for **access tier** (can I use this without coding?).

The right `Item`-model addition serves both:

```python
# proposed addition to techletter.models.Item
item_kind: Literal["paper", "blog_post", "repo", "consumer_product"]
maturity:  Literal["experimental", "beta", "production-ready", "unknown"] | None
access:    Literal["code-only", "hosted-demo", "consumer-product", "research-paper"]
```

---

## Action Items (refreshed)

| # | Owner | Item | Severity | Origin |
|---|-------|------|----------|--------|
| 1 | HYL | Decide: explicit audience scope in the PRD (Section 2 "Target Users"). Engineering-fluent only, or multi-tier? | **High (new)** | Practitioner |
| 2 | HYL | "Exactly 3 deep dives" → flex (2–5)? Revisit when writing F-03 story. | Low | HYL |
| 3 | Architect (HYL) | Add `item_kind`, `maturity`, `access` to the `Item` model — addresses both Researcher and Practitioner concerns in one change. Bumps PRD to v0.3.0. | **Medium-High** | Both subscribers |
| 4 | Engineer (HYL) | GitHub adapter captures repo metadata (stars, last-commit, recent-release, has-hosted-demo if discoverable). | Medium | Both subscribers |
| 5 | Engineer (HYL) | F-02 ranking treats `item_kind` differently — papers, blogs, repos, and products scored on different significance rubrics. | Medium | Researcher |
| 6 | Engineer (HYL) | F-03 composer prompts: condition on `item_kind` + `access`. For papers → method + caveats + (if applicable) production-reality line. For repos → "can a non-coder use this?" line. For products → "what it does in plain language." | Medium | Both subscribers |
| 7 | Engineer (HYL) | Drop "novelty" from F-02 OR back it with prior-issue state (last 4 weeks of cluster topics in `logs/`). | Low | Researcher |
| 8 | HYL | Consider adding a consumer-facing source (e.g., ProductHunt AI section) — only if audience scope includes non-coders. | Low | Practitioner |

---

## What changed from v1 of this review

| Change | Why |
|--------|-----|
| Practitioner verdict **escalated** within ⚠️ Concerns | The persona shift makes the audience question central, not peripheral. They're now asking "am I even the intended reader?" |
| Researcher concerns **expanded** | Hybrid framing adds production-reality concerns (cost, latency, shipping-evidence) on top of the original methodology concerns. |
| New top action item: **audience scope** | The previous review didn't surface this because the old Practitioner was an engineer themselves. Now that they're not, "who is this for?" is the question that unlocks several downstream decisions. |
| Action items consolidated around an `Item`-model change | Single change (add `item_kind`, `maturity`, `access`) addresses both subscribers' top concerns. Strongest argument yet for v0.3.0 PRD bump. |

---

## Recommended next step

The audience-scope question (Action Item #1) and the `Item`-model addition (Action Item #3) are coupled. Suggested flow:

1. Decide audience scope. Two reasonable answers:
   - **(A) Engineering-fluent only.** Update PRD §2 to say so. Accept Practitioner as a marginal/aspirational reader, drop Action Items #6 ("non-coder framing") and #8 (consumer source). Researcher concerns still drive the `Item`-model change.
   - **(B) Multi-tier (engineering + non-coder).** Keep both subscribers as in-scope. Land the full `Item`-model change. Composer becomes audience-aware.
2. Bump PRD to v0.3.0 with whichever choice — both involve PRD edits.
3. Then proceed to `/sdlc-studio epic`.
