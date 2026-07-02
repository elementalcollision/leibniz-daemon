"""Constant-weight (Johnson-scheme) Terwilliger three-point — MECHANICAL dual derivation + checker (free-CPU).

The Phase-1 discipline (terwilliger_dual.py) applied to the Section-III structure: derive the dual
mechanically and DO NOT hand-write signs. `collected()` here is the authoritative stationarity-system spec
for the constant-weight build; `dual_check()` is the exact checker the cert leg feeds.

Primal (Schrijver 2005 eq. 64/65/67, structure from terwilliger_cwc_beta): variables y^{t,s}_{i,j} reduced by
the (65)(iii) orbit merge (key = (sorted{i,j,i+j−t−s}, t−s)) and (65)(iv) distance-zeroing. Dual objects:
PSD Z_{k,l}, Z'_{k,l} (one pair per nonempty block); nonneg α, β1, γ for the three (65)(ii) families indexed
by POSSIBLE quads (t,s,i,j); free ν for (65)(i). Weak duality via the Lagrangian

    L(y, duals) = c·y + Σ_{k,l}⟨Z_{k,l}, M_{k,l}(y)⟩ + Σ_{k,l}⟨Z'_{k,l}, M'_{k,l}(y)⟩
                  + Σ α y + Σ β1(y^{0,0}_{i,0} − y) + Σ γ(1 + y − y^{0,0}_{i,0} − y^{0,0}_{j,0})
                  + ν(y^{0,0}_{0,0} − 1).

For dual-feasible duals and primal-feasible y every added term is ≥ 0 (or = 0), so c·y ≤ L; when the
stationarity system holds, L collapses to the constant Σγ − ν:  A(n,d,w) ≤ Σγ − ν.

VALIDATION (free-CPU, no solver): L evaluated directly as a sum of products must equal its collected form
const(duals) + Σ_v coeff_v(duals)·y_v for ALL (y, duals) — checked on pseudo-random exact-rational points; a
one-sign corruption must break it. Weak duality is sign-checked against real constant-weight codes (Steiner
systems, Johnson spaces) with random feasible duals, with a targeted-corruption teeth check.
"""
from __future__ import annotations

import importlib.util
import json
import random
from fractions import Fraction as Fr
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
OUT = _ROOT / "docs" / "results" / "terwilliger_cwc_dual.json"


def _load(mod, rel):
    spec = importlib.util.spec_from_file_location(mod, _ROOT / rel)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


tc = _load("terwilliger_cwc_beta", "scripts/terwilliger_cwc_beta.py")
is_psd_exact = tc.is_psd_exact


def _val(key, d, yass):
    return yass[key] if tc.classify(key, d) == "free" else Fr(0)


def lagrangian(n, d, w, yass, duals, corrupt=False):
    """Evaluate L(y, duals) DIRECTLY as a sum of products (the definition). `corrupt` flips the α-term sign
    (weak-duality teeth)."""
    v = n - w
    L = Fr(0)
    for key, val in yass.items():                                          # objective c·y
        L += tc.obj_coeff(key, w, v) * val
    for (k, l) in tc.block_pairs(w, v):  # noqa: E741                       # ⟨Z, M⟩ + ⟨Z', M'⟩
        idx = tc.block_idx(w, v, k, l)
        Z, Zp = duals["Z"][(k, l)], duals["Zp"][(k, l)]
        for a, i in enumerate(idx):
            for b, j in enumerate(idx):
                mk = Fr(0)
                mpk = Fr(0)
                for t in range(min(i, j) + 1):
                    bw = tc.beta(w, i, j, k, t)
                    if not bw:
                        continue
                    for s in range(min(i, j) + 1):
                        if not tc.possible(w, v, i, j, t, s):
                            continue
                        bv = tc.beta(v, i, j, l, s)
                        if not bv:
                            continue
                        yv = _val(tc.canon(t, s, i, j), d, yass)
                        y0 = _val(tc.canon(0, 0, i + j - t - s, 0), d, yass)
                        mk += bw * bv * yv
                        mpk += bw * bv * (y0 - yv)
                L += Z[a][b] * mk + Zp[a][b] * mpk
    for (t, s, i, j) in tc.valid_quads(w, v):                              # linear (65)(ii) + (i)
        yv = _val(tc.canon(t, s, i, j), d, yass)
        y0i = _val(tc.canon(0, 0, i, 0), d, yass)
        y0j = _val(tc.canon(0, 0, j, 0), d, yass)
        L += (-1 if corrupt else 1) * duals["a"][(t, s, i, j)] * yv
        L += duals["b1"][(t, s, i, j)] * (y0i - yv)
        L += duals["g"][(t, s, i, j)] * (Fr(1) + yv - y0i - y0j)
    L += duals["nu"] * (_val(((0, 0, 0), 0), d, yass) - 1)
    return L


