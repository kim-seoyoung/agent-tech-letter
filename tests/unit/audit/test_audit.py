"""Tests for techletter.audit - mirrors TS0003 TC0140-TC0150."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from techletter.audit import (
    SendRecord,
    already_sent,
    append_send_record,
    load_records,
    make_record,
)


def _rec(
    issue_id: str = "i1",
    channel: str = "slack",
    status: str = "ok",
    recipient_count: int = 1,
    error: str | None = None,
) -> SendRecord:
    return make_record(
        issue_id=issue_id,
        channel=channel,
        status=status,  # type: ignore[arg-type]
        recipient_count=recipient_count,
        error=error,
        timestamp=datetime(2026, 5, 20, 12, 0, 0, tzinfo=UTC),
    )


# --- SendRecord model -----------------------------------------------------------


def test_send_record_basic() -> None:
    r = _rec()
    assert r.issue_id == "i1"
    assert r.channel == "slack"
    assert r.status == "ok"


def test_send_record_invalid_status_raises() -> None:
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        SendRecord(
            timestamp=datetime(2026, 5, 20, tzinfo=UTC),
            issue_id="i1",
            channel="slack",
            status="unknown",  # type: ignore[arg-type]
            recipient_count=1,
        )


def test_send_record_negative_recipients_raises() -> None:
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        SendRecord(
            timestamp=datetime(2026, 5, 20, tzinfo=UTC),
            issue_id="i1",
            channel="slack",
            status="ok",
            recipient_count=-1,
        )


# --- append + load round-trip ---------------------------------------------------


def test_append_and_load(tmp_path: Path) -> None:
    log = tmp_path / "sends.jsonl"
    r1 = _rec("i1", "slack", "ok", 5)
    r2 = _rec("i1", "telegram", "ok", 3)
    append_send_record(r1, log_path=log)
    append_send_record(r2, log_path=log)
    loaded = load_records(log_path=log)
    assert len(loaded) == 2
    assert loaded[0].channel == "slack"
    assert loaded[1].channel == "telegram"


def test_load_records_missing_file_returns_empty(tmp_path: Path) -> None:
    assert load_records(log_path=tmp_path / "nope.jsonl") == []


def test_load_records_skips_malformed_lines(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    log = tmp_path / "sends.jsonl"
    valid = _rec()
    append_send_record(valid, log_path=log)
    # corrupt a line by appending raw garbage
    with open(log, "a", encoding="utf-8") as f:
        f.write("not valid json\n")
    with caplog.at_level("WARNING"):
        records = load_records(log_path=log)
    assert len(records) == 1
    assert any("malformed" in r.message.lower() for r in caplog.records)


# --- already_sent semantics (the load-bearing tests) ----------------------------


def test_already_sent_no_history(tmp_path: Path) -> None:
    log = tmp_path / "sends.jsonl"
    assert already_sent("i1", "slack", log_path=log) is False


def test_tc0144_ok_blocks_retry(tmp_path: Path) -> None:
    """status=ok → already_sent returns True → retry BLOCKED."""
    log = tmp_path / "sends.jsonl"
    append_send_record(_rec("i1", "slack", "ok", 5), log_path=log)
    assert already_sent("i1", "slack", log_path=log) is True


def test_tc0144_partial_blocks_retry(tmp_path: Path) -> None:
    """status=partial → already_sent returns True → retry BLOCKED."""
    log = tmp_path / "sends.jsonl"
    append_send_record(_rec("i1", "slack", "partial", 3), log_path=log)
    assert already_sent("i1", "slack", log_path=log) is True


def test_tc0145_failed_allows_retry(tmp_path: Path) -> None:
    """status=failed (only) → already_sent returns False → retry ALLOWED."""
    log = tmp_path / "sends.jsonl"
    append_send_record(_rec("i1", "slack", "failed", 0, error="boom"), log_path=log)
    assert already_sent("i1", "slack", log_path=log) is False


def test_already_sent_per_channel_isolation(tmp_path: Path) -> None:
    """A successful send to slack doesn't block a send to telegram."""
    log = tmp_path / "sends.jsonl"
    append_send_record(_rec("i1", "slack", "ok", 5), log_path=log)
    assert already_sent("i1", "slack", log_path=log) is True
    assert already_sent("i1", "telegram", log_path=log) is False


def test_already_sent_per_issue_isolation(tmp_path: Path) -> None:
    """A successful send for issue i1 doesn't block issue i2."""
    log = tmp_path / "sends.jsonl"
    append_send_record(_rec("i1", "slack", "ok", 5), log_path=log)
    assert already_sent("i2", "slack", log_path=log) is False


def test_already_sent_failed_then_ok_blocks(tmp_path: Path) -> None:
    """failed first then ok → still blocked (last ok dominates)."""
    log = tmp_path / "sends.jsonl"
    append_send_record(_rec("i1", "slack", "failed", 0, "first try failed"), log_path=log)
    append_send_record(_rec("i1", "slack", "ok", 5), log_path=log)
    assert already_sent("i1", "slack", log_path=log) is True
