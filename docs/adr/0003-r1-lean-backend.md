# ADR 0003 — R1 Lean Backend, Container Split, and Kernel-Online Sequencing

- Status: Accepted
- Date: 2026-06-21
- Related: ADR 0001 (trust hierarchy), ADR 0002 (faithfulness gate); capability
  ladder R1; HANDOFF §6 (the `LeanBackend` seam).

## Context

R1 brings the real Lean kernel online behind `verifiers.LeanBackend`
(`compile_statement` / `check_proof` / `closed_by_decision_procedure`). Three
forces constrain how:

1. **LeanDojo caps at Python `<3.12`** and its *interactive* proof-state Dojo is
   Linux-favored with no Apple-Silicon guarantee. The Leibniz daemon core is pure
   stdlib and runs fine on the host's Python 3.14.
2. We run **OrbStack** locally (Docker-compatible), so a Linux container for the
   Lean toolchain is cheap and reproducible.
3. R1 only needs to verify *complete* proofs in batch (true→`Q.E.D.`, false→
   `UNPROVEN`, tautology→`TRIVIAL`). It does **not** yet need to step proof states
   — that is an R4 need (prover-class models drafting tactics).

## Decision

**1. R1 backend = Lean CLI in a pinned container, not LeanDojo.**
`leibniz.backends.lean_cli.LeanCliBackend` shells out to `lake env lean <file>`
inside `leibniz-lean:v4.31.0` (built from `docker/lean.Dockerfile`; Lean pinned via
`lean-project/lean-toolchain`). It reads the kernel's diagnostics in batch.
**LeanDojo (interactive stepping) is deferred to R4**, when it is actually needed;
this also sidesteps the documented interactive-Dojo instability on Apple Silicon.

**2. Host/container split.** The daemon stays on host Python **3.14+** (stdlib
core); the Lean kernel lives in the **container**. The only coupling is the
`LeanBackend` Protocol, so swapping the CLI backend for a LeanDojo backend at R4 is
a one-class change.

**3. The backend reports; it never decides.** `LeanCliBackend` cannot touch
`Demonstratio.kernel_verified` — `LeanVerifier.discharge` remains the sole writer
(invariant 1), now guarded by `tests/test_boundary_guards.py`. `check_proof`
returns True **iff** the file elaborates with no error-level diagnostics **and**
uses no `sorry`/`sorryAx` (the axiom of `sorry` must never earn a `Q.E.D.`). The
result cache is keyed on the exact source hash and is populated **only** by a real
kernel run, so a cache hit replays a genuine verdict, never a bare boolean.

**4. No real promulgation on a vacuous faithfulness check.** `_negate` is still a
placeholder (ADR 0002 open item), so the adversarial gaming-witness passes
vacuously. Until R2 delivers a real `_negate` + claim-type probes, the R1 daemon
runs with an **empty probe table**, so every measurable claim returns
`DEFER` (never PASS, never JUDGED) on the faithfulness edge and cannot be
promulgated on faithfulness alone. Pinned by `tests/test_faithfulness_defer_r1.py`.
Enabling end-to-end promulgation is gated on R2's vacuous-specialization
regression test.

## Consequences

- R1a is **core Lean only** (triviality via `decide`/`simp`/`omega`/`trivial`).
  R1b adds Mathlib as a lake dependency (`lake exe cache get`) so
  analysis-of-algorithms statements elaborate, and adds `aesop` to the triviality
  set. R3 additionally requires an **elaborator-canonical `normalize_statement`**
  (today it is a textual hash) so structural novelty matching works — tracked as an
  R1b/R3 item.
- Per-check `docker run` startup (~1–2s) is fine for R1 verification volume; a
  long-running container with `docker exec` (or a small RPC server) is an R1b
  throughput optimization.
- The host never needs Lean/elan installed; reproducibility lives in the pinned
  image + `lean-toolchain`.

## Non-goals

- Interactive proof-state stepping (LeanDojo) — deferred to R4.
- Trusting the backend's report as anything but a relay of the kernel's verdict.
