"""Tests for techletter.delivery.email — TC0210-TC0220 incl. TC0214 NEVER BCC."""

from __future__ import annotations

import smtplib
from datetime import UTC, datetime
from email.message import Message
from email.mime.multipart import MIMEMultipart

import pytest

from techletter.compose.issue import RenderedIssue
from techletter.delivery.base import Recipient
from techletter.delivery.email import EmailAdapter


class FakeSMTP:
    """Fake SMTP that records every send_message call."""

    def __init__(self) -> None:
        self.sent_messages: list[Message] = []
        self.quit_called = False
        self.raise_on_send: list[Exception] = []

    def send_message(self, msg: Message) -> dict[str, tuple[int, bytes]]:
        if self.raise_on_send:
            raise self.raise_on_send.pop(0)
        self.sent_messages.append(msg)
        return {}

    def quit(self) -> None:
        self.quit_called = True


@pytest.fixture
def issue() -> RenderedIssue:
    return RenderedIssue(
        issue_id="issue-2026-05-21",
        issue_date=datetime(2026, 5, 21, tzinfo=UTC),
        body_md="# AI Agent Weekly\n\n**Bold** content here.",
        content_sha256="x" * 64,
    )


# --- TC0210: zero recipients → SendReport(ok, 0, 0, 0) ------------------------


def test_zero_recipients_returns_ok_zero(issue: RenderedIssue) -> None:
    adapter = EmailAdapter(smtp_factory=lambda: FakeSMTP(), from_addr="bot@example.com")  # type: ignore[arg-type]
    report = adapter.send(issue, [])
    assert report.status == "ok"
    assert report.recipient_count == 0
    assert report.success_count == 0


# --- TC0211: SMTP_FROM missing → failed ---------------------------------------


