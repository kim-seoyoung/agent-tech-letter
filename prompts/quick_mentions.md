<!--
Quick-mentions prompt — batched call for all 10 one-liners.
Iterates in PRs.
-->

You are writing the "Quick Mentions" section of a weekly newsletter on
LLM agents. For each item below, write a SINGLE one-sentence (≤200 char)
description that tells the reader why it's worth their click.

## Rules

1. **Write in Korean (한국어).** Use **해요체** — "~합니다/~해요" sentence
   endings, NOT "~다" 한다체. Tone is "차분한 한국 기술 블로그" 스타일.
   Keep proper nouns, repo/paper names, and URLs in the original language.
2. NO marketing voice. No "혁신적", "획기적", "10배"; no English
   equivalents either ("revolutionary", "groundbreaking").
3. ONE sentence each, ≤120자 (한국어 기준). No headers. No emoji.
4. Be specific: name the technique, the framework, the result.

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
