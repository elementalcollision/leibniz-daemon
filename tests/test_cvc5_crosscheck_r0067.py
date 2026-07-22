"""ADR 0067 — cvc5 cross-solver attestation for the Z3 probe layer.

Needs BOTH extras (z3 + cvc5); skips cleanly where either is absent (the CI invariants job installs
core only — the ADR 0066 lesson). The disagreement/degradation path is exercised with a FAKE cvc5
verdict so it does not depend on ever finding a real solver divergence.
"""
from __future__ import annotations

import pytest

from leibniz.backends import smt_cvc5
from leibniz.backends.smt_z3 import CROSS_STATS, Z3Backend, available as z3_available

pytestmark = pytest.mark.skipif(
    not (z3_available() and smt_cvc5.available()),
    reason="z3-solver (verify extra) + cvc5 (cvc5 extra) both required",
)


@pytest.fixture()
def crosscheck_on(monkeypatch):
    monkeypatch.setenv("LEIBNIZ_CVC5_CROSSCHECK", "1")
    before = dict(CROSS_STATS)
    yield
    for k in CROSS_STATS:                                 # restore counters for test isolation
        CROSS_STATS[k] = before[k]


def _delta(before):
    return {k: CROSS_STATS[k] - before[k] for k in CROSS_STATS}


def test_gated_off_by_default(monkeypatch):
    monkeypatch.delenv("LEIBNIZ_CVC5_CROSSCHECK", raising=False)
    before = dict(CROSS_STATS)
    assert Z3Backend().find_counterexample("n % 2 == 0 and n % 2 == 1", 20) is None
    assert _delta(before)["checked"] == 0                 # no cross-check ran


def test_unsat_verdicts_cross_agree_across_encoding_shapes(crosscheck_on):
    be = Z3Backend()
    before = dict(CROSS_STATS)
    assert be.find_counterexample("n % 2 == 0 and n % 2 == 1", 20) is None          # plain modular
    assert be.decide_unsat(["2**n % 7 == 3"], 20) is True                            # ADR 0035 order-chain
    assert be.decide_unsat(["gcd(n, 12) == 5"], 24) is True                          # ADR 0066 gcd table
    assert be.find_counterexample("min(a, b) > a", 10) is None                       # min/max
    d = _delta(before)
    assert d["checked"] == 4 and d["agree"] == 4 and d["disagree"] == 0


def test_sat_verdicts_skip_the_cross_check(crosscheck_on):
    # a sat model is self-validating evidence; only unsat is single-solver trust
    before = dict(CROSS_STATS)
    assert Z3Backend().find_counterexample("factorial(n) == 24", 20) == {"n": 4}
    assert _delta(before)["checked"] == 0


def test_disagreement_degrades_to_inconclusive_and_warns(crosscheck_on, monkeypatch, capsys):
    monkeypatch.setattr(smt_cvc5.Cvc5CrossCheck, "redecide", lambda self, smt2: "sat")
    before = dict(CROSS_STATS)
    # kill-only: a conclusive True (unsat) becomes None (inconclusive) — never a wrong answer
    assert Z3Backend().decide_unsat(["n % 2 == 0 and n % 2 == 1"], 20) is None
    d = _delta(before)
    assert d["disagree"] == 1 and d["agree"] == 0
    assert "CROSS-SOLVER DISAGREEMENT" in capsys.readouterr().out


def test_cvc5_unknown_keeps_the_z3_verdict(crosscheck_on, monkeypatch):
    monkeypatch.setattr(smt_cvc5.Cvc5CrossCheck, "redecide", lambda self, smt2: "unknown")
    before = dict(CROSS_STATS)
    assert Z3Backend().decide_unsat(["n % 2 == 0 and n % 2 == 1"], 20) is True   # attempted, not established
    assert _delta(before)["cvc5_unknown"] == 1


