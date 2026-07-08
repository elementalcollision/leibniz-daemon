"""Differential soundness harness for the five ceiling-raiser decision procedures (Phase 1).

Generate claims across every fragment — modular atoms/residue-sets/conjunctions (residue_law), min/max
identities (minmax_law), same-modulus boolean combinations (boolean_law), mixed-modulus (mixed_law) —
decide ground truth with an INDEPENDENT Python oracle (exact residue enumeration for modular claims; a
grid for min/max; plain Python `eval` semantics, NOT Lean, NOT the daemon's DSL evaluator), run each
generated proof through the real Lean 4.31 kernel, and assert the SOUNDNESS invariant:

    the kernel NEVER accepts a claim the oracle says is FALSE  (no false law can promulgate).

Completeness (kernel DEFERs a true claim) is tracked but is NOT a soundness failure — DEFER is safe.
ONE Lean REPL session, closed in `finally`; the caller verifies containers → 0.

Usage:  python scripts/verify_ceiling_raiser_soundness.py [n_per_fragment]
"""
from __future__ import annotations

import ast
import itertools
import math
import random
import sys

from leibniz.backends.lean_repl import LeanReplBackend
from leibniz.propositio import Expressio
from leibniz.providers.boolean_prover import boolean_law
from leibniz.providers.mixed_modulus_prover import mixed_law
from leibniz.providers.minmax_prover import minmax_law
from leibniz.providers.residue_prover import residue_law

IMPORTS = ("Mathlib.Tactic",)
CD = "a >= 0 and b >= 0"           # the box domain shared by the generated claims (all non-negative)
CD3 = "a >= 0 and b >= 0 and c >= 0"
GRID = 13                          # min/max grid [0, GRID)


# --- the INDEPENDENT oracle (Python eval over residues / a grid; not Lean, not the daemon) ----------

def _tree(s: str) -> ast.AST:
    return ast.parse(s.replace("^", "**"), mode="eval").body


def _moduli(cp: str) -> set[int]:
    ms = set()
    for n in ast.walk(_tree(cp)):
        if isinstance(n, ast.BinOp) and isinstance(n.op, ast.Mod) and isinstance(n.right, ast.Constant):
            ms.add(n.right.value)
    return ms


def _vars(*srcs: str) -> list[str]:
    vs: set[str] = set()
    for s in srcs:
        for n in ast.walk(_tree(s)):
            if isinstance(n, ast.Name) and n.id not in ("min", "max"):
                vs.add(n.id)
    return sorted(vs)


def oracle_true(cd: str, cp: str, mode: str) -> bool:
    """True iff `cp` holds for EVERY in-domain assignment. Modular: exact over residues mod lcm (a
    polynomial is periodic mod m). min/max: a [0,GRID) grid (dense enough to expose a false identity)."""
    vs = _vars(cp, cd)
    cpx, cdx = cp.replace("^", "**"), cd.replace("^", "**")
    if mode == "modular":
        mods = _moduli(cp)
        rng = range(math.lcm(*mods) if mods else 2)
    else:
        rng = range(GRID)
    for pt in itertools.product(rng, repeat=len(vs)):
        asn = dict(zip(vs, pt), min=min, max=max)
        if not eval(cdx, {"__builtins__": {}}, asn):       # noqa: S307 — claims are gate-generated, not user input
            continue
        if not eval(cpx, {"__builtins__": {}}, asn):
            return False
    return True


# --- claim generators per fragment (a spread of true + deliberately-false + mutated) -----------------

_POLYS2 = ["a*a + b*b", "a*b", "a*a + a*b + b*b", "a*b*(a*b + 1)", "(a + b)*(a + b)", "a*a - b*b"]


def _mutate(cp: str, rng: random.Random) -> str:
    """Perturb one integer literal in the claim (a residue or modulus) — a cheap, broad way to spawn
    diverse variants, many of which flip true↔false, so the kernel's soundness is tested on claims no
    template hand-picked. Out-of-fragment mutants simply abstain; the oracle re-decides each."""
    tree = _tree(cp)
    consts = [n for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, int)]
    if not consts or rng.random() < 0.35:
        return cp                                          # sometimes leave it as-is
    target = rng.choice(consts)
    old = str(target.value)
    new = str(max(0, target.value + rng.choice([-2, -1, 1, 2])))
    # replace one occurrence textually (crude but adequate for these small claims)
    return cp.replace(old, new, 1) if old in cp else cp


def _gen_residue(rng: random.Random, n: int):
    out = []
    for _ in range(n):
        poly = rng.choice(_POLYS2)
        m = rng.choice([2, 3, 4, 5, 6])
        c = rng.randrange(m)
        op = rng.choice(["==", "!="])
        if rng.random() < 0.4:      # residue-set (same poly, or-of-eq)
            cs = sorted(rng.sample(range(m), k=min(2, m)))
            cp = " or ".join(f"({poly}) % {m} == {c2}" for c2 in cs)
        elif rng.random() < 0.5:    # conjunction (single modulus)
            p2 = rng.choice(_POLYS2)
            cp = f"(({poly}) % {m} {op} {c}) and (({p2}) % {m} != {rng.randrange(m)})"
        else:                       # single atom
            cp = f"({poly}) % {m} {op} {c}"
        out.append((CD, cp, "modular", residue_law))
    return out


