"""Tests for techletter.delivery.registry."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from techletter.compose.issue import RenderedIssue
from techletter.delivery.base import Recipient, SendReport
from techletter.delivery.config import (
    ChannelsConfig,
    EmailConfig,
    SlackConfig,
    SubscribersConfig,
    TelegramConfig,
)
from techletter.delivery.registry import (
    ChannelRegistry,
    aggregate_reports,
    build_channel_registry,
)


@pytest.fixture
def issue() -> RenderedIssue:
    return RenderedIssue(
        issue_id="i1",
        issue_date=datetime(2026, 5, 21, tzinfo=UTC),
        body_md="# Body",
        content_sha256="x" * 64,
    )


class FakeChannel:
    """Minimal ChannelAdapter for registry testing."""

    def __init__(
        self, name: str, *, report: SendReport | None = None, raise_exc: Exception | None = None
    ) -> None:
        self.name = name
        self._report = report
        self._exc = raise_exc
        self.calls: list[tuple[RenderedIssue, list[Recipient]]] = []

    def send(self, issue: RenderedIssue, recipients: list[Recipient]) -> SendReport:
        self.calls.append((issue, recipients))
        if self._exc:
            raise self._exc
        if self._report is not None:
            return self._report
        return SendReport(
            channel=self.name,
            status="ok",
            recipient_count=len(recipients),
            success_count=len(recipients),
            failure_count=0,
            errors=[],
        )


# --- ChannelRegistry.send_all -------------------------------------------------


def test_send_all_empty_registry(issue: RenderedIssue) -> None:
    reg = ChannelRegistry()
    assert reg.send_all(issue) == []


def test_send_all_calls_each_adapter(issue: RenderedIssue) -> None:
    email_ch = FakeChannel("email")
    slack_ch = FakeChannel("slack")
    reg = ChannelRegistry(
        adapters={"email": email_ch, "slack": slack_ch},
        recipients={
            "email": [Recipient(address="a@b.com")],
            "slack": [Recipient(address="https://hooks/x")],
        },
    )
    reports = reg.send_all(issue)
    assert len(reports) == 2
    assert {r.channel for r in reports} == {"email", "slack"}
    assert len(email_ch.calls) == 1
    assert len(slack_ch.calls) == 1


def test_send_all_isolates_adapter_exception(issue: RenderedIssue) -> None:
    """One adapter raising doesn't abort the other channels."""
    bad = FakeChannel("email", raise_exc=RuntimeError("DNS down"))
    good = FakeChannel("slack")
    reg = ChannelRegistry(
        adapters={"email": bad, "slack": good},
        recipients={
            "email": [Recipient(address="a@b.com")],
            "slack": [Recipient(address="https://hooks/x")],
        },
    )
    reports = reg.send_all(issue)
    by_channel = {r.channel: r for r in reports}
    assert by_channel["email"].status == "failed"
    assert by_channel["slack"].status == "ok"


# --- build_channel_registry from config ---------------------------------------


def test_build_registry_only_enabled() -> None:
    channels = ChannelsConfig(
        email=EmailConfig(enabled=True),
        slack=SlackConfig(enabled=False),
        telegram=TelegramConfig(enabled=True),
    )
    subscribers = SubscribersConfig(
        email=["alice@example.com", "bob@example.com"],
        slack=["https://hooks.slack.com/x"],
        telegram=["@chan1"],
    )
    reg = build_channel_registry(channels, subscribers)
    assert "email" in reg.adapters
    assert "slack" not in reg.adapters  # disabled
    assert "telegram" in reg.adapters
    assert len(reg.recipients["email"]) == 2
    # slack disabled → no recipients map entry either
    assert "slack" not in reg.recipients
    assert len(reg.recipients["telegram"]) == 1


def test_build_registry_empty_subscribers_ok() -> None:
    """A channel can be enabled with zero subscribers — just no-op send."""
    channels = ChannelsConfig(email=EmailConfig(enabled=True))
    subscribers = SubscribersConfig(email=[])
    reg = build_channel_registry(channels, subscribers)
    assert "email" in reg.adapters
    assert reg.recipients["email"] == []


# --- aggregate_reports --------------------------------------------------------


def test_aggregate_reports_all_ok() -> None:
    reports = [
        SendReport(
            channel="email",
            status="ok",
            recipient_count=3,
            success_count=3,
            failure_count=0,
            errors=[],
        ),
        SendReport(
            channel="slack",
            status="ok",
            recipient_count=1,
            success_count=1,
            failure_count=0,
            errors=[],
        ),
    ]
    summary = aggregate_reports(reports)
    assert summary["total_recipients"] == 4
    assert summary["total_success"] == 4
    assert summary["total_failure"] == 0
    assert summary["overall"] == "ok"


def test_aggregate_reports_mixed() -> None:
    reports = [
        SendReport(
            channel="email",
            status="partial",
            recipient_count=5,
            success_count=3,
            failure_count=2,
            errors=[],
        ),
        SendReport(
            channel="slack",
            status="ok",
            recipient_count=1,
            success_count=1,
            failure_count=0,
            errors=[],
        ),
    ]
    summary = aggregate_reports(reports)
    assert summary["total_success"] == 4
    assert summary["total_failure"] == 2
    assert summary["overall"] == "partial"
    assert summary["by_channel"] == {"email": "partial", "slack": "ok"}


def test_aggregate_reports_all_failed() -> None:
    reports = [
        SendReport(
            channel="email",
            status="failed",
            recipient_count=2,
            success_count=0,
            failure_count=2,
            errors=["x"],
        ),
    ]
    summary = aggregate_reports(reports)
    assert summary["overall"] == "failed"


def test_aggregate_reports_empty() -> None:
    summary = aggregate_reports([])
    assert summary["overall"] == "ok"
    assert summary["total_recipients"] == 0
