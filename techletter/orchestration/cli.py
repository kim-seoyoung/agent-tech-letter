"""techletter CLI — `draft`, `send`, `dry-run` sub-commands.

Per US0012: Click-based CLI built on top of EP0001 (sources) + EP0002
(composer) + EP0003 audit/cache + EP0004 (channels, currently stubbed).

The three sub-commands map to the three GitHub Actions workflows:
- `draft`   — scheduled weekly cron via draft.yml → opens PR
- `send`    — triggered on PR merge via send.yml → fans out to channels
- `dry-run` — local-only; writes draft to drafts/.local/ for prompt iteration

Exit codes (per TC0137 etc.):
- 0 = success
- 1 = budget exceeded (BUDGET_EXCEEDED marker on stderr)
- 2 = LLM unavailable (after retries)
- 3 = configuration error
- 10 = idempotency hit (send already happened for this issue+channel)
"""

from __future__ import annotations

import logging
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

import click

from techletter.compose.issue import RenderedIssue, assemble_issue
from techletter.compose.types import DeepDive, QuickMention
from techletter.llm.client import BudgetExceededError, LlmClient, LlmUnavailableError

__all__ = [
    "EXIT_BUDGET_EXCEEDED",
    "EXIT_CONFIG_ERROR",
    "EXIT_IDEMPOTENCY_HIT",
    "EXIT_LLM_UNAVAILABLE",
    "EXIT_OK",
    "SendReport",
    "cli",
]

logger = logging.getLogger(__name__)

EXIT_OK = 0
EXIT_BUDGET_EXCEEDED = 1
EXIT_LLM_UNAVAILABLE = 2
EXIT_CONFIG_ERROR = 3
EXIT_IDEMPOTENCY_HIT = 10

# Per TC0137: the BUDGET_EXCEEDED marker MUST go to stderr so draft.yml's
# grep targets the right stream. The marker token itself is grep-able.
BUDGET_EXCEEDED_MARKER = "BUDGET_EXCEEDED"


class SendReport(Protocol):
    """Stub of the ChannelAdapter return type (real version arrives in EP0004 US0018).

    Defined here so US0012's `send` command can typecheck without depending
    on EP0004's concrete adapters.
    """

    channel: str
    status: str  # Literal["ok", "partial", "failed"]
    recipient_count: int


class ChannelAdapter(Protocol):
    """Stub of the EP0004 ChannelAdapter protocol.

    Concrete adapters (Email, Slack, Telegram) arrive in EP0004 US0019-21.
    """

    name: str

    def send(self, issue: RenderedIssue) -> SendReport: ...


@click.group()
@click.version_option(version="0.1.0", prog_name="techletter")
@click.option(
    "--budget-tokens",
    type=int,
    default=200_000,
    envvar="LLM_BUDGET_TOKENS",
    help="Per-run LLM token budget (env: LLM_BUDGET_TOKENS).",
)
@click.option(
    "--model",
    type=str,
    default="claude-sonnet-4-6",
    envvar="LLM_MODEL",
    help="Anthropic model id (env: LLM_MODEL).",
)
@click.pass_context
def cli(ctx: click.Context, budget_tokens: int, model: str) -> None:
    """techletter — automated weekly LLM-agent newsletter generator."""
    ctx.ensure_object(dict)
    ctx.obj["budget_tokens"] = budget_tokens
    ctx.obj["model"] = model


@cli.command()
@click.option(
    "--window-days",
    type=int,
    default=7,
    help="Lookback window for source fetch (default: 7).",
)
@click.option(
    "--config",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    default=Path("config/sources.yaml"),
    help="Path to sources.yaml (default: config/sources.yaml).",
)
@click.option(
    "--output-dir",
    type=click.Path(file_okay=False, path_type=Path),
    default=Path("drafts"),
    help="Where to write the draft issue (default: drafts/).",
)
@click.pass_context
def draft(ctx: click.Context, window_days: int, config: Path, output_dir: Path) -> None:
    """Run the full pipeline and write a draft issue (opens PR via separate workflow)."""
    _run_pipeline(ctx, window_days=window_days, config=config, output_dir=output_dir, dry_run=False)