def test_cvc5_failure_is_fail_closed(crosscheck_on, monkeypatch):
    monkeypatch.setattr(smt_cvc5.Cvc5CrossCheck, "redecide", lambda self, smt2: None)
    assert Z3Backend().decide_unsat(["n % 2 == 0 and n % 2 == 1"], 20) is True   # verdict stands


def test_redecide_roundtrips_a_real_script():
    import z3
    s = z3.Solver()
    n = z3.Int("n")
    s.add(n >= 0, n <= 10, n % 2 == 0, n % 2 == 1)
    assert smt_cvc5.Cvc5CrossCheck().redecide(s.to_smt2()) == "unsat"
    s2 = z3.Solver()
    s2.add(n >= 3, n <= 5)
    assert smt_cvc5.Cvc5CrossCheck().redecide(s2.to_smt2()) == "sat"
    assert smt_cvc5.Cvc5CrossCheck().redecide("(this is not smt2") is None       # parse surprise → None


# === ADR 0071 (Phase γ leg 2): the Z3-unknown second opinion =======================================

def _unsat_solver():
    """A real solver whose script cvc5 conclusively decides unsat (stands in for a Z3-unknown
    state; to_smt2 serializes the assertions regardless of any prior check outcome)."""
    import z3
    s = z3.Solver()
    n = z3.Int("n")
    s.add(n >= 0, n <= 10, n % 2 == 0, n % 2 == 1)
    return s


def test_second_opinion_gated_off_by_default(monkeypatch):
    from leibniz.backends.smt_z3 import _second_opinion_unknown
    monkeypatch.delenv("LEIBNIZ_CVC5_CROSSCHECK", raising=False)
    called = []
    monkeypatch.setattr(smt_cvc5.Cvc5CrossCheck, "redecide",
                        lambda self, smt2: called.append(1) or "unsat")
    assert _second_opinion_unknown(_unsat_solver()) == "unknown"
    assert not called                                     # cvc5 never consulted when gated off


def test_second_opinion_rescues_real_unsat(crosscheck_on):
    from leibniz.backends.smt_z3 import _second_opinion_unknown
    before = dict(CROSS_STATS)
    assert _second_opinion_unknown(_unsat_solver()) == "unsat"   # real cvc5 decides the script
    assert _delta(before)["unknown_rescued"] == 1


def test_second_opinion_adopts_nothing_but_unsat(crosscheck_on, monkeypatch):
    from leibniz.backends.smt_z3 import _second_opinion_unknown
    for verdict in ("sat", "unknown", None):              # sat carries no re-verifiable witness
        monkeypatch.setattr(smt_cvc5.Cvc5CrossCheck, "redecide", lambda self, smt2, v=verdict: v)
        before = dict(CROSS_STATS)
        assert _second_opinion_unknown(_unsat_solver()) == "unknown"
        assert _delta(before)["unknown_kept"] == 1 and _delta(before)["unknown_rescued"] == 0


def test_second_opinion_failure_keeps_unknown(crosscheck_on, monkeypatch):
    from leibniz.backends.smt_z3 import _second_opinion_unknown

    def boom(self, smt2):
        raise RuntimeError("cvc5 exploded")
    monkeypatch.setattr(smt_cvc5.Cvc5CrossCheck, "redecide", boom)
    assert _second_opinion_unknown(_unsat_solver()) == "unknown"  # never breaks a probe


def test_decide_routes_z3_unknown_through_the_second_opinion(crosscheck_on, monkeypatch):
    import z3
    monkeypatch.setattr(z3.Solver, "check", lambda self, *a: z3.unknown)  # force the unknown tail
    monkeypatch.setattr(smt_cvc5.Cvc5CrossCheck, "redecide", lambda self, smt2: "unsat")
    before = dict(CROSS_STATS)
    # a probe Z3 alone could not conclude now concludes: decide_unsat's conclusive True
    assert Z3Backend().decide_unsat(["n % 2 == 0 and n % 2 == 1"], 20) is True
    assert _delta(before)["unknown_rescued"] == 1
