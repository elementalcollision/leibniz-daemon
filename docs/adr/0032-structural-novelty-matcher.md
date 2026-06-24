# ADR 0032 — Structural novelty matcher (catch restatements by FORM, not truth) (Proposed)

- Status: **Accepted / implemented** (2026-06-24). To not repeat the ADR 0031 L2 failure, the
  process was design → adversarial DESIGN review → implement → adversarial IMPL review, each
  hunting a false-KNOWN. **All three converged SOUND** (empirical prototype; 14-agent design
  review, 10 candidate flaws all dismissed on re-derivation; implementation review, no
  code-level collision). `leibniz/structural.py` + `CorpusBackend.structural_known` +
  `NoveltyGate` integration; pure stdlib (no Z3, no Lean, no corpus rebuild).
- Date: 2026-06-24
- Related: ADR 0031 (novelty; L1 exact-hash + L3 steering stand, **L2 decision-procedure
  equivalence RETRACTED as unsound**), ADR 0001 (novelty = retrieval + decision procedure,
  never a judge), ADR 0021/0030 (the DSL these predicates live in). Targets:
  `leibniz/corpus.py`, `leibniz/gates/novelty.py`. Non-guarded. Roadmap: Tier 1 / R3.

## Context — what L2 got wrong, precisely

The organic run rediscovered Fermat's little theorem and elementary divisibilities, restated
in forms the exact elaborator-hash (L1) misses (`(n^5+4n)%5==0` vs `n^5%5==n%5`). L2 tried to
catch them by Z3 **box-equivalence** of the claim predicates — and that is **fatally unsound for
novelty**: a claim's `claim_property` is, for a *true* conjecture, a tautology over its domain
(it holds for all n). Two tautologies are trivially box-equivalent, so L2 matched **every** true
claim to **any** always-true corpus predicate — it would demote all genuine novelty to KNOWN.
The lesson: **a novelty matcher must not decide on TRUTH** (all theorems are true); it must
decide on **FORM** (what does the claim *say*).

## Decision — canonicalize the claim's congruence FORM to a signature

