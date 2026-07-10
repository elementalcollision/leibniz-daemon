"""ADR 0063 Phase 4 — the ORIGINATION HUNT: a mechanical sweep for gate-novel, kernel-provable facts.

Systematically enumerates candidate claims across the five kernel-decidable fragments (residue /
conjunction, min-max, same-modulus boolean, mixed-modulus, and the ADR 0065 power-mod fragment) and
screens each through the daemon's own honesty machinery, cheapest first:

  1. TRUTH        — an independent exact Python oracle (residue enumeration over the lcm/period;
                    a grid for min/max). False candidates are discarded, not proposed.
  2. ROUTE        — exactly ONE fragment classifier accepts (kernel-decidable, no cross-talk).
  3. DEGENERACY   — ADR 0061 `is_coefficient_degenerate` (variable-independent trivia).
  4. KNOWN        — ADR 0032 `structural_known` against the curated corpus.
  5. DEDUP        — in-run `congruence_signature` dedup (one representative per signature class).
  6. IS_TRIVIAL   — the REAL kernel tactic ladder (decide/simp/omega/trivial/aesop/ring/nlinarith)
                    on the canonical ℤ-box LAW statement: anything a stock tactic closes is vacuous.
  7. PROVABLE     — the fragment's own LAW generator proof must kernel-check (promulgable-grade).

Survivors are exactly the claims `attest_novelty` (ADR 0063) would certify: novel per the mechanical
gate — with the standing honest caveat that gate-novelty is NOT absolute novelty. The report is the
deliverable; no law is promulgated by this script.

Usage:  PYTHONPATH=. python scripts/origination_hunt.py [max_kernel_candidates]
"""
from __future__ import annotations

import ast
import itertools
import math
import sys

from leibniz.backends.lean_repl import LeanReplBackend, available
from leibniz.corpus import CorpusBackend
from leibniz.gates.boolean_decided import classify_boolean
from leibniz.gates.lean_decided import classify_property
from leibniz.gates.minmax_decided import classify_identity
from leibniz.gates.mixed_modulus_decided import classify_mixed
from leibniz.gates.power_mod_decided import _multiplicative_order, classify_power
from leibniz.propositio import Expressio
from leibniz.providers.boolean_prover import boolean_law
from leibniz.providers.minmax_prover import minmax_law
from leibniz.providers.mixed_modulus_prover import mixed_law
from leibniz.providers.power_mod_prover import power_law
from leibniz.providers.residue_prover import residue_law
from leibniz.structural import congruence_signature, is_coefficient_degenerate
from leibniz.verifiers import LeanVerifier

IMPORTS = ("Mathlib.Tactic",)
ROUTERS = [("power_mod", classify_power, power_law), ("minmax", classify_identity, minmax_law),
           ("boolean", classify_boolean, boolean_law), ("mixed", classify_mixed, mixed_law),
           ("lean_decided", classify_property, residue_law)]


# --- the independent oracle -------------------------------------------------------------------------

def _vars(cp: str) -> list[str]:
    t = ast.parse(cp.replace("^", "**"), mode="eval").body
    return sorted({n.id for n in ast.walk(t) if isinstance(n, ast.Name) and n.id not in ("min", "max")})


def _moduli(cp: str) -> set[int]:
    t = ast.parse(cp.replace("^", "**"), mode="eval").body
    return {n.right.value for n in ast.walk(t)
            if isinstance(n, ast.BinOp) and isinstance(n.op, ast.Mod) and isinstance(n.right, ast.Constant)}


def oracle_true(cp: str, mode: str, period: int = 0) -> bool:
    """True iff cp holds for EVERY non-negative assignment: modular claims exactly over one lcm
    period per variable; power-mod exactly over one multiplicative period (+ slack); min/max over a
    [0,13) grid (dense enough to refute a false identity)."""
    vs = _vars(cp)
    cpx = cp.replace("^", "**")
    if mode == "grid":
        rng = range(13)
    elif mode == "power":
        rng = range(max(2 * period + 2, 8))
    else:
        ms = _moduli(cp)
        rng = range(math.lcm(*ms) if ms else 2)
    for pt in itertools.product(rng, repeat=len(vs)):
        if not eval(cpx, {"__builtins__": {}}, dict(zip(vs, pt), min=min, max=max)):  # noqa: S307
            return False
    return True


# --- candidate families (parameterized enumeration; truth decided by the oracle, never assumed) -----

