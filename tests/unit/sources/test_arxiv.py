"""Tests for techletter.sources.arxiv - mirrors TS0001 TC0012-TC0021."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import pytest

# --- Fake arxiv lib objects ----------------------------------------------------


@dataclass
class FakeResult:
    """Mimics arxiv.Result enough for ArxivAdapter consumption."""

    entry_id: str
    title: str
    summary: str
    published: datetime
    primary_category: str


class FakeClient:
    """Mimics arxiv.Client; .results(search) is the only method called."""

    def __init__(self, results: Iterable[FakeResult] | None = None, raise_each: int = 0):
        self._results = list(results or [])
        self._raise_each = raise_each
        self._call_count = 0

    def results(self, search: object) -> Iterable[FakeResult]:
        self._call_count += 1
        if self._raise_each and self._call_count <= self._raise_each:
            raise ConnectionError(f"simulated transient failure attempt {self._call_count}")
        return iter(self._results)


def _now_utc() -> datetime:
    return datetime.now(UTC)


# --- TC0012: Adapter conformance ------------------------------------------------


def test_tc0012_arxiv_adapter_conformance() -> None:
    from techletter.sources.arxiv import ArxivAdapter
    from techletter.sources.base import SourceAdapter

    adapter: SourceAdapter = ArxivAdapter(client_factory=FakeClient)
    assert adapter.name == "arxiv"


# --- TC0013: Fetch returns recent items from configured categories --------------


def test_tc0013_window_filter_returns_only_recent_items() -> None:
    from techletter.sources.arxiv import ArxivAdapter

    now = _now_utc()
    results = [
        FakeResult(
            entry_id=f"http://arxiv.org/abs/2026.0000{i}",
            title=f"LLM agent paper {i}",
            summary="we study agents",
            published=now - timedelta(days=days),
            primary_category="cs.AI",
        )
        for i, days in enumerate([1, 2, 3, 5, 6, 8, 30])
    ]
    adapter = ArxivAdapter(client_factory=lambda: FakeClient(results=results))
    items = adapter.fetch(window_days=7)
    # 5 papers within window (1, 2, 3, 5, 6 days). days=8 and 30 are outside.
    assert len(items) == 5
    for item in items:
        assert item.source == "arxiv"
        assert item.item_kind == "paper"


# --- TC0014: source_subtype attribution per category ---------------------------


@pytest.mark.parametrize(
    "category",
    ["cs.AI", "cs.CL"],
)
def test_tc0014_source_subtype_attribution(category: str) -> None:
    from techletter.sources.arxiv import ArxivAdapter

    now = _now_utc()
    results = [
        FakeResult(
            entry_id="http://arxiv.org/abs/2026.00001",
            title="LLM agent survey",
            summary="we survey LLM agents",
            published=now - timedelta(days=1),
            primary_category=category,
        )
    ]
    adapter = ArxivAdapter(client_factory=lambda: FakeClient(results=results))
    items = adapter.fetch(window_days=7)
    assert len(items) == 1
    assert items[0].source_subtype == category


# --- TC0015: Keyword filter (case-insensitive) ---------------------------------


def test_tc0015_keyword_filter_applied() -> None:
    from techletter.sources.arxiv import ArxivAdapter

    now = _now_utc()
    results = [
        FakeResult(
            entry_id="http://arxiv.org/abs/p1",
            title="LLM Agent for Tool Use",
            summary="we build an agent",
            published=now - timedelta(days=1),
            primary_category="cs.AI",
        ),
        FakeResult(
            entry_id="http://arxiv.org/abs/p2",
            title="Agentic ReAct survey",
            summary="agent agent agent",
            published=now - timedelta(days=2),
            primary_category="cs.AI",
        ),
        FakeResult(
            entry_id="http://arxiv.org/abs/p3",
            title="Tool-use for code",
            summary="tools and tools",
            published=now - timedelta(days=3),
            primary_category="cs.CL",
        ),
        FakeResult(
            entry_id="http://arxiv.org/abs/p4",
            title="Computer Vision Segmentation",
            summary="we segment images",
            published=now - timedelta(days=1),
            primary_category="cs.AI",
        ),
        FakeResult(
            entry_id="http://arxiv.org/abs/p5",
            title="Cryptographic Protocols",
            summary="key exchange",
            published=now - timedelta(days=1),
            primary_category="cs.AI",
        ),
    ]
    adapter = ArxivAdapter(
        keywords=["agent", "tool-use"],
        client_factory=lambda: FakeClient(results=results),
    )
    items = adapter.fetch(window_days=7)
    assert len(items) == 3
    titles = {i.title for i in items}
    assert "LLM Agent for Tool Use" in titles
    assert "Agentic ReAct survey" in titles
    assert "Tool-use for code" in titles


def test_tc0015b_keyword_filter_case_insensitive() -> None:
    from techletter.sources.arxiv import ArxivAdapter

    now = _now_utc()
    results = [
        FakeResult(
            entry_id="http://arxiv.org/abs/p1",
            title="AGENT-Based Reasoning",  # uppercase
            summary="lower case agent",
            published=now - timedelta(days=1),
            primary_category="cs.AI",
        )
    ]
    adapter = ArxivAdapter(keywords=["agent"], client_factory=lambda: FakeClient(results=results))
    items = adapter.fetch(window_days=7)
    assert len(items) == 1


# --- TC0016: Empty result is valid ---------------------------------------------


def test_tc0016_empty_result_returns_empty_list() -> None:
    from techletter.sources.arxiv import ArxivAdapter

    adapter = ArxivAdapter(client_factory=lambda: FakeClient(results=[]))
    items = adapter.fetch(window_days=7)
    assert items == []


# --- TC0017: Retry on transient failure (503x2 then 200) -----------------------


def test_tc0017_retry_succeeds_after_transient_failures() -> None:
    from techletter.sources.arxiv import ArxivAdapter

    now = _now_utc()
    success_results = [
        FakeResult(
            entry_id="http://arxiv.org/abs/p1",
            title="agent paper",
            summary="abstract",
            published=now - timedelta(days=1),
            primary_category="cs.AI",
        )
    ]

    class FlakyClient(FakeClient):
        def __init__(self) -> None:
            super().__init__(results=success_results, raise_each=2)

    # The retry happens INSIDE the adapter's _fetch_results; reuse a single client
    # so its internal call_count persists across attempts.
    shared = FlakyClient()

    adapter = ArxivAdapter(client_factory=lambda: shared)
    items = adapter.fetch(window_days=7)
    assert len(items) == 1
    assert shared._call_count >= 3  # 2 failures + 1 success


# --- TC0018: Permanent failure raises SourceFetchError --------------------------


def test_tc0018_exhausted_retries_raise_source_fetch_error() -> None:
    from techletter.sources.arxiv import ArxivAdapter
    from techletter.sources.base import SourceFetchError

    shared = FakeClient(results=[], raise_each=999)
    adapter = ArxivAdapter(client_factory=lambda: shared)
    with pytest.raises(SourceFetchError) as exc_info:
        adapter.fetch(window_days=7)
    assert "arxiv" in str(exc_info.value).lower()


# --- TC0019: window_days = -1 raises ValueError --------------------------------


def test_tc0019_negative_window_raises_value_error() -> None:
    from techletter.sources.arxiv import ArxivAdapter

    adapter = ArxivAdapter(client_factory=FakeClient)
    with pytest.raises(ValueError):
        adapter.fetch(window_days=-1)


# --- TC0020: window_days = 1000 clamped to 365 ---------------------------------


def test_tc0020_oversized_window_clamped_to_365(caplog: pytest.LogCaptureFixture) -> None:
    from techletter.sources.arxiv import ArxivAdapter

    now = _now_utc()
    results = [
        FakeResult(
            entry_id="http://arxiv.org/abs/p1",
            title="agent paper",
            summary="abstract",
            published=now - timedelta(days=400),  # outside even 365 window
            primary_category="cs.AI",
        ),
        FakeResult(
            entry_id="http://arxiv.org/abs/p2",
            title="agent paper",
            summary="abstract",
            published=now - timedelta(days=200),  # inside 365 window
            primary_category="cs.AI",
        ),
    ]
    adapter = ArxivAdapter(client_factory=lambda: FakeClient(results=results))
    with caplog.at_level("WARNING"):
        items = adapter.fetch(window_days=1000)
    # Only the 200-day-old paper is within the clamped 365 window
    assert len(items) == 1
    # A warning about clamping should have been logged
    assert any("365" in r.message or "clamp" in r.message.lower() for r in caplog.records)


# --- TC0021: Long abstract truncated to 1000 chars -----------------------------


def test_tc0021_long_abstract_truncated_to_1000_chars() -> None:
    from techletter.sources.arxiv import ArxivAdapter

    now = _now_utc()
    long_abstract = "agent " * 250  # ~1500 chars
    results = [
        FakeResult(
            entry_id="http://arxiv.org/abs/p1",
            title="agent paper",
            summary=long_abstract,
            published=now - timedelta(days=1),
            primary_category="cs.AI",
        )
    ]
    adapter = ArxivAdapter(client_factory=lambda: FakeClient(results=results))
    items = adapter.fetch(window_days=7)
    assert len(items) == 1
    assert len(items[0].summary_excerpt) <= 1000
