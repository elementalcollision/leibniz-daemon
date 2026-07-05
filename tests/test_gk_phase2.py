"""Guard Guo–Krattenthaler Phase 2 (scripts/verify_gk_phase2.py): the three all-n divisibilities lifted to a
genuine theorem for the PRIME-MODULUS case (infinitely many n) via an elementary Kummer units-carry argument.
Exact-integer cross-checks are CI-safe; the axiom-clean kernel leg is REPL-gated. Tier audit; no trust surface."""
from __future__ import annotations

import importlib.util
import os
from math import comb
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parent.parent


def _load():
    spec = importlib.util.spec_from_file_location("gk2", _ROOT / "scripts" / "verify_gk_phase2.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_prime_modulus_divisibilities_hold():
    # For every n with the modulus prime, the divisibility holds — the theorem's arithmetic claim, re-derived.
    m = _load()
    for top, bot, dz in m.CASES:
        for n in range(1, 120):
            if m._is_prime(dz * n - 1):
                assert comb(top * n, bot * n) % (dz * n - 1) == 0, (top, bot, dz, n)


def test_cross_check_all_ok():
    m = _load()
    cc = m.cross_check(nmax=200)
    assert cc["all_ok"] is True
    assert len(cc["rows"]) == 3
    for r in cc["rows"]:
        assert r["all_divisible"] is True
        assert r["prime_modulus_n_count"] >= 50   # infinitely many n; a healthy finite sample


def test_units_carry_is_the_real_mechanism():
    # The proof's premise: with the modulus prime, the base-p units digits of k and (m−k) sum to ≥ p (a carry).
    # (6n−1): 3n and 3n+1 → 6n+1 ≥ 6n−1 ✓;  4n and 2n+1 → 6n+1 ≥ 6n−1 ✓;  (66n−1): 22n+1 and 44n+3 → 66n+4 ✓.
    for n in range(1, 60):
        p = 6 * n - 1
        assert (3 * n) % p + (12 * n - 3 * n) % p >= p
        assert (4 * n) % p + (12 * n - 4 * n) % p >= p
        q = 66 * n - 1
        assert (88 * n) % q + (330 * n - 88 * n) % q >= q


def test_artifact_wellformed_and_no_cheating():
    src = (_ROOT / "docs" / "crt" / "guo_krattenthaler_phase2.lean").read_text(encoding="utf-8")
    for name in ("prime_dvd_choose_of_units_carry", "gk_12_3_prime", "gk_12_4_prime", "gk_330_88_prime"):
        assert f"theorem {name}" in src
    assert "Nat.factorization_choose" in src        # the Kummer engine
    assert "dvd_iff_one_le_factorization" in src
    for banned in ("sorry", "native_decide", "admit"):
        assert banned not in src


@pytest.mark.skipif(not os.environ.get("LEIBNIZ_RUN_LEAN"), reason="real-kernel test; set LEIBNIZ_RUN_LEAN=1")
def test_real_kernel_verifies_clean_axioms():
    m = _load()
    from leibniz.backends.lean_repl import LeanReplBackend, available
    if not available():
        pytest.skip("Lean REPL image unavailable")
    src = m.ARTIFACT.read_text(encoding="utf-8")
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
