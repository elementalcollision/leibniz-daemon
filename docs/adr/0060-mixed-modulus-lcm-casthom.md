# ADR 0060 — Mixed-modulus modular claims via the LCM/castHom reduction

**Status:** **BUILT — behind its own code-level review before the `mixed_modular/kernel` producer is
activated.** Closes the last frontier ADR 0059 deferred: **nonlinear MIXED-modulus** claims (boolean
combinations of modular atoms whose moduli differ) — e.g. `((a+b)²%4=1) ↔ ((a+b)%2=1)`,
`(a²+b²)%4=2 ↔ (a%2=1 ∧ b%2=1)`. The **trust boundary is untouched**: the Lean kernel decides every proof
and certifies every faithfulness pair; `TrustPolicy.validate_path` and `tests/test_invariants.py` stay
byte-identical; the procedure is exact-or-DEFER and fail-closed behind the same `LEIBNIZ_LEAN_DECIDED`
activation. One operator-owned line admits `mixed_modular/kernel` to `FAITHFULNESS_PRODUCERS`.

## Context — the single-modulus decide has no single modulus

`lean_decided` (ADR 0056) and `boolean_decided` (ADR 0059) decide a claim over `ZMod m` for **one**
modulus `m`, bridging each atom `poly % m ⋈ c` to `(↑poly : ZMod m) ⋈ c`. A mixed-modulus claim — the
conjecturer's parity/CRT-shaped biconditionals — has atoms with **different** moduli, so there is no
single `ZMod m` over which to `decide`. ADR 0059 flagged this as "feasible via an LCM reduction, but
needs more proof automation." A kernel-prototyping pass established the reduction is now robust.

## Decision — decide over `ZMod(lcm)`, bridge each atom's modulus with a ring homomorphism

`M = lcm(mⱼ)`. Every modulus `mⱼ` divides `M`, and `ZMod.castHom (mⱼ ∣ M) (ZMod mⱼ) : ZMod M →+* ZMod mⱼ`
is the canonical reduction ring homomorphism. The kernel decides the whole boolean formula over the
**finite** `ZMod M`, with each sub-`M` atom expressed via its castHom; a per-atom `intCast` bridge lifts
back to ℤ. The proof (gate-owned, kernel-validated against Lean 4.31):

1. `have key : ∀ (vars : ZMod M), Q_M := by decide` — `Q_M` is the boolean structure with each atom
   `poly % mⱼ ⋈ cⱼ` rendered as `castHom(mⱼ∣M) (poly(vars)) ⋈ cⱼ` (or `poly(vars) ⋈ cⱼ` when `mⱼ = M`).
2. Per DISTINCT `(poly, mⱼ, cⱼ)`: `have hᵢ : (Int.emod poly mⱼ = cⱼ) ↔ ((↑poly : ZMod mⱼ) = ↑cⱼ)`, proved
   `rw [ZMod.intCast_eq_intCast_iff']; show ((poly) % mⱼ = cⱼ) ↔ ((poly) % mⱼ = cⱼ % mⱼ); omega`.
3. `rw` the bridges, `push_cast`, then `have hk := key ↑vars` and
   `simp only [map_add, map_mul, map_pow, map_intCast, …] at hk` — the ring-hom lemmas **distribute** the
   castHoms into direct casts, so `hk` matches the goal — `exact hk`.

A **false** formula makes the `ZMod M` `decide` refuse ⇒ the kernel rejects ⇒ DEFER. The kernel, not the
template, decides — exactly as for the single-modulus procedures.

### Fragment (owned at the classifier — the renderer is more permissive)

- **≥ 2 distinct moduli** — a single-modulus claim is `boolean_decided`'s fragment, so the two backends
  are **disjoint by construction** (not merely by cost order).
- every atom `poly % mⱼ == cⱼ` / `!= cⱼ` (`poly` a pure polynomial, `0 ≤ cⱼ < mⱼ`, reusing
  `lean_decided._atom`); `and`/`or`/`not`/`↔` structure only; the non-triviality guard (`_content_free`,
  reused from `boolean_decided`) rejects propositional tautologies.
- `MIN_VARS ≤ nvars ≤ MAX_VARS`, `M ≤ MAX_LCM`, `M ** nvars ≤ MAX_RESIDUE_CELLS`, `≤ MAX_ATOMS` atoms.

## Realization

- `leibniz/gates/mixed_modulus_decided.py` — the faithfulness backend (`classify_mixed`,
  `_zmod_prop_mixed`, `mixed_proof`, `decide_certificate`, backend, `make_rechecker`,
  `prop_statement_template`, `register`). Reuses `boolean_decided._walk_bool` / `_content_free` and the
  `lean_decided` helpers. Producer `mixed_modular/kernel` (PASS) / `mixed_modular/defer` (DEFER).
- `leibniz/providers/mixed_modulus_prover.py` — `MixedModulusDemonstrate` fast-path + `mixed_law`
  generator, mirroring the residue/minmax/boolean fast-paths (re-renders the LAW from the DSL, gates on
  the `mixed_modular/kernel` edge, promote-on-one, axiom-closed).
- `leibniz/assembly.py` — `maybe_register_mixed_modulus` + `maybe_wrap_mixed_modulus` (opt-in, symmetric
  activation), composing with the three existing fast-paths (each owns its disjoint fragment).

## Consequences

- The ceiling-raiser now covers the mixed-modulus parity/CRT biconditionals the conjecturer produces —
  the last of the compound shapes ADR 0059 enumerated. The **fifth** decision procedure enters the trust
  model under the same "decision kernel-gated" distinction, admitted by the operator after this review.
- Kernel-confirmed: `(a+b)²%4=1 ↔ (a+b)%2=1` and `(a²+b²)%4=2 ↔ (a%2=1 ∧ b%2=1)` promulgate end-to-end
  (Q.E.D., is_promotable); a false biconditional DEFERs; a single-modulus claim declines to
  `boolean_decided`; an over-`MAX_LCM` claim DEFERs.
- **Still out of scope:** 1-variable mixed-modulus claims (held below `MIN_VARS=2`, consistent with the
  other backends); moduli whose LCM exceeds `MAX_LCM`; the `∃`-witness legs remain the domain non-vacuity
  gate, unchanged.
