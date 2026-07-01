<!--
Phase 2a of the SDP three-point build: the cvxpy solve + Table I reproduction (formulation-faithfulness
check) + a real formulation bug found and fixed. Operator-local (cvxpy); no trust surface touched;
tests/test_invariants.py byte-identical. Audit-tier.
-->

# Terwilliger three-point — Phase 2a: SDP solve + Table I reproduction (2026-07-01)

Phase 2a builds the Schrijver primal (eq. 19/20/22) in cvxpy on the Phase-1 structure and solves it
(`scripts/terwilliger_sdp.py`, Clarabel). Its job is the **empirical formulation-faithfulness check** the
adversarial panel asked for: does our transcription reproduce Schrijver's published Table I?

## Headline: it reproduces Table I — and caught a real formulation bug

| cell | our SDP | floor | Table I | Delsarte LP (our k=0) | valid (≥ lower) |
|---|---|---|---|---|---|
| **A(19,6)** | 1280.08 | **1280** | **1280** ✓ | 1289 (Table I: 1289) | ✓ (≥1024) |
| **A(20,8)** | 274.56 | **274** | **274** ✓ | — (see note) | ✓ (≥256) |
| A(8,4) | 16.00 | 16 | — | 16 | ✓ (=A(8,4)) |
| A(4,2)/A(6,4)/A(7,4) | 8/4/8 | 8/4/8 | — | = | ✓ |

**Both record cells reproduce Schrijver Table I** — the empirical answer to the panel's #1 concern
(formulation faithfulness, Fugu's Trap 3): our block β, the two families, the reduction, and the objective
are transcribed correctly, verified against *published* values (a stronger oracle than any review).

## The bug Phase 2a caught (and the fix)
A(8,4) initially floored to **13.7 < 16 = A(8,4)** — an *invalid* upper bound (below the true code size). Root
cause: Schrijver eq. (10) **sets `x^t_{i,j}=0` when the disjoint-subset multinomial `binom(n; i−t,j−t,t)=0`**,
i.e. when a triple is impossible (`i+j−t > n`). My triple enumeration only required `i+j−2t ≤ n`, so it
admitted **phantom free variables** (e.g. the key `(8,8,8)` from the impossible `t=4,i=j=8`). That phantom
variable made a real optimal code ([8,4,4] extended Hamming) look infeasible and the relaxation invalid. Fix:
a `possible(n,i,j,t)` predicate enforcing `i+j−t ≤ n` everywhere a triple is enumerated
(`scripts/terwilliger_dual.py` + the SDP build). After the fix: A(8,4)=16, and every LOWER-known cell floors
at or above its true code size (soundness sweep GREEN). Free-CPU regression:
`tests/test_terwilliger_dual.py::test_impossible_triples_are_excluded`.

This is exactly why the staged plan exists: Phase 0 validated β, Phase 1 validated the dual *of my primal* —
neither could catch a *primal-faithfulness* error. Phase 2a (reproduce published values) did.

## Caveats (⇒ Phase 2b)
- **Float, not exact.** Solves report `optimal_inaccurate` and floors are indicative: e.g. A(6,2) returns
  31.9999 for the true 32. Rigorous integer bounds require the **exact-rational dual certificate** (Phase 2b),
  not `floor(float)`.
- **Conditioning (panel Q-pit-2).** The k=0 diagnostic solve for A(20,8) returned a spurious 217
  (`sdp_le_lp` reported False there) — an ill-conditioned β-block artifact at n≈20, not a formulation error
  (the full SDP still floored to 274). Phase 2b must **solve normalized blocks and transform back exactly** (D6).

## Status
Phase 2a **GREEN** (both record cells reproduce Table I; no bound floors below a known lower bound). Formulation
faithfulness empirically established; phantom-variable bug fixed + guarded. Audit-tier; no trust surface
touched; `tests/test_invariants.py` byte-identical.

## Next — Phase 2b
Extract the dual from the (normalized) solve, rationalize via **feasibility-at-target** (fix `t`=1280, restore
strict-PD margin), **Bareiss**-bound the bit-length, and run it through Phase-1 `dual_check` for an **exact**
audit-tier bound on A(19,6). Then Phase 3 (kernel).
