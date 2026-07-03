"""T8 rank-UPPER bridge lemma — global Hankel rank <= r from a linear representation, kernel-verified in
Lean/Mathlib. Closes the panel's soundness gap: a finite window of vanishing minors does NOT prove global
rank <= r (T8-a's rank-lower minor only certifies rank >= r). The sound rank-UPPER certificate is a
FACTORIZATION: a linear representation P(w)=alpha.T_w.omega gives H[u,v]=P(uv)=(alpha T_u)(T_v omega)=F.B,
inner dim r, so rank(H) <= r. Combined with T8-a's nonsingular r-minor (rank >= r), this pins rank = r EXACTLY.

Kernel-Q.E.D. (Mathlib REPL, the F2a pattern; 0 errors / 0 sorries; controls fail):
  * rank_le_of_factor      -- H = F*B (F: U x Fin r, B: Fin r x V)  =>  Matrix.rank H <= r. The reusable
                              rank-UPPER engine (rank_mul_le_left + rank_le_card_width).
  * rank_eq_of_factor_of_ge -- with r <= Matrix.rank H (the T8-a minor, certified separately in core Lean),
                              Matrix.rank H = r EXACTLY (le_antisymm).
  * Hc_factor / Hc_rank_le_2 -- the lemma FIRES on a concrete rational matrix: the 3x3 rank-2
                              !![1,2,3; 2,4,6; 1,1,1] = !![1,0;2,0;0,1] * !![1,2,3;1,1,1], so rank <= 2.

Audit side (exact-rational): the even process's word-Hankel factors as H = F.B with F[u]=pi.T_u, B[v]=T_v.1
straight from its 2-dim OOM (inner dim 2) -- so the lemma applies to a real beyond-Markov process; with a
nonsingular 2x2 Hankel minor (T8-a), rank(H)=2 exactly. Honest tiering (per the panel): the lemma is Q.E.D.;
the process's factorization is audit (full in-Lean identification is the F2b-scale follow-on). No trust
surface touched; amplification, not discovery.

Run:  python scripts/beyond_markov_rank_upper.py   (needs the Lean REPL image; audit legs run everywhere)
"""
from __future__ import annotations

import importlib.util
import json
import sys
from fractions import Fraction as Fr
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
OUT = _ROOT / "docs" / "results" / "beyond_markov_rank_upper.json"
IMPORTS = ("Mathlib.LinearAlgebra.Matrix.Rank", "Mathlib.Tactic")

LEAN_SRC = r'''open Matrix in
/-- **Rank-UPPER bridge.** A matrix that factors through `ℚ^r` has rank ≤ r. For a Hankel matrix
`H[u,v]=P(uv)`, a linear representation `P(w)=α·T_w·ω` gives `H = F·B` with `F[u]=α T_u`, `B[v]=T_v ω`,
inner dimension r. This is the SOUND global rank-upper certificate (finite-window minors do not prove it). -/
theorem rank_le_of_factor {U V : Type*} [Fintype U] [Fintype V] {r : ℕ}
    (H : Matrix U V ℚ) (F : Matrix U (Fin r) ℚ) (B : Matrix (Fin r) V ℚ)
    (hfac : H = F * B) : Matrix.rank H ≤ r := by
  rw [hfac]
  exact le_trans (Matrix.rank_mul_le_left F B) (le_trans (Matrix.rank_le_card_width F) (by simp))

open Matrix in
/-- **Rank-EXACT.** The factorization bounds rank ABOVE by r; a lower bound `r ≤ rank H` (from a nonsingular
r-minor, certified separately in core Lean, the T8-a certificate) pins `rank H = r`. -/
theorem rank_eq_of_factor_of_ge {U V : Type*} [Fintype U] [Fintype V] {r : ℕ}
    (H : Matrix U V ℚ) (F : Matrix U (Fin r) ℚ) (B : Matrix (Fin r) V ℚ)
    (hfac : H = F * B) (hge : r ≤ Matrix.rank H) : Matrix.rank H = r :=
  le_antisymm (rank_le_of_factor H F B hfac) hge

/-- The lemma fires on a concrete rank-2 rational matrix. -/
def Hc : Matrix (Fin 3) (Fin 3) ℚ := !![1,2,3; 2,4,6; 1,1,1]
def Fc : Matrix (Fin 3) (Fin 2) ℚ := !![1,0; 2,0; 0,1]
def Bc : Matrix (Fin 2) (Fin 3) ℚ := !![1,2,3; 1,1,1]
theorem Hc_factor : Hc = Fc * Bc := by
  ext i j; fin_cases i <;> fin_cases j <;> simp [Hc, Fc, Bc, Matrix.mul_apply, Fin.sum_univ_two] <;> norm_num
theorem Hc_rank_le_2 : Matrix.rank Hc ≤ 2 := rank_le_of_factor Hc Fc Bc Hc_factor
'''


def controls(src):
    """Each mutation must make a theorem FAIL."""
    bad_factor = src.replace("!![1,2,3; 2,4,6; 1,1,1]", "!![9,2,3; 2,4,6; 1,1,1]")  # Hc != Fc*Bc -> Hc_factor fails
    bad_bound = src.replace("theorem Hc_rank_le_2 : Matrix.rank Hc ≤ 2",
                            "theorem Hc_rank_le_2 : Matrix.rank Hc ≤ 1")            # rank_le gives <=2, not <=1
    assert bad_factor != src and bad_bound != src
    return {"bad_factorization": bad_factor, "understated_bound": bad_bound}


