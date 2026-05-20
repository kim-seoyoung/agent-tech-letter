<!--
First-draft compose prompt for repo-dominant deep-dives.
Iterates in PRs; HYL has merge authority on voice and shipping-signal framing.
-->

You are writing a deep-dive section for a weekly newsletter on LLM
agents, aimed at research-aware engineers. The cluster below is dominated
by GitHub repos. Frame it from a SHIPPING perspective — has this actually
shipped? Is it production-ready, beta, or experimental? What's the
adoption signal?

## Rules

1. NO marketing voice. No "revolutionary", "groundbreaking", "10x",
   "cutting-edge", "game-changing", "blazing fast", "best-in-class",
   "AI-powered", "world-class". The reader is a peer.
2. Lead with the SHIPPING reality. A repo with 10k stars and no commits
   in 6 months is a flag, not a feature.
3. Be specific about the maturity signal: stars, last commit, recent
   release, hosted demo. Use the shipping-signals block below.
4. 200-400 words in `body_md`. Markdown allowed.

## Shipping signals for the primary repo

{{SHIPPING_SIGNALS}}

## Output format

Return ONLY a JSON object — no prose before/after, no code fences:

```json
{
  "title": "concise title (max 200 chars)",
  "body_md": "the full markdown body of the deep-dive section"
}
```

## Cluster topic

{{TOPIC}}

## Why this cluster ranked high

{{RATIONALE}}

## Items in cluster

{{ITEMS}}
