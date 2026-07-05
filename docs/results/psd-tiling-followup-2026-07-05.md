# Follow-on — Haynsworth tiling-soundness lemma (proved) + the CRT/Freivalds measurement (closes the gap)

**Date:** 2026-07-05 · **Track:** Terwilliger #3 frontier (ADR 0047 Option-3) · **Tier:** audit / probe
(offline; no `trust.py`/`verifiers.py`, `tests/test_invariants.py` byte-identical) · **EV:** research.

The [probe findings](psd-arithmetization-probe-findings-2026-07-05.md) recorded three bounded follow-ons after
an adversarial review corrected their over-claims. This delivers them.

## (C) The Haynsworth / block-LDLᵀ tiling-soundness lemma — PROVED, axiom-clean

`docs/crt/haynsworth_tiling_soundness.lean` — the panel's tractable "Half 1", now a formalized down-payment
(kernel-verified via `scripts/verify_haynsworth_tiling.py`, `#print axioms` = `{propext, Classical.choice,
Quot.sound}`, 0 `sorry`):

- **`psd_of_congruence`** — `D ⪰ 0 ∧ M = Lᴴ D L → M ⪰ 0`, for **any** `L` (no rank/positivity on the factor).
  This is *why the tiling certificate is fail-closed*: the kernel recomputes the identity `M = Lᴴ D L`; a
  corrupted factor cannot make a non-PSD `M` pass.
- **`psd_of_sum_congruence`** — `M = ∑ᵢ (Cᵢ)ᴴ Bᵢ Cᵢ` with every pivot `Bᵢ ⪰ 0` → `M ⪰ 0`. This **is** the
  Schur-tiling soundness: an order-N block that is a sum of congruences of ≤60-order PSD pivots is PSD — so
  PSD-ness reduces to the small pivots (kernel-decided) + one recomputed identity, **never forming the
  monolithic Ω(N²) `decide` goal**.

Both fall out of Mathlib's `Matrix.PosSemidef.conjTranspose_mul_mul_same` (congruence preserves PSD) +
`.add`/`.zero` — **no Schur-complement iff is needed** (Mathlib has none), which is the key simplification.
Pure Mathlib theorem: **no trust surface** (it would merely be *used* by a future, separately operator-gated
tiling primitive). This is real, banked progress on the tiling path's soundness half.

## (A) CRT / derandomized-Freivalds — measured: it does NOT escape the wall (`scripts/probe_crt_freivalds.py`)

The review's load-bearing catch was that the earlier probe measured the *flat* arithmetization form, not the
**Freivalds/CRT** variant the panel named as approach A's only viable form. Measured now, through the real
Lean 4.31 kernel: verifying `M = FᵀF` by a **matVEC** check `M·v = Fᵀ(F·v)` (O(N²), r× fewer terms) vs the
**full** Gram identity `FᵀF = M` (O(N²·r), r=8):

| order | full identity | Freivalds matvec |
|---|---|---|
| 40 | 16.2 s | 15.5 s |
| 60 | **91.5 s** | **91.4 s** |
| 80 | timeout | timeout |

**Freivalds walls at the SAME N≈60, with near-identical times.** The r× term saving does **not** move the
wall, because the dominant cost is the **O(N²) List structure of `M` itself** (and the O(N²) matvec), not the
r-factor. So the CRT/Freivalds direction gives no lift; and a *sound* single-vector Freivalds would only
*add* cost (needs N+1 evaluation points, ~N×, or a Kronecker-packing magnitude argument). **Net: arithmetization
is now measured-dead in BOTH forms** — flat/entrywise (N≈20) and compact matvec/CRT (N≈60) — neither anywhere
near 130–414. This closes the gap the review flagged: the earned claim is no longer "flat form only" but "no
measured arithmetization form escapes." The escape remains **structure/tiling**, not arithmetic.

## (B) Deepest full-rank tile (k-deep) — analytic note

7c already measured the core: a full order-60 matmul identity times out (>160 s); order-40 = 78 s. The
tiling's *deepest* block-identity tile is `M_ij = Σ_{p≤k} (block products)` — a **k-deep sum** of order-≤tile
matmuls in one goal, so ~k× the single-matmul cost. Combined with 7c's order-60 timeout, the deepest tiles
must therefore use an even smaller order than the shallow ones — reinforcing 7c's conclusion (effective tile
< 60; order-414 costs hours, k rises). No separate probe run; this is a corollary of 7a-B (O(count²)) + 7c.

## Net (bank-and-hold, unchanged; now with a soundness down-payment banked)

- **Arithmetization: measured-dead** across every form we could run (flat N≈20; compact matvec N≈60). Not the escape.
- **Schur-tiling: soundness half now FORMALIZED** (the Haynsworth lemma, axiom-clean) — a real, reusable,
  charter-clean asset. Its efficacy half stays bounded (7c: hours, tile < 60), the genuine remaining research.
- **Go/no-go unchanged: HOLD** — ADR 0047's trigger (novel ∧ float-solve-reachable target) still unmet. The
  bank is now better: the tiling path has its soundness lemma proved and its dead alternative (arithmetization)
  measured out, so if a target ever appears the work starts from a proved soundness core, not a blank page.

## Artifacts

- `docs/crt/haynsworth_tiling_soundness.lean` · `scripts/verify_haynsworth_tiling.py` ·
  `tests/test_haynsworth_tiling.py` · `docs/results/haynsworth_tiling_verification.json`
- `scripts/probe_crt_freivalds.py` · `docs/results/probe_crt_freivalds.json`
