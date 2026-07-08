"""Coverage / completeness + composition harness for the five ceiling-raiser decision procedures (Phase 2).

Where the Phase-1 soundness harness proves NO FALSE law promulgates, this proves the intended coverage:
a curated, systematic corpus of in-reach TRUE claims — run through the FULL path (faithfulness gate →
fast-path → is_promotable), with ALL FIVE backends registered and ALL FIVE fast-paths composed on one
kernel — each promulgates end-to-end via the CORRECT producer; and a boundary corpus (just outside each
fragment) DEFERs cleanly. Because every fragment's backend + fast-path are active at once, this is also
the first test that the five procedures COMPOSE without cross-talk (each claim routes to exactly one).

ONE Lean REPL session, closed in `finally`; the caller verifies containers → 0.

Usage:  PYTHONPATH=. python scripts/verify_ceiling_raiser_coverage.py
"""
from __future__ import annotations

import sys

from leibniz.backends.lean_repl import LeanReplBackend
from leibniz.backends.smt_z3 import Z3Backend
from leibniz.gates.boolean_decided import register as reg_boolean
from leibniz.gates.faithfulness import FaithfulnessGate
from leibniz.gates.lean_decided import register as reg_lean_decided
from leibniz.gates.minmax_decided import register as reg_minmax
from leibniz.gates.mixed_modulus_decided import register as reg_mixed
from leibniz.gates.verification import VerificationGate
from leibniz.probes import default_probes
from leibniz.propositio import Enuntiatio, Expressio, Propositio
from leibniz.providers.boolean_prover import BooleanDemonstrate
from leibniz.providers.minmax_prover import MinMaxDemonstrate
from leibniz.providers.mixed_modulus_prover import MixedModulusDemonstrate
from leibniz.providers.residue_prover import ResidueDemonstrate
from leibniz.trust import NOVELTY_EDGE, TrustPolicy
from leibniz.types import ClaimType, EdgeEvidence, TrustTier, Verdict
from leibniz.verifiers import LeanVerifier, SMTVerifier

CD = "a >= 0 and b >= 0"
CD3 = "a >= 0 and b >= 0 and c >= 0"

# --- in-reach corpus: (claim_domain, claim_property, expected faithfulness producer) ----------------
IN_REACH = [
    # lean_decided (single-modulus modular: atom / residue-set / conjunction)
    (CD, "(a*a + b*b) % 4 != 3", "lean_decided/kernel"),
    (CD, "(a*b*(a*a - b*b)) % 6 == 0", "lean_decided/kernel"),
    (CD, "((a*b)^2 + a*b) % 6 == 0 or ((a*b)^2 + a*b) % 6 == 2", "lean_decided/kernel"),
    (CD, "(a*a) % 4 != 3 and (b*b) % 4 != 3", "lean_decided/kernel"),
    (CD, "((a*b)^2 + a*b) % 6 != 1 and ((a*b)^2 + a*b) % 6 != 3", "lean_decided/kernel"),
    # minmax identities (+ conjunction, 3-var)
    (CD, "max(a,b)**2 + min(a,b)**2 == a**2 + b**2", "minmax_identity/kernel"),
    (CD, "max(a,b) * min(a,b) == a*b", "minmax_identity/kernel"),
    (CD, "max(a,b)**3 + min(a,b)**3 == a**3 + b**3", "minmax_identity/kernel"),
    (CD, "max(a,b)**2 + min(a,b)**2 == a**2 + b**2 and max(a,b)*min(a,b) == a*b", "minmax_identity/kernel"),
    (CD3, "(max(a,b)+min(a,b)) + (max(b,c)+min(b,c)) == a + 2*b + c", "minmax_identity/kernel"),
    # same-modulus boolean combinations (biconditional / not / neq)
    (CD, "((a*b) % 3 == 0) == ((a % 3 == 0) or (b % 3 == 0))", "boolean_modular/kernel"),
    (CD, "((a*b) % 2 != 1) == ((a % 2 == 0) or (b % 2 == 0))", "boolean_modular/kernel"),
    (CD, "(not ((a*b) % 2 == 1)) == ((a % 2 == 0) or (b % 2 == 0))", "boolean_modular/kernel"),
    # mixed-modulus (LCM/castHom: LCM 4, LCM 6, neq)
    (CD, "((a+b)**2 % 4 == 1) == ((a+b) % 2 == 1)", "mixed_modular/kernel"),
    (CD, "((a*a+b*b) % 4 == 2) == ((a % 2 == 1) and (b % 2 == 1))", "mixed_modular/kernel"),
    (CD, "((a*b) % 6 == 0) == (((a % 2 == 0) or (b % 2 == 0)) and ((a % 3 == 0) or (b % 3 == 0)))", "mixed_modular/kernel"),
    (CD, "((a+b)**2 % 4 == 1) == ((a+b) % 2 != 0)", "mixed_modular/kernel"),
]

