"""Terwilliger F2a — weak duality in Lean/Mathlib (task #101, ticket 3; scope doc section F2a).

Machine-checked analogue of weak_duality_holds (scripts/terwilliger_dual.py): over the ABSTRACT primal
(x : Key -> R; two Gram-certified dual block families; the three (20)(ii) multiplier families; the (20)(i)
equality), any dual satisfying stationarity (Lagrangian collapses to Sigma(gamma) - nu) bounds the
objective of every primal-feasible point. No codes are mentioned (that bridge is F2b). Two theorems:

  gram_pairing_nonneg  -- trace(Z*M) >= 0 for M PSD and Z Gram-certified (s*Z = L^T diag(d) L, d>=0, s>0):
                          EXACTLY the witness shape the F1 LDLT certificates emit; sqrt-free proof (this
                          Mathlib pin has no PosSemidef.sqrt), via trace algebra + the PSD quadratic form.
  tw_weak_duality      -- the scope-doc sketch, proved from it.

Checked through the ADR-0011 Mathlib REPL backend with TARGETED imports — the umbrella `import Mathlib`
silently yields a broken env in the repl image (separate bug, flagged). Controls: an alpha-sign flip in
stationarity (the corruption_detected_wd fault) and a weakened s>=0 Gram hypothesis must both FAIL.
"""
from __future__ import annotations

import json
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
OUT = _ROOT / "docs" / "results" / "terwilliger_f2a.json"
IMPORTS = ("Mathlib.LinearAlgebra.Matrix.PosDef", "Mathlib.Tactic")

LEAN_SRC = r'''open Matrix Finset in
/-- The Frobenius pairing of a Gram-certified PSD dual block `Z` (the exact form the F1 LDLT
certificates witness: `s • Z = Lᵀ * diagonal d * L`, `d ≥ 0`, `0 < s`) with a PSD matrix `M`
is nonnegative. Sqrt-free: uses only trace algebra + the PSD quadratic form. -/
lemma gram_pairing_nonneg {n m : ℕ} (Z M : Matrix (Fin n) (Fin n) ℝ)
    (L : Matrix (Fin m) (Fin n) ℝ) (d : Fin m → ℝ) (s : ℝ)
    (hs : 0 < s) (hd : ∀ i, 0 ≤ d i)
    (hZ : s • Z = Lᵀ * Matrix.diagonal d * L)
    (hM : M.PosSemidef) : 0 ≤ (Z * M).trace := by
  have hquad : ∀ i, 0 ≤ (L * M * Lᵀ) i i := by
    intro i
    have h := hM.dotProduct_mulVec_nonneg (fun j => L i j)
    have e : (L * M * Lᵀ) i i = star (fun j => L i j) ⬝ᵥ (M *ᵥ fun j => L i j) := by
      simp [Matrix.mul_apply, Matrix.mulVec, dotProduct, Matrix.transpose_apply,
            Finset.mul_sum, mul_comm, mul_left_comm]
      refine Finset.sum_congr rfl fun y _ => Finset.sum_congr rfl fun x _ => ?_
      rw [show M x y = M y x by simpa using hM.1.apply y x]
    rw [e]; exact h
  have hkey : ((s • Z) * M).trace = ∑ i, d i * ((L * M * Lᵀ) i i) := by
    rw [hZ, Matrix.mul_assoc, Matrix.trace_mul_comm, ← Matrix.mul_assoc]
    simp [Matrix.trace, Matrix.diag, Matrix.mul_diagonal, mul_comm]
  have hs' : 0 ≤ s * (Z * M).trace := by
    have e2 : s * (Z * M).trace = ((s • Z) * M).trace := by
      simp [Matrix.trace_smul]
    rw [e2, hkey]
    exact Finset.sum_nonneg fun i _ => mul_nonneg (hd i) (hquad i)
  nlinarith [hs']

open Matrix Finset in
/-- **F2a — weak duality for the Terwilliger three-point SDP, over the abstract primal.**
Variables `x : Key → ℝ`; two Gram-certified dual block families `Z, W` paired against block maps
`Mmap, M'map` (the eq.(7) β-structure is abstracted — its faithfulness is F1's kernel data / F2b);
multipliers `α, β1, γ ≥ 0` on the three (20)(ii) families and `ν` on (20)(i). If the Lagrangian
collapses to the constant `Σγ − ν` (stationarity) then every primal-feasible `x` obeys
`obj x ≤ Σγ − ν`. No codes are mentioned: this is the machine-checked analogue of
`weak_duality_holds` in scripts/terwilliger_dual.py. -/
theorem tw_weak_duality
    {Key T : Type} [Fintype Key] [Fintype T]
    {nb : ℕ} (bs : Fin nb → ℕ)
    (c : Key → ℝ)
    (Mmap M'map : (k : Fin nb) → (Key → ℝ) → Matrix (Fin (bs k)) (Fin (bs k)) ℝ)
    (Z W : (k : Fin nb) → Matrix (Fin (bs k)) (Fin (bs k)) ℝ)
    (xval x0i x0j : T → (Key → ℝ) → ℝ) (x000 : (Key → ℝ) → ℝ)
    (α β1 γ : T → ℝ) (ν : ℝ)
    {mz mw : Fin nb → ℕ}
    (LZ : (k : Fin nb) → Matrix (Fin (mz k)) (Fin (bs k)) ℝ)
    (LW : (k : Fin nb) → Matrix (Fin (mw k)) (Fin (bs k)) ℝ)
    (dZ : (k : Fin nb) → Fin (mz k) → ℝ) (dW : (k : Fin nb) → Fin (mw k) → ℝ)
    (sZ sW : Fin nb → ℝ)
    (hsZ : ∀ k, 0 < sZ k) (hsW : ∀ k, 0 < sW k)
    (hdZ : ∀ k i, 0 ≤ dZ k i) (hdW : ∀ k i, 0 ≤ dW k i)
    (hgZ : ∀ k, sZ k • Z k = (LZ k)ᵀ * Matrix.diagonal (dZ k) * (LZ k))
    (hgW : ∀ k, sW k • W k = (LW k)ᵀ * Matrix.diagonal (dW k) * (LW k))
    (hα : ∀ t, 0 ≤ α t) (hβ1 : ∀ t, 0 ≤ β1 t) (hγ : ∀ t, 0 ≤ γ t)
    (hstat : ∀ x, (∑ key, c key * x key)
        + (∑ k, ((Z k) * (Mmap k x)).trace) + (∑ k, ((W k) * (M'map k x)).trace)
        + (∑ t, α t * xval t x) + (∑ t, β1 t * (x0i t x - xval t x))
        + (∑ t, γ t * (1 + xval t x - x0i t x - x0j t x)) + ν * (x000 x - 1)
        = (∑ t, γ t) - ν) :
    ∀ x, (∀ k, (Mmap k x).PosSemidef) → (∀ k, (M'map k x).PosSemidef) →
      (∀ t, 0 ≤ xval t x) → (∀ t, xval t x ≤ x0i t x) →
      (∀ t, x0i t x + x0j t x ≤ 1 + xval t x) → x000 x = 1 →
      (∑ key, c key * x key) ≤ (∑ t, γ t) - ν := by
  intro x hM hM' hxa hxb hxg hx0
  have h := hstat x
  have tZ : 0 ≤ ∑ k, ((Z k) * (Mmap k x)).trace :=
    Finset.sum_nonneg fun k _ =>
      gram_pairing_nonneg (Z k) (Mmap k x) (LZ k) (dZ k) (sZ k) (hsZ k) (hdZ k) (hgZ k) (hM k)
  have tW : 0 ≤ ∑ k, ((W k) * (M'map k x)).trace :=
    Finset.sum_nonneg fun k _ =>
      gram_pairing_nonneg (W k) (M'map k x) (LW k) (dW k) (sW k) (hsW k) (hdW k) (hgW k) (hM' k)
  have tA : 0 ≤ ∑ t, α t * xval t x :=
    Finset.sum_nonneg fun t _ => mul_nonneg (hα t) (hxa t)
  have tB : 0 ≤ ∑ t, β1 t * (x0i t x - xval t x) :=
    Finset.sum_nonneg fun t _ => mul_nonneg (hβ1 t) (by linarith [hxb t])
  have tG : 0 ≤ ∑ t, γ t * (1 + xval t x - x0i t x - x0j t x) :=
    Finset.sum_nonneg fun t _ => mul_nonneg (hγ t) (by linarith [hxg t])
  have tN : ν * (x000 x - 1) = 0 := by rw [hx0]; ring
  linarith [h, tZ, tW, tA, tB, tG, tN]
'''


