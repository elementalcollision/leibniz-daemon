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
`PredicateError`, which surfaces as `None`. So an unbounded verdict is only ever returned for
encodings that are exact over the whole domain. Verified for `factorial(n) % 5 == 0`,
`gcd(6, n) == 1` and `2**n % 7 == 1`, each of which returns `None`.

The probe's **coverage** leg now uses it when the backend offers it. Both `False` (a genuine gap)
and `None` (undecided, or not soundly encodable without a box) **refuse** — the probe DEFERs, as
it already did for every inconclusive result.

The **property** leg deliberately stays bounded. It is a pre-proof sanity check, not the thing
that establishes the claim: the kernel is. Making it unbounded would buy little — Z3 returns
`unknown` on exactly this nonlinear fragment (measured) — and would cost real yield.

## Consequences

**Yield: measured zero loss.** Across all 93 ledger rows carrying a DSL contract, the bounded and
unbounded coverage verdicts agree exactly. That is structural, not luck: for a canonical contract
(`established_domain == claim_domain`, which ADR 0074 now derives for decided fragments) the query
is `cd ∧ ¬cd` — unsat instantly for any domain. What changes is precisely the case the fix targets:
an `established_domain` genuinely narrower than the claim, which *should* refuse.

**What this does not fix.** The property leg remains a bounded search, so a claim that is false
only outside `[0, 64]` can still take the probe's PASS branch — with `established_domain` honestly
equal to `claim_domain`. That is not the same defect: coverage now guarantees the statement is
held accountable to the *whole* claimed domain, so a passing claim is one whose own theorem the
kernel must then prove over that domain — and a false theorem is rejected there. The probe was
never the thing that establishes truth.

**Load-dependence** is unchanged in kind: an unbounded query that exceeds Z3's 3-second wall-clock
budget returns `None` and refuses, so a busy machine yields less, never more.
