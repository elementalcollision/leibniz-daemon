"""Guard the Problem 16 self-ordered sequence census (scripts/prob16_census.py). The screen + refutation
witnesses are CI-safe; the bundled `decide` refutation certificate (standard axioms) is REPL-gated. Tier
audit, verification-amplification; no trust surface touched."""
from __future__ import annotations

import importlib.util
import os
from math import prod
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parent.parent


def _load():
    spec = importlib.util.spec_from_file_location("prob16_census", _ROOT / "scripts" / "prob16_census.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_refuted_and_self_ordered_partition():
    m = _load()
    rows = {r["name"]: r for r in m.census(12)}
    refuted = {n for n, r in rows.items() if not r["self_ordered"]}
    self_ordered = {n for n, r in rows.items() if r["self_ordered"]}
    assert refuted == {"cube", "quartic", "factorial", "fibonacci", "primes"}
    assert {"identity", "arith_3_5", "square", "triangular", "pow2"} <= self_ordered


def test_n_squared_is_self_ordered_correcting_the_corpus_doc():
    # The headline correction: {n²} is self-ordered to N=30 — NOT refutable as the corpus doc loosely claimed.
    m = _load()
    assert m.screen(lambda k: k * k, 30) is None
    # while {n³} IS refutable, witness (3,2):
    assert m.screen(lambda k: k ** 3, 12) == (3, 2)


def test_witnesses_are_arithmetically_correct():
    # Independently re-derive each refutation D_n ∤ P(m,n) from the value prefix.
    m = _load()
    for r in m.census(12):
        if r["self_ordered"]:
            continue
        pre, (mm, n) = r["prefix"], r["witness"]
        dn = prod(pre[n] - pre[k] for k in range(n))
        pmn = prod(pre[mm] - pre[k] for k in range(n))
        assert dn != 0 and pmn % dn != 0, r["name"]


def test_certificate_is_wellformed_and_clean():
    m = _load()
    src, names = m.build_certificate(m.census(12))
    assert len(names) == 5
    assert "primes_not_self_ordered" in src and "fibonacci_not_self_ordered" in src
    assert src.count(":= by decide") == 5
    assert "SO_square" not in src               # n² is NOT refuted (must not appear as a refutation)
    for banned in ["sorry", "native_decide", "admit"]:
        assert banned not in src


@pytest.mark.skipif(not os.environ.get("LEIBNIZ_RUN_LEAN"), reason="real-kernel test; set LEIBNIZ_RUN_LEAN=1")
def test_real_kernel_decides_refutations_clean_axioms():
    m = _load()
    from leibniz.backends.lean_repl import LeanReplBackend, available
    if not available():
        pytest.skip("Lean REPL image unavailable")
    src, names = m.build_certificate(m.census(12))
    run_src = "".join(ln for ln in src.splitlines(keepends=True) if not ln.startswith("import "))
    run_src = run_src + "\n" + "\n".join(f"#print axioms {nm}" for nm in names) + "\n"
    bk = LeanReplBackend(timeout_s=400)
    try:
        r = bk._run(run_src, m.IMPORTS)
    finally:
        bk.close()
    msgs = (r or {}).get("messages", []) or []
    assert not [x for x in msgs if x.get("severity") == "error"]
    axiom_lines = [x.get("data", "") for x in msgs if "axiom" in (x.get("data") or "")]
    assert len(axiom_lines) == 5
    std = {"propext", "Classical.choice", "Quot.sound"}
    for ln in axiom_lines:
        if "does not depend on any axioms" in ln:
            continue
        toks = [t.strip() for t in ln.split("[", 1)[-1].rstrip("]").split(",") if t.strip()]
        assert all(t in std for t in toks), ln
