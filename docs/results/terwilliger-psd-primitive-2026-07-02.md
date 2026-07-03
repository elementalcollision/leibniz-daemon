<!--
"Best solver possible" push after GATE 0: a stronger kernel-checkable PSD certification primitive + the
measured ceiling study behind it. Audit/measurement only; no trust surface touched; the primitive is a strict
sound generalization of the shipped ldltOK; tests/test_invariants.py byte-identical.
-->

# The kernel-PSD certification primitive — ceiling study + a stronger primitive (2026-07-02)

GATE 0 showed the GMS quadruple build dies at the **kernel-PSD-certification wall** (blocks O(n²), order
130–414, past the ~26 the current checker handles). The generalizable question — the one that matters for
*any* large-block SDP the daemon might attest — is: **how far can a sound, kernel-checkable PSD certificate
actually reach, and what is the best primitive?** This study measures it and ships the best available answer.

## Measured: the wall is the `decide` reduction, not heartbeats or source size

Benchmarking the current `ldltOK` primitive (`L·diag(d)·Lᵀ == s·M`, kernel-checked by `decide`) with
`maxHeartbeats 0`:

| primitive | N=26 | N=30 | N=36 | N=50 | N=60 |
|---|---|---|---|---|---|
| **current full-rank `ldltOK`** | 11.1 s / 208 KiB | 17.8 s / 377 KiB | 47.6 s / 819 KiB | (blows up) | — |
| **low-rank Gram (r=8) + col-scale** | — | 1.9 s / 5 KiB | — | 42.2 s / 11 KiB | **85.7 s / 16 KiB** |

Two findings:
1. The earlier "wall at N≈26" was partly a **`maxHeartbeats 200000` artifact** — with heartbeats disabled the
   current primitive reaches ~N=36–40 (48 s), and the true wall is the **raw kernel `decide` reduction cost**
   of the nested-`List` matmul (heartbeat- and source-size-independent — an N=60 case with tiny 16 KiB source
   still costs ~86 s of pure reduction). This is Kimi's "term-reduction is the killer" prediction, confirmed.
2. `decide` is **fundamentally superlinear** here; arithmetic optimization buys a constant/rank factor, not a
   new order. **N ≫ 60 is unreachable by any `decide`-based check** — including for the GMS blocks.

## Shipped: the low-rank Gram primitive `lowRankOK` (`scripts/terwilliger_psd_lowrank.py`)

A **strict, sound generalization** of `ldltOK`, chosen as #1 by a 3-angle research survey (factorization /
dominance-Schur / formal-verification literature) + synthesis:

```
lowRankOK M U d s  :=  0 < s  ∧  d.all(≥0)  ∧  (colScale U d) `gram` U == s·M
```
— U an N×r integer thin factor, `colScale` scales U's columns by d (never materializes the N×N `diag(d)`), and
`gram` is the single O(r·N²) matmul. **Soundness is identical to `ldltOK`**: the identity + d≥0 + s>0 make
`M = (1/s)·Σₖ dₖ (U·k)(U·k)ᵀ` a nonnegative combination of rank-1 PSD terms ⟹ M ⪰ 0; the kernel **recomputes**
the matmul and **never trusts the claimed rank** (fewer columns → fail-closed, never false-accept). `r=N`
recovers `ldltOK` exactly. Kernel-attested: the real Lean 4.31 kernel accepts a valid low-rank cert and rejects
a corrupted one (`sound=True`; gated test `tests/test_terwilliger_psd_lowrank.py`).

**Two measured wins, both real:**
- **Low rank** (SDP dual blocks are low-rank at the optimum — complementary slackness; our A(19,6) dual is
  55/4621 sparse): O(r·N²) not O(N³) → **~2× the N ceiling (~40 → ~60+) and ~50× smaller source** at r=8.
- **Column-scale fusion**: one matmul, no `diag(d)` materialization — an unconditional ~2× even at r=N, so it
  helps *every* block including the current three-point ones, and shrinks the certificate.

## Honest scope — what this does and does not do

- **It does NOT rescue GMS-quadruple.** Even O(r·N²) with the fusion, N=130–414 is out of `decide` reach
  (N=60 already costs ~86 s; cost ∝ N²·r), and GMS blocks are not guaranteed low-rank. **GATE 0's RED stands.**
- **It DOES make the core primitive strictly better** for the three-point / low-rank regime and reduces
  certificate bit-length (thin factor over the Bareiss pivots, `scripts/bareiss_ldlt.py`) — a real solver
  improvement that every current and future cell benefits from, at zero trust cost.
- **The one lever that could break `decide`** (to reach N ≫ 60): stop asking the kernel to *reduce* a giant
  `List` equality and instead **generate an explicit proof term** (or chunk the identity to per-row/per-entry
  decidable checks the kernel reduces cheaply). That is a separate, larger research bet — the honest "best
  solver" frontier — and it, not more arithmetic, is where N-scaling lives. Recorded here as the next probe.

## Provenance

Research: a 3-agent survey (factorization; diagonal-dominance/Schur; the formal-verification literature —
verified Cholesky/LDLᵀ, SOS/Positivstellensatz, ValidSDP/CoqInterval) + synthesis, which ranked the low-rank
Gram form #1 and reframed the target away from the dead GMS N=414 regime. Cross-checked against the shipped
`bareiss_ldlt.py`, `psd_certificate_microprobe.py`, and the F1/GATE-0 measurements. Harness + primitive:
`scripts/terwilliger_psd_lowrank.py` (`docs/results/terwilliger_psd_lowrank.json`); test:
`tests/test_terwilliger_psd_lowrank.py`. No trusted surface touched.
