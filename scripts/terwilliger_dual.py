"""Terwilliger three-point — Phase 1: MECHANICAL dual derivation + checker (free-CPU).

Per docs/results/terwilliger-review-synthesis-2026-07-01.md (D3/D5): derive the dual mechanically and DO NOT
hand-write signs. The dual is a *system* (a per-orbit stationarity equation for every primal variable), not
"one scalar identity"; the checker recomputes the dual contributions from (dual point, β) — it never trusts a
producer-supplied slack.

Primal (Schrijver 2005, unrestricted A(n,d), eq. 19/20/22), variables x^t_{i,j} reduced by (20)(iii) orbit
merge (a variable is the multiset {i, j, i+j−2t} of the three pairwise distances of a triple X,Y,Z), (20)(iv)
distance-zeroing, and the even-d weight reduction:

    maximize   Σ_i C(n,i) x^0_{i,0}
    s.t. (19)  M_k(x)  = (Σ_t β^t_{i,j,k} x^t_{i,j})_{i,j∈[k,n-k]}                     ⪰ 0   ∀k
               M'_k(x) = (Σ_t β^t_{i,j,k} (x^0_{i+j−2t,0} − x^t_{i,j}))_{i,j∈[k,n-k]}  ⪰ 0   ∀k
         (20)  (i) x^0_{0,0}=1 ; (ii) 0≤x^t_{i,j}≤x^0_{i,0}, x^0_{i,0}+x^0_{j,0}≤1+x^t_{i,j}

Dual objects: PSD Z_k, Z'_k (size n−2k+1); nonneg α,β1,γ for the three (ii) families; free ν for (i). Weak
duality via the Lagrangian
    L(x, duals) = c·x + Σ_k⟨Z_k,M_k(x)⟩ + Σ_k⟨Z'_k,M'_k(x)⟩ + Σ α x + Σ β1(x^0_{i,0}−x) + Σ γ(1+x−x^0−x^0)
                  + ν(x^0_{0,0}−1).
For dual-feasible duals (Z⪰0, α,β1,γ≥0) and primal-feasible x, every added term is ≥0 (or =0), so c·x ≤ L; and
when the *stationarity system* holds (coefficient of every free x-variable in L is 0) L collapses to a constant
= the bound. A(n,d) ≤ Σγ − ν.

VALIDATION (this file, free-CPU, no solver): the derivation is correct iff L, evaluated directly as a sum of
products, equals its collected form  const(duals) + Σ_v coeff_v(duals)·x_v  for ALL (x, duals). We check that
identity on pseudo-random exact-rational points; a one-sign corruption of the collector must break it (teeth).
Finding a feasible dual (making the slacks PSD and residuals zero) is Phase 2 — not here.
"""
from __future__ import annotations

import importlib.util
import json
import random
from fractions import Fraction as Fr
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
OUT = _ROOT / "docs" / "results" / "terwilliger_dual.json"


def _load(mod, rel):
    spec = importlib.util.spec_from_file_location(mod, _ROOT / rel)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


tb = _load("terwilliger_beta", "scripts/terwilliger_beta.py")
C = tb.C
beta = tb.beta                 # β is NOT blindly trusted: terwilliger_beta.py (Phase 0) validates eq.(7) against
is_psd_exact = tb.is_psd_exact  # the real-code PSD differential test + a corrupt-control, CI-guarded.


# ---- primal structure ------------------------------------------------------------------------------------

def possible(n, i, j, t):
    """A triple (X,Y,Z) with |X△Y|=i, |X△Z|=j, |(X△Y)∩(X△Z)|=t can EXIST iff the disjoint-subset multinomial
    binom(n; i−t, j−t, t) ≠ 0, i.e. (i−t)+(j−t)+t = i+j−t ≤ n with all parts ≥ 0. Schrijver eq. (10) SETS
    x^t_{i,j}=0 in this impossible case, so such (i,j,t) are NOT free variables and carry NO (20) constraint —
    omitting this is what wrongly admitted phantom variables (e.g. key (8,8,8) at n=8) and invalidated the SDP."""
    return 0 <= t <= min(i, j) and i <= n and j <= n and 0 <= i + j - 2 * t and i + j - t <= n


