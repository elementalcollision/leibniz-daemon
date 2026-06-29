"""Covering-design witness verifier + core-Lean renderer (ADR 0043, Track B1 — the 2nd amplification domain).

A (v,k,t)-covering design is a collection of k-subsets ("blocks") of {0..v-1} such that EVERY t-subset
of {0..v-1} is contained in at least one block. A covering of size B is a witness that the covering
number C(v,k,t) <= B (an UPPER bound — fewer blocks is better, the mirror image of CWC's lower bound).

This module is the covering-design analog of probe_beta_cwc_pilot.py's verify_cwc / render_cwc_lean:
    blocks --> verify_covering   (UNTRUSTED pre-check; refuses to render a false theorem)
           --> render_covering_lean (core Lean 4, no Mathlib; kernel-`decide`-able)

SOUNDNESS — completeness is BY CONSTRUCTION, not trusted. The Lean checker GENERATES every t-subset of
{0..v-1} itself (the `combs` helper) and checks each is covered; the witness supplies only the blocks.
A malicious witness therefore cannot omit an uncovered t-subset to sneak a false upper bound past the
kernel. Verified against the real Lean 4.31 kernel: a valid STS(9) covering -> True; a covering with one
block removed (an uncovered pair) -> False.

Pure stdlib.
"""
from __future__ import annotations

from itertools import combinations


def verify_covering(blocks: list[frozenset], v: int, k: int, t: int) -> tuple[bool, str]:
    """True iff `blocks` is a valid (v,k,t)-covering: every block is a k-subset of {0..v-1}, and every
    t-subset of {0..v-1} is contained in some block. Returns (ok, reason). UNTRUSTED pre-check."""
    universe = set(range(v))
    for b in blocks:
        if len(b) != k or not b <= universe:
            return False, f"block {sorted(b)} is not a k-subset of [0,{v})"
    block_sets = [set(b) for b in blocks]
    for s in combinations(range(v), t):
        ss = set(s)
        if not any(ss <= b for b in block_sets):
            return False, f"t-subset {list(s)} is not covered by any block"
    return True, "ok"


# Locked, kernel-validated core-Lean checker. `combs t (List.range v)` enumerates EVERY t-subset in the
# kernel, so coverage completeness cannot be faked; `validCovering ... = true` proves C(v,k,t) <= B.
_LEAN_HELPERS = """\
-- covering-design witness checker (core Lean 4; no Mathlib)
def distinctSyms (c : List Nat) : Bool := c.all (fun x => (c.filter (fun y => x == y)).length == 1)
def blockOK (b : List Nat) (v k : Nat) : Bool :=
  (b.length == k) && b.all (fun x => decide (x < v)) && distinctSyms b
def covered (s : List Nat) (blocks : List (List Nat)) : Bool :=
  blocks.any (fun b => s.all (fun x => b.contains x))
def combs : Nat → List Nat → List (List Nat)
  | 0,     _       => [[]]
  | _+1,   []      => []
  | (k+1), (x::xs) => (combs k xs).map (fun c => x :: c) ++ combs (k+1) xs
def validCovering (blocks : List (List Nat)) (v k t B : Nat) : Bool :=
  (blocks.length == B) && blocks.all (fun b => blockOK b v k) &&
  (combs t (List.range v)).all (fun s => covered s blocks)"""


def render_covering_lean(v: int, k: int, t: int, blocks, thm_name: str | None = None) -> str:
    """Render a self-contained, core-Lean, kernel-`decide`-able theorem `C(v,k,t) <= |blocks|`, witness
    inlined. Refuses to render a FALSE theorem (the Python pre-check; the kernel would reject it too)."""
    block_sets = [frozenset(b) for b in blocks]
    ok, reason = verify_covering(block_sets, v, k, t)
    if not ok:
        raise ValueError(f"refusing to render a false covering theorem: {reason}")
    B = len(block_sets)
    name = thm_name or f"cov_{v}_{k}_{t}_le_{B}"
    lits = "[" + ", ".join("[" + ", ".join(str(x) for x in sorted(b)) + "]"
                           for b in block_sets) + "]"
    return (f"{_LEAN_HELPERS}\n\ntheorem {name} :\n"
            f"    validCovering {lits} {v} {k} {t} {B} = true := by\n  decide\n")
