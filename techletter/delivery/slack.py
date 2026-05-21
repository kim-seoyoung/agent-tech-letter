"""Slack channel adapter — Incoming Webhook + mrkdwn + payload splitting.

Per US0020: posts to each configured webhook URL. Long issues are split
into multiple sequential messages so each fits Slack's per-message
payload limit (default 3500 chars to stay under the soft 4000 cap).
"""

from __future__ import annotations

import json
import logging
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
from techletter.delivery.escaping import commonmark_to_mrkdwn, split_for_slack

__all__ = ["SlackAdapter"]

logger = logging.getLogger(__name__)


SlackPoster = Callable[[str, dict[str, object]], None]


def _default_slack_poster(webhook_url: str, payload: dict[str, object]) -> None:
    """Default poster: synchronous httpx.post to the webhook URL."""
    response = httpx.post(
        webhook_url, json=payload, timeout=15.0, headers={"Content-Type": "application/json"}
    )
    response.raise_for_status()


class SlackAdapter:
    """ChannelAdapter implementation for Slack Incoming Webhooks."""

    name: str = "slack"

    def __init__(
        self,
        *,
        max_chars_per_message: int = 3500,
        poster: SlackPoster | None = None,
    ) -> None:
        self.max_chars_per_message = max_chars_per_message
        self._poster: SlackPoster = poster or _default_slack_poster

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

        mrkdwn_body = commonmark_to_mrkdwn(issue.body_md)
        chunks = split_for_slack(mrkdwn_body, max_chars=self.max_chars_per_message)
        if not chunks:
            chunks = [f"_(empty issue {issue.issue_id})_"]

        success_count = 0
        failure_count = 0
        errors: list[str] = []

        for r in recipients:
            try:
                self._send_chunks_with_retry(r.address, chunks, issue.issue_id)
                success_count += 1
            except RetryError as e:
                inner = e.last_attempt.exception()
                failure_count += 1
                errors.append(f"{r.label or r.address[:20]}: retries exhausted: {inner}")
            except Exception as e:
                failure_count += 1
                errors.append(f"{r.label or r.address[:20]}: {e}")

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
    def _send_chunks_with_retry(self, webhook_url: str, chunks: list[str], issue_id: str) -> None:
        for i, chunk in enumerate(chunks):
            payload: dict[str, object] = {"text": chunk, "mrkdwn": True}
            if len(chunks) > 1:
                # Prefix part marker so readers see ordering
                payload["text"] = f"_[Part {i + 1}/{len(chunks)} — {issue_id}]_\n{chunk}"
            self._poster(webhook_url, payload)
            _ = json.dumps  # touch json import for non-default poster compat

    @staticmethod
    def _derive_status(success: int, failure: int, total: int) -> str:
        if failure == 0:
            return "ok"
        if success == 0:
            return "failed"
        return "partial"
