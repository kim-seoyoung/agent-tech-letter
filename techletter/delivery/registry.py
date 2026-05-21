"""Channel registry: builds adapters from config + dispatches sends.

Per US0022: structurally symmetric to the source registry (EP0001 US0005).
- `build_channel_registry(channels_cfg, subscribers_cfg)` constructs enabled adapters
- `ChannelRegistry.send_all(issue)` calls each adapter, collects SendReports
- Per-channel failure isolation: one bad channel never aborts the run
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from dataclasses import dataclass, field

from techletter.compose.issue import RenderedIssue
from techletter.delivery.base import ChannelAdapter, Recipient, SendReport
from techletter.delivery.config import ChannelsConfig, SubscribersConfig
from techletter.delivery.email import EmailAdapter
from techletter.delivery.slack import SlackAdapter
from techletter.delivery.telegram import TelegramAdapter

__all__ = ["ChannelRegistry", "aggregate_reports", "build_channel_registry"]

logger = logging.getLogger(__name__)


@dataclass
class ChannelRegistry:
    """Dispatcher across configured channel adapters."""

    adapters: Mapping[str, ChannelAdapter] = field(default_factory=lambda: {})
    recipients: Mapping[str, list[Recipient]] = field(default_factory=lambda: {})

    def send_all(self, issue: RenderedIssue) -> list[SendReport]:
        """Send `issue` via each enabled channel; return all SendReports.

        Per-channel failures are isolated: an exception from one adapter
        becomes a "failed" SendReport for that channel and execution
        continues with the others.
        """
        reports: list[SendReport] = []
        for channel_name, adapter in self.adapters.items():
            channel_recipients = list(self.recipients.get(channel_name, []))
            try:
                report = adapter.send(issue, channel_recipients)
                reports.append(report)
            except Exception as e:
                logger.warning("channel %r raised unexpected exception: %s", channel_name, e)
                reports.append(
                    SendReport(
                        channel=channel_name,
                        status="failed",
                        recipient_count=len(channel_recipients),
                        success_count=0,
                        failure_count=len(channel_recipients),
                        errors=[f"{channel_name}: {e}"],
                    )
                )
        return reports


# Explicit adapter-class registry — grep-able + pyright-checkable
_ADAPTER_CLASSES: Mapping[str, type[ChannelAdapter]] = {
    "email": EmailAdapter,
    "slack": SlackAdapter,
    "telegram": TelegramAdapter,
}


def build_channel_registry(
    channels: ChannelsConfig, subscribers: SubscribersConfig
) -> ChannelRegistry:
    """Construct a ChannelRegistry from the two config objects.

    Only enabled channels are included. Adapter construction failures
    are caught + logged + that channel is omitted (others proceed).
    """
    adapters: dict[str, ChannelAdapter] = {}
    recipients_map: dict[str, list[Recipient]] = {}

    if channels.email.enabled:
        try:
            adapters["email"] = EmailAdapter()
        except Exception as e:
            logger.warning("channel 'email' failed to construct: %s", e)
        else:
            recipients_map["email"] = [Recipient(address=a) for a in subscribers.email]

    if channels.slack.enabled:
        try:
            adapters["slack"] = SlackAdapter(
                max_chars_per_message=channels.slack.max_chars_per_message,
            )
        except Exception as e:
            logger.warning("channel 'slack' failed to construct: %s", e)
        else:
            recipients_map["slack"] = [Recipient(address=u) for u in subscribers.slack]

    if channels.telegram.enabled:
        try:
            adapters["telegram"] = TelegramAdapter(
                max_chars_per_message=channels.telegram.max_chars_per_message,
                parse_mode=channels.telegram.parse_mode,
            )
        except Exception as e:
            logger.warning("channel 'telegram' failed to construct: %s", e)
        else:
            recipients_map["telegram"] = [Recipient(address=c) for c in subscribers.telegram]

    return ChannelRegistry(adapters=adapters, recipients=recipients_map)


def aggregate_reports(reports: list[SendReport]) -> dict[str, object]:
    """Project-level summary across all channels.

    Returns counts that orchestrate the EP0003 idempotency log:
    - if any channel returned 'ok', that channel is sealed against retry
    - if any channel returned 'partial', the same is true (per TC0144)
    - if all channels returned 'failed', the next run can retry everything
    """
    total_recipients = sum(r.recipient_count for r in reports)
    total_success = sum(r.success_count for r in reports)
    total_failure = sum(r.failure_count for r in reports)
    by_channel = {r.channel: r.status for r in reports}
    return {
        "channels": list(by_channel.keys()),
        "by_channel": by_channel,
        "total_recipients": total_recipients,
        "total_success": total_success,
        "total_failure": total_failure,
        "overall": _derive_overall(total_success, total_failure, total_recipients),
    }


def _derive_overall(success: int, failure: int, total: int) -> str:
    if total == 0:
        return "ok"
    if failure == 0:
        return "ok"
    if success == 0:
        return "failed"
    return "partial"
