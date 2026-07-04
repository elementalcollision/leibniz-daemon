"""General monomial-ideal normality instrument for k[x,y,z] — stdlib-only, exact.

Generalizes the Problem-41 corner-ideal checker (`prob41_normality_lean.py`, which handles only
I = closure(x^a,y^b,z^c)) to an ARBITRARY monomial ideal given by its generator exponent list. Everything
is decided by the *integral-dependence* definition — no floating-point, no convex-hull library:

  * x^u ∈ I^p            ⟺  some multiset of p generators sums ≤ u (componentwise).
  * x^u ∈ closure(I^p)   ⟺  x^u is integral over I^p  ⟺  ∃ k ≥ 1 : (x^u)^k = x^{ku} ∈ (I^p)^k = I^{pk}.
    (Exact; the search over k terminates — for lattice points the required k is bounded by the
    Newton-polyhedron vertex denominators. `KMAX` is validated against the corner instrument + AM examples.)
  * I is integrally closed  ⟺  no lattice point of closure(I) lies outside I.
  * (Reid–Roberts–Vitulli, d = 3)  I is normal  ⟺  I and I^2 are both integrally closed.

A monomial x^v with v ≤ u lies in the same box, so the search boxes below are bounded by the pure-power
extent of the generators; `box_bound` returns a provably-sufficient cube (a minimal generator of closure(I^p)
cannot exceed p·max_coord in any coordinate). Used to independently verify Ataka–Matsuoka (2026) Example 4.7.
"""
from __future__ import annotations

from itertools import product

KMAX = 8  # integral-dependence search depth (validated: corner instrument + AM 4.5/4.7 agree)


def _le(a, b) -> bool:
    return a[0] <= b[0] and a[1] <= b[1] and a[2] <= b[2]


def in_power(u, gens, p: int) -> bool:
    """x^u ∈ I^p  ⟺  some multiset of exactly p generators sums ≤ u (componentwise)."""
    if p == 0:
        return u[0] >= 0 and u[1] >= 0 and u[2] >= 0
    reach = {(0, 0, 0)}                       # sums achievable with j generators, staying ≤ u
    for _ in range(p):
        nxt = set()
        for s in reach:
            for g in gens:
                t = (s[0] + g[0], s[1] + g[1], s[2] + g[2])
                if _le(t, u):
                    nxt.add(t)
        if not nxt:
            return False
        reach = nxt
    return bool(reach)


def in_closure_of_power(u, gens, p: int, kmax: int = KMAX) -> bool:
    """x^u ∈ closure(I^p)  ⟺  ∃ k ≥ 1 : x^{ku} ∈ (I^p)^k = I^{pk}  (integral dependence, exact)."""
    for k in range(1, kmax + 1):
        ku = (k * u[0], k * u[1], k * u[2])
        if in_power(ku, gens, p * k):
            return True
    return False


def box_bound(gens, p: int) -> int:
    """A coordinate cap that provably contains every minimal generator of closure(I^p): a minimal
    generator cannot exceed p · (max single-coordinate among the generators) in any coordinate."""
    return p * max(max(g) for g in gens)


def integrally_closed(gens, p: int = 1):
    """Is I^p integrally closed? Returns (bool, witness or None) — the lex-first x^u ∈ closure(I^p) ∖ I^p."""
    B = box_bound(gens, p)
    for u in product(range(B + 1), repeat=3):
        if in_closure_of_power(u, gens, p) and not in_power(u, gens, p):
            return False, u
    return True, None


def is_normal(gens):
    """Reid–Roberts–Vitulli (d = 3): I normal ⟺ I and I^2 integrally closed. Returns a verdict dict."""
    ic1, w1 = integrally_closed(gens, 1)
    ic2, w2 = integrally_closed(gens, 2)
    return {"generators": [list(g) for g in gens], "I_integrally_closed": ic1, "I2_integrally_closed": ic2,
            "normal": ic1 and ic2, "closure_witness_I": list(w1) if w1 else None,
            "closure_witness_I2": list(w2) if w2 else None}


def closure_min_generators(gens):
    """Minimal monomial generators of closure(I): the minimal lattice points u with x^u ∈ closure(I)
    (u ∈ closure but u − e_i ∉ closure for each positive coordinate). Self-contained (no external
    convex-hull); used to cross-check this instrument against the corner-ideal checker on closures."""
    B = box_bound(gens, 1)

    def cl(u):
        return in_closure_of_power(u, gens, 1)

    out = []
    for u in product(range(B + 1), repeat=3):
        if not cl(u):
            continue
        minimal = True
        for i in range(3):
            if u[i] > 0:
                v = list(u)
                v[i] -= 1
                if cl(tuple(v)):
                    minimal = False
                    break
        if minimal:
            out.append(u)
    return sorted(out)


def dependence_witness(u, gens, p: int, kmax: int = KMAX):
    """If x^u ∈ closure(I^p) ∖ I^p, return the smallest k with x^{ku} ∈ I^{pk} (a checkable dependence
    certificate: (x^u)^k lies in I^{pk}). Returns None if x^u ∈ I^p already or not in the closure."""
    if in_power(u, gens, p):
        return None
    for k in range(1, kmax + 1):
        if in_power((k * u[0], k * u[1], k * u[2]), gens, p * k):
            return k
    return None
