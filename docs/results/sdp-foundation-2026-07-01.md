<!--
SDP three-point FOUNDATION build (multi-agent workflow, Sonnet 5 build agents + adversarial verify).
Audit-tier; no trust touch; tests/test_invariants.py byte-identical (11/11). READY-TO-COMMIT per the
adversarial verifier and an independent re-run.
-->

# SDP three-point — foundation build + pre-validation (2026-07-01)

Built by a multi-agent workflow (two Sonnet 5 build agents in parallel → adversarial verify → external-brief
draft). Both builds passed an adversarial re-run and an independent spot-check (6 new files, no protected file
touched, ruff clean, 33 new+invariant tests pass, full suite 903 passed / 1 skipped). **Audit-tier: the Lean
kernel is the sole decider; a wrong solver/rounding can only produce a certificate the kernel rejects.**

## What was built
- **`scripts/bareiss_ldlt.py`** — the compute-trap mitigation (external critique #2). A fraction-free
  (Bareiss) integer factorization yielding a kernel-checkable PSD certificate whose bit-length is
  minor/determinant-bounded, in two forms: (a) integer `L, d≥0, scale` reusing `ldltOK` verbatim; (b)
  Sylvester leading-principal-minors > 0, kernel-checked by a new core-Lean `detSignOK` that **recomputes
  the Bareiss minors from M itself** (does not trust the producer's minors). Measured bit-length (naive →
  Bareiss): 944→447 (n=6) … **30,773→10,982 (n=30)** — 2.1×→2.8× on form (a); the underlying minors are
  130→717 bits (much smaller), so form (b) is the cheaper PSD yes/no certificate. Kernel-verified (valid
  accepted, bogus rejected) both forms at n=6/10/14.
- **`scripts/sdp_code_bound.py`** — pre-validates the real code-SDP → dual → rational-cert → kernel chain
  (the irrationality gate used ϑ-of-cycles as a proxy; this uses actual confusability-graph SDPs). Full-graph
  Lovász ϑ via cvxpy/SCS → Strict-PD (+εI) rational Cholesky → kernel. **Reproduced A(4,2)=8, A(4,4)=2,
  A(5,2)=16, all kernel-verified**, bogus rejected, cross-checked against the Delsarte-LP probe's own certs.

## Two findings that shape the Terwilliger build
1. **The kernel checker walls at matrix dimension N ≈ 32–64** (naive core-Lean List matmul is O(N⁴), a
   *separate* wall from bit-length). So the three-point dual **must be checked block-by-block** — largest
   block ~(n+1)×(n+1) after the Terwilliger reduction, never the 2ⁿ ambient matrix. The reduction is
   essential for the *kernel check*, not just the solve. (This is the brief's #1 question, Q-pit-1.)
2. **Plain full-graph Lovász ϑ can be *weaker* than the Delsarte LP** — A(8,5): ϑ floors to 6 vs the true 4.
   So the three-point / Terwilliger bound must **include the LP (Krawtchouk) constraints** to dominate LP by
   construction; the k=0 Terwilliger block should reproduce the Delsarte LP exactly.

## Status
Foundation GREEN and committed. The remaining hard piece — the **Terwilliger three-point block-
diagonalization** — is scoped for external guidance (`docs/external-brief-terwilliger-threepoint-2026-07-01.md`),
which also flags that the illustrative target **"A(12,5) 40→32" is unverified** (not found in Schrijver's
tables; confirmed alternatives offered) and must be corrected before any build. Both prior gates remain GREEN
(mechanism #212, irrationality-margin #214). Needs cvxpy (operator-local) + docker.
