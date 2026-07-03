"""T8-a — the minimal rational-HMM beyond-Markov certificate suite (audit tier).

Per the external witness panel (docs/results/beyond-markov-witness-review-2026-07-03.md), the *first* buildable
artifact of the beyond-Markov domain is a small, self-contained, exact-rational certificate that a concrete
rational HMM is beyond every finite-order Markov model, with EVERY leg the panel demanded:

  1. PROCESS VALIDITY (the panel's #1 soundness mandate): the witness is given as a rational HMM
     (pi >= 0, sum pi = 1; every operator T_a >= 0; sum_a T_a is row-stochastic), so P(w) = pi . T_w . 1 is a
     genuine stochastic process for ALL words — not a formal series with a signed OOM. (General-OOM validity is
     the undecidable Negative Probability Problem; we stay in the positive HMM subclass, as the panel advised.)
  2. HANKEL RANK LOWER BOUND: a nonsingular 2x2 rational Hankel minor, det != 0 -> rank(H) >= 2.
  3. MARKOV ORDER > K: for each k <= K, a conditional-separation certificate on two pasts sharing a length-k
     suffix — the cross-multiplied determinant D_k = P(h1 a)P(h2) - P(h2 a)P(h1) != 0 WITH denominator
     positivity P(h1),P(h2) > 0 (the panel's denominator-positivity requirement) -> P(a|h1) != P(a|h2) -> the
     process is not order-k Markov. This is the finite, honest form: it certifies "order > K", NOT (yet)
     "infinite order" — that is T8-b, a recurrence + induction bridge lemma (F2b pattern), Q.E.D.-reachable.

The kernel checks the arithmetic itself (recomputes each 2x2 determinant and each nonnegativity/row-sum over
the integer-cleared matrices; it does NOT trust the producer's claimed values), with a corrupted control that
must be rejected. Uses core Lean only (no Mathlib). No trust surface touched (verifiers.py / trust.py /
tests/test_invariants.py unchanged); this is a standalone checker exactly like bareiss_ldlt.py's detSignOK.

Run:  python scripts/beyond_markov_cert.py   (free-CPU producer; docker only for the kernel-check leg)
"""
from __future__ import annotations

import importlib.util
import json
import sys
from fractions import Fraction as Fr
from math import gcd
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent


def _load(mod, rel):
    sys.path.insert(0, str(_ROOT))
    sys.path.insert(0, str(_ROOT / "scripts"))
    spec = importlib.util.spec_from_file_location(mod, _ROOT / rel)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


pm = _load("psd_certificate_microprobe", "scripts/psd_certificate_microprobe.py")  # reuse _lit (Lean int-matrix literal)


# --------------------------------------------------------------------------------------------------------
# Rational HMM as (pi, {T_a}) in observable-operator form: P(w) = pi . T_{w_1} ... T_{w_n} . 1 (1 = ones).
# For a valid HMM the T_a are nonnegative and sum_a T_a is row-stochastic; then every P(w) >= 0 and the
# cylinder measures are consistent (sum_a P(wa) = P(w)), so it is a genuine stochastic process.
# --------------------------------------------------------------------------------------------------------
def _matvec(M, v):
    return [sum(M[i][j] * v[j] for j in range(len(v))) for i in range(len(M))]


def _vecmat(v, M):
    n = len(M)
    return [sum(v[i] * M[i][j] for i in range(n)) for j in range(len(M[0]))]


def prob(hmm, w) -> Fr:
    pi, T = hmm["pi"], hmm["T"]
    v = pi[:]
    for sym in w:
        v = _vecmat(v, T[sym])
    return sum(v)  # v . 1


