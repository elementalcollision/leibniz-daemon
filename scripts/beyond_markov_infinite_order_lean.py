"""Full in-Lean process identification (INFINITE ORDER) — the even process's infinite Markov order derived in
the kernel from its OOM operator definition, end-to-end, no audit link. The flashiest F2b-scale lift: a
textbook process proven infinite-order purely from its operators, through the ADR-0011 Mathlib REPL.

This lifts T8-b (which proved the ABSTRACT recurrence sequence nonzero, with "evenGap = the process's gap" as a
Python audit) to a genuine Q.E.D. about the even process itself.

Kernel-Q.E.D. (0 errors, 0 sorries; controls fail):
  * eOp1_sq        -- eOp 1 * eOp 1 = (1/2) • I  (the parity engine, a 2x2 computation).
  * eP_append_11   -- appending "11" halves the word probability: eP (w ++ [1,1]) = (1/2) * eP w
                      (from eOp1_sq + operator-product / smul associativity).
  * Dgap_rec       -- the cross-multiplied order-k conditional gap D_k = P(0·1^k·1)P(1·1^k) - P(1·1^k·1)P(0·1^k)
                      satisfies D_{k+2} = (1/4) D_k (both pasts gain "11" -> each P halves -> D scales by 1/4).
  * Dgap0/Dgap1    -- base cases evaluated in-kernel: D_0 = -1/18, D_1 = 1/36 (both nonzero).
  * even_infinite_order -- ∀ k, D_k ≠ 0, via two_step_recurrence_nonzero (T8-b, q=1/4). The even process is
                      not order-k Markov for ANY k: INFINITE Markov order, from the operators.

Honest scope: this closes the INFINITE-ORDER identification in-kernel (was the T8-b audit link). With the
earlier rank identification (docs/results/beyond-markov-process-lean-*), the even process's rank=2 AND its
infinite order are BOTH now fully kernel-derived from its 2-dim OOM. The T8-c positive-realization
identification remains the last audit-linked follow-on. Amplification, not discovery; no trust surface touched.

Run:  python scripts/beyond_markov_infinite_order_lean.py   (needs the Lean REPL image; audit runs everywhere)
"""
from __future__ import annotations

import importlib.util
import json
import sys
from fractions import Fraction as Fr
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
OUT = _ROOT / "docs" / "results" / "beyond_markov_infinite_order_lean.json"
IMPORTS = ("Mathlib.LinearAlgebra.Matrix.Rank", "Mathlib.Tactic")

