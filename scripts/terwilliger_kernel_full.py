"""Terwilliger F1 — whole-certificate-in-kernel (task #100, ticket 2; scope doc section F1).

The kernel checks the ENTIRE exact dual certificate, not just its PSD blocks:
  1. betaOK   — a supplied Pascal triangle is verified row-by-row (pascalOK), then the supplied dense beta
                table is verified against Schrijver eq. (7) per k-slice (the kernel recomputes-and-compares;
                it never trusts the table). Strategy fixed by the measured k=0 benchmark: table lookups 8.0 s
                vs naive cc-recursion 10.8 s at n=19 (both pass; table wins and stays flat in k).
  2. statOK   — the per-orbit stationarity identities, transcribed line-for-line from collected() in
                scripts/terwilliger_dual.py (the authoritative spec): the kernel re-enumerates the free orbit
                keys itself, folds the objective + beta-block + linear-multiplier contributions over integers
                (everything cleared by the common denominator D), and requires every coefficient to be 0.
  3. nonneg   — every listed multiplier numerator >= 0 (unlisted multipliers are 0 by convention — a sound
                dual choice), and every listed (t,i,j) is a VALID triple (phantom constraints rejected).
  4. bound    — sum(gamma) - nu <= target * D, with D > 0.
  5. PSD      — ldltOK per block on the SAME integer literals statOK reads (Z*D), so the PSD check and the
                stationarity check cannot be fed different matrices.

One theorem per obligation (the B2 lesson), `maxHeartbeats 0`, decide only (never native_decide). Output
stays audit-tier: F1 changes how much of the check the kernel performs, not what is trusted. No trusted
surface touched. Needs cvxpy (+sdpap for the D6 cells) to produce duals and docker for the kernel.
"""
from __future__ import annotations

import importlib.util
import json
import time
from fractions import Fraction as Fr
from math import comb
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
OUT = _ROOT / "docs" / "results" / "terwilliger_kernel_full.json"


def _load(mod, rel):
    spec = importlib.util.spec_from_file_location(mod, _ROOT / rel)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


td = _load("terwilliger_dual", "scripts/terwilliger_dual.py")
pm = _load("psd_certificate_microprobe", "scripts/psd_certificate_microprobe.py")

