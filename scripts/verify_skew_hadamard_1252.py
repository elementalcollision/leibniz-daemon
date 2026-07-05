"""Independent verification of the bordered skew-Hadamard difference family behind the order-1252 skew-Hadamard
matrix of Karoui (2026), arXiv:2602.16089 — a construction that fills a reported-missing Hadamard order.

The paper builds a skew-Hadamard matrix of order 1252 = 2(5^4 + 1) by a bordered Goethals–Seidel array over a
bordered skew-Hadamard difference family (SHDF) {D0, D1} in the additive group of GF(5^4), whose blocks are
unions of cyclotomic classes of order N = 16: with a primitive g and C_i = g^i·<g^16> (|C_i| = 39),
  D0 = ∪_{i in I0} C_i,  D1 = ∪_{i in I1} C_i,   I0 = {4..11}, I1 = {0..7}  (relative to the paper's g).
The two structural prerequisites the paper proves — and that make the Goethals–Seidel array skew-Hadamard —
are checked here EXACTLY over the real field:
  (S)  D0 is SKEW:  for every x != 0, exactly one of x, -x lies in D0   (so |D0| = (625-1)/2 = 312);
  (A)  the ±1 periodic autocorrelations sum to a constant:  A_{D0}(w) + A_{D1}(w) = -2  for all w != 0,
       where A_D(w) = Σ_{x in GF(5^4)} ψ_D(x) ψ_D(x+w),  ψ_D(x) = +1 if x in D else -1.
Given (S)+(A) a skew-Hadamard matrix of order 2(v+1) = 1252 EXISTS by the cited Goethals–Seidel lemma
(Colbourn & Dinitz 2006; Momihara & Xiang 2018) — the paper's headline claim.

We build GF(5^4) from scratch (an irreducible primitive quartic over GF(5), so x is a primitive element),
form the cyclotomic classes, and verify (S)+(A). The paper's index sets are stated relative to ITS choice of
primitive element; a different primitive g relabels the 16 classes, so we accept ANY cyclic offset s of the
paper's window structure (I1 = {s..s+7}, I0 = I1 + 4) — a relabeling, not a different family — and report
which offset realizes the SHDF. LLMs propose nothing; this is exact finite-field arithmetic. Tier audit,
verification-AMPLIFICATION; no trust surface.

Run:  python scripts/verify_skew_hadamard_1252.py
"""
from __future__ import annotations

import json
from itertools import product
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
OUT = _ROOT / "docs" / "results" / "skew_hadamard_1252_verification.json"

P = 5
DEG = 4
Q = P ** DEG          # 625
GORD = Q - 1          # 624 = 16 * 39
N = 16                # cyclotomic order
CLASS_SIZE = GORD // N  # 39


# --- GF(5^4) as GF(5)[x]/(f), elements are 4-tuples (c0,c1,c2,c3) = c0 + c1 x + c2 x^2 + c3 x^3 ---
def _poly_mul(a, b):
    """Multiply two GF(5^4) elements mod x^4 (reduction applied by caller's field table)."""
    r = [0] * (2 * DEG - 1)
    for i, ai in enumerate(a):
        if ai:
            for j, bj in enumerate(b):
                r[i + j] = (r[i + j] + ai * bj) % P
    return r


def _reduce(r, red):
    """Reduce a degree<7 polynomial r by the reduction table red (x^k for k>=DEG in terms of low powers)."""
    r = list(r) + [0] * (2 * DEG - 1 - len(r))
    for k in range(2 * DEG - 2, DEG - 1, -1):
        c = r[k] % P
        if c:
            r[k] = 0
            for j, coeff in enumerate(red[k]):
                r[j] = (r[j] + c * coeff) % P
    return tuple(r[:DEG])


def _find_field():
    """Find a monic irreducible quartic f over GF(5) for which x is a primitive element (order 624).
    Returns (mul, elements, powtable, logtable) with mul(a,b) the field product."""
    for coeffs in product(range(P), repeat=DEG):        # f = x^4 + c3 x^3 + c2 x^2 + c1 x + c0
        c0, c1, c2, c3 = coeffs
        if c0 == 0:
            continue
        # reduction: x^k for k=DEG..2DEG-2 as low-degree tuples; x^4 = -(c0 + c1 x + c2 x^2 + c3 x^3)
        red = {}
        base = [(-c0) % P, (-c1) % P, (-c2) % P, (-c3) % P]
        red[DEG] = base[:]
        for k in range(DEG + 1, 2 * DEG - 1):
            prev = red[k - 1]                            # x^(k-1) = Σ prev[j] x^j
            shifted = [0] + prev[:]                       # x * x^(k-1)
            hi = shifted[DEG] if len(shifted) > DEG else 0
            low = shifted[:DEG]
            if hi:
                for j in range(DEG):
                    low[j] = (low[j] + hi * base[j]) % P
            red[k] = low

        def mul(a, b, red=red):
            return _reduce(_poly_mul(a, b), red)

        # order of x
        x = (0, 1, 0, 0)
        cur = (1, 0, 0, 0)
        pw = [cur]
        for _ in range(GORD):
            cur = mul(cur, x)
            pw.append(cur)
        if pw[GORD] == (1, 0, 0, 0) and all(pw[d] != (1, 0, 0, 0) for d in _proper_divisors(GORD)):
            powtable = pw[:GORD]
            logtable = {e: i for i, e in enumerate(powtable)}
            return mul, powtable, logtable, coeffs
    raise RuntimeError("no primitive quartic found (impossible over GF(5))")


