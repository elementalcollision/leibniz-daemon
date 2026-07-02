<!--
Follow-up to PR #231 (D6 solve-leg fix): kernel-attest the two new exact certificates it banked.
Audit/measurement only; no trust touch; tests/test_invariants.py byte-identical.
-->

# Terwilliger kernel bank — the two D6 certificates are kernel-attested (2026-07-02)

PR #231 produced two new exact-rational certificates through `certify_lp` at P=1e14 — **A(23,6) ≤ 13766**
(Table I, previously the probe's CLARABEL-crash cell) and **A(25,10) ≤ 503** (Table I, the first d≥10
certificate) — dual_check-validated but with their kernel legs not yet run. This session ran them.

## Verdict: **GREEN** — 2/2 sound; both now sit at the same kernel-attested tier as A(19,6) ≤ 1280

| certificate | exact bound (floor) | blocks | kernel: valid cert | kernel: corrupted control | total |
|---|---|---|---|---|---|
| **A(23,6) ≤ 13766** | 688309497034285983/50000000000000 (13766) | 24, largest 24×24 | **True** | **False** ✓ | 124 s |
| **A(25,10) ≤ 503** | 50378865077422117/100000000000000 (503) | 26, largest 26×26 | **True** | **False** ✓ | 123 s |

The real Lean 4.31 kernel verified every PSD block of each certificate (per-block theorems,
`maxHeartbeats 0`) and rejected the corrupted-block control both times. A(25,10) ≤ 503 is the repo's
**first d≥10 kernel-attested certificate** — the d≥10 leg that the reach probe flagged as unvalidated is
now validated end-to-end: SDPA-GMP float → exact-rational LP → dual_check → kernel.

## Change

`kernel_verify_lp` now forwards `precisions`/`time_cap_s` to `certify_lp` (the D6 cells certify only at
P=1e14, above the default ladder — without the passthrough the kernel leg could never reach them; a free-CPU
test guards the forwarding). Harness: `scripts/terwilliger_kernel_bank.py` (regenerates
`docs/results/terwilliger_kernel_bank.json`, ~4 min operator-local, needs cvxpy+sdpap+docker).

## Trust

Audit tier unchanged (`DUAL_CERTIFICATE_CHECKED`, now kernel-attested for three cells). Floats remain
targeting data; the deciders are the exact-rational LP + the kernel. No trusted surface touched;
`tests/test_invariants.py` byte-identical.
