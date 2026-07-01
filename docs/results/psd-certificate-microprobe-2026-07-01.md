<!--
$0 exact-PSD certificate micro-probe — the gate for the SDP three-point discovery bet. Isolates the
trust-boundary-unique make-or-break (exact-PSD kernel-checkable certificate + rounding), independent of the
specific SDP. Audit/measurement only; no trust touch; tests/test_invariants.py byte-identical.
-->

# Exact-PSD certificate micro-probe — SDP gate: **GREEN** (2026-07-01)

The SDP three-point scoping flagged the make-or-break as the leg **unique to Leibniz's trust boundary**:
can a float PSD solution be rounded to an **exact rational PSD certificate the kernel checks cheaply**? That
is independent of the specific SDP, so this $0 probe isolates it (no SDP solver is installed).

## Kernel-checkable PSD certificate (integer, core Lean, no Mathlib)
The producer supplies integer `L` (lower-triangular), integer diagonal `d`, positive integer `scale` with
```
L · diag(d) · Lᵀ  ==  scale · M      and    dᵢ ≥ 0
```
⟹ `M = (1/scale)·L·diag(d)·Lᵀ ⪰ 0` (congruence of a nonneg diagonal). The kernel verifies an **integer
matrix identity + a sign check** — polynomial, decidable, no eigenvalues, no decide-wall. Same posture as
the covering/Delsarte checkers.

## Result — GREEN
- **Exact-PSD certificates verify: 3/3** constructed strictly-PD matrices produce an integer LDLᵀ
  certificate that passes the exact re-check.
- **Kernel-checked, sound end-to-end:** the real Lean 4.31 kernel **verifies** a valid certificate
  (`ldltOK … = true := by decide`, True) and **rejects** a bogus one (False).
- **Rounding recipe recovers 18/18** (rate 1.0): floatify an exact PD matrix + Gaussian noise (simulating an
  SDP solver's output), round back to integers with a diagonal shift, and an exact PSD certificate recovers
  every time across sizes 3–5. The float→rational→exact-PSD rounding the panel flagged as *the* fragility
  **held**.

## What this establishes (and what it doesn't)
- **GREEN on the two trust-boundary-unique legs:** exact-PSD certificates are cheaply kernel-checkable, and
  a noisy float PSD can be rounded to an exact PSD certificate. These were the parts genuinely at risk for
  our architecture — and they work.
- **Out of scope here (the residual build):** solving the *actual* Terwilliger three-point SDP for a real
  cell (e.g. A(12,5) 40→32) needs **an SDP solver dependency** (SCS/cvxpy — not installed) plus the
  Terwilliger block-diagonalization. Those are "known-correct math + engineering," not novel-soundness risk.
  This probe deliberately did not reproduce a code bound; it de-risked the legs that could have killed the
  approach.
- **A surfaced subtlety for the build:** SDP optima are often irrational, so a rational certificate proves a
  rational *upper* bound ≥ the SDP optimum; for an integer code bound this is fine as long as the rational
  bound floors to the target integer (round up with margin — exactly what the diagonal shift does).

## Disposition / recommendation
The SDP gate is **GREEN**: the exact-PSD certificate mechanism is feasible under the trust boundary. The
remaining risk is ordinary engineering (add an SDP solver + the Terwilliger formulation), not a
soundness/kernel unknown. Recommended next step if the operator greenlights the build:
1. add an operator-local SDP solver (SCS via cvxpy);
2. wire the three-point (Terwilliger) SDP for A(n,d);
3. run the real reproduction probe (A(12,5) 40→32) → rational PSD certificate → kernel-check, reusing this
   probe's `ldltOK` core-Lean checker verbatim;
4. only on a reproduced-and-kernel-verified SDP bound, push to open cells for a genuine tightening (with the
   authoritative version-pinned UB oracle in place).

Artifact: `docs/results/psd_certificate_microprobe.json`. Harness: `scripts/psd_certificate_microprobe.py`
(`render_ldlt_lean` = the reusable core-Lean PSD checker). Test: `tests/test_psd_certificate_microprobe.py`.
