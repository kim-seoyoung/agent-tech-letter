# Researcher Subscriber

## Quick Reference

| Attribute | Value |
|-----------|-------|
| **Category** | Stakeholder |
| **Amigo** | n/a |
| **Role** | Reader of the newsletter; works in or near LLM/agent research |
| **Age** | adult professional |
| **Experience** | reads papers regularly; comfortable with formal notation; engineer or applied ML/DS; ships LLM-backed features for a living |
| **Technical Level** | Expert (in their narrow research area and as a shipping engineer) |

## Identity

### Who They Are

A research-aware engineer — applied ML scientist, research engineer at an AI lab, a PhD student building real systems, or a senior practitioner who follows the literature closely while also shipping LLM-backed features for users. They live on the seam between "what papers are claiming" and "what actually holds up when you try to ship it." They subscribe to *Tech-Letter for HYL* because they need both halves: a credible read on research significance, and a credible read on what's crossing over into things they can actually use in production.

### Personality Traits

- **Methodologically careful:** "significant" means there's an actual contribution — a new benchmark, a clean ablation, a real result. Hype framings register as noise.
- **Production-grounded:** evaluates papers and tools through the lens of "what would it take to ship this to real users next quarter." Sceptical of results that won't survive contact with real prompts, real users, real cost constraints.
- **Citation-minded:** wants the original paper link more than the summary, and wants the summary to be accurate enough to decide whether to read the paper.

### Communication Style

- **Formality:** Moderate to formal in research framings; casual when talking shop about shipping
- **Verbosity:** Tolerates detail when warranted, especially around methodology and real-world results
- **Directness:** Precise; phrases pushback as a technical question rather than a complaint

## Professional Context

### Background

PhD or equivalent in CS / ML, or a senior engineer who reads at that level. Works somewhere on the spectrum from "research lab that also ships" (e.g., Anthropic / OpenAI / DeepMind-adjacent, applied research at a frontier-lab customer) to "engineering team that runs evals like researchers." Spends a meaningful part of every week reading recent papers; spends a meaningful part of every week writing code and tuning prompts that go live.

### Expertise Areas

- A specific sub-area of LLM agents (e.g., tool-use benchmarks, planning, RLHF, multi-agent coordination, agentic evaluation)
- Reading and critiquing experimental design — distinguishing real results from cherry-picked demos
- Production LLM engineering: function-calling, structured outputs, eval harnesses, cost/latency/quality trade-offs
- Translating a paper result into a "can we actually use this?" judgment

### Blind Spots

- May still under-weight non-research signal: a popular tool with no paper behind it can be more important week-over-week than the third incremental improvement on a benchmark they care about
- Limited time for items outside their sub-area; relies on the newsletter to triage
- Sometimes evaluates a paper's significance by how strong the methodology is, rather than by whether anyone will actually use the result

## Psychology

### Primary Goals

- Catch significant work in *adjacent* research areas they don't actively track.
- Identify which research is crossing over into things they can apply or ship.
- Avoid both extremes: hyping demos that won't generalise, *and* sleeping on slow-building research that's about to land.

### Hidden Concerns

- That the newsletter will drift toward hype, vendor announcements, or "tool of the week" content with no methodological substance.
- That summaries will obscure methodological issues that matter for whether a result is real and reproducible.
- That tools / patterns will be recommended without consideration of cost, latency, or eval performance — i.e., research-paper-style "look at this result!" without engineering reality.

### Decision Drivers

- **Values:** rigor; provenance (paper vs. blog vs. tweet); novelty over recency; replicability; honesty about production constraints.
- **Evidence:** the actual paper link, the actual eval table, the actual repo with running code. A summary that names methodology and limitations.
- **Red Flags:** marketing voice; missing citations; treating an Anthropic blog post and an arXiv paper as equivalent signal; benchmark numbers without code; "agent breakthroughs" that haven't been independently reproduced.

### Frustrations

- Newsletter summaries that don't distinguish "tweeted about a lot" from "actually advances the field."
- Summaries that flatten contributions into one-liners with no method/result distinction.
- Items that don't link to the primary source.
- Hype around an agent capability that, when they go look at the eval setup, is doing something they wouldn't trust in production.

### Delights

- A deep-dive section that nails a paper they'd been meaning to read, complete with a clear-eyed "here's what they actually showed."
- A bridge between two items: a recent paper + a tool that just shipped something the paper described.
- A quick-mention bullet that flags a non-headline paper from a venue they don't track but should.
- Honest reporting on which recent results have *not* replicated.

## Interaction Guide

### Questions They Typically Ask

- "Where is the paper / where can I read the full result?"
- "How is this different from $prior_work?"
- "What does the baseline they compare against actually do?"
- "Has anyone shipped this in production yet? At what scale?"
- "What's the eval cost?"

### What Makes Them Approve

- Summaries accurate enough to decide whether to read the original.
- A clear separation between "we think this matters because..." and "the authors claim..."
- Links to canonical sources (arXiv abstract page, not a tweet about it).
- Acknowledgement of production trade-offs when relevant (cost, latency, eval-on-real-data).

### What Makes Them Push Back

- Calling a blog post a "paper."
- Summaries that ignore obvious caveats (small sample size, no human eval, contamination concerns).
- Treating the same authors' follow-up paper as if it were independent confirmation.
- Hyping a paper whose result obviously won't survive a production cost or latency budget.

### Representative Quote

> "Tell me what the paper actually showed *and* whether anyone can run it for less than a thousand dollars per eval."

## Backstory

Has been on the receiving end of newsletter writeups about their own work that mischaracterized the contribution — either over-claiming or missing the actual point. Has also shipped at least one feature based on a hyped agent paper, only to discover months later that the paper's eval setup was nothing like real user traffic. Those two experiences make them sensitive in both directions: they don't trust summaries that don't engage with methodology, *and* they don't trust paper results that ignore production reality.

---

*Consult this persona when: deciding how summaries handle methodology and caveats, weighing arXiv papers against blog posts in ranking, deciding whether to surface "does it replicate?" or "does it ship?" framings in deep dives, designing the "deep dive" template for paper-shaped items, or evaluating whether to add or drop a content source.*
