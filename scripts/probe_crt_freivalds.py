"""Probe (A) — CRT / derandomized-Freivalds: does the matvec-based check escape the full-identity wall?

The adversarial review of the 7a/7b/7c findings correctly flagged that we measured the flat/entrywise
arithmetization form, NOT the CRT-congruence / Freivalds "certificate-of-a-certificate" the panel named as
approach A's only viable form. This probe measures it. To verify `M = FᵀF`, instead of the full identity
(O(N²·r) terms), a Freivalds check verifies `M·v = Fᵀ(F·v)` for a vector `v` (a matVEC, O(N²) terms — `r×`
fewer). We compare, through the real Lean 4.31 kernel, at growing N:

  (1) FULL identity  `mm Fᵀ F == M`        — the lowRankOK-style Gram check (O(N²·r)); the baseline that walls ~N=60.
  (2) FREIVALDS      `mv M v == mv Fᵀ (mv F v)`  — one matVEC each side (O(N²)); the CRT/Freivalds core.

If (2) reaches meaningfully higher N than (1), the Freivalds/CRT direction is a partial mitigation worth
noting. If it walls at ~the same N, arithmetization is confirmed dead even in its viable form: the wall is the
O(N²) matvec fact count, which packing/mod-p (per-op, 7a-A) cannot remove.

HONEST CAVEAT (soundness, not measured here): a SINGLE-vector Freivalds is NOT sound (`M·v = C·v` for one `v`
does not imply `M = C`); soundness needs `N+1` evaluation points (→ ~N× the cost) or a Kronecker/packing
magnitude argument. So even a cost win here is not a sound win without that multiplier — this probe measures
only whether the matvec form escapes the term-count wall at all.

Run:  python scripts/probe_crt_freivalds.py   (needs docker + leibniz-lean-repl; skips cleanly if absent)
"""
from __future__ import annotations

import json
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
OUT = _ROOT / "docs" / "results" / "probe_crt_freivalds.json"
HDR = "set_option maxHeartbeats 0\nset_option maxRecDepth 1000000\n"
_PRE = (
    "def dotp (u v : List Int) : Int := (List.zipWith (· * ·) u v).foldl (· + ·) 0\n"
    "def col (m : List (List Int)) (j : Nat) : List Int := m.map (fun r => r.getD j 0)\n"
    "def mm (a b : List (List Int)) : List (List Int) :=\n"
    "  a.map (fun r => (List.range (b.headD []).length).map (fun j => dotp r (col b j)))\n"
    "def mv (m : List (List Int)) (v : List Int) : List Int := m.map (fun r => dotp r v)\n"
    "def tr (m : List (List Int)) : List (List Int) :=\n"
    "  (List.range (m.headD []).length).map (fun j => col m j)\n"
)


def _lcg(seed):
    s = seed & 0x7FFFFFFF
    while True:
        s = (1103515245 * s + 12345) & 0x7FFFFFFF
        yield s


def _lit1(v):
    return "[" + ", ".join(str(x) for x in v) + "]"


def _lit2(m):
    return "[" + ", ".join(_lit1(r) for r in m) + "]"


def _gram(n, r, g):
    F = [[(next(g) % 7) - 3 for _ in range(n)] for _ in range(r)]           # r×n factor
    M = [[sum(F[k][i] * F[k][j] for k in range(r)) for j in range(n)] for i in range(n)]
    return F, M


def full_src(n, r):
    g = _lcg(700 + n)
    F, M = _gram(n, r, g)
    Ft = [[F[k][i] for k in range(r)] for i in range(n)]                    # n×r = Fᵀ
    return (HDR + _PRE + f"def Ft : List (List Int) := {_lit2(Ft)}\n"
            + f"def F : List (List Int) := {_lit2(F)}\n"
            + f"def M : List (List Int) := {_lit2(M)}\n"
            + "theorem t : (mm Ft F == M) = true := by decide")


def freivalds_src(n, r):
    g = _lcg(700 + n)
    F, M = _gram(n, r, g)
    Ft = [[F[k][i] for k in range(r)] for i in range(n)]
    v = [((i * 2654435761) % 5) - 2 for i in range(n)]                       # a fixed test vector
    return (HDR + _PRE + f"def Ft : List (List Int) := {_lit2(Ft)}\n"
            + f"def F : List (List Int) := {_lit2(F)}\n"
            + f"def M : List (List Int) := {_lit2(M)}\n"
            + f"def v : List Int := {_lit1(v)}\n"
            + "theorem t : (mv M v == mv Ft (mv F v)) = true := by decide")


def _run(bk, src):
    r = bk._run(src, ())
    return (r is not None) and not any(m.get("severity") == "error" for m in (r.get("messages") or []))


def main(cap_s: int = 160) -> int:
    print("=== Probe A — CRT/Freivalds matvec vs full-identity Gram (real Lean 4.31 kernel) ===")
    try:
        from leibniz.backends.lean_repl import LeanReplBackend, available
    except Exception:
        available = lambda: False  # noqa: E731
    if not available():
        print("  SKIP (needs docker + leibniz-lean-repl)")
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps({"gate": "AMBER(lean-unavailable)"}, indent=2) + "\n")
        return 0
    bk = LeanReplBackend(timeout_s=cap_s)
    _run(bk, HDR + "theorem warm : (1 + 1 == 2) = true := by decide")

    r = 8
    full, frei = [], []
    for kind, builder, store in (("full", full_src, full), ("freivalds", freivalds_src, frei)):
        print(f"  {kind} (rank {r}):")
        for n in (40, 60, 80, 100):
            t0 = time.time()
            ok = _run(bk, builder(n, r))
            secs = round(time.time() - t0, 1)
            store.append({"n": n, "ok": ok, "secs": secs})
            print(f"    order {n:>3}: ok={ok} {secs}s", flush=True)
            if not (ok and secs < cap_s * 0.9):
                break

    def nmax(rows):
        return max([x["n"] for x in rows if x["ok"] and x["secs"] < cap_s * 0.9], default=0)
    nf, nfr = nmax(full), nmax(frei)
    frei_helps = nfr > nf
    out = {"gate": "GREEN(measured)", "tier": "probe", "ev": "AMPLIFICATION-research", "rank": r,
           "full_identity": full, "freivalds_matvec": frei,
           "full_N_max": nf, "freivalds_N_max": nfr, "freivalds_reaches_higher_N": frei_helps,
           "reading": (
               f"Full Gram identity (O(N²·r), r={r}) reaches N≈{nf}; the Freivalds matVEC check (O(N²)) reaches "
               f"N≈{nfr}. Freivalds {'reaches HIGHER N — the matvec form is a partial mitigation (r× fewer terms), worth banking' if frei_helps else 'does NOT reach meaningfully higher N — the O(N²) matvec fact count is the wall, and mod-p/packing (per-op, 7a-A) cannot remove it'}. "
               "Either way this is NOT a sound break: single-vector Freivalds needs N+1 points (~N× cost) or a "
               "Kronecker packing to be sound, so the measured cost is a LOWER bound on the sound check. Net: "
               "the CRT/Freivalds direction is "
               + ("a modest, still-far-from-414 mitigation for the arithmetization path — recorded, still bank-and-hold."
                  if frei_helps else
                  "confirmed to NOT escape the term-count wall — arithmetization is dead in its viable form too; "
                  "the escape remains structure/tiling (Haynsworth), not arithmetic."))}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2) + "\n")
    print(f"\n  full N_max ≈ {nf} | freivalds N_max ≈ {nfr} | freivalds helps: {frei_helps}")
    print(f"  -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
