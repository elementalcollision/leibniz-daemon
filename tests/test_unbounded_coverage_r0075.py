"""ADR 0075 — the faithfulness probe's COVERAGE leg is decided without a box.

The coverage leg asserts a UNIVERSALLY QUANTIFIED implication (claim_domain implies
established_domain). Deciding it inside the [0, bound] search box is unsound whenever the
domain is box-unrepresentative: the bounded search reports "no gap" because the few in-box
points happen to satisfy the narrower established_domain, while real counterexamples sit
just outside. That let a FALSE claim take this probe's PASS branch.

CI-safe: no Docker, no Lean. The z3-dependent cases skip without the verify extra.
"""
from __future__ import annotations

import pytest

from leibniz.backends.smt_z3 import Z3Backend, available
from leibniz.probes import default_probes
from leibniz.propositio import Enuntiatio, Expressio, Propositio
from leibniz.types import ClaimType
from leibniz.verifiers import SMTVerifier

# The review exploit: only in-box point is (61,61), which satisfies ed; a=65 is the real gap.
EXPLOIT_CD = "a % 4 == 1 and a > 60 and b % 4 == 1 and b > 60"
EXPLOIT_ED = "a % 16 == 13 and b % 16 == 13"
EXPLOIT_CP = "(a*a + b*b) % 16 == 2"          # FALSE at (61, 65) -> 10


def _prop(cd, cp, ed):
    en = Enuntiatio(statement="t", claim_type=ClaimType.INVARIANT, falsifiable_claim="x",
                    claim_domain=cd, claim_property=cp)
    return Propositio(enuntiatio=en,
                      expressio=Expressio(theorem_src="theorem t : True", established_domain=ed))


pytestmark = pytest.mark.skipif(not available(), reason="z3-solver (verify extra) required")


def test_the_box_hides_the_gap_that_the_unbounded_query_finds():
    be = Z3Backend()
    args = [f"({EXPLOIT_CD})", f"not ({EXPLOIT_ED})"]
    assert be.decide_unsat(args, 64) is True            # bounded: "no gap" — WRONG
    assert be.decide_unsat_unbounded(args) is False     # unbounded: the real counterexample


def test_probe_refuses_the_box_unrepresentative_claim_via_the_COVERAGE_leg():
    smt = SMTVerifier(backend=Z3Backend())
    probe = default_probes(smt)[ClaimType.INVARIANT]
    assert probe(_prop(EXPLOIT_CD, EXPLOIT_CP, EXPLOIT_ED)) is None      # DEFER, was True


def test_probe_refuses_the_SAME_claim_through_the_PROPERTY_leg():
    """The first draft of ADR 0075 unbounded only the coverage leg. With established_domain
    == claim_domain — the honest shape, and the one ADR 0074 DERIVES — coverage passes
    trivially as `cd and not cd` and the identical false claim walked through the still
    bounded property leg to a MECHANICAL PASS. Both legs must be unbounded."""
    smt = SMTVerifier(backend=Z3Backend())
    probe = default_probes(smt)[ClaimType.INVARIANT]
    assert probe(_prop(EXPLOIT_CD, EXPLOIT_CP, EXPLOIT_CD)) is None
    # and the bounded query really would have passed it (the defect, pinned)
    be = Z3Backend()
    args = [f"({EXPLOIT_CD})", f"({EXPLOIT_CD})", f"not ({EXPLOIT_CP})"]
    assert be.decide_unsat(args, 64) is True                  # box: no counterexample
    assert be.decide_unsat_unbounded(args) is False           # truth: (61, 65)


def test_probe_defers_when_the_backend_cannot_decide_unbounded():
    """Fail CLOSED: a backend without the unbounded decider must DEFER, never silently fall
    back to the bounded query the exploit defeats."""

    class _BoundedOnly:
        def encodable(self, pred):
            return True

        def decide_unsat(self, preds, bound=0):
            return True                                        # would have PASSed everything

        def find_gaming_witness(self, **kw):
            return None
    smt = SMTVerifier(backend=_BoundedOnly())
    probe = default_probes(smt)[ClaimType.INVARIANT]
    assert probe(_prop(EXPLOIT_CD, EXPLOIT_CP, EXPLOIT_CD)) is None


def test_byte_identical_domains_cover_without_a_solver_call():
    """ed == cd covers by construction. Deciding it instead would needlessly DEFER every
    ADR 0035/0066 domain, whose encodings are exact only inside the box."""

    class _CountingZ3(Z3Backend):
        calls = 0

        def decide_unsat_unbounded(self, preds):
            type(self).calls += 1
            return super().decide_unsat_unbounded(preds)
    be = _CountingZ3()
    probe = default_probes(SMTVerifier(backend=be))[ClaimType.INVARIANT]
    probe(_prop("n >= 0", "n + 1 > n", "n >= 0"))
    assert _CountingZ3.calls == 1                              # property leg only


@pytest.mark.parametrize("cd,cp", [
    ("n >= 0", "n + 1 > n"),
    ("a >= 0 and b >= 0", "a + b >= 0"),
    ("n >= 0", "(n + n) % 2 == 0"),
])
def test_probe_still_certifies_honest_canonical_contracts(cd, cp):
    """No yield loss on the population the probe actually decides: with ed == cd the
    unbounded coverage query is `cd and not cd` — unsat instantly, for any domain.
    (Claims whose PROPERTY leg Z3 cannot decide, e.g. the nonlinear `(a^2+b^2) % 4 != 3`,
    were never probe-passable and still are not; they certify via the kernel backend.)"""
    smt = SMTVerifier(backend=Z3Backend())
    probe = default_probes(smt)[ClaimType.INVARIANT]
    assert probe(_prop(cd, cp, cd)) is True


def test_probe_refuses_a_genuinely_narrower_established_domain():
    smt = SMTVerifier(backend=Z3Backend())
    probe = default_probes(smt)[ClaimType.INVARIANT]
    assert probe(_prop("n >= 0", "(n^2) % 2 == 0", "n >= 0 and n % 2 == 0")) is None


def test_unbounded_queries_refuse_box_only_encodings():
    """ADR 0066 factorial/gcd tables and the ADR 0035 order reduction are exact ONLY inside
    the box, so an unbounded query must not use them: compile refuses -> None -> DEFER."""
    be = Z3Backend()
    for pred in ("factorial(n) % 5 == 0", "gcd(6, n) == 1", "2**n % 7 == 1"):
        assert be.decide_unsat_unbounded([pred]) is None
    # ... while a plain modular predicate is still decided
    assert be.decide_unsat_unbounded(["(n^2) % 2 == 0", "not ((n^2) % 2 == 0)"]) is True


def test_non_negativity_is_kept_in_the_unbounded_mode():
    """The DSL's Z-with-box semantics make non-negativity part of the claim; only the UPPER
    bound is dropped. Without this, `n >= 0` would no longer be implied and coverage checks
    involving it would flip."""
    be = Z3Backend()
    assert be.decide_unsat_unbounded(["n < 0"]) is True          # negatives are excluded
    assert be.decide_unsat_unbounded(["n > 1000000"]) is False   # but nothing above the box is
