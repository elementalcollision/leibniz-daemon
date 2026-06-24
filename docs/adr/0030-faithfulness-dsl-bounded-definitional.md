# ADR 0030 — Faithfulness DSL increment: bounded definitional encodings (Proposed)

- Status: **Tier A implemented** (2026-06-23). **Tier B implemented on branch
  `adr0030-tierb-symbolic-exp` (2026-06-24) and HELD — not merged** (sound but inert at the
  gate's bound; see *Tier B outcome* below). **Tier C revisited (2026-06-24) and SHELVED** —
  the conjecture mix produces zero such claims and `factorial` is inert at the production bound
  (see *Tier C outcome* below).
- Date: 2026-06-23
- Related: ADR 0002 (faithfulness gate), ADR 0004 (structured contract), ADR 0020 (refuse
  vacuous passes), ADR 0021 (widen the DSL — multi-var, constant powers, constant mod/div),
  ADR 0022 (conjecturer contract encodability). Target: `leibniz/backends/smt_z3.py`.
  Non-guarded (proposal-side gate input). Roadmap: Tier 1 (faithfulness — remaining follow-up).

## Context

ADR 0021 widened the faithfulness DSL to multi-variable arithmetic, **constant** powers
(`n^3`), and **constant** mod/div, and ADR 0022 steers the conjecturer to emit contracts
inside it — together collapsing the DEFER fraction (~95% → ~20%) so candidates now reach
proof. The remaining DEFER bucket is dominated by two un-encodable shapes the conjecturer
still naturally reaches for:

- **symbolic exponents** — `2^n`, `k^n` (a variable in the exponent), and
- **named arithmetic functions** — `min`, `max`, `gcd`, `factorial`, `Nat.log`.

These currently raise `PredicateError` → "no witness" → the ADR 0020 probe DEFERs (the safe
default — a wrong UNSAT would be a vacuous PASS, the exact failure ADR 0020 closed). So claims
that mention them can never be certified, hence never promulgated. This is **not** the current
binding blocker (prover reach is — ADR 0028/0029), so this is a *band-widening* increment, not
a critical-path one; it is recorded now so it can be approved deliberately and picked up when
reach work plateaus.

## Non-negotiable posture (unchanged)

Every accepted construct must have an **exact** encoding over the bounded box `[0, bound]`, so
`UNSAT` genuinely means "no witness in the box" and `SAT` exhibits one. Anything not exactly
encodable continues to raise `PredicateError` and DEFER. We never trade a DEFER for a guess.
The `ast.Call`/`eval`/`__import__` security whitelist stays closed except for the named,
pure, total functions enumerated below. `gates/` and `tests/test_invariants.py` stay untouched.

## Decision — three tiers, gated by soundness + cost, shipped in order

### Tier A — `min` / `max` (trivial, exact) — **IMPLEMENTED**

Whitelist `min(a, b)` and `max(a, b)` in the `ast.Call` handler, encoding to
`z3.If(a < b, a, b)` / `z3.If(a > b, a, b)` (n-ary via fold). Exact for all integers, no
bound interaction, no blow-up. Reject any other call shape (attributes, keywords, starred
args, other names, arity < 2). The cheapest, highest-confidence win.

**Shipped** in `smt_z3.py` (`_conv` `ast.Call` branch) + the conjecturer `_DSL` prompt
(min/max moved from forbidden to allowed). Property tests pin exactness over the box
(`max+min == a+b`, `min ∈ {a,b}`, n-ary bounds), reject cases degrade to DEFER, and a
wrong-UNSAT regression confirms a false claim yields a real witness. An independent
adversarial review (soundness + security of the new `ast.Call` surface) returned SOUND —
no eval/import/attribute reachable; encoding exactly equals Python min/max.

### Tier B — symbolic exponents `base ^ exp` (bounded If-chain)

When `ast.Pow` has a **non-constant** exponent (today: DEFER), and the exponent sub-term is a
single bounded variable `e` with box bound `B`, encode `base ^ e` as the exact finite
case-split

    z3.If(e == 0, 1, z3.If(e == 1, base, … z3.If(e == B, base^B, 0) …))

— `B + 1` arms, each a constant-power expansion (reusing the ADR 0021 repeated-multiplication
path). It is exact because `e ∈ [0, B]` is the *entire* domain of the search box, so no arm is
missed. Guardrails:

- **New cap `MAX_SYM_EXP_BOUND` (default 16).** If the exponent variable's effective bound
  exceeds it, DEFER — the If-chain (and the magnitude `base^B`) would be too large to decide
  reliably. (The search box `bound` may be temporarily clamped for that variable, or the whole
  predicate DEFERs — see Open questions.)
- **Exponent must be a bare variable or constant**, not a compound expression (`2^(n+1)` →
  DEFER in v1; can phase in by encoding the inner term then If-chaining over its range, but the
  range of a compound term isn't a single box bound, so it's deferred until proven sound).
- Magnitude: `base^B` is exact in Z3's unbounded integers (no overflow), just costly; the cap
  keeps it tractable and the per-search timeout (ADR 0021) still turns an undecided search into
  a DEFER, never an UNSAT.

#### Tier B outcome (2026-06-24) — implemented, verified sound, HELD as inert

Built on branch `adr0030-tierb-symbolic-exp` exactly as specified (the `B+1`-arm `If`-chain,
`MAX_SYM_EXP_BOUND=16`, whole-predicate DEFER, compound/over-cap → DEFER). Empirical review on
that branch:

- **Sound** (no wrong-UNSAT). A symbolic-exponent claim that is false somewhere yields a real
  witness (`find_counterexample("2^n % 2 != 0", 16)` → `{n:0}`); a tautology → UNSAT; an
  over-cap or compound exponent → `encodable` False → DEFER, never a vacuous PASS.
- **But inert at the production bound.** The faithfulness gate searches at `gaming_bound = 64`
  (`gates/faithfulness.py`), and `MAX_SYM_EXP_BOUND = 16 < 64`, so *every* symbolic-exponent
  predicate is over-cap → DEFER. `encodable("2^n % 3 == 1")` is False at the default bound —
  identical behaviour to pre-Tier-B. The machinery only activates when a caller passes
  `bound ≤ 16`, which the gate never does.
- **The prompt change is therefore a net regression.** Tier B moved `2^n, k^n` into the
  *allowed* DSL in the conjecturer prompt; at the gate's bound those claims DEFER, so it merely
  invites conjecture cycles that cannot pass faithfulness, with zero upside.

This **resolves the open question below**: neither clamp option works at `bound = 64`.
*Per-variable clamping* (exponent → 16, other vars → 64) is **unsound** — a multivariate claim
false only at some other variable in `[17, 64]` would be missed → wrong-UNSAT. *Whole-predicate
DEFER* (the implemented choice) is sound but inert as shown. The only sound *and* active option
is a chain reaching the full `B = 64`, i.e. `MAX_SYM_EXP_BOUND = 64` — but that is a degree-64
nonlinear term over the box, which Z3 times out on → DEFER anyway, just slower. So symbolic
exponents do not fit the bounded-Z3 model at the production bound.

**Decision: shelve Tier B.** The branch is preserved for the record but not merged; the prompt
stays as-is (symbolic exponents forbidden) on `main`. This vindicates the ADR's own framing that
the DSL increment is band-widening, not critical-path — and shows the symbolic-exponent band in
particular cannot be widened soundly *and* usefully here. Revisit only if the gate's bound model
changes (e.g. a periodicity-aware reduction for modular claims).

### Tier C — `gcd` / `factorial` / `Nat.log` (bounded tables, behind tight caps)

Each is total and pure but only *cheaply* sound over a small range:

- **`factorial(n)`** — exact via an If-chain table for `n ∈ [0, MAX_FACT]` (default 12; `12!`
  fits comfortably); DEFER if `n`'s bound exceeds `MAX_FACT`. `n!` explodes, so the cap is
  about cost, not soundness.
- **`gcd(a, b)`** — exact via Euclid **unrolled to a fixed depth** `GCD_STEPS` (default 8;
  enough for any `a,b ≤ 256` since Euclid is logarithmic), each step a `z3.If(b == 0, a, …)`
  with `a, b := b, a % b`; the final value is `gcd` iff the unrolling reached `b == 0`, else
  DEFER (witness it didn't converge → refuse rather than approximate).
- **`Nat.log(b, n)`** — exact via the bounded table `largest k with b^k ≤ n` over the box;
  reuses the Tier-B If-chain. Lowest value, ship last or not at all.

Tier C is the riskiest (a subtly wrong table = a wrong UNSAT = a vacuous PASS), so each
function lands with its own adversarial soundness review (per the ADR 0021 precedent) and a
property test that the Z3 encoding agrees with Python's `math.gcd`/`factorial` on the whole box.

#### Tier C outcome (2026-06-24) — revisited, SHELVED (does not earn its keep)

Revisited per the open question below ("only do Tier C if the conjecture mix actually needs
it"). The evidence says it does not:

- **Zero demand.** The conjecturer DSL *explicitly forbids* `gcd`/`factorial`/`Nat.log`
  (`anthropic_provider.py`: "FORBIDDEN … named functions (log, sqrt, gcd, factorial, Nat.log,
  floor, sums/products)"). The organic runs' ledger contains no such claims — every candidate is
  a polynomial/modular congruence (min/max + the Tier A band). So nothing would ever exercise
  Tier C unless the prompt were *also* changed to invite these functions.
- **Inviting them repeats the Tier B trap.** `factorial` caps at `MAX_FACT = 12`, far below the
  gate's `gaming_bound = 64`; a factorial claim over the box would be over-cap → DEFER at the
  production bound — inert, exactly like Tier B. (`gcd`'s logarithmic Euclid unroll *could* be
  active and sound over [0,64], but there is no demand for it.)
- **Wrong lever.** Like Tier B, this is band-widening; the binding constraint is prover reach
  (ADR 0028/0029), not the faithfulness band.

**Decision: shelve Tier C.** Do not implement; keep the functions forbidden in the conjecturer
DSL. Revisit only if a future conjecture mix genuinely produces `gcd`/`factorial` claims that
DEFER for lack of an encoding — and even then, only `gcd` looks both sound and active at the
production bound.

## Soundness argument

- `min`/`max`: `If(a<b,a,b)` is definitionally `min` over ℤ — exact, unconditionally.
- Symbolic exponent: the If-chain enumerates the **complete** domain of `e` in the box, each
  arm exact (constant-power expansion). No arm omitted ⇒ no missed witness ⇒ UNSAT is genuine.
  The cap only ever makes the gate DEFER (safe), never pass.
- Tier C: each is an exact finite computation over its capped range, cross-checked against the
  Python reference on the entire box in tests; outside the cap it DEFERs. The Euclid unrolling
  emits a "converged?" flag and DEFERs if not converged, so a too-shallow unroll can never read
  as a decided UNSAT.

The residual is the same bounded-search limitation as today (a witness beyond `bound` is
missed) — unchanged. Every new path's failure mode is DEFER, never wrong-UNSAT.

## Security

`ast.Call` stays rejected by default. The handler whitelists **only** the bare names above
(`min`, `max`, `gcd`, `factorial`, `nat_log`/`Nat.log`), each with a fixed arity and
integer-only args; attribute calls (`x.foo()`), keyword args, starred args, and any other name
all still raise `PredicateError`. No `eval`, no `__import__`, no dynamic dispatch. `MAX_NODES`
still bounds AST size against recursion on untrusted input.

## Consequences

- The gate certifies a broader, still-elementary band (exponential-growth divisibility,
  gcd/lcm identities, min/max bounds) instead of DEFERring it — more of what the conjecturer
  naturally proposes becomes promulgatable, *if* the prover can also close it.
- The conjecturer DSL prompt (ADR 0022) gains the new constructs so it steers INTO them.
- Strictly additive: anything not in the whitelist/caps DEFERs exactly as before. Trust
  posture preserved; `gates/` and the invariant tests untouched.

## Validation plan

- **Unit (CI-safe):** per construct, a property test that the Z3 encoding equals the Python
  reference (`min`/`max`/`math.gcd`/`math.factorial`/integer log) across the entire box; plus
  the DEFER cases (over-cap, compound exponent, non-whitelisted call, attribute call) all raise
  `PredicateError`; plus an explicit wrong-UNSAT regression (a true-everywhere claim using each
  construct must PASS, a false-somewhere one must produce a SAT witness).
- **Adversarial soundness review** (ADR 0021 precedent: ≥3 lenses, each finding independently
  verified) before merge — the bar for anything that can turn into a PASS.
- **Live:** a calibration after ADR 0022's prompt gains the constructs — does the DEFER
  fraction drop further without any new vacuous PASS (audit every promulgation)?

## Open questions

- **Per-variable bound clamping vs whole-predicate DEFER** for Tier B: clamping the exponent
  variable to `MAX_SYM_EXP_BOUND` while leaving other variables at `bound` changes the search
  box non-uniformly — is that still a sound "no witness in the box" statement, or should the
  whole predicate DEFER when any exponent variable's bound would exceed the cap? (Leaning DEFER
  for clarity; revisit if it over-rejects.)
- Whether Tier C earns its keep at all, given prover reach (not the band) is the live blocker —
  ship Tier A + B, measure, and only do Tier C if the conjecture mix actually needs it.