def valid_triples(n):
    """Ordered POSSIBLE (t,i,j): 0≤t≤min(i,j), i,j≤n, 0≤i+j−2t, and i+j−t≤n (binom≠0)."""
    for i in range(n + 1):
        for j in range(n + 1):
            for t in range(min(i, j) + 1):
                if possible(n, i, j, t):
                    yield t, i, j


def canon(t, i, j):
    """Orbit key = sorted multiset of the three pairwise distances {i, j, i+j−2t}."""
    return tuple(sorted((i, j, i + j - 2 * t)))


def classify(key, d):
    """'zero' if forbidden by (20)(iv) or the even-d weight reduction, else 'free'. (0,0,0) is a free variable
    (it carries x^0_{0,0}; pinned to 1 by the (i) constraint with dual ν, not substituted away)."""
    if any(1 <= v <= d - 1 for v in key):
        return "zero"
    if d % 2 == 0 and any(v % 2 == 1 for v in key):
        return "zero"
    return "free"


def free_keys(n, d):
    keys = set()
    for (t, i, j) in valid_triples(n):
        k = canon(t, i, j)
        if classify(k, d) == "free":
            keys.add(k)
    return sorted(keys)


def obj_coeff(key, n):
    """Objective Σ_i C(n,i) x^0_{i,0}. x^0_{i,0} has key (0,i,i); i=0 gives (0,0,0) with C(n,0)=1."""
    a, b, c = key
    return C(n, b) if a == 0 and b == c else 0


def block_idx(n, k):
    return list(range(k, n - k + 1))


# ---- the two evaluators whose agreement validates the derivation -----------------------------------------

def _val(key, d, xass):
    return xass[key] if classify(key, d) == "free" else Fr(0)