# --------------------------------------------------------------------------------------------------------
# Audit: the even process's word-Hankel factors through ℚ^2 (its OOM), so the lemma applies; with a
# nonsingular 2x2 minor (T8-a) its Hankel rank is EXACTLY 2.
# --------------------------------------------------------------------------------------------------------
def _load_cert():
    sys.path.insert(0, str(_ROOT))
    sys.path.insert(0, str(_ROOT / "scripts"))
    spec = importlib.util.spec_from_file_location("beyond_markov_cert", _ROOT / "scripts" / "beyond_markov_cert.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _words(alph, L):
    out, cur = [], [()]
    for _ in range(L):
        cur = [c + (a,) for c in cur for a in alph]
        out += cur
    return out


def even_factorization_audit(L=3) -> dict:
    m = _load_cert()
    ev = m.even_process()
    pi, T = ev["pi"], ev["T"]

    def vecmat(v, M):
        return [sum(v[i] * M[i][j] for i in range(len(M))) for j in range(len(M[0]))]

    def Trow(u):                       # F[u] = pi . T_u   (row 2-vector)
        v = pi[:]
        for s in u:
            v = vecmat(v, T[s])
        return v

    def Tcol(w):                       # B[v] = T_v . 1    (col 2-vector)
        v = [Fr(1), Fr(1)]
        for s in reversed(w):
            v = [sum(T[s][i][j] * v[j] for j in range(2)) for i in range(2)]
        return v

    U = _words(range(2), L)
    # H[u,v] = P(uv) = F[u] . B[v]  where F[u]=pi T_u, B[v]=T_v 1 : verify H = F B, inner dim 2
    factor_ok = all(sum(Trow(u)[k] * Tcol(v)[k] for k in range(2)) == m.prob(ev, u + v)
                    for u in U for v in U)
    # rank >= 2: a nonsingular 2x2 Hankel minor (pasts {(),(1,)} x futures {(0,),(1,)})
    H2 = [[m.prob(ev, u + v) for v in [(0,), (1,)]] for u in [(), (1,)]]
    minor = H2[0][0] * H2[1][1] - H2[0][1] * H2[1][0]
    return {"inner_dim": 2, "factorization_H_eq_FB": factor_ok, "words_len<=": L,
            "rank_ge2_minor_det": str(minor), "rank_ge2": minor != 0,
            "rank_exact_2": bool(factor_ok and minor != 0),
            "ok": bool(factor_ok and minor != 0)}


def main() -> int:
    aud = even_factorization_audit()
    print(f"audit (even process): H=F.B inner-dim-2 factorization={aud['factorization_H_eq_FB']}  "
          f"rank>=2 minor det={aud['rank_ge2_minor_det']}  -> rank exact 2={aud['rank_exact_2']}")

    kernel = {"status": "not run"}
    try:
        from leibniz.backends.lean_repl import LeanReplBackend
        bk = LeanReplBackend(timeout_s=600)

        def check(src):
            r = bk._run(src, IMPORTS)
            if r is None:
                return None, ["no response"]
            msgs = r.get("messages", []) or []
            errs = [mm for mm in msgs if mm.get("severity") == "error"]
            sorries = [mm for mm in msgs if "sorry" in (mm.get("data") or "")]
            return (not errs and not sorries), [(mm.get("data") or "")[:140] for mm in errs[:2]]

        ok, err = check(LEAN_SRC)
        ctl = {}
        for name, csrc in controls(LEAN_SRC).items():
            cok, _ = check(csrc)
            ctl[name] = {"failed_as_required": cok is False}
        controls_fail = all(v["failed_as_required"] for v in ctl.values())
        kernel = {"status": "checked", "theorems_ok": ok, "theorem_errors": err,
                  "controls": ctl, "controls_all_fail": controls_fail,
                  "sound": bool(ok is True and controls_fail)}
        print(f"  kernel: theorems_ok={ok}  controls_all_fail={controls_fail}")
        if err:
            print(f"    errors: {err}")
    except Exception as ex:  # pragma: no cover
        kernel = {"status": f"unavailable ({type(ex).__name__}: {ex})"}
        print(f"  kernel: {kernel['status']}")

    gate = ("GREEN" if aud["ok"] and kernel.get("sound") is True else
            "AMBER(kernel-unavailable)" if aud["ok"] and "unavailable" in str(kernel.get("status")) else "RED")
    res = {"gate": gate, "audit": aud, "kernel": kernel, "imports": list(IMPORTS),
           "reading": ("T8 rank-UPPER bridge lemma, kernel-verified in Lean/Mathlib: a factorization H=F.B "
                       "(inner dim r) proves the GLOBAL rank(H) <= r that window minors cannot. GREEN = "
                       "rank_le_of_factor + rank_eq_of_factor_of_ge + the concrete Hc instantiation elaborate "
                       "0 errors/0 sorries AND both controls (broken factorization; understated bound) FAIL, "
                       "AND the even-process word-Hankel factors through Q^2 (audit) with a nonsingular 2x2 "
                       "minor -> rank EXACTLY 2. The lemma is Q.E.D.; the process factorization is audit "
                       "(full in-Lean identification is F2b-scale). No trust surface touched.")}
    OUT.write_text(json.dumps(res, indent=2, default=str) + "\n")
    print(f"\ngate={gate}  kernel={kernel.get('status')} sound={kernel.get('sound')}\n-> {OUT}")
    return 0 if gate != "RED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
