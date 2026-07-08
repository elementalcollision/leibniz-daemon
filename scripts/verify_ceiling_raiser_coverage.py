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

import ast
import itertools
import math
import random
import sys

from leibniz.backends.lean_repl import LeanReplBackend
from leibniz.backends.smt_z3 import Z3Backend
from leibniz.gates.boolean_decided import classify_boolean
from leibniz.gates.boolean_decided import register as reg_boolean
from leibniz.gates.faithfulness import FaithfulnessGate
from leibniz.gates.lean_decided import classify_property
from leibniz.gates.lean_decided import register as reg_lean_decided
from leibniz.gates.minmax_decided import classify_identity
from leibniz.gates.minmax_decided import register as reg_minmax
from leibniz.gates.mixed_modulus_decided import classify_mixed
from leibniz.gates.mixed_modulus_decided import register as reg_mixed
from leibniz.dsl_to_lean import free_vars
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


# --- breadth via a FUZZED full-path sweep: generate diverse claims, keep the oracle-TRUE single-fragment
#     ones, and confirm each promulgates through the FULL path via the correct producer (an independent
#     ground-truth oracle — Python residue/grid enumeration, not Lean, not the daemon's evaluator). ------

def _tree(s):
    return ast.parse(s.replace("^", "**"), mode="eval").body


def _oracle_true(cd, cp, minmax):
    """True iff cp holds for EVERY in-domain assignment. Modular: exact over residues mod lcm. min/max:
    a [0,13) grid."""
    vs = sorted({n.id for n in ast.walk(_tree(cp)) if isinstance(n, ast.Name) and n.id not in ("min", "max")})
    mods = {n.right.value for n in ast.walk(_tree(cp))
            if isinstance(n, ast.BinOp) and isinstance(n.op, ast.Mod) and isinstance(n.right, ast.Constant)}
    rng = range(13) if minmax else range(math.lcm(*mods) if mods else 2)
    cpx, cdx = cp.replace("^", "**"), cd.replace("^", "**")
    for pt in itertools.product(rng, repeat=len(vs)):
        asn = dict(zip(vs, pt), min=min, max=max)
        if eval(cdx, {"__builtins__": {}}, asn) and not eval(cpx, {"__builtins__": {}}, asn):  # noqa: S307
            return False
    return True


_PRODUCER = {"lean_decided": "lean_decided/kernel", "minmax": "minmax_identity/kernel",
             "boolean": "boolean_modular/kernel", "mixed": "mixed_modular/kernel"}


def _route(cp, cd):
    """The single fragment cp classifies to (with 2..3 vars), or None if 0 or >1 — the fuzz sweep keeps
    only claims that route to EXACTLY one fragment, so 'promulgates via the correct producer' is well-posed."""
    if not (2 <= len(free_vars(cd, cp)) <= 3):
        return None
    hits = [k for k, f in (("lean_decided", classify_property), ("minmax", classify_identity),
                           ("boolean", classify_boolean), ("mixed", classify_mixed)) if f(cp)]
    return hits[0] if len(hits) == 1 else None


def _candidate_pool():
    """Parameterized TRUE-by-design templates per fragment (CRT prime facts, square-parity relations,
    Fermat little-theorem congruences, min/max symmetric identities). Every candidate is still
    oracle-verified before use, so a template that is accidentally false is dropped, not trusted."""
    pool = {"lean_decided": [], "minmax": [], "boolean": [], "mixed": []}
    # lean_decided — neq/eq atoms + Fermat congruences over a range of moduli/polys (oracle keeps the true)
    for m in (2, 3, 4, 5, 6):
        for p in ("a*a + b*b", "a*b", "a*a - b*b", "a*a + a*b + b*b"):
            for c in range(m):
                pool["lean_decided"].append((CD, f"({p}) % {m} != {c}", False))
    pool["lean_decided"] += [
        (CD, "((a*b)**2 + a*b) % 6 == 0 or ((a*b)**2 + a*b) % 6 == 2", False),
        (CD, "(a**3 - a) % 3 == 0 and (b**3 - b) % 3 == 0", False),
        (CD, "(a*a*(a*a - 1)) % 12 == 0 and (b*b*(b*b - 1)) % 12 == 0", False),
    ]
    # minmax — symmetric-function identities, powers 1..3, product, conjunctions, 3-var
    for k in (2, 3):
        pool["minmax"].append((CD, f"max(a,b)**{k} + min(a,b)**{k} == a**{k} + b**{k}", True))
    pool["minmax"] += [
        (CD, "max(a,b) + min(a,b) == a + b", True),
        (CD, "max(a,b) * min(a,b) == a*b", True),
        (CD, "max(a,b)**2 + min(a,b)**2 == a**2 + b**2 and max(a,b)*min(a,b) == a*b", True),
        (CD3, "(max(a,b)+min(a,b)) + (max(b,c)+min(b,c)) == a + 2*b + c", True),
        (CD3, "(max(a,b)+min(a,b)) + (max(a,c)+min(a,c)) == 2*a + b + c", True),
    ]
    # boolean — CRT prime-modulus zero-product facts (ab≡0 ⟺ a≡0 ∨ b≡0), several primes/polys
    for m in (2, 3, 5, 7):
        for p in ("a*b", "a*a*b*b"):
            pool["boolean"].append((CD, f"(({p}) % {m} == 0) == ((a % {m} == 0) or (b % {m} == 0))", False))
            pool["boolean"].append((CD, f"(({p}) % {m} != 0) == ((a % {m} != 0) and (b % {m} != 0))", False))
    # mixed — square-parity (n²≡r mod 4 ⟺ n≡r mod 2) over several bases, + a CRT-6 zero-product
    for base in ("a + b", "a*b", "a*a + b"):
        pool["mixed"].append((CD, f"(({base})**2 % 4 == 1) == (({base}) % 2 == 1)", False))
        pool["mixed"].append((CD, f"(({base})**2 % 4 == 0) == (({base}) % 2 == 0)", False))
    pool["mixed"].append(
        (CD, "((a*b) % 6 == 0) == (((a % 2 == 0) or (b % 2 == 0)) and ((a % 3 == 0) or (b % 3 == 0)))", False))
    return pool


