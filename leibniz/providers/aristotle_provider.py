"""Harmonic Aristotle proof provider (ADR 0028 / lever 3) — PROPOSAL ONLY.

Aristotle is a hosted theorem-proving agent: give it a Lean 4 project whose goals are
`sorry`, and it returns the project with the sorries filled by formally-verified proofs.
We use it as one more `ProviderAdapter`: it PROPOSES a proof; Leibniz's own Lean kernel
(`LeanVerifier.discharge`) still SOLELY decides (ADR 0001). Aristotle's internal
verification is irrelevant to our trust boundary — we re-check whatever it returns.

Unlike the single-shot HTTP provers, Aristotle is **project-based and asynchronous**
(submit → poll an AgentTask → download the filled files), so a `propose()` call here can
take minutes. It uses the official `aristotlelib` client (lazy import; ships behind the
`propose` extra), authed by `ARISTOTLE_API_KEY`.

Two flow details are pinned to `aristotlelib`'s API but only fully confirmable on a first
live run (the dashboard API docs are auth-gated): (1) whether `create_from_directory`
auto-starts the agent task or needs a follow-up `ask`; (2) that the filled proof comes
back via `get_files`. The code handles (1) defensively and `scripts/try_aristotle.py`
validates both end-to-end.
"""
from __future__ import annotations

import asyncio
import os
import tarfile
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from leibniz.providers import ProviderUnavailable
from leibniz.types import Role

_FILL_PROMPT = (
    "Replace every `sorry` in this Lean 4 project with a complete, correct, "
    "kernel-checkable proof. Do NOT change any theorem statement; only fill the proofs."
)
# Terminal AgentTask statuses (by name, so we don't hard-import the enum at module load).
_TERMINAL = {"COMPLETE", "COMPLETE_WITH_ERRORS", "FAILED", "CANCELED", "OUT_OF_BUDGET", "UNKNOWN"}


def _strip_to_statement(theorem_src: str) -> str:
    """Drop any `:= …` proof tail so we submit `theorem … := by sorry` for Aristotle to
    fill (mirrors the backends' _join_proof convention)."""
    head = theorem_src.rstrip()
    cut = head.find(":=")
    if cut != -1:
        head = head[:cut].rstrip()
    return f"{head} := by sorry"


def _extract_proof(lean_text: str) -> str:
    """Pull the proof body (everything after the first `:=`) out of a filled Lean file,
    so it can be re-attached to our statement and re-checked by our kernel."""
    cut = lean_text.find(":=")
    return lean_text[cut + 2:].strip() if cut != -1 else ""


