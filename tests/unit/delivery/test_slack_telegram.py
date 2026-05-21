"""Tests for techletter.delivery.{slack,telegram} — TC0240-TC0260 incl. TC0247."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from techletter.compose.issue import RenderedIssue
from techletter.delivery.base import Recipient
from techletter.delivery.slack import SlackAdapter
from techletter.delivery.telegram import TelegramAdapter


@pytest.fixture
def issue() -> RenderedIssue:
    return RenderedIssue(
        issue_id="issue-2026-05-21",
        issue_date=datetime(2026, 5, 21, tzinfo=UTC),
        body_md="# Tech-Letter\n\n**Bold** and a [link](https://example.com).",
        content_sha256="x" * 64,
    )


# --- Slack adapter tests ------------------------------------------------------


def test_slack_zero_recipients_returns_ok(issue: RenderedIssue) -> None:
    calls: list[tuple[str, dict[str, object]]] = []
    adapter = SlackAdapter(poster=lambda url, p: calls.append((url, p)))
    report = adapter.send(issue, [])
    assert report.status == "ok"
    assert calls == []


def test_slack_all_succeed(issue: RenderedIssue) -> None:
    calls: list[tuple[str, dict[str, object]]] = []
    adapter = SlackAdapter(poster=lambda url, p: calls.append((url, p)))
    recipients = [
        Recipient(address="https://hooks.slack.com/w1"),
        Recipient(address="https://hooks.slack.com/w2"),
    ]
    report = adapter.send(issue, recipients)
    assert report.status == "ok"
    assert report.success_count == 2


def test_slack_one_failure_partial(issue: RenderedIssue) -> None:
    seen_urls: list[str] = []

    def poster(url: str, payload: dict[str, object]) -> None:
        seen_urls.append(url)
        if "fail" in url:
            raise ConnectionError("boom")

    adapter = SlackAdapter(poster=poster)
    recipients = [
        Recipient(address="https://hooks.slack.com/ok"),
        Recipient(address="https://hooks.slack.com/fail"),
        Recipient(address="https://hooks.slack.com/ok2"),
    ]
    report = adapter.send(issue, recipients)
    assert report.status == "partial"
    assert report.success_count == 2
    assert report.failure_count == 1


def test_slack_splits_long_message(issue: RenderedIssue) -> None:
    """A long body produces multiple chunks; each chunk is one POST."""
    long_issue = RenderedIssue(
        issue_id=issue.issue_id,
        issue_date=issue.issue_date,
        body_md="\n".join(f"line {i}: " + "x" * 200 for i in range(50)),
        content_sha256="x" * 64,
    )
    posts: list[dict[str, object]] = []
    adapter = SlackAdapter(
        max_chars_per_message=500,
        poster=lambda url, p: posts.append(p),
    )
    adapter.send(long_issue, [Recipient(address="https://hooks.slack.com/w")])
    assert len(posts) >= 5  # multiple parts
    # Part markers present in multi-chunk sends
    assert any("Part 1" in str(p["text"]) for p in posts)


def test_slack_payload_has_mrkdwn_true(issue: RenderedIssue) -> None:
    posts: list[dict[str, object]] = []
    adapter = SlackAdapter(poster=lambda url, p: posts.append(p))
    adapter.send(issue, [Recipient(address="https://hooks.slack.com/w")])
    assert posts[0].get("mrkdwn") is True


# --- Telegram adapter tests ---------------------------------------------------


def test_telegram_zero_recipients_returns_ok(issue: RenderedIssue) -> None:
    calls: list[tuple[str, dict[str, object]]] = []
    adapter = TelegramAdapter(
        bot_token="123:fake",
        poster=lambda t, p: calls.append((t, p)),
    )
    report = adapter.send(issue, [])
    assert report.status == "ok"
    assert calls == []


def test_telegram_missing_token_returns_failed(
    issue: RenderedIssue, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    adapter = TelegramAdapter(bot_token="")  # explicitly empty
    report = adapter.send(issue, [Recipient(address="@channel1")])
    assert report.status == "failed"
    assert "TELEGRAM_BOT_TOKEN" in report.errors[0]


def test_telegram_all_succeed(issue: RenderedIssue) -> None:
    calls: list[tuple[str, dict[str, object]]] = []
    adapter = TelegramAdapter(
        bot_token="123:secret",
        poster=lambda t, p: calls.append((t, p)),
    )
    recipients = [Recipient(address="@chan1"), Recipient(address="@chan2")]
    report = adapter.send(issue, recipients)
    assert report.status == "ok"
    assert report.success_count == 2


def test_telegram_partial_failure(issue: RenderedIssue) -> None:
    def poster(token: str, payload: dict[str, object]) -> None:
        if "bad" in str(payload["chat_id"]):
            raise ConnectionError("simulated")

    adapter = TelegramAdapter(bot_token="123:secret", poster=poster)
    recipients = [
        Recipient(address="@ok1"),
        Recipient(address="@bad-chat"),
        Recipient(address="@ok2"),
    ]
    report = adapter.send(issue, recipients)
    assert report.status == "partial"
    assert report.success_count == 2


# --- TC0247: Bot token NEVER appears in any log/error output -----------------


def test_tc0247_bot_token_never_in_errors(
    issue: RenderedIssue, caplog: pytest.LogCaptureFixture
) -> None:
    """Per TC0247 (security-class): even when the adapter fails, no log
    line or SendReport.error string ever contains the bot token."""
    TOKEN = "1234567890:SECRET-TOKEN-VALUE-mustneverleak"

    def failing_poster(token: str, payload: dict[str, object]) -> None:
        # Simulate an error that might naively include the token
        raise RuntimeError(f"failed to post to {token}")

    adapter = TelegramAdapter(bot_token=TOKEN, poster=failing_poster)
    with caplog.at_level("WARNING"):
        report = adapter.send(issue, [Recipient(address="@somechannel")])
    # The token must NOT appear in any error string
    for err in report.errors:
        assert TOKEN not in err, f"token leaked into error: {err}"
    # And not in any log record
    for record in caplog.records:
        assert TOKEN not in record.getMessage()


def test_tc0247_redaction_replaces_token(issue: RenderedIssue) -> None:
    """When an error message would contain the token, _scrub replaces it."""
    TOKEN = "1234567890:SECRET-XYZ"

    def failing_poster(token: str, payload: dict[str, object]) -> None:
        raise RuntimeError(f"posted to https://api.telegram.org/bot{token}/sendMessage")

    adapter = TelegramAdapter(bot_token=TOKEN, poster=failing_poster)
    report = adapter.send(issue, [Recipient(address="@chan")])
    assert TOKEN not in report.errors[0]
    assert "[REDACTED]" in report.errors[0]


def test_telegram_splits_long_message(issue: RenderedIssue) -> None:
    long_issue = RenderedIssue(
        issue_id=issue.issue_id,
        issue_date=issue.issue_date,
        body_md="\n".join(f"line {i}: " + "x" * 200 for i in range(50)),
        content_sha256="x" * 64,
    )
    posts: list[dict[str, object]] = []
    adapter = TelegramAdapter(
        bot_token="123:secret",
        max_chars_per_message=500,
        poster=lambda t, p: posts.append(p),
    )
    adapter.send(long_issue, [Recipient(address="@chan")])
    assert len(posts) >= 5
    assert any("Part 1" in str(p["text"]) for p in posts)


def test_telegram_payload_has_parse_mode_html(issue: RenderedIssue) -> None:
    posts: list[dict[str, object]] = []
    adapter = TelegramAdapter(bot_token="123:secret", poster=lambda t, p: posts.append(p))
    adapter.send(issue, [Recipient(address="@chan")])
    assert posts[0]["parse_mode"] == "HTML"
