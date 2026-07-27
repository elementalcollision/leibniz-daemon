# ADR 0079 — A re-rendering certificate binds the statement that gets promulgated

- Status: accepted
- Date: 2026-07-25
- Depends on: ADR 0058 (the A2 re-rendering argument), ADR 0074 (which documented this gap)

## Context

When a re-rendering fragment certifies faithfulness, its certificate binds a **canonical**
statement derived from `(claim_domain, claim_property)`. But DEMONSTRATE may still fall through
to the LLM ensemble — the fast-path declines whenever the kernel rejects the re-rendered law, or
`axiom_closure` fails, or the REPL hiccups — and the ensemble proves the autoformalizer's *own*
`theorem_src`, a statement the certificate never bound.

Nothing tied the two together. ADR 0074 recorded this as a residual gap and noted it did not
create it but did make it reachable more often. The design review of the mechanical-render
proposal recommended closing it here, as the safe alternative to rendering `Expressio` early —
because a check in the promotion gate can only ever **refuse**, whereas the render could
*manufacture* a law (demonstrated: an empty-domain contract producing a kernel-provable theorem).

## Decision

In `VerificationGate.is_promotable`, before `validate_path`: for each faithfulness **PASS** edge
whose producer is in `_CANONICAL_BY_PRODUCER`, compute the statement that fragment's fast-path
would have proved and require `expressio.theorem_src` to be **byte-identical** to it
(`type(x) is str` + `str.__ne__`, the discipline used at the gate's other binding sites).

**Refuse-only.** It can reject a promotion, never create one. When the canonical form is not
computable — no such producer, no DSL contract, or the generator abstains — **no constraint is
imposed**, so prose-only claims, `walnut`, `ClaimProbe` and every non-re-rendering path behave
exactly as before.

## Consequences

The certificate and the proof now describe the same statement, or the law is not promulgated.

**Honest limit on the impact measurement.** I could not measure this against the live ledger:
`claim_domain` is not persisted in `memory`, and the certifying producer is not recorded per row,
so any reconstruction has to guess both. An initial attempt reported "8 mismatches" and was
discarded as an artifact of that guessing. What is verified is behavioural: the canonical
statement promotes, a different statement under a re-rendering certificate is refused,
non-re-rendering producers are unconstrained, an uncomputable canonical form imposes no
constraint, and a prop the base gate already rejects is not rescued.

**Yield risk, stated plainly.** Where the fast-path legitimately declines and the ensemble proves
a *sound* variant, that law is now refused rather than promulgated. That is the intended trade —
the certificate did not bind that statement — but it is a real narrowing, and the journal's
promulgation counts are where it will show.

One existing test paired a re-rendering producer with an unrelated `theorem_src`; its subject is
novelty revalidation, so its producer was incidental and is now a non-re-rendering one.

## Review

Adversarially reviewed before merge (refuse-only verification, yield, code review). Findings, all
fixed here:

- **A silently unbound fragment.** The table mapped `mixed_modular/kernel` to
  `mixed_modulus_law`; the generator is `mixed_law`. `getattr` raised, the blanket
  `except Exception` swallowed it, the canonical form came back `None` — "no constraint" — and
  mixed-modulus claims were left exactly as exposed as before, with nothing failing. My own test
  file would never have caught it: every assertion used the default `lean_decided/kernel`.
- **The blanket except was the mechanism**, not an accident. It now distinguishes a *structural*
  failure (a table that no longer resolves — a bug) from a generator's legitimate abstention, and
  `test_every_table_entry_resolves` fails loudly on the former. Reintroducing the typo now turns
  two tests red.
- **Order.** The binding moved to *after* `validate_path`, so untrusted contract strings are never
  rendered on a path the trust policy is about to reject. Verdict-neutral.
- **Refuse-only confirmed independently**: a differential harness over 302,400 constructed
  candidates (every tier × verdict × producer × edge-subset × theorem_src shape) found **0
  False→True flips** against `origin/main`, with the typo both present and patched. Cost ~26 ms
  one-time import, ~129 µs per call.
