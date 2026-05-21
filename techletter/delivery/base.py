"""Delivery layer shared types: ChannelAdapter Protocol + SendReport.

Per US0018: defines the contract every channel adapter (Email/Slack/Telegram)
implements. SendReport is the return value the orchestration layer consumes
to decide idempotency outcomes (per EP0003 SendRecord).
"""

from __future__ import annotations

from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field

from techletter.compose.issue import RenderedIssue

__all__ = [
    "ChannelAdapter",
    "ChannelSendError",
    "Recipient",
    "SendReport",
    "SendStatus",
]

SendStatus = Literal["ok", "partial", "failed"]


class ChannelSendError(Exception):
    """Raised when a channel adapter exhausts retries on a transient failure
    or hits a non-retryable error. Caught by the registry layer (US0022)."""


class Recipient(BaseModel):
    """One recipient address — shape depends on channel.

    For email: `address` is an email address.
    For slack: `address` is the webhook URL.
    For telegram: `address` is the chat_id (as string).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    address: str = Field(min_length=1)
    label: str | None = None


class SendReport(BaseModel):
    """Aggregated outcome of one channel's send pass.

    Consistency invariants (TC0206 — validated at construction):
    - status="ok"      → failure_count == 0 AND success_count == recipient_count
    - status="partial" → 0 < success_count < recipient_count
    - status="failed"  → success_count == 0 AND recipient_count > 0
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    channel: str
    status: SendStatus
    recipient_count: int = Field(ge=0)
    success_count: int = Field(ge=0)
    failure_count: int = Field(ge=0)
    errors: list[str] = Field(default_factory=lambda: [])
    # US0031/US0032: populated when the channel used a publisher (e.g.,
    # Telegram in teaser_link mode); None for inline / non-publisher channels.
    published_url: str | None = None

    def __init__(self, **data: object) -> None:
        super().__init__(**data)
        # Re-validate consistency (frozen so we can't use a model validator post-init cleanly;
        # validate at __init__ time via pydantic + a post check)
        self._validate_consistency()

    def _validate_consistency(self) -> None:
        if self.success_count + self.failure_count != self.recipient_count:
            raise ValueError(
                f"SendReport: success_count ({self.success_count}) + failure_count "
                f"({self.failure_count}) must equal recipient_count ({self.recipient_count})"
            )
        if self.status == "ok":
            if self.failure_count != 0 or self.success_count != self.recipient_count:
                raise ValueError(
                    f"SendReport status=ok requires failure_count=0 and success_count="
                    f"recipient_count; got success={self.success_count}, "
                    f"failure={self.failure_count}, total={self.recipient_count}"
                )
        elif self.status == "partial":
            if not (0 < self.success_count < self.recipient_count):
                raise ValueError(
                    f"SendReport status=partial requires 0 < success_count < recipient_count; "
                    f"got success={self.success_count}, total={self.recipient_count}"
                )
        elif self.status == "failed" and self.recipient_count > 0 and self.success_count != 0:
            raise ValueError(
                f"SendReport status=failed requires success_count=0; "
                f"got success={self.success_count}"
            )


class ChannelAdapter(Protocol):
    """Structural contract every channel adapter implements.

    Members:
        name: short identifier (e.g., 'email', 'slack', 'telegram')
        send(issue, recipients): deliver the issue; return SendReport

    Per US0018 AC: per-recipient failure must be caught and counted in
    SendReport, never propagated as an exception. ChannelSendError is
    only raised when the channel itself is unreachable (e.g., DNS down,
    invalid webhook URL after retries) — i.e., when status would be "failed"
    AND no further useful work can be done.
    """

    name: str

    def send(self, issue: RenderedIssue, recipients: list[Recipient]) -> SendReport: ...