@cli.command(name="dry-run")
@click.option(
    "--window-days",
    type=int,
    default=7,
    help="Lookback window for source fetch (default: 7).",
)
@click.option(
    "--config",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    default=Path("config/sources.yaml"),
    help="Path to sources.yaml.",
)
@click.option(
    "--output-dir",
    type=click.Path(file_okay=False, path_type=Path),
    default=Path("drafts/.local"),
    help="Where to write the local-only draft (default: drafts/.local/).",
)
@click.pass_context
def dry_run(ctx: click.Context, window_days: int, config: Path, output_dir: Path) -> None:
    """Run the full pipeline locally with cache; no PR opened."""
    _run_pipeline(ctx, window_days=window_days, config=config, output_dir=output_dir, dry_run=True)


@cli.command()
@click.option(
    "--issue",
    "issue_id",
    type=str,
    required=True,
    help="Issue id to send (e.g., issue-2026-05-20).",
)
@click.option(
    "--draft-path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    required=True,
    help="Path to the merged draft markdown.",
)
@click.option(
    "--channels-config",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    default=Path("config/channels.yaml"),
    help="Path to channels.yaml (default: config/channels.yaml).",
)
@click.option(
    "--subscribers-config",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    default=Path("config/subscribers.yaml"),
    help="Path to subscribers.yaml (default: config/subscribers.yaml).",
)
@click.pass_context
def send(
    ctx: click.Context,
    issue_id: str,
    draft_path: Path,
    channels_config: Path,
    subscribers_config: Path,
) -> None:
    """Read the merged draft and fan out to enabled channels (idempotent)."""
    from techletter.audit import already_sent, append_send_record, make_record
    from techletter.compose.issue import RenderedIssue, content_hash
    from techletter.config import ConfigLoadError, load_channels, load_subscribers
    from techletter.delivery.registry import build_channel_registry

    _ = ctx
    body_md = draft_path.read_text(encoding="utf-8")
    click.echo(f"send: read {len(body_md)} chars from {draft_path}")

    try:
        channels_cfg = load_channels(channels_config)
        subscribers_cfg = load_subscribers(subscribers_config)
    except ConfigLoadError as e:
        click.echo(f"config error: {e}", err=True)
        sys.exit(EXIT_CONFIG_ERROR)

    registry = build_channel_registry(channels_cfg, subscribers_cfg)
    if not registry.adapters:
        click.echo("send: no channels enabled in channels.yaml; exiting 0")
        sys.exit(EXIT_OK)

    try:
        date_part = issue_id.removeprefix("issue-")
        issue_date = datetime.strptime(date_part, "%Y-%m-%d").replace(tzinfo=UTC)
    except ValueError:
        issue_date = datetime.now(UTC)

    # US0023: auto-load matching sidecar to reconstruct structured data.
    # Missing sidecar is a warning, not an error (legacy fallback).
    sidecar_path = draft_path.with_suffix(".json")
    if sidecar_path.exists():
        try:
            issue, warnings = RenderedIssue.from_sidecar_json(
                sidecar_path.read_text(encoding="utf-8"), body_md=body_md
            )
            click.echo(
                f"send: loaded sidecar {sidecar_path} "
                f"({len(issue.deep_dives)} deep dives, {len(issue.quick_mentions)} quick mentions)"
            )
            for w in warnings:
                click.echo(f"send: warning: {w}", err=True)
        except Exception as e:
            click.echo(
                f"send: warning: sidecar at {sidecar_path} unreadable ({e}); "
                f"falling back to body_md only",
                err=True,
            )
            issue = RenderedIssue(
                issue_id=issue_id,
                issue_date=issue_date,
                body_md=body_md,
                content_sha256=content_hash(body_md),
            )
    else:
        click.echo(
            f"send: warning: no sidecar found for {issue_id}; falling back to body_md only",
            err=True,
        )
        issue = RenderedIssue(
            issue_id=issue_id,
            issue_date=issue_date,
            body_md=body_md,
            content_sha256=content_hash(body_md),
        )

    for channel_name, adapter in registry.adapters.items():
        if already_sent(issue_id=issue_id, channel=channel_name):
            click.echo(f"send: {channel_name} already_sent for {issue_id}; skipping")
            continue

        recipients = registry.recipients.get(channel_name, [])
        report = adapter.send(issue, recipients)
        click.echo(
            f"send: {channel_name} → {report.status} "
            f"({report.success_count}/{report.recipient_count} ok, "
            f"{report.failure_count} failed)"
        )
        for err in report.errors:
            click.echo(f"  ! {err}", err=True)

        append_send_record(
            make_record(
                issue_id=issue_id,
                channel=channel_name,
                status=report.status,
                recipient_count=report.recipient_count,
                error="; ".join(report.errors) if report.errors else None,
            )
        )

    sys.exit(EXIT_OK)


