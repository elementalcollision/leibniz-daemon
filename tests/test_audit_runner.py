"""Regression pack for the audit-runner (T5) — makes the MCR formal-verification audit a re-runnable,
CI-guarded instrument, not a one-off. CI-safe: the spec's verdicts + the pure-numeric artifacts (P1, P5) run
everywhere; the Z3 artifacts (P2/P3/P6) are z3-gated; the Lean leg (P4) is docker/REPL-gated with a corrupted
control. No trust surface touched."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parent.parent
_HAS_Z3 = importlib.util.find_spec("z3") is not None


def _load():
    spec = importlib.util.spec_from_file_location("audit_runner", _ROOT / "scripts" / "audit_runner.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _lean_available() -> bool:
    try:
        from leibniz.backends.lean_repl import available
        return bool(available())
    except Exception:
        return False


def test_spec_locks_the_eight_verdicts():
    m = _load()
    spec = m.mcr_audit_spec()
    assert [f["id"] for f in spec] == ["P1", "P2", "P3", "P4", "P5", "P6", "P7", "P8"]
    v = {f["id"]: f["verdict"] for f in spec}
    assert v["P1"] == "VACUOUS" and v["P4"] == "REFUTED"
    assert v["P7"] == "NOT-PROVEN" and v["P8"] == "PROVEN"   # the honest downgrade + the steelman
    assert {f["id"] for f in spec if f["kind"] == "lean"} == {"P4"}


def test_numeric_artifacts_reproduce_ci_safe():
    m = _load()
    report = m.run_audit(m.mcr_audit_spec(), run_z3=False, lean_backend=None)
    assert report["P1"]["artifact_ok"] is True          # parametricity square (real & no-op stub) — VACUOUS
    assert report["P5"]["artifact_ok"] is True          # E > log2 N — ILL-POSED
    assert report["P2"]["artifact_ok"] is None and report["P4"]["artifact_ok"] is None   # not run without z3/lean
    assert report["P7"]["artifact_ok"] is None          # reasoning verdict, no automated artifact


@pytest.mark.skipif(not _HAS_Z3, reason="z3 is operator-local; MCR audit Z3 artifacts skipped in CI")
def test_z3_artifacts_reproduce():
    m = _load()
    report = m.run_audit(m.mcr_audit_spec(), run_z3=True, lean_backend=None)
    for fid in ("P2", "P3", "P6"):
        assert report[fid]["artifact_ok"] is True       # the SMT verdicts survive re-running


@pytest.mark.skipif(not _lean_available(), reason="Lean REPL image unavailable; P4 kernel leg is operator-local")
def test_p4_lean_leg_kernel_attests_and_rejects_corruption():
    m = _load()
    from leibniz.backends.lean_repl import LeanReplBackend
    bk = LeanReplBackend(timeout_s=400)
    # the shipped P4 proof kernel-checks clean (0 errors / 0 sorries)
    assert m.lean_leg_ok("docs/audits/mcr_p4_not_derivable.lean", ("Mathlib.Tactic",), bk) is True
    # a corrupted P4 (its core step replaced by `sorry`) must NOT pass
    raw = (_ROOT / "docs" / "audits" / "mcr_p4_not_derivable.lean").read_text()
    body = "\n".join(ln for ln in raw.splitlines() if not ln.strip().startswith("import "))
    corrupted = body.replace("exact absurd hstrict (lt_irrefl _)", "sorry")
    assert corrupted != body
    r = bk._run(corrupted, ("Mathlib.Tactic",))
    msgs = r.get("messages", []) or [] if r else []
    clean = r is not None and not any(x.get("severity") == "error" for x in msgs) \
        and not any("sorry" in (x.get("data") or "") for x in msgs)
    assert clean is False
