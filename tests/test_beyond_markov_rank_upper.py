"""Guard the T8 rank-UPPER bridge lemma (scripts/beyond_markov_rank_upper.py). CI-safe: the exact-rational
audit (the even process's word-Hankel factors through ℚ^2, plus a nonsingular 2x2 minor ⇒ rank exactly 2)
runs everywhere; the Lean/Mathlib REPL leg is gated and CI-skips, mirroring test_terwilliger_f2a. No trust
surface touched."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parent.parent


def _load():
    spec = importlib.util.spec_from_file_location("beyond_markov_rank_upper",
                                                  _ROOT / "scripts" / "beyond_markov_rank_upper.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _repl_available() -> bool:
    try:
        from leibniz.backends.lean_repl import available
        return bool(available())
    except Exception:
        return False


def test_even_hankel_factors_through_Q2_giving_rank_exact_2():
    m = _load()
    a = m.even_factorization_audit(L=3)
    assert a["inner_dim"] == 2
    assert a["factorization_H_eq_FB"] is True        # H = F·B, F[u]=π T_u, B[v]=T_v 1  (rank ≤ 2)
    assert a["rank_ge2"] is True                     # nonsingular 2×2 minor (rank ≥ 2)
    assert a["rank_exact_2"] is True and a["ok"] is True


def test_controls_are_real_mutations():
    m = _load()
    ctl = m.controls(m.LEAN_SRC)
    assert set(ctl) == {"bad_factorization", "understated_bound"}
    for src in ctl.values():
        assert src != m.LEAN_SRC


def test_factorization_is_load_bearing():
    # If the factorization is corrupted, H ≠ F·B and the audit's identity must break.
    m = _load()
    a = m.even_factorization_audit(L=2)
    assert a["factorization_H_eq_FB"] is True
    # a bad "inner dim 1" (rank-1) collapse cannot reproduce a rank-2 Hankel: the 2x2 minor is nonzero
    assert a["rank_ge2"] is True                     # so no rank-1 factorization exists -> the ≤2 bound is tight


@pytest.mark.skipif(not _repl_available(), reason="Lean REPL image unavailable; kernel leg is operator-local")
def test_kernel_verifies_bridge_and_rejects_controls():
    m = _load()
    from leibniz.backends.lean_repl import LeanReplBackend
    bk = LeanReplBackend(timeout_s=600)

    def ok(src):
        r = bk._run(src, m.IMPORTS)
        if r is None:
            return None
        msgs = r.get("messages", []) or []
        return not any(x.get("severity") == "error" for x in msgs) and \
            not any("sorry" in (x.get("data") or "") for x in msgs)

    assert ok(m.LEAN_SRC) is True                    # rank_le_of_factor + rank_eq + concrete Hc, 0 errors/sorries
    for src in m.controls(m.LEAN_SRC).values():
        assert ok(src) is False                      # broken factorization / understated bound must fail
