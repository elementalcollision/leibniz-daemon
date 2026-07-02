<!--
Task #101 (handoff ticket ③) — F2a weak duality in Lean/Mathlib, per the scope doc §F2a.
Audit/measurement only; no trust touch; tests/test_invariants.py byte-identical.
-->

# Terwilliger F2a — weak duality is machine-checked (2026-07-02)

## Verdict: **GREEN** — both theorems verify (Mathlib REPL, zero errors/sorries); both corrupted controls fail

Two Lean theorems (`scripts/terwilliger_f2a.py::LEAN_SRC`, checked through the ADR-0011 REPL backend):

1. **`gram_pairing_nonneg`** — `trace(Z·M) ≥ 0` for `M` PSD and `Z` **Gram-certified**
   (`s·Z = Lᵀ·diag(d)·L`, `d ≥ 0`, `s > 0`). This is *exactly* the witness shape the F1 LDLT
   certificates emit, so F2a's dual-feasibility notion matches the kernel-checked artifacts one-to-one.
   The proof is **sqrt-free** (this Mathlib pin has no `PosSemidef.sqrt`/factorization API): trace
   algebra + `PosSemidef.dotProduct_mulVec_nonneg`.
2. **`tw_weak_duality`** — the scope-doc sketch, proved: over the abstract primal (`x : Key → ℝ`, two
   block families, the three (20)(ii) multiplier families α/β1/γ ≥ 0, the (20)(i) equality with free ν),
   any dual whose Lagrangian collapses to the constant `Σγ − ν` (stationarity) bounds every
   primal-feasible point: `obj x ≤ Σγ − ν`. **No codes are mentioned** — the machine-checked analogue of
   `weak_duality_holds`.

Controls (must FAIL, and do): an **α-sign flip** in stationarity (the `corruption_detected_wd` fault) and
the Gram scale weakened to `s ≥ 0` (which would admit the vacuous s=0 certificate the F1 review killed).

## Scope — what is hypothesis vs. proved

- **Proved**: signs/positivity of every Lagrangian term ⇒ weak duality. The one mathematical lemma
  (PSD pairing ≥ 0) is proved from first principles.
- **Hypothesis**: stationarity is the function-level identity `∀x, L(x) = Σγ−ν`; per-certificate, F1
  kernel-checks its coefficient form (`stat_*` theorems). Closing that gap formally (coefficient-form ⇒
  function-level, plus `M_k` = the eq.(7) β-maps) is F2b-adjacent plumbing.
- **Not covered** (by design): codes ⇒ primal-feasible — that is **F2b**, the external-round candidate.

## Found along the way

The REPL backend's umbrella `import Mathlib` silently yields a broken env (even `OfNat` unknown) while
targeted module imports work — `pipeline.py` defaults to the umbrella, so Mathlib-needing checks
fail-closed through this backend. No soundness impact; flagged as a follow-up task.

## The two operator decisions this ticket ends with (scope doc §F2)

1. **F2b external brief** — send the drafted brief (scope doc, "Draft external brief") to a formalization
   round (Aristotle / panel / Mathlib community)? Evidence from tickets ①+D6: F2b is infrastructure, not
   discovery-motivated; the frontier cells are Delsarte-tie bound-blocked. F2b's value is TCB-shrinking
   for the already-banked certificates (A(19,6), A(23,6), A(25,10)).
2. **F2c tier** — gated Q.E.D. wiring (guarded-core edits + hook + witness round) vs. the no-trust-edit
   **Observatory tier** (ADR 0038 precedent). Nothing here forces the choice; F2c stays gated behind
   F2b + an ADR either way.

Artifacts: `docs/results/terwilliger_f2a.json`. Harness: `scripts/terwilliger_f2a.py` (re-run ~2 min,
needs the `leibniz-lean-repl:v4.31.0` image). Test: `tests/test_terwilliger_f2a.py`.
