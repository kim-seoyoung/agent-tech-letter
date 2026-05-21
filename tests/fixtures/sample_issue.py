"""Canonical sample RenderedIssue used by the golden fixture tests (EP0005)."""

from __future__ import annotations

from datetime import UTC, datetime

from techletter.compose.issue import RenderedIssue, assemble_issue
from techletter.compose.types import DeepDive, QuickMention


def make_sample_issue() -> RenderedIssue:
    """A deterministic 3-deep-dive / 5-quick-mention issue.

    Kept small + simple so manual diffs of golden HTML are tractable.
    Increase the counts (and re-bless fixtures) if we want richer coverage.
    """
    deep_dives = [
        DeepDive(
            cluster_id="c1",
            title="Diffusion-as-Optimizer 논문",
            body_md=(
                "Diffusion 모델을 일반 비볼록 최적화 문제의 sampler로 재해석한다.\n"
                "**핵심 결과:** ImageNet-scale 벤치마크에서 5% 개선.\n"
                "주의: production 환경에서 latency가 1.6x 늘어남."
            ),
            item_kind="paper",
            primary_url="https://arxiv.org/abs/2505.10001",  # type: ignore[arg-type]
            source_count=3,
        ),
        DeepDive(
            cluster_id="c2",
            title="vLLM v0.7 릴리스",
            body_md=(
                "PagedAttention의 NUMA-aware variant 추가. continuous batching이 "
                "default가 됐고 throughput이 14% 향상.\n\n"
                "- 신규 `--enable-numa-paging` 플래그\n"
                "- KV-cache eviction policy 교체 가능"
            ),
            item_kind="repo",
            primary_url="https://github.com/vllm-project/vllm",  # type: ignore[arg-type]
            source_count=2,
            maturity="production-ready",
        ),
        DeepDive(
            cluster_id="c3",
            title="MoE routing 블로그",
            body_md=(
                "Expert routing의 entropy-collapse 문제에 대한 분석. "
                "auxiliary loss 없이도 안정적으로 학습되는 변형 제안."
            ),
            item_kind="blog_post",
            primary_url="https://latent.space/p/moe-routing-2026",  # type: ignore[arg-type]
            source_count=1,
        ),
    ]
    quick_mentions = [
        QuickMention(
            title=f"Quick item {i}",
            url=f"https://example.com/q/{i}",  # type: ignore[arg-type]
            source="arxiv",
            item_kind="paper",
            one_liner=f"A one-line summary for item {i}.",
        )
        for i in range(5)
    ]
    return assemble_issue(
        issue_id="issue-2026-05-21",
        issue_date=datetime(2026, 5, 21, 0, 0, 0, tzinfo=UTC),
        deep_dives=deep_dives,
        quick_mentions=quick_mentions,
        source_counts={"arxiv": 3, "github": 1, "rss": 2},
    )