def test_missing_from_addr_returns_failed(
    issue: RenderedIssue, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("SMTP_FROM", raising=False)
    adapter = EmailAdapter(smtp_factory=lambda: FakeSMTP())  # type: ignore[arg-type]
    report = adapter.send(issue, [Recipient(address="a@b.com")])
    assert report.status == "failed"
    assert "SMTP_FROM" in report.errors[0]


# --- TC0212: All recipients succeed → ok --------------------------------------


def test_all_succeed_returns_ok(issue: RenderedIssue) -> None:
    fake = FakeSMTP()
    adapter = EmailAdapter(smtp_factory=lambda: fake, from_addr="bot@example.com")  # type: ignore[arg-type]
    recipients = [Recipient(address=f"r{i}@example.com") for i in range(3)]
    report = adapter.send(issue, recipients)
    assert report.status == "ok"
    assert report.success_count == 3
    assert len(fake.sent_messages) == 3


# --- TC0213: Per-recipient failure isolation → partial ------------------------


def test_partial_failure_returns_partial(issue: RenderedIssue) -> None:
    fake = FakeSMTP()
    fake.raise_on_send = [smtplib.SMTPRecipientsRefused({"a@bad.com": (550, b"bad")})]
    adapter = EmailAdapter(smtp_factory=lambda: fake, from_addr="bot@example.com")  # type: ignore[arg-type]
    recipients = [
        Recipient(address="a@bad.com"),
        Recipient(address="b@ok.com"),
        Recipient(address="c@ok.com"),
    ]
    report = adapter.send(issue, recipients)
    assert report.status == "partial"
    assert report.success_count == 2
    assert report.failure_count == 1
    assert any("a@bad.com" in e for e in report.errors)


# --- TC0214: NEVER BCC (the load-bearing privacy test) -----------------------


def test_tc0214_never_uses_bcc(issue: RenderedIssue) -> None:
    """Each recipient gets their OWN message. To: header has exactly one
    address. Bcc and Cc headers are NEVER set."""
    fake = FakeSMTP()
    adapter = EmailAdapter(smtp_factory=lambda: fake, from_addr="bot@example.com")  # type: ignore[arg-type]
    recipients = [
        Recipient(address="alice@example.com"),
        Recipient(address="bob@example.com"),
        Recipient(address="carol@example.com"),
    ]
    adapter.send(issue, recipients)
    # Exactly one message per recipient
    assert len(fake.sent_messages) == 3
    # Each To: header is the SINGLE recipient
    for msg, expected_to in zip(
        fake.sent_messages,
        ["alice@example.com", "bob@example.com", "carol@example.com"],
        strict=True,
    ):
        assert msg["To"] == expected_to
        # CRITICAL: no Bcc, no Cc anywhere
        assert msg.get("Bcc") is None
        assert msg.get("Cc") is None
        # And the To: header lists exactly ONE address (no comma-separated leak)
        assert "," not in (msg["To"] or "")


# --- TC0215: One SMTP connection per batch ------------------------------------


def test_tc0215_one_smtp_connection_per_batch(issue: RenderedIssue) -> None:
    """The adapter opens ONE SMTP connection and sends all recipients through it."""
    factory_calls: list[FakeSMTP] = []

    def factory() -> FakeSMTP:
        s = FakeSMTP()
        factory_calls.append(s)
        return s

    adapter = EmailAdapter(smtp_factory=factory, from_addr="bot@example.com")  # type: ignore[arg-type]
    adapter.send(issue, [Recipient(address=f"r{i}@example.com") for i in range(5)])
    assert len(factory_calls) == 1  # only ONE connection opened
    assert factory_calls[0].quit_called  # and it was closed


# --- TC0216: Message has plain + html alternative parts ----------------------


def test_message_is_multipart_alternative(issue: RenderedIssue) -> None:
    fake = FakeSMTP()
    adapter = EmailAdapter(smtp_factory=lambda: fake, from_addr="bot@example.com")  # type: ignore[arg-type]
    adapter.send(issue, [Recipient(address="a@b.com")])
    msg = fake.sent_messages[0]
    assert isinstance(msg, MIMEMultipart)
    assert msg.get_content_subtype() == "alternative"
    payload = msg.get_payload()
    assert isinstance(payload, list)
    assert len(payload) == 2  # plain + html
    # Plain text is markdown-stripped
    plain = payload[0]
    assert isinstance(plain, Message)
    assert plain.get_content_type() == "text/plain"
    plain_text = plain.get_payload(decode=True).decode("utf-8")  # type: ignore[union-attr]
    assert "**" not in plain_text  # bold markers stripped
    # HTML alternative present
    html = payload[1]
    assert isinstance(html, Message)
    assert html.get_content_type() == "text/html"


# --- TC0217: SMTP connect failure → failed report -----------------------------


def test_smtp_connect_failure_returns_failed_report(issue: RenderedIssue) -> None:
    def bad_factory() -> FakeSMTP:
        raise ConnectionError("simulated DNS failure")

    adapter = EmailAdapter(smtp_factory=bad_factory, from_addr="bot@example.com")  # type: ignore[arg-type]
    report = adapter.send(issue, [Recipient(address="a@b.com")])
    assert report.status == "failed"
    assert any("SMTP connect failed" in e for e in report.errors)


# --- TC0218: Plain text is markdown-stripped ----------------------------------


def test_plain_text_is_markdown_stripped(issue: RenderedIssue) -> None:
    fake = FakeSMTP()
    adapter = EmailAdapter(smtp_factory=lambda: fake, from_addr="bot@example.com")  # type: ignore[arg-type]
    adapter.send(issue, [Recipient(address="a@b.com")])
    msg = fake.sent_messages[0]
    plain_part = msg.get_payload()[0]  # type: ignore[index]
    plain_text = plain_part.get_payload(decode=True).decode("utf-8")  # type: ignore[union-attr]
    assert "AI Agent Weekly" in plain_text
    assert "Bold" in plain_text
    assert "**Bold**" not in plain_text  # bold markers stripped