The rediscovered band is **univariate polynomial congruences**: "for all n, `F(n) ≡ G(n)
(mod m)`" (incl. divisibility `m | F(n)` written `F(n) % m == 0`). Restatements of the *same*
fact differ only in surface algebra. Reduce each such claim to a canonical **signature**, purely
SYMBOLICALLY, and match signature-to-signature.

**`structural_signature(claim_property) -> Optional[Signature]`:**
1. **Parse** the DSL predicate into a recognized congruence shape, else return `None`
   (un-recognized → no signature → never matched → stays NOVEL). Recognized:
   - `P % m <relop> c`            (relop ∈ {==, !=}, c a constant) → `P − c ≡ 0 (mod m)`
   - `P1 % m <relop> P2 % m`      → `P1 − P2 ≡ 0 (mod m)`
   - `P % m <relop> Q`            (Q a constant) → as above.
   where `P, P1, P2` are **univariate** polynomials in the single claim variable, built from
   the DSL's `+ - *` and constant `^` (the poly fragment). `m` is a constant ≥ 2.
2. **Expand** the difference polynomial to monomials with a small stdlib AST expander
   (represent as `{exponent: int_coeff}`; implement add/sub/mul/const-pow over these dicts —
   no sympy, no Z3). Multivariate or non-polynomial (variable exponent, `/` or `%` inside `P`,
   a function call) → `None` (skip).
3. **Reduce** every coefficient mod `m`; drop zero monomials.
4. **Normalize** (recall, not soundness): if `m` is prime and the leading coefficient is a unit,
   multiply through by its inverse mod `m` (canonical monic form) so unit-multiples and
   side-swaps collapse. If normalization is not well-defined (composite `m`, non-unit lead),
   **skip it** — that only costs a missed match (NOVEL), never a wrong one.
5. **Signature** = `(relop, m, tuple(sorted (exponent, coeff)))`. The variable name is dropped
   (single var → alpha-invariant).

**Match:** precompute every corpus entry's signature from its `claim_property` (already stored
since the L1 rebuild — **no Lean, no corpus rebuild**). A candidate is KNOWN iff its signature
is non-`None` and equals a curated entry's. `NoveltyGate` runs this after the exact-hash miss;
no Z3, no `smt` wiring.

## Soundness argument (the crux — and why it can't repeat L2)

The signature is a **faithful, purely symbolic** encoding of the polynomial congruence the claim
asserts in `ℤ/mℤ`. Coefficient reduction mod `m` is sound because two integer polynomials with
coefficients congruent mod `m` denote the **same** congruence (they are equal in `(ℤ/mℤ)[n]`).
Therefore:

- **Same signature ⟺ same congruence ⟺ same fact.** Two claims match exactly when they assert
  the same polynomial congruence (up to the unit-normalization in step 4). A genuinely
  *different* fact — different polynomial, modulus, or relation — has a *different* signature.
- **No false-KNOWN.** There is no path by which two *distinct* congruences collapse to one
  signature; the canonicalization is injective on the congruence-as-written (mod-`m`
  coefficients + monomial collection are exact algebraic normalizations, not value reductions).
  Crucially, **truth is never evaluated** — so the L2 failure (all-truths-are-equivalent) cannot
  arise. `n + 0 == n` (the case L2 wrongly matched) is not a congruence → `None` → NOVEL.
- **All error is one-directional and benign.** Anything not recognized, not univariate, or not
  unit-normalizable → `None` → NOVEL (a *missed* known, the pre-existing gap), never a wrongly
  suppressed novelty. And novelty only DEMOTES (KNOWN quarantines, reversible; ADR 0031) — it can
  never cause a false promulgation.

Worked check of the L2 trap: `(n^2+n) % 2 == 0` → `{n^2:1, n:1}, m=2, ==,c=0`; Fermat-2
`n^2%2==n%2` → `n^2−n` → mod 2 → `{n^2:1, n:1}` (−1≡1) → **same signature**. These genuinely ARE
the same congruence (n²+n ≡ n²−n mod 2), so matching is CORRECT — unlike L2, which also matched
the *unrelated* `n+0==n`. The structural matcher matches the former and rejects the latter.

## Scope + limits (stated, not hidden)

- Handles **univariate polynomial congruences** — exactly where every rediscovered classic lives
  (Fermat `n^p≡n mod p`, power-residue `n^k≡n mod m`, consecutive-product `% m == 0`).
- Does NOT handle: multivariate claims, non-polynomial `P`, inequalities, symbolic moduli — all
  return `None` → NOVEL. Acceptable: the inflow that matters is the modular band, and L3 steering
  + L1 exact-hash cover adjacent cases. Widening is additive later.
- It is a *recall* tool with perfect precision by construction; missed restatements outside the
  recognized shapes are the residual (safe).

## Status note — multivariate extension (2026-06-24, additive, DORMANT)

`leibniz/structural.py` now also signs **multivariate** polynomial congruences (a 2nd distinct
variable no longer forces `None`). This is the additive widening the original scope note
anticipated, done SOUNDLY and conservatively:

- **Monomial = sorted tuple of `(variable_name, exponent)`**; signature =
  `(relop, m, tuple(sorted((monomial, coeff_mod_m))))`. The constant monomial is `()`.
- **Match keys on the LITERAL variable names — NO variable-renaming canonicalization.** Mapping
  `a,b → x,y` is a permutation-canonical-form problem; a wrong canonical choice would collapse two
  genuinely different congruences into one signature — a **false-KNOWN**, the one forbidden bug.
  We refuse it. Consequence: `a*b % 2 == 0` matches a corpus `a*b % 2 == 0` but NOT `x*y % 2 == 0`
  (a rename). That miss is a **false-NOVEL** — safe (lower recall, never a wrong KNOWN).
- **Univariate behavior is byte-identical.** The single-variable claim is the special case: it
  still renders the legacy `(exponent, coeff)` signature and still applies prime-`m` unit
  (monic) normalization. Multivariate **skips** unit normalization — unit-normalization across
  several variables is ambiguous (which leading term?), so we skip it (lower recall, never wrong).
  The two render shapes are disjoint (int exponent keys vs `(name,exp)`-tuple monomial keys), so a
  univariate signature and a multivariate signature can never coincide.
- **No false-KNOWN, by construction.** A different monomial set — different variable *names*,
  different exponents, a different *number* of variables, or a different coefficient mod `m` —
  yields a different signature. Coefficient reduction mod `m` is exact in `(ℤ/mℤ)[vars]`; truth is
  never consulted. The prototype-era bug (`a*b` colliding with `a^2`) cannot recur: `a*b`'s key is
  the tuple `((('a',1),('b',1)),1)` while `a^2`'s univariate key is `((2,1))` — structurally
  distinct. (Note a benign edge: a *syntactically present but cancelled* variable, e.g.
  `(n + m - m) % 3 == 0`, is treated as multivariate and so does NOT collapse onto pure `n % 3 ==
  0` — a conservative miss, never a wrong match.)
- **DORMANT until corpus has multivariate entries.** The matcher only demotes to KNOWN against a
  curated corpus signature; `corpus/known_results.json` currently has **no** multivariate
  `claim_property`, so this path matches nothing in production today. It only *prepares* the
  matcher; a future `build_corpus` run that adds multivariate knowns activates it. Until then the
  behavior change is invisible at the gate (multivariate candidates still survive as NOVEL — they
  just now carry a signature instead of `None`).

## Integration

- `corpus.CorpusBackend`: precompute `{signature: name}` from entries' `claim_property` at load;
  add `structural_known(claim_property) -> Optional[str]`.
- `gates/novelty.NoveltyGate`: after `contains_equivalent` (hash) misses, compute the
  candidate's signature from `prop.enuntiatio.claim_property`; a hit → KNOWN with the matched
  name + `"reason": "structural congruence match"`. No new backend; `smt` stays unused/removed.
- The canonicalizer is a standalone, pure-Python, CI-safe module (`leibniz/structural.py` or in
  `corpus.py`), unit-testable without Lean or Z3.

## Validation plan (gate the implementation, then the activation)

- **Unit (CI-safe, no backend):** the expander/canonicalizer is exact — distinct polynomials get
  distinct signatures; restatements collapse:
  - the 12 organic restatements (`(n^5+4n)%5==0`, `(n^3+2n)%3==0`, `(n^5−n)%30==0`, …) each map
    to the signature of their corpus family entry → KNOWN;
  - the L2 traps: `n+0==n` → `None` (NOVEL); a genuinely-novel congruence (`n^2 % 7 == 2`) →
    distinct signature → NOVEL; an always-true-but-different fact stays distinct.
  - a property-style test over random small polynomials: `sig(P)==sig(Q)` ⟺ `P≡Q (mod m)` as
    formal polynomials (cross-checked by direct coefficient comparison, not by evaluation).
- **Adversarial review of the DESIGN (this ADR) BEFORE coding**, then of the implementation —
  both hunting a single thing: can two DIFFERENT facts share a signature (false-KNOWN)? This time
  a BROKEN verdict halts the merge; findings are re-derived from first principles, not dismissed.
- **Live:** re-run the organic funnel; the classic families come back KNOWN, genuinely novel
  conjectures survive (audited).

## Open questions

- Unit-normalization for composite `m` (skip vs partial) — start with prime-only normalization;
  measure how many composite-`m` restatements are missed before adding more.
- Whether to also structurally canonicalize the corpus's `theorem_src` (Lean) rather than the DSL
  `claim_property`, to cover knowns lacking a DSL contract — deferred; the DSL path covers the band.