def gen_power_mod():
    """The NEW fragment: for each (base, m) with gcd=1 and small order, the missed-residue facts
    (`base^n % m != c` for c outside the cycle) and the exact cycle residue-set."""
    for base in (2, 3, 5, 6, 7, 10):
        for m in range(3, 41):
            ordv = _multiplicative_order(base, m)
            if ordv is None or not (2 <= ordv <= 10):
                continue
            cyc = sorted({pow(base, k, m) for k in range(ordv)})
            missed = [c for c in range(m) if c not in cyc]
            if missed:
                c = missed[len(missed) // 2]
                yield f"{base}**n % {m} != {c}", "power", ordv
            if 3 <= len(cyc) <= 6:
                yield " or ".join(f"{base}**n % {m} == {c}" for c in cyc), "power", ordv


_POLY2 = ["a*b*(a*a - b*b)", "a*b*(a**4 - b**4)", "(a + b)**3 - a**3 - b**3",
          "(a + b)**5 - a**5 - b**5", "a**3*b - a*b**3", "a*a*b*b*(a*a - b*b)",
          "(a - b)*(a + b)*(a*b + 1)", "a**4 + b**4 - a*a*b*b", "(a*a + a)*(b*b + b)",
          "a**5*b - a*b**5", "(a + b)**7 - a**7 - b**7"]
_POLY3 = ["(a + b + c)**3 - a**3 - b**3 - c**3", "a*b*c*(a + b + c)",
          "(a - b)*(b - c)*(a - c)", "a*a + b*b + c*c", "(a + b)*(b + c)*(a + c)"]


def gen_residue():
    """Multivariable polynomial congruences: exact residue sets computed by enumeration, emitted as
    a missed-residue neq (the sharpest single-atom fact) or a small residue-set."""
    for poly, nv in [(p, 2) for p in _POLY2] + [(p, 3) for p in _POLY3]:
        for m in (3, 4, 5, 7, 8, 9, 12, 16):
            vs = ["a", "b", "c"][:nv]
            residues = set()
            for pt in itertools.product(range(m), repeat=nv):
                residues.add(eval(poly.replace("^", "**"), {"__builtins__": {}}, dict(zip(vs, pt))) % m)  # noqa: S307
            missed = sorted(set(range(m)) - residues)
            if missed:
                yield f"({poly}) % {m} != {missed[len(missed) // 2]}", "modular", 0
            if 2 <= len(residues) <= 4 and len(residues) < m:
                yield " or ".join(f"({poly}) % {m} == {c}" for c in sorted(residues)), "modular", 0


def gen_minmax():
    """min/max identities beyond the corpus staples: coefficient combinations of the symmetric
    functions, oracle-filtered for truth."""
    cands = [
        "max(a,b)**2 - min(a,b)**2 == (a + b)*max(a,b) - (a + b)*min(a,b)",
        "max(a,b)**3 - min(a,b)**3 == (max(a,b) - min(a,b))*(a**2 + a*b + b**2)",
        "max(a,b)*min(a,b)*(max(a,b) + min(a,b)) == a*b*(a + b)",
        "max(a,b)**2 + max(a,b)*min(a,b) + min(a,b)**2 == a**2 + a*b + b**2",
        "(max(a,b) - min(a,b))**2 == a**2 - 2*a*b + b**2",
        "max(a,b)**4 + min(a,b)**4 == a**4 + b**4",
        "(max(a,b) + min(a,b))**2 - 2*max(a,b)*min(a,b) == a**2 + b**2",
        "max(a,b)**2*min(a,b) + max(a,b)*min(a,b)**2 == a**2*b + a*b**2",
        "(max(a,b)+min(a,b)) + (max(b,c)+min(b,c)) + (max(a,c)+min(a,c)) == 2*a + 2*b + 2*c",
    ]
    for cp in cands:
        yield cp, "grid", 0


def gen_boolean_mixed():
    """Biconditionals: same-modulus (boolean fragment) and mixed-modulus characterizations,
    truth-filtered by the oracle."""
    cands = [
        "((a*b) % 9 == 0) == ((a % 3 == 0) and (b % 3 == 0))",
        "((a*a*b*b) % 9 == 0) == ((a % 3 == 0) or (b % 3 == 0))",
        "((a*a - b*b) % 8 == 0) == ((a % 2 == 0) == (b % 2 == 0))",
        "((a*a + b*b) % 8 == 2) == ((a % 2 == 1) and (b % 2 == 1))",
        "((a*b*(a + b)) % 2 == 0) == ((a % 2 == 0) or (b % 2 == 0) or ((a + b) % 2 == 0))",
        "((a*a*a) % 9 == 1) == ((a % 9 == 1) or (a % 9 == 4) or (a % 9 == 7))",
        "((a*a) % 16 == 4) == ((a % 8 == 2) or (a % 8 == 6))",
        "((a + b)**2 % 8 == 4) == ((a + b) % 4 == 2)",
        "((a*a + b*b) % 4 == 0) == ((a % 2 == 0) and (b % 2 == 0))",
        "((a*a - b*b) % 3 == 0) == ((a % 3 == b % 3) or ((a + b) % 3 == 0))",
    ]
    for cp in cands:
        yield cp, "modular", 0


def main() -> int:
    cap = int(sys.argv[1]) if len(sys.argv) > 1 else 40
    corpus = CorpusBackend.from_json()
    stats = {"generated": 0, "oracle_false": 0, "unrouted": 0, "degenerate": 0,
             "known": 0, "dup_signature": 0, "cheap_survivors": 0}
    seen_sigs: set = set()
    survivors: list[tuple[str, str, str]] = []          # (fragment, cp, mode)

    for gen in (gen_power_mod, gen_residue, gen_minmax, gen_boolean_mixed):
        for cp, mode, period in gen():
            stats["generated"] += 1
            try:
                if not oracle_true(cp, mode, period):
                    stats["oracle_false"] += 1
                    continue
            except Exception:
                stats["oracle_false"] += 1
                continue
            hits = [(name, law) for name, classify, law in ROUTERS if classify(cp)]
            if len(hits) != 1:
                stats["unrouted"] += 1
                continue
            if is_coefficient_degenerate(cp):
                stats["degenerate"] += 1
                continue
            if corpus.structural_known(cp) is not None:
                stats["known"] += 1
                continue
            sig = congruence_signature(cp)
            key = sig if sig is not None else cp
            if key in seen_sigs:
                stats["dup_signature"] += 1
                continue
            seen_sigs.add(key)
            stats["cheap_survivors"] += 1
            survivors.append((hits[0][0], cp, mode))

    print("=== ORIGINATION HUNT — cheap-screen funnel ===")
    for k, v in stats.items():
        print(f"  {k:16} {v}")
    # diversify the kernel budget ROUND-ROBIN across fragments (else one family eats the cap)
    by_frag: dict = {}
    for frag, cp, mode in survivors:
        by_frag.setdefault(frag, []).append((frag, cp, mode))
    interleaved: list = []
    idx = 0
    while len(interleaved) < len(survivors):
        added = False
        for frag in sorted(by_frag):
            if idx < len(by_frag[frag]):
                interleaved.append(by_frag[frag][idx])
                added = True
        if not added:
            break
        idx += 1
    survivors = interleaved
    print("  survivors by fragment: " + ", ".join(f"{f}={len(v)}" for f, v in sorted(by_frag.items())))
    print(f"\n  kernel budget: {min(len(survivors), cap)} of {len(survivors)} cheap survivors (round-robin)\n")

    if not available():
        print("Lean kernel unavailable — stopping at the cheap screens.")
        return 1

    LAW = dict((name, law) for name, _c, law in ROUTERS)
    be = LeanReplBackend(timeout_s=170)
    lean = LeanVerifier(be)
    gate_novel: list[tuple[str, str]] = []
    n_trivial = n_unprovable = 0
    try:
        for frag, cp, mode in survivors[:cap]:
            vs = _vars(cp)
            cd = " and ".join(f"{v} >= 0" for v in vs)
            gen_out = LAW[frag](f"hunt_{len(gate_novel)}", cd, cp)
            if gen_out is None:
                n_unprovable += 1
                continue
            thm, proof = gen_out
            expr = Expressio(theorem_src=thm, imports=IMPORTS)
            if lean.is_trivial(expr):                    # 6. the stock tactic ladder closes it → vacuous
                n_trivial += 1
                print(f"  -- is_trivial   [{frag}] {cp[:64]}")
                continue
            if not be.check_proof(expr, proof):          # 7. must be promulgable-grade
                n_unprovable += 1
                print(f"  -- unprovable   [{frag}] {cp[:64]}")
                continue
            gate_novel.append((frag, cp))
            print(f"  ** GATE-NOVEL   [{frag}] {cp[:64]}")
    finally:
        be.close()

    print("\n=== VERDICT ===")
    print(f"  kernel-screened : {min(len(survivors), cap)}")
    print(f"  is_trivial      : {n_trivial}")
    print(f"  unprovable      : {n_unprovable}")
    print(f"  GATE-NOVEL + kernel-provable survivors: {len(gate_novel)}")
    for frag, cp in gate_novel:
        print(f"    [{frag:12}] {cp}")
    print("\nCaveat (ADR 0063): gate-novelty is novelty per the mechanical gate and the curated corpus —")
    print("NOT absolute mathematical novelty. Each survivor still requires an honest textbook-derivability")
    print("assessment before any origination claim.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