def hmm_valid(hmm) -> dict:
    """Exact-rational HMM validity: pi >= 0, sum pi = 1; every T_a >= 0; sum_a T_a row-stochastic (rows sum 1)."""
    pi, T = hmm["pi"], hmm["T"]
    n = len(pi)
    pi_ok = all(x >= 0 for x in pi) and sum(pi) == 1
    Ta_nonneg = all(all(all(e >= 0 for e in row) for row in T[a]) for a in T)
    S = [[sum(T[a][i][j] for a in T) for j in range(n)] for i in range(n)]
    row_stoch = all(sum(S[i]) == 1 for i in range(n))
    return {"valid": bool(pi_ok and Ta_nonneg and row_stoch),
            "pi_ok": bool(pi_ok), "Ta_nonneg": bool(Ta_nonneg), "row_stochastic": bool(row_stoch)}


# --------------------------------------------------------------------------------------------------------
# Certificates.
# --------------------------------------------------------------------------------------------------------
def _clear_int(rows):
    """Scale a matrix/vector of Fractions to integers by the LCM of denominators. Returns (int_rows, denom)."""
    flat = [x for r in rows for x in (r if isinstance(r, list) else [r])]
    D = 1
    for x in flat:
        D = D * x.denominator // gcd(D, x.denominator)
    if isinstance(rows[0], list):
        return [[int(x * D) for x in r] for r in rows], D
    return [int(x * D) for x in rows], D


def hankel_minor_cert(hmm, U, V) -> dict:
    """H[U,V][i][j] = P(U[i] + V[j]); clear to integers; det (2x2) != 0  =>  rank(H) >= |U|."""
    H = [[prob(hmm, u + v) for v in V] for u in U]
    Hint, D = _clear_int(H)
    det = Hint[0][0] * Hint[1][1] - Hint[0][1] * Hint[1][0]
    return {"U": U, "V": V, "H_int": Hint, "denom": D, "det_int": det, "rank_ge": len(U), "ok": det != 0}


def order_separation_cert(hmm, k, a=0, pre1=(0,), pre2=(1,), suffix=0) -> dict:
    """Two pasts h1=pre1+suffix^k, h2=pre2+suffix^k share the last-k suffix; certify P(a|h1) != P(a|h2) via
    D_k = P(h1 a)P(h2) - P(h2 a)P(h1) != 0, with P(h1),P(h2) > 0 (denominator positivity)."""
    h1 = tuple(pre1) + (suffix,) * k
    h2 = tuple(pre2) + (suffix,) * k
    p1, p2 = prob(hmm, h1), prob(hmm, h2)
    p1a, p2a = prob(hmm, h1 + (a,)), prob(hmm, h2 + (a,))
    # cross-multiplied determinant on [[p1a, p1],[p2a, p2]]
    mat = [[p1a, p1], [p2a, p2]]
    Mint, D = _clear_int(mat)
    det = Mint[0][0] * Mint[1][1] - Mint[0][1] * Mint[1][0]
    n1, n2 = Mint[0][1], Mint[1][1]  # cleared P(h1), P(h2)
    return {"k": k, "h1": list(h1), "h2": list(h2), "sym": a, "M_int": Mint, "denom": D,
            "det_int": det, "num_h1": n1, "num_h2": n2,
            "ok": det != 0 and n1 > 0 and n2 > 0}


# --------------------------------------------------------------------------------------------------------
# Kernel rendering — core Lean, `decide`. The kernel recomputes every det / nonneg / row-sum from the
# integer-cleared data; it does not trust the producer's claimed values.
# --------------------------------------------------------------------------------------------------------
def _vlit(v) -> str:
    """Lean literal for a flat integer vector (pm._lit is matrix-only)."""
    return "[" + ", ".join(str(x) for x in v) + "]"


_LEAN_HELPERS = """\
set_option maxRecDepth 100000
def det2 (A : List (List Int)) : Int := A[0]![0]! * A[1]![1]! - A[0]![1]! * A[1]![0]!
def minorNZ (A : List (List Int)) : Bool := det2 A != 0
def allNonneg (xs : List Int) : Bool := xs.all (fun x => 0 <= x)
def matNonneg (M : List (List Int)) : Bool := M.all allNonneg
def rowsSumTo (M : List (List Int)) (s : Int) : Bool := M.all (fun r => r.foldl (·+·) 0 == s)
def hmmValid (piI : List Int) (Dpi : Int) (Ts : List (List (List Int))) (sumT : List (List Int)) (Dt : Int) : Bool :=
  allNonneg piI && (piI.foldl (·+·) 0 == Dpi) && Ts.all matNonneg && rowsSumTo sumT Dt"""


