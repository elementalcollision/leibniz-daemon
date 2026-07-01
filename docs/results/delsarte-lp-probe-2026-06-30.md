<!--
P1 result — the Delsarte LP dual-certificate probe, the first concrete step of the post-scout
certificate-architecture pivot (external round, docs/external-round-discovery-frontier-synthesis.md).
Audit/measurement only; no trust touch; tests/test_invariants.py byte-identical.
-->

# P1 — Delsarte LP dual-certificate probe: **GREEN, sound end-to-end** (2026-06-30)

The external panel's convergent escape from the (now-scoped) structural hypothesis: stop *constructing*
optimal objects; **verify a small certificate from an untrusted solver for the UPPER-bound band.** This is
the make-or-break probe of that pivot, for unrestricted binary codes A(n,d).

## The chain (soundness rests only on the last step)
```
untrusted ortools GLOP (float)  ->  Delsarte dual polynomial f = 1 + Σ f_k K_k
   ->  round to an EXACT INTEGER certificate (q; p_1..p_n),  f_k = p_k/q          [untrusted]
   ->  exact re-check: p_k>=0, q>0, and  q + Σ_k p_k K_k(i) <= 0  for i=d..n        [SOUND]
   ->  A(n,d) <= floor((q + Σ_k p_k K_k(0))/q)                                      [Delsarte's theorem]
```
Clearing denominators makes the certificate **integer**, so the check is small integer arithmetic — no
rationals, and (crucially) **no `decide`-wall**: the kernel recomputes Krawtchouk itself (binomial via
Pascal's rule, core Lean, no Mathlib) and verifies in seconds.

## Result — GREEN
- **9/9 cells produced an exact integer certificate that passed the sound re-check**, and **all 9 reproduce
  rock-solid known values**: A(5,3)=4, A(6,3)=8, A(7,3)=16, A(6,4)=4, A(8,4)=16, A(8,5)=4, A(9,5)=6,
  A(10,5)=12, A(11,5)=24.
- **End-to-end kernel-checked:** the real Lean 4.31 kernel **verifies** the A(5,3) certificate (`certOK … =
  true := by decide`, True) and **rejects** a bogus all-zero certificate (False). The full
  untrusted-LP → exact-cert → **kernel** chain is sound.
- The float→rational rounding the panel flagged as fragile **held** across all 9 cells (denominator-grid
  search + margin nudge). ortools only; $0.

## The oracle-wall lesson (caught live)
The first draft hard-coded `A(9,5)=12` (a typo for A(10,5)=12). The certificate certified A(9,5) ≤ **6**,
which tripped a self-consistency guard: *a verified Delsarte certificate is always a valid upper bound, so
`cert_bound < known` is impossible for a sound cert — it flags the KNOWN entry as wrong, never a discovery.*
Correcting the table (A(9,5)=6) resolved it. This is exactly the panel's oracle-wall warning in miniature:
**any future "tightening" must be judged against a real, version-pinned upper-bound oracle, not an unvetted
table** — and the certificate's own validity is the backstop that catches a bad oracle.

## What this establishes
- The **certificate architecture is mechanically feasible** under the trust boundary: an untrusted solver
  proposes, the kernel decides a small certificate, soundness is preserved, and it sidesteps both the
  producer wall (no construction) and the decide wall (small integer check). This is the first direction
  since the covering work that is *not* dead.
- It attacks the **upper-bound** band the 7-family scout never tested — the panel's polarity flip.

## Next steps (gated; not started)
1. **Real version-pinned upper-bound oracle** — replace the hardcoded `KNOWN` with a DOI-pinned snapshot of
   the Brouwer/code tables' UPPER-bound column (the novelty oracle for any actual tightening). Prereq to any
   discovery claim.
2. **The Delsarte bridge lemma** — `certOK ⇒ A(n,d) ≤ f(0)` currently rests on Delsarte's theorem as a
   meta-argument; formalize it in Lean for a fully self-contained proof (mirrors the pending
   `validCovering ⇒ C(v,k,t) ≤ B` bridge). Until then this is audit-tier (kernel-checked *certificate
   validity*, not a promulgated bound).
3. **Reach probe (the actual bet):** run on **open** cells where the table's LB < UB and check whether the
   LP dual **tightens** the published upper bound — a *genuine, sound-checkable* result if it does. Free-CPU;
   the honest test of whether this yields discovery, not just reproduction.
4. **Constant-weight A(n,d,w)** — the Johnson-scheme analog (Hahn polynomials) extends this to our existing
   CWC domain's upper bounds.

Artifact: `docs/results/delsarte_lp_probe.json`. Harness: `scripts/delsarte_lp_probe.py`
(`render_cert_lean` = the core-Lean checker). Test: `tests/test_delsarte_lp_probe.py`.
