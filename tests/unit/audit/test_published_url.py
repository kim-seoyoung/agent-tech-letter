"""US0032: SendRecord.published_url tests.

Covers AC1 (field added optional, default None), AC2 (populated for
teaser_link sends), backward compat (old JSONL without the field loads
as None).
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from techletter.audit import (
    SendRecord,
    append_send_record,
    load_records,
    make_record,
)


def test_AC1_published_url_field_optional_default_none():
    rec = SendRecord(
        timestamp=datetime.now(UTC),
        issue_id="issue-2026-05-21",
        channel="telegram",
        status="ok",
        recipient_count=1,
    )
    assert rec.published_url is None


def test_AC1_published_url_can_be_set():
    rec = SendRecord(
        timestamp=datetime.now(UTC),
        issue_id="issue-2026-05-21",
        channel="telegram",
        status="ok",
        recipient_count=1,
        published_url="https://user.github.io/repo/issues/abc.html",
    )
    assert rec.published_url == "https://user.github.io/repo/issues/abc.html"


def test_backward_compat_old_jsonl_without_field_loads(tmp_path: Path):
    """Old SendRecord JSONL lines (pre-US0032) must parse cleanly."""
    p = tmp_path / "sends.jsonl"
    old_record = {
        "timestamp": "2026-05-19T00:00:00Z",
        "issue_id": "issue-2026-05-19",
        "channel": "telegram",
        "status": "ok",
        "recipient_count": 3,
        "error": None,
        # NOTE: no `published_url` field
    }
    p.write_text(json.dumps(old_record) + "\n", encoding="utf-8")
    records = load_records(log_path=p)
    assert len(records) == 1
    assert records[0].published_url is None
    assert records[0].channel == "telegram"


def test_AC2_append_and_load_round_trip_with_published_url(tmp_path: Path):
    p = tmp_path / "sends.jsonl"
    rec = make_record(
        issue_id="issue-2026-05-21",
        channel="telegram",
        status="ok",
        recipient_count=3,
        published_url="https://x.github.io/r/issues/2026-05-21-abc.html",
    )
    append_send_record(rec, log_path=p)

    loaded = load_records(log_path=p)
    assert len(loaded) == 1
    assert loaded[0].published_url == "https://x.github.io/r/issues/2026-05-21-abc.html"


def test_AC3_make_record_default_published_url_is_none():
    """Channels that don't publish (email, slack, inline_html telegram)
    leave published_url as None."""
    rec = make_record(
        issue_id="issue-2026-05-21",
        channel="email",
        status="ok",
        recipient_count=5,
    )
    assert rec.published_url is None
