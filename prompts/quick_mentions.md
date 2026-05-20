<!--
Quick-mentions prompt — batched call for all 10 one-liners.
Iterates in PRs.
-->

You are writing the "Quick Mentions" section of a weekly newsletter on
LLM agents. For each item below, write a SINGLE one-sentence (≤200 char)
description that tells the reader why it's worth their click.

## Rules

1. NO marketing voice. No "revolutionary", "groundbreaking", "10x".
   The reader is a peer.
2. ONE sentence each. No headers. No emoji.
3. Be specific: name the technique, the framework, the result.

## Output format

Return ONLY a JSON object — no prose before/after, no code fences:

```json
{
  "mentions": [
    {"item_index": 0, "one_liner": "..."},
    {"item_index": 1, "one_liner": "..."}
  ]
}
```

## Items

{{ITEMS}}
