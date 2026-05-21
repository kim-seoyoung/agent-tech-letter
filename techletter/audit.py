"""Audit log + idempotency for send operations.

Per US0013: `logs/sends.jsonl` is the canonical record of every send
attempt across every channel. Each line is a SendRecord JSON object,
appended atomically via O_APPEND so concurrent writes from different
channels don't tear lines.

Idempotency semantics (per TC0144 / TC0145):
- status=ok      → retry BLOCKED (already sent successfully)
- status=partial → retry BLOCKED (don't double-send to recipients who got it)
- status=failed  → retry ALLOWED (try again from scratch)
"""

from __future__ import annotations

import json
import logging
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

__all__ = [
    "DEFAULT_AUDIT_PATH",
    "SendRecord",
    "SendStatus",
    "already_sent",
    "append_send_record",
    "load_records",
]

logger = logging.getLogger(__name__)

DEFAULT_AUDIT_PATH = Path("logs/sends.jsonl")

SendStatus = Literal["ok", "partial", "failed"]


class SendRecord(BaseModel):
    """One row in `logs/sends.jsonl` — atomic record of a send attempt."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    timestamp: datetime
    issue_id: str
    channel: str
    status: SendStatus
    recipient_count: int = Field(ge=0)
    error: str | None = None


def append_send_record(record: SendRecord, *, log_path: Path | None = None) -> None:
    """Append a SendRecord to the audit log atomically (O_APPEND).

    O_APPEND guarantees each write is positioned at end-of-file by the
    kernel, so concurrent writes from different channels never tear lines.
    """
    path = log_path if log_path is not None else DEFAULT_AUDIT_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    line = record.model_dump_json() + "\n"
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
    try:
        os.write(fd, line.encode("utf-8"))
    finally:
        os.close(fd)


def load_records(*, log_path: Path | None = None) -> list[SendRecord]:
    """Load all records from the audit log. Returns [] if missing."""
    path = log_path if log_path is not None else DEFAULT_AUDIT_PATH
    if not path.exists():
        return []
    records: list[SendRecord] = []
    for line_no, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip():
            continue
        try:
            data: Any = json.loads(raw)
            records.append(SendRecord.model_validate(data))
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning("audit: skipping malformed line %d in %s: %s", line_no, path, e)
    return records


def already_sent(issue_id: str, channel: str, *, log_path: Path | None = None) -> bool:
    """Return True if (issue_id, channel) has a non-retryable record.

    Per TC0144 / TC0145:
    - 'ok' or 'partial' status → retry blocked (return True)
    - 'failed' status (with no later 'ok'/'partial') → retry allowed (return False)
    """
    records = load_records(log_path=log_path)
    relevant = [r for r in records if r.issue_id == issue_id and r.channel == channel]
    if not relevant:
        return False
    # If ANY record is ok or partial, retry is blocked.
    return any(r.status in ("ok", "partial") for r in relevant)


def make_record(
    *,
    issue_id: str,
    channel: str,
    status: SendStatus,
    recipient_count: int,
    error: str | None = None,
    timestamp: datetime | None = None,
) -> SendRecord:
    """Convenience constructor with timestamp default = now()."""
    return SendRecord(
        timestamp=timestamp if timestamp is not None else datetime.now(UTC),
        issue_id=issue_id,
        channel=channel,
        status=status,
        recipient_count=recipient_count,
        error=error,
    )