# --- boundary corpus: just outside each fragment → must DEFER (not promulgate via the ceiling-raiser)
BOUNDARY = [
    ("n >= 0", "(n*n) % 5 == 0 or (n*n) % 5 == 1", "1-var: below MIN_VARS"),
    (CD, "(a*a + b*b) % 71 != 0", "residue budget m**nvars over cap"),
    (CD3, "max(a, min(b,c)) == a", "nested min/max"),
    (CD3, "max(a, b, c) == a", ">=3-ary min/max"),
    (CD, "max(a + 1, b) == a", "compound (non-variable) min/max arg"),
    (CD, "((a+b) % 8 == 0) == ((a+b) % 9 == 0)", "mixed LCM 72 over MAX_LCM"),
    (CD, "(a*a + b*b) % 4 == 5", "out-of-range residue (c >= m)"),
    (CD, "max(a,b) < a + b", "min/max inequality (not Eq)"),
]


def _prop(cd, cp):
    en = Enuntiatio(statement="cov", claim_type=ClaimType.INVARIANT, falsifiable_claim="x",
                    claim_domain=cd, claim_property=cp)
    prop = Propositio(enuntiatio=en, expressio=Expressio(theorem_src="theorem llm (a b : Nat) : True",
                                                         established_domain=cd))
    prop.record(EdgeEvidence(NOVELTY_EDGE, TrustTier.MECHANICAL, Verdict.PASS, producer="NoveltyGate"))
    return prop


class RecordingInner:
    def run(self, prop):
        return prop


def main() -> int:
    be = LeanReplBackend(timeout_s=170)
    fails = []
    try:
        kernel = LeanVerifier(be)
        gate = FaithfulnessGate(smt=SMTVerifier(backend=Z3Backend()),
                                probes=default_probes(SMTVerifier(backend=Z3Backend())),
                                judge=type("J", (), {"round_trip_agrees": lambda self, p: 0.0})())
        for reg in (reg_lean_decided, reg_minmax, reg_boolean, reg_mixed):   # all five faithfulness backends
            reg(gate, be)
        # compose all four fast-paths on one kernel (lean_decided is proved by the residue fast-path)
        demo = RecordingInner()
        for Wrap in (ResidueDemonstrate, MinMaxDemonstrate, BooleanDemonstrate, MixedModulusDemonstrate):
            demo = Wrap(inner=demo, lean=kernel)
        verify = VerificationGate(TrustPolicy())

        print("=== IN-REACH: full path (faithfulness → fast-path → is_promotable) ===")
        for cd, cp, want_producer in IN_REACH:
            prop = _prop(cd, cp)
            faith = gate.check(prop)
            prop.record(faith)
            demo.run(prop)
            promotable = verify.is_promotable(prop)
            routed = faith.producer
            ok = promotable and routed == want_producer
            if not ok:
                fails.append(("in-reach", cp, f"promotable={promotable} routed={routed} want={want_producer}"))
            print(f"  {'OK ' if ok else '!! '}{routed:22} promotable={promotable!s:5}  {cp[:56]}")

        print("\n=== BOUNDARY: just outside each fragment → must DEFER ===")
        for cd, cp, why in BOUNDARY:
            prop = _prop(cd, cp)
            prop.record(gate.check(prop))
            demo.run(prop)
            promotable = verify.is_promotable(prop)
            ok = not promotable
            if not ok:
                fails.append(("boundary", cp, f"promotable={promotable} (should DEFER: {why})"))
            print(f"  {'OK ' if ok else '!! '}DEFER={not promotable!s:5}  {why:34} {cp[:40]}")
    finally:
        be.close()

    print()
    if not fails:
        print(f"COVERAGE OK: all {len(IN_REACH)} in-reach claims promulgate via the correct producer; "
              f"all {len(BOUNDARY)} boundary claims DEFER. The five procedures compose without cross-talk.")
        return 0
    print(f"!! {len(fails)} coverage failure(s):")
    for kind, cp, detail in fails:
        print(f"   [{kind}] {cp}  ->  {detail}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
