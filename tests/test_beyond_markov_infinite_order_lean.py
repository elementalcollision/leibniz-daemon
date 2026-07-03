"""Guard the full in-Lean INFINITE-ORDER identification (scripts/beyond_markov_infinite_order_lean.py). CI-safe:
the Python cross-check (the even process's actual cross-multiplied gap matches the Lean values + recurrence)
runs everywhere; the Lean/Mathlib REPL leg is gated and CI-skips. No trust surface touched."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parent.parent


def _load():
    spec = importlib.util.spec_from_file_location("beyond_markov_infinite_order_lean",
                                                  _ROOT / "scripts" / "beyond_markov_infinite_order_lean.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _repl_available() -> bool:
    try:
        from leibniz.backends.lean_repl import available
        return bool(available())
    except Exception:
        return False


def test_gap_matches_the_even_process_and_recurs():
    m = _load()
    a = m.audit()
    assert a["D0_is"] is True and a["D1_is"] is True   # D_0=-1/18, D_1=1/36 (the in-kernel base cases)
    assert a["recurrence_quarter"] is True             # D_{k+2} = 1/4 D_k
    assert a["nonzero_0_to_19"] is True                # the gap never vanishes -> infinite order
    assert a["ok"] is True


def test_controls_are_real_mutations():
    m = _load()
    ctl = m.controls(m.LEAN_SRC)
    assert set(ctl) == {"wrong_base_case", "wrong_recurrence_ratio"}
    for src in ctl.values():
        assert src != m.LEAN_SRC


def test_source_contains_the_key_theorems():
    m = _load()
    for name in ("eOp1_sq", "eP_append_11", "Dgap_rec", "even_infinite_order"):
        assert name in m.LEAN_SRC


@pytest.mark.skipif(not _repl_available(), reason="Lean REPL image unavailable; kernel leg is operator-local")
def test_kernel_derives_infinite_order_from_the_operators():
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

    assert ok(m.LEAN_SRC) is True                       # even_infinite_order + all lemmas, 0 errors/sorries
    for src in m.controls(m.LEAN_SRC).values():
        assert ok(src) is False                         # wrong base case / wrong recurrence ratio must fail
