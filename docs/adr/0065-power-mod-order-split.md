# ADR 0065 — Symbolic exponents: the order-split decision procedure for `base^n % m`

**Status:** **BUILT — behind the same fail-closed activation as its siblings.** The roadmap's deferred
DSL increment ("symbolic exponents (`2^n`)"): claims about `base^n % m` with a **variable exponent**
become renderable, kernel-decidable for faithfulness, and provable as promulgable LAWS. The **trust
boundary is untouched**: the Lean kernel decides every proof; `TrustPolicy.validate_path` and
`tests/test_invariants.py` stay byte-identical; the procedure is exact-or-DEFER and fail-closed behind
`LEIBNIZ_LEAN_DECIDED`. One operator-owned line admits `power_mod/kernel` to `FAITHFULNESS_PRODUCERS`.

## Context — Z3 already decides this fragment; the kernel path could not see it

ADR 0035's order-reduction encodes `base^n % m` (constant base, bare-variable exponent, constant
modulus, `gcd(base,m)=1`) EXACTLY over its multiplicative-order period, so the Z3 probes handle these
claims. But the DSL→Lean renderer refused every variable exponent, so the fragment could never reach
the kernel: no statement-binding faithfulness certificate, no canonical LAW, no promote-on-one — such
conjectures could pass faithfulness (via ClaimProbe) yet only be proven by the N+1 ensemble, which
does not know the period trick.

## Decision — decide over the multiplicative-order period, in the kernel

For `gcd(base, m) = 1`, `base^k mod m` is purely periodic with period `ord`. The gate-owned proof
(kernel-validated against Lean 4.31, 8/8 template battery + 8/8 assembled end-to-end):

1. `key : ∀ k : ℕ, base^k % m = base^(k % ord) % m` — `conv_lhs => rw [← Nat.div_add_mod k ord,
   pow_add, pow_mul]; rw [Nat.mul_mod, Nat.pow_mod]; norm_num`. **The kernel checks the period**: a
   wrong `ord` leaves `base^ord % m ≠ 1` and `norm_num` cannot close ⇒ DEFER (validated negative
   control: claiming period 4 for 2 mod 7 is rejected).
2. `bridge : ∀ t : ℕ, Int.emod ((base:ℤ)^t) m = ((base^t % m : ℕ) : ℤ)` — `push_cast; rfl`.
3. `rw [bridge]`, instantiate `key` at `(n).toNat`, `set r := (n).toNat % ord`, `interval_cases r <;>
   norm_num` — `ord` closed arithmetic arms the kernel evaluates.

A false claim fails some arm ⇒ the kernel rejects ⇒ DEFER. (The ℤ-ModEq route was rejected during
prototyping: its `simpa` close fails at reducible transparency — the same defect class as the ADR 0059
eq-conjunct bug — so the template works in ℕ and bridges by explicit ascription.)

### Renderer (lockstep preserved)

`_term` gains ONE admission, intercepted at the `Mod` node: `base^n % m` (constant base,
bare-variable exponent, constant modulus) renders `(Int.emod ((base : ℤ) ^ (n).toNat) m)` — exactly
the shape smt_z3's order-reduction admits, and nowhere else (a bare `2^n`, compound exponent, or
variable base still raises `RenderError`). Faithful under the ℤ-box: `0 ≤ n ⇒ ↑n.toNat = n`. The
conformance suite's stale refusal of `2**n % 5` is replaced by the still-refused neighbouring shapes;
a semantics grid pins the encoding against the DSL's own evaluation.

### Fragment (owned at `classify_power`; mirrors smt_z3's guards)

ONE atom family `base**n % m ⋈ c`: constant base ≥ 2, bare single-variable exponent, constant m ≥ 2,
`gcd(base,m) = 1`, `ord ≤ MAX_ORDER` (the smt_z3 cap, imported), `eq`/`neq` single atom or an
or-disjunction of `==` atoms over the same power (residue_set), residues in `[0, m)`; the claim's
ONLY free variable is the exponent.

### Components (the ADR 0055–0060 sibling pattern, verbatim)

- `leibniz/gates/power_mod_decided.py` — classifier, gate-owned four-leg `decide_certificate`
  (coverage/property/∃-controls + axiom closure), `PowerModFaithfulness` (cost_rank 95, producer
  `power_mod/kernel`), byte-binding statement template, re-deriving re-checker, fail-closed `register`.
- `leibniz/providers/power_mod_prover.py` — `power_law` (canonical ℤ-box LAW + order-split proof) and
  `PowerModDemonstrate` (promote-on-one, gated on a `power_mod/kernel` faithfulness edge — the
  A1/A2/A4 obligations exactly as `ResidueDemonstrate`).
- `assembly.maybe_register_power_mod` / `maybe_wrap_power_mod` — operator opt-in, same
  `LEIBNIZ_LEAN_DECIDED` + REPL gate as the siblings.

### A deliberate 1-variable fragment (invariant 5, argued)

The fragment is inherently single-variable (a bare exponent), unlike the siblings' `MIN_VARS = 2`.
Sound backends run before the probes, so an in-fragment claim pays one kernel decide (≤ `ord ≤ 64`
arms) where Z3 might have sufficed — accepted deliberately: the kernel certificate is what
byte-binds the canonical statement and enables promote-on-one (skipping an N+1 ensemble run, which
dwarfs the decide), and the Z3 probe cannot provide either.

## Consequences

- The encodable region widens by the symbolic-exponent fragment — the stated precondition for any
  origination candidate beyond the polynomial-congruence wall. Honestly: facts in this fragment
  (residue cycles, order facts) are textbook-dense; this raises reach, it does not manufacture novelty.
- Named functions (`factorial`, `gcd`, `Nat.log`) remain the roadmap's next deferred increment.

## Non-goals

No trust-core change; no judge anywhere; no activation by default; no claim that the widened fragment
contains non-textbook mathematics.
