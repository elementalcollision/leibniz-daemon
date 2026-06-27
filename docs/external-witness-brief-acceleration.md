<!--
External-witness elicitation #2 — compute/library acceleration for the autonomous-discovery track.
Two operator-named tracks: (A) GPU assist (RunPod remote / Apple MLX local); (B) Codon / SciPy.
§1 operator-facing framing; §2 the verbatim prompt for each witness. Precedent: ADR 0036 rounds +
docs/external-witness-brief-2026-06-26.md. Witnesses advise on DIRECTION; the trust boundary and the
human novelty verdict (invariant 4) are fixed.
-->

# External-witness brief #2 — should we accelerate the autonomous track (GPU / Codon / SciPy)?

## §1 The decision (operator-facing)

The autonomous-discovery track is measured-RED across five probes; most recently the **constant-weight-code
record factory** (Probe β) is built and sound (Lean-checked witness; automated Brouwer table-of-record
oracle) but a strong CPU solver (**CP-SAT, 8 workers**) *matches but does not beat* Brouwer's lower bounds
on the tractable cells, and the open cells are too large for a laptop. So the apparent next lever is
**more compute / better libraries**. The operator named two tracks to evaluate:

- **(A) GPU assist** — a RunPod API integration to kick off remote GPU jobs, and/or local Apple GPU/NPU
  acceleration via **MLX**.
- **(B) Codon** (Python→native LLVM compiler) and/or **SciPy** (HiGHS MILP, sparse linalg, scientific
  routines) for more speed / precision / capability.

We are asking the field one question — **is acceleration the right lever, and if so which one and where?**
— and asking them to *attack the premise first* (maybe the binding constraint is algorithm/domain, not
hardware, in which case acceleration just fails faster on harder cells). Responses feed the next
measure-before-build probe / ADR. Witnesses advise on **direction**; the trust boundary stays fixed and
novelty stays the human panel's call.

## §2 The prompt (verbatim — give this, unedited, to each witness)

> **You are an external witness reviewing a compute/library investment decision for an automated
> mathematics project. Be adversarial, concrete, and calibrated. No flattery. Attack the premise before
> you advise. Distinguish what you KNOW from what you GUESS, and give numeric estimates with confidence.**
>
> ### The project (fixed constraints — do not propose weakening these)
> "Leibniz" is an agentic theorem daemon: **LLMs only PROPOSE; only mechanical checkers DECIDE.** A result
> is `Q.E.D.` only when the Lean kernel verifies a proof; soundness ("nothing false is ever stamped") is
> non-negotiable. The workloads split into two trust classes, and this distinction is central to your
> answer:
> - **UNTRUSTED proposer / search** (may be accelerated freely — its output is always re-checked
>   downstream): conjecture generation; combinatorial search (max-clique / SAT / CP-SAT / ILP);
>   SDP solving for sum-of-squares; any ML-guided heuristic or construction search.
> - **TRUSTED checkers** (must stay sound and minimal-TCB; accelerating them *expands the trusted
>   computing base* unless the acceleration is itself re-verified by an independent sound check): the
>   exact-rational re-checkers (Python `fractions.Fraction`), the finite-witness verifiers, and the Lean
>   kernel. `kernel_verified` is written in exactly one place.
>
> ### Where the project is (measured, not asserted)
> Five independent probes converge: the *soundly-checkable, cheaply-reachable* region of a studied domain
> is the region humans have already solved. Concretely, the current autonomous track is a **finite-witness
> record factory** for binary constant-weight codes A(n,d,w): an untrusted search proposes a code; a Lean
> theorem (the witness IS the proof) is kernel-checked; novelty = beating Andries Brouwer's published
> lower-bound table, judged by an automated oracle. Results so far:
> - Pure-Python exact max-clique decides only TINY cells — all already tight (optimal).
> - **CP-SAT (8 workers, ~25 s/cell)** on the larger non-tight cells (C(n,w) ≈ 1000–1700): **0 records
>   beaten**; it *matched* every best-known and *proved* a couple optimal. The open (potentially beatable)
>   cells have C(n,w) in the thousands-to-millions — out of reach for a laptop solver.
> The binding constraint is therefore *either* compute/solver power on large open instances, *or*
> something deeper (algorithm/domain): the easy region is solved and the hard region is research-hard.
>
> ### The investment under evaluation
> - **(A) GPU assist** — (i) **RunPod**: on-demand cloud GPUs kicked off via API (async, billable);
>   (ii) **Apple MLX**: local Apple-Silicon GPU/NPU array framework.
> - **(B) libraries** — **Codon** (compiles a Python subset to native via LLVM; 10–100× on tight numeric
>   loops, limited library/dynamic-Python support); **SciPy** (HiGHS MILP via `scipy.optimize.milp`,
>   sparse linear algebra, scientific routines; float-based, not exact).
>
> ### Your task — answer all six, briefly and concretely
> 1. **Attack the premise.** Is the binding constraint actually **compute/library**, or is it
>    **algorithm/domain** (so any accelerator just lets us fail faster on harder cells / rediscover known
>    bounds)? Give the single strongest reason acceleration is the *wrong* lever, and the cheapest
>    experiment that would settle compute-bound vs algorithm-bound.
> 2. **Map accelerator → workload, with calibrated numbers.** For each of {RunPod GPU, Apple MLX, Codon,
>    SciPy/HiGHS}, state which workloads it actually speeds up and by how much (order-of-magnitude, with
>    confidence): (a) exact combinatorial search (max-clique / SAT / CP-SAT / ILP), (b) SDP for
>    sum-of-squares, (c) ML-guided proposal/construction search, (d) the LLM conjecturer, (e) the trusted
>    re-checkers / Lean kernel. Be explicit where a tool does NOT help (e.g. branch-heavy exact solvers are
>    notoriously poor GPU fits; SciPy is float, not exact).
> 3. **Trust-safe placement.** Where may acceleration live *without expanding the TCB*? Is it acceptable to
>    Codon-compile a *checker*? Is the right pattern "GPU/float computes a candidate, then an exact
>    CPU/Lean re-check confirms it"? Name explicitly what must NEVER be accelerated into the trust path.
> 4. **Rank the single highest-EV investment** for actually reaching novel / record-beating territory:
>    RunPod GPU vs Apple MLX vs Codon vs SciPy/HiGHS vs **none (compute isn't the constraint)**. Defend on
>    expected value, not enthusiasm.
> 5. **Name a sleeper we're missing.** An accelerated approach with real upside we haven't listed —
>    e.g. GPU SDP for sum-of-squares at scale; learned construction search on GPU (FunSearch / AlphaTensor
>    style) feeding the sound checker; massively-parallel randomized/heuristic construction search; GPU
>    SAT; exact-rational arithmetic at scale. Be specific about why it is both reachable and high-upside.
> 6. **One falsifiable next step per accelerator you recommend** — a measure-before-build probe whose
>    result would change the decision, with a GREEN/RED criterion tied to a *discovery* outcome (a beaten
>    record, a newly-reachable cell class, or a speedup threshold that unlocks a class), not a microbench.
>
> Constraints on your answer: respect the trust boundary (untrusted search may be accelerated; the sound
> checkers + Lean kernel must stay minimal-TCB or be re-verified); prefer concrete mechanisms and numbers
> over generalities; separate what you know from what you guess; end with a single prioritized
> recommendation in one sentence. You are advising on **direction**, not deciding novelty (a human panel
> does that) and not relaxing soundness.
