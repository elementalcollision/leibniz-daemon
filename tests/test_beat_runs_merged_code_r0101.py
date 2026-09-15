"""ADR 0101 -- the beat must not mint against stale code, silently.

ADR 0068 says the daemon "always runs the latest OPERATOR-MERGED code, never a working tree". That
was an intention, not a check. Both worktree-sync failures printed
`WARN: ... running last-synced code` and CARRIED ON.

Observed live on 2026-09-15: the beat ran pinned to 9484d5e -- four trust-boundary ADRs behind
origin/main, including the one that fixed a demonstrated `kernel_verified=True` on a false theorem
-- and promulgated a law. Nothing was published (publication is the operator's ADR 0033 act), but
the verdict came from a build with a known hole and nothing said so. The three nights before it,
`git fetch` failed with `Could not resolve host` and that too was only a WARN in a log.

These tests RUN the launcher against a real throwaway git repo. A shell guard that is only read is
not a guard.
"""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

LAUNCHER = Path(__file__).resolve().parents[1] / "deploy" / "heartbeat" / "launch-heartbeat.sh"

pytestmark = pytest.mark.skipif(shutil.which("zsh") is None, reason="launcher is zsh")


def _git(cwd: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True,
                          check=True).stdout.strip()


def _repo(tmp_path: Path) -> Path:
    """A canonical repo with a real `origin/main` ref, as the launcher expects to find."""
    origin = tmp_path / "origin"
    origin.mkdir()
    _git(origin, "init", "--quiet", "--initial-branch=main")
    _git(origin, "config", "user.email", "t@example.com")
    _git(origin, "config", "user.name", "t")
    (origin / "README").write_text("x")
    _git(origin, "add", "-A")
    _git(origin, "commit", "--quiet", "-m", "one")

    repo = tmp_path / "repo"
    _git(tmp_path, "clone", "--quiet", str(origin), str(repo))
    _git(repo, "config", "user.email", "t@example.com")
    _git(repo, "config", "user.name", "t")
    return repo


def _run(repo: Path) -> subprocess.CompletedProcess:
    env = {**os.environ, "LEIBNIZ_REPO": str(repo)}
    return subprocess.run(["zsh", str(LAUNCHER)], capture_output=True, text=True, env=env,
                          timeout=120)


def _log(repo: Path, name: str) -> str:
    p = repo / ".leibniz" / name
    return p.read_text() if p.exists() else ""


def test_a_worktree_that_cannot_sync_ABORTS_instead_of_running_stale_code(tmp_path):
    """The live defect. A non-worktree sitting at the worktree path makes both sync commands fail;
    the launcher used to shrug and run whatever was there."""
    repo = _repo(tmp_path)
    squatter = repo / ".leibniz" / "heartbeat-wt"
    squatter.mkdir(parents=True)
    (squatter / "scripts").mkdir()
    (squatter / "scripts" / "heartbeat.py").write_text("raise SystemExit('STALE CODE RAN')")

    r = _run(repo)

    assert r.returncode == 2, f"beat did not abort:\n{_log(repo, 'heartbeat-launch.log')}"
    assert "STALE CODE RAN" not in _log(repo, "heartbeat-launch.log"), "it ran the stale beat"
    assert "ABORTED at bootstrap" in _log(repo, "alarms.log"), "abort raised no alarm"


def test_a_squatting_directory_must_not_reach_the_CANONICAL_repo(tmp_path):
    """The worse half of the same defect, and it predates ADR 0101.

    If an ordinary directory sits at the worktree path, `git -C "$WT" ..." walks UP and operates on
    the CANONICAL repo. Measured: `git -C <plain-dir> checkout --detach origin/main` succeeds and
    leaves the operator's primary checkout DETACHED (main -> HEAD). The nightly daemon was one
    stray directory away from moving the operator's own working checkout out from under them.
    """
    repo = _repo(tmp_path)
    squatter = repo / ".leibniz" / "heartbeat-wt"
    squatter.mkdir(parents=True)
    before = _git(repo, "rev-parse", "--abbrev-ref", "HEAD")
    assert before == "main"

    r = _run(repo)

    assert r.returncode == 2, _log(repo, "heartbeat-launch.log")
    assert _git(repo, "rev-parse", "--abbrev-ref", "HEAD") == "main", \
        "the beat detached the operator's canonical checkout"
    assert "canonical repo" in _log(repo, "alarms.log") + _log(repo, "heartbeat-launch.log")


def test_a_healthy_worktree_proceeds_and_records_which_commit_it_ran(tmp_path):
    """The guard must not refuse the honest case -- and every beat is now attributable to a commit,
    which is the question the 2026-09-15 beat could not answer."""
    repo = _repo(tmp_path)
    r = _run(repo)

    log = _log(repo, "heartbeat-launch.log")
    head = _git(repo, "rev-parse", "origin/main")
    # scripts/heartbeat.py is absent from this bare fixture, so it stops there -- AFTER verifying.
    assert r.returncode == 0, log
    assert "beat code: " + head[:12] in log, log
    assert "ABORTED" not in _log(repo, "alarms.log")


def test_a_failed_fetch_is_alarmed_rather_than_only_warned(tmp_path):
    """Four consecutive nights of `Could not resolve host` went unnoticed because the only record
    was a WARN in a log nothing watched. A survivable failure still has to be visible."""
    repo = _repo(tmp_path)
    _git(repo, "remote", "set-url", "origin", "https://127.0.0.1:1/nope.git")

    r = _run(repo)

    assert "could not fetch origin" in _log(repo, "alarms.log"), "a silent fetch failure again"
    # survivable: the worktree is still at the last-seen origin/main, so the beat proceeds
    assert r.returncode == 0
    assert "fetch failed, may be behind" in _log(repo, "heartbeat-launch.log")
