"""T8-c — Minimal Positive Realization Problem: a kernel-certified positive-realization > linear-dimension
separation for a small rational process (audit tier). The one discovery-shaped bet on the beyond-Markov
track — resolved, honestly, as AMPLIFICATION with a certifiable modest separation.

Setup (verified by the T8-c soundness workflow, docs/results/beyond-markov-t8c-2026-07-03.md):
  * Bridge (sound): an r-state POSITIVE HMM realizing a process gives H = F·B with F,B ≥ 0, inner dim r, so
    nonneg-rank(H) ≤ r. Contrapositive: nonneg-rank(H) > r  ⇒  NO r-state positive HMM realizes it.
  * Fooling-set lower bound (sound, Fiorini–Kaibel–Pashkovich–Theis): positions (i_l,j_l) with M[i_l,j_l] > 0
    and M[i_l,j_m]·M[i_m,j_l] = 0 for l≠m  ⇒  nonneg-rank(M) ≥ t. COMBINATORIAL (sign/zero pattern), decided by
    integer positivity + zero-product `decide` — NOT an LP (the panel's "Farkas/LP" framing was wrong; and
    deciding nonneg-rank ≤ k in general is ExR-complete = the DEFERRED SOS/Positivstellensatz territory, so only
    VERIFICATION of a supplied separation is reachable, not autonomous search).

The witness: the 4-state cyclic ("necklace") Markov chain on {0,1,2,3}, A a circulant with support = the
4-cycle matrix M = [[1,1,0,0],[1,0,1,0],[0,1,0,1],[0,0,1,1]], uniform stationary π, each state emitting its
label. Its word-Hankel has ordinary rank EXACTLY 3 (stable to length 3), but its length-2 block
H2[a,b] = π_a·A[a,b] = (1/8)·M carries a size-4 fooling set ⇒ nonneg-rank(H) ≥ 4 ⇒ minimal positive
realization = 4 > 3 = OOM/linear dimension.

HONEST scope: +1-state gap on a FULLY-OBSERVED chain (positive realization is the 4 chain states) — the
classical smallest rank/nonneg-rank gap, AMPLIFICATION not discovery. The deep "finite-OOM-but-no-finite-HMM"
phenomenon (Jaeger's probability clock) is irrational / dense-Hankel and stays DEFERRED (unreachable by any
finite fooling set). No trust surface touched; a standalone integer checker like bareiss_ldlt.py's detSignOK.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from fractions import Fraction as Fr
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
OUT = _ROOT / "docs" / "results" / "beyond_markov_mprp.json"


def _pm():
    sys.path.insert(0, str(_ROOT))
    sys.path.insert(0, str(_ROOT / "scripts"))
    spec = importlib.util.spec_from_file_location("psd_certificate_microprobe",
                                                  _ROOT / "scripts" / "psd_certificate_microprobe.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


# The 4-cycle witness matrix (support of the necklace chain).
M4 = [[1, 1, 0, 0], [1, 0, 1, 0], [0, 1, 0, 1], [0, 0, 1, 1]]
DEP = [1, -1, -1, 1]                          # r0 − r1 − r2 + r3 = 0  ⇒ rank ≤ 3
SUB3_ROWS, SUB3_COLS = (0, 1, 2), (0, 1, 2)   # a 3×3 minor with det = −1 ≠ 0 ⇒ rank ≥ 3
FS_ROWS, FS_COLS = [0, 1, 2, 3], [0, 2, 1, 3] # fooling set {(0,0),(1,2),(2,1),(3,3)} ⇒ nonneg-rank ≥ 4


def _sub3(M):
    return [[M[i][j] for j in SUB3_COLS] for i in SUB3_ROWS]


def _det3(A):
    return (A[0][0] * (A[1][1] * A[2][2] - A[1][2] * A[2][1])
            - A[0][1] * (A[1][0] * A[2][2] - A[1][2] * A[2][0])
            + A[0][2] * (A[1][0] * A[2][1] - A[1][1] * A[2][0]))


def fooling_ok(M, ri, ci) -> bool:
    t = len(ri)
    if not all(M[ri[a]][ci[a]] > 0 for a in range(t)):
        return False
    return all(M[ri[a]][ci[b]] * M[ri[b]][ci[a]] == 0 for a in range(t) for b in range(t) if a < b)


def dep_ok(coeffs, M) -> bool:
    ncol = len(M[0])
    return all(sum(coeffs[i] * M[i][j] for i in range(len(M))) == 0 for j in range(ncol))


def matrix_cert(M=M4) -> dict:
    rank_le3 = dep_ok(DEP, M)
    minor = _det3(_sub3(M))
    rank_ge3 = minor != 0
    fool = fooling_ok(M, FS_ROWS, FS_COLS)
    return {"rank_le3_dependency": rank_le3, "minor3_det": minor, "rank_ge3": rank_ge3,
            "fooling_valid": fool, "rank": 3 if (rank_le3 and rank_ge3) else None,
            "nonneg_rank_ge": 4 if fool else None,
            "separation": bool(rank_le3 and rank_ge3 and fool)}


# --------------------------------------------------------------------------------------------------------
# The necklace chain and its exact word-Hankel (audit: it IS a valid stationary rational process).
# --------------------------------------------------------------------------------------------------------
def necklace():
    A = [[Fr(1, 2), Fr(1, 2), Fr(0), Fr(0)],
         [Fr(1, 2), Fr(0), Fr(1, 2), Fr(0)],
         [Fr(0), Fr(1, 2), Fr(0), Fr(1, 2)],
         [Fr(0), Fr(0), Fr(1, 2), Fr(1, 2)]]
    pi = [Fr(1, 4)] * 4
    return A, pi


def word_prob(A, pi, w) -> Fr:
    p = pi[w[0]]
    for a, b in zip(w, w[1:]):
        p *= A[a][b]
    return p


def _words(alph, L):
    out = []
    cur = [()]
    for _ in range(L):
        cur = [c + (a,) for c in cur for a in alph]
        out += cur
    return out


def _exact_rank(rows):
    R = [r[:] for r in rows]
    m, n = len(R), len(R[0]) if R else 0
    rank, prow = 0, 0
    for col in range(n):
        piv = next((i for i in range(prow, m) if R[i][col] != 0), None)
        if piv is None:
            continue
        R[prow], R[piv] = R[piv], R[prow]
        pv = R[prow][col]
        R[prow] = [x / pv for x in R[prow]]
        for i in range(m):
            if i != prow and R[i][col] != 0:
                f = R[i][col]
                R[i] = [x - f * y for x, y in zip(R[i], R[prow])]
        prow += 1
        rank += 1
        if prow == m:
            break
    return rank


def process_audit(Lmax=2) -> dict:
    A, pi = necklace()
    stat = all(sum(pi[i] * A[i][j] for i in range(4)) == pi[j] for j in range(4))
    # length-2 joint block H2[a,b] = P(ab) = pi_a A[a,b]; 8*H2 == M4
    H2 = [[word_prob(A, pi, (a, b)) for b in range(4)] for a in range(4)]
    h2_is_M = all(8 * H2[a][b] == M4[a][b] for a in range(4) for b in range(4))
    # consistency: sum_x P(ux) == P(u) for u up to length 2
    cons = all(sum(word_prob(A, pi, u + (x,)) for x in range(4)) == word_prob(A, pi, u)
               for u in _words(range(4), 2))
    # word-Hankel over words of length 1..L, ordinary rank (should be exactly 3, stable)
    ranks = {}
    for L in range(1, Lmax + 1):
        W = _words(range(4), L)
        H = [[word_prob(A, pi, u + v) for v in W] for u in W]
        ranks[f"len<={L}"] = _exact_rank(H)
    return {"stationary": stat, "h2_scaled_is_M": h2_is_M, "consistency": cons,
            "hankel_ranks": ranks, "hankel_rank_stable_3": all(r == 3 for r in ranks.values()),
            "ok": bool(stat and h2_is_M and cons and all(r == 3 for r in ranks.values()))}


# --------------------------------------------------------------------------------------------------------
# Kernel rendering — core Lean, `decide`. The kernel recomputes the dependency, the 3×3 minor, and the
# fooling predicate from the integer matrix itself.
# --------------------------------------------------------------------------------------------------------
_HELPERS = """\
set_option maxRecDepth 100000
def det3 (A : List (List Int)) : Int :=
  A[0]![0]! * (A[1]![1]! * A[2]![2]! - A[1]![2]! * A[2]![1]!)
  - A[0]![1]! * (A[1]![0]! * A[2]![2]! - A[1]![2]! * A[2]![0]!)
  + A[0]![2]! * (A[1]![0]! * A[2]![1]! - A[1]![1]! * A[2]![0]!)