def lagrangian(n, d, xass, duals, corrupt=False):
    """Evaluate L(x, duals) DIRECTLY as a sum of products (the definition). `corrupt` flips the α-term sign to
    prove the weak-duality direction check has teeth (a wrong sign there breaks c·x ≤ L for feasible points)."""
    L = Fr(0)
    # objective c·x
    for key, v in xass.items():
        L += obj_coeff(key, n) * v
    # PSD blocks ⟨Z_k, M_k(x)⟩ and ⟨Z'_k, M'_k(x)⟩
    for k in range(n // 2 + 1):
        idx = block_idx(n, k)
        Z, Zp = duals["Z"][k], duals["Zp"][k]
        for a, i in enumerate(idx):
            for b, j in enumerate(idx):
                mk = Fr(0)
                mpk = Fr(0)
                for t in range(min(i, j) + 1):
                    s = i + j - 2 * t
                    if not possible(n, i, j, t):
                        continue
                    bijk = beta(n, i, j, k, t)
                    if not bijk:
                        continue
                    xv = _val(canon(t, i, j), d, xass)
                    x0 = _val(canon(0, s, 0), d, xass)
                    mk += bijk * xv
                    mpk += bijk * (x0 - xv)
                L += Z[a][b] * mk + Zp[a][b] * mpk
    # linear (ii) families + (i)
    for (t, i, j) in valid_triples(n):
        xv = _val(canon(t, i, j), d, xass)
        x0i = _val(canon(0, i, 0), d, xass)
        x0j = _val(canon(0, j, 0), d, xass)
        L += (-1 if corrupt else 1) * duals["a"][(t, i, j)] * xv
        L += duals["b1"][(t, i, j)] * (x0i - xv)
        L += duals["g"][(t, i, j)] * (Fr(1) + xv - x0i - x0j)
    L += duals["nu"] * (_val((0, 0, 0), d, xass) - 1)
    return L


def collected(n, d, duals, corrupt=False):
    """Collect L into  (const, {key: coeff})  purely from the duals + β — the mechanical dual EMITTER /
    CHECKER. Agreement with lagrangian() for all (x,duals) certifies every sign/index. `corrupt` flips one
    β sign to prove the identity test discriminates."""
    keys = free_keys(n, d)
    coeff = {k: Fr(0) for k in keys}
    const = Fr(0)

    def add(key, val):
        if classify(key, d) == "free":
            coeff[key] += val

    for key in keys:                                   # objective
        coeff[key] += obj_coeff(key, n)
    for k in range(n // 2 + 1):                          # PSD blocks
        idx = block_idx(n, k)
        Z, Zp = duals["Z"][k], duals["Zp"][k]
        for a, i in enumerate(idx):
            for b, j in enumerate(idx):
                for t in range(min(i, j) + 1):
                    s = i + j - 2 * t
                    if not possible(n, i, j, t):
                        continue
                    bijk = beta(n, i, j, k, t)
                    if not bijk:
                        continue
                    if corrupt:
                        bijk = -bijk                    # the single-sign fault the control must catch
                    add(canon(t, i, j), Z[a][b] * bijk)          # ⟨Z_k, M_k⟩ : +β·x
                    add(canon(0, s, 0), Zp[a][b] * bijk)         # ⟨Z'_k, M'_k⟩: +β·x^0_{s,0}
                    add(canon(t, i, j), -Zp[a][b] * bijk)        #             : −β·x
    for (t, i, j) in valid_triples(n):                  # linear (ii)
        add(canon(t, i, j), duals["a"][(t, i, j)])
        add(canon(0, i, 0), duals["b1"][(t, i, j)])
        add(canon(t, i, j), -duals["b1"][(t, i, j)])
        const += duals["g"][(t, i, j)]
        add(canon(t, i, j), duals["g"][(t, i, j)])
        add(canon(0, i, 0), -duals["g"][(t, i, j)])
        add(canon(0, j, 0), -duals["g"][(t, i, j)])
    add((0, 0, 0), duals["nu"])                          # (i): ν·x^0_{0,0}
    const += -duals["nu"]                                # (i): ν·(−1)
    return const, coeff


# ---- random exact-rational points for the identity test --------------------------------------------------

def _rand_rat(rng):
    return Fr(rng.randint(-5, 5), rng.randint(1, 4))


def _rand_duals(n, d, rng):
    Z = {k: _rand_sym(len(block_idx(n, k)), rng) for k in range(n // 2 + 1)}
    Zp = {k: _rand_sym(len(block_idx(n, k)), rng) for k in range(n // 2 + 1)}
    a = {tij: _rand_rat(rng) for tij in valid_triples(n)}
    b1 = {tij: _rand_rat(rng) for tij in valid_triples(n)}
    g = {tij: _rand_rat(rng) for tij in valid_triples(n)}
    return {"Z": Z, "Zp": Zp, "a": a, "b1": b1, "g": g, "nu": _rand_rat(rng)}


def _rand_sym(m, rng):
    M = [[Fr(0)] * m for _ in range(m)]
    for i in range(m):
        for j in range(i, m):
            M[i][j] = M[j][i] = _rand_rat(rng)
    return M


def identity_holds(n, d, trials=8, corrupt=False, seed=1):
    rng = random.Random(seed * 1000 + n * 10 + d)
    for _ in range(trials):
        xass = {k: _rand_rat(rng) for k in free_keys(n, d)}
        duals = _rand_duals(n, d, rng)
        lhs = lagrangian(n, d, xass, duals)
        const, coeff = collected(n, d, duals, corrupt=corrupt)
        rhs = const + sum(coeff[k] * xass[k] for k in coeff)
        if lhs != rhs:
            return False
    return True


# ---- checker (used by Phase 2) + structural facts --------------------------------------------------------

def xass_from_code(n, d, code):
    """Map a real code's inner distribution (Phase-0 code_x) onto the reduced free variables. A real code with
    minimum distance ≥ d is PRIMAL-FEASIBLE: its β-blocks are PSD (Phase 0) and (20)(ii) holds. Orbit-invariant
    by (iii), so each free key takes the code_x value of any representative triple."""
    x, _x0 = tb.code_x(n, code)
    xass = {}
    for key in free_keys(n, d):
        a, b, c = key                                   # a representative triple: i=b, j=c, t=(b+c−a)/2
        t = (b + c - a) // 2
        xass[key] = x.get((t, b, c), Fr(0))
    xass[(0, 0, 0)] = Fr(1)                              # x^0_{0,0}=1
    return xass


def _feasible_duals(n, d, rng):
    """A DUAL-FEASIBLE point (not necessarily stationary): Z_k, Z'_k ⪰ 0 (via A·Aᵀ) and α,β1,γ ≥ 0."""
    def psd(m):
        A = [[_rand_rat(rng) for _ in range(m)] for _ in range(m)]
        return [[sum(A[i][k] * A[j][k] for k in range(m)) for j in range(m)] for i in range(m)]

    def nn():
        return {tij: abs(_rand_rat(rng)) for tij in valid_triples(n)}
    return {"Z": {k: psd(len(block_idx(n, k))) for k in range(n // 2 + 1)},
            "Zp": {k: psd(len(block_idx(n, k))) for k in range(n // 2 + 1)},
            "a": nn(), "b1": nn(), "g": nn(), "nu": _rand_rat(rng)}


def _codes_for(n, d):
    """Small codes with minimum distance ≥ d — hence PRIMAL-FEASIBLE by construction: their β-blocks are PSD
    (Phase 0) and their inner distribution satisfies (20)(ii), so no explicit feasibility check is needed here."""
    out = [[0]]                                          # singleton, min-dist ∞
    if n >= d:
        out.append([0, (1 << n) - 1])                   # repetition, min-dist n
    if d == 2:
        out.append([v for v in range(1 << n) if v.bit_count() % 2 == 0])   # even-weight, min-dist 2
    return out


def weak_duality_holds(n, d, trials=6, seed=7):
    """SIGN-VALIDITY check: for primal-feasible x (real code) and dual-feasible duals, c·x ≤ L(x,duals) — this
    is weak duality in Lagrangian form and holds only if every term's sign is right."""
    rng = random.Random(seed * 1000 + n * 10 + d)
    for code in _codes_for(n, d):
        xass = xass_from_code(n, d, code)
        cx = sum(obj_coeff(k, n) * v for k, v in xass.items())
        for _ in range(trials):
            duals = _feasible_duals(n, d, rng)
            if not (cx <= lagrangian(n, d, xass, duals)):
                return False
    return True


def _zero_duals(n, d):
    z = {k: [[Fr(0)] * len(block_idx(n, k)) for _ in block_idx(n, k)] for k in range(n // 2 + 1)}
    zero_lin = {tij: Fr(0) for tij in valid_triples(n)}
    return {"Z": {k: [r[:] for r in z[k]] for k in z}, "Zp": {k: [r[:] for r in z[k]] for k in z},
            "a": dict(zero_lin), "b1": dict(zero_lin), "g": dict(zero_lin), "nu": Fr(0)}


def corruption_detected_wd(n, d):
    """Teeth for the sign-validity check: a TARGETED dual-feasible point (α large on one triple where x>0, all
    else 0) keeps c·x ≤ L under correct signs but makes c·x > L once the α-sign is flipped."""
    for code in _codes_for(n, d):
        xass = xass_from_code(n, d, code)
        cx = sum(obj_coeff(k, n) * v for k, v in xass.items())
        for (t, i, j) in valid_triples(n):
            key = canon(t, i, j)
            if classify(key, d) == "free" and xass.get(key, Fr(0)) > 0:
                duals = _zero_duals(n, d)
                duals["a"][(t, i, j)] = Fr(10)
                good = cx <= lagrangian(n, d, xass, duals, corrupt=False)
                bad = cx <= lagrangian(n, d, xass, duals, corrupt=True)
                if good and not bad:
                    return True
    return False


def dual_check(n, d, duals):
    """The dual-feasibility CHECKER: recompute the stationarity residuals + bound from (duals, β) and the PSD
    conditions. Feasible iff all residuals are 0, every Z_k/Z'_k ⪰ 0, and α,β1,γ ≥ 0. (Phase 2 supplies the
    duals; this never trusts a producer-supplied slack — it rebuilds the coefficients itself; β itself is
    validated upstream in Phase 0.)

    GUARANTEE: a *dual-feasible* point certifies `A(n,d) ≤ bound` by weak duality — NO primal witness is needed
    (a feasible dual bounds the max over ALL primal-feasible x at once). SCOPE (audit-tier): this certifies the
    bound for the SDP *as transcribed here*; that the transcription equals the code problem (formulation
    faithfulness, Fugu's Trap 3) is NOT machine-checked and awaits the bridge theorem — hence
    DUAL_CERTIFICATE_CHECKED, not Q.E.D."""
    const, coeff = collected(n, d, duals)
    residuals = {k: v for k, v in coeff.items() if v != 0}
    psd = all(is_psd_exact(duals["Z"][k]) and is_psd_exact(duals["Zp"][k]) for k in duals["Z"])
    nonneg = all(v >= 0 for v in duals["a"].values()) and all(v >= 0 for v in duals["b1"].values()) \
        and all(v >= 0 for v in duals["g"].values())
    bound = sum(duals["g"].values()) - duals["nu"]      # Σγ − ν (homogeneous PSD ⇒ linear duals set the bound)
    feasible = (not residuals) and psd and nonneg
    return {"feasible": feasible, "bound": bound, "n_residuals_nonzero": len(residuals),
            "psd_ok": psd, "nonneg_ok": nonneg}


def delsarte_objective_keys(n, d):
    """Objective free variables — should be exactly {x^0_{i,0} : i=0 or i≥d} (even i if d even): the Delsarte
    inner-distribution variables A_i (A_0 and A_i for i≥d)."""
    return sorted(k for k in free_keys(n, d) if obj_coeff(k, n))


def main() -> int:
    cells = [(4, 2), (5, 2), (6, 2), (6, 4), (7, 4)]
    rows = []
    all_ok = True
    for (n, d) in cells:
        ok = identity_holds(n, d)
        broke = not identity_holds(n, d, corrupt=True)          # corruption MUST break the identity
        wd = weak_duality_holds(n, d)                            # c·x ≤ L for feasible x, feasible duals
        wd_broke = corruption_detected_wd(n, d)                  # a flipped α-sign MUST break it
        keys = free_keys(n, d)
        obj_keys = delsarte_objective_keys(n, d)
        # Delsarte check: objective variables are exactly weights {0} ∪ {i≥d} (even if d even)
        want = [i for i in range(n + 1) if (i == 0 or i >= d) and not (d % 2 == 0 and i % 2 == 1)]
        got = [k[1] for k in obj_keys]                          # (0,i,i) -> i
        delsarte_ok = got == want
        blocks = [len(block_idx(n, k)) for k in range(n // 2 + 1)]
        row = {"n": n, "d": d, "n_free_vars": len(keys), "identity_holds": ok,
               "corruption_breaks_identity": broke, "weak_duality_holds": wd,
               "corruption_breaks_weak_duality": wd_broke, "block_sizes": blocks,
               "objective_weights": got, "delsarte_objective_ok": delsarte_ok,
               "largest_block": max(blocks)}
        rows.append(row)
        all_ok = all_ok and ok and broke and wd and wd_broke and delsarte_ok

    verdict = "GREEN" if all_ok else "RED"
    res = {"verdict": verdict, "cells": rows,
           "reading": ("GREEN = the mechanically-collected dual (const + Σ coeff_v·x_v) equals the Lagrangian "
                       "for all random exact-rational (x, duals) [no hand-derived sign survives a mismatch], a "
                       "one-sign corruption breaks it [the check has teeth], and the k=0 objective variables are "
                       "exactly the Delsarte inner-distribution weights. The dual STRUCTURE + CHECKER are ready; "
                       "Phase 2 finds a feasible dual (normalized solve -> feasibility-at-target -> Bareiss). "
                       "RED = a sign/index bug in the dual derivation.")}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(res, indent=2) + "\n")
    print(f"terwilliger dual (Phase 1): {verdict}")
    for r in rows:
        print(f"  A({r['n']},{r['d']}): vars={r['n_free_vars']:3d} identity={r['identity_holds']} "
              f"corrupt_breaks={r['corruption_breaks_identity']} weak_dual={r['weak_duality_holds']} "
              f"wd_corrupt_breaks={r['corruption_breaks_weak_duality']} "
              f"delsarte_obj={r['delsarte_objective_ok']} blocks={r['block_sizes']}")
    print(f"  -> {OUT}")
    return 0 if verdict == "GREEN" else 1


if __name__ == "__main__":
    raise SystemExit(main())
