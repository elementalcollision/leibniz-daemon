"""Constant-weight (Johnson-scheme) Terwilliger block structure + independent validation (D1 step 1 of the
discovery pivot; see docs/handoff-terwilliger-discovery-2026-07-02.md).

AUTHORITATIVE source: Schrijver 2005, "New code upper bounds from the Terwilliger algebra and semidefinite
programming," Section III (constant-weight codes). Fix a codeword X with |X| = w, put v := n − w, and identify
any word Y with the pair (X\\Y, Y\\X) ∈ P_w × P_v. For a triple (X,Y,Z) of weight-w words the ordered
configuration is the quadruple (eq. 63)

    i = |X\\Y|,  j = |X\\Z|,  t = |(X\\Y)∩(X\\Z)|,  s = |(Y\\X)∩(Z\\X)|      (half-distances: |X△Y| = 2i etc.)

with variables (eq. 62)  y^{t,s}_{i,j} = μ^{t,s}_{i,j} / (|C|·binom(w; i−t,j−t,t)·binom(v; i−s,j−s,s)),
set to 0 when either multinomial vanishes (the impossible-configuration convention of eq. 10 — the same trap
that produced the unrestricted A(8,4)=13.7 bug; enforced here by possible()). Block-diagonalization (eq. 58/64):
for each k = 0..⌊w/2⌋ and l = 0..⌊v/2⌋ with W_k∩V_l ≠ ∅ (W_k = {k..w−k}, V_l = {l..v−l}), TWO PSD families on
index set W_k∩V_l:

    R -family:  M_{k,l}(y)_{i,j}  = Σ_{t,s} β^{t,w}_{i,j,k} · β^{s,v}_{i,j,l} · y^{t,s}_{i,j}
    R'-family:  M'_{k,l}(y)_{i,j} = Σ_{t,s} β^{t,w}_{i,j,k} · β^{s,v}_{i,j,l} · (y^{0,0}_{i+j−t−s,0} − y^{t,s}_{i,j})

where β is the SAME eq.(7) generator as the unrestricted build (terwilliger_beta.beta, Phase-0-validated),
evaluated at ground-set sizes w and v — the "new β" is a product of two banked β's. (The paper deletes the
(w−2k,i−k)^{−1/2}(v−2l,i−l)^{−1/2} row/column factors to make coefficients integer; that is a positive diagonal
congruence, so PSD is preserved exactly — same argument as the unrestricted build.)

Orbit merge (65)(iii): permuting (X,Y,Z) permutes the half-distance triple (i, j, i+j−t−s) and fixes t−s
(|X△Y△Z| = w+2t−2s is symmetric), so the orbit key is (sorted{i,j,i+j−t−s}, t−s). Distance zeroing (65)(iv):
y = 0 if any pairwise distance 2·h lies in {1..d−1}.

VALIDATION (free-CPU, exact rational, no numpy/solver/docker — the Phase-0 discipline): for any REAL
constant-weight code C, y from triple counts makes BOTH block families PSD for ALL (k,l) by construction
(multiplicity-reduced blocks of a sum of Gram matrices, eq. 60/61). A single wrong sign/index/normalization
breaks some real code's block. We validate on Johnson spaces, Steiner systems (Fano, AG(2,3)), and pair codes;
a deliberately-corrupted β (the transposed binomial) must FAIL; the eq.(66) identity |C| = Σ C(w,i)C(v,i)
y^{0,0}_{i,0} pins the multinomial normalization; and orbit-constancy of real-code y validates (iii).
"""
from __future__ import annotations

import importlib.util
import json
from fractions import Fraction as Fr
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
OUT = _ROOT / "docs" / "results" / "terwilliger_cwc_beta.json"


def _load(mod, rel):
    spec = importlib.util.spec_from_file_location(mod, _ROOT / rel)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


tb = _load("terwilliger_beta", "scripts/terwilliger_beta.py")
C = tb.C
beta = tb.beta                    # eq. (7), Phase-0-validated (real-code PSD differential + corrupt control)
is_psd_exact = tb.is_psd_exact


# ---- ordered-configuration structure ---------------------------------------------------------------------