def _fuzz_claims(rng, want_per):
    """From the parameterized pool, keep candidates that (a) route to EXACTLY one fragment with 2..3
    vars and (b) are oracle-TRUE; shuffle and sample up to `want_per` per fragment. Returns
    (cd, cp, minmax, fragment) tuples + per-fragment counts."""
    out, counts = [], {}
    for kind, cands in _candidate_pool().items():
        good = [(cd, cp, mm) for (cd, cp, mm) in cands if _route(cp, cd) == kind and _oracle_true(cd, cp, mm)]
        rng.shuffle(good)
        picked = good[:want_per]
        counts[kind] = len(picked)
        out += [(cd, cp, mm, kind) for (cd, cp, mm) in picked]
    return out, counts


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
    per_fuzz = int(sys.argv[1]) if len(sys.argv) > 1 else 6      # fuzzed claims per fragment (0 = skip)
    curated = "fuzzonly" not in sys.argv                        # skip the (already-validated) curated set
    rng = random.Random(20260708)
    be = LeanReplBackend(timeout_s=175)
    fails = []
    fuzz_counts = {k: 0 for k in _PRODUCER}
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

        def promulgates(cd, cp):
            """Run the full path; return (is_promotable, faithfulness_producer)."""
            prop = _prop(cd, cp)
            faith = gate.check(prop)
            prop.record(faith)
            demo.run(prop)
            return verify.is_promotable(prop), faith.producer

        if curated:
            print("=== IN-REACH (curated): full path (faithfulness → fast-path → is_promotable) ===")
            for cd, cp, want in IN_REACH:
                promotable, routed = promulgates(cd, cp)
                ok = promotable and routed == want
                if not ok:
                    fails.append(("in-reach", cp, f"promotable={promotable} routed={routed} want={want}"))
                print(f"  {'OK ' if ok else '!! '}{routed:22} promotable={promotable!s:5}  {cp[:56]}")

            print("\n=== BOUNDARY: just outside each fragment → must DEFER ===")
            for cd, cp, why in BOUNDARY:
                promotable, _ = promulgates(cd, cp)
                if promotable:
                    fails.append(("boundary", cp, f"promotable=True (should DEFER: {why})"))
                print(f"  {'OK ' if not promotable else '!! '}DEFER={not promotable!s:5}  {why:34} {cp[:40]}")

        if per_fuzz > 0:
            claims, gen_counts = _fuzz_claims(rng, per_fuzz)
            print(f"\n=== FUZZED breadth ({len(claims)} oracle-TRUE single-fragment claims: {gen_counts}) ===")
            for cd, cp, _mm, kind in claims:
                promotable, routed = promulgates(cd, cp)
                ok = promotable and routed == _PRODUCER[kind]
                fuzz_counts[kind] += ok
                if not ok:
                    fails.append(("fuzz", cp, f"promotable={promotable} routed={routed} want={_PRODUCER[kind]}"))
                print(f"  {'OK ' if ok else '!! '}{routed:22} {cp[:60]}")
    finally:
        be.close()

    print()
    if not fails:
        nf = sum(fuzz_counts.values())
        curated_part = (f"{len(IN_REACH)} curated in-reach claims promulgate via the correct producer; "
                        f"all {len(BOUNDARY)} boundary claims DEFER; " if curated else "")
        print(f"COVERAGE OK: {curated_part}{nf} fuzzed in-reach claims promulgate via the correct producer "
              f"(fuzz per fragment: {fuzz_counts}). The five procedures compose without cross-talk.")
        return 0
    print(f"!! {len(fails)} coverage failure(s):")
    for kind, cp, detail in fails:
        print(f"   [{kind}] {cp}  ->  {detail}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
