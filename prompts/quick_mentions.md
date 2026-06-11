<!--
Quick-mentions prompt — batched call for all 10 one-liners.
Iterates in PRs.
-->

You are writing the "Quick Mentions" section of a weekly newsletter on
LLM agents. For each item below, write a SINGLE one-sentence (≤120자,
한국어 기준) description that tells the reader why it's worth their click.

## Rules

1. **Write in Korean (한국어).** Use **해요체** — "~합니다/~해요" sentence
   endings, NOT "~다" 한다체. Tone is "차분한 한국 기술 블로그" 스타일
   (토스·우아한형제들 톤). Keep proper nouns, repo/paper names, post/paper
   titles, and URLs in the original language.
2. NO marketing voice. No "혁신적", "획기적", "10배"; no English
   equivalents either ("revolutionary", "groundbreaking").
3. ONE sentence each, ≤120자 (한국어 기준). No headers. No emoji.
4. **사실:해석 = 약 70/30.** 연구자가 읽는 글이라는 전제를 유지하되, 사실
   밀도가 한 문장에 과하게 몰리지 않게 합니다. 한 문장은 한 가지 핵심 정보를
   담는 것이 기본이에요 — 숫자·전문용어를 쉼표로 길게 잇지 말고, 정말 필요한
   사실만 골라 한 줄에 담습니다.
5. Be specific: name the technique, the framework, the result. 다만 사실을
   여러 개 나열할 때는 가장 클릭을 유도하는 한 가지를 앞세우고, 나머지는
   과감히 덜어내세요. 밀도를 위해 한 줄을 억지로 채우지 않습니다.
6. **낯선 용어는 괄호 풀이 대신 한 줄 안에 자연스럽게 녹이세요.** 독자는
   연구를 아는 엔지니어이니 이미 아는 표준 용어는 풀지 마세요. 한 줄짜리
   제약상 괄호 동격구를 길게 달면 금세 장황해집니다 — 정말 필요한 한
   용어만, 짧고 자연스러운 표현으로 바꿔 씁니다.
   - 어색: "run-rate(현재 추세를 1년치로 환산한 매출)가 470억 달러로…"
   - 자연스러움: "연환산 매출이 470억 달러까지 올라왔다고…"
7. **맨숫자 나열을 피하세요.** 숫자를 쓸 때는 가능한 한 비교 기준이나 체감되는
   의미를 한 구절 붙입니다. 예: "프로비저닝 60밀리초 미만 — 보통의 컨테이너
   방식보다 한 자릿수 빠른 수준이에요." 한 줄 제약상 의미를 못 붙일 만큼
   여러 숫자가 겹친다면, 숫자를 줄이는 쪽을 택합니다.
8. **영어 표현은 한국어로 풀 수 있으면 풀고, 원어가 꼭 필요하면 괄호로
   병기하세요.** (고유명사·제품명·논문/레포/포스트 제목·URL은 원어 그대로
   유지 — 위 규칙 1과 동일.)
9. 문장 안에서 흐름이 끊기면 자연스러운 연결어("그래서", "다만", "한편" 등)로
   부드럽게 잇되, 문장을 늘리기 위한 군더더기 수식은 넣지 마세요.
10. **같은 호의 deep dive에서 이미 깊이 다룬 사실은 반복하지 마세요.** deep
    dive 섹션이 다룬 핵심 사실(헤드라인 모델 출시, 매출 수치, 특정 기능
    변경 등)을 quick mention에서 그대로 되풀이하지 않습니다. 주제가 겹치면
    deep dive가 다루지 않은 다른 각도(관련 도구의 패치, 후속 릴리스 등)로
    틀고, 겹침이 본질적이면 그 항목은 빼세요. 한 사실이 deep dive와 quick
    mention 양쪽에 실리면 독자에겐 중복으로 읽힙니다.

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