def collected(n, d, w, duals, corrupt=False):
    """Collect L into (const, {key: coeff}) purely from the duals + β-products — the mechanical dual
    EMITTER / CHECKER (the constant-weight `collected()`). Agreement with lagrangian() for all (y, duals)
    certifies every sign/index. `corrupt` flips one β-product sign (identity teeth)."""
    v = n - w
    keys = tc.free_keys(w, v, d)
    coeff = {key: Fr(0) for key in keys}
    const = Fr(0)

    def add(key, val):
        if tc.classify(key, d) == "free":
            coeff[key] += val

    for key in keys:                                                       # objective
        coeff[key] += tc.obj_coeff(key, w, v)
    for (k, l) in tc.block_pairs(w, v):  # noqa: E741                       # PSD blocks
        idx = tc.block_idx(w, v, k, l)
        Z, Zp = duals["Z"][(k, l)], duals["Zp"][(k, l)]
        for a, i in enumerate(idx):
            for b, j in enumerate(idx):
                for t in range(min(i, j) + 1):
                    bw = tc.beta(w, i, j, k, t)
                    if not bw:
                        continue
                    for s in range(min(i, j) + 1):
                        if not tc.possible(w, v, i, j, t, s):
                            continue
                        bv = tc.beta(v, i, j, l, s)
                        if not bv:
                            continue
                        bb = -bw * bv if corrupt else bw * bv
                        add(tc.canon(t, s, i, j), Z[a][b] * bb)            # ⟨Z, M⟩  : +ββ·y
                        add(tc.canon(0, 0, i + j - t - s, 0), Zp[a][b] * bb)   # ⟨Z', M'⟩: +ββ·y⁰
                        add(tc.canon(t, s, i, j), -Zp[a][b] * bb)          #          : −ββ·y
    for (t, s, i, j) in tc.valid_quads(w, v):                              # linear (65)(ii)
        add(tc.canon(t, s, i, j), duals["a"][(t, s, i, j)])
        add(tc.canon(0, 0, i, 0), duals["b1"][(t, s, i, j)])
        add(tc.canon(t, s, i, j), -duals["b1"][(t, s, i, j)])
        const += duals["g"][(t, s, i, j)]
        add(tc.canon(t, s, i, j), duals["g"][(t, s, i, j)])
        add(tc.canon(0, 0, i, 0), -duals["g"][(t, s, i, j)])
        add(tc.canon(0, 0, j, 0), -duals["g"][(t, s, i, j)])
    add(((0, 0, 0), 0), duals["nu"])                                       # (65)(i): ν·y⁰₀₀
    const += -duals["nu"]
    return const, coeff


# ---- random exact-rational points for the identity test --------------------------------------------------

def _rand_rat(rng):
    return Fr(rng.randint(-5, 5), rng.randint(1, 4))


def _rand_sym(m, rng):
    M = [[Fr(0)] * m for _ in range(m)]
    for i in range(m):
        for j in range(i, m):
            M[i][j] = M[j][i] = _rand_rat(rng)
    return M


def _rand_duals(n, w, rng):
    v = n - w
    pairs = tc.block_pairs(w, v)
    Z = {kl: _rand_sym(len(tc.block_idx(w, v, *kl)), rng) for kl in pairs}
    Zp = {kl: _rand_sym(len(tc.block_idx(w, v, *kl)), rng) for kl in pairs}
    a = {q: _rand_rat(rng) for q in tc.valid_quads(w, v)}
    b1 = {q: _rand_rat(rng) for q in tc.valid_quads(w, v)}
    g = {q: _rand_rat(rng) for q in tc.valid_quads(w, v)}
    return {"Z": Z, "Zp": Zp, "a": a, "b1": b1, "g": g, "nu": _rand_rat(rng)}


def identity_holds(n, d, w, trials=6, corrupt=False, seed=1):
    v = n - w
    rng = random.Random(seed * 10000 + n * 100 + d * 10 + w)
    for _ in range(trials):
        yass = {key: _rand_rat(rng) for key in tc.free_keys(w, v, d)}
        duals = _rand_duals(n, w, rng)
        lhs = lagrangian(n, d, w, yass, duals)
        const, coeff = collected(n, d, w, duals, corrupt=corrupt)
        rhs = const + sum(coeff[key] * yass[key] for key in coeff)
        if lhs != rhs:
            return False
    return True


