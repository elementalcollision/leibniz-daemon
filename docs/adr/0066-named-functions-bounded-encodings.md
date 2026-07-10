# ADR 0066 — Named functions in the faithfulness DSL: `factorial` and `gcd` by bounded definition

**Status:** **BUILT.** The roadmap's last deferred DSL item ("named functions (`Nat.log`, `factorial`,
`gcd`) — a bounded definitional encoding would bring them in"): `factorial(n)` and `gcd(a, b)` join
the faithfulness DSL, encoded EXACTLY over the bounded box as Z3 If-tables. Probe-reach only — the
**trust boundary is untouched**, no kernel procedure is added, and the renderer deliberately keeps
refusing these (lockstep is ⊆, never more than Z3 — the pre-ADR-0065 status quo for the order case).

## Context

The Z3 probes (cheap refutation, the gaming spine, ClaimProbe faithfulness) decide DSL predicates
over a bounded box (`0 ≤ v ≤ bound` is asserted for every variable in every solver query). A named
function with no Z3 builtin can still be encoded **exactly** on that box as a value table — the same
"box makes it finite" assumption the ADR 0035 order-reduction already rests on. Without this,
conjectures mentioning `factorial`/`gcd` were rejected at the grammar (`FORBIDDEN` in the ADR 0022
prompt) and DEFERred at encoding.

## Decision

1. **`factorial(n)`** — argument a BARE variable (exact: `v ∈ [0, bound]` in every query) or a small
   constant. Encoded as an If-chain `If(v = 0, 0!, If(v = 1, 1!, …))` over the box; a constant folds
   to its value. Cap: `MAX_TABLE_BOUND = 128` on `bound`/constants.
2. **`gcd(a, b)`** — both arguments bare variables or constants. `const/const` folds;
   `var/const` is one If-chain; `var/var` is the nested `(bound+1)²` table. DSL semantics are
   Python's `math.gcd` on the non-negative box (agreeing with `Nat.gcd`/`Int.gcd` there).
3. **Exact-or-DEFER, mirror of ADR 0035:** a compound argument (`factorial(n+1)`, `gcd(a*b, c)`,
   a nested call), a missing search bound, or an over-cap constant raises `PredicateError` → the
   caller DEFERs. Never a wrong encoding.
4. **Grammar (ADR 0022 prompt):** `factorial`/`gcd` move from FORBIDDEN to allowed, with the
   bare-argument restriction stated; everything else stays forbidden.
5. **Renderer unchanged (deliberate):** no kernel decision procedure consumes these yet, so
   `dsl_to_lean` keeps raising on them. The lockstep doctrine is "never MORE than Z3" — Z3-only
   widening matches how the ADR 0035 order case lived before ADR 0065 gave it a kernel procedure.
6. **`Nat.log` stays deferred:** no DSL surface or conjecturer demand exists for it; add it the day
   a use appears (one more table).

## Soundness

The tables are exact on the box because every solver query in `smt_z3` asserts the box for every
variable; a bare-variable argument therefore ranges exactly over the table's index set. Everything
un-tableable DEFERs. Pinned by tests that compare `find_counterexample` against a brute-force Python
oracle over the same box (agreement on SAT/UNSAT and model validity), plus DEFER cases and the
renderer's continued refusal.

## Consequences

- Conjectures about factorials and gcds stop dying at the grammar/encoding: the cheap-refutation and
  gaming spines can kill false ones, and ClaimProbe can certify bounded-faithful ones.
- Honestly: this is **reach, not novelty** — Wilson-type instances and gcd identities are textbook;
  the origination-hunt finding (2026-07-09) applies unchanged to this fragment.
- Follow-on if ever warranted: a kernel decision procedure (and renderer support) for a decidable
  factorial/gcd fragment, as ADR 0065 did for the order case.
