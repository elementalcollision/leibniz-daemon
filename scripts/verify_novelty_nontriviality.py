"""Phase 3 — novelty / non-triviality quarantine validation + yield characterization.

Before any ``LEIBNIZ_LEAN_DECIDED`` activation, this proves the kill-only novelty layer QUARANTINES
trivial / textbook claims that route to a ceiling-raiser fragment, and MEASURES how much of the
"in-reach" region the stock non-triviality ladder already eats (the honest yield instrument the
optimization roadmap calls for).

The layer, in order (all MECHANICAL, kill-only — trust invariant 4: novelty is settled by retrieval +
a decision procedure, never a judge):
  1. classification content-free guard — `P == P` / vacuous shapes rejected at ROUTING (never reach a
     procedure; the `*_law` builder returns None).
  2. is_trivial — LeanVerifier.is_trivial → the real backend's 7-tactic ladder
     (decide/simp/omega/trivial/aesop/ring/nlinarith) on the bare statement. Runs BEFORE the
     ceiling-raiser, so the procedure's unique value is exactly the region these tactics can NOT close.
  3. structural_known (ADR 0032 congruence signature) + contains_equivalent (formal_hash) — KNOWN
     restatements, matched by FORM not truth (cannot false-KNOWN).

We test each trivial claim through the SAME statement the daemon would promulgate (the `*_law` theorem
the ceiling-raiser emits) and assert it is caught by AT LEAST ONE defense; and we confirm the genuine
Phase-2 in-reach claims survive is_trivial (the procedure adds real value), reporting honestly where a
stock tactic already closes one.

ONE Lean REPL backend, closed in `finally`; the caller verifies containers -> 0.

Usage:  PYTHONPATH=. python scripts/verify_novelty_nontriviality.py
"""
from __future__ import annotations

import ast
import sys

from leibniz.backends.lean_repl import LeanReplBackend
from leibniz.corpus import CorpusBackend
from leibniz.gates.boolean_decided import classify_boolean
from leibniz.gates.lean_decided import classify_property
from leibniz.gates.minmax_decided import classify_identity
from leibniz.gates.mixed_modulus_decided import classify_mixed
from leibniz.propositio import Expressio
from leibniz.providers.boolean_prover import boolean_law
from leibniz.providers.minmax_prover import minmax_law
from leibniz.providers.mixed_modulus_prover import mixed_law
from leibniz.providers.residue_prover import residue_law
from leibniz.structural import is_coefficient_degenerate
from leibniz.verifiers import LeanVerifier

IMPORTS = ("Mathlib.Tactic",)

# routing order matters only for reporting which fragment owns a claim; each claim below routes to
# exactly one (Phase 2 established no cross-talk). mixed is tried before lean_decided because a
# mixed-modulus claim also fails classify_property (single modulus) — order is defensive.
ROUTERS = [
    ("minmax", classify_identity, minmax_law),
    ("boolean", classify_boolean, boolean_law),
    ("mixed", classify_mixed, mixed_law),
    ("lean_decided", classify_property, residue_law),
]


def _fvars(s: str) -> list[str]:
    return sorted({n.id for n in ast.walk(ast.parse(s.replace("^", "**"), mode="eval").body)
                   if isinstance(n, ast.Name) and n.id not in ("min", "max")})


def _route(cp: str):
    for gen, classify, builder in ROUTERS:
        if classify(cp) is not None:
            return gen, builder
    return None, None


# --- corpora --------------------------------------------------------------------------------------

# TRIVIAL / textbook-vacuous: each MUST be quarantined by some defense (classification-reject,
# is_trivial, or structural_known). None may survive to promulgable.
TRIVIAL = [
    "(a % 2 == 0) == (a % 2 == 0)",                       # boolean P<->P  (expect: classification-reject)
    "((a*b) % 2 == 0) or not ((a*b) % 2 == 0)",           # boolean tautology (expect: classification-reject)
    "((a+b) % 4 == 1) == ((a+b) % 4 == 1)",               # mixed P<->P (expect: classification-reject)
    "max(a,b) == max(b,a)",                               # minmax commutativity (expect: is_trivial)
    "min(a,b) == min(b,a)",                               # minmax commutativity (expect: is_trivial)
    "max(a,b) + min(a,b) == a + b",                       # minmax textbook identity (expect: is_trivial)
    "max(a,b) - min(a,b) == max(a,b) - min(a,b)",         # minmax reflexive (expect: classification-reject or is_trivial)
    "(2*a*b) % 2 == 0",                                   # ADR 0061: coeff 2 | 2, nonlinear (expect: coefficient_degenerate)
    "(3*a*b) % 3 == 0",                                   # ADR 0061: coeff 3 | 3 (expect: coefficient_degenerate)
    "(2*a*b + 1) % 2 == 1",                               # ADR 0061: poly-c=2ab (expect: coefficient_degenerate)
    "(4*a + 2*b) % 2 == 0",                               # ADR 0061: linear-degenerate omega misses (expect: coefficient_degenerate)
    "(a + b - a - b) % 3 == 0",                           # lean_decided: 0 % 3 (expect: coefficient_degenerate or is_trivial)
    "(a*a - a*a + b) % 1 == 0",                           # modulus 1 (expect: classification-reject, m<2)
]

