"""US0028: Publisher Protocol + PublishResult + PublisherError tests."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from techletter.compose.issue import RenderedIssue, assemble_issue
from techletter.compose.types import DeepDive
from techletter.delivery.publishers import (
    Publisher,
    PublisherError,
    PublishResult,
)


def _result(**overrides) -> PublishResult:
    defaults = dict(
        url="https://example.com/issues/2026-05-21-abc.html",
        path="issues/2026-05-21-abc.html",
        published_at=datetime(2026, 5, 21, tzinfo=UTC),
        publisher_name="github_pages",
        commit_sha="a" * 40,
    )
    defaults.update(overrides)
    return PublishResult(**defaults)


def test_AC1_publish_result_constructs():
    r = _result()
    assert r.url.startswith("https://")
    assert r.commit_sha == "a" * 40


def test_AC2_publish_result_frozen():
    r = _result()
    with pytest.raises(ValidationError):
        r.url = "https://other"  # type: ignore[misc]


def test_AC2_publish_result_rejects_empty_url():
    with pytest.raises(ValidationError):
        _result(url="")


def test_AC2_publish_result_rejects_unknown_field():
    with pytest.raises(ValidationError):
        PublishResult(  # type: ignore[call-arg]
            url="https://e.com",
            path="x",
            published_at=datetime.now(UTC),
            publisher_name="p",
            unknown="boom",
        )


def test_AC2_publish_result_commit_sha_optional():
    r = _result(commit_sha=None)
    assert r.commit_sha is None


def test_AC3_publish_result_json_round_trip():
    r = _result()
    restored = PublishResult.model_validate_json(r.model_dump_json())
    assert restored == r


def test_AC4_top_level_reexports_resolve():
    from techletter.delivery.publishers import (
        Publisher as P,
    )
    from techletter.delivery.publishers import (
        PublisherError as E,
    )
    from techletter.delivery.publishers import (
        PublishResult as R,
    )

    assert P is Publisher
    assert E is PublisherError
    assert R is PublishResult


def test_AC4b_publisher_error_is_exception_subclass():
    assert issubclass(PublisherError, Exception)

    e = PublisherError("dirty worktree at /tmp/foo")
    assert str(e) == "dirty worktree at /tmp/foo"

    with pytest.raises(PublisherError):
        raise PublisherError("test")


def test_AC1_publisher_protocol_structural_conformance():
    """A class with `name` + `publish` satisfies the Protocol."""

    class FakePublisher:
        name: str = "fake"

        def publish(self, issue: RenderedIssue) -> PublishResult:
            return _result()

    # Structural typing: assignment to a Publisher-typed variable works.
    p: Publisher = FakePublisher()
    issue = assemble_issue(
        issue_id="issue-2026-05-21",
        issue_date=datetime(2026, 5, 21, tzinfo=UTC),
        deep_dives=[
            DeepDive(
                cluster_id=f"c{i}",
                title=f"t{i}",
                body_md="x",
                item_kind="paper",
                primary_url="https://e.com",  # type: ignore[arg-type]
                source_count=1,
            )
            for i in range(2)
        ],
        quick_mentions=[],
    )
    result = p.publish(issue)
    assert isinstance(result, PublishResult)