def possible(w: int, v: int, i: int, j: int, t: int, s: int) -> bool:
    """A triple of weight-w words with parameters (i,j,t,s) EXISTS iff all eight Venn cells are nonnegative:
    inside X the cells are t, i−t, j−t, w−i−j+t; outside X they are s, i−s, j−s, v−i−j+s. Equivalently both
    multinomials binom(w; i−t,j−t,t) and binom(v; i−s,j−s,s) are nonzero. Schrijver sets y^{t,s}_{i,j} = 0
    otherwise, so such quads are NOT variables and carry NO (65)(ii) constraint."""
    return (0 <= t <= min(i, j) and 0 <= s <= min(i, j)
            and i + j - t <= w and i + j - s <= v
            and i <= min(w, v) and j <= min(w, v))


def valid_quads(w: int, v: int):
    """Ordered POSSIBLE (t,s,i,j), fixed enumeration order (constraint families and duals index by this)."""
    m = min(w, v)
    for i in range(m + 1):
        for j in range(m + 1):
            for t in range(min(i, j) + 1):
                for s in range(min(i, j) + 1):
                    if possible(w, v, i, j, t, s):
                        yield t, s, i, j


def canon(t: int, s: int, i: int, j: int):
    """Orbit key under permuting (X,Y,Z), eq. (65)(iii): the sorted multiset of the three pairwise
    half-distances {i, j, i+j−t−s} together with the invariant t−s."""
    return tuple(sorted((i, j, i + j - t - s))), t - s


