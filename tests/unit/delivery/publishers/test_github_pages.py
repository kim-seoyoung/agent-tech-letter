"""US0029: GitHubPagesPublisher tests (mocked git subprocess).

Covers AC1 (signature + name), AC2 (first publish: seed + write + commit + push),
AC3 (idempotency: no commit on identical bytes), AC4 (worktree provisioned),
AC5 (dirty worktree refusal), AC6 (secret scrubbing — RV0002 F-4),
AC7 (file equals html_web.render), AC8 (seed files written only when missing — RV0002 F-3).
"""

from __future__ import annotations

import subprocess
from datetime import UTC, datetime
from pathlib import Path

import pytest

from techletter.compose.issue import RenderedIssue, assemble_issue
from techletter.compose.types import DeepDive
from techletter.delivery.publishers.base import PublisherError
from techletter.delivery.publishers.github_pages import (
    GitHubPagesPublisher,
    scrub_secrets,
)
from techletter.delivery.renderers.html_web import render as render_html_web

# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------


class _GitRecorder:
    """Records every git invocation and returns scripted CompletedProcess values."""

    def __init__(self, scripts: list[dict] | None = None) -> None:
        # Each script entry: {"match": substring or tuple, "rc": int, "stdout": "", "stderr": ""}
        self.scripts: list[dict] = scripts or []
        self.calls: list[tuple[tuple[str, ...], Path]] = []

    def __call__(self, args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
        self.calls.append((tuple(args), cwd))
        for spec in self.scripts:
            m = spec["match"]
            if isinstance(m, str):
                if m in " ".join(args):
                    return subprocess.CompletedProcess(
                        ["git", *args],
                        spec.get("rc", 0),
                        spec.get("stdout", ""),
                        spec.get("stderr", ""),
                    )
            else:  # tuple/list of substrings, all must appear
                if all(p in " ".join(args) for p in m):
                    return subprocess.CompletedProcess(
                        ["git", *args],
                        spec.get("rc", 0),
                        spec.get("stdout", ""),
                        spec.get("stderr", ""),
                    )
        # default: success
        return subprocess.CompletedProcess(["git", *args], 0, "", "")

    def saw(self, *patterns: str) -> bool:
        return any(all(p in " ".join(args) for p in patterns) for args, _ in self.calls)


def _issue() -> RenderedIssue:
    return assemble_issue(
        issue_id="issue-2026-05-21",
        issue_date=datetime(2026, 5, 21, tzinfo=UTC),
        deep_dives=[
            DeepDive(
                cluster_id=f"c{i}",
                title=f"t{i}",
                body_md="b",
                item_kind="paper",
                primary_url="https://example.com",  # type: ignore[arg-type]
                source_count=1,
            )
            for i in range(2)
        ],
        quick_mentions=[],
    )


def _build(tmp_path: Path, runner: _GitRecorder) -> GitHubPagesPublisher:
    repo = tmp_path / "repo"
    worktree = tmp_path / "wt"
    repo.mkdir()
    worktree.mkdir()  # pretend worktree already provisioned
    return GitHubPagesPublisher(
        repo_path=repo,
        base_url="https://user.github.io/repo",
        author_name="bot",
        author_email="bot@example.com",
        worktree_path=worktree,
        runner=runner,
    )


# ----------------------------------------------------------------------------
# AC1
# ----------------------------------------------------------------------------


def test_AC1_publisher_name():
    p = GitHubPagesPublisher(
        repo_path=Path("."),
        base_url="https://x.github.io/y",
        author_name="bot",
        author_email="b@e.com",
        runner=_GitRecorder(),
    )
    assert p.name == "github_pages"


# ----------------------------------------------------------------------------
# AC2 — first publish writes + commits + pushes
# ----------------------------------------------------------------------------


def test_AC2_first_publish_commits_and_pushes(tmp_path: Path):
    runner = _GitRecorder(
        scripts=[
            {"match": "status --porcelain", "rc": 0, "stdout": ""},
            {"match": "diff --cached --quiet", "rc": 1},  # there IS a diff
            {"match": "rev-parse HEAD", "rc": 0, "stdout": "a" * 40},
        ]
    )
    pub = _build(tmp_path, runner)
    issue = _issue()

    result = pub.publish(issue)

    assert result.url.startswith("https://user.github.io/repo/issues/2026-05-21-")
    assert result.url.endswith(".html")
    assert result.commit_sha == "a" * 40
    assert runner.saw("add", "--", "issues/")
    assert runner.saw("commit", "-m")
    assert runner.saw("push", "origin", "gh-pages")

    # Seed files written
    assert (pub.worktree_path / ".nojekyll").exists()
    robots = (pub.worktree_path / "robots.txt").read_text(encoding="utf-8")
    assert robots == "User-agent: *\nDisallow: /\n"


# ----------------------------------------------------------------------------
# AC3 — idempotency
# ----------------------------------------------------------------------------


def test_AC3_idempotent_no_commit_on_same_content(tmp_path: Path):
    issue = _issue()
    # Pre-seed the worktree with the exact bytes the renderer would write.
    pub_setup_runner = _GitRecorder()
    pub_pre = _build(tmp_path, pub_setup_runner)
    sha16 = issue.content_sha256[:16]
    target = pub_pre.worktree_path / f"issues/2026-05-21-{sha16}.html"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render_html_web(issue), encoding="utf-8")
    # Seed the infra files so AC8 doesn't trigger writes
    (pub_pre.worktree_path / ".nojekyll").write_text("", encoding="utf-8")
    (pub_pre.worktree_path / "robots.txt").write_text(
        "User-agent: *\nDisallow: /\n", encoding="utf-8"
    )

    runner = _GitRecorder(
        scripts=[
            {"match": "status --porcelain", "rc": 0, "stdout": ""},
            {"match": "diff --cached --quiet", "rc": 0},  # NO diff
            {"match": "rev-parse HEAD", "rc": 0, "stdout": "b" * 40},
        ]
    )
    pub = GitHubPagesPublisher(
        repo_path=pub_pre.repo_path,
        base_url="https://user.github.io/repo",
        author_name="bot",
        author_email="b@e.com",
        worktree_path=pub_pre.worktree_path,
        runner=runner,
    )

    result = pub.publish(issue)

    assert result.commit_sha == "b" * 40
    assert not runner.saw("commit", "-m")
    assert not runner.saw("push", "origin")


