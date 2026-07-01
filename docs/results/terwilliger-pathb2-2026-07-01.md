<!--
Path B2: the A(19,6) <= 1280 exact certificate is now KERNEL-ATTESTED. The "scaling wall" was a render
artifact (one giant decide conjunction), not block content. Operator-local (cvxpy + docker). No trust surface
touched; tests/test_invariants.py byte-identical. Audit-tier.
-->

# Terwilliger three-point — Path B2: the A(19,6) certificate is kernel-attested (2026-07-01)

Path B2 closes the last open leg of the "all three" program: the **real Lean 4.31 kernel now verifies the
A(19,6) ≤ 1280 certificate's PSD content** — all 20 blocks accepted, a corrupted block rejected.

## The diagnosis (the wall was the render, not the content)
The earlier n=19 kernel failure (`valid_cert=False`, ~9 s) was a **resource artifact, not a rejection**:
`render_cert_lean` put all 20 blocks into ONE `decide` over a giant `&&` conjunction, which exceeded the
elaborator's budget — and `check_source` reports any elaboration failure as False (the same
resource-error-misread-as-rejection trap as the GATE-2 `maxRecDepth` incident). Measured with raw diagnostics:
- the **largest single block (20×20, scale ≈ 2113 bits) verifies `ldltOK = true` in ~5 s as-is** —
  the block content was never the problem (no Bareiss/`native_decide` needed);
- all 20 blocks as **separate theorems** (one source, `set_option maxHeartbeats 0`): **True in 16 s**;
- the corrupted-block control: **False in 13 s** (the whole file fails if any theorem fails).

## The fix
`render_cert_lean` now emits **one theorem per block** (+ `maxHeartbeats 0`). Soundness is identical: the
source elaborates cleanly iff *every* block's `decide` succeeds. `terwilliger_exact_lp.kernel_verify_lp`
runs the exact-LP certificate through this render, and `main()` records the A(19,6) kernel verdict.

## Result (measured, this machine)
| leg | verdict | time |
|---|---|---|
| exact LP certificate A(19,6) | certified, ⌊Σγ−ν⌋ = **1280** | ~17 s |
| kernel: 20 valid PSD blocks (largest 20×20) | **True** | ~16 s |
| kernel: corrupted block control | **False** | ~13 s |

Small cells (Phase 2b/`terwilliger_cert.py`) stay GREEN under the new render. Guarded by
`tests/test_terwilliger_exact_lp.py::test_kernel_attests_a19_6_certificate_and_rejects_bogus` (docker-gated).

## Scope / what remains
The kernel attests the **PSD content** of the certificate (the kernel-nontrivial part); the stationarity
system + bound arithmetic are exact-rational Python (`dual_check`). Remaining rungs, both known and scoped:
- **stationarity-in-Lean** (D3's "kernel recomputes S_k from β" in full) — moves the whole certificate check
  into the kernel;
- **the bridge theorem** (formalize the Terwilliger reduction) — the charter step that would lift
  `DUAL_CERTIFICATE_CHECKED` to Q.E.D.

Audit-tier throughout; no trusted surface touched; `tests/test_invariants.py` byte-identical.
