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

1. **Write in Korean (한국어).** Use **해요체** — "~합니다/~해요" sentence
   endings, NOT "~다" 한다체. The reader is a peer engineer; the tone is
   "차분한 한국 기술 블로그(예: 토스, 우아한형제들 기술 블로그)" 스타일.
   Keep proper nouns, post titles, and URLs in the original language —
   translate only running prose.
2. NO marketing voice. No "혁신적", "획기적", "차세대", "AI 기반",
   "게임 체인저"; no English equivalents either ("revolutionary",
   "groundbreaking", "cutting-edge", "game-changing", "next-generation").
3. Lead with what the post actually argues. If multiple posts in the
   cluster make the same point, say so. If only one does, hedge.
4. 800-1400자 (한국어 기준) in `body_md`. Markdown allowed.
5. **Fact-to-interpretation ratio is roughly 70/30.** Lead with what the
   post(s) actually say — specific numbers, dated claims, named systems,
   quotes — and keep the editor's take tight. Quote specific numbers
   when the posts cite them. 이 70/30 비율과 연구자 대상 톤은 아래 가독성
   규칙(10~14)을 적용한 뒤에도 그대로 유지하세요. 문장을 쉽게 푼다고 해서
   사실을 빼거나 뭉뚱그리면 안 됩니다 — 모든 사실은 그대로 살리되, 담는
   그릇(문장)만 잘게 나눕니다.
6. **Reconstruct the argument concretely.** Spend at least one paragraph
   walking through the chain of reasoning or evidence the post uses.
   메커니즘이나 아티팩트는 "무엇을 어떻게" 수준까지 구체적으로 풀어주세요.
7. **Situate against the wider conversation.** What was the state of
   the discussion before this post, and what specifically does it shift?
   선행 연구나 가장 가까운 대안과 견주어 무엇이 같고 무엇이 다른지
   한 문장 이상으로 짚으세요.
8. **End with one action-item sentence**, plain inline at the bottom of
   the body — no separate header, no bullet list. **액션은 본문에서 이미
   설명한 기능·결과를 재진술하면 안 됩니다.** 독자가 자기 환경에서 실제로
   해볼 수 있는, 검증 가능한 한 가지 동작이어야 합니다.
   - 좋은 예: "평균 sandbox lifetime이 1분 미만인지부터 측정해보세요."
     (구체적이고 직접 확인할 수 있음)
   - 나쁜 예: "user 턴 뒤 system 메시지 기능을 활용해보세요."
     (방금 설명한 기능의 재진술 — 새 정보가 없음)
9. **`title` (큰제목)은 명사형으로 끝내세요.** "~다", "~합니다", "~해요"
   같은 서술형 어미로 끝나면 안 됩니다. 명사·명사구로 마무리하세요.
   예: "RAG 파이프라인의 재현성 문제" (○),
   "RAG 파이프라인이 재현되지 않는다" (✗).
   이 규칙은 `body_md` 본문이 아니라 `title` 필드에만 적용됩니다.

### 가독성 규칙 (강도: "균형" — 사실 밀도와 연구자 톤은 위 5번 그대로 유지)

10. **한 문장 = 한 가지 정보.** 사실을 여러 개 나열할 때 쉼표로 길게
    잇지 말고 문장을 끊으세요. 한 문장이 대략 60~80자를 넘어가면 둘로
    나누는 것을 기본으로 합니다. 숫자·전문용어가 한 문장에 몰려 밀도가
    높아지면, 정보를 빼지 말고 문장을 나눠 분산시키세요.
    예: "Daytona는 월 74% MoM 성장률을 유지하고, 단일 최대 고객 한
    곳에서만 하루 850,000번의 샌드박스 런이 돌고, 동시 가동 CPU도 50만
    코어 단위까지 요청이 들어와요." (✗ — 한 문장에 세 사실)
    → "Daytona는 월 74%의 MoM(전월 대비) 성장률을 유지하고 있어요.
    단일 최대 고객 한 곳에서만 하루 850,000번의 샌드박스 런이 돌아가요.
    동시 가동 CPU도 50만 코어 단위까지 요청이 들어온다고 해요." (○)
11. **낯선 용어는 괄호 풀이 대신 문장 안에 자연스럽게 녹여 설명하세요.**
    독자는 연구를 아는 엔지니어입니다. latency·throughput·fine-tuning
    처럼 이미 아는 표준 용어는 풀지 마세요 — 풀면 오히려 장황하고
    어색합니다. 정말 낯설 수 있는 용어만, 괄호 동격구를 줄줄이 달지 말고
    설명을 문장 흐름 속에 풀어 씁니다. 괄호 풀이는 한 문단에 한 번을
    넘기지 말고, 자연스러운 풀어쓰기가 가능하면 늘 그쪽을 택하세요.
    - 어색(피하세요): "EBS 같은 네트워크 스토리지를 거치지 않아
      IOPS(초당 디스크 입출력 횟수)가 높고, run-rate(현재 추세를
      1년치로 환산한 매출)도 470억 달러예요."
    - 자연스러움(권장): "EBS 같은 네트워크 스토리지를 거치지 않고
      머신 디스크를 직접 쓰니 읽고 쓰는 속도가 빨라요. 이 성장세가 1년
      이어진다고 보면 매출은 470억 달러 규모예요."
    같은 용어를 두 번 풀지는 마세요.
12. **숫자 뒤에는 '그래서 무슨 의미인지'를 한 구절 붙이세요.** 비교
    기준이나 체감되는 의미가 없는 맨숫자 나열을 피합니다.
    예: "프로비저닝 시간은 60밀리초 미만이에요 — 보통의 컨테이너 방식보다
    약 10배 빠른 수준이에요." 단, 사실을 살리는 범위에서 붙이고, 의미가
    이미 명백하면 군더더기 해설을 덧대지 마세요.
13. **자연스러운 연결어로 문단 흐름을 만드세요**(그래서, 다만, 한편,
    정리하면 등). 단, 문장을 늘리기 위한 군더더기 수식은 넣지 마세요.
    연결어는 흐름을 잡는 용도이지 분량을 채우는 용도가 아닙니다.
14. **영어 표현은 한국어로 풀 수 있으면 풀고, 원어가 꼭 필요하면 괄호로
    병기하세요.** 단, 고유명사·제품명·논문/리포/포스트 제목·URL은 원어
    그대로 유지합니다(규칙 1과 동일). 인용구(예: "modest but tangible
    improvement")도 원문 그대로 둡니다.

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
