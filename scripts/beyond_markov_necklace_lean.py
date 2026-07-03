"""Tie off the last plumbing thread: define the NECKLACE process as an OOM in Lean and derive its
positive-realization gap end-to-end — making T8-c (and the whole beyond-Markov track) ZERO-AUDIT. Previously
the composed positive-realization theorem was stated for "any positive OOM whose Hankel block equals NM", with
"the necklace's block = NM" a Python audit. This defines the necklace's operators in Lean and discharges that
hypothesis, so the gap is proven about the actual process. Verified through the ADR-0011 Mathlib REPL.

Kernel-Q.E.D. (0 errors, 0 sorries; controls fail):
  * fooling_le_of_nonneg_factor + hankel_nonneg_factor -- the general soundness + positive-OOM factorization
    bridge (from the T8-c positive-realization work).
  * nInit / nOp / nFin -- the necklace 4-state chain as an OOM in Lean (init uniform, op = the labelled
    transition operators, fin = ones), so P(w) = the Markov-chain probability.
  * necklace_block_no_rank3_nonneg_factor -- the necklace's OWN length-2 Hankel block (computed from the OOM
    definition) has the size-4 fooling set, so admits NO rank-3 nonnegative factorization. The fooling
    conditions are evaluated in-kernel on the actual block (16 exact Fin-4 evaluations).
  * necklace_positive_realization_needs_4 -- composition: any positive HMM/OOM whose length-2 Hankel block
    equals the necklace's needs >= 4 states -> NO <=3-state positive HMM realizes the necklace process.
  * necklace_is_positive_realization -- nInit, nOp, nFin are all >= 0, so the necklace IS a valid 4-state
    positive realization: the bound is tight, minimal positive realization = 4 > 3 = ordinary rank.

With this, ALL of the even process's and the necklace's beyond-Markov properties (rank, infinite order,
positive-realization gap) are kernel-derived from Lean process definitions — zero audit. Amplification, not
discovery; no trust surface touched.

Run:  python scripts/beyond_markov_necklace_lean.py   (needs the Lean REPL image; audit runs everywhere)
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
OUT = _ROOT / "docs" / "results" / "beyond_markov_necklace_lean.json"
IMPORTS = ("Mathlib.LinearAlgebra.Matrix.Rank", "Mathlib.Tactic")

LEAN_SRC = r'''open Finset in
theorem fooling_le_of_nonneg_factor {U V : Type*} [Fintype U] [Fintype V] {r t : Nat}
    (M : Matrix U V Rat) (F : Matrix U (Fin r) Rat) (B : Matrix (Fin r) V Rat)
    (hM : M = F * B) (hF : ∀ i k, 0 ≤ F i k) (hB : ∀ k j, 0 ≤ B k j)
    (row : Fin t → U) (col : Fin t → V)
    (hdiag : ∀ l, 0 < M (row l) (col l))
    (hfool : ∀ l m, l ≠ m → M (row l) (col m) * M (row m) (col l) = 0) : t ≤ r := by
  have hentry : ∀ i j, M i j = ∑ k, F i k * B k j := by intro i j; rw [hM, Matrix.mul_apply]
  have hchoose : ∀ l, ∃ k, 0 < F (row l) k ∧ 0 < B k (col l) := by
    intro l; by_contra h; push_neg at h
    have hterm : ∀ k ∈ (univ : Finset (Fin r)), F (row l) k * B k (col l) = 0 := by
      intro k _; rcases (hF (row l) k).lt_or_eq with hFk | hFk
      · rw [le_antisymm (h k hFk) (hB k (col l)), mul_zero]
      · rw [← hFk, zero_mul]
    have hz := hdiag l; rw [hentry, Finset.sum_eq_zero hterm] at hz; exact lt_irrefl 0 hz
  choose φ hφF hφB using hchoose
  have hinj : Function.Injective φ := by
    intro l m hlm; by_contra hne
    have h1 : 0 < M (row l) (col m) := by
      rw [hentry]; refine lt_of_lt_of_le ?_ (Finset.single_le_sum (fun k _ => mul_nonneg (hF _ k) (hB k _)) (mem_univ (φ l)))
      exact mul_pos (hφF l) (by rw [hlm]; exact hφB m)
    have h2 : 0 < M (row m) (col l) := by
      rw [hentry]; refine lt_of_lt_of_le ?_ (Finset.single_le_sum (fun k _ => mul_nonneg (hF _ k) (hB k _)) (mem_univ (φ m)))
      exact mul_pos (hφF m) (by rw [← hlm]; exact hφB l)
    nlinarith [h1, h2, hfool l m hne]
  simpa using Fintype.card_le_of_injective φ hinj

def Tprod {A : Type*} {r : Nat} (op : A -> Matrix (Fin r) (Fin r) Rat) : List A -> Matrix (Fin r) (Fin r) Rat
  | [] => 1
  | a :: w => op a * Tprod op w
def Pval {A : Type*} {r : Nat} (init : Fin r -> Rat) (op : A -> Matrix (Fin r) (Fin r) Rat)
    (fin : Fin r -> Rat) (w : List A) : Rat := dotProduct init (Matrix.mulVec (Tprod op w) fin)
lemma Tprod_append {A : Type*} {r : Nat} (op : A -> Matrix (Fin r) (Fin r) Rat) (u v : List A) :
    Tprod op (u ++ v) = Tprod op u * Tprod op v := by
  induction u with
  | nil => simp [Tprod]
  | cons a u ih => simp [Tprod, ih, Matrix.mul_assoc]
lemma Pval_append {A : Type*} {r : Nat} (init : Fin r -> Rat) (op : A -> Matrix (Fin r) (Fin r) Rat)
    (fin : Fin r -> Rat) (u v : List A) :
    Pval init op fin (u ++ v) = dotProduct (Matrix.vecMul init (Tprod op u)) (Matrix.mulVec (Tprod op v) fin) := by
  rw [Pval, Tprod_append, ← Matrix.mulVec_mulVec, Matrix.dotProduct_mulVec]
lemma Tprod_nonneg {A : Type*} {r : Nat} (op : A -> Matrix (Fin r) (Fin r) Rat)
    (hop : ∀ a i j, 0 ≤ op a i j) : ∀ (w : List A) i j, 0 ≤ Tprod op w i j := by
  intro w
  induction w with
  | nil => intro i j; by_cases h : i = j <;> simp [Tprod, Matrix.one_apply, h]
  | cons a w ih => intro i j; simp only [Tprod, Matrix.mul_apply]
                   exact Finset.sum_nonneg (fun k _ => mul_nonneg (hop a i k) (ih k j))
theorem hankel_nonneg_factor {A : Type*} {r : Nat} (init : Fin r -> Rat)
    (op : A -> Matrix (Fin r) (Fin r) Rat) (fin : Fin r -> Rat)
    (hinit : ∀ i, 0 ≤ init i) (hop : ∀ a i j, 0 ≤ op a i j) (hfin : ∀ i, 0 ≤ fin i)
    {p q : Nat} (u : Fin p -> List A) (v : Fin q -> List A) :
    ∃ (F : Matrix (Fin p) (Fin r) Rat) (B : Matrix (Fin r) (Fin q) Rat),
      (∀ i k, 0 ≤ F i k) ∧ (∀ k j, 0 ≤ B k j) ∧ (fun i j => Pval init op fin (u i ++ v j)) = F * B := by
  refine ⟨fun i k => Matrix.vecMul init (Tprod op (u i)) k, fun k j => Matrix.mulVec (Tprod op (v j)) fin k, ?_, ?_, ?_⟩
  · intro i k; exact Finset.sum_nonneg (fun s _ => mul_nonneg (hinit s) (Tprod_nonneg op hop (u i) s k))
  · intro k j; exact Finset.sum_nonneg (fun s _ => mul_nonneg (Tprod_nonneg op hop (v j) k s) (hfin s))
  · ext i j; rw [Matrix.mul_apply, Pval_append]; rfl

/-- The necklace 4-state chain as an OOM in Lean: init uniform, op = the labelled transition operators
(row a = A a, else 0), fin = ones. Then `Pval nInit nOp nFin` is the Markov-chain word probability. -/
def nInit : Fin 4 -> Rat := ![1/4, 1/4, 1/4, 1/4]
def nOp : Fin 4 -> Matrix (Fin 4) (Fin 4) Rat :=
  ![!![1/2,1/2,0,0; 0,0,0,0; 0,0,0,0; 0,0,0,0], !![0,0,0,0; 1/2,0,1/2,0; 0,0,0,0; 0,0,0,0],
    !![0,0,0,0; 0,0,0,0; 0,1/2,0,1/2; 0,0,0,0], !![0,0,0,0; 0,0,0,0; 0,0,0,0; 0,0,1/2,1/2]]
def nFin : Fin 4 -> Rat := ![1, 1, 1, 1]

/-- The necklace's own length-2 Hankel block (computed from the OOM) admits no rank-3 nonneg factorization:
its size-4 fooling set is evaluated in-kernel on the actual block. -/
theorem necklace_block_no_rank3_nonneg_factor {r : Nat}
    (F : Matrix (Fin 4) (Fin r) Rat) (B : Matrix (Fin r) (Fin 4) Rat)
    (hF : ∀ i k, 0 ≤ F i k) (hB : ∀ k j, 0 ≤ B k j)
    (hM : (fun i j => Pval nInit nOp nFin [i, j]) = F * B) : 4 ≤ r := by
  refine fooling_le_of_nonneg_factor _ F B hM hF hB ![0,1,2,3] ![0,2,1,3] ?_ ?_
  · intro l
    fin_cases l <;> simp [Pval, Tprod, nInit, nOp, nFin, Matrix.mulVec, dotProduct, Matrix.mul_apply, Fin.sum_univ_four, Matrix.cons_val] <;> norm_num
  · intro l m hlm
    fin_cases l <;> fin_cases m <;> simp_all [Pval, Tprod, nInit, nOp, nFin, Matrix.mulVec, dotProduct, Matrix.mul_apply, Fin.sum_univ_four, Matrix.cons_val]

/-- **No ≤3-state positive HMM/OOM realizes the necklace process.** Any positive realization whose length-2
Hankel block equals the necklace's block needs ≥ 4 states. -/
theorem necklace_positive_realization_needs_4 {A : Type*} {r : Nat} (init : Fin r -> Rat)
    (op : A -> Matrix (Fin r) (Fin r) Rat) (fin : Fin r -> Rat)
    (hinit : ∀ i, 0 ≤ init i) (hop : ∀ a i j, 0 ≤ op a i j) (hfin : ∀ i, 0 ≤ fin i)
    (u v : Fin 4 -> List A)
    (hHb : (fun i j => Pval init op fin (u i ++ v j)) = (fun i j => Pval nInit nOp nFin [i, j])) : 4 ≤ r := by
  obtain ⟨F, B, hF, hB, hfac⟩ := hankel_nonneg_factor init op fin hinit hop hfin u v
  exact necklace_block_no_rank3_nonneg_factor F B hF hB (hHb.symm.trans hfac)

/-- The necklace IS a valid 4-state positive realization: minimal positive realization = 4 > 3 = rank. -/
theorem necklace_is_positive_realization :
    (∀ i, (0:Rat) ≤ nInit i) ∧ (∀ a i j, (0:Rat) ≤ nOp a i j) ∧ (∀ i, (0:Rat) ≤ nFin i) := by
  refine ⟨?_, ?_, ?_⟩
  · intro i; fin_cases i <;> norm_num [nInit]
  · intro a i j; fin_cases a <;> fin_cases i <;> fin_cases j <;> simp [nOp, Matrix.cons_val] <;> norm_num
  · intro i; fin_cases i <;> norm_num [nFin]
'''


def controls(src):
    """Each mutation must make a theorem FAIL."""
    corrupt_op = src.replace("!![1/2,1/2,0,0; 0,0,0,0; 0,0,0,0; 0,0,0,0]",
                             "!![1/2,1/2,1/2,0; 0,0,0,0; 0,0,0,0; 0,0,0,0]")  # fills a structural zero -> fooling breaks
    overclaim = src.replace("(hM : (fun i j => Pval nInit nOp nFin [i, j]) = F * B) : 4 ≤ r",
                            "(hM : (fun i j => Pval nInit nOp nFin [i, j]) = F * B) : 5 ≤ r")
    assert corrupt_op != src and overclaim != src
    return {"corrupt_operator_zero": corrupt_op, "overclaim_states": overclaim}


def audit() -> dict:
    """Cross-check (Python): the Lean necklace OOM reproduces the necklace chain — its length-2 block is
    (1/4)*A with the size-4 fooling set, and 8*H2 equals the T8-c witness matrix."""
    sys.path.insert(0, str(_ROOT))
    sys.path.insert(0, str(_ROOT / "scripts"))
    spec = importlib.util.spec_from_file_location("beyond_markov_mprp", _ROOT / "scripts" / "beyond_markov_mprp.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    A, pi = m.necklace()
    # nBlock[a][b] = P(ab) = pi[a]*A[a][b]  (the Lean Pval nInit nOp nFin [a,b])
    block = [[pi[a] * A[a][b] for b in range(4)] for a in range(4)]
    block_int8 = all(8 * block[a][b] == m.M4[a][b] for a in range(4) for b in range(4))
    fooling = m.fooling_ok([[1 if block[a][b] > 0 else 0 for b in range(4)] for a in range(4)],
                           m.FS_ROWS, m.FS_COLS)
    pa = m.process_audit()
    return {"block_8x_is_M4": block_int8, "fooling_on_block": fooling,
            "hankel_rank_stable_3": pa["hankel_rank_stable_3"],
            "ok": bool(block_int8 and fooling and pa["hankel_rank_stable_3"])}


def main() -> int:
    aud = audit()
    print(f"audit: 8*nBlock==M4={aud['block_8x_is_M4']}  fooling(block)={aud['fooling_on_block']}  "
          f"full-Hankel rank 3={aud['hankel_rank_stable_3']}")

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
           "reading": ("Tie-off: the necklace process is defined as an OOM in Lean (nInit, nOp, nFin) and its "
                       "positive-realization gap is derived from that definition -- no <=3-state positive HMM/OOM "
                       "realizes it (its own length-2 Hankel block has a size-4 fooling set, evaluated in-kernel), "
                       "while the necklace itself is a valid 4-state positive realization (nonneg init/op/fin). So "
                       "minimal positive realization = 4 > 3 = ordinary rank, ZERO AUDIT. GREEN = all theorems "
                       "elaborate 0 errors/0 sorries, both controls (corrupt an operator zero; overclaim 5<=r) "
                       "fail, and the Python cross-check confirms the Lean OOM is the necklace chain. The whole "
                       "beyond-Markov track is now kernel-derived from process definitions. Amplification, not "
                       "discovery. No trust surface touched.")}
    OUT.write_text(json.dumps(res, indent=2, default=str) + "\n")
    print(f"\ngate={gate}  kernel={kernel.get('status')} sound={kernel.get('sound')}\n-> {OUT}")
    return 0 if gate != "RED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
