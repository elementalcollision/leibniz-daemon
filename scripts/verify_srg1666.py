"""Kernel-attested AUDIT of Belousova-Makhnev-Tokbaeva (2026): "A strongly regular graph
with parameters (1666, 105, 0, 7) does not exist" (Vestnik Perm. Univ. 1(72), 29-34;
DOI 10.17072/1993-0550-2026-1-29-34; Russian).

WHAT THIS AUDIT FINDS (all from first principles, exact rational arithmetic; the intersection
array {105,104,98,7,1; 1,7,98,104,105} is the bipartite double of the putative srg(1666,105,0,7)):

  * Lemmas 1-3 of the paper reproduce EXACTLY -- except a single typo: Lemma 1 prints
    p^2_{33}=543, but it is forced to 1461 (by the duality k_2 p^2_{33}=k_3 p^3_{23} and the
    row sum p^2_{31}+p^2_{33}+p^2_{35}=k_3=1560). Not load-bearing.
  * The proof of Theorem 1 does NOT establish non-existence. Its contradiction compares two
    computations of the mean lambda-bar of the auxiliary graph Lambda (the distance-2 graph on
    Gamma_2(u), p^2_{22}=1461-regular on k_2=1560 vertices). Done with correct arithmetic BOTH
    routes are identically 1999388/1461: the paper's apparent gap (1362.905 vs 1368.09) is an
    artifact of two compensating errors -- using 104 for the true non-neighbour count
    1560-1-1461=98, and dividing by 1560 instead of by the degree 1461. The structural reason:
    [222]_{Lemma2}+[224]_{Lemma2}=1364+97=1461=p^2_{22}, so S1 - S2 = 98*(1461-1364-97)=0.
  * The triple-intersection method leaves the array FEASIBLE. Every metrically-valid base triple
    (with all zero-Krein equations imposed) has a non-negative integer solution; the all-distance-2
    config (Lemma 3) has EXACTLY 8 solutions (r1 in {0..7}). Independently confirmed by the
    canonical tool the authors cite, sage-drg (check_feasible clean; tripleSolution_generator(2,2,2)
    -> 8 solutions; no zero-solution config).

CONCLUSION (report-only, audit tier): the parameter set srg(1666,105,0,7) is NOT resolved by the
given proof and should be regarded as OPEN. We make NO claim that the graph exists or does not
exist -- only that this argument does not decide it. LLMs propose nothing; exact arithmetic and
the Lean 4.31 kernel decide.

The Lean 4.31 kernel re-decides the finite core:
  srg1666_contradiction_vacuous : the two mean-lambda sums are EQUAL (1461*1460-98*1364 = 98*97+1461*1362).
  srg1666_row_identity          : [222]+[224]=p^2_22 (1364+97=1461) -- the structural reason.
  srg1666_paper_gap_from_104    : the paper's 104 manufactures the gap (1461*1460-104*1364 != 98*97+1461*1362).
  srg1666_lemma3_feasible       : all 8 Lemma-3 witnesses (r1=0..7) satisfy every marginal, all zero-Krein
                                  equations, and non-negativity -> the (2,2,2) system is feasible.
  srg1666_lemma2_feasible       : the unique Lemma-2 witness satisfies its marginals + Krein + non-negativity.
  srg1666_control_r1_8          : r1=8 breaks non-negativity (a discriminating negative control).

Plain `decide` -- no native_decide, no sorry; #print axioms shows at most [propext]. Report-only.

Run:  python scripts/verify_srg1666.py            (exact arithmetic; writes the cert)
      python scripts/verify_srg1666.py --kernel   (also re-decide via Lean 4.31 in Docker)
"""
from __future__ import annotations

from fractions import Fraction as F
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
CERT = _ROOT / "docs" / "crt" / "srg1666_audit.lean"