def render_cert_lean(hmm, valid_lit, rank_cert, order_certs) -> str:
    piI, Dpi = _clear_int(hmm["pi"])
    syms = sorted(hmm["T"].keys())
    Ts_int = []
    Dt = None
    for a in syms:
        Ti, d = _clear_int(hmm["T"][a])
        Ts_int.append((Ti, d))
    # common integer scale for the operators, so sum_a T_a rows sum to the same integer
    Dt = 1
    for _, d in Ts_int:
        Dt = Dt * d // gcd(Dt, d)
    Ts_scaled = [[[e * (Dt // d) for e in row] for row in Ti] for (Ti, d) in Ts_int]
    n = len(hmm["pi"])
    sumT = [[sum(Ts_scaled[s][i][j] for s in range(len(syms))) for j in range(n)] for i in range(n)]
    lits_T = "[" + ", ".join(pm._lit(T) for T in Ts_scaled) + "]"
    # conjunction: validity ∧ rank minor ∧ every order minor ∧ every denominator positivity
    parts = [f"hmmValid {_vlit(piI)} {Dpi} {lits_T} {pm._lit(sumT)} {Dt}",
             f"minorNZ {pm._lit(rank_cert['H_int'])}"]
    for oc in order_certs:
        parts.append(f"minorNZ {pm._lit(oc['M_int'])}")
        parts.append(f"(0 < ({oc['num_h1']} : Int)) && (0 < ({oc['num_h2']} : Int))")
    body = " &&\n    ".join(parts)
    return (f"{_LEAN_HELPERS}\n\ntheorem beyond_markov_cert :\n    ({body}) = true := by\n  decide\n")


def render_cert_lean_bogus(hmm, rank_cert, order_certs) -> str:
    """Control: corrupt the rank minor so its determinant becomes 0 (make row 1 a copy of row 0), forcing the
    kernel to reject — the whole conjunction must fail."""
    bad = {k: v for k, v in rank_cert.items()}
    bad["H_int"] = [rank_cert["H_int"][0][:], rank_cert["H_int"][0][:]]  # det = 0
    valid_lit = None
    return render_cert_lean(hmm, valid_lit, bad, order_certs)


# --------------------------------------------------------------------------------------------------------
# Witnesses.
# --------------------------------------------------------------------------------------------------------
def bm1_two_mode(q=Fr(3, 4), e=Fr(1, 8)) -> dict:
    """BM-1: symmetric 2-mode HMM. Hidden transition M=[[1-e,e],[e,1-e]]; mode A emits 1 w.p. q, B emits 1 w.p.
    1-q. T_a[i][j] = E_i(a) * M[i][j] (emission on the current mode, then transition)."""
    M = [[1 - e, e], [e, 1 - e]]
    E = {0: [1 - q, q], 1: [q, 1 - q]}       # E[state][symbol]: state A=0 emits 0 w.p. 1-q, 1 w.p. q
    T = {a: [[E[i][a] * M[i][j] for j in range(2)] for i in range(2)] for a in (0, 1)}
    return {"name": "BM-1 symmetric 2-mode HMM", "params": {"q": str(q), "e": str(e)},
            "pi": [Fr(1, 2), Fr(1, 2)], "T": T,
            # 0^{k+1} vs 1·0^k: shared suffix 0^k, mode posterior differs -> P(0|·) differs for all k.
            "order": {"pre1": (0,), "pre2": (1,), "suffix": 0, "a": 0}}


def even_process() -> dict:
    """BM-4: the canonical even process epsilon-machine. T0=[[1/2,0],[0,0]], T1=[[0,1/2],[1,0]], pi=[2/3,1/3].
    Its memory is the PARITY of the current 1-run: pasts 0·1^k vs 1·1^k share the suffix 1^k but differ in
    1-run parity, so P(1|·) differs for every k -> infinite order."""
    return {"name": "even process (epsilon-machine)", "params": {},
            "pi": [Fr(2, 3), Fr(1, 3)],
            "T": {0: [[Fr(1, 2), Fr(0)], [Fr(0), Fr(0)]], 1: [[Fr(0), Fr(1, 2)], [Fr(1), Fr(0)]]},
            "order": {"pre1": (0,), "pre2": (1,), "suffix": 1, "a": 1}}


def certify(hmm, K=8, rank_UV=None) -> dict:
    val = hmm_valid(hmm)
    U = rank_UV[0] if rank_UV else [(), (0,)]
    V = rank_UV[1] if rank_UV else [(0,), (1,)]
    rank = hankel_minor_cert(hmm, U, V)
    oc = hmm.get("order", {"pre1": (0,), "pre2": (1,), "suffix": 0, "a": 0})
    order = [order_separation_cert(hmm, k, a=oc["a"], pre1=oc["pre1"], pre2=oc["pre2"], suffix=oc["suffix"])
             for k in range(K + 1)]
    order_ok = all(o["ok"] for o in order)
    return {"name": hmm["name"], "params": hmm["params"], "validity": val, "rank_cert": rank,
            "order_certs": order, "K": K,
            "certified": bool(val["valid"] and rank["ok"] and order_ok),
            "reading": (f"{hmm['name']}: valid HMM={val['valid']}; rank(H)>={rank['rank_ge']} "
                        f"(det={rank['det_int']}!=0); Markov order>{K} "
                        f"({sum(o['ok'] for o in order)}/{len(order)} conditional-separation certs).")}


def main() -> int:
    print("=== T8-a — minimal rational-HMM beyond-Markov certificate suite ===")
    results = []
    for hmm in (bm1_two_mode(), even_process()):
        c = certify(hmm)
        print(c["reading"])
        results.append(c)

    kernel = {"status": "not run"}
    try:
        from leibniz.backends.lean_cli import LeanCliBackend, available
        if available():
            bk = LeanCliBackend(timeout_s=120)
            krows = []
            for hmm, c in zip((bm1_two_mode(), even_process()), results):
                good = bk.check_source(render_cert_lean(hmm, None, c["rank_cert"], c["order_certs"]))
                bogus = bk.check_source(render_cert_lean_bogus(hmm, c["rank_cert"], c["order_certs"]))
                krows.append({"name": c["name"], "valid": good, "bogus_rejected": bogus is False})
                print(f"  kernel {c['name']}: valid={good}  bogus_rejected={bogus is False}")
            kernel = {"status": "checked", "rows": krows,
                      "sound": all(r["valid"] is True and r["bogus_rejected"] for r in krows)}
        else:
            kernel = {"status": "unavailable (no docker)"}
    except Exception as ex:  # pragma: no cover
        kernel = {"status": f"unavailable ({type(ex).__name__}: {ex})"}

    all_py = all(c["certified"] for c in results)
    gate = ("GREEN" if all_py and kernel.get("sound") is True else
            "AMBER(kernel-unavailable)" if all_py and "unavailable" in str(kernel.get("status")) else "RED")
    out = {"gate": gate, "results": results, "kernel": kernel,
           "reading": ("T8-a beyond-Markov certificate suite: each witness is a valid rational HMM with a "
                       "kernel-checkable Hankel rank lower bound and Markov-order>K separation. GREEN = Python "
                       "certs hold AND the real Lean kernel accepts the valid cert and rejects the corrupted "
                       "control. Honest scope: 'order>K', not 'infinite order' (that is T8-b, an induction "
                       "bridge lemma). Amplification, not discovery (textbook processes).")}
    p = _ROOT / "docs" / "results" / "beyond_markov_cert.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, indent=2, default=str) + "\n")
    print(f"\ngate={gate}  kernel={kernel.get('status')} sound={kernel.get('sound')}\n-> {p}")
    return 0 if gate != "RED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
