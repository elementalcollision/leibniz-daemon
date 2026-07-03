"""Full in-Lean process identification (the F2b-scale follow-on): DEFINE a beyond-Markov process in Lean from
its OOM operators and DERIVE its Hankel rank from that definition — lifting the rank story from audit to genuine
Q.E.D. Verified through the ADR-0011 Mathlib REPL (the F2a pattern). No trust surface touched.

Across T8, the "audit half" was always the process-identification: e.g. "the even process's Hankel = F·B"
(rank-upper) was Python-verified, the kernel only proved the abstract lemma. This closes it for the RANK story.

Kernel-Q.E.D. (0 errors, 0 sorries; controls fail):
  * hankel_block_rank_le — GENERAL: for any r-dim OOM (init, op, fin) with P(w)=init·(∏op)·fin, EVERY finite
    Hankel block H[i,j]=P(u_i ++ v_j) has Matrix.rank ≤ r. Pure operator-product associativity (Tprod is a
    monoid hom; the Hankel factors through the r-dim state space) + rank_le_of_factor. The process-INTRINSIC
    rank-upper certificate — no per-process audit.
  * even_hankel_rank_le — the even process defined in Lean (eInit, eOp = the ε-machine operators, eFin): EVERY
    finite Hankel block has rank ≤ 2. A statement about the ACTUAL process, fully in-kernel.
  * eB_det / eB_rank_eq_two — a concrete 2×2 even-process Hankel block, its determinant COMPUTED in Lean
    (= 1/18 ≠ 0), so its rank = 2 (via IsUnit). Combined with the ≤2 bound: the even process's Hankel rank is
    EXACTLY 2 — proven from the operator definition, not asserted from Python.

Honest scope: this fully closes the RANK identification (upper + exact) in-kernel. The infinite-order (T8-b)
and positive-realization (T8-c) identifications remain the audit-linked follow-ons (they need the operator-power
closed form / fooling embedding proved in Lean). Amplification, not discovery.

Run:  python scripts/beyond_markov_process_lean.py   (needs the Lean REPL image; audit cross-check runs everywhere)
"""
from __future__ import annotations

import importlib.util
import json
import sys
from fractions import Fraction as Fr
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
OUT = _ROOT / "docs" / "results" / "beyond_markov_process_lean.json"
IMPORTS = ("Mathlib.LinearAlgebra.Matrix.Rank", "Mathlib.Tactic")

LEAN_SRC = r'''open Matrix in
/-- A matrix that factors through `ℚ^r` has rank ≤ r (the rank-upper engine). -/
theorem rank_le_of_factor {U V : Type*} [Fintype U] [Fintype V] {r : Nat}
    (H : Matrix U V Rat) (F : Matrix U (Fin r) Rat) (B : Matrix (Fin r) V Rat)
    (hfac : H = F * B) : Matrix.rank H <= r := by
  rw [hfac]
  exact le_trans (Matrix.rank_mul_le_left F B) (le_trans (Matrix.rank_le_card_width F) (by simp))

variable {A : Type*} {r : Nat}

/-- The word-operator product of an OOM: `Tprod op (a::w) = op a * Tprod op w`. -/
def Tprod (op : A -> Matrix (Fin r) (Fin r) Rat) : List A -> Matrix (Fin r) (Fin r) Rat
  | [] => 1
  | a :: w => op a * Tprod op w

/-- The word probability of an OOM: `P(w) = init · (Tprod op w) · fin`. -/
def Pval (init : Fin r -> Rat) (op : A -> Matrix (Fin r) (Fin r) Rat) (fin : Fin r -> Rat) (w : List A) : Rat :=
  dotProduct init (Matrix.mulVec (Tprod op w) fin)

/-- `Tprod` is a monoid homomorphism from `(List A, ++)` to `(Matrix, *)`. -/
lemma Tprod_append (op : A -> Matrix (Fin r) (Fin r) Rat) (u v : List A) :
    Tprod op (u ++ v) = Tprod op u * Tprod op v := by
  induction u with
  | nil => simp [Tprod]
  | cons a u ih => simp [Tprod, ih, Matrix.mul_assoc]

/-- The Hankel factorization: `P(u ++ v) = (init · Tprod u) · (Tprod v · fin)`. -/
lemma Pval_append (init : Fin r -> Rat) (op : A -> Matrix (Fin r) (Fin r) Rat) (fin : Fin r -> Rat)
    (u v : List A) :
    Pval init op fin (u ++ v)
      = dotProduct (Matrix.vecMul init (Tprod op u)) (Matrix.mulVec (Tprod op v) fin) := by
  rw [Pval, Tprod_append, ← Matrix.mulVec_mulVec, Matrix.dotProduct_mulVec]

/-- **OOM dimension bound.** For any r-dim OOM, every finite Hankel block has rank ≤ r. The Hankel factors
as `F * B` through the r-dim state space (`F[i] = init · Tprod u_i`, `B[j] = Tprod v_j · fin`). -/
theorem hankel_block_rank_le (init : Fin r -> Rat) (op : A -> Matrix (Fin r) (Fin r) Rat) (fin : Fin r -> Rat)
    {p q : Nat} (u : Fin p -> List A) (v : Fin q -> List A) :
    Matrix.rank (fun i j => Pval init op fin (u i ++ v j)) <= r := by
  refine rank_le_of_factor _ (fun i k => Matrix.vecMul init (Tprod op (u i)) k)
                             (fun k j => Matrix.mulVec (Tprod op (v j)) fin k) ?_
  ext i j
  rw [Matrix.mul_apply, Pval_append]
  rfl

/-- The even process ε-machine as a 2-dim OOM (defined in Lean, not asserted from Python). -/
def eInit : Fin 2 -> Rat := ![2/3, 1/3]
def eOp : Fin 2 -> Matrix (Fin 2) (Fin 2) Rat := ![!![1/2,0;0,0], !![0,1/2;1,0]]
def eFin : Fin 2 -> Rat := ![1, 1]

/-- **Every finite Hankel block of the even process has rank ≤ 2** — the actual process, fully in-kernel. -/
theorem even_hankel_rank_le {p q : Nat} (u : Fin p -> List (Fin 2)) (v : Fin q -> List (Fin 2)) :
    Matrix.rank (fun i j => Pval eInit eOp eFin (u i ++ v j)) <= 2 :=
  hankel_block_rank_le eInit eOp eFin u v

/-- A concrete 2×2 even-process Hankel block (pasts/futures {"0","1"}). -/
def eB : Matrix (Fin 2) (Fin 2) Rat := fun i j => Pval eInit eOp eFin (![[0],[1]] i ++ ![[0],[1]] j)

/-- Its determinant, COMPUTED in the kernel from the operator definition: `det = 1/18 ≠ 0`. -/
theorem eB_det : eB.det = 1/18 := by
  rw [Matrix.det_fin_two]
  simp [eB, Pval, Tprod, eInit, eOp, eFin, Matrix.mulVec, dotProduct, Matrix.mul_apply,
        Fin.sum_univ_two, Matrix.cons_val_zero, Matrix.cons_val_one, Matrix.head_cons] <;> norm_num

/-- **The even process's Hankel rank is EXACTLY 2** — derived from the OOM definition, not audited. -/
theorem eB_rank_eq_two : Matrix.rank eB = 2 := by
  have hu : IsUnit eB := (Matrix.isUnit_iff_isUnit_det eB).mpr (by rw [eB_det]; norm_num)
  rw [Matrix.rank_of_isUnit eB hu, Fintype.card_fin]
'''


