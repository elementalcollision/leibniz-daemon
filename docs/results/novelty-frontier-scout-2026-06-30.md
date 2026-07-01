<!--
Novelty-frontier scout (Track 1): a measure-before-build survey of candidate domains for a reachable,
genuinely-novel, sound-checkable result, run after the covering D-line was banked. Advisory analysis
(invariant 4: no LLM decides); no code, no trust touch. Produced by a 10-agent workflow (8 family mappers +
rank + adversarial critique); the LABS mapper hit the structured-output retry cap and is folded into the
"exhausted" bucket by the critique.
-->

# Novelty-frontier scout — where is a reachable NOVEL result? (2026-06-30)

**Verdict: no PURSUE candidate. All surveyed families are DEAD as an autonomous table-beat.** The scout
assessed candidate domains against the Gate-B0 4-way conjunction (MECHANISM ∧ HEADROOM ∧ ORACLE ∧
NON-COINCIDENCE) plus the two constraints this project has repeatedly found binding — producer-reachability
and a clean witness-shipping oracle — and every one fails.

## The structural hypothesis (scoped — see the external-round correction below)
> In the surveyed public-table finite-witness **positive/lower-bound** domains, the intersection of cheap
> kernel checking, a clean oracle, and reachable open headroom was **empty**: wherever a positive witness is
> cheap for the kernel to decide, the reachable-scale record is already proven-optimal, closed-form, or
> exhaustively classified.

This generalizes the covering result (0 beats / 22 proven-optimal over 71 cells) to six more families. It is
structural, not a failure of search effort: the objects with cheap kernel checks are exactly the well-studied
ones whose small cases are settled; the objects with open headroom need exponential non-existence proofs
(the Ramsey/Gate-B2 decide-wall) or human-directed prescribed-automorphism search (the CWC/Gate-D0 producer
wall).

> **External-round correction (2026-06-30, `docs/external-round-discovery-frontier-synthesis.md`).** The
> external panel accepted this for positive-witness table-beating but flagged it was **overstated as a
> "law"** — it is a **scoped hypothesis**. It does NOT cover the bands the panel identified as the escape:
> **upper-bound / negative certificates** (e.g. Delsarte LP duals), **non-existence** (SAT-UNSAT), and
> **falsification**. Those attack a different (continuous / search) band the scout never tested. Direction
> pivots there; see the synthesis.

## Per-family (all DEAD)
| family | mechanism | why DEAD |
|---|---|---|
| Packing / Steiner existence | poly decide (covering dual) | packing numbers are closed-form (Schönheim) at reachable band + no clean oracle; Steiner-existence is open but needs prescribed-automorphism research compute (PRODUCER) + only a binary non-machine-readable oracle (ORACLE) |
| Binary/ternary codes A(n,d) | poly all-pairs distance | CWC sibling on a denser, more-exhausted table; no single witness-shipping oracle (needs Brouwer+codes.se+Litsyn-Rains-Sloane merge) |
| Difference sets/families | poly difference-multiset | *best of the dead* — strong single-source oracle (dmgordon.org/diffset), but open cells are conjectured-**non-existent** (no positive witness to emit) and (v,k,1) families are the already-banked frontier |
| Costas arrays / Golomb rulers | poly (distinct differences) | feasibility is trivial/constructive (no novelty); optimality is co-NP/super-exponential with no poly witness (order-28 Golomb took ~8.5 CPU-decades) — free-CPU-unreachable |
| Orthogonal / covering arrays | poly (flat array) | closest covering sibling; renderable band proven-optimal, beatable band (t≥4) doesn't render in-kernel; records are algebraic-seed constructions |
| Additive combinatorics (caps/Sidon/sum-free) | poly | fails 3/4 legs; the one open cell (cap n=7) is *the* famous hand-crafted problem free-CPU can't reach; Sidon oracle lists proven maxima (a novelty trap) |
| Walnut/Z3/proof-compression (non-table) | Walnut/Z3 decide | the most-exhausted region in the program already (measured negative in prior probes); oracle only partial/lane-specific |

## Recommended kill-confirmation (optional, $0)
The single cheapest residual check is a ~30-min desk look at **difference families** on dmgordon.org/diffset
(the one family with both a witness-producible object and a strong single-author oracle — same
infrastructure as the integrated LJCR covering repo). Classify OPEN cells in the reachable band. The critique
predicts **expected yield 0** (even clearing the 4-way conjunction is insufficient — covering cleared it and
beat nothing), so treat this as a cheap confirmation, not a bet. **No build is justified by this scout.**

## Strategic implication
Autonomous **table-beating discovery is dead across the surveyed space** — the covering conclusion is
general, not covering-specific. The program's value remains where it is banked:
- **Verification-amplification** (the kernel-checked corpus) is the product — and note several DEAD-as-a-beat
  families (Steiner existence, difference families) are *real Track-A amplification targets*: their witnesses
  ARE cheaply kernel-checkable, so a human/research-supplied witness could be re-checked into the corpus.
- Genuine autonomous **discovery** would require leaving the "cheap-witness ⇒ already-solved" band — i.e. a
  certificate architecture for the exponential-predicate objects (large, separately scoped), a full-text
  witness-**reconstruction** producer (the research-ingestion §"out of baseline" slice), or a different KIND
  of result than a table beat. None is a free-CPU next step.

Net: the honest next move is **not** another table scout. Either invest in one of the heavier bets above
(operator decision) or keep consolidating the amplification product. Findings this cycle:
`docs/results/tier2-results-2026-06-30.md`, `docs/ingestion-pipeline-baseline.md`, and this doc.
