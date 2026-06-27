<!--
Synthesis of the 7-model external-witness round #2 (compute/library acceleration). Inputs: Fugu,
Fugu Ultra, Deepseek v4 Pro, Kimi, GLM 5.2, Gemini 3.5 Thinking, Qwen 3.7 Max. Witnesses advised on
DIRECTION; trust boundary + human novelty verdict fixed. Pairs with the CP-SAT A(14,6,6) datapoint.
-->

# External-witness round #2 (acceleration) — synthesis

**Unanimous (7/7): the binding constraint is ALGORITHM/DOMAIN, not compute/library.** Generic
acceleration of the current exact-search track is negative-EV; the lever is a *paradigm shift to
construction search*, where GPU/parallelism genuinely helps. This matches our own measurement
(CP-SAT extended sweep: on A(14,6,6) a strong solver found only 30 vs Brouwer's known 42 — it could
not even *match* a known construction).

## The sharp reframe (the line that recurs)
We are using an **optimality/upper-bound prover** (max-clique / CP-SAT / ILP) to find **lower-bound
witnesses**. A lower-bound record needs **one larger code**, not a proof of optimality — so exact
branch-and-bound pays exponential cost for something the task does not require, and the records come
from human **constructions** (symmetry, algebraic, cyclic/quasi-cyclic, shortenings), not bigger search
trees. (GLM, Qwen, Kimi, Deepseek all state this; Fugu: "proof of optimality is irrelevant.")

## Convergence across the six questions

| Q | Convergent answer (7/7 unless noted) |
|---|---|
| 1 Premise | **Algorithm-bound.** 10–100× = constant Δn on an exponential/superexponential curve. Cheapest settling test: budget-scaling (run current solver at 10×/100× on open cells; no +1 ⇒ algorithm-bound) — *largely already answered by our A(14,6,6) shortfall*. Qwen's "plant-and-recover" (delete 2 words from a known optimal; if the solver can't recover them, its landscape is blind) is a sharp cheap variant. |
| 2 Accelerator→workload | **GPU (RunPod/MLX) on exact max-clique/CP-SAT/SAT: ~0–1.5× (often slowdown)** — branch-heavy solvers are GPU-hostile (HIGH confidence, all 7). GPU on **SDP/SOS 3–50×**, on **ML-guided/LLM 10–100×** (the real GPU win). **Codon 10–100× on pure-Python loops ONLY; 0× on CP-SAT (already native).** **SciPy/HiGHS float, ~0.3–3× vs CP-SAT, untrusted.** **Trusted checkers/Lean: 0× — never accelerate.** |
| 3 Trust placement | Acceleration **only** in the untrusted proposer/search tier. The pattern *"untrusted GPU/float/heuristic proposes → exact CPU/Lean re-checks"* is **already our design** (witness-checker + oracle) — confirmed correct. **Codon-compiling a checker: NO (7/7)** — adds an unverified LLVM compiler to the TCB; a miscompiled carry bit silently breaks soundness. |
| 4 Highest-EV | **"None" for the current exact-search track** (majority rank it #1; negative-EV to accelerate brute search). **RunPod GPU is #1 only *conditional on pivoting* to construction search** (Qwen, Fugu, GLM). Codon ranked high only as an accelerator *for untrusted heuristic-construction loops* (GLM). |
| 5 Sleeper | **CONSTRUCTION SEARCH** — overwhelming convergence on two forms: **(a) massively-parallel randomized/heuristic construction** (greedy + simulated-annealing/tabu/genetic, batched popcount Hamming checks — embarrassingly parallel; Fugu, Fugu Ultra, Kimi); **(b) learned construction à la FunSearch/AlphaTensor** — LLM/evolution proposes *construction programs* (priority functions / algebraic builds), evaluated untrusted, Lean-checked (Deepseek, GLM, Qwen, Gemini; FunSearch already cracked cap-sets). Plus **(c) automorphism-prescribed search** — assume a symmetry group, collapse variables by orders of magnitude, then solve (Gemini, Qwen — "how Brouwer records were actually found"). |
| 6 Falsifiable next | Cheap CPU budget-scaling probe FIRST (≈$3–10), then a construction-search pilot (random or FunSearch), GREEN = ≥1 Lean-verified +1 record (or reach a known M where CP-SAT can't). GLM/Qwen: rediscover a *known* construction on a solved hard cell to validate the paradigm before scaling. |

## What this changes
- **Do not buy generic acceleration** (GPU/Codon/SciPy) for the current exact-search pipeline — unanimous.
- **The autonomous lever is construction search** (right objective: find a big code, not prove
  optimality). GPU helps *there* and only there; our sound checker is already the right backstop.
- **The trust architecture is vindicated again** — accelerate only the untrusted side; the witness IS
  the proof; never accelerate the checker/kernel.

## Recommended next move (measure-before-build, autonomous, no humans, no spend)
Per the cheapest-decisive-first discipline: prototype **construction search on CPU first** — stochastic
greedy + penalty/swap local search targeting best_known+1 on the open cells, Lean-checking any beat.
This (i) directly tests the witnesses' "wrong objective" reframe (construction vs optimality), (ii) is a
free local measure-before-build for the GPU construction-search pivot, and (iii) is fully autonomous
(no humans, no billing). If CPU construction search reaches/beats records → GPU scaling is justified
(and the FunSearch/automorphism forms become the next escalation); if it plateaus at known bounds like
CP-SAT did → even construction search needs structure (symmetry/algebra/learned heuristics), confirming
the records are research-hard and bounding the autonomous track honestly.