# ---- checker (fed by the cert leg) + weak-duality sign validation ----------------------------------------

def yass_from_code(n, d, w, code):
    """Map a real constant-weight code's triple counts onto the reduced free variables. A code with minimum
    distance ≥ d is PRIMAL-FEASIBLE: its blocks are PSD (cwc Phase 0) and (65)(ii) holds. Orbit-invariant by
    (iii), so each free key takes the code_y value of any possible representative."""
    v = n - w
    y, _y0 = tc.code_y(n, w, code)
    yass = {}
    for key in tc.free_keys(w, v, d):
        rep = tc.rep_quad(w, v, key)
        yass[key] = y.get(rep, Fr(0)) if rep is not None else Fr(0)
    yass[((0, 0, 0), 0)] = Fr(1)
    return yass


def _codes_for(n, d, w):
    """Small constant-weight codes with minimum distance ≥ d — primal-feasible by construction."""
    full = tc.johnson_space(n, w)
    out = [[full[0]]]                                     # singleton, min-dist ∞
    lo = tc._mask(range(w))
    hi = tc._mask(range(n - w, n))
    if 2 * min(w, n - w) >= d and lo != hi:
        out.append([lo, hi])                              # max-distance pair, dist 2·min(w, n−w)
    if d == 2:
        out.append(full)                                  # the whole Johnson space, min-dist 2
    if d == 4 and (n, w) == (7, 3):
        out.append(tc.FANO)
    if d == 4 and (n, w) == (9, 3):
        out.append(tc.STS9)
    return out


def _feasible_duals(n, w, rng):
    """A DUAL-FEASIBLE point (not necessarily stationary): Z, Z' ⪰ 0 (via A·Aᵀ), α,β1,γ ≥ 0."""
    v = n - w

    def psd(m):
        A = [[_rand_rat(rng) for _ in range(m)] for _ in range(m)]
        return [[sum(A[i][k] * A[j][k] for k in range(m)) for j in range(m)] for i in range(m)]

    def nn():
        return {q: abs(_rand_rat(rng)) for q in tc.valid_quads(w, v)}
    pairs = tc.block_pairs(w, v)
    return {"Z": {kl: psd(len(tc.block_idx(w, v, *kl))) for kl in pairs},
            "Zp": {kl: psd(len(tc.block_idx(w, v, *kl))) for kl in pairs},
            "a": nn(), "b1": nn(), "g": nn(), "nu": _rand_rat(rng)}


def weak_duality_holds(n, d, w, trials=4, seed=7):
    """SIGN-VALIDITY: for primal-feasible y (real code) and dual-feasible duals, c·y ≤ L(y, duals)."""
    v = n - w
    rng = random.Random(seed * 10000 + n * 100 + d * 10 + w)
    for code in _codes_for(n, d, w):
        yass = yass_from_code(n, d, w, code)
        cy = sum(tc.obj_coeff(key, w, v) * val for key, val in yass.items())
        for _ in range(trials):
            duals = _feasible_duals(n, w, rng)
            if not (cy <= lagrangian(n, d, w, yass, duals)):
                return False
    return True


def _zero_duals(n, w):
    v = n - w
    pairs = tc.block_pairs(w, v)
    zero_lin = {q: Fr(0) for q in tc.valid_quads(w, v)}

    def zmat(kl):
        m = len(tc.block_idx(w, v, *kl))
        return [[Fr(0)] * m for _ in range(m)]
    return {"Z": {kl: zmat(kl) for kl in pairs}, "Zp": {kl: zmat(kl) for kl in pairs},
            "a": dict(zero_lin), "b1": dict(zero_lin), "g": dict(zero_lin), "nu": Fr(0)}


def corruption_detected_wd(n, d, w):
    """Teeth for the sign-validity check: a targeted α (large on one quad where y > 0, all else 0) keeps
    c·y ≤ L under correct signs but breaks it once the α-sign is flipped."""
    v = n - w
    for code in _codes_for(n, d, w):
        yass = yass_from_code(n, d, w, code)
        cy = sum(tc.obj_coeff(key, w, v) * val for key, val in yass.items())
        for q in tc.valid_quads(w, v):
            key = tc.canon(*q)
            if tc.classify(key, d) == "free" and yass.get(key, Fr(0)) > 0:
                duals = _zero_duals(n, w)
                duals["a"][q] = Fr(10)
                good = cy <= lagrangian(n, d, w, yass, duals, corrupt=False)
                bad = cy <= lagrangian(n, d, w, yass, duals, corrupt=True)
                if good and not bad:
                    return True
    return False


