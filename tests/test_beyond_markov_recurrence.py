"""Guard T8-b — infinite Markov order via the recurrence + induction bridge lemma
(scripts/beyond_markov_recurrence.py). CI-safe: the exact-rational audit legs (the abstract recurrence
sequences ARE the even process's conditional gap and the BM-4 excess loss) run everywhere; the
Lean/Mathlib REPL kernel leg is gated and CI-skips, mirroring test_terwilliger_f2a. No trust surface touched."""
from __future__ import annotations

import importlib.util
from fractions import Fraction as Fr
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parent.parent


def _load():
    spec = importlib.util.spec_from_file_location("beyond_markov_recurrence",
                                                  _ROOT / "scripts" / "beyond_markov_recurrence.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _repl_available() -> bool:
    try:
        from leibniz.backends.lean_repl import available
        return bool(available())
    except Exception:
        return False


def test_audit_sequences_match_the_processes():
    m = _load()
    a = m.audit(N=14)
    assert a["even_gap_matches_process"] is True        # evenGap = P(1|0·1^k) − P(1|1·1^k), exactly
    assert a["even_recurrence_q1"] is True              # Δ_{k+2} = 1·Δ_k
    assert a["g_recurrence_qhalf"] is True              # g_{k+2} = g_k/2
    assert a["even_bases"] == ["-1/4", "1/3"] and a["g_bases_ok"] is True
    assert a["ok"] is True


def test_even_process_gap_is_period_2_and_nonzero():
    m = _load()
    for k in range(12):
        g = m.even_gap(m._load_cert(), k)
        assert g == (Fr(-1, 4) if k % 2 == 0 else Fr(1, 3))
        assert g != 0                                   # the order-k conditional gap never vanishes


def test_two_step_recurrence_stays_nonzero_numerically():
    # The bridge lemma's claim, checked over the rationals: Δ_{k+2}=q·Δ_k, q≠0, bases≠0 ⇒ Δ_k≠0 ∀k.
    for q, d0, d1 in ((Fr(1), Fr(-1, 4), Fr(1, 3)), (Fr(1, 2), Fr(1, 9), Fr(1, 12)), (Fr(-3), Fr(2), Fr(5))):
        d = [d0, d1]
        for k in range(2, 40):
            d.append(q * d[k - 2])
        assert all(x != 0 for x in d)                   # matches evenGap/gSeq/general geometric


def test_controls_are_real_mutations():
    m = _load()
    ctl = m.controls(m.LEAN_SRC)
    assert set(ctl) == {"even_base_zero", "g_base_zero", "q_is_zero"}
    for src in ctl.values():
        assert src != m.LEAN_SRC                        # each control genuinely changes the source


@pytest.mark.skipif(not _repl_available(), reason="Lean REPL image unavailable; kernel leg is operator-local")
def test_kernel_verifies_and_rejects_controls():
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

    assert ok(m.LEAN_SRC) is True                       # general lemma + both instantiations, 0 errors/sorries
    for src in m.controls(m.LEAN_SRC).values():
        assert ok(src) is False                         # zeroed base / zero ratio must fail