def controls(src):
    """Each mutation must make a theorem FAIL."""
    wrong_det = src.replace("theorem eB_det : eB.det = 1/18", "theorem eB_det : eB.det = 1/17")
    wrong_dim = src.replace("Matrix.rank (fun i j => Pval eInit eOp eFin (u i ++ v j)) <= 2",
                            "Matrix.rank (fun i j => Pval eInit eOp eFin (u i ++ v j)) <= 1")
    assert wrong_det != src and wrong_dim != src
    return {"wrong_determinant": wrong_det, "understated_dimension": wrong_dim}


def audit() -> dict:
    """Cross-check (Python): the Lean-encoded even process matches the actual even process — P(00)=1/6 and the
    encoded 2×2 block has det 1/18. Confirms the Lean definition IS the even process."""
    sys.path.insert(0, str(_ROOT))
    sys.path.insert(0, str(_ROOT / "scripts"))
    spec = importlib.util.spec_from_file_location("beyond_markov_cert", _ROOT / "scripts" / "beyond_markov_cert.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    ev = m.even_process()
    p00 = m.prob(ev, (0, 0))
    block = [[m.prob(ev, u + v) for v in [(0,), (1,)]] for u in [(0,), (1,)]]
    det = block[0][0] * block[1][1] - block[0][1] * block[1][0]
    return {"P00": str(p00), "P00_is_1_6": p00 == Fr(1, 6), "block_det": str(det),
            "block_det_is_1_18": det == Fr(1, 18), "ok": p00 == Fr(1, 6) and det == Fr(1, 18)}


def main() -> int:
    aud = audit()
    print(f"audit: P(00)={aud['P00']} (==1/6: {aud['P00_is_1_6']})  block det={aud['block_det']} "
          f"(==1/18: {aud['block_det_is_1_18']})")

    kernel = {"status": "not run"}
    try:
        from leibniz.backends.lean_repl import LeanReplBackend
        bk = LeanReplBackend(timeout_s=900)

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
           "reading": ("Full in-Lean process identification for the RANK story: the even process is defined in "
                       "Lean from its OOM operators and its Hankel rank is DERIVED = 2 (every block ≤ 2 via the "
                       "general OOM dimension bound; a concrete block's det = 1/18 computed in-kernel ⇒ rank 2). "
                       "GREEN = all theorems elaborate 0 errors/0 sorries, both controls fail, and the Python "
                       "cross-check confirms the Lean definition IS the even process. Lifts rank-upper/rank-exact "
                       "from audit to Q.E.D.; infinite-order (T8-b) and positive-realization (T8-c) "
                       "identifications remain the audit-linked follow-ons. No trust surface touched.")}
    OUT.write_text(json.dumps(res, indent=2, default=str) + "\n")
    print(f"\ngate={gate}  kernel={kernel.get('status')} sound={kernel.get('sound')}\n-> {OUT}")
    return 0 if gate != "RED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
