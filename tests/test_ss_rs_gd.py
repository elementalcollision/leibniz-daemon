"""Guard the SS-RS-GD refutation artifact (scripts/ss_rs_gd_lean.py). CI-safe checks are structural
(the Lean states the refutation core and the identity (1.7) as printed, plus an exact-rational re-check of
(1.7) from an independent transcription of the paper); the real kernel verification (all headline theorems
elaborate with only the standard axioms) is a REPL-gated test. No trust surface touched."""
from __future__ import annotations

import importlib.util
import os
from fractions import Fraction
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parent.parent


def _load():
    spec = importlib.util.spec_from_file_location("ss_rs_gd_lean", _ROOT / "scripts" / "ss_rs_gd_lean.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_states_the_refutation_core():
    m = _load()
    # the gap identity (1.8), the violation, and a concrete witness must be present
    for name in ["gap_identity", "ss_exceeds_rs", "violation_at_half"]:
        assert f"theorem {name}" in m.SRC


def test_states_identity_1_7_as_printed_and_the_vindication():
    m = _load()
    # (1.7) holds as printed; the former "erratum" was our transcription error (square on mu_RS dropped)
    assert "theorem dominance_mu_1_7" in m.SRC
    assert "(q^4 + 4*q^3 - 42*q^2 + 4*q + 1)^2/16384" in m.SRC   # mu_RS carries the paper's square
    assert "paper_eq_1_7_false_at_half" not in m.SRC             # the retracted erratum stays retracted
    # the mis-transcription survives only as a labelled negative control
    assert "theorem mistranscribed_1_7_false_at_half" in m.SRC
    assert "NEGATIVE CONTROL" in m.SRC
    # the SOS the scout doubted, and the inequality (1.7) establishes
    assert "sos_cofactor" in m.SRC
    assert "lamRS_ge_muRS_at_half" in m.SRC


def _poly_1_7(q: Fraction, squared: bool = True):
    """Independent transcription of Lemma 1.5 from the paper: returns (lam_RS - mu_RS, RHS of (1.7))."""
    lam = ((q**6 - 6*q**5 + 15*q**4 + 12*q**3 + 15*q**2 - 6*q + 1) / 32) ** 2
    quartic = q**4 + 4*q**3 - 42*q**2 + 4*q + 1
    mu = (q + 1)**4 * (quartic**2 if squared else quartic) / 16384
    rhs = (1 - q)**4 * (5*q**2 + 2*q + 5) * (3*q**6 - 30*q**5 + 93*q**4 + 124*q**3 + 93*q**2 - 30*q + 3) / 16384
    return lam - mu, rhs


def test_identity_1_7_holds_exactly_and_the_mistranscription_does_not():
    # Both sides are degree-12 polynomials, so agreement at 13 distinct points proves the identity.
    points = [Fraction(k, 7) for k in range(-6, 7)]
    assert len(set(points)) == 13
    for q in points:
        lhs, rhs = _poly_1_7(q)
        assert lhs == rhs, f"(1.7) fails at q={q}"
    lhs, rhs = _poly_1_7(Fraction(1, 2), squared=False)
    assert lhs != rhs  # the negative control: our former transcription


def test_no_stray_sorry():
    m = _load()
    for banned in ["sorry", "admit", "native_decide"]:
        assert banned not in m.SRC, f"artifact must not contain {banned!r}"


def test_headline_list_covers_refutation_and_identity_1_7():
    m = _load()
    assert "SSRSGD.ss_exceeds_rs" in m.HEADLINE
    assert "SSRSGD.dominance_mu_1_7" in m.HEADLINE
    assert "SSRSGD.mistranscribed_1_7_false_at_half" in m.HEADLINE
    assert "SSRSGD.paper_eq_1_7_false_at_half" not in m.HEADLINE


@pytest.mark.skipif(not os.environ.get("LEIBNIZ_RUN_LEAN"), reason="real-kernel test; set LEIBNIZ_RUN_LEAN=1")
def test_real_kernel_verifies_all_headline_theorems():
    m = _load()
    from leibniz.backends.lean_repl import LeanReplBackend, available
    if not available():
        pytest.skip("Lean REPL image unavailable")
    bk = LeanReplBackend(timeout_s=400)
    try:
        r = bk._run(m.full_source(), m.IMPORTS)
    finally:
        bk.close()
    msgs = (r or {}).get("messages", []) or []
    errs = [x for x in msgs if x.get("severity") == "error"]
    assert not errs, errs[:2]
    std = {"propext", "Classical.choice", "Quot.sound"}
    for name in m.HEADLINE:
        line = next((x.get("data", "") for x in msgs if name in (x.get("data") or "")
                     and "axioms" in (x.get("data") or "")), None)
        assert line is not None, f"no axiom line for {name}"
        am = m._AX.search(line)
        assert am is not None
        got = {a.strip() for a in am.group(1).split(",") if a.strip()}
        assert got <= std and got, f"{name}: non-standard axioms {got}"