# ---- Lean checker (core Lean, no Mathlib; decide-only) ----------------------------------------------------
# The stationarity fold mirrors collected() in terwilliger_dual.py line-for-line; keep the two in sync.
_HELPERS = """set_option maxRecDepth 100000
set_option maxHeartbeats 0
def zipAdd (u v : List Int) : List Int := (u.zip v).map (fun p => p.1 + p.2)
def pascalOK (P : List (List Int)) : Bool :=
  P.head? == some [1] && ((P.zip P.tail).all (fun p => p.2 == zipAdd (p.1 ++ [0]) (0 :: p.1)))
def bin (P : List (List Int)) (a b : Nat) : Int := (P.getD a []).getD b 0
def betaAt (P : List (List Int)) (n k t i j : Nat) : Int :=
  (List.range (n+1)).foldl (fun acc u =>
    if u < k || i < u || j < u || n - k < u then acc
    else acc + (if (u - t) % 2 == 0 then (1:Int) else (-1)) * bin P u t * bin P (n-2*k) (u-k)
             * bin P (n-k-u) (i-u) * bin P (n-k-u) (j-u)) 0
def sliceOK (P : List (List Int)) (n k : Nat) (B : List (List (List Int))) : Bool :=
  B.length == n - 2*k + 1 &&
  B.zipIdx.all (fun (row, a) => row.length == n - 2*k + 1 &&
    row.zipIdx.all (fun (ts, b) => ts.length == min (k + a) (k + b) + 1 &&
      ts.zipIdx.all (fun (v, t) => betaAt P n k t (k + a) (k + b) == v)))
abbrev Key := Nat × Nat × Nat
def keyEq (a b : Key) : Bool := a.1 == b.1 && a.2.1 == b.2.1 && a.2.2 == b.2.2
def canonK (t i j : Nat) : Key :=
  let s := i + j - 2*t
  let lo := min i (min j s)
  let hi := max i (max j s)
  (lo, i + j + s - lo - hi, hi)
def isFree (d : Nat) (kk : Key) : Bool :=
  let bad (v : Nat) : Bool := (1 <= v && v <= d - 1) || (d % 2 == 0 && v % 2 == 1)
  !(bad kk.1 || bad kk.2.1 || bad kk.2.2)
def validT (n t i j : Nat) : Bool := t <= min i j && i <= n && j <= n && i + j <= n + t
def keysFor (n d : Nat) : List Key :=
  ((List.range (n+1)).foldl (fun acc i => (List.range (n+1)).foldl (fun acc j =>
    (List.range (min i j + 1)).foldl (fun acc t =>
      if validT n t i j then
        let kk := canonK t i j
        if isFree d kk && !(acc.any (keyEq kk)) then acc ++ [kk] else acc
      else acc) acc) acc) [])
def upd (acc : List (Key × Int)) (kk : Key) (v : Int) : List (Key × Int) :=
  if v == 0 then acc else acc.map (fun p => if keyEq p.1 kk then (p.1, p.2 + v) else p)
def objInt (P : List (List Int)) (n : Nat) (D : Int) (kk : Key) : Int :=
  if kk.1 == 0 && kk.2.1 == kk.2.2 then bin P n kk.2.1 * D else 0
def blockFold1 (n k : Nat) (Bk : List (List (List Int))) (Zk Wk : List (List Int))
    (acc : List (Key × Int)) : List (Key × Int) :=
  Bk.zipIdx.foldl (fun acc (row, a) =>
    row.zipIdx.foldl (fun acc (ts, b) =>
      let i := k + a; let j := k + b
      let z := (Zk.getD a []).getD b 0
      let w := (Wk.getD a []).getD b 0
      ts.zipIdx.foldl (fun acc (bv, t) =>
        if i + j <= n + t then
          upd (upd acc (canonK t i j) (bv * (z - w))) (canonK 0 (i + j - 2*t) 0) (bv * w)
        else acc) acc) acc) acc
def multFold (M : List (Nat × Nat × Nat × Int)) (f : Nat → Nat → Nat → Int → List (Key × Int) →
    List (Key × Int)) (acc : List (Key × Int)) : List (Key × Int) :=
  M.foldl (fun acc e => f e.1 e.2.1 e.2.2.1 e.2.2.2 acc) acc
def multsValid (n : Nat) (M : List (Nat × Nat × Nat × Int)) : Bool :=
  M.all (fun e => validT n e.1 e.2.1 e.2.2.1)
def linFin (acc : List (Key × Int)) (MA MB MG : List (Nat × Nat × Nat × Int)) (nu : Int) :
    List (Key × Int) :=
  let acc2 := multFold MA (fun t i j v acc => upd acc (canonK t i j) v) acc
  let acc3 := multFold MB (fun t i j v acc => upd (upd acc (canonK 0 i 0) v) (canonK t i j) (-v)) acc2
  let acc4 := multFold MG (fun t i j v acc =>
    upd (upd (upd acc (canonK t i j) v) (canonK 0 i 0) (-v)) (canonK 0 j 0) (-v)) acc3
  upd acc4 (0, 0, 0) nu
def dot (u v : List Int) : Int := ((u.zip v).map (fun p => p.1 * p.2)).foldl (· + ·) 0
def col (A : List (List Int)) (j : Nat) : List Int := A.map (fun r => r[j]!)
def matmul (A B : List (List Int)) : List (List Int) :=
  A.map (fun r => (List.range (B[0]!.length)).map (fun j => dot r (col B j)))
def transpose (A : List (List Int)) : List (List Int) :=
  (List.range (A[0]!.length)).map (fun j => col A j)
def diag (d : List Int) : List (List Int) :=
  (List.range d.length).map (fun i => (List.range d.length).map (fun j => if i == j then d[i]! else 0))
def scaleM (s : Int) (M : List (List Int)) : List (List Int) := M.map (fun r => r.map (fun x => s * x))
def ldltOK (M L : List (List Int)) (d : List Int) (s : Int) : Bool :=
  0 < s && d.all (fun x => 0 <= x) && (matmul (matmul L (diag d)) (transpose L) == scaleM s M)
"""


