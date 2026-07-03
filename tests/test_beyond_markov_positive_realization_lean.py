"""Guard the full in-Lean POSITIVE-REALIZATION identification (T8-c;
scripts/beyond_markov_positive_realization_lean.py). CI-safe: the Python cross-check (NM is the necklace
co-occurrence witness — fooling set, rank 3, 8·H2=NM) runs everywhere; the Lean/Mathlib REPL leg is gated and
CI-skips. No trust surface touched."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parent.parent


def _load():
    spec = importlib.util.spec_from_file_location("beyond_markov_positive_realization_lean",
                                                  _ROOT / "scripts" / "beyond_markov_positive_realization_lean.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _repl_available() -> bool:
    try:
        from leibniz.backends.lean_repl import available
        return bool(available())
    except Exception:
        return False


def test_NM_is_the_necklace_witness():
    m = _load()
    a = m.audit()
    assert a["NM_is_M4"] is True                    # the Lean NM equals the T8-c witness matrix
    assert a["fooling_size4_valid"] is True         # the size-4 fooling set is valid
    assert a["rank"] == 3                           # ordinary rank 3 (so nonneg-rank 4 > rank 3: the gap)
    assert a["process_8H2_is_NM"] is True           # 8·H2 = NM: NM is the necklace's co-occurrence matrix
    assert a["ok"] is True


def test_controls_are_real_mutations():
    m = _load()
    ctl = m.controls(m.LEAN_SRC)
    assert set(ctl) == {"overclaim_nonneg_rank", "corrupt_fooling_zero"}
    for src in ctl.values():
        assert src != m.LEAN_SRC


def test_source_contains_the_key_theorems():
    m = _load()
    for name in ("fooling_le_of_nonneg_factor", "necklace_no_rank3_nonneg_factor",
                 "hankel_nonneg_factor", "positive_realization_of_NM_needs_4_states"):
        assert name in m.LEAN_SRC


@pytest.mark.skipif(not _repl_available(), reason="Lean REPL image unavailable; kernel leg is operator-local")
def test_kernel_proves_no_3state_positive_realization():
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

    assert ok(m.LEAN_SRC) is True                   # the whole positive-realization chain, 0 errors/sorries
    for src in m.controls(m.LEAN_SRC).values():
        assert ok(src) is False                     # overclaimed bound / corrupted fooling zero must fail
