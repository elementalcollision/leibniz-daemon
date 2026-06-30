"""Structural-guard red-team corpus (validation plan Tier 0, R0.5).

`construction_intake.theorem_structural_guard` is a DENYLIST and its own docstring warns it is NOT
trust-path ready: it admits declaration/metaprogram forms a sound ALLOWLIST would reject. This test turns
that porosity into an ASSERTING regression so:
  (1) the known bypasses are documented in code (no silent assumption the guard is safe), and
  (2) if someone replaces the denylist with the allowlist the §10 design requires, the ADMITS_TODAY cases
      flip to rejected and THIS test fails loudly — forcing a conscious update rather than silent drift,
  (3) any accidental wiring of this guard into a trust path is caught by the explicit "not trust-ready"
      assertions below.

It also pins `canonical_claim` as the tri-edge binding source: size is ALWAYS len(witness), so a laundered
statement claiming a smaller bound cannot be derived from it.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parent.parent


def _load(mod_name: str, rel: str):
    spec = importlib.util.spec_from_file_location(mod_name, _ROOT / rel)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


ci = _load("construction_intake", "scripts/construction_intake.py")


# ---- the guard does its denylist job on the clearly-forbidden forms -------------------------------------
REJECTED = [
    ("def smuggle (x:Nat) := x\ntheorem t : True := by decide", "def"),
    ("axiom bad : False\ntheorem t : True := by decide", "axiom"),
    ("theorem t : validCovering [] 1 1 1 0 = true := by native_decide", "native_decide"),
    ("@[simp] theorem t : True := by decide", "@["),
    ("theorem t : True := by sorry", "sorry"),
    ("import Mathlib\ntheorem t : True := by decide", "import"),
    ("macro \"x\" : term => `(1)\ntheorem t : True := by decide", "macro"),
    ("set_option maxHeartbeats 0 in\ntheorem t : True := by decide", "set_option"),
    ("theorem a : True := by decide\ntheorem b : True := by decide", "two theorems"),
    # ACCIDENTAL DEFENSE: inline let/have WITH an assignment inside the type adds a second ':=', which the
    # single-':=' rule rejects. This is fragile (a shadow without ':=' would slip), but documents that
    # these specific shadowing shapes are caught today.
    ("theorem t : (let validCovering := fun _ => true; validCovering 0) = true := by decide",
     "let-shadow in type (two :=)"),
    ("theorem t : (have validCovering := true; validCovering) = true := by decide",
     "have-shadow in type (two :=)"),
]


def test_guard_rejects_forbidden_forms():
    for src, why in REJECTED:
        ok, reason = ci.theorem_structural_guard(src)
        assert ok is False, f"guard wrongly ADMITTED a {why!r} form: {src!r}"


# ---- KNOWN GAPS: forms the denylist ADMITS that a sound allowlist MUST reject --------------------------
# Each is asserted ADMITS-TODAY so the porosity is explicit. When the allowlist replaces the denylist these
# flip to rejected and this test must be updated deliberately (that is the point).
ADMITS_TODAY = [
    # statement laundering: a true-but-irrelevant theorem (not about validCovering at all)
    ("theorem t : 1 = 1 := by decide", "irrelevant statement (laundering)"),
    # arbitrary proof term: the guard never checks the proof is `by decide`
    ("theorem t : True := by exact trivial", "non-decide proof"),
    # elaboration-time side effect (run_tac/run_cmd/elab are not in the denylist)
    ("theorem t : True := by run_tac (pure ())", "elaboration tactic admitted"),
    # a structurally-valid but FALSE bound (1 block cannot cover C(9,3,2)); admitted by the guard, the
    # KERNEL is the backstop that rejects it at `decide` time — the guard alone cannot catch a false bound
    ("theorem t : validCovering [[0,1,2]] 9 3 2 1 = true := by decide", "false bound (kernel-caught)"),
]


def test_known_denylist_gaps_are_documented_not_silent():
    for src, gap in ADMITS_TODAY:
        ok, _reason = ci.theorem_structural_guard(src)
        assert ok is True, (
            f"KNOWN-GAP CLOSED: the denylist now rejects {gap!r}. If the allowlist landed, update this "
            f"corpus to assert rejection. Source: {src!r}")


def test_guard_is_marked_not_trust_ready():
    # the WARNING must remain in the docstring until an allowlist replaces the denylist
    assert "NOT TRUST-PATH READY" in (ci.theorem_structural_guard.__doc__ or "")


# ---- canonical_claim is the tri-edge binding source: size is always len(witness) -----------------------
def test_canonical_claim_recomputes_size_blocking_laundering():
    witness = {"domain": "covering", "v": 9, "k": 3, "t": 2,
               "blocks": [[0, 1, 2]] * 12, "claimed_size": 11}   # a lie: claims 11, supplies 12
    claim = ci.canonical_claim(witness)
    assert claim["size"] == 12                      # recomputed from the witness, not the claimed field
    assert claim["statement"] == "C(9,3,2) <= 12"   # the bound binds to the real size
    assert claim["cell"] == "C(9,3,2)"


def test_canonical_claim_cwc_and_unknown_domain():
    cwc = ci.canonical_claim({"domain": "cwc", "n": 13, "d": 6, "w": 5, "code": [[0]] * 18})
    assert cwc["size"] == 18 and cwc["statement"] == "A(13,6,5) >= 18"
    with pytest.raises(ValueError):
        ci.canonical_claim({"domain": "nonsense"})
