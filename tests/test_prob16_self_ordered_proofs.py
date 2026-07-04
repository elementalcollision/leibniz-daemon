"""Guard the Problem 16 positive proofs (docs/crt/prob16_self_ordered_proofs.lean): arithmetic sequences are
self-ordered. The source is structurally checked in CI (predicate + theorems present, no sorry / native_decide);
the real kernel elaboration + axiom footprint is REPL-gated. Tier audit; no trust surface touched."""
from __future__ import annotations

import importlib.util
import os
from math import prod
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parent.parent
_ARTIFACT = _ROOT / "docs" / "crt" / "prob16_self_ordered_proofs.lean"


def _load():
    spec = importlib.util.spec_from_file_location(
        "prob16_proofs", _ROOT / "scripts" / "prob16_self_ordered_proofs.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_artifact_states_the_predicate_and_theorems_no_cheating():
    src = _ARTIFACT.read_text(encoding="utf-8")
    assert "def SelfOrdered" in src
    for thm in ["identity_selfOrdered", "arith_selfOrdered", "even_selfOrdered", "arith_3_5_selfOrdered"]:
        assert f"theorem {thm}" in src
    for banned in ["sorry", "native_decide", "admit", ":= by sorry"]:
        assert banned not in src


def test_the_arithmetic_claim_holds_numerically():
    # Sanity the mathematical claim the theorem generalizes: for arithmetic α+βn, D_n | P(m,n).
    for alpha, beta in [(0, 1), (0, 2), (3, 5), (-1, 3)]:
        a = lambda k: alpha + beta * k  # noqa: E731
        for n in range(1, 8):
            dn = prod(a(n) - a(k) for k in range(n))
            for m in range(10):
                assert dn == 0 or prod(a(m) - a(k) for k in range(n)) % dn == 0, (alpha, beta, m, n)


@pytest.mark.skipif(not os.environ.get("LEIBNIZ_RUN_LEAN"), reason="real-kernel test; set LEIBNIZ_RUN_LEAN=1")
def test_real_kernel_elaborates_all_theorems_clean_axioms():
    m = _load()
    from leibniz.backends.lean_repl import LeanReplBackend, available
    if not available():
        pytest.skip("Lean REPL image unavailable")
    src = _ARTIFACT.read_text(encoding="utf-8")
    run_src = "".join(ln for ln in src.splitlines(keepends=True) if not ln.startswith("import "))
    run_src += "\n" + "\n".join(f"#print axioms {t}" for t in m.THEOREMS) + "\n"
    bk = LeanReplBackend(timeout_s=300)
    try:
        r = bk._run(run_src, m.IMPORTS)
    finally:
        bk.close()
    msgs = (r or {}).get("messages", []) or []
    assert not [x for x in msgs if x.get("severity") == "error"]
    axiom_lines = [x.get("data", "") for x in msgs if "axiom" in (x.get("data") or "")]
    assert len(axiom_lines) == len(m.THEOREMS)
    std = {"propext", "Classical.choice", "Quot.sound"}
    for ln in axiom_lines:
        if "does not depend on any axioms" in ln:
            continue
        toks = [t.strip() for t in ln.split("[", 1)[-1].rstrip("]").split(",") if t.strip()]
        assert all(t in std for t in toks), ln