D = 5
_B = [105, 104, 98, 7, 1, 0]     # b_0..b_5
_C = [0, 1, 7, 98, 104, 105]      # c_0..c_5
_K = _B[0]
_A = [_K - _B[i] - _C[i] for i in range(D + 1)]   # a_i (all 0: bipartite)
_KSZ = [1]
for _i in range(1, D + 1):
    _KSZ.append(_KSZ[-1] * _B[_i - 1] // _C[_i])
_V = sum(_KSZ)                    # 3332
_THETA = [F(105), F(14), F(7), F(-7), F(-14), F(-105)]
_M = [1, 560, 1105, 1105, 560, 1]


def _bb(i): return _B[i] if 0 <= i <= D else 0
def _cc(i): return _C[i] if 0 <= i <= D else 0
def _aa(i): return _A[i] if 0 <= i <= D else 0


def intersection_numbers():
    """p[i][j][k] via A_1(A_j A_k)=(A_1 A_j)A_k, from the intersection array (first principles)."""
    p = [[[F(0)] * (D + 1) for _ in range(D + 1)] for _ in range(D + 1)]
    for j in range(D + 1):
        p[0][j][j] = F(_KSZ[j])
    for i in range(0, D):
        if _bb(i) == 0:
            continue
        for j in range(D + 1):
            for k in range(D + 1):
                rhs = _bb(j - 1) * (p[i][j - 1][k] if j - 1 >= 0 else F(0))
                rhs += _aa(j) * p[i][j][k]
                rhs += _cc(j + 1) * (p[i][j + 1][k] if j + 1 <= D else F(0))
                rhs -= _aa(i) * p[i][j][k]
                rhs -= _cc(i) * (p[i - 1][j][k] if i - 1 >= 0 else F(0))
                p[i + 1][j][k] = rhs / _bb(i)
    return p


def _inv(M):
    n = len(M)
    A = [[M[i][j] for j in range(n)] + [F(int(i == j)) for j in range(n)] for i in range(n)]
    for col in range(n):
        piv = next(r for r in range(col, n) if A[r][col] != 0)
        A[col], A[piv] = A[piv], A[col]
        pv = A[col][col]
        A[col] = [x / pv for x in A[col]]
        for r in range(n):
            if r != col and A[r][col] != 0:
                f = A[r][col]
                A[r] = [A[r][j] - f * A[col][j] for j in range(2 * n)]
    return [[A[i][n + j] for j in range(n)] for i in range(n)]


def eigenmatrices():
    """P[l][i] (primal), Q[l][i]=v*(P^-1)[i][l] (dual, myQ; paperQ = myQ^T)."""
    P = [[F(0)] * (D + 1) for _ in range(D + 1)]
    for ell in range(D + 1):
        P[ell][0] = F(1)
        P[ell][1] = _THETA[ell]
        for i in range(1, D):
            P[ell][i + 1] = ((_THETA[ell] - _aa(i)) * P[ell][i] - _bb(i - 1) * P[ell][i - 1]) / _cc(i + 1)
    Pinv = _inv(P)
    Q = [[F(_V) * Pinv[i][ell] for i in range(D + 1)] for ell in range(D + 1)]
    return P, Q


def krein_zeros(P, Q):
    """Krein q^k_{ij} via Hadamard structure constants; return (qkij, zero-list with i,j,k>=1)."""
    Mmat = [[Q[k][s] for k in range(D + 1)] for s in range(D + 1)]
    Minv = _inv(Mmat)
    qkij = {}
    for i in range(D + 1):
        for j in range(D + 1):
            w = [Q[i][s] * Q[j][s] for s in range(D + 1)]
            qkij[(i, j)] = [sum(Minv[k][s] * w[s] for s in range(D + 1)) for k in range(D + 1)]
    zeros = [(i, j, k) for i in range(1, D + 1) for j in range(1, D + 1) for k in range(1, D + 1)
             if qkij[(i, j)][k] == 0]
    return qkij, zeros


# ---- triple intersection solver (Vidali/Coolsaet-Jurisic), exact ----
_IDX = [(i, j, h) for i in range(D + 1) for j in range(D + 1) for h in range(D + 1)]
_POS = {t: n for n, t in enumerate(_IDX)}
_N = len(_IDX)


def _qc(Q, r, i):  # correct dual entry Q_{r,i}=paperQ[r][i]=myQ[i][r]
    return Q[i][r]


def _build(p, Q, zeros, W, U, V):
    eqs = []
    def P(a, b, c): return p[a][b][c]
    for j in range(D + 1):
        for h in range(D + 1):
            c = {}
            for i in range(D + 1):
                c[(i, j, h)] = c.get((i, j, h), F(0)) + 1
            eqs.append((c, P(U, j, h)))
    for i in range(D + 1):
        for h in range(D + 1):
            c = {}
            for j in range(D + 1):
                c[(i, j, h)] = c.get((i, j, h), F(0)) + 1
            eqs.append((c, P(V, i, h)))
    for i in range(D + 1):
        for j in range(D + 1):
            c = {}
            for h in range(D + 1):
                c[(i, j, h)] = c.get((i, j, h), F(0)) + 1
            eqs.append((c, P(W, i, j)))
    for (i, j, h) in _IDX:
        if P(W, i, j) == 0 or P(U, j, h) == 0 or P(V, i, h) == 0:
            eqs.append(({(i, j, h): F(1)}, F(0)))
    for (i0, j0, h0) in zeros:
        c = {}
        for (r, s, t) in _IDX:
            co = _qc(Q, r, i0) * _qc(Q, s, j0) * _qc(Q, t, h0)
            if co != 0:
                c[(r, s, t)] = c.get((r, s, t), F(0)) + co
        eqs.append((c, F(0)))
    return eqs


def _solve(eqs):
    rows = []
    for coeffs, rhs in eqs:
        row = [F(0)] * (_N + 1)
        for var, co in coeffs.items():
            row[_POS[var]] += co
        row[_N] = rhs
        rows.append(row)
    pivots = {}
    used = 0
    for col in range(_N):
        pr = next((rr for rr in range(used, len(rows)) if rows[rr][col] != 0), None)
        if pr is None:
            continue
        rows[used], rows[pr] = rows[pr], rows[used]
        pv = rows[used][col]
        rows[used] = [x / pv for x in rows[used]]
        for rr in range(len(rows)):
            if rr != used and rows[rr][col] != 0:
                f = rows[rr][col]
                rows[rr] = [rows[rr][k] - f * rows[used][k] for k in range(_N + 1)]
        pivots[col] = used
        used += 1
    for rr in range(len(rows)):
        if all(rows[rr][k] == 0 for k in range(_N)) and rows[rr][_N] != 0:
            return None, None
    free = [c for c in range(_N) if c not in pivots]
    sol = {}
    for col, rr in pivots.items():
        sol[col] = (rows[rr][_N], {f: -rows[rr][f] for f in free if rows[rr][f] != 0})
    return sol, free


def _materialize(sol, free, assign):
    """Return dict (i,j,h)->Int value for a specific integer assignment of free vars."""
    out = {}
    for t in _IDX:
        c = _POS[t]
        if c in sol:
            const, fp = sol[c]
            val = const + sum(co * assign.get(f, F(0)) for f, co in fp.items())
        elif c in free:
            val = assign.get(c, F(0))
        else:
            val = F(0)
        out[t] = val
    return out


def _valid_table(p, Q, zeros, W, U, V, table):
    """Check a materialized table against the FULL system: marginals, non-negativity, all zero-Krein."""
    def g(i, j, h): return table.get((i, j, h), F(0))
    for j in range(D + 1):
        for h in range(D + 1):
            if sum(g(i, j, h) for i in range(D + 1)) != p[U][j][h]:
                return False
    for i in range(D + 1):
        for h in range(D + 1):
            if sum(g(i, j, h) for j in range(D + 1)) != p[V][i][h]:
                return False
    for i in range(D + 1):
        for j in range(D + 1):
            if sum(g(i, j, h) for h in range(D + 1)) != p[W][i][j]:
                return False
    if any(v < 0 or v.denominator != 1 for v in table.values()):
        return False
    for (i0, j0, h0) in zeros:
        s = F(0)
        for (r, s2, t), v in table.items():
            if v != 0:
                s += _qc(Q, r, i0) * _qc(Q, s2, j0) * _qc(Q, t, h0) * v
        if s != 0:
            return False
    return True


def checks() -> dict:
    p = intersection_numbers()
    P, Q = eigenmatrices()
    qkij, zeros = krein_zeros(P, Q)

    # Lemma 1 faithfulness (with the 543->1461 typo catch)
    lemma1 = {
        (1, 1, 1): 0, (1, 1, 2): 104, (1, 2, 3): 1456, (1, 3, 4): 104, (1, 4, 5): 1,
        (2, 1, 1): 7, (2, 1, 2): 0, (2, 1, 3): 98, (2, 2, 2): 1461, (2, 2, 4): 98,
        (2, 3, 5): 1, (2, 4, 4): 7, (3, 1, 2): 98, (3, 2, 3): 1461, (3, 3, 4): 98,
        (3, 2, 5): 1, (4, 1, 3): 104, (4, 2, 2): 1456, (4, 2, 4): 104, (4, 3, 3): 1456,
        (5, 1, 4): 105, (5, 2, 3): 1560,
    }
    lemma1_ok = all(p[i][j][k] == v for (i, j, k), v in lemma1.items())
    p2_33 = int(p[2][3][3])                     # 1461 (paper printed 543)
    typo_forced = (_KSZ[2] * p[2][3][3] == _KSZ[3] * p[3][2][3]     # duality
                   and p[2][3][1] + p[2][3][3] + p[2][3][5] == _KSZ[3])  # row sum

    # Lemma 2 (config W=2,U=4,V=2) unique; Lemma 3 (W=U=V=2) one-parameter family
    sol2, free2 = _solve(_build(p, Q, zeros, 2, 4, 2))
    sol3, free3 = _solve(_build(p, Q, zeros, 2, 2, 2))
    lemma2_unique = (free2 == [])
    lemma3_oneparam = (len(free3) == 1)

    # the vacuity of the contradiction (exact integers)
    p2_22 = int(p[2][2][2])          # 1461 (= degree of Lambda)
    p2_24 = int(p[2][2][4])          # 98   (= non-neighbours of v in Lambda)
    l2_222 = 1364                    # [222] in Lemma 2 (edges each non-neighbour sends to Lambda(v))
    l2_224 = 97                      # [224] in Lemma 2 (used in the f4 double-count)
    l3_222_base = p2_22 - p2_24 - 1  # 1362 = constant term of [222] in Lemma 3 (r1=0)
    # sum of lambda over the 1461 edges at v, computed two ways; both must equal it
    S1 = p2_22 * (p2_22 - 1) - p2_24 * l2_222      # 1461*1460 - 98*1364  (edge-count route)
    S2 = p2_24 * l2_224 + p2_22 * l3_222_base      # 98*97 + 1461*1362    (Lemma-3 / f4 route)
    contradiction_vacuous = (S1 == S2 == 1999388)
    row_identity = (l2_222 + l2_224 == p2_22)      # 1364+97=1461
    paper_gap_from_104 = (p2_22 * (p2_22 - 1) - 104 * l2_222 != S2)

    # feasibility: all 8 Lemma-3 witnesses satisfy the FULL system incl. Krein; r1=8 fails.
    # The free variable is [444] = a; the paper's r1 = [113] = 7 - a, so a = 7 - r1.
    freec = free3[0]
    wit_valid = {}
    for r1 in range(0, 9):                       # 0..7 valid; 8 is the out-of-range control
        tbl = _materialize(sol3, free3, {freec: F(7 - r1)})
        assert int(tbl[(1, 1, 3)]) == r1         # [113] == r1 by construction
        wit_valid[r1] = _valid_table(p, Q, zeros, 2, 2, 2, tbl)
    lemma3_feasible_8 = all(wit_valid[r1] for r1 in range(0, 8))
    control_r1_8 = (wit_valid[8] is False)       # r1=8 -> [444]=-1<0 -> non-negativity fails

    # Lemma 2 witness validity
    tbl2 = _materialize(sol2, free2, {})
    lemma2_valid = _valid_table(p, Q, zeros, 2, 4, 2, tbl2)

    ok = (lemma1_ok and typo_forced and lemma2_unique and lemma3_oneparam
          and contradiction_vacuous and row_identity and paper_gap_from_104
          and lemma3_feasible_8 and control_r1_8 and lemma2_valid)

    return {
        "n_vertices": _V, "eigenvalues_ok": _THETA[1] == 14 and _THETA[4] == -14,
        "lemma1_ok": lemma1_ok, "p2_33": p2_33, "p2_33_typo_forced_to_1461": typo_forced,
        "lemma2_unique": lemma2_unique, "lemma3_oneparam": lemma3_oneparam,
        "S1": S1, "S2": S2, "contradiction_vacuous": contradiction_vacuous,
        "row_identity": row_identity, "paper_gap_from_104": paper_gap_from_104,
        "lemma3_feasible_8": lemma3_feasible_8, "control_r1_8": control_r1_8,
        "lemma2_valid": lemma2_valid, "num_zero_krein": len(zeros),
        "ok": ok,
        "_sol3": sol3, "_free3": free3, "_sol2": sol2, "_free2": free2,
        "_p": p, "_Q": Q, "_zeros": zeros,
    }


# ---------------- Lean 4.31 certificate ----------------
_HDR = r"""/-
  Kernel-attested AUDIT of Belousova, Makhnev, Tokbaeva, "A strongly regular graph with parameters
  (1666, 105, 0, 7) does not exist" (Vestnik Perm. Univ. 1(72), 2026, 29-34; DOI
  10.17072/1993-0550-2026-1-29-34; Russian). The array {105,104,98,7,1; 1,7,98,104,105} is the
  bipartite double of the putative srg(1666,105,0,7).

  The paper's Theorem 1 proof compares two computations of the mean lambda of the auxiliary graph
  Lambda (distance-2 graph on Gamma_2(u); degree p^2_22=1461 on k_2=1560 vertices). Done correctly
  BOTH equal 1999388/1461; the printed gap (1362.905 vs 1368.09) is an artifact of two compensating
  arithmetic errors -- 104 for the true non-neighbour count 1560-1-1461=98, and dividing by 1560
  instead of 1461. The kernel re-decides the finite core (plain `decide`, exact Int arithmetic):

    srg1666_contradiction_vacuous : the two mean-lambda sums are EQUAL (1461*1460-98*1364 = 98*97+1461*1362).
    srg1666_row_identity          : [222]_L2 + [224]_L2 = p^2_22  (1364+97=1461) -- why S1=S2.
    srg1666_paper_gap_from_104    : the paper's 104 manufactures the gap.
    srg1666_lemma3_feasible       : all 8 Lemma-3 triple witnesses (r1=0..7) satisfy every marginal,
                                    all zero-Krein equations, and non-negativity => the (2,2,2) system
                                    is feasible => the triple-intersection method does NOT rule out the array.
    srg1666_lemma2_feasible       : the unique Lemma-2 witness satisfies its marginals + Krein + non-negativity.
    srg1666_control_r1_8          : r1=8 breaks non-negativity (a discriminating negative control).

  Report-only, audit tier: this shows the given proof does not decide the parameter set (treat as OPEN);
  it does NOT claim the graph exists or does not exist. Plain `decide`; no native_decide, no sorry;
  #print axioms shows at most [propext].
-/
set_option maxHeartbeats 0
set_option maxRecDepth 1000000

abbrev Tri := Nat × Nat × Nat × Int          -- (i, j, h, value); unlisted entries are 0
abbrev Tbl := List Tri

-- data lookups (flattened 6x6 tables, row-major index 6*i+j)
def look (xs : List Int) (i j : Nat) : Int := xs.getD (6 * i + j) 0

def tget (T : Tbl) (i j h : Nat) : Int :=
  (T.filter (fun e => e.1 == i && e.2.1 == j && e.2.2.1 == h)).foldl (fun a e => a + e.2.2.2) 0

def margI (T : Tbl) (j h : Nat) : Int :=
  (T.filter (fun e => e.2.1 == j && e.2.2.1 == h)).foldl (fun a e => a + e.2.2.2) 0
def margJ (T : Tbl) (i h : Nat) : Int :=
  (T.filter (fun e => e.1 == i && e.2.2.1 == h)).foldl (fun a e => a + e.2.2.2) 0
def margH (T : Tbl) (i j : Nat) : Int :=
  (T.filter (fun e => e.1 == i && e.2.1 == j)).foldl (fun a e => a + e.2.2.2) 0

def allPairs : List (Nat × Nat) :=
  (List.range 6).flatMap (fun i => (List.range 6).map (fun j => (i, j)))

-- marginals against p-slices pU,pV,pW; non-negativity; and all zero-Krein equations (Q3 = 3*Q)
def marginalsOK (T : Tbl) (pU pV pW : List Int) : Bool :=
  allPairs.all (fun p => (margI T p.1 p.2 == look pU p.1 p.2)
                      && (margJ T p.1 p.2 == look pV p.1 p.2)
                      && (margH T p.1 p.2 == look pW p.1 p.2))
def nonnegOK (T : Tbl) : Bool := T.all (fun e => decide (0 <= e.2.2.2))
def kreinOK (T : Tbl) (Q3 : List Int) (zk : List (Nat × Nat × Nat)) : Bool :=
  zk.all (fun z =>
    (T.foldl (fun a e => a + look Q3 e.1 z.1 * look Q3 e.2.1 z.2.1 * look Q3 e.2.2.1 z.2.2 * e.2.2.2) 0) == 0)
def validTbl (T : Tbl) (pU pV pW Q3 : List Int) (zk : List (Nat × Nat × Nat)) : Bool :=
  marginalsOK T pU pV pW && nonnegOK T && kreinOK T Q3 zk
"""


def _lean_intlist(xs):
    return "[" + ", ".join(str(int(x)) for x in xs) + "]"


def _lean_tbl(table):
    items = [(i, j, h, int(v)) for (i, j, h), v in sorted(table.items()) if v != 0]
    return "[" + ", ".join(f"({i}, {j}, {h}, {v})" for (i, j, h, v) in items) + "]"


def build_lean_cert(r=None) -> tuple[str, list[str]]:
    if r is None:
        r = checks()
    p, Q, zeros = r["_p"], r["_Q"], r["_zeros"]
    sol3, free3, sol2, free2 = r["_sol3"], r["_free3"], r["_sol2"], r["_free2"]
    freec = free3[0]

    # p-slices for the two configs (row-major 6x6 int lists)
    def slice_p(a):
        return [int(p[a][i][j]) for i in range(D + 1) for j in range(D + 1)]
    p2 = slice_p(2)            # config (2,2,2): pU=pV=pW=p^2
    p4 = slice_p(4)            # config (2,4,2): U=4 -> pU=p^4 ; V=2 -> pV=p^2 ; W=2 -> pW=p^2
    # look(Q3, r, i0) must equal 3*_qc(Q,r,i0) = 3*Q[i0][r]; so Q3T[6*r+i] = 3*Q[i][r]:
    Q3T = [int(3 * Q[j][i]) for i in range(D + 1) for j in range(D + 1)]

    zk = "[" + ", ".join(f"({i}, {j}, {h})" for (i, j, h) in zeros) + "]"

    # 8 Lemma-3 witnesses (r1=0..7) + r1=8 control + Lemma-2 witness (a = 7 - r1)
    wtbls = {r1: _materialize(sol3, free3, {freec: F(7 - r1)}) for r1 in range(0, 9)}
    tbl2 = _materialize(sol2, free2, {})

    data = []
    data.append(f"def p2 : List Int := {_lean_intlist(p2)}")
    data.append(f"def p4 : List Int := {_lean_intlist(p4)}")
    data.append(f"def Q3 : List Int := {_lean_intlist(Q3T)}")
    data.append(f"def zk : List (Nat × Nat × Nat) := {zk}")
    for r1 in range(0, 8):
        data.append(f"def w{r1} : Tbl := {_lean_tbl(wtbls[r1])}")
    data.append(f"def w8 : Tbl := {_lean_tbl(wtbls[8])}")
    data.append(f"def wL2 : Tbl := {_lean_tbl(tbl2)}")
    data.append("def lemma3wits : List Tbl := [w0, w1, w2, w3, w4, w5, w6, w7]")

    thms = []
    thms.append("theorem srg1666_row_identity : (1364 : Int) + 97 = 1461 := by decide")
    thms.append("theorem srg1666_contradiction_vacuous : "
                "(1461*1460 - 98*1364 : Int) = 98*97 + 1461*1362 := by decide")
    thms.append("theorem srg1666_paper_gap_from_104 : "
                "(1461*1460 - 104*1364 : Int) ≠ 98*97 + 1461*1362 := by decide")
    thms.append("theorem srg1666_lemma3_feasible : "
                "lemma3wits.all (fun T => validTbl T p2 p2 p2 Q3 zk) = true := by decide")
    thms.append("theorem srg1666_lemma2_feasible : "
                "validTbl wL2 p4 p2 p2 Q3 zk = true := by decide")
    thms.append("theorem srg1666_control_r1_8 : "
                "validTbl w8 p2 p2 p2 Q3 zk = false := by decide")
    names = ["srg1666_row_identity", "srg1666_contradiction_vacuous", "srg1666_paper_gap_from_104",
             "srg1666_lemma3_feasible", "srg1666_lemma2_feasible", "srg1666_control_r1_8"]
    src = _HDR + "\n" + "\n".join(data) + "\n\n" + "\n\n".join(thms) + "\n\n" + \
        "".join(f"#print axioms {n}\n" for n in names)
    return src, names


def _leg_decls(src: str):
    prefix = src.split("\ntheorem ", 1)[0]
    out = []
    for chunk in src.split("\ntheorem ")[1:]:
        nm = chunk.split(" ", 1)[0].rstrip(":")
        thm = "theorem " + chunk.split("\n\n", 1)[0].split("\n#print", 1)[0].rstrip()
        out.append((nm, f"{prefix}\n\n{thm}\n\n#print axioms {nm}\n"))
    return out


def run_kernel(src: str, timeout_s: int = 300) -> dict:
    try:
        from leibniz.backends.lean_repl import LeanReplBackend, available
    except Exception:
        return {"status": "unavailable (import)"}
    if not available():
        return {"status": "unavailable (docker/image)"}
    legs = {}
    for name, decl in _leg_decls(src):
        body = "\n".join(ln for ln in decl.splitlines() if not ln.startswith("import "))
        res = LeanReplBackend(timeout_s=timeout_s)._run(body, ())
        if not isinstance(res, dict):
            legs[name] = {"verified": False, "status": "timeout/unavailable"}
            continue
        msgs = res.get("messages", [])
        errors = [m.get("data") for m in msgs if m.get("severity") == "error"]
        axioms = " ".join(str(m.get("data", "")) for m in msgs
                          if "axiom" in str(m.get("data", "")).lower() or "depend" in str(m.get("data", "")).lower())
        cheated = ("sorryAx" in axioms) or ("native" in axioms.lower())
        legs[name] = {"verified": not errors and not cheated, "axioms": axioms.strip(),
                      "errors": errors[:3]}
    return {"status": "checked", "legs": legs, "all_verified": all(v.get("verified") for v in legs.values())}


def main() -> int:
    import sys
    r = checks()
    print("=== AUDIT: srg(1666,105,0,7) non-existence (Belousova-Makhnev-Tokbaeva 2026) ===")
    print(f"  bipartite-double DRG on {r['n_vertices']} vertices; Lemma 1 reproduced: {r['lemma1_ok']}")
    print(f"  p^2_33 = {r['p2_33']} (paper printed 543; forced to 1461: {r['p2_33_typo_forced_to_1461']})")
    print(f"  Lemma 2 unique: {r['lemma2_unique']}   Lemma 3 one-parameter: {r['lemma3_oneparam']}")
    print(f"  contradiction vacuous: S1={r['S1']}  S2={r['S2']}  equal={r['contradiction_vacuous']}")
    print(f"  structural [222]+[224]=p^2_22 (1364+97=1461): {r['row_identity']}   "
          f"paper's 104 breaks it: {r['paper_gap_from_104']}")
    print(f"  Lemma-3 all 8 witnesses (r1=0..7) valid (marginals+Krein+nonneg): {r['lemma3_feasible_8']}   "
          f"r1=8 control fails: {r['control_r1_8']}")
    print(f"  Lemma-2 witness valid: {r['lemma2_valid']}   #zero-Krein eqns: {r['num_zero_krein']}")
    print(f"  ALL CHECKS OK: {r['ok']}")
    src, names = build_lean_cert(r)
    CERT.parent.mkdir(parents=True, exist_ok=True)
    CERT.write_text(src)
    print(f"  Lean cert ({len(names)} theorems) -> {CERT.relative_to(_ROOT)}")
    if "--kernel" in sys.argv:
        k = run_kernel(src)
        print(f"  kernel: {k['status']}")
        if k["status"] == "checked":
            for nm, v in k["legs"].items():
                print(f"    {nm}: verified={v.get('verified')}  {v.get('axioms','')}  {v.get('errors','')}")
            print(f"  all_verified={k['all_verified']}")
    return 0 if r["ok"] else 1


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(_ROOT))
    raise SystemExit(main())