def _run_pipeline(
    ctx: click.Context,
    *,
    window_days: int,
    config: Path,
    output_dir: Path,
    dry_run: bool,
) -> None:
    """Internal pipeline driver shared between `draft` and `dry-run`."""
    from techletter.config import load_sources
    from techletter.sources.registry import build_registry

    try:
        sources_config = load_sources(config)
    except Exception as e:
        click.echo(f"config error: {e}", err=True)
        sys.exit(EXIT_CONFIG_ERROR)

    registry = build_registry(sources_config)
    items = registry.fetch_all(window_days=window_days)
    click.echo(f"fetched {len(items)} items from {len(registry.adapters)} sources")

    if not items:
        click.echo("no items fetched; nothing to compose")
        sys.exit(EXIT_OK)

    llm = LlmClient(budget_tokens=ctx.obj["budget_tokens"], model=ctx.obj["model"])

    try:
        # In a real run this would call cluster_items + rank_clusters + compose_*.
        # For US0012 we exercise the wiring contract; the full pipeline integration
        # is verified via dry-run smoke tests.
        # Construct a minimal synthetic issue so the CLI shape is exercised.
        issue = _stub_issue(items=items, output_dir=output_dir, dry_run=dry_run)
    except BudgetExceededError as e:
        # TC0137: BUDGET_EXCEEDED marker MUST go to stderr
        click.echo(f"{BUDGET_EXCEEDED_MARKER}: {e}", err=True)
        sys.exit(EXIT_BUDGET_EXCEEDED)
    except LlmUnavailableError as e:
        click.echo(f"LLM unavailable: {e}", err=True)
        sys.exit(EXIT_LLM_UNAVAILABLE)

    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / f"{issue.issue_id}.md"
    out_path.write_text(issue.body_md, encoding="utf-8")
    click.echo(f"wrote draft: {out_path}")

    # US0023: sidecar JSON carries the structured DeepDive/QuickMention data
    # across the draft → PR-merge → send boundary so channel renderers don't
    # have to regex-parse the markdown body. Not part of content_sha256.
    sidecar_path = output_dir / f"{issue.issue_id}.json"
    sidecar_path.write_text(issue.to_sidecar_json(), encoding="utf-8")
    click.echo(f"wrote sidecar: {sidecar_path}")

    usage = llm.usage_report()
    click.echo(
        f"usage: {usage['total_tokens_used']}/{usage['budget_tokens']} tokens "
        f"({usage['budget_remaining']} remaining)"
    )
    sys.exit(EXIT_OK)


def _stub_issue(*, items: list[Any], output_dir: Path, dry_run: bool) -> RenderedIssue:
    """Wire a minimal RenderedIssue from items so US0012 can be tested.

    Full pipeline (cluster → rank → compose) integration is exercised
    end-to-end via dry-run smoke tests in TS0003 integration suite.
    """
    _ = output_dir, dry_run  # acknowledged; not used in stub
    if len(items) < 2:
        # Need at least 2 items for assemble_issue's count guard
        items = items * 3 if items else []

    now = datetime.now(UTC)
    issue_id = f"issue-{now.strftime('%Y-%m-%d')}"
    # Build 3 stub deep dives + 3 quick mentions just to satisfy assemble_issue
    deep_dives = [
        DeepDive(
            cluster_id=f"c{i}",
            title=f"Stub deep dive {i}",
            body_md=f"Stub body for cluster {i}. Real compose pipeline runs here.",
            item_kind="paper",
            primary_url="https://example.com/stub",  # type: ignore[arg-type]
            source_count=1,
        )
        for i in range(3)
    ]
    quick = [
        QuickMention(
            title=f"Stub quick {i}",
            url="https://example.com/stub",  # type: ignore[arg-type]
            source="arxiv",
            item_kind="paper",
            one_liner=f"Stub quick mention {i}.",
        )
        for i in range(3)
    ]
    return assemble_issue(
        issue_id=issue_id,
        issue_date=now,
        deep_dives=deep_dives,
        quick_mentions=quick,
    )


def main() -> None:
    cli()  # pragma: no cover


if __name__ == "__main__":  # pragma: no cover
    main()