def _lit1(v):
    return "[" + ", ".join(str(x) for x in v) + "]"


def _lit2(M):
    return "[" + ", ".join(_lit1(r) for r in M) + "]"


def _lit3(B):
    return "[" + ", ".join(_lit2(r) for r in B) + "]"


def _mult_lit(entries):
    return "[" + ", ".join(f"({t}, {i}, {j}, ({v} : Int))" for (t, i, j, v) in entries) + "]"


def dense_beta(n, k):
    """Raw eq.(7) values over the FULL (a,b,t) slice domain (impossible triples included — the stationarity
    fold carries the possible() guard, exactly like collected())."""
    idx = td.block_idx(n, k)
    return [[[td.beta(n, i, j, k, t) for t in range(min(i, j) + 1)] for j in idx] for i in idx]


# ---- Python mirror of the Lean fold ----------------------------------------------------------------------
# Computes the SUPPLIED intermediate accumulators for the chunked stationarity theorems (one per k-slice —
# the single whole-fold theorem hit the elaborator's recursion wall at n=19, the B2 lesson again). The kernel
# re-verifies every chunk against its own fold, so a mirror bug can only yield a kernel False, never a false
# certificate. Order-faithful to the Lean functions: keep in sync with _HELPERS.

def _canon(t, i, j):
    return tuple(sorted((i, j, i + j - 2 * t)))


def _isfree(d, kk):
    def bad(v):
        return 1 <= v <= d - 1 or (d % 2 == 0 and v % 2 == 1)
    return not any(bad(v) for v in kk)


def _keys(n, d):
    acc = []
    for i in range(n + 1):
        for j in range(n + 1):
            for t in range(min(i, j) + 1):
                if i + j <= n + t:
                    kk = _canon(t, i, j)
                    if _isfree(d, kk) and kk not in acc:
                        acc.append(kk)
    return acc


def _upd(acc, kk, v):
    if v == 0:
        return acc
    return [(K, c + v) if K == kk else (K, c) for (K, c) in acc]


def _blockfold1(n, k, Bk, Zk, Wk, acc):
    for a, row in enumerate(Bk):
        for b, ts in enumerate(row):
            i, j = k + a, k + b
            z, w = Zk[a][b], Wk[a][b]
            for t, bv in enumerate(ts):
                if i + j <= n + t:
                    acc = _upd(acc, _canon(t, i, j), bv * (z - w))
                    acc = _upd(acc, _canon(0, i + j - 2 * t, 0), bv * w)
    return acc


def _accs(data):
    """[A_0 .. A_{kmax+1}]: A_0 = objective init over the free keys; A_{k+1} = A_k + the k-slice fold."""
    n, d, D = data["n"], data["d"], data["D"]
    acc = [(kk, (comb(n, kk[1]) * D if kk[0] == 0 and kk[1] == kk[2] else 0)) for kk in _keys(n, d)]
    out = [acc]
    for k in range(len(data["B"])):
        acc = _blockfold1(n, k, data["B"][k], data["Z"][k], data["W"][k], acc)
        out.append(acc)
    return out


def _acc_lit(acc):
    return "[" + ", ".join(f"(({a}, {b}, {c}), ({v} : Int))" for ((a, b, c), v) in acc) + "]"


