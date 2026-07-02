# ADR 0011 — Proving Throughput & Cost Governance (Proposed)

- Status: **Accepted** (fully implemented 2026-06-21 — concurrency, cost cap,
  cross-cycle cache, thread-safe persistent container, **and the Lean REPL backend**
  all landed and wired)
- Date: 2026-06-21
- Related: ADR 0003 (Lean backend), ADR 0006 (consensus proving);
  `backends/lean_cli.py`, `backends/lean_repl.py`, `docker/lean-repl.Dockerfile`,
  `consensus.py`, `assembly.py`. Non-guarded. Roadmap #4.

## Context

Measured in the live runs: each Lean check is ~1.3 s (Mathlib oleans reload per
`lake env lean` invocation), the N+1 consensus provers run **sequentially**, there
is no cross-cycle result cache, and there is no spend cap on a deliberately costly
("even if costly") consensus proof. Once ADR 0009 produces candidates at volume,
the proof stage dominates wall-clock and cost.

## Decision (proposed)

1. **Persistent Lean container.** `LeanCliBackend(persistent=True)` keeps one
   container alive and uses `docker exec` per check — removes ~25% per-check
   container churn. Made thread-safe (a lock guards container creation + the
   scratch-file counter; the `docker exec` runs outside the lock) so it composes
   with the concurrent ensemble.
2. **Lean REPL backend (the big win).** A long-lived `leanprover-community/repl`
   process (`docker/lean-repl.Dockerfile` → `leibniz-lean-repl:v4.31.0`) with the
   candidate's import set preloaded into a REPL *environment*, so Mathlib loads
   ONCE per import-set instead of per check. `LeanReplBackend` implements the same
   `LeanBackend` protocol (JSON line protocol over stdin/stdout, env cached per
   import-set, I/O serialized under a lock); the assembly prefers it for the
   consensus discharge path and falls back to the CLI backend when the image is
   absent or `LEIBNIZ_LEAN_REPL=0`. **Measured 3x on a 4-check Mathlib batch**
   (2.0s vs 6.0s), and the gap widens as more checks amortize the single load.
3. **Concurrent prover ensemble.** Run the consensus provers' drafts + discharges
   concurrently (threads/async) instead of sequentially — N-way speedup on proof.
4. **Cross-cycle result cache.** Persist the structural-hash-keyed result cache so
   identical statements/proofs are never re-checked across cycles.
5. **USD budget cap.** A token-based spend estimator + `LEIBNIZ_DAILY_USD_CAP`;
   stop the cycle when the cap is hit; surface spend in `CycleReport` (mirrors
   Leonardo's `LEONARDO_DAILY_USD_CAP`).

## Options considered

- Persistent container vs REPL: do both — container is cheap and immediate; the
  REPL is the real throughput lever but more work. Cache + concurrency are additive.
- Budget as a hard stop vs advisory: **hard stop** (consensus is costly by design).

## Consequences

- Lower `$ / promulgation` and wall-clock; sustained autonomous runs become
  affordable and bounded.
- Soundness unaffected — these are performance/cost mechanisms; the kernel + N+1
  consensus still decide (ADR 0001/0006). The REPL backend only *reports* the
  kernel's verdict (no errors + no `sorry` ⇒ verified); `LeanVerifier.discharge`
  remains the sole `kernel_verified` writer (CLAUDE.md inv. 1), so the proof edge
  is `MECHANICAL` regardless of which backend ran the check. All non-guarded.
- Throughput/serialization trade-off: the REPL is a single stdin/stdout stream, so
  its checks serialize under a lock. The ensemble's LLM *proposals* still run
  concurrently (the slow part); only the now-fast kernel checks serialize. Net win
  because each check no longer reloads Mathlib.

## Open questions

- REPL crash/restart handling and per-import-set process pooling (current backend
  degrades to conservative `False` on a dead process; the assembly's CLI fallback
  covers a missing image, not a mid-run crash).
- Spend estimation accuracy across Anthropic vs OpenRouter pricing.

## Amendment (2026-07-02) — silently-broken umbrella import

**Defect.** `lake exe cache get` ships per-module oleans but NOT the umbrella
`Mathlib.olean`, so `import Mathlib` — the pipeline's *default* import set
(`pipeline._parse_expressio`) — failed on both backends: loudly under
`lake env lean` ("object file … of module Mathlib does not exist"), and
**silently** in the repl, which swallows a failed import and answers
`{"env": N}` with no error messages. The resulting env is coreless (even
`example : 1 = 1 := rfl` dies with ``Unknown constant `OfNat` ``); `_env_for`
cached it, so every Mathlib-defaulted check fail-closed for the process
lifetime with misleading diagnostics. No soundness impact (fail-closed), but
Mathlib proposals could never verify via the repl backend.

**Fix (both layers).**
1. `docker/lean.Dockerfile` now runs `lake build Mathlib` after `cache get`
   (~15 s warm; also fills in the missing `Batteries.olean`), so the umbrella
   works in the base image (CLI backend) and the repl image layered on it.
   Operators must rebuild both images (base first, then the repl image).
2. `LeanReplBackend._env_for` probes every freshly created env with a
   core-prelude, ASCII-only canary (`example : (1 : Nat) = 1 := rfl`) before
   caching. A failed canary marks the env broken → `None` (the same
   conservative fail-closed path as an unavailable backend), never a poisoned
   cache. This guards against stale images and any future repl
   swallowed-import behavior.

The pipeline default stays `("Mathlib",)`: with the umbrella built it is the
right maximal-coverage default for proposals that omit imports, and its
one-time load cost is exactly what the env cache amortizes. Regression tests:
`tests/test_lean_repl_broken_env.py` (fake repl, CI-safe) and the umbrella /
swallowed-import cases in `tests/test_lean_repl_r0011.py` (docker-gated).
