<!--
Tier 2 (docker-local) results — the spine-hardening gates (GATE-4 soundness backstop, GATE-2 covering
decide-wall, GATE-5 continuous guard). Run on a machine with docker + leibniz-lean:v4.31.0. Audit/
measurement only; the one code change (covering_verify maxRecDepth) is a sound resource limit, not a trust
edit; tests/test_invariants.py byte-identical.
-->

# Tier 2 results — amplification-spine hardening (GATE-4 / GATE-2 / GATE-5, 2026-06-30)

With the D-line banked, Tier 2 hardens and bounds the **amplification spine** (the product). All three
active gates ran on the real Lean 4.31 kernel. **No soundness hole; one real completeness bug found and
fixed; the spine is now sound, bounded, and continuously guarded.**

## GATE-4 — soundness backstop: **GREEN**
`tests/test_kernel_false_theorem_rejection.py` on the real kernel: **20/20 well-formed FALSE theorems
REJECTED, 10/10 TRUE theorems ACCEPTED**, across covering / CWC / Ramsey (22 tests pass). Every false case
is built from the same locked prelude + `validX … = true := by decide` template as the renderer, so a
`False` is the kernel disproving a false *claim*, not a compile error (the TRUE controls prove the templates
compile). **"Nothing false is ever KERNEL-VERIFIED" holds across a broad adversarial corpus.**

## GATE-2 — covering decide-wall: **MEASURED (+ a completeness bug fixed)**
The probe (`scripts/covering_kernel_wall_probe.py`) first reported a **SOUNDNESS ALARM** — the kernel
"rejecting" valid t≥3 witnesses. Investigation of the raw output showed the true cause:

```
error: maximum recursion depth has been reached — use `set_option maxRecDepth <num>` to increase limit
```

This is **not a rejection**. Lean's default `maxRecDepth` (512) is exceeded while `decide` reduces the
t-subset enumeration for t≥3, and the elaboration error was reported by `check_source` as `False`, which the
probe misclassified. Two fixes:
- **`render_covering_lean` now sets `maxRecDepth` (100000)** — a pure resource limit (it cannot make
  `decide` accept a false proposition; GATE-4 still holds with it raised), so a *valid* t≥3 covering now
  reduces to completion. This is a real **completeness fix**: covering t≥3 kernel-checks (via `covering_check`
  and the amplification spine) previously **silently errored**; they now verify.
- The probe now classifies the raw output — `intractable(maxRecDepth/heartbeats/timeout)` = the resource
  WALL, vs `DECIDE-FALSE` = a genuine rejection (the only thing that raises a soundness alarm; it stayed
  empty).

**Re-run with the fix — the real wall (per-cell 60 s, near-minimal CP-SAT witnesses):**

| cell | C(v,t) | blocks | kernel | wall |
|---|---:|---:|---|---:|
| C(7,3,2)…C(20,4,2) (t=2) | ≤190 | ≤37 | verified | ≤1.3 s |
| C(12,4,3) | 220 | 59 | verified | 1.4 s |
| C(14,4,3) | 364 | 102 | verified | 3.3 s |
| C(16,5,3) | 560 | 79 | verified | 3.4 s |
| C(18,5,3) | 816 | 120 | verified | 5.9 s |
| **C(20,5,3)** | **1,140** | **169** | **verified** | **10.9 s** |
| C(15,4,4) | 1,365 | 1365† | intractable(heartbeats) | 8.4 s |

†all-k-subsets fallback (CP-SAT found no smaller covering in the 15 s witness budget), so this rung is
confounded by a huge witness, not C(v,t) alone. **No `DECIDE-FALSE` anywhere → no soundness alarm.**

**GATE-2 disposition:** with `maxRecDepth` raised, covering `decide` verifies comfortably across the
realistic amplification band — up to **C(v,t) ≈ 1,140 and ~170 blocks in ~11 s**. The wall beyond that is
the `decide` reduction *cost* (heartbeats/time), not recursion depth. **No `RENDER_SUBSET_CAP` is required
for near-minimal witnesses in this range** (unlike Ramsey, whose predicate is exponential — Gate B2); only
very large cells or non-minimal (all-subset) witnesses time out, which is honest and expected. The covering
amplification spine is bounded and honest as-is across its working range.

## GATE-5 — continuous guard: **GREEN**
- **Full soak** (`scripts/run_kernel_soak.sh`, kernel present): **861 passed, 1 skipped, 0 failed** in
  185 s. The single skip is the live-`ANTHROPIC_API_KEY` test; the skip-count guard (`--max-skips 3`)
  passes with baseline 1 — so a gate silently turning into a no-op (skip count jumping) would now fail the
  soak.
- **Strict zero-skip lane** (`scripts/run_kernel_tests.sh`, widened with GATE-4): **34 passed, 0 skipped.**
- The audit-tier "nothing false is KERNEL-VERIFIED" guarantee is now exercised on every render→kernel path
  and continuously guardable (locally or via the self-hosted `lean` nightly).

## Net
The post-D0 validation arc is complete. The amplification spine is:
- **sound** — the kernel rejects every false bound across covering/CWC/Ramsey (GATE-4);
- **bounded + more complete** — the covering decide range is measured (~C(v,t) 1,140 / ~170 blocks), and the
  `maxRecDepth` fix makes t≥3 coverings kernel-checkable for the first time (GATE-2);
- **continuously guarded** — full soak + skip guard + widened strict lane (GATE-5).

No trust-core change; `tests/test_invariants.py` byte-identical. DEFERRED with the proof-edge: the GATE-3
cluster (degenerate-cell battery, domain-guard prototype, non-promoting ConstructionVerifier).

Artifacts: `docs/results/covering_kernel_wall.json`. Harnesses: `tests/test_kernel_false_theorem_rejection.py`,
`scripts/covering_kernel_wall_probe.py`, `scripts/run_kernel_soak.sh`, `scripts/run_kernel_tests.sh`.