def build_data(n, d, duals, target):
    """Integerize the certificate by ONE common denominator D and assemble all render data."""
    nums = [duals["nu"]]
    for fam in ("a", "b1", "g"):
        nums += list(duals[fam].values())
    for f in ("Z", "Zp"):
        for k in duals[f]:
            nums += [x for row in duals[f][k] for x in row]
    D = 1
    for v in nums:
        q = Fr(v).denominator
        D = D * q // __import__("math").gcd(D, q)
    kmax = n // 2
    Z = [[[int(Fr(x) * D) for x in row] for row in duals["Z"][k]] for k in range(kmax + 1)]
    W = [[[int(Fr(x) * D) for x in row] for row in duals["Zp"][k]] for k in range(kmax + 1)]
    mult = {fam: sorted((t, i, j, int(Fr(v) * D)) for (t, i, j), v in duals[fam].items() if v != 0)
            for fam in ("a", "b1", "g")}
    nu = int(Fr(duals["nu"]) * D)
    B = [dense_beta(n, k) for k in range(kmax + 1)]
    P = [[comb(a, b) for b in range(a + 1)] for a in range(n + 2)]
    gsum = sum(v for (_, _, _, v) in mult["g"])
    return {"n": n, "d": d, "D": D, "target": target, "P": P, "B": B, "Z": Z, "W": W,
            "mult": mult, "nu": nu, "gsum": gsum}


def psd_certs(data):
    """LDLT certificates for the SAME Z*D / Zp*D literals statOK reads (PSD is scale-invariant for D>0)."""
    blocks = []
    for fam, mats in (("Z", data["Z"]), ("W", data["W"])):
        for k, M in enumerate(mats):
            res = pm.ldlt([[Fr(v) for v in row] for row in M])
            if res is None:
                return None
            L, dd = res
            Li, di, sc = pm.clear_denoms(L, dd)
            blocks.append({"fam": fam, "k": k, "L": Li, "d": di, "scale": sc})
    return blocks


def render(data, blocks):
    """One self-contained Lean source: shared data defs + one theorem per obligation."""
    n, d, D = data["n"], data["d"], data["D"]
    s = [_HELPERS]
    s.append(f"def P : List (List Int) := {_lit2(data['P'])}")
    for k, Bk in enumerate(data["B"]):
        s.append(f"def B{k} : List (List (List Int)) := {_lit3(Bk)}")
    for k, M in enumerate(data["Z"]):
        s.append(f"def Z{k} : List (List Int) := {_lit2(M)}")
    for k, M in enumerate(data["W"]):
        s.append(f"def W{k} : List (List Int) := {_lit2(M)}")
    s.append(f"def MA : List (Nat × Nat × Nat × Int) := {_mult_lit(data['mult']['a'])}")
    s.append(f"def MB : List (Nat × Nat × Nat × Int) := {_mult_lit(data['mult']['b1'])}")
    s.append(f"def MG : List (Nat × Nat × Nat × Int) := {_mult_lit(data['mult']['g'])}")
    accs = _accs(data)
    for k, acc in enumerate(accs):
        s.append(f"def A{k} : List (Key × Int) := {_acc_lit(acc)}")
    # P's length is pinned (a short P would getD-default binomials to 0); row lengths are forced by pascalOK
    thms = [f"theorem pascal_ok : (P.length == {n + 2} && pascalOK P) = true := by\n  decide"]
    for k in range(len(data["B"])):
        thms.append(f"theorem beta_ok_{k} : sliceOK P {n} {k} B{k} = true := by\n  decide")
    thms.append(f"theorem mults_valid : (multsValid {n} MA && multsValid {n} MB && multsValid {n} MG) "
                f"= true := by\n  decide")
    # chunked stationarity (the whole-fold theorem hits the recursion wall at n=19): the supplied A_k are
    # each re-verified, so the chain A_0 -> ... -> A_last -> linear -> all-zero is kernel-checked end to end
    thms.append(f"theorem stat_init : (((keysFor {n} {d}).map (fun kk => (kk, objInt P {n} ({D}) kk))) "
                f"== A0) = true := by\n  decide")
    for k in range(len(data["B"])):
        thms.append(f"theorem stat_k{k} : (blockFold1 {n} {k} B{k} Z{k} W{k} A{k} == A{k + 1}) "
                    f"= true := by\n  decide")
    thms.append(f"theorem stat_fin : (linFin A{len(accs) - 1} MA MB MG ({data['nu']}))"
                f".all (fun p => p.2 == 0) = true := by\n  decide")
    thms.append("theorem nonneg_ok : ((MA ++ MB ++ MG).all (fun e => 0 <= e.2.2.2)) = true := by\n  decide")
    # floor semantics: the cert proves A <= sum(gamma)-nu, and A integer => A <= floor(.) <= target, i.e.
    # (gsum-nu)/D < target+1  <=>  gsum-nu < (target+1)*D  (D > 0 checked alongside). Sigma(gamma) is folded
    # KERNEL-SIDE from MG — a supplied gsum literal was the review's soundness hole #1 (nothing tied it to MG).
    thms.append(f"theorem bound_ok : ((MG.foldl (fun s e => s + e.2.2.2) 0) - ({data['nu']}) "
                f"< ({data['target']} + 1) * ({D}) && (0 : Int) < ({D})) = true := by\n  decide")
    for b in blocks:
        thms.append(f"theorem psd_{b['fam']}_{b['k']} : ldltOK {b['fam']}{b['k']} {_lit2(b['L'])} "
                    f"{_lit1(b['d'])} ({b['scale']}) = true := by\n  decide")
    return "\n".join(s) + "\n\n" + "\n\n".join(thms) + "\n"


