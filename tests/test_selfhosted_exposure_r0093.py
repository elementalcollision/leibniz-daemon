"""ADR 0093 — a self-hosted runner on a PUBLIC repo must never be reachable from an untrusted trigger.

`kernel-nightly.yml` targets `[self-hosted, lean]`, and this repository is public. GitHub warns
against exactly that combination: if any workflow ever pairs a self-hosted job with a fork-reachable
trigger (`pull_request`, `pull_request_target`, `issue_comment`, ...), an outside contributor's PR
runs arbitrary code on the operator's own machine.

Today that is safe, and ADR 0049 says so in a comment: the kernel lane uses only `schedule` and
`workflow_dispatch`. But a comment is a convention, and a convention is one edit away from being
false. This test makes it mechanical: it reads every workflow and fails if a self-hosted job is
reachable from a trigger a fork can fire. Stdlib-only, so it runs in the BLOCKING invariants job.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

_WF = Path(__file__).resolve().parent.parent / ".github" / "workflows"

#: Triggers an outside contributor can cause to fire on this repository.
UNTRUSTED = ("pull_request", "pull_request_target", "issue_comment", "issues",
             "fork", "watch", "discussion", "discussion_comment")


def _workflows():
    return sorted(p for p in _WF.glob("*.yml")) + sorted(_WF.glob("*.yaml"))


def _trigger_block(src: str) -> str:
    """The `on:` block, without needing a YAML parser (core install is stdlib-only)."""
    m = re.search(r"^on:\s*$\n((?:[ \t]+.*\n|\n)*)", src, re.M)
    if m:
        return m.group(1)
    m = re.search(r"^on:\s*(.+)$", src, re.M)          # inline form: `on: [push]`
    return m.group(1) if m else ""


def _declared_triggers(block: str) -> set[str]:
    out = set()
    for line in block.splitlines():
        s = line.strip().lstrip("-").strip()
        if not s or s.startswith("#"):
            continue
        name = s.split(":")[0].strip().strip("[],'\" ")
        # only top-level trigger names, not the nested keys under them
        if name and re.fullmatch(r"[a-z_]+", name):
            out.add(name)
    return out


def test_workflows_exist():
    assert _workflows(), "no workflows found — the check would pass vacuously"


@pytest.mark.parametrize("wf", _workflows(), ids=lambda p: p.name)
def test_no_self_hosted_job_is_reachable_from_an_untrusted_trigger(wf):
    src = wf.read_text()
    if "self-hosted" not in src:
        return                                        # nothing to protect in this file
    fired_by = _declared_triggers(_trigger_block(src)) & set(UNTRUSTED)
    assert not fired_by, (
        f"{wf.name} runs a self-hosted job AND can be fired by {sorted(fired_by)}. On a public "
        f"repository that lets a fork PR execute arbitrary code on the operator's machine. "
        f"Use `schedule` / `workflow_dispatch` only (ADR 0049), or move the job to a hosted runner."
    )


def test_the_check_would_actually_catch_a_violation(tmp_path):
    """A guard that cannot fail is not a guard. Feed it the dangerous shape and require a catch."""
    bad = tmp_path / "bad.yml"
    bad.write_text("name: bad\non:\n  pull_request:\njobs:\n  j:\n    runs-on: [self-hosted, lean]\n")
    src = bad.read_text()
    assert "self-hosted" in src
    assert _declared_triggers(_trigger_block(src)) & set(UNTRUSTED) == {"pull_request"}


def test_kernel_nightly_still_uses_only_trusted_triggers():
    """Named explicitly: this is the file the runner exists for."""
    src = (_WF / "kernel-nightly.yml").read_text()
    trig = _declared_triggers(_trigger_block(src))
    assert "schedule" in trig and "workflow_dispatch" in trig
    assert not (trig & set(UNTRUSTED))
