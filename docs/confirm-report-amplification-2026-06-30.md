<!--
Confirm report for the post-D0 amplification arc (operator: "what needs testing / confirmed?").
Three confirm items run 2026-06-30. Provenance: this session's runs; docs/results/exact_confirm.json.
No trust-boundary change.
-->

# Confirm report — amplification arc (2026-06-30)

Three open confirm items from the post-D0 assessment, run and recorded. **Two clean; one honest nuance.**

## 1. Covering-oracle snapshot fidelity — ✅ CLEAN
The committed `scripts/data/covering_snapshot.json` (9,482 cells, LJCR 2026-04-21) was checked two ways:
- **parse determinism:** re-parsing the originally-fetched HTML reproduces the snapshot **byte-identically** (9,482/9,482);
- **staleness:** a **fresh re-fetch** of `ljcr.dmgordon.org/cover/table.html` parses to the **identical** set — 0 improved, 0 worse, 0 new, 0 gone.

The oracle mirror is faithful and current. (It is also now load-validated against ground-truth anchors + the Schönheim floor — ADR 0045 PR.)

### 1a. Float-Schönheim bug — B0 numbers re-confirmed unaffected
The Gate B0 headroom counts were originally computed with a **float** Schönheim later found to misround
(e.g. `L(98,5,2)` → 491 vs the true 490). Re-counting with the fixed **exact-integer** Schönheim gives
**identical** numbers (5,460 small-witness ∩ gap≥2; 2,251 with <100 blocks) and **0** cells where the
float-vs-int verdict flips — the bug only ever misrounded Schönheim-tight (gap=0) cells, never the gap≥2
set. The Gate B0 finding stands as committed.

## 2. Ramsey kernel-tractability on REAL witnesses — ✅ CONFIRMED
The earlier ≤0.07s @ n=240 result used *random* circulants. Re-run on **Paley graphs** — the classical,
structured, near-threshold (ω=α≈√p) cyclic Ramsey lower-bound construction — the VT-reduced check stays
fast: Paley(101) 0.00s, Paley(149) 0.01s, Paley(197) 0.04s, **Paley(241) 0.27s** (Python; the kernel is
slower but with orders of margin). The vertex-transitive reduction is tractable at frontier sizes on
*structured/extremal* witnesses, not just random ones. *(Caveat: Paley is the balanced ω=α regime; an
off-diagonal R(4,t) frontier witness has small ω and large α — the independent-set side would be the cost
and warrants its own timing if Ramsey/B2 is ever pursued.)*

## 3. The two budget-limited exact cells — ⚠️ NUANCE (not proven optimal)
The earlier exact-producer run left C(13,5,2) and C(16,6,2) budget-limited at 90s. Re-run at **600s each**:

| cell | LJCR record | exact found @600s | proven optimal? |
|---|---|---|---|
| C(13,5,2) | 10 | 10 (reproduced) | **no** (still budget-limited) |
| C(16,6,2) | 10 | **11** (record NOT reached) | **no** |

**Honest reading:** the "reachable records proven optimal" verdict (the exact-producer escalation) holds
for the **4/6 small cells it proved**, but these two larger cells are genuinely harder — and C(16,6,2)'s
record of 10 is **not reached** by either generic greedy or 600s exact (both land at 11). So C(16,6,2) is
a cell where the record came from a *stronger method we have not reproduced within budget*, its
optimality is **open**, and its witness (10 blocks of 6-subsets of {0..15}) is **small and
kernel-renderable**.

### Implication — a concrete narrow-D candidate
C(16,6,2) is exactly the shape ADR 0042 reserved for re-opening Track D: *a specific cell with open
optimality AND a renderable witness*, where our budget producers fall short of the record. Whether 10 is
optimal (no beat) or beatable (a 9-block covering exists) is **unknown** — neither reaching 10 nor
proving it optimal was possible in 600s. This does **not** revive the swing on its own (the odds of a beat
are unmeasured), but it is the first concrete cell that meets the narrow-D precondition, should the
operator ever want to point a stronger producer at it.

## Net
- Snapshot oracle: faithful + current + load-validated. B0 numbers stand.
- Ramsey VT-check: tractable on real structured witnesses.
- Exact cells: 4/6 reachable records proven optimal stands; 2 larger cells remain open at 600s, with
  C(16,6,2) surfacing as a concrete narrow-D candidate (open optimality, small witness, record unreached).
