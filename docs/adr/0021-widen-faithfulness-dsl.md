# ADR 0021 — Widen the faithfulness DSL (soundly) (Accepted)

- Status: **Accepted** (implemented 2026-06-22)
- Date: 2026-06-22
- Related: ADR 0002 (faithfulness gate), ADR 0004 (structured contract), ADR 0020
  (refuse vacuous passes — exposed this as the binding blocker).
  `leibniz/backends/smt_z3.py`. Non-guarded. Roadmap: Tier 1 (faithfulness).

## Context

ADR 0020 made the faithfulness probe honest: it DEFERs unless the structured contract
is encodable in the SMT DSL. That exposed the **DSL as the binding discovery
blocker** — it was single-variable arithmetic (`n`, `+ − *`, comparisons), so nearly
every real conjecture (multi-variable, powers, mod) DEFERred *before proof*. The
faithfulness gate couldn't certify the very claims the daemon proposes.

## Decision

Widen the DSL — but only with constructs Z3 can decide **soundly** over a bounded
box, because a wrong "no witness" (UNSAT) would be a vacuous PASS again (the exact
thing ADR 0020 closed). Added:

- **Multiple variables** — any identifier becomes a non-negative integer var, created
  on demand and bounded `[0, bound]`; predicates in one search share a namespace
  (so `a` means the same `a` in `statement` and `negated_claim`).
- **Constant-exponent power** (`^`/`**`) — expanded to repeated multiplication
  (`n^3 → n*n*n`), capped at `MAX_POW`. No symbolic Power term.
- **Constant-positive `/` and `%`** — floor division / modulo by a literal `> 0`.

Deliberately **still DEFER** (raise `PredicateError` → "no witness" → the ADR 0020
probe DEFERs): symbolic exponents (`2^n`), function calls (`Nat.log(...)`, also the
security guard against `__import__`/`open`), and variable/zero divisors. These are
not soundly encodable here, so the gate refuses to certify them rather than guess.

## Soundness argument

Every accepted construct has an exact Z3 integer encoding over `[0, bound]`:
multi-variable linear/nonlinear arithmetic, repeated multiplication for constant
powers, and `div`/`mod` by a positive constant (floor semantics, matching ℕ for
non-negative operands). So `UNSAT` genuinely means "no witness in the box" and `SAT`
genuinely exhibits one — the gate's PASS/GAMED verdicts rest on real checks. The only
residual is the bound itself (a witness beyond `bound` is missed), which is the
pre-existing bounded-search limitation, unchanged. Un-encodable constructs raise and
DEFER, never silently UNSAT.

## Soundness-review hardening (8 findings, all fixed)

An adversarial soundness review (3 lenses, each finding independently verified)
caught a **critical** wrong-UNSAT and several ways an undecided/malformed search
could become a vacuous PASS or a gate crash. All fixed before merge:

- **CRITICAL — `^` precedence.** Python parses a bare `^` as BitXor, which binds
  *looser* than `*`/`/`, so `n*2^0` parsed as `(2n)^0 = 1` (true everywhere) → a
  vacuous PASS that hid an `n=0` coverage gap. Fixed by rewriting `^`→`**` *before*
  parsing, so it gets exponentiation precedence; `ast.BitXor` is no longer treated as
  power.
- **`unknown` ≠ UNSAT.** A search is now tri-state (`decide_unsat` → True/False/None);
  z3 `unknown` (with an explicit per-search **timeout**) returns None, and the probe
  certifies **only on conclusive UNSAT** of *both* coverage and no-gaming. An
  undecided or timed-out search DEFERs — it never reads as "no witness".
- **Crash-safety.** Non-boolean predicates (`n + 1`), deeply-nested input
  (RecursionError, capped by `MAX_NODES`), and Z3 errors all degrade to "error" →
  DEFER, never escaping the gate. `encodable` requires a boolean result.

The net posture is unchanged in spirit and stronger in fact: certify only what is
conclusively, soundly checked; DEFER everything else.

## Consequences

- The faithfulness gate now genuinely certifies multi-variable / constant-power /
  modular conjectures — the bulk of what the daemon proposes — instead of DEFERring
  them. This unblocks the path from conjecture to honest proof.
- Trust posture preserved: only sound encodings; everything else DEFERs; the security
  whitelist (no `eval`, `ast.Call` rejected) is intact; `gates/` untouched;
  `tests/test_invariants.py` byte-identical.

## Open questions

- Symbolic exponents (`2^n`) and named functions (`Nat.log`, `factorial`, `gcd`) are
  still beyond the gate — a bounded definitional encoding (or a different faithfulness
  mechanism) could bring them in, the next increment.
- With faithfulness now certifying real conjectures, the deeper live calibration
  (ADR 0019) becomes meaningful — proving reach is the next thing to measure.
