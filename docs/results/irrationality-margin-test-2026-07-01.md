<!--
Revised SDP gate — the irrationality-margin test (external critique #213, risk #1). Isolates the
irrationality wall via Lovász-ϑ SDPs with genuinely irrational optima. Audit/measurement; no trust touch;
tests/test_invariants.py byte-identical.
-->

# Irrationality-margin test — the revised SDP gate: **GREEN (in proxy)** (2026-07-01)

The external agent's PRIMARY, previously-untested SDP risk (95% confidence it is fatal): SDP optima are
algebraic-irrational, so a rational PSD dual certificate over-approximates, and with the εI/rounding margin
`⌈bound⌉` overshoots the target integer → cannot certify a tightening. This gate isolates that question
**without** building the full Terwilliger three-point SDP (the gated build), using the Lovász theta ϑ(G) — a
real SDP whose optimum is genuinely irrational for odd cycles (ϑ(C₅)=√5).

## Method
Dual ϑ SDP `min t s.t. Z := t·I − J + Σ_{ij∈E} y_ij·E_ij ⪰ 0` ⟹ `α(G) ≤ t` (= ϑ at optimum). An untrusted
solver (cvxpy/SCS) proposes `(t, y)`; we round `y` to rationals, find the smallest rational `t*` making
`Z(t*)` exactly PSD (strict-PD rational Cholesky), clear denominators, and **kernel-check** `Z(t*) ⪰ 0` via
the integer LDLᵀ checker from the exact-PSD micro-probe (#212). Soundness rests only on the kernel check.

## Result — GREEN
| graph | α | ϑ (irrational) | rational cert bound | **irrationality tax** | cert bits | ⌊bound⌋=α? | kernel |
|---|---:|---:|---:|---:|---:|:--:|:--:|
| C₅ | 2 | 2.236068 (√5) | 2.238 | **0.0019** | 150 | ✅ | True |
| C₇ | 3 | 3.317667 | 3.319 | **0.0013** | 478 | ✅ | True |
| C₉ | 4 | 4.360090 | 4.362 | **0.0019** | 827 | ✅ | True |
| C₁₁ | 5 | 5.386303 | 5.388 | **0.0017** | 1444 | ✅ | True |

**4/4 certify the tight integer α despite an irrational optimum; achievable irrationality tax ≈ 0.001–0.002**
(well below the 0.01 threshold); every certificate **kernel-verified** on the real Lean 4.31 kernel.

## What this means (and its honest limits)
- **The irrationality wall is surmountable.** A kernel-checked *rational* PSD certificate floors to the
  correct integer even when the SDP optimum is irrational, and the tax it pays is **~0.002**, not stuck-large.
  So a narrow code-cell margin down to ~0.002 is reachable — the agent's #1 risk **does not bite** in this
  proxy. This materially downgrades the 95%-fatal estimate.
- **Proxy caveat.** This is odd-cycle ϑ, not the code three-point SDP. The irrationality *mechanism* is
  identical (irrational optimum + rational cert), so it is a strong signal, but the specific open-code-cell
  margin `⌈optimum⌉ − optimum` is only measurable once the three-point SDP is built — a chicken-and-egg the
  gate cannot fully remove.
- **Compute trap (#2) reconfirmed, mild here.** Bit-length grows 150→1444 (n=5→11) with naive rational
  Cholesky; fine at these sizes. At Terwilliger scale, **Bareiss fraction-free elimination** remains the
  required technique (measured separately, `psd_scaling_probe.py`).

## Gate status — both SDP gates now GREEN
1. **Mechanism** (#212): exact-PSD kernel-checkable certificate + float→exact rounding — GREEN.
2. **Irrationality margin** (this): rational certs floor correctly despite irrational optima, tax ~0.002 —
   GREEN (proxy).

The residual unknowns are ordinary engineering + one measurement that requires the build itself: (a) an SDP
solver + Terwilliger three-point formulation, (b) Bareiss for scale, (c) the actual open-code-cell margin.
None is a novel-soundness risk.

## Recommendation
The revised gate clears the risk that most threatened the SDP bet. **Proceed to the three-point SDP build is
now justified** — with Bareiss for bit-length and the actual-margin measurement as the first in-build
checkpoint (reproduce A(12,5), then a non-tight cell). Alternatively, bank both GREEN gates and commit the
build later; the LP certificate product stands regardless.

Needs: cvxpy (operator-local) + docker. Artifact: `docs/results/irrationality_margin_test.json`. Harness:
`scripts/irrationality_margin_test.py`. Test: `tests/test_irrationality_margin.py`.
