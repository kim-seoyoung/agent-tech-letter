"""US0029: GitHubPagesPublisher — writes the rendered page to `gh-pages`.

Drives `git` via subprocess (no GitPython). Reasons:
- Easier to scrub secrets: we control exactly what stderr we see.
- No new dep.
- Easier to test by injecting the subprocess runner.

Idempotency rule (per EP0006 + RV0002): same `content_sha256` → same
file path → if bytes match, `git diff --quiet` returns 0, and we
return the existing HEAD without committing or pushing.

Security rule (RV0002 F-4): all stderr passes through `_scrub` before
appearing in any exception or log message.
"""

from __future__ import annotations

import logging
import os
import re
import subprocess
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from techletter.compose.issue import RenderedIssue
from techletter.delivery.publishers.base import PublisherError, PublishResult
from techletter.delivery.renderers.html_web import render as render_html_web

__all__ = ["GitHubPagesPublisher", "scrub_secrets"]

logger = logging.getLogger(__name__)


# Subprocess runner type; injectable for testing.
GitRunner = Callable[[list[str], Path], subprocess.CompletedProcess[str]]


def _default_git_runner(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=False,
    )


# --- scrubbing ---------------------------------------------------------------

# Pre-compile patterns once (RV0002 F-4).
_RE_TOKEN_URL = re.compile(r"https?://[^@\s]+@github\.com/[^\s]*")
_RE_GHS = re.compile(r"ghs_[A-Za-z0-9]{36,}")
_RE_GHP = re.compile(r"ghp_[A-Za-z0-9]{36,}")
_RE_SSH_PATH = re.compile(r"(/[^\s]*\.ssh/[^\s]+|/[^\s]*ssh-agent[^\s]*)")


def scrub_secrets(s: str) -> str:
    """Remove credentials/secrets from any git stderr or log line."""
    if not s:
        return s
    out = _RE_TOKEN_URL.sub("https://[REDACTED]@github.com/...", s)
    out = _RE_GHS.sub("ghs_[REDACTED]", out)
    out = _RE_GHP.sub("ghp_[REDACTED]", out)
    out = _RE_SSH_PATH.sub("[SSH_PATH_REDACTED]", out)
    tok = os.environ.get("GITHUB_TOKEN")
    if tok and len(tok) > 4:
        out = out.replace(tok, "[REDACTED]")
    sock = os.environ.get("SSH_AUTH_SOCK")
    if sock:
        out = out.replace(sock, "[SSH_AUTH_SOCK_REDACTED]")
    return out


# --- publisher ---------------------------------------------------------------


class GitHubPagesPublisher:
    """Writes `issues/<YYYY-MM-DD>-<sha16>.html` to a `gh-pages` worktree
    and pushes to `origin/gh-pages`. Idempotent on same content.
    """

    name: str = "github_pages"

    def __init__(
        self,
        *,
        repo_path: Path,
        base_url: str,
        author_name: str,
        author_email: str,
        branch: str = "gh-pages",
        worktree_path: Path | None = None,
        runner: GitRunner | None = None,
    ) -> None:
        self.repo_path = Path(repo_path)
        self.base_url = base_url.rstrip("/")
        self.author_name = author_name
        self.author_email = author_email
        self.branch = branch
        # Default worktree path must be OUTSIDE `.git/` — git stores worktree
        # metadata at `.git/worktrees/<name>/`, which collides with the
        # contents we'd check out there.
        self.worktree_path = (
            Path(worktree_path)
            if worktree_path is not None
            else self.repo_path / ".gh-pages-publish"
        )
        self._runner: GitRunner = runner or _default_git_runner

    # -- public ----------------------------------------------------------------

    def publish(self, issue: RenderedIssue) -> PublishResult:
        self._ensure_worktree()
        self._assert_worktree_clean()
        self._seed_pages_infra()

        sha16 = issue.content_sha256[:16].ljust(16, "0")
        date_str = issue.issue_date.strftime("%Y-%m-%d")
        rel_path = f"issues/{date_str}-{sha16}.html"
        target = self.worktree_path / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)

        body = render_html_web(issue)
        # AC3 idempotency: only write if file is missing or content differs.
        existing = target.read_text(encoding="utf-8") if target.exists() else None
        if existing != body:
            target.write_text(body, encoding="utf-8")

        url = f"{self.base_url}/{rel_path}"

        # Stage + check for diff. If no diff → keep current HEAD, no commit/push.
        self._git_or_raise(["add", "--", rel_path, ".nojekyll", "robots.txt"], stage="add")
        diff = self._runner(["diff", "--cached", "--quiet"], self.worktree_path)
        if diff.returncode == 0:
            # No diff → idempotent return
            head_sha = self._rev_parse_head()
            return PublishResult(
                url=url,
                path=rel_path,
                published_at=datetime.now(UTC),
                publisher_name=self.name,
                commit_sha=head_sha,
            )

        # Commit + push
        msg = f"publish: {issue.issue_id} {issue.content_sha256[:8]}"
        self._git_or_raise(
            [
                "-c",
                f"user.name={self.author_name}",
                "-c",
                f"user.email={self.author_email}",
                "commit",
                "-m",
                msg,
            ],
            stage="commit",
        )
        self._git_or_raise(["push", "origin", self.branch], stage="push")

        return PublishResult(
            url=url,
            path=rel_path,
            published_at=datetime.now(UTC),
            publisher_name=self.name,
            commit_sha=self._rev_parse_head(),
        )

    # -- helpers ---------------------------------------------------------------

    def _ensure_worktree(self) -> None:
        if self.worktree_path.exists():
            return
        self.worktree_path.parent.mkdir(parents=True, exist_ok=True)
        r = self._runner(
            ["worktree", "add", str(self.worktree_path), self.branch],
            self.repo_path,
        )
        if r.returncode != 0:
            raise PublisherError(
                f"failed to provision worktree for branch '{self.branch}': "
                f"{scrub_secrets(r.stderr)}"
            )

    def _assert_worktree_clean(self) -> None:
        # `git status --porcelain` is empty when worktree is clean.
        r = self._runner(["status", "--porcelain"], self.worktree_path)
        if r.returncode != 0:
            raise PublisherError(
                f"failed to status worktree at {self.worktree_path}: "
                f"{scrub_secrets(r.stderr)}"
            )
        if r.stdout.strip():
            raise PublisherError(
                f"gh-pages worktree at {self.worktree_path} is dirty; "
                f"clean it manually before publishing"
            )

    def _seed_pages_infra(self) -> None:
        # Per RV0002 F-3: write only when missing.
        nojekyll = self.worktree_path / ".nojekyll"
        if not nojekyll.exists():
            nojekyll.write_text("", encoding="utf-8")
        robots = self.worktree_path / "robots.txt"
        if not robots.exists():
            robots.write_text("User-agent: *\nDisallow: /\n", encoding="utf-8")

    def _rev_parse_head(self) -> str:
        r = self._runner(["rev-parse", "HEAD"], self.worktree_path)
        if r.returncode != 0:
            raise PublisherError(f"failed to read HEAD: {scrub_secrets(r.stderr)}")
        return r.stdout.strip()

    def _git_or_raise(self, args: list[str], *, stage: str) -> None:
        r = self._runner(args, self.worktree_path)
        if r.returncode != 0:
            raise PublisherError(
                f"git {stage} failed (exit {r.returncode}): "
                f"{scrub_secrets(r.stderr)}"
            )