def dual_check(n, d, w, duals):
    """The dual-feasibility CHECKER: recompute the stationarity residuals + bound from (duals, β-products)
    and the PSD/nonneg conditions. Feasible iff all residuals are 0, every Z/Z' ⪰ 0, and α,β1,γ ≥ 0.

    GUARANTEE: a dual-feasible point certifies `A(n,d,w) ≤ Σγ − ν` by weak duality — no primal witness
    needed. SCOPE (audit-tier): certifies the bound for the SDP *as transcribed here*; formulation
    faithfulness is empirical (Table II gate) — hence DUAL_CERTIFICATE_CHECKED, not Q.E.D."""
    const, coeff = collected(n, d, w, duals)
    residuals = {key: val for key, val in coeff.items() if val != 0}
    psd = all(is_psd_exact(duals["Z"][kl]) and is_psd_exact(duals["Zp"][kl]) for kl in duals["Z"])
    nonneg = (all(val >= 0 for val in duals["a"].values()) and all(val >= 0 for val in duals["b1"].values())
              and all(val >= 0 for val in duals["g"].values()))
    bound = sum(duals["g"].values()) - duals["nu"]
    feasible = (not residuals) and psd and nonneg
    return {"feasible": feasible, "bound": bound, "n_residuals_nonzero": len(residuals),
            "psd_ok": psd, "nonneg_ok": nonneg}


def main() -> int:
    cells = [(6, 2, 3), (6, 4, 3), (7, 4, 3), (8, 4, 4), (9, 4, 3)]
    rows = []
    all_ok = True
    for (n, d, w) in cells:
        v = n - w
        ok = identity_holds(n, d, w)
        broke = not identity_holds(n, d, w, corrupt=True)
        wd = weak_duality_holds(n, d, w)
        wd_broke = corruption_detected_wd(n, d, w)
        keys = tc.free_keys(w, v, d)
        # objective free keys must be exactly the half-distances {0} ∪ {i ≥ d/2} up to min(w,v) — the
        # Johnson-scheme inner-distribution variables.
        got = sorted(key[0][1] for key in keys if tc.obj_coeff(key, w, v))
        want = [i for i in range(min(w, v) + 1) if i == 0 or i > (d - 1) // 2]
        obj_ok = got == want
        blocks = [len(tc.block_idx(w, v, *kl)) for kl in tc.block_pairs(w, v)]
        row = {"n": n, "d": d, "w": w, "n_free_vars": len(keys), "identity_holds": ok,
               "corruption_breaks_identity": broke, "weak_duality_holds": wd,
               "corruption_breaks_weak_duality": wd_broke, "n_blocks": len(blocks),
               "largest_block": max(blocks), "objective_weights": got, "objective_ok": obj_ok}
        rows.append(row)
        all_ok = all_ok and ok and broke and wd and wd_broke and obj_ok

    verdict = "GREEN" if all_ok else "RED"
    res = {"verdict": verdict, "cells": rows,
           "reading": ("GREEN = the mechanically-collected constant-weight dual equals the Lagrangian for all "
                       "random exact-rational (y, duals), a one-sign corruption breaks it, weak duality holds "
                       "with real Steiner/Johnson codes (and its targeted corruption breaks), and the "
                       "objective variables are exactly the Johnson inner-distribution weights. collected() "
                       "here is the authoritative stationarity spec the cert leg prices against. "
                       "RED = a sign/index bug in the dual derivation.")}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(res, indent=2) + "\n")
    print(f"terwilliger cwc dual: {verdict}")
    for r in rows:
        print(f"  A({r['n']},{r['d']},{r['w']}): vars={r['n_free_vars']:3d} identity={r['identity_holds']} "
              f"corrupt_breaks={r['corruption_breaks_identity']} weak_dual={r['weak_duality_holds']} "
              f"wd_corrupt_breaks={r['corruption_breaks_weak_duality']} obj_ok={r['objective_ok']} "
              f"blocks={r['n_blocks']} largest={r['largest_block']}")
    print(f"  -> {OUT}")
    return 0 if verdict == "GREEN" else 1


if __name__ == "__main__":
    raise SystemExit(main())
