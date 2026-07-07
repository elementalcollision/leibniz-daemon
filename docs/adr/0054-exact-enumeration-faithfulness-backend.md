# ADR 0054 — An exact-enumeration / periodicity faithfulness backend (unifies Lever A + Lever B)

**Status:** **NEEDS REDESIGN (2026-07-07) — SUPERSEDED-BY [ADR 0055](0055-lean-decided-faithfulness-backend.md)
(2026-07-07).** The adversarial soundness review below returned
`needs-redesign` (high confidence, **not safe to implement**). Do **not** implement the design as
written; the capability is sound in principle but three of the six decision points are unsound as
specified (one is a *regression* in gate soundness). The redesign (the "v2 ADR" this called for) is
**ADR 0055**, which moves the enumeration onto the Lean kernel (per the external fleet review) so a
wrong period or a buggy evaluator DEFERs instead of false-PASSing; it folds in all seven mitigations
below and must clear its **own** review before any code. Complements ADR 0002 (faithfulness
gate), ADR 0037 (sound-backend seam), ADR 0020/0022 (contract encodability / probe), ADR 0051 (the
review precedent — likewise rejected on review). Supersedes the "cheap Lever A" framing in
`docs/fleet-review-raising-the-ceiling.md`.

## Review outcome — NEEDS REDESIGN (do not implement as written)

A four-lens adversarial review (verdict `needs-redesign`, high confidence, `safe_to_implement:false`)
verified three unsound decision points **against the code**, not merely in the abstract:

1. **The decision target is wrong, and dropping `established_domain` is a *regression* (critical).**
   Point 2 enumerates `claim_domain ∧ ¬claim_property` — a claim-**truth** check, not a
   statement↔claim **faithfulness** check. The real probe (`probes.py:61-68`) checks *two* conjuncts
   that both reference `established_domain` (coverage: `claim_domain ∧ ¬established_domain` UNSAT;
   property: `established_domain ∧ claim_domain ∧ ¬claim_property` UNSAT). A strong-contract /
   weak-theorem claim — `established_domain` honestly narrowed to `a==0`, `claim_property` true
   everywhere — enumerates zero points → **false EXACT-PASS** while the kernel proves only the `a==0`
   slice → a permanently mislabelled law (ADR 0002's worst case). Worse: today `coverage_probe`
   makes that same case a **safe DEFER** (`probes.py:62-63`), so ADR 0054 would make the gate
   *strictly less sound* for exactly the claims it targets. And an accepted backend PASS returns
   before the coverage probe (`faithfulness.py:125-148`), so the coverage half is bypassed.
2. **The certificate re-check is prop-blind and cannot express the named guards (critical).**
   `CertificateRechecker = Callable[[Certificate], bool]` (`sound_backends.py:48`) receives no `prop`,
   so it validates the certificate against itself and re-confirms a wrong derived domain/period. The
   ADR's "gate-derived period" and "independent re-check" guards require `prop` — i.e. **new gate
   code / a widened seam**, contradicting the ADR's "reuse the ADR 0037 seam" premise.
3. **The period formula under-derives the true period (high).** "lcm of the `mᵢ`" drops every
   non-modulus period source: floor-division `/d` (a DSL-whitelisted const op, `smt_z3.py:177-181`)
   multiplies the period by `d` — `(b/2)%8` has true period 16, not 8, so a gaming point at `b=12,13`
   is never enumerated → false EXACT-PASS; likewise `gcd(v,c)` (period `c`) and bounded `Σ/Π` index
   ranges. Point 4 only DEFERs on `%`/`÷` by a *variable*, not by a constant.

Plus vacuity/tautology gaps (empty `claim_domain` → vacuous PASS; all-of-ℤ/m property → non-discriminating PASS) and TCB growth (the interpreter **and** the period-deriver are trusted and unguarded by `test_invariants.py`; a shared trusted-input error reproduces on re-check).

**Required mitigations (the redesign blueprint for a v2):**
1. Re-specify the target: enumerate the **faithfulness PAIR over `established_domain`** exactly as
   `probes.py` does (coverage *and* property both zero over the decisive domain) — never
   `claim_domain ∧ ¬claim_property` alone. Delete the false "same target the probe/Z3 use" claim.
2. Bind the Certificate to `established_domain` **and** the `theorem_src`/statement hash, so it cannot
   be replayed for a broader claim (a COMPUTE certificate must name the exact statement it certifies).
3. Thread `prop` into the re-check: widen `CertificateRechecker` to `(Certificate, Propositio) → bool`
   (or have the gate derive the period from `prop`'s AST and assert it equals the certificate's), and
   state plainly that this is **new gate code**, not the unchanged ADR 0037 seam.
4. Replace "lcm of the `mᵢ`" with a **per-op period contract**: `% m`→`m`; `/d` on a decisive path →
   ×`d` (or DEFER on any `/const` on a decisive path); `gcd(v,c)`→`c`; bounded `Σ/Π`/factorial → the
   index cap enters the decisive range; any op without a proven period contract ⇒ DEFER. Add
   `/ by a constant` to the DEFER list.
5. **Build** (not merely name) vacuity/discrimination controls on the EXACT-PASS path: a
   `claim_domain`-SAT positive control (empty domain ⇒ DEFER), a non-tautology control, and a
   positive/negative/DEFER regression triple the checker must respectively FAIL/PASS/DEFER.
6. Treat the period-deriver + interpreter as **inside the faithfulness TCB, not protected by the
   re-check**; pin them with an adversarial trust-boundary regression suite (nested mod, `/const`
   phase, `gcd` second-arg, Σ/Π index range, differential derived-vs-bruteforce period, an interpreter
   known-answer set) before shipping.
7. Move the AST periodicity/DEFER screen into the **gate** (which holds `prop`), not the
   backend-owned `applies()`; DEFER on any non-whitelisted construct before accepting an exact PASS.

The capability remains worth pursuing (exact enumeration genuinely decides two-variable modular UNSAT
where Z3 returns unknown, and unblocks the richer laws the daemon already conjectures) — but only via
a v2 that adopts all seven mitigations and passes a fresh adversarial review. As written, ADR 0054 is
not implementable.

---

*Original proposal (retained for the record — do not implement without the redesign above):*

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