# GENUINE Phase-2 in-reach: the ceiling-raiser's real value. Expect is_trivial == False (survives the
# stock ladder). Where a tactic DOES close one, we report it honestly (not a failure — it just means
# that claim was never the procedure's unique contribution).
GENUINE = [
    ("lean_decided", "(a*a + b*b) % 4 != 3"),
    ("lean_decided", "(a*b*(a*a - b*b)) % 6 == 0"),
    ("lean_decided", "(a**3 - a) % 3 == 0 and (b**3 - b) % 3 == 0"),
    ("minmax", "max(a,b)**2 + min(a,b)**2 == a**2 + b**2"),
    ("minmax", "max(a,b) * min(a,b) == a*b"),
    ("boolean", "((a*b) % 3 == 0) == ((a % 3 == 0) or (b % 3 == 0))"),
    ("boolean", "((a*b) % 2 != 1) == ((a % 2 == 0) or (b % 2 == 0))"),
    ("mixed", "((a+b)**2 % 4 == 1) == ((a+b) % 2 == 1)"),
    ("mixed", "((a*a+b*b) % 4 == 2) == ((a % 2 == 1) and (b % 2 == 1))"),
]


def _law_theorem(cp: str):
    """The `*_law` theorem the ceiling-raiser would emit for `cp`, or None if no fragment routes it
    (classification content-free / out-of-fragment rejection)."""
    gen, builder = _route(cp)
    if builder is None:
        return gen, None
    cd = " and ".join(f"{v} >= 0" for v in _fvars(cp)) or "a >= 0"
    law = builder("phase3", cd, cp)
    return gen, (law[0] if law else None)


def main() -> int:
    corpus = CorpusBackend.from_json()
    be = LeanReplBackend(timeout_s=175)
    lean = LeanVerifier(be)
    fails = []
    triv_rows, genuine_rows = [], []
    try:
        # --- 1. trivial-quarantine: every trivial claim caught by SOME defense --------------------
        # ordered cheapest-first, mirroring NoveltyGate: classification-reject (routing) -> ADR 0061
        # coefficient_degenerate (pure DSL) -> is_trivial (Lean ladder) -> structural_known (corpus).
        for cp in TRIVIAL:
            gen, thm = _law_theorem(cp)
            coeff_deg = is_coefficient_degenerate(cp)
            # only pay for the Lean is_trivial call when the cheaper defenses miss
            triv = bool(thm) and not coeff_deg and lean.is_trivial(Expressio(theorem_src=thm, imports=IMPORTS))
            sk = corpus.structural_known(cp)
            if thm is None:
                defense = "classification-reject"
            elif coeff_deg:
                defense = "coefficient_degenerate"
            elif triv:
                defense = "is_trivial"
            elif sk is not None:
                defense = f"structural_known:{sk}"
            else:
                defense = None
            quarantined = defense is not None
            triv_rows.append((quarantined, gen or "-", defense or "!! SURVIVES", cp))
            if not quarantined:
                fails.append(("trivial-survives", cp,
                              f"routed={gen} coeff_degenerate=False is_trivial=False structural_known=None "
                              f"-> would promulgate"))

        # --- 2. no over-quarantine: genuine in-reach survives is_trivial --------------------------
        n_survive = 0
        for want_gen, cp in GENUINE:
            gen, thm = _law_theorem(cp)
            if thm is None:
                genuine_rows.append(("MISROUTE", gen or "-", cp))
                fails.append(("genuine-misroute", cp, f"expected {want_gen}, routed {gen}"))
                continue
            triv = lean.is_trivial(Expressio(theorem_src=thm, imports=IMPORTS))
            n_survive += (not triv)
            genuine_rows.append(("is_trivial" if triv else "SURVIVES", gen, cp))
    finally:
        be.close()

    print("=== 1. TRIVIAL-QUARANTINE: every vacuous/textbook claim caught by a defense ===")
    for q, gen, defense, cp in triv_rows:
        print(f"  {'OK ' if q else '!! '}{gen:13} {defense:26} {cp[:44]}")
    print("\n=== 2. NO OVER-QUARANTINE: genuine in-reach vs the is_trivial ladder ===")
    for status, gen, cp in genuine_rows:
        mark = "OK " if status in ("SURVIVES",) else ("-- " if status == "is_trivial" else "!! ")
        print(f"  {mark}{gen:13} {status:10} {cp[:50]}")

    # --- 3. yield characterization ----------------------------------------------------------------
    n_triv_caught = sum(1 for q, *_ in triv_rows if q)
    n_class = sum(1 for _q, _g, d, _c in triv_rows if d == "classification-reject")
    n_coeff = sum(1 for _q, _g, d, _c in triv_rows if d == "coefficient_degenerate")
    n_istriv = sum(1 for _q, _g, d, _c in triv_rows if d == "is_trivial")
    n_sk = sum(1 for _q, _g, d, _c in triv_rows if d and d.startswith("structural_known"))
    print("\n=== 3. YIELD INSTRUMENT ===")
    print(f"  trivial corpus: {n_triv_caught}/{len(TRIVIAL)} quarantined (classification-reject={n_class}, "
          f"coefficient_degenerate={n_coeff}, is_trivial={n_istriv}, structural_known={n_sk})")
    print(f"  genuine corpus: {n_survive}/{len(GENUINE)} survive is_trivial "
          f"(the ceiling-raiser's non-trivial contribution; the rest a stock tactic already closes)")

    print()
    if not fails:
        print("PHASE 3 OK: no trivial/textbook claim reaches promulgable — every one is quarantined by "
              "classification-reject, the ADR 0061 coefficient_degenerate guard, the is_trivial ladder, or "
              "structural_known; genuine in-reach claims survive. The non-triviality layer is sound before "
              "LEIBNIZ_LEAN_DECIDED activation.")
        return 0
    print(f"!! {len(fails)} FAILURE(S):")
    for kind, cp, detail in fails:
        print(f"   [{kind}] {cp} -> {detail}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