def depOK (coeffs : List Int) (M : List (List Int)) (ncol : Nat) : Bool :=
  (List.range ncol).all (fun j =>
    ((List.range coeffs.length).foldl (fun acc i => acc + coeffs[i]! * M[i]![j]!) 0) == 0)
def foolingOK (M : List (List Int)) (ri : List Nat) (ci : List Nat) : Bool :=
  let t := ri.length
  (List.range t).all (fun l => 0 < M[ri[l]!]![ci[l]!]!) &&
  (List.range t).all (fun l => (List.range t).all (fun m =>
    (! (l < m)) || (M[ri[l]!]![ci[m]!]! * M[ri[m]!]![ci[l]!]! == 0)))
def mprpOK (M sub3 : List (List Int)) (dep : List Int) (ri ci : List Nat) : Bool :=
  depOK dep M 4 && (det3 sub3 != 0) && foolingOK M ri ci"""


def render_lean(M, sub3, dep=DEP, ri=FS_ROWS, ci=FS_COLS) -> str:
    pm = _pm()
    ril = "[" + ", ".join(str(x) for x in ri) + "]"
    cil = "[" + ", ".join(str(x) for x in ci) + "]"
    depl = "[" + ", ".join(str(x) for x in dep) + "]"
    return (f"{_HELPERS}\n\ntheorem mprp_separation :\n"
            f"    mprpOK {pm._lit(M)} {pm._lit(sub3)} {depl} {ril} {cil} = true := by\n  decide\n")


def render_control_fill(M=M4) -> str:
    """Fill a structural zero M[0][2]:=1 — breaks the fooling predicate AND lifts rank to 4 (gap collapses)."""
    bad = [r[:] for r in M]
    bad[0][2] = 1
    return render_lean(bad, _sub3(bad))


def render_control_allones() -> str:
    """All-ones J (rank 1) with the same size-4 fooling claim — the fooling predicate must return false."""
    J = [[1, 1, 1, 1] for _ in range(4)]
    return render_lean(J, _sub3(J))


def main() -> int:
    print("=== T8-c — Minimal Positive Realization: nonneg-rank > rank separation (audit tier) ===")
    mc = matrix_cert()
    pa = process_audit()
    print(f"matrix: rank={mc['rank']} (dep={mc['rank_le3_dependency']}, minor3_det={mc['minor3_det']}), "
          f"fooling={mc['fooling_valid']} -> nonneg-rank>={mc['nonneg_rank_ge']}; separation={mc['separation']}")
    print(f"process (necklace): stationary={pa['stationary']} 8*H2==M={pa['h2_scaled_is_M']} "
          f"consistency={pa['consistency']} hankel-ranks={pa['hankel_ranks']} (stable-3={pa['hankel_rank_stable_3']})")

    kernel = {"status": "not run"}
    try:
        from leibniz.backends.lean_cli import LeanCliBackend, available
        if available():
            bk = LeanCliBackend(timeout_s=120)
            good = bk.check_source(render_lean(M4, _sub3(M4)))
            c_fill = bk.check_source(render_control_fill())
            c_ones = bk.check_source(render_control_allones())
            kernel = {"status": "checked", "separation_valid": good,
                      "control_fill_rejected": c_fill is False, "control_allones_rejected": c_ones is False,
                      "sound": bool(good is True and c_fill is False and c_ones is False)}
            print(f"  kernel: separation_valid={good}  control_fill_rejected={c_fill is False}  "
                  f"control_allones_rejected={c_ones is False}")
        else:
            kernel = {"status": "unavailable (no docker)"}
    except Exception as ex:  # pragma: no cover
        kernel = {"status": f"unavailable ({type(ex).__name__}: {ex})"}

    all_py = mc["separation"] and pa["ok"]
    gate = ("GREEN" if all_py and kernel.get("sound") is True else
            "AMBER(kernel-unavailable)" if all_py and "unavailable" in str(kernel.get("status")) else "RED")
    res = {"gate": gate, "matrix_cert": mc, "process_audit": pa, "kernel": kernel,
           "verdict": "AMPLIFICATION",
           "reading": ("T8-c: a kernel-certified minimal-positive-realization > linear-dimension separation for "
                       "the 4-state necklace chain (nonneg-rank(H)=4 > 3=rank via a fooling set; no 3-state "
                       "positive HMM). GREEN = the matrix separation kernel-verifies (rank 3 + fooling set → "
                       "nonneg-rank ≥ 4), both corrupted controls (fill a zero; all-ones) are rejected, AND the "
                       "process audit holds (valid stationary rational chain, Hankel rank 3 stable, 8·H2=M). "
                       "HONEST: AMPLIFICATION (textbook smallest rank/nonneg-rank gap; +1 state; fully-observed "
                       "chain). The deep finite-OOM-no-finite-HMM separation (Jaeger, irrational) stays DEFERRED "
                       "— unreachable by the fooling machinery; deciding nonneg-rank is ExR-complete (SOS "
                       "territory). The sound tool is the combinatorial fooling `decide`, NOT exact_simplex/LP.")}
    OUT.write_text(json.dumps(res, indent=2, default=str) + "\n")
    print(f"\ngate={gate}  kernel={kernel.get('status')} sound={kernel.get('sound')}  verdict=AMPLIFICATION\n-> {OUT}")
    return 0 if gate != "RED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
