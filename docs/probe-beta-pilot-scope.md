<!--
Probe β pilot result (mechanism validation) + the full-build scope and pre-registered GREEN/RED.
The witnesses' best-remaining autonomous lever: finite-witness SEARCH with OBJECTIVE novelty
(beats a public table-of-record). Provenance: scripts/probe_beta_cwc_pilot.py (+ tests).
-->

# Probe β — finite-witness record factory: pilot result + full-build scope

**Status:** pilot run, 2026-06-26. **Mechanism VALIDATED; full build scoped & pre-registered (not yet
built).** Probe β is the one autonomous lever the four enumerate-and-decide probes never tested: replace
LLM theorem-*ideation* with **search over a finite object space whose novelty is OBJECTIVE** — a witness
that *beats a public table-of-record*. Untrusted search proposes; a checker decides; novelty = improves the
best-known entry. This restores the propose/decide split and gives the objective novelty criterion the
"non-named" enumerate probes lacked (Probe α's name-detector false-negatived 8/8 — the α lesson).

## Pilot (mechanism validation) — GREEN
Domain: binary constant-weight codes `A(n,d,w)` (witness = list of w-subsets; distance `2(w−|A∩B|)`).
`scripts/probe_beta_cwc_pilot.py` ran untrusted greedy+restart search on **8 cells whose optimum is
provably/derivably known** (matchings, packings, and the Fano/STS(7) Johnson-bound optimum), each result
checked by the reference verifier:

- **8/8 reached the known optimum**, including **A(7,4,3)=7 (the Fano plane)** — a genuine combinatorial
  design, not a trivial packing.
- The **verifier is sound on every code found** (it is the trust-critical re-check; pinned by
  `tests/test_probe_beta_cwc.py`: accepts Fano, rejects too-close pairs / wrong weight / duplicates /
  out-of-range symbols; the search is untrusted and only ever checked).

So the **end-to-end pipeline works** (search → verify → compare-to-oracle) and cheap search reaches known
optima for small cells. **What the pilot does NOT show:** it does not *beat* a record (the cells sit at the
optimum), the cells are small (cheap greedy will fall short at the larger cells where records are
beatable — that needs CP-SAT/ILP), and the oracle here is a hand-curated *provably-correct* slice, not the
automated table-of-record the full build requires.

## Full-build scope (the three pieces, in trust order)
1. **Lean witness-checker (the trusted re-check) — BUILT + VALIDATED (2026-06-26).** The Python verifier
   mirrored as a self-contained **core-Lean** (no Mathlib ⇒ minimal TCB, fast) theorem
   `validCWC witness n d w M = true`, kernel-checked by `decide` (pure kernel — NOT `native_decide`, which
   would put the compiler in the TCB). `scripts/probe_beta_cwc_pilot.py::render_cwc_lean` emits it and
   refuses to render a false statement. **Validated end-to-end against the real Lean 4.31 kernel**
   (Docker-gated tests in `tests/test_probe_beta_cwc.py`): the **Fano `A(7,4,3) ≥ 7` theorem is
   kernel-ACCEPTED** (genuinely Q.E.D. — the witness *is* the proof, the first Q.E.D.-bearing result of
   the whole discovery arc), and a **too-close pair claimed at `d=4` is kernel-REJECTED** (`decide` proved
   it false — sound + non-vacuous). Dual-use: this *is* the checker verification-amplification needs for
   "verify this claimed code."
   - **Finding for the full build (triviality gate):** `decide` is in `lean_cli.DEFAULT_TRIVIAL_TACTICS`,
     so although the kernel sets `kernel_verified=True`, the downstream triviality gate would **quarantine**
     a CWC witness theorem as "closed by a trivial tactic." A record-beating witness closed by `decide` is
     *not* trivial — so the full build needs a **witness-non-triviality carve-out** (e.g. recognize a
     decide over an explicit table-beating witness as non-trivial) before such a theorem can be promulgated
     rather than quarantined. This is an ADR-level decision for the full build, surfaced here.
2. **Automated table-of-record oracle (the α lesson) — BUILT + VALIDATED (2026-06-26).**
   `scripts/cwc_table_oracle.py` parses Andries Brouwer's A(n,d,w) lower-bound tables (BSSS 1990 +
   Brouwer–Etzion 2011) into a committed snapshot (`docs/results/brouwer_cwc_lower_bounds.json`, **839
   cells, d∈{4,6,8,10,12,14,16,18}**, with fetch provenance: URL + date + page sha256). Novelty =
   `is_improvement(n,d,w,found)` ⇔ `found > best_known(n,d,w)` — **automated lookup, never LLM-judged**.
   The α safeguard is enforced: `load_snapshot` VALIDATES against ground-truth anchors (Fano A(7,4,3)=7,
   STS(13) A(13,4,3)=26, …) + monotonicity-in-n and **refuses a snapshot that fails**; out-of-table cells
   (trivial small-w matchings/packings Brouwer omits) return **None** (never a fabricated bound, never a
   false novelty claim). 0 validation violations on the live parse. Refreshable via `build_snapshot`.
3. **Untrusted heavy search.** CP-SAT / ILP / SAT (cvxpy is for SOS; here it's e.g. OR-Tools CP-SAT or a
   MaxSAT encoding) + symmetry breaking + local-search repair, on a pre-registered set of **non-tight**
   cells. LLM may propose encodings / symmetry breaks / restart schedules (proposal-only).

## Pre-registered full GREEN / RED
- **GREEN:** ≥1 cell where the pipeline produces a **Lean-kernel-checked witness that strictly beats the
  automated table-of-record's best-known lower bound**, confirmed by a domain expert as not already known.
  → a genuinely-novel, Q.E.D., autonomous result exists; the search track is alive.
- **RED:** after a pre-registered budget over the non-tight cells, **0** strict improvements (only
  matches/rediscoveries/known values) → record-beating needs more than this pipeline; conclude the
  autonomous search track and pivot wholly to verification amplification.
- **Caveat (honest):** even GREEN yields *computational-record* novelty (a better witness), not
  conceptual novelty — the human panel decides whether that counts (invariant 4). And matching ≠ beating:
  the pilot's 8/8 is reach, not improvement.

## Disposition
The pilot clears the mechanism gate, so the full build is *justified* but it is a real, heavier slice
(Lean checker + automated oracle + CP-SAT, partly billable/operator-run). **Verification amplification
remains the strategic home regardless** (witnesses' unanimous #1); Probe β is the budgeted *side*-track
that decides whether a narrow autonomous record-factory lives alongside it. Trust boundary untouched;
`tests/test_invariants.py` byte-identical.
