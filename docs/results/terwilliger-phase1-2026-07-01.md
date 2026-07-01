<!--
Phase 1 of the SDP three-point build: mechanical dual derivation + checker. Free-CPU; no trust touch;
tests/test_invariants.py byte-identical. Audit-tier (DUAL_CERTIFICATE_CHECKED). Validated by three machine
checks (each with a corrupt-control) + an adversarial faithfulness panel.
-->

# Terwilliger three-point — Phase 1: mechanical dual + checker (2026-07-01)

Phase 1 delivers the **mechanically-derived dual** and the **checker** for the Schrijver three-point SDP,
per the review synthesis (D3: recompute a *system*, not "one scalar identity"; D5: no hand-derived signs).
Free-CPU, exact rational. `scripts/terwilliger_dual.py`, guarded by `tests/test_terwilliger_dual.py`.

## What was built
The primal (Schrijver 2005, unrestricted `A(n,d)`, eq. 19/20/22) with variables `x^t_{i,j}` reduced by
(20)(iii) orbit merge (a variable = the sorted multiset `{i, j, i+j−2t}` of the triple's three pairwise
distances), (20)(iv) distance-zeroing, and the even-d weight reduction. The dual is assembled as a Lagrangian
with PSD `Z_k, Z'_k` (one per block family), nonneg `α, β1, γ` (the three (20)(ii) inequality families), and
free `ν` (the (i) normalization). Weak duality: `A(n,d) ≤ Σγ − ν` once the per-variable **stationarity system**
holds (homogeneous PSD ⇒ the linear duals set the bound, consistent with the panel's Q-dual-3).

`dual_check(n,d,duals)` is the checker: it **recomputes** every stationarity residual and the bound from
`(duals, β)` — never trusting a producer-supplied slack — and checks `Z_k, Z'_k ⪰ 0` (exact rational LDLᵀ) and
`α,β1,γ ≥ 0`. Feasible ⟺ all residuals 0 ∧ PSD ∧ nonneg.

## Validation (free-CPU, each with a corrupt-control proving teeth)
Across cells A(4,2), A(5,2), A(6,2), A(6,4), A(7,4) — all **GREEN**:
1. **Lagrangian identity (emitter-consistency).** The collected form `const + Σ coeffᵥ·xᵥ` equals the directly
   evaluated Lagrangian for all pseudo-random exact-rational `(x, duals)`. A one-sign β corruption in the
   collector breaks it. ⇒ no hand-derived sign/index error survives in the emitter.
2. **Weak duality (sign-validity).** For a primal-feasible `x` (a real code's inner distribution) and any
   dual-feasible `duals`, `c·x ≤ L(x,duals)`. A flipped α-sign (targeted adversarial dual) breaks it. ⇒ the
   sign conventions actually yield a valid *upper* bound, not just an internally-consistent formalism.
3. **Delsarte tie (structural).** The k=0 objective variables are exactly the Delsarte inner-distribution
   weights `{0} ∪ {i ≥ d}` (even `i` when `d` even). Block sizes are `p_k = n−2k+1`, largest `(n+1)×(n+1)` —
   the dimension-wall escape.

## Adversarial panel (4 independent lenses)
Primal-fidelity-to-Schrijver, dual-correctness, and code-correctness/edge-cases all returned **SOUND, no
issues**. The soundness-scope lens raised a **CONCERN** whose two "major" items are *scope restatements, not
bugs*: (1) formulation-faithfulness is not machine-checked — the documented audit-tier caveat (Fugu's Trap 3),
addressed later by the bridge theorem; (2) β is "trusted" — but it is validated upstream by Phase 0's real-code
differential test (now noted in-code). Two minor docstring gaps (the checker certifies `A(n,d) ≤ bound` by weak
duality with **no primal witness needed**; the validation codes are feasible-by-construction) were tightened.
No logic changed.

## Scope / trust
Audit-tier **`DUAL_CERTIFICATE_CHECKED`**. Phase 1 validates the dual *structure + checker + sign conventions*;
it does **not** yet find a feasible dual (that is Phase 2: normalized solve → feasibility-at-target → Bareiss
round → kernel). Formulation-faithfulness to Schrijver is de-risked by the machine checks + an adversarial
panel, but is **not** itself machine-proven — the bridge theorem (later rung) is what would make an output
Q.E.D. No trusted surface touched; `tests/test_invariants.py` byte-identical.

## Next — Phase 2
Feed the checker a numerically-solved dual: solve the *normalized* blocks (cvxpy/Clarabel), transform back to
exact rationals, target the known integer (feasibility-at-target, D2a), keep bit-length bounded with Bareiss
(#215), and — for a singular optimal slack — the gated pivoted-LDLᵀ fallback (D2b). First reproduction cell:
**A(19,6) 1289→1280**.