LEAN_SRC = r'''theorem two_step_recurrence_nonzero {α : Type*} [MulZeroClass α] [NoZeroDivisors α]
    (D : Nat -> α) (q : α) (hq : q ≠ 0) (h0 : D 0 ≠ 0) (h1 : D 1 ≠ 0)
    (hrec : ∀ k, D (k + 2) = q * D k) : ∀ k, D k ≠ 0 := by
  have key : ∀ k, D k ≠ 0 ∧ D (k + 1) ≠ 0 := by
    intro k
    induction k with
    | zero => exact ⟨h0, h1⟩
    | succ n ih =>
        refine ⟨ih.2, ?_⟩
        show D (n + 2) ≠ 0
        rw [hrec n]
        exact mul_ne_zero hq ih.1
  exact fun k => (key k).1

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

/-- The even process ε-machine as a 2-dim OOM (defined in Lean, not asserted from Python). -/
def eInit : Fin 2 -> Rat := ![2/3, 1/3]
def eOp : Fin 2 -> Matrix (Fin 2) (Fin 2) Rat := ![!![1/2,0;0,0], !![0,1/2;1,0]]
def eFin : Fin 2 -> Rat := ![1, 1]
noncomputable def eP (w : List (Fin 2)) : Rat := Pval eInit eOp eFin w

/-- The parity engine: `T1² = ½·I`. -/
lemma eOp1_sq : eOp 1 * eOp 1 = (1/2 : Rat) • (1 : Matrix (Fin 2) (Fin 2) Rat) := by
  ext i j
  fin_cases i <;> fin_cases j <;>
    simp [eOp, Matrix.mul_apply, Fin.sum_univ_two, Matrix.cons_val_zero, Matrix.cons_val_one,
          Matrix.head_cons, Matrix.one_apply, Matrix.smul_apply] <;> norm_num

/-- Appending "11" halves the word probability. -/
lemma eP_append_11 (w : List (Fin 2)) : eP (w ++ [1, 1]) = (1/2 : Rat) * eP w := by
  have h11 : Tprod eOp ([1, 1] : List (Fin 2)) = (1/2 : Rat) • (1 : Matrix (Fin 2) (Fin 2) Rat) := by
    simp only [Tprod, Matrix.mul_one]; exact eOp1_sq
  rw [eP, eP, Pval, Pval, Tprod_append, h11, Matrix.mul_smul, Matrix.mul_one]
  simp only [Matrix.mulVec, dotProduct, Fin.sum_univ_two, Matrix.smul_apply, smul_eq_mul]
  ring

def w1 (k : Nat) : List (Fin 2) := 0 :: List.replicate k 1
def w2 (k : Nat) : List (Fin 2) := 1 :: List.replicate k 1
/-- Cross-multiplied order-k conditional gap on pasts `0·1^k` vs `1·1^k` (sharing the length-k suffix). -/
noncomputable def Dgap (k : Nat) : Rat := eP (w1 k ++ [1]) * eP (w2 k) - eP (w2 k ++ [1]) * eP (w1 k)

lemma w1_add2 (k : Nat) : w1 (k + 2) = w1 k ++ [1, 1] := by simp [w1, List.replicate_add]
lemma w2_add2 (k : Nat) : w2 (k + 2) = w2 k ++ [1, 1] := by simp [w2, List.replicate_add]
lemma w1_add2_snoc (k : Nat) : w1 (k + 2) ++ [1] = (w1 k ++ [1]) ++ [1, 1] := by
  simp [w1, List.replicate_add, List.append_assoc]
lemma w2_add2_snoc (k : Nat) : w2 (k + 2) ++ [1] = (w2 k ++ [1]) ++ [1, 1] := by
  simp [w2, List.replicate_add, List.append_assoc]

/-- The gap satisfies a two-step geometric recurrence: `D_{k+2} = ¼ D_k` (each past gains "11", each P halves). -/
lemma Dgap_rec (k : Nat) : Dgap (k + 2) = (1/4 : Rat) * Dgap k := by
  have e1 : eP (w1 (k+2) ++ [1]) = (1/2 : Rat) * eP (w1 k ++ [1]) := by
    rw [w1_add2_snoc]; exact eP_append_11 _
  have e2 : eP (w2 (k+2)) = (1/2 : Rat) * eP (w2 k) := by rw [w2_add2]; exact eP_append_11 _
  have e3 : eP (w2 (k+2) ++ [1]) = (1/2 : Rat) * eP (w2 k ++ [1]) := by
    rw [w2_add2_snoc]; exact eP_append_11 _
  have e4 : eP (w1 (k+2)) = (1/2 : Rat) * eP (w1 k) := by rw [w1_add2]; exact eP_append_11 _
  simp only [Dgap, e1, e2, e3, e4]; ring

lemma Dgap0 : Dgap 0 = -1/18 := by
  simp only [Dgap, w1, w2, List.replicate_zero, List.nil_append]
  norm_num [eP, Pval, Tprod, eInit, eOp, eFin, Matrix.mulVec, dotProduct, Matrix.mul_apply,
            Fin.sum_univ_two, Matrix.cons_val_zero, Matrix.cons_val_one, Matrix.head_cons]

lemma Dgap1 : Dgap 1 = 1/36 := by
  simp only [Dgap, w1, w2, List.replicate_one]
  norm_num [eP, Pval, Tprod, eInit, eOp, eFin, Matrix.mulVec, dotProduct, Matrix.mul_apply,
            Fin.sum_univ_two, Matrix.cons_val_zero, Matrix.cons_val_one, Matrix.head_cons]

/-- **The even process has INFINITE Markov order** — derived from its OOM operator definition, in-kernel.
For every k the cross-multiplied order-k conditional gap is nonzero, so no finite Markov order captures it. -/
theorem even_infinite_order : ∀ k, Dgap k ≠ 0 :=
  two_step_recurrence_nonzero Dgap (1/4) (by norm_num) (by rw [Dgap0]; norm_num) (by rw [Dgap1]; norm_num)
    Dgap_rec
'''


