# ADR 0061 — Coefficient-degenerate non-triviality guard for the modular fragment

**Status:** **BUILT.** A Phase-3 (pre-activation) validation of the novelty / non-triviality layer found
that `is_trivial`'s stock tactic ladder is effectively **inert on the modular fragment**, so a class of
*vacuous* modular claims would promulgate as "novel." This ADR adds a mechanical, kill-only
non-triviality check that closes that gap. The **trust boundary is untouched**: the guard only ever
*quarantines* (never promotes), it is a decision procedure not a judge (invariant #4), and
`TrustPolicy.validate_path` / `tests/test_invariants.py` stay byte-identical.

## Context — `is_trivial` cannot see through the modular fragment

The novelty gate's non-triviality part is `LeanVerifier.is_trivial`: it tries a fixed tactic ladder
(`decide, simp, omega, trivial, aesop, ring, nlinarith`) on the bare `∀ vars : ℤ, … → property`
statement; anything a tactic closes on its own is vacuous → quarantine `TRIVIAL`. Phase 3 measured this
ladder against the ceiling-raiser fragments (real Lean 4.31 kernel):

- **min/max:** the ladder is discriminating — it closes commutativity, `max+min=a+b`, `max·min=a·b`
  (aesop/ring/omega) and lets the harder identities through. Working as intended.
- **content-free `P == P`:** rejected earlier, at classification (the content-free guard).
- **modular (`lean_decided` / `boolean` / `mixed`):** the ladder closes **essentially nothing** — not
  even the linear-degenerate `(4a+2b) % 2 == 0`. `decide` can't enumerate unbounded ℤ; `omega`/`nlinarith`
  abstract a nonlinear term like `a*b` into an opaque variable and lose its divisibility. So a *vacuous*
  claim such as `(2*a*b) % 2 == 0` (true for every `a,b` because the coefficient `2` vanishes mod `2`)
  survives every defense — routes in, `is_trivial = False`, not KNOWN — and would promulgate as novel.

This is not a soundness bug (the claim is a true theorem; the kernel proved it), but a **yield-quality**
gap: the modular structure that makes such a claim provable lives in the ceiling-raiser's `ZMod`
reduction, which the stock ladder does not have — so the ladder cannot tell `2ab ≡ 0 (mod 2)`
(degenerate) from `a²+b² ≢ 3 (mod 4)` (genuine).

## Decision — quarantine claims whose every atom reduces to a constant mod m

Add `structural.is_coefficient_degenerate(claim_property)`: a claim is **coefficient-degenerate** iff it
is built entirely from congruence atoms (`P % m ⋈ c`, `P₁ % m == P₂ % m`, `P % m (not) in {…}`, and
∧/∨/¬/↔ combinations of these) and **every** atom's polynomial reduces to a *constant* modulo its
modulus — i.e. in the expansion of `P` (minus the residue), every non-constant monomial has coefficient
`≡ 0 (mod m)`. Then `P ≡ (its constant term) (mod m)` identically, so the atom's residue — and hence the
whole boolean combination's truth — is **variable-independent**: the claim carries no mathematical
content.

The check reuses ADR 0032's exact `(ℤ/mℤ)[vars]` polynomial machinery (`_expand`, coefficient reduction
mod m). It **decides on FORM, never truth** — the same posture that makes `congruence_signature` unable
to false-KNOWN. Consequences:

- It flags `(2*a*b) % 2 == 0`, `(3*a*b) % 3 == 0`, `(2*a*b + 1) % 2 == 1`, `(4*a + 2*b) % 2 == 0`,
  `(2*a) % 2 == (2*b) % 2`, and all-degenerate ∧/∨/¬/↔ combinations of these.
- It flags **nothing genuine**: `a²+b² % 4 != 3` (coeffs `1,1 ≢ 0 mod 4`) and the parity fact
  `a²+a % 2 == 0` (coeff `1`) have a non-constant residue → not flagged. A conjunction mixing one
  degenerate atom with one genuine atom is **not** all-degenerate → not flagged (it still asserts the
  genuine part). `P == P` is left to the content-free guard.
- Non-modular or unrecognized shapes (a `min`/`max` atom, division, `< / >`, no congruence atom at all)
  → cannot conclude → returns `False` (fail toward keeping content). Total-or-`False`; never raises.

### Placement — the cheapest non-triviality check, in the gate, both stages

Wire it into `NoveltyGate` as the **first** non-triviality check, ahead of the Lean `is_trivial` call:
it is pure stdlib (no Docker) and strictly cheaper. On a match it quarantines `FinishReason.TRIVIAL` and
returns a **FAIL** `NOVELTY_EDGE` (`TrustTier.MECHANICAL`, producer `structural.coefficient_degenerate`),
so `TrustPolicy.validate_path` refuses promulgation (a required edge is not PASS). It is added to **both**
`check` (FORMALIZE) and `revalidate` (the ADR 0059 post-fast-path re-check), so a canonical law that a
fast-path rewrites into a degenerate form is caught too — the same belt-and-suspenders as the other
novelty parts.

## Consequences

- **Soundness:** unchanged. The guard is kill-only; it can only demote a candidate to quarantine, which
  is reversible and never affects the proof/faithfulness trust edges. Even a hypothetical over-flag would
  cost only yield, never correctness — and by construction it flags only variable-independent claims.
- **No judge:** the guard is a decision procedure over the claim's algebraic form (invariant #4). No LLM,
  no Z3, no truth evaluation.
- **Scope:** it targets the modular fragment specifically. min/max non-triviality already works via the
  tactic ladder and is left as-is.
- **Fail-closed composition:** the guard runs for every candidate, but it only *matters* for the modular
  fragments the ceiling-raiser handles — and those stay behind the unchanged `LEIBNIZ_LEAN_DECIDED`
  activation default. Phase 3's `scripts/verify_novelty_nontriviality.py` is the regression: every
  vacuous/textbook claim is now quarantined by classification-reject, `is_trivial`, **or**
  `coefficient_degenerate`; genuine in-reach claims still survive.
