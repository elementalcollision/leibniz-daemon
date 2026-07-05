# Findings — probes 7a/7b/7c: the large-block PSD wall, measured (arithmetization dead in its flat form; Schur-tiling sound but not de-risked)

**Date:** 2026-07-05 · **Track:** Terwilliger #3 frontier (ADR 0047 Option-3 de-risk) · **Tier:** probe
(offline; no `trust.py`/`verifiers.py`, mints nothing, no ADR) · **EV:** research · **Gate:** GREEN(measured).

The [external panel](large-block-psd-panel-findings-2026-07-05.md) recommended one bounded measure-before-build
spike to settle whether the ADR 0047 large-block PSD wall is a *permanent trust-model property* or an artifact
of the flat-`decide` encoding. Probes **7a** (kernel per-op vs fact-count), **7b** (Schur-tiling bit-growth),
and **7c** (the decisive realistic-tile cost, added after an adversarial review of this doc's first draft) are
done. **Corrected result:** the *flat/entrywise* arithmetization form is dead (7a), the CRT-congruence variant
is unmeasured, and Schur-tiling is **sound and structurally viable but not de-risked** — 7c shows its realistic
full-rank tiles cost hours, not minutes. **BANK-AND-HOLD is unchanged;** the bank is now honestly bounded.

## Probe 7a — the wall is DISTINCT-FACT COUNT, not per-op arithmetic (`scripts/probe_psd_arithmetization_7a.py`)

Two curves through the real Lean 4.31 kernel (`leibniz-lean-repl:v4.31.0`, `maxHeartbeats 0`):

| Curve A — one big-`Nat` multiply+compare | time | | Curve B — flat ∧ of K distinct big-`Nat` facts | time |
|---|---|---|---|---|
| `a·b == c`, ~996 bits | **0.24 s** | | K = 100 | 2.8 s |
| `a·b == c`, ~9 960 bits | **0.25 s** | | K = 400 | **51 s** |
| `a·b == c`, ~99 600 bits | 1.69 s\* | | K = 1600 | **timeout (>130 s)** |

- **Curve A is GMP-flat:** a single big-`Nat` op is ~O(1) kernel steps across a **10× bit-size jump**
  (0.24→0.25 s). **Per-op arithmetic cost is not the wall.** (\*The 100 k-bit point's 1.69 s is REPL
  literal-transport, not kernel reduction.)
- **Curve B walls on COUNT:** the flat conjunction is **~O(K²)** (4× more facts → 18× slower: 2.8→51 s) and
  times out by K ≈ 1600. **The killer is the number of distinct facts**, K_max ≈ **400** within the cap.

**Consequence (scoped — an adversarial review of this doc narrowed it).** A **monolithic, flat, entrywise
dense recompute** (list all N² identity facts as one `decide` goal) walls at **N_max ≈ √K_max ≈ 20** — *below*
even the compact `lowRankOK` ceiling of N≈60 (confirming the proof-term probe's "flat is worse than compact").
Per-op arithmetic is free (curve A), so *that* form gains nothing from big-`Nat`/GMP packing.

Two honest caveats the review is right to flag: (i) curve B measures the cost of a **flat K-deep `&&`-chain
under `decide`**; the ~O(K²) is plausibly partly a Decidable-instance / right-nested-`Bool.and` traversal
artifact, so "distinct-fact count" is the operative variable *for that encoding*, not a proven law. (ii) We did
**not** run the **k-prime CRT-congruence** variant (`M ≡ LᵀDL mod pⱼ`, ~8–12 primes, + a kernel-discharged
prime-adequacy lemma) — the panel's stated *only viable* form of approach A, designed precisely to avoid
stating N² distinct facts. So the earned claim is: **the monolithic flat entrywise dense recompute is
fact-count-walled; whether the CRT-congruence variant escapes is UNMEASURED** (it likely still touches Ω(N²)
entries via an in-kernel matvec, but this is a follow-on measurement, not a settled result). We do **not**
declare "arithmetization/CRT dead" beyond the flat entrywise regime we tested.

## Probe 7b — Schur-tiling bit-growth is POLYNOMIAL; structure survives (`scripts/probe_schur_tiling_7b.py`)

Exact-rational block-Schur elimination of representative integer PSD blocks `M = BᵀB` (dense = worst-case
fill-in; banded = structured), tiling in ≤60-order pivots, over `n = 30..160`:

- **Bit-growth is polynomial**, not exponential: over the actually-eliminated range the log-log exponent is
  **1.34 (dense) / 1.43 (banded)** — consistent with the Hadamard bound ~O(n·log n). A single order-60 Schur
  step inflates entries to ~1035 bits (dense) / 675 bits (banded), which is **inherent** (the Schur complement
  carries a 60-block inverse whose entries have ~det-of-60×60-sized denominators) and *grows polynomially*.
- **Structure helps:** the banded input keeps Schur-complement density at **0.44–0.69** vs **1.0** for dense,
  and smaller entries — so a real (sparse/algebraic) GMS block plausibly does *better* than these proxies.

**Consequence — the escape mechanism (in principle).** The Ω(N²) facts of an order-414 block are
**partitioned into k²+k independent `decide` goals** (k = ⌈N/tile⌉): the **k pivot-PSD checks** `B_i ⪰ 0` and
the **k² block-identity checks** `M_ij = (LᵀDL)_ij` tying the untrusted `(L,D)` to `M`, combined by **one
once-proved block-LDLᵀ / Haynsworth inertia lemma** (`M ⪰ 0 ⟺ M = LᵀDL ∧ all B_i ⪰ 0`). This is **sound**
(the `lowRankOK` posture already recomputes such identities fail-closed, never trusting the factor/rank) and
it **never forms the monolithic Ω(N²) term blob** — because `decide` is O(count²) *per goal*, many small goals
beat one giant goal. That structural escape is real. **What the tile SIZE and per-tile COST are, however, is
an efficacy question — measured next in 7c, and it is worse than an initial (retracted) estimate that borrowed
the shipped low-rank `lowRankOK` timing.**

## Probe 7c — the decisive tile-cost measurement (`scripts/probe_tile_cost_7c.py`)

An adversarial review of this doc flagged (correctly) that the tiling's block-identity tiles are **full-rank**
order-≤60 matmul identities with **~1000-bit** entries (7b) — *not* the rank-8, ~8-bit object the shipped
`lowRankOK` N=60 (~86 s) point was measured on. So we measured the real object: a compact `List`-`def`
**full** matmul-identity `mm A B == C` through the Lean 4.31 kernel, at growing order and entry bit-size:

| order | 8-bit entries | ~1000-bit entries |
|---|---|---|
| 20 | 3.5 s | 4.0 s |
| 40 | **78 s** | **125 s** |
| 60 | **timeout (>160 s)** | **timeout (>160 s)** |

- A **full** order-60 matmul identity **does not verify within 160 s even at 8-bit entries** — full-rank
  (O(N³)) is far heavier than the low-rank (O(N²·r), r=8) `lowRankOK`, so the effective ceiling for the
  block-identity tiles is **~order-40, not 60.**
- Entry size is **not free** once the fact count is large: at order-40, ~1000-bit entries cost **~1.6×** the
  8-bit time (78→125 s). "One big-`Nat` op is GMP-flat" (7a-A) does **not** transfer to a goal of ~10⁵ such ops.

**This downgrades the tiling de-risk.** With an effective identity-tile order of ~40, tiling order-414 needs
k ≈ ⌈414/40⌉ ≈ 11 → ~k²+k ≈ **132 tiles**, each ~78–125 s (and the deepest block-identity is a k-deep sum of
block-products, heavier still, unmeasured) → an order of **several hours** of kernel time, not the ~83 min
first estimated. The path is **sound and structurally viable, but its efficacy is materially worse than the
low-rank reference implied.**

## Net verdict (decision-grade, adversarially corrected)

- **Arithmetization (approach A): the flat/entrywise form is dead; the CRT-congruence form is UNMEASURED.**
  A monolithic flat entrywise dense recompute walls at N≈20 (7a-B) and packing/GMP can't help it (arithmetic
  already free, 7a-A). We did **not** measure the k-prime CRT-congruence variant the panel named as A's only
  viable form — so A is *not* declared globally dead, only its flat form.
- **Schur-tiling (approach best-novel): SOUND, structurally viable, NOT de-risked.** It avoids the monolithic
  blob and is charter-clean (soundness confirmed via the `lowRankOK` posture + a once-proved Haynsworth lemma;
  bit-growth polynomial, 7b). But 7c shows the realistic full-rank, large-entry identity tiles cap at
  ~order-40 and cost ~hours for order-414 — feasibility-in-principle, not a de-risked build.
- **Refinement to ADR 0047 (net):** the wall is real and neither mechanical path is a clean win. `decide`'s
  O(count²)-per-goal cost means *structure/partitioning* mitigates the wall (tiling) where *arithmetic
  packing* does not — but the mitigation buys hours, not minutes, and shrinks the usable tile below 60. The
  charter boundary stands.

## Recommendation — BANK-AND-HOLD (unchanged), with two precisely-specified follow-on measurements

The go/no-go is **unchanged: HOLD.** ADR 0047's trigger (a large-block cell *novel* **and**
*float-solve-reachable*) is still unmet (GMS records published; reachable cells DRY). The probe's value is a
**sharper, honestly-bounded bank**: if a target ever appears, the two measurements that would settle the path
(neither authorized here, both offline/no-trust-surface) are — (1) the **k-prime CRT-congruence** 7a variant
(does `M ≡ LᵀDL mod pⱼ` verify in o(N²) kernel terms, or still touch Ω(N²) entries?); (2) the **deepest
k-deep block-identity tile at full rank on a real GMS block** (needs cvxpy, operator-local) — plus the
one-time Haynsworth-lemma formalization (~3–6 PM per the panel). No trust surface touched;
`tests/test_invariants.py` byte-identical.

## Honest-scope note

This doc's first draft over-claimed ("arithmetization dead / tiling de-risked / ~83 min"); a two-lens
adversarial review (`docs/…` panel-style) caught both, and probe **7c was added and run** to replace the
borrowed cost estimate with a measured one. The corrected findings above are what the evidence supports.

## Artifacts

- `scripts/probe_psd_arithmetization_7a.py` · `docs/results/probe_psd_arithmetization_7a.json`
- `scripts/probe_schur_tiling_7b.py` · `docs/results/probe_schur_tiling_7b.json`
- `scripts/probe_tile_cost_7c.py` · `docs/results/probe_tile_cost_7c.json`
