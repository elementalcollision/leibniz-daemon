# ADR 0075 — The faithfulness probe's coverage leg is decided without a box

- Status: accepted
- Date: 2026-07-25
- Depends on: ADR 0002 (the faithfulness gate), ADR 0021/0022 (the probe's two-leg form),
  ADR 0035/0066 (the box-dependent encodings this must refuse), ADR 0074 (which surfaced it)

## Context

`ClaimProbe` — the gate's mechanical fast path — certifies on two bounded Z3 queries:

1. **coverage** — `decide_unsat([claim_domain, ¬established_domain])`: no point the claim covers
   lies outside what the statement establishes;
2. **property** — `decide_unsat([established_domain, claim_domain, ¬claim_property])`: no
   counterexample to the claimed property.

Leg 1 asserts a **universally quantified implication**. Deciding it inside the `[0, 64]` search
box is unsound whenever the domain is *box-unrepresentative*: the search reports "no gap" because
the handful of in-box points happen to satisfy the narrower `established_domain`, while real
counterexamples sit just outside.

Found while reviewing ADR 0074, and **verified against clean `origin/main` (`91db5b0`)**:

```
claim_domain       = a % 4 == 1 and a > 60 and b % 4 == 1 and b > 60
established_domain = a % 16 == 13 and b % 16 == 13
claim_property     = (a*a + b*b) % 16 == 2        # FALSE at (61, 65) -> 10
```

The domain's only in-box point is `(61, 61)`, which satisfies both — so coverage returned
`unsat` and the probe returned **PASS** for a false claim. Unbounded, Z3 immediately exhibits the
gap: `a = 65` is in the domain and not in the established domain.

## Decision

`Z3Backend.decide_unsat_unbounded(preds)` — tri-state UNSAT over **all** non-negative integers:
the upper box is dropped from the solver, `v >= 0` is kept (non-negativity is part of the DSL's
ℤ-with-box semantics, not an artefact of the search), and predicates are compiled with
`bound=None`.

That last detail is what makes it safe rather than merely broader. **Every encoding that is exact
only inside the box refuses itself when the bound is `None`** — the ADR 0066 factorial/gcd
If-tables (`_table_arg`) and the ADR 0035 order reduction all require a usable bound and raise
`PredicateError`, surfacing as `None`. An unbounded verdict is therefore only ever returned for
encodings exact over the whole domain. Verified for `factorial(n) % 5 == 0`, `gcd(6, n) == 1`
and `2**n % 7 == 1`.

**Both** probe legs now use it. `False` (a genuine gap / a real counterexample) and `None`
(undecided, or not soundly encodable unbounded) both refuse — the probe DEFERs, as it already did
for every inconclusive result. A backend without the unbounded decider **DEFERs**; it never falls
back to the bounded query.

Coverage additionally short-circuits when `established_domain` is **byte-identical** to
`claim_domain`: it covers by construction, so no solver is consulted. Without this, every ADR
0035/0066 domain would DEFER unconditionally at the coverage leg even on the canonical contract,
killing fragments those ADRs exist to decide.

### The first draft fixed only the coverage leg — and that was not enough

Adversarial review demonstrated the identical exploit walking through the **property** leg
instead. With `established_domain == claim_domain` — the honest shape, and the one ADR 0074 now
*derives* — coverage passes trivially as `cd ∧ ¬cd`, handing the whole decision to the still
bounded property query, which is vacuously satisfied because the domain's only in-box point
`(61,61)` satisfies the claim. The probe returned a MECHANICAL PASS on a false claim. One leg
fixed, the identical hole one line below.

Two justifications the first draft gave for leaving that leg bounded were **empirically false**,
and are recorded here so the error is not inherited:

- *"Z3 returns unknown on exactly this nonlinear fragment."* It does not. On this predicate it
  returns **sat with the witness `(61, 65)`**. The `unknown` measurement came from a *different*
  predicate and was over-generalised.
- *"It would cost real yield."* Measured over the honest corpus: **zero** loss.

A third argument — *"a passing claim's theorem must still clear the kernel"* — was also
overstated and is withdrawn. The probe certifies the DSL triple while the kernel proves
`expressio.theorem_src`, a separately authored Lean string; nothing binds them on this path. The
probe's PASS is the last mechanical word on statement-vs-claim here, which is the argument for
fixing the leg rather than deferring to a backstop that does not exist yet.

## Consequences

**Yield.** On the canonical contract (`established_domain == claim_domain`, which ADR 0074 derives
for decided fragments) coverage is free and the property leg is *stronger* than before — some
claims the bounded query timed out on are now decided, so the probe certifies more, not less, on
better evidence. Measured on the honest corpus: no case lost.

**A real, deliberate refusal.** Claims whose *property* uses an ADR 0035/0066 encoding
(`factorial`, `gcd`, `base^n % m`) can no longer be certified by this probe at all: those
encodings are exact only inside the box, so the unbounded query refuses them. Those fragments have
kernel decision procedures which run **before** the probe in the gate's cost-ordered dispatch, so
they are decided where they should be — by the kernel, not by a bounded solver search. This is a
narrowing of the probe's reach and is intended.

**Load-dependence** is unchanged in kind: a query exceeding Z3's 3-second wall-clock budget
returns `None` and refuses, so a busy machine yields less, never more.

## Review

Reviewed adversarially before merge (soundness, yield/regression, bypass). The soundness angle
found the property-leg hole above and refuted two of this ADR's own claims; both are corrected
here rather than quietly dropped. The review also caught the fail-open fallback for backends
lacking the unbounded decider, and the unconditional DEFER of ADR 0035/0066 domains — both fixed.
