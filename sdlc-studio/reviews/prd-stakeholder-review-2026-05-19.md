# Stakeholder Consultation — PRD v0.2.0

**Artefact:** [sdlc-studio/prd.md](../prd.md) (Tech-Letter for HYL, v0.2.0, Ready)
**Date:** 2026-05-19
**Command:** `/sdlc-studio consult stakeholders sdlc-studio/prd.md`
**Personas consulted:** HYL (Author/Editor), Researcher Subscriber, Practitioner Subscriber

---

## Summary

| Persona | Verdict |
|---------|---------|
| HYL (Author/Editor) | ✅ Approve, with one note |
| Researcher Subscriber | ⚠️ Concerns |
| Practitioner Subscriber | ⚠️ Concerns |

**Aggregate:** PRD is shippable into Epic decomposition, but **two material concerns** from subscribers should be reflected — either in the PRD itself or recorded as items to handle when writing F-03 stories (the issue composer). Neither concern blocks; both are "the composer prompts need to be designed with these in mind."

---

## HYL (Author/Editor)
**Verdict:** ✅ Approve

> The PRD reflects what I asked for: weekly cron, draft-as-PR approval gate that I cannot accidentally bypass, 200K token budget enforced *before* compose, no database, no signup flow. The cost surface is bounded, the failure modes are isolated, and the architecture pattern (adapter for sources/channels) means I can add Discord or a new RSS feed without core edits. Status moved Draft → Ready is appropriate; all my original questions are closed.

**One note (not a blocker):**
- F-03 says "exactly 3 deep dives + 10 quick mentions." I'd want flex on this. Some weeks will have 2 substantive topics and 5 thin ones; some weeks will have 4 strong topics. Hard-coding *exactly* 3 is more rigid than my actual editorial preference.

**Questions:**
- Is the "exactly 3" intentional structure (for cadence consistency) or just a target?

**Conditions for approval:**
- None. This is shippable. The deep-dive count rigidity can be revisited when writing the F-03 story — soften "exactly" to "typically 3 (range: 2–5)" if I agree.

---

## Researcher Subscriber
**Verdict:** ⚠️ Concerns

> Glad arXiv is in the source set. Two things concern me. First, the PRD treats arXiv submissions, blog posts (Latent Space, Import AI, The New Stack), and Simon Willison's feed as homogeneous inputs to clustering and ranking. They are not. A vendor blog post and a peer-reviewed (or even unreviewed-but-formal) arXiv submission are categorically different signals. If the ranker weights them equally on "significance," it will conflate marketing announcements with research contributions. Second, the F-02 ranking criterion mentions "novelty (relative to prior weeks if state is available)" — that "if available" is doing a lot of work. Without persistent state, every week is week zero, and "novelty" collapses to "recency." That's not novelty; that's news.

**Questions:**
- Does the F-02 ranking prompt distinguish source provenance (paper vs blog), or are they pooled?
- How is "novelty" actually computed without prior-week context? Is the LLM expected to know what was novel last month from training data alone?
- Will deep-dive summaries surface methodological caveats (sample size, eval choice, no human eval, etc.) when the source is a paper?

**Conditions for approval:**
- F-02 prompts (which live in `prompts/` per the TRD) should track source-type metadata and bias significance scoring accordingly — papers are not "less significant," but they're scored differently from announcements.
- F-03 deep-dive template should have a "what was actually shown" line and a "caveats" line when the source is a paper. Not when the source is a blog post.
- The "novelty" criterion in F-02 should either drop or be backed by lightweight prior-issue state (last 4 weeks of cluster topics, in `logs/`).

---

## Practitioner Subscriber
**Verdict:** ⚠️ Concerns

> The bones are right — GitHub trending is in, Latent Space and Import AI lean practical, the issue shape (a few deep dives + many quick hits) is what I scan in 5 minutes on Monday morning. But the PRD doesn't say anything about signal I actually care about when deciding "should I try this on my own work?" Specifically: GitHub repo metadata (stars trajectory, last-commit date, has it shipped to anyone real?) and an explicit "experimental vs production-ready" tag. Right now a research demo repo and a battle-tested tool will look identical in the rendered issue — same headline, same summary structure, same link. That's the exact failure mode I want this newsletter to *fix* for me.

> Also — I read papers, but I read them because I'm trying to do something with them on my own work (papers, text, Excel files I'm pulling apart). So summaries that say what a paper *enables in practice* are more useful to me than summaries that say what a paper *contributes theoretically*. The Researcher will want the opposite. The composer probably needs to do both.

**Questions:**
- Will the GitHub adapter capture repo metadata (stars, last-commit, contributors, has-recent-release) and pass it to the composer?
- How will "experimental demo" vs "production-ready" be conveyed in the rendered issue?
- Will deep dives include a "what you can do with this today" framing where applicable?

**Conditions for approval:**
- F-01 GitHub adapter should capture repo metadata as part of the `Item` model (extending the existing `score` field, or via the `raw` payload).
- F-03 composer prompts should output a "maturity" tag per item where inferable (e.g., `experimental | beta | production-ready | unknown`).
- F-03 deep dives should include practical takeaway framing for tool/repo-shaped items, distinct from paper-shaped items.

---

## Cross-Cutting Findings

Both subscriber personas independently flagged the same root issue from different angles: **the PRD treats heterogeneous source types as homogeneous in ranking and rendering.** Researcher wants this fixed because it conflates papers and announcements. Practitioner wants it fixed because it conflates demos and shipped tools.

**Recommended PRD change (small):** add an "Item type / maturity classification" requirement to F-01 or a new sub-feature, with corresponding rendering treatment in F-03. This is one change that addresses both subscriber concerns.

**Recommended (no PRD change):** these concerns flow into the F-02 ranker prompt and F-03 composer prompts when those stories are written. The prompts are version-controlled in `prompts/` per the TRD, so this is iterable post-launch.

---

## Action Items

| # | Owner | Item | Severity | Origin |
|---|-------|------|----------|--------|
| 1 | HYL | Decide: is "exactly 3 deep dives" a hard target or a typical count? Revisit when writing F-03 story. | Low | HYL |
| 2 | Architect (HYL) | Decide: add source-type / maturity classification to the `Item` model (touches F-01, F-02, F-03), or handle entirely in composer prompts? | **Medium** | Both subscribers |
| 3 | Engineer (HYL) | GitHub adapter should capture repo metadata (stars, last-commit, recent-release) — make this explicit in F-01 acceptance criteria when story is written. | Medium | Practitioner |
| 4 | Engineer (HYL) | F-02 ranking prompt design should treat paper vs blog provenance differently. | Medium | Researcher |
| 5 | Engineer (HYL) | F-03 composer prompts should include a maturity tag and condition-on-source-type framing (caveats for papers; practical-takeaway for tools). | Medium | Both subscribers |
| 6 | Engineer (HYL) | Decide: ship "novelty" as a real criterion (requires prior-issue state) or drop the word from F-02. | Low | Researcher |

---

## Next Steps

- Decide on Action Item #2 (Item-model change vs. prompt-only handling). If model change, bump PRD to v0.3.0 and adjust F-01/F-02/F-03 acceptance criteria. If prompt-only, the PRD can stay at v0.2.0; concerns are noted here and inform story-writing.
- Items #3–#6 are deferred to story-writing time; no PRD action needed unless #2 turns into a model change.
- Proceed to `/sdlc-studio epic` when #2 is decided.
