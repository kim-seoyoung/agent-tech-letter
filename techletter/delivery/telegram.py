"""Telegram channel adapter — Bot API sendMessage with HTML parse_mode.

Per US0021 + TC0247: bot token MUST NEVER appear in any log output
(security invariant). All log messages reference the channel name only,
never the token.
"""

from __future__ import annotations

import logging
import os
from collections.abc import Callable

import httpx
from tenacity import (
    RetryError,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from techletter.compose.issue import RenderedIssue
from techletter.delivery.base import (
    Recipient,
    SendReport,
)
from techletter.delivery.escaping import (
    commonmark_to_telegram_html,
    split_for_telegram,
)

__all__ = ["TelegramAdapter"]

logger = logging.getLogger(__name__)

TelegramPoster = Callable[[str, dict[str, object]], None]


def _default_telegram_poster(token: str, payload: dict[str, object]) -> None:
    """Default poster: POSTs to the Bot API. Token NEVER appears in logs.

    Caller must guarantee `token` is the full bot token (the URL is
    constructed here, kept LOCAL, never logged).
    """
    # CRITICAL (TC0247): URL contains token — must NEVER appear in log/exception strings
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    response = httpx.post(
        url, json=payload, timeout=15.0, headers={"Content-Type": "application/json"}
    )
    if response.status_code >= 400:
        # Strip the token from any URL in the error before re-raising
        raise httpx.HTTPStatusError(
            f"Telegram API returned {response.status_code} (response body redacted)",
            request=httpx.Request("POST", "https://api.telegram.org/bot[REDACTED]/sendMessage"),
            response=response,
        )
    response.raise_for_status()


class TelegramAdapter:
    """ChannelAdapter implementation for Telegram Bot API."""

    name: str = "telegram"

    def __init__(
        self,
        *,
        bot_token: str | None = None,
        max_chars_per_message: int = 4096,
        parse_mode: str = "HTML",
        poster: TelegramPoster | None = None,
    ) -> None:
        # CRITICAL: bot_token is held privately; never logged
        self._bot_token = bot_token or os.environ.get("TELEGRAM_BOT_TOKEN", "")
        self.max_chars_per_message = max_chars_per_message
        self.parse_mode = parse_mode
        self._poster: TelegramPoster = poster or _default_telegram_poster

    def send(self, issue: RenderedIssue, recipients: list[Recipient]) -> SendReport:
        if not recipients:
            return SendReport(
                channel=self.name,
                status="ok",
                recipient_count=0,
                success_count=0,
                failure_count=0,
                errors=[],
            )

        if not self._bot_token:
            return SendReport(
                channel=self.name,
                status="failed",
                recipient_count=len(recipients),
                success_count=0,
                failure_count=len(recipients),
                errors=["telegram: TELEGRAM_BOT_TOKEN not configured"],
            )

        html_body = commonmark_to_telegram_html(issue.body_md)
        chunks = split_for_telegram(html_body, max_chars=self.max_chars_per_message)
        if not chunks:
            chunks = [f"<i>(empty issue {issue.issue_id})</i>"]

        success_count = 0
        failure_count = 0
        errors: list[str] = []

        for r in recipients:
            try:
                self._send_chunks_with_retry(chat_id=r.address, chunks=chunks)
                success_count += 1
            except RetryError as e:
                inner = e.last_attempt.exception()
                failure_count += 1
                # CRITICAL: never include token in error string
                errors.append(f"telegram chat={r.address}: retries exhausted: {self._scrub(inner)}")
            except Exception as e:
                failure_count += 1
                errors.append(f"telegram chat={r.address}: {self._scrub(e)}")

        status = self._derive_status(success_count, failure_count, len(recipients))
        return SendReport(
            channel=self.name,
            status=status,
            recipient_count=len(recipients),
            success_count=success_count,
            failure_count=failure_count,
            errors=errors,
        )

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=0, min=0, max=0),  # no wait in tests
        retry=retry_if_exception_type((httpx.HTTPError, ConnectionError, TimeoutError)),
        reraise=False,
    )
    def _send_chunks_with_retry(self, *, chat_id: str, chunks: list[str]) -> None:
        for i, chunk in enumerate(chunks):
            payload: dict[str, object] = {
                "chat_id": chat_id,
                "text": chunk,
                "parse_mode": self.parse_mode,
                "disable_web_page_preview": False,
            }
            if len(chunks) > 1:
                payload["text"] = f"<i>[Part {i + 1}/{len(chunks)}]</i>\n{chunk}"
            self._poster(self._bot_token, payload)

    def _scrub(self, msg: object) -> str:
        """Remove the bot token from any string representation."""
        s = str(msg)
        if self._bot_token and self._bot_token in s:
            return s.replace(self._bot_token, "[REDACTED]")
        return s

    @staticmethod
    def _derive_status(success: int, failure: int, total: int) -> str:
        if failure == 0:
            return "ok"
        if success == 0:
            return "failed"
        return "partial"
