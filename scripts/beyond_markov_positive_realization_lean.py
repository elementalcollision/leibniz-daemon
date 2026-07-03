"""Full in-Lean POSITIVE-REALIZATION identification (T8-c) — the last audit-linked follow-on. The T8-c
fooling-set certificate was previously a BOOLEAN predicate (`foolingOK M = true`) plus an on-paper argument
"foolingOK ⇒ nonneg-rank ≥ 4 ⇒ no 3-state positive HMM". This lifts that whole argument to PROVEN Lean
theorems, through the ADR-0011 Mathlib REPL. No trust surface touched.

Kernel-Q.E.D. (0 errors, 0 sorries; controls fail):
  * fooling_le_of_nonneg_factor -- GENERAL: if M >= 0 factors as F*B with F,B >= 0 (inner dim r) and there is
    a size-t fooling set (positive diagonal, vanishing cross-products), then t <= r. The soundness of the
    fooling certificate, proven via the injectivity argument (each fooling position picks a factor index; a
    positive summand of a positive sum; the picks are injective by the cross-product condition).
  * necklace_no_rank3_nonneg_factor -- the 4-cycle matrix NM admits NO rank-3 (or less) nonnegative
    factorization: any nonneg factorization has inner dim >= 4, i.e. nonneg-rank(NM) >= 4. Proven, not a
    boolean.
  * Tprod_nonneg + hankel_nonneg_factor -- a positive realization (init, op, fin all >= 0) factors every
    finite Hankel block as F*B with F,B >= 0, inner dim r (products/vecMuls of nonnegatives stay nonneg).
  * positive_realization_of_NM_needs_4_states -- the composition: any positive HMM/OOM whose Hankel block
    equals NM needs >= 4 states. So NO 3-state positive HMM produces the necklace's co-occurrence matrix.

Honest scope: this proves the positive-realization gap for the matrix NM (= 8 * the necklace's length-2 Hankel
block, audit-verified) end-to-end. The composed theorem holds for ANY positive OOM whose Hankel block is NM;
the necklace process IS such an OOM (8*H2 = NM). Defining the necklace as an OOM in Lean and discharging that
`hHb` hypothesis is the same plumbing pattern as the rank/infinite-order process defs — the thin residual.
Amplification, not discovery; behind the unbroken trust boundary.

Run:  python scripts/beyond_markov_positive_realization_lean.py   (needs the Lean REPL image; audit runs everywhere)
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
OUT = _ROOT / "docs" / "results" / "beyond_markov_positive_realization_lean.json"
IMPORTS = ("Mathlib.LinearAlgebra.Matrix.Rank", "Mathlib.Tactic")

LEAN_SRC = r'''open Finset in
/-- **Fooling-set lower bound on nonnegative factorization rank.** M ≥ 0 = F·B (F,B ≥ 0, inner dim r) with a
size-t fooling set ⇒ t ≤ r. Each fooling position picks a factor index (a positive summand of a positive sum),
injectively (the cross-product condition rules out shared indices). -/
theorem fooling_le_of_nonneg_factor {U V : Type*} [Fintype U] [Fintype V] {r t : Nat}
    (M : Matrix U V Rat) (F : Matrix U (Fin r) Rat) (B : Matrix (Fin r) V Rat)
    (hM : M = F * B) (hF : ∀ i k, 0 ≤ F i k) (hB : ∀ k j, 0 ≤ B k j)
    (row : Fin t → U) (col : Fin t → V)
    (hdiag : ∀ l, 0 < M (row l) (col l))
    (hfool : ∀ l m, l ≠ m → M (row l) (col m) * M (row m) (col l) = 0) :
    t ≤ r := by
  have hentry : ∀ i j, M i j = ∑ k, F i k * B k j := by
    intro i j; rw [hM, Matrix.mul_apply]
  have hchoose : ∀ l, ∃ k, 0 < F (row l) k ∧ 0 < B k (col l) := by
    intro l
    by_contra h
    push_neg at h
    have hterm : ∀ k ∈ (univ : Finset (Fin r)), F (row l) k * B k (col l) = 0 := by
      intro k _
      rcases (hF (row l) k).lt_or_eq with hFk | hFk
      · rw [le_antisymm (h k hFk) (hB k (col l)), mul_zero]
      · rw [← hFk, zero_mul]
    have hz := hdiag l
    rw [hentry, Finset.sum_eq_zero hterm] at hz
    exact lt_irrefl 0 hz
  choose φ hφF hφB using hchoose
  have hinj : Function.Injective φ := by
    intro l m hlm
    by_contra hne
    have h1 : 0 < M (row l) (col m) := by
      rw [hentry]
      refine lt_of_lt_of_le ?_ (Finset.single_le_sum (fun k _ => mul_nonneg (hF _ k) (hB k _)) (mem_univ (φ l)))
      exact mul_pos (hφF l) (by rw [hlm]; exact hφB m)
    have h2 : 0 < M (row m) (col l) := by
      rw [hentry]
      refine lt_of_lt_of_le ?_ (Finset.single_le_sum (fun k _ => mul_nonneg (hF _ k) (hB k _)) (mem_univ (φ m)))
      exact mul_pos (hφF m) (by rw [← hlm]; exact hφB l)
    nlinarith [h1, h2, hfool l m hne]
  simpa using Fintype.card_le_of_injective φ hinj

/-- The 4-cycle ("necklace") co-occurrence matrix. -/
def NM : Matrix (Fin 4) (Fin 4) Rat := !![1,1,0,0; 1,0,1,0; 0,1,0,1; 0,0,1,1]

/-- **NM admits no rank-3 (or less) nonnegative factorization** (nonneg-rank ≥ 4). -/
theorem necklace_no_rank3_nonneg_factor
    {r : Nat} (F : Matrix (Fin 4) (Fin r) Rat) (B : Matrix (Fin r) (Fin 4) Rat)
    (hF : ∀ i k, 0 ≤ F i k) (hB : ∀ k j, 0 ≤ B k j) (hM : NM = F * B) : 4 ≤ r := by
  refine fooling_le_of_nonneg_factor NM F B hM hF hB ![0,1,2,3] ![0,2,1,3] ?_ ?_
  · intro l; fin_cases l <;> simp [NM] <;> norm_num
  · intro l m hlm; fin_cases l <;> fin_cases m <;> simp_all [NM]

def Tprod {A : Type*} {r : Nat} (op : A -> Matrix (Fin r) (Fin r) Rat) :
    List A -> Matrix (Fin r) (Fin r) Rat
  | [] => 1
  | a :: w => op a * Tprod op w

def Pval {A : Type*} {r : Nat} (init : Fin r -> Rat) (op : A -> Matrix (Fin r) (Fin r) Rat)
    (fin : Fin r -> Rat) (w : List A) : Rat :=
  dotProduct init (Matrix.mulVec (Tprod op w) fin)

lemma Tprod_append {A : Type*} {r : Nat} (op : A -> Matrix (Fin r) (Fin r) Rat) (u v : List A) :
    Tprod op (u ++ v) = Tprod op u * Tprod op v := by
  induction u with
  | nil => simp [Tprod]
  | cons a u ih => simp [Tprod, ih, Matrix.mul_assoc]

lemma Pval_append {A : Type*} {r : Nat} (init : Fin r -> Rat) (op : A -> Matrix (Fin r) (Fin r) Rat)
    (fin : Fin r -> Rat) (u v : List A) :
    Pval init op fin (u ++ v)
      = dotProduct (Matrix.vecMul init (Tprod op u)) (Matrix.mulVec (Tprod op v) fin) := by
  rw [Pval, Tprod_append, ← Matrix.mulVec_mulVec, Matrix.dotProduct_mulVec]

lemma Tprod_nonneg {A : Type*} {r : Nat} (op : A -> Matrix (Fin r) (Fin r) Rat)
    (hop : ∀ a i j, 0 ≤ op a i j) : ∀ (w : List A) i j, 0 ≤ Tprod op w i j := by
  intro w
  induction w with
  | nil => intro i j; by_cases h : i = j <;> simp [Tprod, Matrix.one_apply, h]
  | cons a w ih => intro i j; simp only [Tprod, Matrix.mul_apply]
                   exact Finset.sum_nonneg (fun k _ => mul_nonneg (hop a i k) (ih k j))

/-- **Positive-OOM ⟹ nonnegative Hankel factorization.** -/
theorem hankel_nonneg_factor {A : Type*} {r : Nat} (init : Fin r -> Rat)
    (op : A -> Matrix (Fin r) (Fin r) Rat) (fin : Fin r -> Rat)
    (hinit : ∀ i, 0 ≤ init i) (hop : ∀ a i j, 0 ≤ op a i j) (hfin : ∀ i, 0 ≤ fin i)
    {p q : Nat} (u : Fin p -> List A) (v : Fin q -> List A) :
    ∃ (F : Matrix (Fin p) (Fin r) Rat) (B : Matrix (Fin r) (Fin q) Rat),
      (∀ i k, 0 ≤ F i k) ∧ (∀ k j, 0 ≤ B k j) ∧
      (fun i j => Pval init op fin (u i ++ v j)) = F * B := by
  refine ⟨fun i k => Matrix.vecMul init (Tprod op (u i)) k,
          fun k j => Matrix.mulVec (Tprod op (v j)) fin k, ?_, ?_, ?_⟩
  · intro i k; exact Finset.sum_nonneg (fun s _ => mul_nonneg (hinit s) (Tprod_nonneg op hop (u i) s k))
  · intro k j; exact Finset.sum_nonneg (fun s _ => mul_nonneg (Tprod_nonneg op hop (v j) k s) (hfin s))
  · ext i j; rw [Matrix.mul_apply, Pval_append]; rfl

/-- **No ≤3-state positive HMM/OOM produces the necklace co-occurrence matrix NM.** Any positive realization
whose Hankel block equals NM needs ≥ 4 states — the positive-realization gap, proven end-to-end. -/
theorem positive_realization_of_NM_needs_4_states {A : Type*} {r : Nat} (init : Fin r -> Rat)
    (op : A -> Matrix (Fin r) (Fin r) Rat) (fin : Fin r -> Rat)
    (hinit : ∀ i, 0 ≤ init i) (hop : ∀ a i j, 0 ≤ op a i j) (hfin : ∀ i, 0 ≤ fin i)
    (u v : Fin 4 -> List A) (hHb : (fun i j => Pval init op fin (u i ++ v j)) = NM) : 4 ≤ r := by
  obtain ⟨F, B, hF, hB, hfac⟩ := hankel_nonneg_factor init op fin hinit hop hfin u v
  exact necklace_no_rank3_nonneg_factor F B hF hB (hHb.symm.trans hfac)
'''


def controls(src):
    """Each mutation must make a theorem FAIL."""
    overclaim = src.replace("(hM : NM = F * B) : 4 ≤ r", "(hM : NM = F * B) : 5 ≤ r")
    corrupt_nm = src.replace("!![1,1,0,0; 1,0,1,0; 0,1,0,1; 0,0,1,1]", "!![1,1,1,0; 1,0,1,0; 0,1,0,1; 0,0,1,1]")
    assert overclaim != src and corrupt_nm != src
    return {"overclaim_nonneg_rank": overclaim, "corrupt_fooling_zero": corrupt_nm}


def audit() -> dict:
    """Cross-check (Python): NM is the necklace co-occurrence matrix — has the size-4 fooling set, rank 3, and
    equals 8 * the necklace chain's length-2 Hankel block. Confirms the Lean NM is the T8-c witness."""
    sys.path.insert(0, str(_ROOT))
    sys.path.insert(0, str(_ROOT / "scripts"))
    spec = importlib.util.spec_from_file_location("beyond_markov_mprp", _ROOT / "scripts" / "beyond_markov_mprp.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    NM = [[1, 1, 0, 0], [1, 0, 1, 0], [0, 1, 0, 1], [0, 0, 1, 1]]
    same = NM == m.M4
    fooling = m.fooling_ok(NM, m.FS_ROWS, m.FS_COLS)
    mc = m.matrix_cert(NM)
    pa = m.process_audit()
    return {"NM_is_M4": same, "fooling_size4_valid": fooling, "rank": mc["rank"],
            "process_8H2_is_NM": pa["h2_scaled_is_M"], "hankel_rank_stable_3": pa["hankel_rank_stable_3"],
            "ok": bool(same and fooling and mc["rank"] == 3 and pa["h2_scaled_is_M"])}


def main() -> int:
    aud = audit()
    print(f"audit: NM==M4={aud['NM_is_M4']}  fooling(size4)={aud['fooling_size4_valid']}  rank={aud['rank']}  "
          f"8*H2==NM (necklace)={aud['process_8H2_is_NM']}")

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
           "reading": ("Full in-Lean POSITIVE-REALIZATION identification (T8-c): the fooling-set certificate "
                       "is lifted from a boolean predicate to PROVEN theorems -- the general fooling lower "
                       "bound (t <= r), nonneg-rank(NM) >= 4, the positive-OOM nonneg-factorization bridge, and "
                       "the composition: no <=3-state positive HMM/OOM produces the necklace co-occurrence "
                       "matrix NM. GREEN = all theorems elaborate 0 errors/0 sorries, both controls (overclaim "
                       "5<=r; corrupt a fooling zero) fail, and the audit confirms NM is the necklace witness "
                       "(fooling set, rank 3, 8*H2=NM). Residual: the necklace-as-OOM definition discharging "
                       "the block=NM hypothesis (same plumbing as the rank/infinite-order process defs). "
                       "Amplification, not discovery. No trust surface touched.")}
    OUT.write_text(json.dumps(res, indent=2, default=str) + "\n")
    print(f"\ngate={gate}  kernel={kernel.get('status')} sound={kernel.get('sound')}\n-> {OUT}")
    return 0 if gate != "RED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