def controls(src):
    """Each mutation must make the proof FAIL (kernel error) — teeth for the sign/positivity structure."""
    flip_alpha = src.replace("+ (\u2211 t, \u03b1 t * xval t x) + (\u2211 t, \u03b21 t",
                             "- (\u2211 t, \u03b1 t * xval t x) + (\u2211 t, \u03b21 t")
    weaken_s = src.replace("(hs : 0 < s)", "(hs : 0 <= s)").replace("(hs : 0 \u2264 s)", "(hs : 0 <= s)")
    assert flip_alpha != src and weaken_s != src
    return {"alpha_sign_flip": flip_alpha, "gram_scale_weakened": weaken_s}


def main() -> int:
    from leibniz.backends.lean_repl import LeanReplBackend
    bk = LeanReplBackend(timeout_s=900)

    def check(src):
        r = bk._run(src, IMPORTS)
        if r is None:
            return None, ["no response"]
        msgs = r.get("messages", []) or []
        errs = [m for m in msgs if m.get("severity") == "error"]
        sorries = [m for m in msgs if "sorry" in (m.get("data") or "")]
        return (not errs and not sorries), [(m.get("data") or "")[:120] for m in errs[:3]]

    ok, err = check(LEAN_SRC)
    rows = {"theorems": {"ok": ok, "errors": err}}
    ctl = {}
    for name, src in controls(LEAN_SRC).items():
        cok, cerr = check(src)
        ctl[name] = {"ok": cok, "first_error": cerr[:1]}
    rows["controls"] = ctl
    controls_fail = all(v["ok"] is False for v in ctl.values())
    verdict = "GREEN" if ok is True and controls_fail else "AMBER"
    res = {"verdict": verdict, "imports": list(IMPORTS), "rows": rows,
           "reading": ("F2a weak duality, kernel-checked via the Mathlib REPL backend. GREEN = both theorems "
                       "(gram_pairing_nonneg, tw_weak_duality) elaborate with zero errors/sorries AND both "
                       "corrupted controls (alpha-sign flip in stationarity; Gram scale weakened to s>=0) "
                       "FAIL. Scope: the abstract primal only — stationarity is the function-level hypothesis "
                       "(F1 kernel-checks its coefficient form per certificate); the codes=>feasible bridge "
                       "is F2b. No trust surface touched.")}
    OUT.write_text(json.dumps(res, indent=2) + "\n")
    print(f"terwilliger F2a: {verdict} (theorems ok={ok}; controls fail={controls_fail})")
    print(f"  -> {OUT}")
    return 0 if verdict == "GREEN" else 1


if __name__ == "__main__":
    raise SystemExit(main())
