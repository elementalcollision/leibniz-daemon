"""Guard the necklace-process tie-off (scripts/beyond_markov_necklace_lean.py) — T8-c made zero-audit by
defining the necklace as an OOM in Lean and deriving its positive-realization gap. CI-safe: the Python
cross-check (the Lean OOM reproduces the necklace chain) runs everywhere; the Lean/Mathlib REPL leg is gated
and CI-skips. No trust surface touched."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parent.parent


def _load():
    spec = importlib.util.spec_from_file_location("beyond_markov_necklace_lean",
                                                  _ROOT / "scripts" / "beyond_markov_necklace_lean.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _repl_available() -> bool:
    try:
        from leibniz.backends.lean_repl import available
        return bool(available())
    except Exception:
        return False


def test_lean_oom_reproduces_the_necklace_chain():
    m = _load()
    a = m.audit()
    assert a["block_8x_is_M4"] is True           # 8·(Lean nBlock) = the T8-c witness matrix
    assert a["fooling_on_block"] is True         # the block carries the size-4 fooling set
    assert a["hankel_rank_stable_3"] is True      # ordinary Hankel rank 3 (so nonneg-rank 4 > rank 3)
    assert a["ok"] is True


def test_controls_are_real_mutations():
    m = _load()
    ctl = m.controls(m.LEAN_SRC)
    assert set(ctl) == {"corrupt_operator_zero", "overclaim_states"}
    for src in ctl.values():
        assert src != m.LEAN_SRC


def test_source_contains_the_key_theorems():
    m = _load()
    for name in ("nInit", "nOp", "nFin", "necklace_block_no_rank3_nonneg_factor",
                 "necklace_positive_realization_needs_4", "necklace_is_positive_realization"):
        assert name in m.LEAN_SRC


@pytest.mark.skipif(not _repl_available(), reason="Lean REPL image unavailable; kernel leg is operator-local")
def test_kernel_derives_the_gap_from_the_necklace_definition():
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

    assert ok(m.LEAN_SRC) is True                # the whole zero-audit necklace chain, 0 errors/sorries
    for src in m.controls(m.LEAN_SRC).values():
        assert ok(src) is False                  # corrupted operator zero / overclaimed states must fail