@dataclass
class AristotleProver:
    """A prover-ensemble member backed by Harmonic Aristotle. Proposal-only."""

    api_key_env: str = "ARISTOTLE_API_KEY"
    imports: tuple[str, ...] = ("Mathlib",)
    poll_interval_s: float = 10.0
    timeout_s: float = 1800.0           # Aristotle jobs run minutes→hours; bound it
    meter: Optional[object] = None      # Aristotle bills per job, not per token — not metered here
    # Aristotle ingests a Lean PROJECT and warns when no `lean-toolchain` is present; ship
    # one. Default to Aristotle's OWN deps toolchain (v4.28.0): a first live run showed
    # Aristotle's Mathlib/Batteries are built for 4.28, so submitting 4.31 forced it to
    # self-correct down to 4.28 before it could build. The resulting proof still
    # re-verifies cleanly on OUR 4.31 kernel (confirmed live), so 4.28 here is strictly
    # better. Override via LEIBNIZ_ARISTOTLE_TOOLCHAIN. Mathlib deps (the `.lake` warning)
    # are resolved on Aristotle's side; we don't ship them.
    toolchain: str = field(
        default_factory=lambda: os.environ.get("LEIBNIZ_ARISTOTLE_TOOLCHAIN")
        or "leanprover/lean4:v4.28.0"
    )

    def available(self) -> bool:
        if not os.environ.get(self.api_key_env):
            return False
        try:
            import aristotlelib  # noqa: F401
            return True
        except ImportError:
            return False

    def _lib(self):
        try:
            import aristotlelib
        except ImportError as e:  # pragma: no cover
            raise ProviderUnavailable("aristotlelib not installed (propose extra)") from e
        key = os.environ.get(self.api_key_env)
        if not key:
            raise ProviderUnavailable(f"{self.api_key_env} not set")
        aristotlelib.set_api_key(key)
        return aristotlelib

    def propose(self, role: Role, context: str) -> str:
        """For PROOF_DRAFT: submit `context` (a theorem statement) to Aristotle as a
        one-file Lean project, wait for the agent to fill the `sorry`, and return the
        proof body. Other roles are unsupported (Aristotle is a prover).

        `aristotlelib` is async; `propose` is sync (the ProviderAdapter contract), so the
        async flow runs in a fresh event loop. ProofConsensus calls provers in worker
        threads, each of which gets its own loop, so this composes with the ensemble."""
        if role is not Role.PROOF_DRAFT:
            raise ProviderUnavailable(f"AristotleProver only handles PROOF_DRAFT, not {role}")
        return asyncio.run(self._aprove(context))

    async def _aprove(self, context: str) -> str:
        lib = self._lib()  # set_api_key is sync
        with tempfile.TemporaryDirectory() as work:
            (Path(work) / "lean-toolchain").write_text(self.toolchain + "\n")  # Aristotle wants this
            src = "\n".join(f"import {m}" for m in self.imports) + "\n\n" + _strip_to_statement(context)
            (Path(work) / "Thm.lean").write_text(src + "\n")
            project = await lib.Project.create_from_directory(_FILL_PROMPT, work)
        task = await self._await_task(project)
        if task is None or str(getattr(task.status, "name", task.status)) != "COMPLETE":
            return ""  # no usable proof — Leibniz settles this candidate UNPROVEN
        with tempfile.TemporaryDirectory() as out:
            # get_files writes to a FILE path (a tarball, like the CLI's
            # `download --destination result.tar.gz`) — NOT a directory.
            dest = Path(out) / "aristotle_result.tar.gz"
            try:
                got = await project.get_files(str(dest))
            except Exception:
                got = None
            return self._read_proof(got or dest, out)

    async def _await_task(self, project):
        """Get the agent task (create may auto-start it; else `ask`) and poll to terminal."""
        tasks, _ = await project.get_tasks(limit=1)
        task = tasks[0] if tasks else await project.ask(_FILL_PROMPT)
        start = time.time()
        while True:
            await task.refresh()
            if str(getattr(task.status, "name", task.status)) in _TERMINAL:
                return task
            if time.time() - start > self.timeout_s:
                try:
                    await task.cancel()
                except Exception:
                    pass
                return None
            await asyncio.sleep(self.poll_interval_s)

    @staticmethod
    def _read_proof(path, work=None) -> str:
        """Read the filled proof from Aristotle's download — a tarball, a directory, or a
        single .lean. Returns the first non-`sorry` proof body found; "" if none."""
        p = Path(path)
        candidates: list[Path] = []
        if p.is_file() and tarfile.is_tarfile(p):
            ex = Path(work or p.parent) / "_extracted"
            ex.mkdir(parents=True, exist_ok=True)
            with tarfile.open(p) as tf:
                tf.extractall(ex, filter="data")  # safe extraction (no path traversal)
            candidates = sorted(ex.rglob("*.lean"))
        elif p.is_file():
            candidates = [p]
        elif p.is_dir():
            candidates = sorted(p.rglob("*.lean"))
        if not candidates and work:  # fallback: scan the work dir broadly
            candidates = sorted(Path(work).rglob("*.lean"))
        for f in candidates:
            try:
                proof = _extract_proof(f.read_text())
            except OSError:
                continue
            if proof and "sorry" not in proof:
                return proof
        return ""
