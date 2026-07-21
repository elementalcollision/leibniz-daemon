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
