# ADR 0070 — Factorial/gcd kernel decision procedure (Phase γ, leg 1)

- Status: accepted
- Date: 2026-07-22
- Depends on: ADR 0066 (factorial/gcd Z3 If-tables), ADR 0065 (the order-split discipline this
  mirrors), ADR 0056–0060 (the decision-procedure lineage), ADR 0041 (operator-admitted producers)

## Context

ADR 0066 gave the Z3 layer exact bounded If-tables for `factorial`/`gcd`, so such claims can be
cheaply refuted and triviality-checked — but they had **no kernel path**: a true factorial/gcd
conjecture could never become a promulgable law without an LLM-drafted proof. Phase γ's charter is
to widen what autonomous cycles can close. This is the sixth kernel decision procedure, and the
first whose fragment covers *named functions*.

## Decision

Two kernel-validated proof templates (prototyped against live Lean 4.31 on 2026-07-22, six
instances: true claims CHECKED, false controls REJECTED — the kernel, not the template, decides):

1. **Factorial, two-regime** — for `factorial(n) % m ⋈ c` claims: a cast `bridge`
   (`push_cast; rfl`), the tail `key : ∀ t, m ≤ t → t! % m = 0` proved by `Nat.dvd_factorial` +
   `omega` (no lemma-name roulette — the first prototype died on a nonexistent
   `Nat.mod_eq_zero_iff_dvd`), then a split: the finite initial segment `t < m` by
   `interval_cases <;> norm_num [Nat.factorial]`, the tail rewritten to 0.
2. **Gcd, period-split** — for `gcd(c, n)` / `gcd(n, c)` claims: gcd is periodic in its variable
   argument with period `c` (`key` via `Nat.gcd_rec` + `Nat.gcd_comm` — the ADR 0065 discipline
   with the multiplicative order swapped for the gcd period), then `interval_cases r <;>
   norm_num [Nat.gcd]` over the `c` arms; a leading `gcd_comm` flips the var-first spelling.

Renderer: `factorial(x)`/`gcd(a, b)` are admitted in `_term` **exactly on smt_z3's ADR 0066 table
fragment** — bare-variable or constant arguments, constants ≤ `MAX_TABLE_BOUND` (the constant is
imported, not duplicated) — rendered through ℕ and cast into the ℤ box
(`((Nat.factorial ((n).toNat) : ℕ) : ℤ)`), vacuous outside the box per the note-1 convention.
Everything else still refuses → DEFER. The conformance suite's stale `gcd(n, 6) == 1` refusal pin
(from the pre-0066 "dropped from scope" era) is replaced by still-refused neighbours (compound
argument, nested call, wrong arity, over-cap constant).

Fragment (classifier-owned): one atom family per claim; `eq`/`neq`/or-of-`==` (residue set);
single free variable (the function's argument); factorial modulus in `[2, MAX_ORDER]`, gcd
constant in `[1, MAX_ORDER]` (the same arm-count cap as ADR 0065); asserted values in range
(`[0, m)` resp. `[0, c]`).

Wiring is the established pattern, unchanged in shape: `gates/factgcd_decided.py`
(SoundFaithfulnessBackend + gate-owned `decide_certificate` + re-checker + template, KIND
`factgcd-faithfulness`, producer `factgcd/kernel`, cost_rank 96), `providers/factgcd_prover.py`
(canonical-law generator + `FactGcdDemonstrate` promote-on-one fast-path, gated on this fragment's
own faithfulness edge), `assembly.maybe_register_factgcd` / `maybe_wrap_factgcd` (opt-in behind
`LEIBNIZ_LEAN_DECIDED` + a real REPL image; fail-closed otherwise), and the operator admission of
`factgcd/kernel` to `FAITHFULNESS_PRODUCERS` (ADR 0041 — the one sanctioned trust.py line).

## Trust argument

No new trust *kinds*: this is the ADR 0058/0065 design with the classifier and templates swapped.
Every certificate is decided by the kernel four times over (coverage, property, two ∃-witnesses),
each with an axiom-closure check; the re-checker re-derives rather than trusts; the fast-path
promotes only on `LeanVerifier.discharge` (the sole `kernel_verified` writer) plus a
promotion-time axiom closure. False claims are not "handled" — they fail an arm and the kernel
rejects. `tests/test_invariants.py` is untouched.

## Consequences

- Autonomous cycles can now close factorial/gcd conjectures as kernel-verified laws with zero LLM
  proof spend — the ADR 0066 proposal surface finally has a matching Q.E.D. path.
- The arm cap (`MAX_ORDER` = 64) bounds kernel cost; larger moduli DEFER honestly.
- Validated: CI suite (renderer lockstep + semantics grid, classification guards, fake-kernel
  certificate paths, tamper refusal, fail-closed) + live-kernel e2e (both fragments certify; both
  false controls DEFER).
