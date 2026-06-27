"""Probe β pilot — finite-witness record factory, mechanism validation (constant-weight codes).

The witnesses' best remaining autonomous lever: replace LLM theorem-IDEATION with SEARCH over a
finite object space whose novelty is OBJECTIVE (beats a public table-of-record). The witness is a
finite combinatorial object; a checker verifies it; novelty = improves the best-known entry. This
respects propose/decide (untrusted search proposes; a checker decides) and gives the objective
novelty criterion the enumerate-and-decide probes lacked.

Domain: binary CONSTANT-WEIGHT CODES. A(n,d,w) = max number of binary length-n weight-w vectors with
pairwise Hamming distance >= d. A witness is a list of w-subsets of {0..n-1}; two weight-w words are
at distance 2*(w - |A∩B|), so distance >= d  <=>  |A∩B| <= w - ceil(d/2).

This PILOT answers the measure-before-build question: can untrusted search even REACH known optima
(validating the end-to-end search -> verify -> compare-to-oracle pipeline) before we invest in the
trusted Lean witness-checker + an automated Brouwer-table oracle + heavy CP-SAT search? It uses ONLY
cells whose optimum is provably/derivably known, so the oracle is correct by construction (the α
lesson: a wrong table-of-record poisons every novelty claim).

NO trust claim is made here: the Python verifier is a stand-in for the eventual Lean kernel re-check;
the search is untrusted. Pure stdlib + deterministic (seeded LCG, no external RNG).
"""
from __future__ import annotations

import json
import sys
from itertools import combinations
from pathlib import Path


# --- the (eventual-Lean) reference verifier: the trust-critical re-check, mirrored in Python ----
def verify_cwc(code: list[frozenset], n: int, d: int, w: int) -> tuple[bool, str]:
    """True iff `code` is a valid (n,d,w) constant-weight code: every codeword is a w-subset of
    {0..n-1}, all distinct, pairwise Hamming distance >= d. Returns (ok, reason)."""
    universe = set(range(n))
    for c in code:
        if len(c) != w or not c <= universe:
            return False, f"codeword {sorted(c)} not a w-subset of [0,{n})"
    if len({frozenset(c) for c in code}) != len(code):
        return False, "duplicate codewords"
    cl = list(code)
    for i in range(len(cl)):
        for j in range(i + 1, len(cl)):
            dist = 2 * (w - len(cl[i] & cl[j]))
            if dist < d:
                return False, f"pair {sorted(cl[i])},{sorted(cl[j])} at distance {dist} < {d}"
    return True, "ok"


# --- the oracle: ONLY provably-known optima (correct by construction) ---------------------------
# Each entry: (n,d,w) -> (best_known A(n,d,w), provenance). Kept to cells with a derivation we can
# stand behind, so the pilot's "matched the record" claims are sound. The FULL build must replace
# this with an automated parse of Brouwer's table-of-record (the α false-negative-detector lesson).
def _packing(n, w):       # A(n,2w,w) = floor(n/w): disjoint w-blocks (intersection 0 => dist 2w)
    return n // w
def _matching(n):         # A(n,4,2) = floor(n/2): disjoint pairs
    return n // 2


ORACLE: dict[tuple, tuple] = {
    (6, 4, 2): (_matching(6), "matching floor(6/2)"),
    (8, 4, 2): (_matching(8), "matching floor(8/2)"),
    (10, 4, 2): (_matching(10), "matching floor(10/2)"),
    (9, 6, 3): (_packing(9, 3), "packing floor(9/3) disjoint triples"),
    (12, 6, 3): (_packing(12, 3), "packing floor(12/3)"),
    (8, 8, 4): (_packing(8, 4), "packing floor(8/4)"),
    (7, 4, 3): (7, "Steiner triple system STS(7)=Fano; Johnson bound A(7,4,3)<=7 => optimal"),
    (6, 4, 3): (4, "documented A(6,4,3)=4 (small CWC table)"),
}


# --- untrusted search: deterministic greedy + restarts + local repair (pure stdlib) ------------
class _LCG:
    """Tiny deterministic PRNG (no Math.random / os.urandom — reproducible pilot)."""

    def __init__(self, seed):
        self.s = seed & 0xFFFFFFFF

    def nxt(self):
        self.s = (1103515245 * self.s + 12345) & 0x7FFFFFFF
        return self.s

    def shuffled(self, xs):
        a = list(xs)
        for i in range(len(a) - 1, 0, -1):
            j = self.nxt() % (i + 1)
            a[i], a[j] = a[j], a[i]
        return a


def _compatible(c, code, w, d):
    cap = w - (d + 1) // 2                      # max allowed |intersection|
    return all(len(c & e) <= cap for e in code)


def search_cwc(n: int, d: int, w: int, target: int, restarts: int = 400) -> list[frozenset]:
    """Greedy-with-random-restart search for an (n,d,w) code of size >= target. Returns the best
    code found (untrusted; the verifier checks it)."""
    allcw = [frozenset(c) for c in combinations(range(n), w)]
    best: list[frozenset] = []
    rng = _LCG(0x9E3779B1 ^ (n * 73856093) ^ (d * 19349663) ^ (w * 83492791))
    for r in range(restarts):
        order = rng.shuffled(allcw)
        code: list[frozenset] = []
        for c in order:
            if _compatible(c, code, w, d):
                code.append(c)
        if len(code) > len(best):
            best = code
            if len(best) >= target:
                break
    return best


# --- pilot driver -----------------------------------------------------------------------------
def run(out_path: Path) -> dict:
    rows = []
    for (n, d, w), (best_known, prov) in sorted(ORACLE.items()):
        code = search_cwc(n, d, w, best_known)
        ok, reason = verify_cwc(code, n, d, w)
        found = len(code) if ok else 0
        rows.append({"n": n, "d": d, "w": w, "best_known": best_known, "found": found,
                     "verified": ok, "matched": ok and found >= best_known,
                     "gap": best_known - found, "provenance": prov,
                     "verify_reason": reason})
    matched = sum(1 for r in rows if r["matched"])
    summary = {"cells": len(rows), "matched_known_optimum": matched,
               "reproduced_all": matched == len(rows),
               "rows": rows}
    out_path.write_text(json.dumps(summary, indent=2))
    return summary


def main() -> int:
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("probe_beta_out/cwc_pilot.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    s = run(out)
    print(f"[probe-β pilot] constant-weight-code mechanism validation -> {out}")
    print(f"  cells: {s['cells']} | reached known optimum: {s['matched_known_optimum']}/{s['cells']}")
    for r in s["rows"]:
        tag = "OK " if r["matched"] else ("near" if r["verified"] else "BAD")
        print(f"   [{tag}] A({r['n']},{r['d']},{r['w']})  best_known={r['best_known']:3d} "
              f"found={r['found']:3d}  gap={r['gap']:+d}   ({r['provenance']})")
    print(f"  verifier sound on all found codes: {all(r['verified'] for r in s['rows'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
