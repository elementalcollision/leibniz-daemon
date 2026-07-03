"""Guard the full in-Lean process identification (scripts/beyond_markov_process_lean.py). CI-safe: the Python
cross-check (the Lean-encoded even process matches the actual even process) runs everywhere; the Lean/Mathlib
REPL leg is gated and CI-skips, mirroring test_terwilliger_f2a. No trust surface touched."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parent.parent


def _load():
    spec = importlib.util.spec_from_file_location("beyond_markov_process_lean",
                                                  _ROOT / "scripts" / "beyond_markov_process_lean.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _repl_available() -> bool:
    try:
        from leibniz.backends.lean_repl import available
        return bool(available())
    except Exception:
        return False


def test_lean_definition_matches_the_actual_even_process():
    m = _load()
    a = m.audit()
    assert a["P00_is_1_6"] is True            # P(00)=1/6: the Lean eInit/eOp/eFin encode the even process
    assert a["block_det_is_1_18"] is True     # the 2×2 block det = 1/18 (what eB_det asserts in-kernel)
    assert a["ok"] is True


def test_controls_are_real_mutations():
    m = _load()
    ctl = m.controls(m.LEAN_SRC)
    assert set(ctl) == {"wrong_determinant", "understated_dimension"}
    for src in ctl.values():
        assert src != m.LEAN_SRC


def test_source_contains_the_key_theorems():
    m = _load()
    for name in ("hankel_block_rank_le", "even_hankel_rank_le", "eB_det", "eB_rank_eq_two"):
        assert name in m.LEAN_SRC        # the identification theorems are present


@pytest.mark.skipif(not _repl_available(), reason="Lean REPL image unavailable; kernel leg is operator-local")
def test_kernel_derives_rank_from_the_process_definition():
    m = _load()
    from leibniz.backends.lean_repl import LeanReplBackend
    bk = LeanReplBackend(timeout_s=900)

    def ok(src):
        r = bk._run(src, m.IMPORTS)
        if r is None:
            return None
        msgs = r.get("messages", []) or []
        return not any(x.get("severity") == "error" for x in msgs) and \
            not any("sorry" in (x.get("data") or "") for x in msgs)

    assert ok(m.LEAN_SRC) is True                    # the OOM dimension bound + even-process rank = 2, sorry-free
    for src in m.controls(m.LEAN_SRC).values():
        assert ok(src) is False                      # wrong determinant / understated dimension must fail