def python_check(data):
    """Free-CPU mirror of the kernel obligations (fast pre-flight; the kernel remains the decider)."""
    n, d, D = data["n"], data["d"], data["D"]
    duals = {"Z": {k: [[Fr(x, D) for x in row] for row in M] for k, M in enumerate(data["Z"])},
             "Zp": {k: [[Fr(x, D) for x in row] for row in M] for k, M in enumerate(data["W"])},
             "nu": Fr(data["nu"], D)}
    for fam, name in (("a", "a"), ("b1", "b1"), ("g", "g")):
        full = {tij: Fr(0) for tij in td.valid_triples(n)}
        for (t, i, j, v) in data["mult"][fam]:
            full[(t, i, j)] = Fr(v, D)
        duals[name] = full
    chk = td.dual_check(n, d, duals)
    return chk


def kernel_full(n, d, target, precisions=None, timeout_s=1800):
    """Produce the exact certificate, render ALL obligations, and kernel-check (plus per-stage timing)."""
    tel = _load("terwilliger_exact_lp", "scripts/terwilliger_exact_lp.py")
    kw = {} if precisions is None else {"precisions": precisions}
    row = tel.certify_lp(n, d, target=target, return_duals=True, time_cap_s=2400, **kw)
    if not row.get("certified"):
        return {"n": n, "d": d, "certified": False, "note": "no exact LP cert to render"}
    data = build_data(n, d, row["duals"], target)
    blocks = psd_certs(data)
    if blocks is None:
        return {"n": n, "d": d, "certified": True, "error": "LDLT failed on a Z*D block"}
    pre = python_check(data)
    src = render(data, blocks)
    out = {"n": n, "d": d, "target": target, "exact_bound": row["exact_bound"], "D_bits": data["D"].bit_length(),
           "n_keys": len(td.free_keys(n, d)), "n_mults": sum(len(v) for v in data["mult"].values()),
           "n_beta_entries": sum(len(ts) for Bk in data["B"] for r in Bk for ts in r),
           "src_kib": len(src) // 1024, "preflight_feasible": pre["feasible"]}
    from leibniz.backends.lean_cli import LeanCliBackend, available
    if not available():
        out["kernel"] = "unavailable (no docker/image)"
        return out
    bk = LeanCliBackend(timeout_s=timeout_s)
    t0 = time.time()
    out["kernel_valid"] = bk.check_source(src)
    out["kernel_valid_secs"] = round(time.time() - t0, 1)
    return out, data, blocks, src


CONTROLS = ("beta_entry", "stationarity", "negative_mult", "bound_claim", "psd_scale", "beta_shape")


def corrupt(data, blocks, mode):
    """The four scope-doc controls + two review-added ones (zero-scale PSD cert; truncated beta shape),
    each a one-datum mutation that must flip the kernel to False."""
    import copy
    d2, b2 = copy.deepcopy(data), copy.deepcopy(blocks)
    if mode == "psd_scale":
        m = len(b2[0]["M"]) if "M" in b2[0] else len(data["Z"][0])
        b2[0] = dict(b2[0], L=[[0] * m for _ in range(m)], d=[0] * m, scale=0)   # vacuous-PSD attack
    elif mode == "beta_shape":
        d2["B"][0][2][2] = d2["B"][0][2][2][:-1]     # truncated t-list: shape pin must catch it
    elif mode == "beta_entry":
        d2["B"][0][2][2][0] += 1                     # table no longer matches eq. (7)
    elif mode == "stationarity":
        f = d2["mult"]["g"] or d2["mult"]["b1"] or d2["mult"]["a"]
        t, i, j, v = f[0]
        f[0] = (t, i, j, v + 1)                      # breaks the orbit identity (and only that)
        d2["gsum"] = sum(x[3] for x in d2["mult"]["g"])
    elif mode == "negative_mult":
        d2["mult"]["a"] = d2["mult"]["a"] + [(0, d2["d"], d2["d"], -d2["D"])]
    elif mode == "bound_claim":
        d2["target"] = d2["target"] - 1
    return d2, b2


def main() -> int:
    from leibniz.backends.lean_cli import LeanCliBackend
    rows = []
    for (n, d, target, precs) in [(4, 2, 8, None), (6, 4, 4, None), (19, 6, 1280, None)]:
        t0 = time.time()
        r = kernel_full(n, d, target, precisions=precs)
        if not isinstance(r, tuple):
            r["total_secs"] = round(time.time() - t0, 1)
            rows.append(r)
            continue
        out, data, blocks, src = r
        if (n, d) == (19, 6):                        # the four controls run on the record cell
            bk = LeanCliBackend(timeout_s=1800)
            ctl = {}
            for mode in CONTROLS:
                d2, b2 = corrupt(data, blocks, mode)
                t1 = time.time()
                ctl[mode] = {"kernel": bk.check_source(render(d2, b2)), "secs": round(time.time() - t1, 1)}
            out["controls"] = ctl
            out["controls_all_false"] = all(v["kernel"] is False for v in ctl.values())
        out["total_secs"] = round(time.time() - t0, 1)
        rows.append(out)
    ok = [r for r in rows if r.get("kernel_valid") is True]
    a19 = next((r for r in rows if r["n"] == 19), {})
    verdict = ("GREEN" if len(ok) == len(rows) and a19.get("controls_all_false") else "AMBER")
    res = {"verdict": verdict, "rows": rows,
           "reading": ("F1 whole-certificate-in-kernel. For each cell the REAL Lean 4.31 kernel now checks "
                       "EVERY obligation of the exact dual certificate: the beta table against eq.(7) "
                       "(recompute-and-compare via a verified Pascal triangle), the per-orbit stationarity "
                       "identities (transcribed from collected(); keys re-enumerated kernel-side), multiplier "
                       "validity + nonnegativity, the bound inequality, and the PSD blocks (ldltOK on the "
                       "SAME integer literals the stationarity fold reads). GREEN = all cells kernel-True "
                       "AND the four A(19,6) corrupted controls (wrong beta entry / perturbed multiplier / "
                       "negative multiplier / bound 1279) all kernel-False. Audit tier unchanged: F1 moves "
                       "the CHECK into the kernel; the formulation bridge (F2) is still informal.")}
    OUT.write_text(json.dumps(res, indent=2) + "\n")
    print(f"terwilliger F1 whole-cert-in-kernel: {verdict}")
    for r in rows:
        print(f"  A({r['n']},{r['d']}): valid={r.get('kernel_valid')} ({r.get('kernel_valid_secs')}s, "
              f"src {r.get('src_kib')}KiB, {r.get('n_beta_entries')} beta) controls_false="
              f"{r.get('controls_all_false', '-')} total={r.get('total_secs')}s")
    print(f"  -> {OUT}")
    return 0 if verdict == "GREEN" else 1


if __name__ == "__main__":
    raise SystemExit(main())
