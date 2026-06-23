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


# --- availability + role guard -----------------------------------------------

def test_unavailable_without_key(monkeypatch):
    monkeypatch.delenv("ARISTOTLE_API_KEY", raising=False)
    assert AristotleProver().available() is False


def test_non_proof_role_is_rejected(monkeypatch):
    monkeypatch.setenv("ARISTOTLE_API_KEY", "k")
    monkeypatch.setitem(sys.modules, "aristotlelib", _fake_lib())
    try:
        AristotleProver(poll_interval_s=0).propose(Role.CONJECTURE, "x")
        assert False, "expected ProviderUnavailable"
    except ProviderUnavailable:
        pass


# --- submit -> poll -> get_files flow (fake aristotlelib) --------------------

def _fake_lib(status="COMPLETE", filled="theorem t : True := by simp"):
    m = types.ModuleType("aristotlelib")
    m.set_api_key = lambda k: k

    class _Status:
        def __init__(self, name):
            self.name = name

    class _Task:
        def __init__(self):
            self.status = _Status(status)

        def refresh(self):
            pass

        def cancel(self):
            pass

    class _Project:
        @classmethod
        def create_from_directory(cls, prompt, d, **kw):
            return cls()

        def get_tasks(self, limit=1):
            return ([_Task()], None)

        def ask(self, prompt, **kw):
            return _Task()

        def get_files(self, dest):
            (Path(dest) / "Thm.lean").write_text(filled + "\n")
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