# ----------------------------------------------------------------------------
# AC4 — worktree provisioned on demand
# ----------------------------------------------------------------------------


def test_AC4_provisions_worktree_if_missing(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    worktree = tmp_path / "wt"
    # NOTE: worktree path does NOT exist yet
    assert not worktree.exists()

    # Side-effect: when "worktree add" runs, we actually create the dir so
    # subsequent operations (status, seed) work.
    class Runner(_GitRecorder):
        def __call__(self, args, cwd):
            if "worktree" in args and "add" in args:
                worktree.mkdir(parents=True, exist_ok=True)
            return super().__call__(args, cwd)

    runner = Runner(
        scripts=[
            {"match": "status --porcelain", "rc": 0, "stdout": ""},
            {"match": "diff --cached --quiet", "rc": 1},
            {"match": "rev-parse HEAD", "rc": 0, "stdout": "c" * 40},
        ]
    )
    pub = GitHubPagesPublisher(
        repo_path=repo,
        base_url="https://user.github.io/repo",
        author_name="bot",
        author_email="b@e.com",
        worktree_path=worktree,
        runner=runner,
    )
    pub.publish(_issue())
    assert runner.saw("worktree", "add")


# ----------------------------------------------------------------------------
# AC5 — dirty worktree refusal
# ----------------------------------------------------------------------------


def test_AC5_dirty_worktree_raises(tmp_path: Path):
    runner = _GitRecorder(
        scripts=[
            {"match": "status --porcelain", "rc": 0, "stdout": " M some-file\n"},
        ]
    )
    pub = _build(tmp_path, runner)

    with pytest.raises(PublisherError, match="dirty"):
        pub.publish(_issue())

    # No commit/push attempted
    assert not runner.saw("commit", "-m")
    assert not runner.saw("push")


# ----------------------------------------------------------------------------
# AC6 — secret scrubbing (RV0002 F-4)
# ----------------------------------------------------------------------------


@pytest.mark.parametrize(
    "input_str,must_not_contain",
    [
        (
            "fatal: could not push to https://x-access-token:ghs_AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA@github.com/u/r.git",
            ["ghs_AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA", "x-access-token"],
        ),
        (
            "ghp_BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB invalid",
            ["ghp_BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB"],
        ),
        (
            "could not open /Users/me/.ssh/id_rsa",
            ["/Users/me/.ssh/id_rsa"],
        ),
    ],
)
def test_AC6_scrub_known_patterns(input_str: str, must_not_contain: list[str]):
    out = scrub_secrets(input_str)
    for pattern in must_not_contain:
        assert pattern not in out, f"scrub failed: '{pattern}' still in '{out}'"


def test_AC6_scrub_env_github_token(monkeypatch):
    secret = "ghs_" + "Z" * 40
    monkeypatch.setenv("GITHUB_TOKEN", secret)
    out = scrub_secrets(f"git command leaked: {secret} here")
    assert secret not in out
    assert "[REDACTED]" in out


def test_AC6_push_failure_raises_with_scrubbed_message(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "ghs_" + "X" * 40)
    leaked_stderr = (
        "fatal: could not push to "
        "https://x-access-token:ghs_XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX@github.com/u/r.git"
    )
    runner = _GitRecorder(
        scripts=[
            {"match": "status --porcelain", "rc": 0, "stdout": ""},
            {"match": "diff --cached --quiet", "rc": 1},
            {"match": "push origin", "rc": 1, "stderr": leaked_stderr},
        ]
    )
    pub = _build(tmp_path, runner)

    with pytest.raises(PublisherError) as exc_info:
        pub.publish(_issue())

    msg = str(exc_info.value)
    assert "ghs_XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX" not in msg
    assert "x-access-token" not in msg
    assert "[REDACTED]" in msg


# ----------------------------------------------------------------------------
# AC7 — file content equals html_web.render byte-for-byte
# ----------------------------------------------------------------------------


def test_AC7_file_equals_html_web_render(tmp_path: Path):
    runner = _GitRecorder(
        scripts=[
            {"match": "status --porcelain", "rc": 0},
            {"match": "diff --cached --quiet", "rc": 1},
            {"match": "rev-parse HEAD", "rc": 0, "stdout": "d" * 40},
        ]
    )
    pub = _build(tmp_path, runner)
    issue = _issue()
    pub.publish(issue)

    sha16 = issue.content_sha256[:16]
    written = (pub.worktree_path / f"issues/2026-05-21-{sha16}.html").read_text(encoding="utf-8")
    assert written == render_html_web(issue)


# ----------------------------------------------------------------------------
# AC8 — seed files written only when missing (RV0002 F-3)
# ----------------------------------------------------------------------------


def test_AC8_seed_files_not_rewritten_when_present(tmp_path: Path, monkeypatch):
    runner = _GitRecorder(
        scripts=[
            {"match": "status --porcelain", "rc": 0},
            {"match": "diff --cached --quiet", "rc": 1},
            {"match": "rev-parse HEAD", "rc": 0, "stdout": "e" * 40},
        ]
    )
    pub = _build(tmp_path, runner)
    # Pre-populate seed files with specific content
    (pub.worktree_path / ".nojekyll").write_text("pre-existing", encoding="utf-8")
    (pub.worktree_path / "robots.txt").write_text("CUSTOM CONTENT\n", encoding="utf-8")

    # Spy on Path.write_text — any call to either seed file fails the test
    seed_paths = {
        str(pub.worktree_path / ".nojekyll"),
        str(pub.worktree_path / "robots.txt"),
    }
    write_calls: list[str] = []

    original = Path.write_text

    def spy(self, *args, **kwargs):
        if str(self) in seed_paths:
            write_calls.append(str(self))
        return original(self, *args, **kwargs)

    monkeypatch.setattr(Path, "write_text", spy)

    pub.publish(_issue())

    assert write_calls == [], f"unexpected writes to seed files: {write_calls}"
    # Content preserved
    assert (pub.worktree_path / ".nojekyll").read_text(encoding="utf-8") == "pre-existing"
    assert (pub.worktree_path / "robots.txt").read_text(encoding="utf-8") == "CUSTOM CONTENT\n"


def test_AC8_seed_files_written_on_first_publish(tmp_path: Path):
    runner = _GitRecorder(
        scripts=[
            {"match": "status --porcelain", "rc": 0},
            {"match": "diff --cached --quiet", "rc": 1},
            {"match": "rev-parse HEAD", "rc": 0, "stdout": "f" * 40},
        ]
    )
    pub = _build(tmp_path, runner)
    # Worktree is clean (build creates the dir but no files)
    assert not (pub.worktree_path / ".nojekyll").exists()
    assert not (pub.worktree_path / "robots.txt").exists()

    pub.publish(_issue())

    assert (pub.worktree_path / ".nojekyll").read_text(encoding="utf-8") == ""
    assert (
        pub.worktree_path / "robots.txt"
    ).read_text(encoding="utf-8") == "User-agent: *\nDisallow: /\n"
