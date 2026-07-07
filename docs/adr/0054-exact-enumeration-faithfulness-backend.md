# ADR 0054 — An exact-enumeration / periodicity faithfulness backend (unifies Lever A + Lever B)

**Status:** Proposed (2026-07-07) — **blocked on an adversarial soundness review** (do not implement
until it clears). Complements ADR 0002 (faithfulness gate), ADR 0037 (sound-backend seam — the seam
this uses), ADR 0020/0022 (contract encodability / probe), ADR 0051 (the review precedent). Supersedes
the "cheap Lever A" framing in `docs/fleet-review-raising-the-ceiling.md`.

## Context — the empirical correction

Raising the conjecturer's ambition (ADR 0053) flipped it to richer **two-variable / min-max /
composite-modulus** claims. Two live cycles then located the binding constraint, and a third
measurement corrected our diagnosis:

- The richer claims **die at the faithfulness gate** (`reached_proof = 0`; the FORMALIZE exit with no
  disposition), before the prover — so proof-repair / Leanstral cannot help them.
- The fleet-review thesis posited a **cheap "Lever A"**: the two-variable claims are "already
  Z3-decidable and DSL-legal", so just fix the FORMALIZE contract. **This is false.** Measured
  directly: the Z3 backend `encodable`s the two-variable predicates, but `decide_unsat` on
  `[a≥0 ∧ b≥0, (a²+b²) % 4 == 3]` returns **`None` (unknown)** — two-variable nonlinear-modular UNSAT
  is outside Z3's decidable fragment. The coverage probe then DEFERs (no conclusive result), which is
  exactly the observed block. The single-variable analogue *is* decided; that is why the daemon only
  ever promulgated single-variable laws.
- **These claims are, however, decidable by full-period enumeration.** `(a²+b²) % 4` depends only on
  `(a mod 2, b mod 2)`; enumerating the finite residue period is a **total, exact** decision where Z3
  returns unknown (verified for `(a²+b²)%4≠3`, `(a²+ab+b²)%3≠2`, `ab(a²−b²)%6=0`).

**Consequence: Lever A and Lever B are the same lever.** The two-variable modular claims need the
*same* exact-enumeration/periodicity mechanism that Lever B (gcd, bounded Σ/Π, factorial) needs. There
is one increment to build, not two, and it is trust-critical.

## Decision (proposed, pending review)

Add a **`SoundFaithfulnessBackend` (ADR 0037) that decides a modular/computable claim by exact
enumeration** when Z3 declines, with the strict discipline the seam already enforces (exact-or-DEFER,
gate-owned certificate re-check, MECHANICAL, never a judge):

1. **When it applies.** The claim's contract (`claim_domain`, `claim_property`) is fully encodable in
   the DSL and every variable's dependence enters the property only through `vᵢ mod mᵢ` for **fixed**
   moduli (periodic), **or** through a statically-bounded index (bounded Σ/Π, factorial to a fixed
   cap) — i.e. the predicate is a total computable function with a **finite decisive domain**.
2. **What it decides.** It evaluates `claim_domain ∧ ¬claim_property` (the same target the probe/Z3
   use) over the **entire** decisive domain — the full residue period (product/lcm of the `mᵢ`), or
   the full bounded index range — with a closed, total interpreter (no `eval`). **Any point
   satisfying it ⇒ FAIL (a real gaming witness), exact at any size.** **Zero points ⇒ EXACT PASS.**
3. **EXACT-only PASS.** It **never** issues a bounded PASS. If the decisive domain is not fully
   enumerable within a hard resource cap, it **DEFERs** — it can only add exact decisions and sound
   refutations, never a merely-bounded acceptance. (This is stricter than the current Z3 bound=64
   gaming search, which is refutation-only anyway.)
4. **The period is derived by the GATE, not asserted by the backend.** A structural derivation from
   the predicate AST: only `% const` and whitelisted periodic/bounded ops contribute a period; any
   raw variable, `%`/`/` by a variable, unbounded op, or unrecognized construct ⇒ non-periodic ⇒
   DEFER. The backend receives the derived period; a mismatch is a gate-level refusal.
5. **Certificate + re-check.** A PASS emits a `Certificate(kind="exact-enumeration", data=hash(domain,
   predicate, enumerated-range))`; the gate's registered re-checker independently re-runs the
   enumeration. A self-reported PASS with no matching re-check is not a PASS (ADR 0037 unchanged).
6. **DSL expansion rides on the same checker.** `gcd(·,c)` (periodic in the variable, period `c`),
   bounded `Σ/Π`, `n!` to a cap become admissible **because and only because** this backend can decide
   them exactly — added incrementally, each with the periodicity/bound story above, never on Z3.

## Why this is trust-critical (not kill-only)

Unlike the novelty gate (ADR 0052, kill-only), a faithfulness **PASS is load-bearing**: it lets a
claim proceed to proof and promotion. A **false EXACT-PASS** — from a wrong derived period or an
interpreter bug — certifies a *mis-stated* claim, and the kernel then proves the (true) formal
statement, minting a law that does not mean what it says. That is worse than no proof. The trusted
base grows by the interpreter **and** the periodicity-deriver, neither guarded by
`tests/test_invariants.py` today. Per the ADR 0051 precedent this must clear a **≥3-lens adversarial
soundness review before merge**, red-teaming at least:

- **Periodicity spoofing** — a predicate whose true period exceeds the naively-derived one (nested
  `mod`, `gcd(n,c)` interacting with `n^k % m`, lcm of several moduli, a `%` that is not the outer
  operation) ⇒ a false EXACT-PASS on an under-enumerated domain.
- **Evaluator poisoning / divergence** — an attacker-shaped summand or index that diverges or exploits
  an interpreter bug; hard static bounds on indices and a resource cap, timeout ⇒ DEFER never PASS.
- **Vacuity / non-discriminating** — an empty `claim_domain` or an all-of-ℤ/m property that asserts
  nothing ⇒ require ADR 0020/0022 non-vacuity + positive/negative/DEFER controls the checker MUST
  respectively fail / pass / DEFER.
- **Certificate laundering / kind-collision** (ADR 0041) — bind the certificate to the exact statement
  hash so it cannot be replayed for a weaker claim; a COMPUTE result must never wear a DECIDE tag.

## Consequences

- Unblocks the entire richer batch the daemon already conjectures (two-variable modular), and — as a
  strict superset — the Lever-B DSL constructs, from **one** reviewed backend.
- The honest ordering becomes **[this backend, reviewed] → prover (Leanstral, repair)**: only once
  richer claims can be *certified faithful* does prover reach become the limiting factor.
- Not implemented until the review clears; if the review finds an unguarded false-EXACT-PASS path, the
  ADR is amended or rejected, not shipped on optimism.
