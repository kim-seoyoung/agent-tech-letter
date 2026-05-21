"""Tests for techletter.delivery.base - SendReport consistency (TC0206)."""

from __future__ import annotations

import pytest

from techletter.delivery.base import ChannelAdapter, Recipient, SendReport

# --- TC0206: SendReport consistency parametric (the load-bearing test) -------


@pytest.mark.parametrize(
    ("status", "success", "failure", "total", "should_pass"),
    [
        # status=ok: all succeed
        ("ok", 5, 0, 5, True),
        ("ok", 0, 0, 0, True),  # zero recipients edge case
        ("ok", 4, 1, 5, False),  # one failure → status should be partial
        ("ok", 0, 5, 5, False),  # all fail → status should be failed
        # status=partial: 0 < success < total
        ("partial", 3, 2, 5, True),
        ("partial", 5, 0, 5, False),  # no failures → status should be ok
        ("partial", 0, 5, 5, False),  # no successes → status should be failed
        # status=failed: success == 0 (and recipient_count > 0)
        ("failed", 0, 5, 5, True),
    ],
)
def test_tc0206_send_report_consistency(
    status: str, success: int, failure: int, total: int, should_pass: bool
) -> None:
    kwargs = {
        "channel": "email",
        "status": status,
        "recipient_count": total,
        "success_count": success,
        "failure_count": failure,
        "errors": [],
    }
    if should_pass:
        report = SendReport(**kwargs)  # type: ignore[arg-type]
        assert report.status == status
    else:
        with pytest.raises(ValueError):
            SendReport(**kwargs)  # type: ignore[arg-type]


# --- Recipient model -----------------------------------------------------------


def test_recipient_basic() -> None:
    r = Recipient(address="alice@example.com", label="Alice")
    assert r.address == "alice@example.com"
    assert r.label == "Alice"


def test_recipient_empty_address_raises() -> None:
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        Recipient(address="")


# --- ChannelAdapter Protocol structural test ----------------------------------


def test_channel_adapter_protocol_can_be_implemented() -> None:
    from datetime import UTC, datetime

    from techletter.compose.issue import RenderedIssue

    class FakeAdapter:
        name = "fake"

        def send(self, issue: RenderedIssue, recipients: list[Recipient]) -> SendReport:
            return SendReport(
                channel=self.name,
                status="ok",
                recipient_count=len(recipients),
                success_count=len(recipients),
                failure_count=0,
                errors=[],
            )

    adapter: ChannelAdapter = FakeAdapter()
    assert adapter.name == "fake"
    issue = RenderedIssue(
        issue_id="i1",
        issue_date=datetime(2026, 5, 21, tzinfo=UTC),
        body_md="# Body\n",
        content_sha256="x" * 64,
    )
    report = adapter.send(issue, [Recipient(address="a@b.com")])
    assert report.success_count == 1
