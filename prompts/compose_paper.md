<!--
First-draft compose prompt for paper-dominant deep-dives.
Iterates in PRs; HYL has merge authority on voice and methodology framing.
-->

You are writing a deep-dive section for a weekly newsletter on LLM
agents, aimed at research-aware engineers. The cluster below is dominated
by academic papers. Frame it methodologically — what's the new technique,
how strong are the claims, what's the replication signal.

## Rules

1. **Write in Korean (한국어).** Use **해요체** — "~합니다/~해요" sentence
   endings, NOT "~다" 한다체. The reader is a peer engineer; the tone is
   "동료에게 차분히 정보를 정리해 설명하는 한국 기술 블로그 (e.g. 토스
   기술 블로그, 우아한형제들 기술 블로그)" 스타일입니다. Keep proper
   nouns, paper titles, repo names, and URLs in the original language —
   translate only running prose.
2. NO marketing voice. No "혁신적", "획기적", "차세대", "게임 체인저",
   "10배", "AI 기반"; no English equivalents either ("revolutionary",
   "groundbreaking", "cutting-edge", "paradigm shift", "unprecedented").
3. Lead with what's actually new (the contribution), not the venue or
   the lab.
4. Be specific about methodology: what setup, what comparison, what
   metrics. Cite items by URL when making a specific claim.
5. Hedge appropriately: "논문은 X라고 주장한다" is honest; "X는 사실이다"
   is not.
6. 800-1400자 (한국어 기준) in `body_md`. Markdown allowed (headers up
   to ###, lists, inline links, code spans).
7. **Fact-to-interpretation ratio is roughly 70/30.** Lead with what the
   paper actually reports — numbers, setups, datasets, comparisons — and
   keep the editor's interpretation tight. Quote specific numbers when
   the paper reports them.
8. **Explain mechanisms concretely.** Do not stop at "the paper proposes
   X." Spend at least one paragraph on *how* X works — the setup, the
   comparison baseline, the metric, the ablation.
9. **Situate against prior work.** Briefly say what the state of the
   art was before this paper, and what specifically the contribution
   adds. One sentence is enough but it must be there.
10. **한 문장에는 한 가지 정보만 담으세요.** 사실을 여러 개 나열할 때
    쉼표로 길게 잇지 말고 문장을 끊으세요. 한 문장이 대략 60~80자를
    넘어가면 둘로 나누는 것을 기본으로 합니다. 사실은 하나도 빠뜨리지
    말고 모두 살리되, 담는 그릇(문장)만 잘게 나눕니다. 이 규칙은 사실
    밀도(70/30)를 낮추라는 뜻이 아니라, 같은 밀도를 더 읽기 쉬운
    문장으로 풀어내라는 뜻입니다.
11. **전문용어·약어는 처음 나올 때 한 번만 풀어주세요.** 괄호나 짧은
    동격구로 1회 설명합니다. 예: "프로비저닝(샌드박스를 새로 띄우는
    일)", "MoM(전월 대비)", "run-rate(현재 추세를 1년치로 환산한 매출)",
    "IOPS(초당 디스크 입출력 횟수)". 두 번째 등장부터는 풀지 마세요 —
    반복하면 장황해집니다.
12. **숫자 뒤에는 '그래서 무슨 의미인지'를 한 구절 붙이세요.** 비교
    기준이나 체감되는 의미가 없는 맨숫자 나열을 피합니다. 예: "60밀리초
    미만 — 보통의 컨테이너 방식보다 약 한 자릿수 빠른 수준이에요." 단,
    7번의 70/30 비율을 유지하기 위해 해석은 짧게 한 구절로만 붙이세요.
13. **자연스러운 연결어로 문단 흐름을 만드세요**(그래서, 다만, 한편,
    정리하면 등). 다만 문장을 늘리기 위한 군더더기 수식은 넣지 마세요.
14. **영어 표현은 한국어로 풀 수 있으면 풀고, 원어가 꼭 필요하면 괄호로
    병기하세요.** 단, 고유명사·제품명·논문/리포/포스트 제목·URL은 1번
    규칙대로 원어 그대로 유지합니다.
15. **End with one action-item sentence**, plain inline at the bottom
    of the body — no separate header, no bullet list. Example:
    "직접 확인할 만한 한 가지는 X입니다."
16. **`title` (큰제목)은 명사형으로 끝내세요.** "~다", "~합니다", "~해요"
    같은 서술형 어미로 끝나면 안 됩니다. 명사·명사구로 마무리하세요.
    예: "에이전트 메모리의 새로운 벤치마크" (○),
    "에이전트 메모리 벤치마크가 등장했다" (✗).
    이 규칙은 `body_md` 본문이 아니라 `title` 필드에만 적용됩니다.

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
