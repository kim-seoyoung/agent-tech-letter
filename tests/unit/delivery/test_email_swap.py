"""US0027: EmailAdapter swap to html_email.render — additional invariants.

Covers AC1 (no _wrap_html), AC2 (renderer wired), AC3 (called once),
AC4 (privacy invariant unchanged), AC5 (plain-text unchanged),
AC8 (idempotency preserved).
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock

from techletter.compose.issue import RenderedIssue, assemble_issue, content_hash
from techletter.compose.types import DeepDive
from techletter.delivery import email as email_mod
from techletter.delivery.base import Recipient
from techletter.delivery.email import EmailAdapter


class _FakeSMTP:
    """Minimal SMTP double — counts connections + send_message calls."""

    instance_count = 0

    def __init__(self) -> None:
        _FakeSMTP.instance_count += 1
        self.sent: list[object] = []
        self.quit_called = False

    def send_message(self, msg) -> None:
        self.sent.append(msg)

    def quit(self) -> None:
        self.quit_called = True


def _issue() -> RenderedIssue:
    return assemble_issue(
        issue_id="issue-2026-05-21",
        issue_date=datetime(2026, 5, 21, tzinfo=UTC),
        deep_dives=[
            DeepDive(
                cluster_id=f"c{i}",
                title=f"t{i}",
                body_md=f"body {i}",
                item_kind="paper",
                primary_url="https://example.com",  # type: ignore[arg-type]
                source_count=1,
            )
            for i in range(2)
        ],
        quick_mentions=[],
    )


def test_AC1_wrap_html_symbol_removed():
    """Hard delete: no _wrap_html survives anywhere in the email module."""
    src = Path(email_mod.__file__).read_text(encoding="utf-8")
    assert "_wrap_html" not in src

    # Also: instance has no such attribute
    adapter = EmailAdapter(smtp_factory=_FakeSMTP, from_addr="bot@example.com")
    assert not hasattr(adapter, "_wrap_html")


def test_AC3_renderer_called_once_per_send_regardless_of_recipients(monkeypatch):
    """Critical: html_email.render must be cached across all N recipients."""
    spy = MagicMock(return_value="<html>spied</html>")
    monkeypatch.setattr("techletter.delivery.email.html_email.render", spy)
    _FakeSMTP.instance_count = 0

    adapter = EmailAdapter(smtp_factory=_FakeSMTP, from_addr="bot@example.com")
    recipients = [Recipient(address=f"r{i}@example.com") for i in range(5)]
    report = adapter.send(_issue(), recipients)

    assert report.success_count == 5
    spy.assert_called_once()


def test_AC2_AC5_html_part_is_renderer_output_plain_unchanged(monkeypatch):
    """text/html ← html_email.render, text/plain ← strip_markdown(body_md)."""
    monkeypatch.setattr(
        "techletter.delivery.email.html_email.render",
        lambda issue: "<html>PHANTOM_HTML</html>",
    )
    fake = _FakeSMTP()
    adapter = EmailAdapter(smtp_factory=lambda: fake, from_addr="bot@example.com")
    issue = _issue()
    adapter.send(issue, [Recipient(address="alice@example.com")])

    assert len(fake.sent) == 1
    msg = fake.sent[0]
    payloads = msg.get_payload()
    assert len(payloads) == 2  # plain + html, in that order
    plain_part, html_part = payloads
    assert plain_part.get_content_type() == "text/plain"
    assert html_part.get_content_type() == "text/html"
    # html part: renderer output verbatim
    assert "PHANTOM_HTML" in html_part.get_payload(decode=True).decode("utf-8")
    # plain part: derived from body_md via strip_markdown (unchanged behavior)
    from techletter.delivery.escaping import strip_markdown
    assert plain_part.get_payload(decode=True).decode("utf-8") == strip_markdown(issue.body_md)


def test_AC4_privacy_one_recipient_per_to_no_bcc(monkeypatch):
    monkeypatch.setattr(
        "techletter.delivery.email.html_email.render", lambda issue: "<html>x</html>"
    )
    fake = _FakeSMTP()
    adapter = EmailAdapter(smtp_factory=lambda: fake, from_addr="bot@example.com")
    adapter.send(
        _issue(),
        [Recipient(address="a@example.com"), Recipient(address="b@example.com")],
    )

    assert len(fake.sent) == 2
    for msg in fake.sent:
        to_header = msg["To"]
        # Single recipient address; no comma indicating multi-address
        assert "," not in to_header
        assert msg.get("Cc") is None
        assert msg.get("Bcc") is None


def test_AC6_one_smtp_connection_for_N_recipients(monkeypatch):
    monkeypatch.setattr(
        "techletter.delivery.email.html_email.render", lambda issue: "<html>x</html>"
    )
    _FakeSMTP.instance_count = 0
    adapter = EmailAdapter(smtp_factory=_FakeSMTP, from_addr="bot@example.com")
    recipients = [Recipient(address=f"r{i}@e.com") for i in range(5)]
    adapter.send(_issue(), recipients)
    assert _FakeSMTP.instance_count == 1


def test_AC8_content_sha256_unchanged_by_renderer_swap():
    """The hash is derived from body_md — renderer change must not move it."""
    issue = _issue()
    # Recompute from body_md directly
    assert issue.content_sha256 == content_hash(issue.body_md)