def _proper_divisors(n):
    return [n // p for p in (2, 3, 13) if n % p == 0]     # 624 = 2^4·3·13; check maximal proper divisors


def _add(a, b):
    return tuple((a[i] + b[i]) % P for i in range(DEG))


def verify() -> dict:
    mul, powtable, logtable, fpoly = _find_field()
    elements = [tuple(c) for c in product(range(P), repeat=DEG)]
    zero = (0, 0, 0, 0)
    log16 = {e: (logtable[e] % N) for e in powtable}       # class index of each nonzero element

    def blocks_for(offset: int):
        i1 = {(offset + k) % N for k in range(8)}
        i0 = {(offset + 4 + k) % N for k in range(8)}
        d0 = frozenset(e for e in powtable if log16[e] in i0)
        d1 = frozenset(e for e in powtable if log16[e] in i1)
        return i0, i1, d0, d1

    def is_skew(d0):
        for e in powtable:
            neg = tuple((-c) % P for c in e)
            if (e in d0) == (neg in d0):
                return False
        return True

    def autocorr_ok(d0, d1):
        psi0 = {e: (1 if e in d0 else -1) for e in elements}
        psi1 = {e: (1 if e in d1 else -1) for e in elements}
        for w in elements:
            if w == zero:
                continue
            s = 0
            for x in elements:
                xw = _add(x, w)
                s += psi0[x] * psi0[xw] + psi1[x] * psi1[xw]
            if s != -2:
                return False, w
        return True, None

    # try the paper's window structure at every cyclic offset (relabeling under the primitive-element choice)
    result = {"field_poly_x4_plus": list(fpoly), "primitive_element": "x", "found_offset": None}
    for offset in range(N):
        i0, i1, d0, d1 = blocks_for(offset)
        skew = is_skew(d0)
        sizes = (len(d0), len(d1))
        if not (skew and sizes == (8 * CLASS_SIZE, 8 * CLASS_SIZE)):
            continue
        ok, bad = autocorr_ok(d0, d1)
        if ok:
            result.update({"found_offset": offset, "I0": sorted(i0), "I1": sorted(i1),
                           "D0_size": sizes[0], "D1_size": sizes[1], "skew": True,
                           "autocorrelation_sum": -2, "shdf_valid": True})
            break
    if result["found_offset"] is None:
        result["shdf_valid"] = False
    return result


def main() -> int:
    print("=== Skew-Hadamard matrix of order 1252 (Karoui 2026, arXiv:2602.16089) — SHDF core verification ===")
    print(f"  building GF(5^4) (|G|={Q}, |G*|={GORD}=16·39), cyclotomic classes of order 16 ...")
    r = verify()
    print(f"  field: x^4 + {r['field_poly_x4_plus']} coeffs (x primitive); classes size {CLASS_SIZE}")
    if r["shdf_valid"]:
        print(f"  offset s={r['found_offset']}: I1={r['I1']}, I0={r['I0']}")
        print(f"  (S) D0 skew: True   |D0|={r['D0_size']}=312, |D1|={r['D1_size']}=312")
        print("  (A) autocorrelation sum A_D0(w)+A_D1(w) = -2 for all 624 nonzero w: True")
        print("  => {D0,D1} is a valid bordered skew-Hadamard difference family")
        print("  => a skew-Hadamard matrix of order 2(5^4+1)=1252 EXISTS (Goethals-Seidel) — paper's claim CONFIRMED")
    else:
        print("  !! could not realize the SHDF at any offset — refusing to certify")

    gate = "GREEN" if r["shdf_valid"] else "RED"
    out = {"gate": gate, "tier": "audit", "ev": "AMPLIFICATION",
           "target": "Karoui (2026), arXiv:2602.16089 — skew-Hadamard matrix of order 1252",
           "verification": r,
           "reading": ("Independent exact-arithmetic verification of the bordered skew-Hadamard difference "
                       "family {D0,D1} over GF(5^4) (cyclotomic classes of order 16) underlying Karoui's "
                       "order-1252 skew-Hadamard matrix: D0 is skew and the ±1 autocorrelations sum to -2 for "
                       "all nonzero w, so a skew-Hadamard matrix of order 1252 exists by Goethals-Seidel — "
                       "confirming the construction that fills the reported-missing order. Verification-"
                       "amplification (audit tier); no trust surface.")}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2) + "\n")
    print(f"\ngate={gate}  tier=audit  ev=AMPLIFICATION\n-> {OUT}")
    return 0 if gate == "GREEN" else 1


if __name__ == "__main__":
    raise SystemExit(main())
