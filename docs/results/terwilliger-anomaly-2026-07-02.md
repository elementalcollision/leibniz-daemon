<!--
Discovery pivot D2 (task #103) — resolve the A(22,10) anomaly. Audit/measurement only; no trust touch;
tests/test_invariants.py byte-identical. Outcome: Table I VALIDATED (no discrepancy claim; the operator
stop-condition did not fire).
-->

# The A(22,10) anomaly is RESOLVED — Table I validated, our gap found (D2, 2026-07-02)

The solve-leg session left one open cell: our transcription certified **A(22,10) ≤ 88** exactly (88.2463 at
P=1e14), **87 did not certify**, floats stalled on both sides, and Schrijver's Table I says 87. Ticket D2's
three paths all ran this session; they converge on one answer:

> **The 87 is correct, and our transcription reaches it.** The ≤88-only record was a dual-*source* artifact:
> `certify_lp` fixes its PSD blocks from the FULL problem's float dual — the stalled `optimal_inaccurate`
> solve. The k_max-**truncated** problem is a *relaxation* (fewer PSD constraints ⇒ truncated optimum ≥ full
> optimum), SDPA solves it to clean `optimal` at (22,10), and a truncated dual, zero-padded on the dropped
> blocks, is a feasible full-problem dual. The exact LP through **that** dual certifies Table I's value.

## Path (a) — the better dual: two new exact certificates, both kernel-attested

| cell | old record | new exact certificate | Table I |
|---|---|---|---|
| A(22,10) | ≤ 88 (88.2463); "87 does not certify" | **≤ 87** (exact bound 87.97336, P=1e14, k_max=2 dual; k_max=3 agrees) | 87 ✓ |
| A(26,10) | float stall 948.33, no certificate | **≤ 886** (exact bound 886.8587, P=1e14, k_max=4 dual; k_max=3 agrees) | 886 ✓ |

Mechanics (`scripts/terwilliger_anomaly.py`): solve the k ≤ k_max truncation (SDPA-GMP tight, eq.(8)
normalization), extract its dual, set Z_k = Z'_k = 0 exactly for the dropped k > k_max blocks (exact zero —
no εI margin, no residual contribution), rationalize the kept blocks at P=1e14, then the one exact simplex
over all multipliers + `dual_check`, unchanged. The zero blocks carry the trivial LDLT certificate
(L=I, d=0, scale=1) in the kernel leg, so **every** block is attested — the real Lean 4.31 kernel accepts
both certificates (24 blocks / ~51 s and 28 blocks / ~100 s, incl. the controls) and rejects the
corrupted-block control on each (kernel-bank tier).

With A(26,10) closed, **every Table I cell our pipeline has attempted is now reproduced at the exact tier**
(1280 / 274 / 13766 / 503 / 87 / 886) — the transcription-faithfulness record has no remaining exceptions.

Two corollaries the exact tier settles about the solve-leg session's readings:

- The full-solve float "pseudo-optimum" **88.63 was infeasible**, full stop: its value exceeds a now-certified
  upper bound on the SDP optimum by 0.66. ("No float-side audit is a bound in either direction" stands.)
- The **87.97 "stall attractor" was the honest signal**, not a provable under-solve. The under-solve reading
  leaned on the 88.63 point (the caps-augmented dismissal assumed that point was feasible). The k_max ladder
  was monotone all along: 95.32 → 93.06 → 87.974 → 87.974 → full ≤ 87.9734 (certified).

## Path (b) — formulation diff vs Schrijver's program: no delta

Re-read against the published paper (IEEE-IT 51(8), 2005, §I): the program is (19) PSD blocks — with the
paper's own note that the `C(n−2k,i−k)^{−1/2}` factors are deleted to make β integer, i.e. exactly our
integer-β/eq.(8) split — plus (20)(i)–(iv), the even-d reduction ("one can put x^t_{i,j}=0 if i or j is
odd"), objective (22). All present in our transcription (`terwilliger_dual.py`), none extra. On cell-specific
constraints: **eq. (25) caps were not used** — the paper states "we did not obtain in this way any
improvement in the above table." Table I *is* the base program. No formulation gap existed; the d≥10
γ-substitution suspicion was already closed as a non-bug in the solve-leg session.

## Path (c) — provenance of the 87: double-precision, era-consistent, now upgraded

- **Schrijver 2005**: "Our computations were done by the algorithm SDPT3 version 3.02 … on the NEOS Server
  … The answers have been confirmed by the algorithm DSDP version 5.5." Both double-precision; no
  exact-rational leg existed. Table I row (22,10): prev-best 88 → new 87 (Delsarte 95); row (26,10):
  989 → 886 (Delsarte 1040).
- **Gijswijt–Mittelmann–Schrijver 2012** (arXiv:1005.4959, the four-point paper: A(22,10) ≤ 84, A₄ = 84.421)
  lists 87 as the prior best and documents exactly the failure mode we measured: "the semidefinite programs
  generated appear to have rather thin feasible regions so that SDPA and the other high-quality but double
  precision codes terminate prematurely with large infeasibilities" — their reason for SDPA-GMP, same as our
  D6 fix.
- **Brouwer's current table** (snapshot 2026-07-01): (22,10) ub is now 84 (GMS 2012); the 87 ("Schrijver,
  personal communication, March 2004") is the superseded three-point value. Our certificates therefore
  claim nothing against the *current* table — they re-derive the 2005 three-point values at a **higher
  trust tier than the original computation** (exact-rational dual + kernel attestation vs confirmed floats).

## What this changes for the discovery pivot

- The anomaly is closed as **our gap, found and fixed** — no discrepancy claim, so the operator
  stop-condition did not fire and nothing needs external communication.
- **Truncated-dual extraction is a general tool**: wherever the full solve stalls but a truncation reaches
  clean `optimal`, the truncated dual is a valid (possibly slightly loose) exact-certification source. It
  rescued both stall cells here; D1/D3 builds should inherit it.
- The reach-probe verdict stands unchanged: reproduction ≠ discovery; the three-point family's frontier
  cells remain bound-blocked (Delsarte-ties), and the current best at (22,10) is GMS12's four-point 84 —
  exactly the D3 (hierarchy scoping) direction.

## Artifacts / repro

`docs/results/terwilliger_anomaly.json` (per-k_max certification rows, kernel legs, provenance quotes) —
regenerate with `python3 scripts/terwilliger_anomaly.py` (operator-local: cvxpy + sdpap + numpy for the
solves, docker for the kernel legs; ~5 min). Tests: `tests/test_terwilliger_anomaly.py` (zero-block LDLT
exactness free of solver, truncation-is-a-relaxation, labeled-truncated-build structure, and the two
headline regressions A(22,10)≤87 / A(26,10)≤886; CI skips clean). Trust surfaces untouched;
`tests/test_invariants.py` byte-identical.