def controls(src):
    """Each mutation must make a theorem FAIL."""
    wrong_base = src.replace("lemma Dgap0 : Dgap 0 = -1/18", "lemma Dgap0 : Dgap 0 = -1/17")
    wrong_q = src.replace("two_step_recurrence_nonzero Dgap (1/4)", "two_step_recurrence_nonzero Dgap (1/3)")
    assert wrong_base != src and wrong_q != src
    return {"wrong_base_case": wrong_base, "wrong_recurrence_ratio": wrong_q}


def audit() -> dict:
    """Cross-check (Python): the even process's actual cross-multiplied gap matches the Lean values/recurrence."""
    sys.path.insert(0, str(_ROOT))
    sys.path.insert(0, str(_ROOT / "scripts"))
    spec = importlib.util.spec_from_file_location("beyond_markov_cert", _ROOT / "scripts" / "beyond_markov_cert.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    ev = m.even_process()

    def D(k):
        h1, h2 = (0,) + (1,) * k, (1,) + (1,) * k
        return m.prob(ev, h1 + (1,)) * m.prob(ev, h2) - m.prob(ev, h2 + (1,)) * m.prob(ev, h1)

    d0, d1 = D(0), D(1)
    rec = all(D(k + 2) == Fr(1, 4) * D(k) for k in range(10))
    nonzero = all(D(k) != 0 for k in range(20))
    return {"D0": str(d0), "D1": str(d1), "D0_is": d0 == Fr(-1, 18), "D1_is": d1 == Fr(1, 36),
            "recurrence_quarter": rec, "nonzero_0_to_19": nonzero,
            "ok": d0 == Fr(-1, 18) and d1 == Fr(1, 36) and rec and nonzero}


def main() -> int:
    aud = audit()
    print(f"audit: D0={aud['D0']} (==-1/18: {aud['D0_is']})  D1={aud['D1']} (==1/36: {aud['D1_is']})  "
          f"D(k+2)=1/4 D(k): {aud['recurrence_quarter']}  nonzero: {aud['nonzero_0_to_19']}")

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
           "reading": ("Full in-Lean INFINITE-ORDER identification: the even process defined from its OOM "
                       "operators is proven to have infinite Markov order in-kernel (forall k, the cross-"
                       "multiplied order-k conditional gap D_k != 0; D_{k+2}=1/4 D_k from T1^2=1/2 I, base cases "
                       "evaluated, closed by the T8-b recurrence bridge). GREEN = all theorems elaborate 0 "
                       "errors/0 sorries, both controls fail, and the Python cross-check confirms D_0=-1/18, "
                       "D_1=1/36, D_{k+2}=1/4 D_k, all nonzero. Lifts T8-b from audit to Q.E.D. With the rank "
                       "identification, the even process's rank=2 AND infinite order are both kernel-derived. "
                       "Amplification, not discovery. No trust surface touched.")}
    OUT.write_text(json.dumps(res, indent=2, default=str) + "\n")
    print(f"\ngate={gate}  kernel={kernel.get('status')} sound={kernel.get('sound')}\n-> {OUT}")
    return 0 if gate != "RED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