def classify(key, d: int) -> str:
    """'zero' if some pairwise distance 2·h is forbidden by (65)(iv) (1 ≤ 2h ≤ d−1), else 'free'. Constant-
    weight distances are automatically even; ((0,0,0),0) stays free (pinned to 1 by (65)(i), dual ν)."""
    tri, _delta = key
    if any(1 <= h <= (d - 1) // 2 for h in tri):
        return "zero"
    return "free"


def free_keys(w: int, v: int, d: int):
    keys = set()
    for (t, s, i, j) in valid_quads(w, v):
        k = canon(t, s, i, j)
        if classify(k, d) == "free":
            keys.add(k)
    return sorted(keys)


def obj_coeff(key, w: int, v: int) -> int:
    """Objective (67): Σ_i C(w,i)·C(v,i)·y^{0,0}_{i,0}. y^{0,0}_{i,0} has key ((0,i,i), 0)."""
    (a, b, c), delta = key
    return C(w, b) * C(v, b) if a == 0 and b == c and delta == 0 else 0


def rep_quad(w: int, v: int, key):
    """A POSSIBLE ordered representative (t,s,i,j) of an orbit key, or None. Possibility is orbit-invariant
    (a realizable configuration realizes all six orderings), so any hit represents the whole orbit."""
    tri, delta = key
    (p, q, r) = tri
    for (i, j, rr) in {(p, q, r), (p, r, q), (q, p, r), (q, r, p), (r, p, q), (r, q, p)}:
        two_t = i + j - rr + delta
        if two_t % 2:
            continue
        t = two_t // 2
        s = t - delta
        if possible(w, v, i, j, t, s):
            return t, s, i, j
    return None


# ---- block families (eq. 58/64) ---------------------------------------------------------------------------

def block_idx(w: int, v: int, k: int, l: int):  # noqa: E741 -- l mirrors the paper's block index
    return list(range(max(k, l), min(w - k, v - l) + 1))


def block_pairs(w: int, v: int):
    """All (k,l) with W_k∩V_l ≠ ∅ (zero-order blocks are skipped, per the paper)."""
    return [(k, l) for k in range(w // 2 + 1) for l in range(v // 2 + 1) if block_idx(w, v, k, l)]  # noqa: E741


def r_block(w, v, k, l, y, beta_w=beta):  # noqa: E741
    """M_{k,l}(y)_{i,j} = Σ_{t,s} β^{t,w}_{i,j,k} β^{s,v}_{i,j,l} y^{t,s}_{i,j}. y maps (t,s,i,j)->Fr,
    missing = 0. beta_w only substitutes the w-side factor (the corrupt-control hook)."""
    idx = block_idx(w, v, k, l)
    M = [[Fr(0) for _ in idx] for _ in idx]
    for a, i in enumerate(idx):
        for b, j in enumerate(idx):
            acc = Fr(0)
            for t in range(min(i, j) + 1):
                bw = beta_w(w, i, j, k, t)
                if not bw:
                    continue
                for s in range(min(i, j) + 1):
                    if not possible(w, v, i, j, t, s):
                        continue
                    yv = y.get((t, s, i, j), Fr(0))
                    if yv:
                        acc += bw * beta(v, i, j, l, s) * yv
            M[a][b] = acc
    return M


def rp_block(w, v, k, l, y, y0, beta_w=beta):  # noqa: E741
    """M'_{k,l}(y)_{i,j} = Σ_{t,s} β^{t,w}_{i,j,k} β^{s,v}_{i,j,l} (y^{0,0}_{i+j−t−s,0} − y^{t,s}_{i,j}).
    y0 maps the pairwise half-distance r -> y^{0,0}_{r,0}. Impossible (t,s) are skipped ENTIRELY (their
    tensor matrix M^{t,w}∘M^{s,v} is zero, so they contribute neither the y nor the y0 term)."""
    idx = block_idx(w, v, k, l)
    M = [[Fr(0) for _ in idx] for _ in idx]
    for a, i in enumerate(idx):
        for b, j in enumerate(idx):
            acc = Fr(0)
            for t in range(min(i, j) + 1):
                bw = beta_w(w, i, j, k, t)
                if not bw:
                    continue
                for s in range(min(i, j) + 1):
                    if not possible(w, v, i, j, t, s):
                        continue
                    bv = beta(v, i, j, l, s)
                    if not bv:
                        continue
                    r = i + j - t - s
                    acc += bw * bv * (y0.get(r, Fr(0)) - y.get((t, s, i, j), Fr(0)))
            M[a][b] = acc
    return M


# ---- combinatorial oracle: real constant-weight-code triple counts (eq. 62/63) ---------------------------

def _multinom(a: int, b1: int, b2: int, b3: int) -> int:
    """binom(a; b1,b2,b3) = number of pairwise disjoint subsets of sizes b1,b2,b3 in a set of size a;
    0 if any part is negative or b1+b2+b3 > a."""
    if b1 < 0 or b2 < 0 or b3 < 0 or b1 + b2 + b3 > a:
        return 0
    return C(a, b1) * C(a - b1, b2) * C(a - b1 - b2, b3)


def code_y(n: int, w: int, code):
    """y^{t,s}_{i,j} and y^{0,0}_{r,0} from brute triple/pair counting over C³/C² (eqs. 62/63). Codewords are
    int bitmasks of weight w in [0, 2^n). Returns (y keyed (t,s,i,j), y0 keyed r)."""
    v = n - w
    words = list(code)
    m = len(words)
    assert m > 0 and all(x.bit_count() == w for x in words)
    mu: dict = {}
    mu0: dict = {}
    for X in words:
        nX = ~X
        for Y in words:
            r0 = (X & ~Y).bit_count()
            mu0[r0] = mu0.get(r0, 0) + 1
            for Z in words:
                i = (X & ~Y).bit_count()
                j = (X & ~Z).bit_count()
                t = (X & ~Y & ~Z).bit_count()
                s = (Y & Z & nX).bit_count()
                key = (t, s, i, j)
                mu[key] = mu.get(key, 0) + 1
    y = {}
    for (t, s, i, j), cnt in mu.items():
        den = _multinom(w, i - t, j - t, t) * _multinom(v, i - s, j - s, s)
        assert den, f"triple count at impossible quad {(t, s, i, j)}"
        y[(t, s, i, j)] = Fr(cnt, m * den)
    y0 = {}
    for r, cnt in mu0.items():
        den = C(w, r) * C(v, r)
        assert den, f"pair count at impossible half-distance {r}"
        y0[r] = Fr(cnt, m * den)
    return y, y0


# ---- test codes ------------------------------------------------------------------------------------------

def _mask(points):
    m = 0
    for p in points:
        m |= 1 << p
    return m


def johnson_space(n: int, w: int):
    return [x for x in range(1 << n) if x.bit_count() == w]


FANO = [_mask(p) for p in ((0, 1, 2), (0, 3, 4), (0, 5, 6), (1, 3, 5), (1, 4, 6), (2, 3, 6), (2, 4, 5))]
STS9 = [_mask(p) for p in ((0, 1, 2), (3, 4, 5), (6, 7, 8), (0, 3, 6), (1, 4, 7), (2, 5, 8),
                           (0, 4, 8), (1, 5, 6), (2, 3, 7), (0, 5, 7), (1, 3, 8), (2, 4, 6))]


def _test_codes(n: int, w: int):
    full = johnson_space(n, w)
    codes = {"singleton": [full[0]], "johnson-space": full}
    if len(full) >= 2:
        codes["pair"] = [full[0], full[-1]]
    if (n, w) == (7, 3):
        codes["fano-STS(7)"] = FANO
    if (n, w) == (9, 3):
        codes["AG(2,3)-STS(9)"] = STS9
    return codes


def validate_code(n: int, w: int, code, beta_w=beta) -> bool:
    """All R and R' blocks PSD for a real constant-weight code — the necessary condition (64)."""
    y, y0 = code_y(n, w, code)
    v = n - w
    for (k, l) in block_pairs(w, v):  # noqa: E741
        if not is_psd_exact(r_block(w, v, k, l, y, beta_w)):
            return False
        if not is_psd_exact(rp_block(w, v, k, l, y, y0, beta_w)):
            return False
    return True


def objective_identity_holds(n: int, w: int, code) -> bool:
    """eq. (66): |C| = Σ_i C(w,i)·C(v,i)·y^{0,0}_{i,0} — exact; pins the multinomial normalization."""
    v = n - w
    _y, y0 = code_y(n, w, code)
    return sum(C(w, i) * C(v, i) * y0.get(i, Fr(0)) for i in range(min(w, v) + 1)) == len(list(code))


def orbit_merge_holds(n: int, w: int, code) -> bool:
    """(65)(iii): a real code's y is constant on canon orbits, and y^{0,0}_{r,0} agrees with the (t,s,i,j) =
    (0,0,r,0) entry of y."""
    v = n - w
    y, y0 = code_y(n, w, code)
    by_key: dict = {}
    for (t, s, i, j), val in y.items():
        key = canon(t, s, i, j)
        if by_key.setdefault(key, val) != val:
            return False
    for r, val in y0.items():
        if y.get((0, 0, r, 0), Fr(0)) != val:
            return False
    for key in by_key:
        if rep_quad(w, v, key) is None:      # every realized orbit must have a possible representative
            return False
    return True


def main() -> int:
    cells = [(4, 2), (5, 2), (6, 3), (7, 3), (8, 4), (9, 3)]
    results: dict = {"codes": {}, "identities": {}, "control": {}}
    all_ok = True
    for (n, w) in cells:
        tag = f"n={n},w={w}"
        results["codes"][tag] = {}
        results["identities"][tag] = {}
        for name, code in _test_codes(n, w).items():
            ok = validate_code(n, w, code)
            ident = objective_identity_holds(n, w, code) and orbit_merge_holds(n, w, code)
            results["codes"][tag][name] = ok
            results["identities"][tag][name] = ident
            all_ok = all_ok and ok and ident

    # Control: corrupting the w-side β factor (transposed binomial, the Phase-0 fault) MUST break PSD.
    broke = any(not validate_code(n, w, list(_test_codes(n, w).values())[-1], beta_w=tb.beta_corrupt)
                for (n, w) in ((6, 3), (7, 3), (8, 4)))
    results["control"]["corrupt_beta_breaks_psd"] = broke

    # Structural facts a fresh session should not re-derive.
    results["structure"] = {
        "n17_w7_free_vars_d6": len(free_keys(7, 10, 6)),
        "n17_w7_blocks": len(block_pairs(7, 10)),
        "n17_w7_largest_block": max(len(block_idx(7, 10, k, l)) for (k, l) in block_pairs(7, 10)),  # noqa: E741
    }

    verdict = "GREEN" if all_ok and broke else "RED"
    results["verdict"] = verdict
    results["reading"] = (
        "GREEN = every real constant-weight code's Johnson-Terwilliger blocks (both families, all (k,l)) are "
        "exactly PSD, the eq.(66) counting identity and the (65)(iii) orbit merge hold exactly, AND the "
        "transposed-binomial corruption breaks PSD -> the Section-III structure (product-of-two-eq.(7)-β "
        "blocks, quadruple variables, multinomial normalization) is transcribed correctly and the test has "
        "teeth. This is D1 step 1; the SDP producer (terwilliger_cwc_sdp.py) builds on these functions. "
        "RED = a sign/index/normalization bug."
    )
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(results, indent=2) + "\n")

    print(f"terwilliger cwc structure: {verdict}")
    for tag, codes in results["codes"].items():
        print(f"  {tag}: " + ", ".join(f"{k}={'ok' if val else 'FAIL'}" for k, val in codes.items())
              + " | identities: " + ", ".join(f"{k}={'ok' if val else 'FAIL'}"
                                              for k, val in results["identities"][tag].items()))
    print(f"  control (corrupt β breaks PSD): {broke}")
    print(f"  structure: {results['structure']}")
    print(f"  -> {OUT}")
    return 0 if verdict == "GREEN" else 1


if __name__ == "__main__":
    raise SystemExit(main())
