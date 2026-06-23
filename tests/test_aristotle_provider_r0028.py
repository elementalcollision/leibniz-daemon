"""ADR 0028 / lever 3: the Harmonic Aristotle proof provider.

Aristotle PROPOSES; our kernel still decides. CI-safe — the aristotlelib client is faked
(no network); the submit→poll→get_files flow and the proof parsing are exercised against
the fake. The real end-to-end live check is scripts/try_aristotle.py (billable)."""
from __future__ import annotations

import sys
import types
from pathlib import Path

from leibniz.providers import ProviderUnavailable
from leibniz.providers.aristotle_provider import (
    AristotleProver,
    _extract_proof,
    _strip_to_statement,
)
from leibniz.types import Role


# --- pure helpers (no lib needed) --------------------------------------------

def test_strip_to_statement_replaces_proof_tail_with_sorry():
    assert _strip_to_statement("theorem t (n:Nat) : n = n := by rfl") == "theorem t (n:Nat) : n = n := by sorry"
    assert _strip_to_statement("theorem t : True") == "theorem t : True := by sorry"


def test_extract_proof_takes_body_after_assign():
    assert _extract_proof("theorem t : True := by trivial") == "by trivial"
    assert _extract_proof("no assignment here") == ""


def test_read_proof_skips_sorry_and_reads_filled(tmp_path):
    (tmp_path / "Thm.lean").write_text("import Mathlib\n\ntheorem t : True := by trivial\n")
    assert AristotleProver._read_proof(tmp_path) == "by trivial"
    (tmp_path / "Thm.lean").write_text("theorem t : True := by sorry\n")
    assert AristotleProver._read_proof(tmp_path) == ""  # an unfilled sorry is not a proof


def test_read_proof_extracts_from_tarball(tmp_path):
    import io
    import tarfile
    tb = tmp_path / "result.tar.gz"
    body = b"theorem t : True := by trivial\n"
    with tarfile.open(tb, "w:gz") as tf:
        info = tarfile.TarInfo(name="Thm.lean")
        info.size = len(body)
        tf.addfile(info, io.BytesIO(body))
    assert AristotleProver._read_proof(tb, str(tmp_path)) == "by trivial"  # untars + reads


# --- availability + role guard -----------------------------------------------

def test_unavailable_without_key(monkeypatch):
    monkeypatch.delenv("ARISTOTLE_API_KEY", raising=False)
    assert AristotleProver().available() is False


def test_default_toolchain_matches_aristotles_deps(monkeypatch):
    # live learning: Aristotle's Mathlib/Batteries are built for 4.28; submitting 4.31
    # forced a self-correction. Default to 4.28 (the proof still re-verifies on our 4.31).
    monkeypatch.delenv("LEIBNIZ_ARISTOTLE_TOOLCHAIN", raising=False)
    assert AristotleProver().toolchain == "leanprover/lean4:v4.28.0"


def test_non_proof_role_is_rejected(monkeypatch):
    monkeypatch.setenv("ARISTOTLE_API_KEY", "k")
    monkeypatch.setitem(sys.modules, "aristotlelib", _fake_lib())
    try:
        AristotleProver(poll_interval_s=0).propose(Role.CONJECTURE, "x")
        assert False, "expected ProviderUnavailable"
    except ProviderUnavailable:
        pass


# --- submit -> poll -> get_files flow (fake aristotlelib) --------------------

def _fake_lib(status="COMPLETE", filled="theorem t : True := by simp", captured=None):
    # aristotlelib is async: every Project/AgentTask method is a coroutine (set_api_key
    # is sync). The fake mirrors that so the await path in AristotleProver is exercised.
    # `captured` (a dict) records what was submitted, so tests can assert the project shape.
    m = types.ModuleType("aristotlelib")
    m.set_api_key = lambda k: k

    class _Status:
        def __init__(self, name):
            self.name = name

    class _Task:
        def __init__(self):
            self.status = _Status(status)

        async def refresh(self):
            pass

        async def cancel(self):
            pass

    class _Project:
        @classmethod
        async def create_from_directory(cls, prompt, d, **kw):
            if captured is not None:
                captured["files"] = sorted(p.name for p in Path(d).iterdir())
                tc = Path(d) / "lean-toolchain"
                captured["toolchain"] = tc.read_text() if tc.exists() else None
            return cls()

        async def get_tasks(self, limit=1):
            return ([_Task()], None)

        async def ask(self, prompt, **kw):
            return _Task()

        async def get_files(self, dest):
            import io
            import tarfile
            body = (filled + "\n").encode()  # real get_files writes a tarball at a FILE path
            with tarfile.open(dest, "w:gz") as tf:
                info = tarfile.TarInfo(name="Thm.lean")
                info.size = len(body)
                tf.addfile(info, io.BytesIO(body))
            return dest

    m.Project = _Project
    return m


def test_propose_returns_proof_body_on_complete(monkeypatch):
    monkeypatch.setenv("ARISTOTLE_API_KEY", "k")
    monkeypatch.setitem(sys.modules, "aristotlelib", _fake_lib("COMPLETE", "theorem t : True := by simp"))
    out = AristotleProver(poll_interval_s=0).propose(Role.PROOF_DRAFT, "theorem t : True")
    assert out == "by simp"  # the filled proof body, ready for our kernel to re-check


def test_propose_returns_empty_on_failed(monkeypatch):
    monkeypatch.setenv("ARISTOTLE_API_KEY", "k")
    monkeypatch.setitem(sys.modules, "aristotlelib", _fake_lib("FAILED", "irrelevant"))
    out = AristotleProver(poll_interval_s=0).propose(Role.PROOF_DRAFT, "theorem t : True")
    assert out == ""  # a non-COMPLETE task yields no proof -> candidate settles UNPROVEN


def test_submitted_project_ships_a_lean_toolchain(monkeypatch):
    # Aristotle warns without a lean-toolchain; the submitted project must include one,
    # honoring the env override.
    monkeypatch.setenv("ARISTOTLE_API_KEY", "k")
    monkeypatch.setenv("LEIBNIZ_ARISTOTLE_TOOLCHAIN", "leanprover/lean4:v4.28.0")
    cap: dict = {}
    monkeypatch.setitem(sys.modules, "aristotlelib", _fake_lib(captured=cap))
    AristotleProver(poll_interval_s=0).propose(Role.PROOF_DRAFT, "theorem t : True")
    assert "lean-toolchain" in cap["files"] and "Thm.lean" in cap["files"]
    assert cap["toolchain"].strip() == "leanprover/lean4:v4.28.0"
