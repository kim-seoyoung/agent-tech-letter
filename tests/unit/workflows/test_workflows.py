"""Static + structural tests for .github/workflows/{draft,send}.yml.

Per TS0003: pyyaml-parse assertions on cron, concurrency, env, and the
LOAD-BEARING `if: merged == true` predicate (TC0179).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

_REPO_ROOT = Path(__file__).resolve().parents[3]
DRAFT_YML = _REPO_ROOT / ".github" / "workflows" / "draft.yml"
SEND_YML = _REPO_ROOT / ".github" / "workflows" / "send.yml"


def _load(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


# --- Files exist + parse as YAML ----------------------------------------------


def test_draft_yml_exists_and_parses() -> None:
    assert DRAFT_YML.exists()
    parsed = _load(DRAFT_YML)
    assert parsed["name"] == "draft"


def test_send_yml_exists_and_parses() -> None:
    assert SEND_YML.exists()
    parsed = _load(SEND_YML)
    assert parsed["name"] == "send"


# --- draft.yml structural assertions ------------------------------------------


def test_draft_cron_is_monday_midnight_utc() -> None:
    """Per PRD §F-04: schedule is Monday 09:00 KST = Monday 00:00 UTC."""
    parsed = _load(DRAFT_YML)
    # YAML's `on:` key is parsed as Python True when bare; use the boolean key
    on_key: Any = parsed.get("on") or parsed.get(True)  # type: ignore[arg-type]
    assert on_key is not None, "draft.yml missing 'on' trigger block"
    cron_entries = on_key["schedule"]
    assert any(entry["cron"] == "0 0 * * 1" for entry in cron_entries)


def test_draft_has_workflow_dispatch() -> None:
    """Manual dispatch must be available for backfill."""
    parsed = _load(DRAFT_YML)
    on_key: Any = parsed.get("on") or parsed.get(True)  # type: ignore[arg-type]
    assert "workflow_dispatch" in on_key


def test_draft_concurrency_group_set() -> None:
    """concurrency.group prevents duplicate scheduled runs."""
    parsed = _load(DRAFT_YML)
    assert parsed["concurrency"]["group"] == "draft"


def test_draft_uses_anthropic_api_key_secret() -> None:
    """ANTHROPIC_API_KEY must come from GitHub Secrets, never inline."""
    raw = DRAFT_YML.read_text(encoding="utf-8")
    assert "${{ secrets.ANTHROPIC_API_KEY }}" in raw


def test_draft_has_budget_grep() -> None:
    """draft.yml must check stderr for BUDGET_EXCEEDED marker (TC0137)."""
    raw = DRAFT_YML.read_text(encoding="utf-8")
    assert "BUDGET_EXCEEDED" in raw


# --- send.yml structural assertions (incl. TC0179 — the critical one) --------


def test_send_yml_trigger_is_pull_request_closed() -> None:
    parsed = _load(SEND_YML)
    on_key: Any = parsed.get("on") or parsed.get(True)  # type: ignore[arg-type]
    pr_trigger = on_key["pull_request"]
    assert "closed" in pr_trigger["types"]
    assert "main" in pr_trigger["branches"]


def test_tc0179_send_yml_has_merged_predicate() -> None:
    """THE most important test in the project. send.yml's job-level `if:`
    MUST include `github.event.pull_request.merged == true` so the workflow
    only fires on actual merges, NOT on close-without-merge events.

    Without this guard, ANY closed PR triggers a send fan-out — including
    spam-closed PRs from random contributors. This is a security AND a
    correctness gate.
    """
    parsed = _load(SEND_YML)
    job = parsed["jobs"]["send"]
    assert "if" in job, "send.yml's send job missing `if:` predicate"
    predicate = str(job["if"])
    assert "github.event.pull_request.merged" in predicate
    assert "== true" in predicate or "==true" in predicate


def test_send_concurrency_group_per_pr() -> None:
    """concurrency.group must scope per-PR so two PRs don't serialise unnecessarily."""
    parsed = _load(SEND_YML)
    assert "${{ github.event.pull_request.number }}" in parsed["concurrency"]["group"]


@pytest.mark.parametrize(
    "secret_name",
    [
        "SMTP_HOST",
        "SMTP_USER",
        "SMTP_PASS",
        "SMTP_FROM",
        "SLACK_WEBHOOK_URLS",
        "TELEGRAM_BOT_TOKEN",
    ],
)
def test_send_references_required_secrets(secret_name: str) -> None:
    """send.yml must reference all delivery secrets via secrets context."""
    raw = SEND_YML.read_text(encoding="utf-8")
    assert f"secrets.{secret_name}" in raw


def test_send_commits_sends_jsonl() -> None:
    """send.yml must commit logs/sends.jsonl back to main after fan-out."""
    raw = SEND_YML.read_text(encoding="utf-8")
    assert "logs/sends.jsonl" in raw
    assert "git push" in raw


# --- Secret-leak grep on both workflows ---------------------------------------


def test_no_inline_secrets_in_workflows() -> None:
    """No raw API keys, tokens, or webhook URLs hard-coded in YAML."""
    import re

    secret_pattern = re.compile(r"(sk-ant|AKIA|xoxb-|SG\.|AIza)")
    for wf in (DRAFT_YML, SEND_YML):
        raw = wf.read_text(encoding="utf-8")
        assert not secret_pattern.search(raw), f"inline secret detected in {wf.name}"
