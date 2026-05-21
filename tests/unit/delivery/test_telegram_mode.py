"""US0031: Telegram adapter mode + publisher wiring tests.

Covers AC1 (params), AC2 (construction guard), AC3 (publish called once),
AC4 (publisher failure → SendReport.failed, no Bot API), AC5 (inline_html
behavioral equivalence), AC6/AC7 (config schema + registry resolution),
AC8 (backward compat), AC9 (token scrub on new paths).
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import yaml

from techletter.compose.issue import RenderedIssue, assemble_issue
from techletter.compose.types import DeepDive
from techletter.config import ConfigLoadError, load_channels
from techletter.delivery.base import Recipient
from techletter.delivery.publishers.base import PublisherError, PublishResult
from techletter.delivery.telegram import TelegramAdapter


def _issue() -> RenderedIssue:
    return assemble_issue(
        issue_id="issue-2026-05-21",
        issue_date=datetime(2026, 5, 21, tzinfo=UTC),
        deep_dives=[
            DeepDive(
                cluster_id=f"c{i}",
                title=f"t{i}",
                body_md="b",
                item_kind="paper",
                primary_url="https://example.com",  # type: ignore[arg-type]
                source_count=1,
            )
            for i in range(2)
        ],
        quick_mentions=[],
    )


class _FakePublisher:
    name = "github_pages"

    def __init__(self, *, raise_on_publish: Exception | None = None) -> None:
        self.raise_on_publish = raise_on_publish
        self.calls = 0

    def publish(self, issue: RenderedIssue) -> PublishResult:
        self.calls += 1
        if self.raise_on_publish:
            raise self.raise_on_publish
        return PublishResult(
            url="https://user.github.io/repo/issues/2026-05-21-abc.html",
            path="issues/2026-05-21-abc.html",
            published_at=datetime.now(UTC),
            publisher_name=self.name,
            commit_sha="a" * 40,
        )


# ---------------------------------------------------------------------------
# AC1 + AC2: construction
# ---------------------------------------------------------------------------


def test_AC1_default_mode_is_inline_html():
    a = TelegramAdapter(bot_token="t")
    assert a.mode == "inline_html"


def test_AC1_teaser_link_with_publisher_constructs():
    pub = _FakePublisher()
    a = TelegramAdapter(bot_token="t", mode="teaser_link", publisher=pub)
    assert a.mode == "teaser_link"


def test_AC2_teaser_link_without_publisher_raises():
    with pytest.raises(ValueError, match="requires a publisher"):
        TelegramAdapter(bot_token="t", mode="teaser_link", publisher=None)


# ---------------------------------------------------------------------------
# AC3: publisher called exactly once per send
# ---------------------------------------------------------------------------


def test_AC3_publisher_called_once_for_N_recipients():
    pub = _FakePublisher()
    poster = MagicMock()
    a = TelegramAdapter(
        bot_token="t", mode="teaser_link", publisher=pub, poster=poster
    )
    recipients = [Recipient(address=f"chat{i}") for i in range(5)]
    report = a.send(_issue(), recipients)

    assert pub.calls == 1
    assert report.success_count == 5
    assert report.published_url == "https://user.github.io/repo/issues/2026-05-21-abc.html"
    # 5 Bot API calls, one per recipient
    assert poster.call_count == 5


# ---------------------------------------------------------------------------
# AC4: publisher failure → status=failed, NO Bot API
# ---------------------------------------------------------------------------


def test_AC4_publisher_failure_zero_bot_api_calls():
    pub = _FakePublisher(raise_on_publish=PublisherError("simulated push failure"))
    poster = MagicMock()
    a = TelegramAdapter(
        bot_token="t", mode="teaser_link", publisher=pub, poster=poster
    )
    recipients = [Recipient(address=f"c{i}") for i in range(3)]
    report = a.send(_issue(), recipients)

    assert report.status == "failed"
    assert report.success_count == 0
    assert report.failure_count == 3
    assert "publisher error" in report.errors[0]
    assert poster.call_count == 0
    assert report.published_url is None


# ---------------------------------------------------------------------------
# AC5: inline_html mode — Bot API payload behavioral equivalence
# ---------------------------------------------------------------------------


def test_AC5_inline_html_publisher_never_called():
    pub = _FakePublisher()
    poster = MagicMock()
    a = TelegramAdapter(
        bot_token="t", mode="inline_html", publisher=pub, poster=poster
    )
    a.send(_issue(), [Recipient(address="c0")])
    # Even when a publisher is passed by mistake, inline_html ignores it
    assert pub.calls == 0


def test_AC5_inline_html_payload_shape_preserved():
    """Bot API payload for inline_html must include chat_id, text, parse_mode,
    disable_web_page_preview — EP0004 contract preserved.
    """
    poster = MagicMock()
    a = TelegramAdapter(bot_token="t", mode="inline_html", poster=poster)
    a.send(_issue(), [Recipient(address="chat1")])

    # poster signature: (token, payload_dict)
    assert poster.call_count >= 1
    _, payload = poster.call_args_list[0].args
    for key in ("chat_id", "text", "parse_mode", "disable_web_page_preview"):
        assert key in payload
    assert payload["chat_id"] == "chat1"


# ---------------------------------------------------------------------------
# AC6 + AC8: config schema + backward compat
# ---------------------------------------------------------------------------


def test_AC6_new_schema_parses(tmp_path: Path):
    cfg = {
        "publishers": {
            "github_pages": {
                "enabled": True,
                "repo_path": ".",
                "branch": "gh-pages",
                "base_url": "https://USER.github.io/REPO",
                "author_name": "bot",
                "author_email": "bot@example.com",
            }
        },
        "telegram": {
            "enabled": True,
            "mode": "teaser_link",
            "publisher": "github_pages",
        },
    }
    p = tmp_path / "channels.yaml"
    p.write_text(yaml.dump(cfg), encoding="utf-8")
    loaded = load_channels(p)
    assert loaded.telegram.mode == "teaser_link"
    assert loaded.telegram.publisher == "github_pages"
    assert loaded.publishers.github_pages.base_url == "https://USER.github.io/REPO"


def test_AC7_missing_publisher_reference_raises(tmp_path: Path):
    cfg = {
        "telegram": {
            "enabled": True,
            "mode": "teaser_link",
            # No "publisher" key
        }
    }
    p = tmp_path / "channels.yaml"
    p.write_text(yaml.dump(cfg), encoding="utf-8")
    with pytest.raises(ConfigLoadError):
        load_channels(p)


def test_AC8_old_channels_yaml_defaults_to_inline_html(tmp_path: Path):
    """Old config without `mode` / `publishers` blocks must load and default
    telegram to inline_html (no behavior change)."""
    cfg = {
        "email": {"enabled": False},
        "slack": {"enabled": False},
        "telegram": {"enabled": True},
    }
    p = tmp_path / "channels.yaml"
    p.write_text(yaml.dump(cfg), encoding="utf-8")
    loaded = load_channels(p)
    assert loaded.telegram.mode == "inline_html"
    assert loaded.telegram.publisher is None


# ---------------------------------------------------------------------------
# AC9: token scrub on publisher failure path
# ---------------------------------------------------------------------------


def test_AC9_publisher_error_with_token_substring_is_scrubbed(monkeypatch):
    secret = "ghs_" + "X" * 40
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", secret)
    # Adapter's existing _scrub replaces the bot token in error strings.
    poster = MagicMock()
    a = TelegramAdapter(
        bot_token=secret,
        mode="teaser_link",
        publisher=_FakePublisher(raise_on_publish=PublisherError(f"leak: {secret}")),
        poster=poster,
    )
    report = a.send(_issue(), [Recipient(address="c0")])

    assert report.status == "failed"
    joined_errors = " ".join(report.errors)
    assert secret not in joined_errors
    assert "[REDACTED]" in joined_errors
