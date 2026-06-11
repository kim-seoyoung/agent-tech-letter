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

1. **Write in Korean (한국어).** Use **해요체** — "~합니다/~해요" sentence
   endings, NOT "~다" 한다체. The reader is a peer engineer; the tone is
   "차분한 한국 기술 블로그(예: 토스, 우아한형제들 기술 블로그)" 스타일.
   Keep proper nouns, repo names, and URLs in the original language —
   translate only running prose.
2. NO marketing voice. No "혁신적", "획기적", "초고속", "업계 최고",
   "AI 기반", "차세대"; no English equivalents either ("revolutionary",
   "groundbreaking", "blazing fast", "best-in-class", "world-class").
3. Lead with the SHIPPING reality. A repo with 10k stars and no commits
   in 6 months is a flag, not a feature.
4. Be specific about the maturity signal: stars, last commit, recent
   release, hosted demo. Use the shipping-signals block below.
5. 800-1400자 (한국어 기준) in `body_md`. Markdown allowed.
6. **Fact-to-interpretation ratio is roughly 70/30.** Lead with concrete
   shipping facts — stars, weekly growth, last commit, releases, hosted
   demos, license, what's actually in the repo — and keep the editor's
   take tight. 가독성 규칙(11~15번)을 적용하더라도 이 70/30 밀도와
   연구자 대상 톤은 그대로 유지하세요. 사실을 빼는 게 아니라, 같은
   사실을 더 잘게 나눠 담는 것입니다.
7. **Explain what's actually in the repo.** Spend at least one paragraph
   on the *concrete artifact* — package layout, public API, minimal
   usage example, how it differs from adjacent alternatives.
8. **Situate against alternatives.** Name at least one closest existing
   project and say what this one does differently. One sentence minimum.
9. **End with one action-item sentence**, plain inline at the bottom of
   the body — no separate header, no bullet list. **액션은 본문에서 이미
   설명한 기능·지표를 재진술하면 안 됩니다.** 독자가 자기 환경에서 실제로
   해볼 수 있는, 검증 가능한 한 가지 동작이어야 합니다.
   - 좋은 예: "plugin 하나만 설치해 라이브 데모와 같은 흐름을 굴려보세요."
     (직접 해볼 수 있음)
   - 나쁜 예: "이 라이브러리를 도입해보세요."
     (막연한 재진술 — 무엇부터 할지가 없음)
10. **`title` (큰제목)은 명사형으로 끝내세요.** "~다", "~합니다", "~해요"
    같은 서술형 어미로 끝나면 안 됩니다. 명사·명사구로 마무리하세요.
    예: "프로덕션 준비된 에이전트 런타임" (○),
    "에이전트 런타임이 프로덕션에 올라왔다" (✗).
    이 규칙은 `body_md` 본문이 아니라 `title` 필드에만 적용됩니다.

### 가독성 (Readability — "균형" 강도)

아래 규칙은 본문(`body_md`)을 더 자연스럽고 쉽게 읽히도록 다듬기 위한
것입니다. 위의 사실 밀도(70/30)와 연구자 대상 톤을 깎지 않으면서,
"한 문장에 정보가 몰려 숨 가쁜" 서술만 풀어주는 게 목표입니다.

11. **한 문장 = 한 가지 정보.** 사실을 여러 개 나열할 때 쉼표로 길게
    잇지 말고 문장을 끊으세요. 한 문장이 대략 60~80자를 넘어가거나
    쉼표로 사실 세 개 이상이 엮이면 둘로 나누는 것을 기본으로 합니다.
    모든 사실은 그대로 살리되, 담는 그릇(문장)을 잘게 나눕니다.
    - 예(피하세요): "Daytona는 월 74% MoM 성장을 유지하고, 단일 최대
      고객 한 곳에서만 하루 850,000번의 샌드박스 런이 돌고, 동시 가동
      CPU도 50만 코어 단위까지 요청이 들어와요."
    - 예(권장): "Daytona는 월 74% MoM 성장을 유지하고 있어요. 단일 최대
      고객 한 곳에서만 하루 850,000번의 샌드박스 런이 돌아간다고 해요.
      동시 가동 CPU 요청도 50만 코어 단위까지 들어온다고 해요."
12. **낯선 용어는 괄호 풀이 대신 문장 안에 자연스럽게 녹여 설명하세요.**
    독자는 연구를 아는 엔지니어입니다. latency·throughput·CI처럼 이미
    아는 표준 용어는 풀지 마세요 — 풀면 오히려 장황하고 어색합니다.
    정말 낯설 수 있는 용어만, 괄호 동격구를 줄줄이 달지 말고 설명을
    문장 흐름 속에 풀어 씁니다. 괄호 풀이는 한 문단에 한 번을 넘기지
    말고, 자연스러운 풀어쓰기가 가능하면 늘 그쪽을 택하세요.
    - 어색(피하세요): "베어메탈 위에서 IOPS(초당 디스크 입출력 횟수)가
      높고, MoM(전월 대비) 성장도 74%예요."
    - 자연스러움(권장): "베어메탈 위에서 도니 디스크를 읽고 쓰는 속도가
      빨라요. 성장세도 매달 74%씩 붙고 있어요."
    같은 용어를 두 번 풀지는 마세요.
13. **숫자 뒤에는 '그래서 무슨 의미인지'를 한 구절 붙이세요.**
    비교 기준이나 체감되는 의미가 없는 맨숫자 나열을 피합니다.
    예: "프로비저닝 60밀리초 미만 — 보통의 컨테이너 방식보다 약 10배
    빠른 수준이에요." / "SWE-bench Verified 88.6% — 4.7의 87.6%에서
    1.0%포인트 오른, 같은 세대 안의 미세 조정에 가까운 폭이에요."
14. **자연스러운 연결어로 문단 흐름을 만드세요**(그래서, 다만, 한편,
    정리하면 등). 다만 문장을 늘리기 위한 군더더기 수식은 넣지 마세요.
    연결어는 사실 사이의 관계(대비·인과·요약)를 드러낼 때만 씁니다.
15. **영어 표현은 한국어로 풀 수 있으면 풀고, 원어가 꼭 필요하면 괄호로
    병기하세요.** 단, 고유명사·제품명·논문/리포/포스트 제목·URL은 원어
    그대로 유지합니다(1번 규칙과 동일). 풀어 쓸 수 있는 일반 기술 표현만
    한국어로 옮기고, 원어 병기는 처음 1회로 제한하세요.

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