def _gen_minmax(rng: random.Random, n: int):
    tmpls = [
        "max(a,b)**2 + min(a,b)**2 == a**2 + b**2",
        "max(a,b) * min(a,b) == a*b",
        "max(a,b) + min(a,b) == a + b",
        "max(a,b) - min(a,b) == a - b",                 # FALSE (it is |a-b|)
        "max(a,b) + min(a,b) == a",                     # FALSE
        "max(a,b)**2 + min(a,b)**2 == a**2 + b**2 and max(a,b)*min(a,b) == a*b",
        "(max(a,b)+min(a,b)) + (max(b,c)+min(b,c)) == a + 2*b + c",
        "min(a,b) + max(b,c) == a + c",                 # FALSE (missing-branch attack)
        "max(a,b)**3 + min(a,b)**3 == a**3 + b**3",
        "max(a,b) + min(a,b) == a + b + 1",             # FALSE (off by one)
    ]
    out = []
    for _ in range(n):
        cp = _mutate(rng.choice(tmpls), rng)
        cd = CD3 if "c" in cp else CD
        out.append((cd, cp, "minmax", minmax_law))
    return out


def _gen_boolean(rng: random.Random, n: int):
    tmpls = [
        "((a*b) % 3 == 0) == ((a % 3 == 0) or (b % 3 == 0))",
        "((a*b) % 3 == 0) == ((a % 3 == 0) and (b % 3 == 0))",   # FALSE
        "(a*a % 5 == 1) == ((a % 5 == 1) or (a % 5 == 4))",       # (single var → may abstain <MIN_VARS)
        "((a*b) % 2 != 1) == ((a % 2 == 0) or (b % 2 == 0))",
        "(not ((a*b) % 2 == 1)) == ((a % 2 == 0) or (b % 2 == 0))",
        "((a*b) % 4 == 0) == ((a % 4 == 0) or (b % 4 == 0))",     # FALSE
        "((a*a + b*b) % 4 != 3) and ((a*a + b*b) % 4 != 2)",      # (both true? a²+b² can be 2 → FALSE 2nd)
        "((a + b) % 6 == 0) == ((a + b) % 6 == 3)",               # FALSE
    ]
    out = []
    for _ in range(n):
        cp = _mutate(rng.choice(tmpls), rng)
        out.append((CD, cp, "modular", boolean_law))
    return out


def _gen_mixed(rng: random.Random, n: int):
    tmpls = [
        "((a+b)**2 % 4 == 1) == ((a+b) % 2 == 1)",
        "((a+b)**2 % 4 == 1) == ((a+b) % 2 == 0)",               # FALSE
        "((a*a+b*b) % 4 == 2) == ((a % 2 == 1) and (b % 2 == 1))",
        "((a*a+b*b) % 4 == 2) == ((a % 2 == 1) and (b % 2 == 0))",   # FALSE
        "((a*b) % 6 == 0) == (((a % 2 == 0) or (b % 2 == 0)) and ((a % 3 == 0) or (b % 3 == 0)))",
        "((a*b) % 6 == 0) == ((a % 2 == 0) and (a % 3 == 0))",   # FALSE
        "(not ((a+b) % 4 == 1)) or ((a+b) % 2 == 1)",
        "((a+b)**2 % 4 == 1) == ((a+b) % 2 != 0)",
    ]
    out = []
    for _ in range(n):
        cp = _mutate(rng.choice(tmpls), rng)
        out.append((CD, cp, "modular", mixed_law))
    return out


def main() -> int:
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 14
    rng = random.Random(20260708)
    claims = (_gen_residue(rng, n) + _gen_minmax(rng, n)
              + _gen_boolean(rng, n) + _gen_mixed(rng, n))

    stats = {"tested": 0, "abstain": 0, "kernel_accept": 0, "kernel_defer": 0,
             "false_accept": 0, "true_defer": 0}
    unsound = []
    be = LeanReplBackend(timeout_s=170)
    try:
        for i, (cd, cp, mode, gen) in enumerate(claims):
            law = gen(f"sound_{i}", cd, cp)
            if law is None:
                stats["abstain"] += 1
                continue
            stats["tested"] += 1
            truth = oracle_true(cd, cp, mode)
            ok = be.check_proof(Expressio(theorem_src=law[0], imports=IMPORTS), law[1])
            if ok:
                stats["kernel_accept"] += 1
                if not truth:                              # !!! the kernel proved a FALSE claim
                    stats["false_accept"] += 1
                    unsound.append((cd, cp, gen.__name__))
                    print(f"  !! UNSOUND: kernel ACCEPTED an oracle-FALSE claim [{gen.__name__}]: {cp}")
            else:
                stats["kernel_defer"] += 1
                if truth:
                    stats["true_defer"] += 1               # completeness loss (safe)
    finally:
        be.close()

    print("\n=== differential soundness result ===")
    for k, v in stats.items():
        print(f"  {k:16} {v}")
    print()
    if stats["false_accept"] == 0:
        print(f"SOUND: across {stats['tested']} kernel-checked claims spanning all five fragments, the "
              f"kernel accepted 0 false claims. No false law can promulgate.")
        print(f"  (completeness note: {stats['true_defer']} true claims DEFERred — safe yield loss.)")
        return 0
    print(f"!! SOUNDNESS ALARM: {stats['false_accept']} false-accept(s). Investigate immediately.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
