# γ3b verdict — do NOT build the lean-smt image; the tail is a *gate* problem, not a prover problem

- Date: 2026-07-24
- Method: four independent investigators over the live ledger + journal, each re-derived by an
  adversarial skeptic instructed to refute it; load-bearing claims re-run by hand afterwards.
- Supersedes the "defer, evidence-gated" recommendation in
  [`lean-smt-spike-2026-07-22.md`](./lean-smt-spike-2026-07-22.md).

## Verdict 1 — the lean-smt image: DON'T BUILD

The gate was: build only if the journal shows unclassified-arithmetic UNPROVEN volume, or cvc5
rescuing Z3-unknowns. Both readings came back negative, and the second decisively:

- **cvc5 rescue rate: 0 of 21.** Aggregate `CROSS_STATS` over every beat: `checked=10, agree=10,
  disagree=0, unknown_rescued=0, unknown_kept=21`.
- **That 0/21 is an on-population number.** The obvious objection — "the cross-check re-decides
  *bounded, quantifier-free box* scripts, while an `smt` tactic would face the *unbounded* goal, so
  the measurement doesn't transfer" — was tested and **refuted**. Taking the daemon's own live
  claim `(a^2 + b^2) % 4 != 3` through the production compile path and box: Z3 returns `unknown`
  at 2.06 s, and `Cvc5CrossCheck().redecide()` on that exact script then also returns `unknown`
  (33 s). cvc5 sees the real tail and fails on it.
- lean-smt **is** cvc5 plus in-kernel proof reconstruction. A tactic backed by a solver that
  cannot decide these goals cannot close them either. Expected yield ≈ 0, against a rebuilt
  ~11 GB image, a toolchain pin that must match Lean 4.31 + Mathlib exactly, and a nightly
  preflight newly dependent on it.

**What would flip this:** a tail population that is *decidable by cvc5 but not by Z3*. The
`unknown_rescued` counter measures exactly that and is free to keep watching. It is 0 today.

## Verdict 2 — the actual defect (this is where the yield is)

The premise behind γ3b — "the UNPROVEN tail needs more prover reach" — is **false**. The tail never
reaches a prover at all.

- **8 of the 12** notebook `too_hard` entries die at the **faithfulness gate**, before any proof
  compute. (The 2026-07-24 beat: 8 candidates, `reached_proof: 0`.)
- An **empty `finish_reason` uniquely means faithfulness DEFER**: `Formalize.run`'s
  `if faith.verdict is not Verdict.PASS: return None` is the only non-quarantining exit, and
  `daemon.py` relabels the absent reason as `UNPROVEN` for the report and the notebook only. The
  notebook's `too_hard` is therefore a misnomer — these are *ungated*, not *unproved*.
- **Variable count is not the limit.** `lean_decided.MIN_VARS, MAX_VARS = 2, 3`; the tail's
  residue-cell counts are 16–81 against `MAX_RESIDUE_CELLS = 4096`. Nothing caps them.
- **The kernel can already do these.** With a canonical contract (`established_domain` = the plain
  box), `FaithfulnessGate.check` returns PASS / `lean_decided/kernel` for **7 of 11** tail
  properties — including `(a^2 + a*b + b^2) % 9 != 6` — and `residue_prover`'s generated law is
  kernel-**accepted** for all 6 distinct true claims, while the false control
  `((4*a+1)*(4*b+3)) % 8 == 3` is correctly kernel-**rejected**. The trust boundary holds; the
  machinery works.

### The causal chain, verified end to end

1. `established_domain` is **LLM-authored free text** (the FORMALIZE prompt asks for "the DSL
   predicate ... that the formal statement ACTUALLY establishes the property on"). Nothing derives
   it mechanically and nothing validates it beyond encodability.
2. When the LLM folds the claim property into that field, the gate's **coverage leg becomes the
   theorem itself** and the kernel refuses it. Measured by variant sweep on one claim: plain-box
   `established_domain` → PASS (`z3: unsat×1`); property-restating → DEFER
   (`z3: unknown×2`); `decide_certificate` reports `reason='kernel did not accept coverage'`.
3. **ADR 0022's `_steer_contract` should repair exactly this** — it is the mechanical,
   bounded contract-repair pass, it is active on beats, and its guards are sound by construction.
   But every guard "needs a conclusive `decide_unsat`", and it **fails closed** without one.
4. **Z3 cannot answer on this fragment.** `decide_unsat` returns `None` for
   `(a^2+a*b+b^2) % 9 != 6`, `(a^2+b^2) % 4 != 3` and `(a^2+a*b+b^2) % 4 != 2` (linear control:
   `True`). So the repair pass silently commits nothing, the bad contract reaches the gate, and
   the candidate DEFERs.
5. The tail then **self-amplifies**: `weakening_seeds` re-proposes `too_hard` entries, which
   re-DEFER for the same reason. `(a^2 + b^2) % 4 != 3` appears as a DEFERred row on 07-07, 07-14,
   07-21, 07-22 and 07-23 before finally being promulgated on 07-23 — five wasted passes at a
   claim the kernel could decide the whole time.

**Ledger-wide scale:** of the 54 DEFERred rows carrying a DSL property, **25–29 are decidable by
already-shipped, already-registered procedures** (the two independent classifications differ by
4). Roughly half the daemon's dead candidates are dead for contract reasons, not mathematical ones.

## Recommended next increment (needs the operator's word — it touches the gate's input)

Give `_steer_contract`'s guards a decider that can actually answer: **fall back to the kernel
(the registered decided-fragment backends) when `decide_unsat` returns `None`.** The guards, their
soundness conditions, and the ADR 0022 discipline all stay exactly as written — the repair is still
committed only when *conclusively* sound, and the faithfulness gate still re-decides coverage and
property afterwards. The only change is which oracle discharges the guard, and the substitute is
the *more* trusted one: Z3 says "I don't know", the Lean kernel says "proved".

This is flagged rather than shipped because it changes what the faithfulness gate is handed, and
that is a trust edge (ADR 0001/0002). Expected yield if it holds up: on the order of half the
DEFERred ledger, without a single new line of prover reach.
