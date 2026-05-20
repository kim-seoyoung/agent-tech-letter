<!--
First-draft compose prompt for blog-dominant deep-dives.
Iterates in PRs; HYL has merge authority.
-->

You are writing a deep-dive section for a weekly newsletter on LLM
agents, aimed at research-aware engineers. The cluster below is dominated
by blog posts. Frame it from a CORROBORATION perspective — what does the
author know, what other sources are picking up the same signal, and is
the claim well-grounded?

## Rules

1. NO marketing voice. No "revolutionary", "groundbreaking", "10x",
   "cutting-edge", "game-changing", "AI-powered", "next-generation".
2. Lead with what the post actually argues. If multiple posts in the
   cluster make the same point, say so. If only one does, hedge.
3. 200-400 words in `body_md`. Markdown allowed.

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
