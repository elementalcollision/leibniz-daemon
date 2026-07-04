# Leibniz — Auditable Capability Roadmap (2026-07-03)

**What this is.** A forward-looking map of Leibniz's capabilities where *every* item carries a
**mechanically-checkable gate** (a GREEN/RED criterion, a kernel-attested artifact, or a named
regression test), an explicit **trust-tier disposition**, and an **honest expected-value** label
(discovery vs. verification-amplification). It is the auditable index over the running log in
[`optimization-roadmap.md`](optimization-roadmap.md) and the rung tickets in [`HANDOFF.md`](../HANDOFF.md);
those hold the depth, this holds the gates. Produced from a 7-track analyst sweep + an adversarial
trust/honesty critique (2026-07-03).

**Standing.** R0–R6 are built; the trust boundary is real and `tests/test_invariants.py` is byte-identical
(last touched at the R0 scaffold, never since). The measured binding constraint is **novelty at the producer**
— autonomous positive-witness table-beating is a measured negative across ~6 probes. The daemon's honest role
is a **vindicated sound verification / non-Q.E.D. decision instrument** (0 unsound; no LLM ever decided),
just validated on a real external target (the MCR whitepaper audit).

**Auditability contract (applies to every increment below):**
- No increment may weaken the trust boundary. `tests/test_invariants.py` stays byte-identical and green;
  any change that would require editing it is a **STOP**.
- Q.E.D. is minted only by `LeanVerifier.discharge`. Precisely: `discharge` is the sole writer of a *fresh*
  `kernel_verified` verdict; `runtime.py` hydration *replays* a persisted verdict via the `Demonstratio`
  constructor (a recall, not a decision). This is now **mechanically enforced** by the H0 sole-writer guard
  (`tests/test_kernel_verified_writers.py`) — see H0 below.
- Trust-touching increments (F2c, an external checker, a large-block PSD primitive) are gated behind a
  dedicated ADR + PreToolUse hook + operator sign-off + a witness round (0044/0045/0046 precedent).

---

## The tracks at a glance

| Track | Capability | Tier | Measured EV | Status |
|---|---|---|---|---|
| **H0** | Trust-integrity hardening (sole-fresh-writer guard + axiom-closure gate) | trust-integrity; no core edit | n/a | ✅ **GREEN** (#268) |
| **T1** | Certificate amplification (Delsarte LP + Terwilliger 3-point SDP) | audit `DUAL_CERTIFICATE_CHECKED` | **amplification** | GREEN, measured DRY for discovery |
| **T2** | The audit→Q.E.D. formalization ladder (F1/F2a done; F2b/F2c open) | audit → (gated) Q.E.D. | amplification | F1+F2a GREEN; **F2b-M2 PSD engine lemma DISCHARGED (clean axioms)**; validator GREEN; full F2b out for external round |
| **T3** | Trust-tier expansion: the ~N≈60 kernel-PSD ceiling & the bridge | audit; expansion = new tier, gated | amplification-enabling | ADR 0047 HOLD |
| **T4** | The organic discovery loop (proposer / faithfulness / prover / novelty) | proposal-side; audit | amplification | CONCLUDED-RED for autonomous novelty |
| **T5** | Daemon as external audit instrument | audit (promulgates nothing) | **measured-positive (n=2)** | GREEN (MCR); audit-runner + P4 kernel-attested (#270); **2nd external target GREEN — SS-RS-GD COLT refutation kernel-verified + erratum caught**; F2b validator on an internal claim |
| **T6** | New-frontier / second-domain scouting | audit | discovery EV measured LOW→ZERO | CONVERGED |
| **T7** | Calculemus reading-room + publishing | non-guarded, read-only | presentation | Tier 4 complete |
| **T8** | *Beyond-Markov process-complexity certificates* | audit | **amplification (measured: T8-c discovery probe = amplification)** | **COMPLETE & ZERO-AUDIT: every property (rank / ∀k infinite order / positive realization) kernel-derived from Lean process definitions** |
| **T9** | *External open-problem corpus* (Cahen–Fontana–Frisch–Glaz CRT + Erdős DB) — tractability ledger, statement formalizations, certificate instruments | audit | amplification | **SCOPED; Problem 41 CERTIFIED (#276); counterexample-certificate domain Tier-1 SHIPPED** — one `certify(object)` over 3 finite-decidable families (monomial-normal / self-ordered / n-absorbing), 7 objects kernel-verified; Tier-2 (attested infinite-ring) scoped (`docs/t9-tier2-attested-scoping.md`); Erdős-367 statement formalized |

---

## H0 — Cross-cutting trust-integrity hardening ✅ GREEN (2026-07-03; `docs/results/h0-trust-hardening-2026-07-03.md`)

The critique's top finding — both guards now landed (cheap, no compute, no core edit):

1. **"No new fresh `kernel_verified` writer" guard ✅** — `tests/test_kernel_verified_writers.py`: an AST scan
   of `leibniz/**/*.py` asserts the `kernel_verified` write set is exactly `{LeanVerifier.discharge` (mints),
   `_row_to_prop` (replays)`}`; a planted second writer fails. Mechanizes the charter invariant previously only
   stated in `CLAUDE.md`.
2. **Axiom-closure honesty gate ✅** — `scripts/export_calculemus.py::axiom_closure`, wired into `--check` +
   `tests/test_axiom_closure.py`: for every claimed-Q.E.D. law it runs `#print axioms` and RED-flags any
   `sorryAx` or axiom outside the standard Lean/Mathlib set. An admitted-axiom scaffold can no longer reach the
   reading-room labeled as discharged. Verified against the real kernel (clean passes; `sorry`/admitted fail).

These must stay green before any F2b scaffold lands.

---

## T1 — Certificate amplification (Delsarte LP + Terwilliger three-point SDP)

- **Capability today.** A complete mechanically-checked upper-bound certificate pipeline for A(n,d): untrusted
  SDP/LP → exact rational simplex (stationarity + nonneg in one solve) → `dual_check` → the real Lean 4.31
  kernel re-checks every PSD block. Six Table I cells kernel-attested (A(19,6)≤1280, A(20,8)≤274, A(23,6)≤13766,
  A(25,10)≤503 first d≥10, A(22,10)≤87, A(26,10)≤886); 18/18 Delsarte LP UB corpus; a separate constant-weight
  Johnson build (Table II gate 3/3, **47/51** cells reproduced — 4 unreproduced, not "complete").
- **Exit test today.** `tests/test_terwilliger_exact_lp.py` (A(19,6)≤1280 exact cert + docker kernel-attest w/
  corrupted-block control), `_kernel_bank`, `_anomaly`, `_kernel_full` (F1), `_delsarte_bank`. GREEN for a new
  cell = `certify_lp` returns certified AND the kernel returns True on every block, False on the corrupted control.
- **Trust.** Audit `DUAL_CERTIFICATE_CHECKED` (ADR 0038/0046). The kernel checks certificate arithmetic; the
  `certOK ⇒ A≤bound` reduction is a deferred bridge lemma (T2). No Q.E.D.
- **Measured EV.** **Amplification.** Reach probes #210 (LP, 0 tightenings) and #99 (3-point, 0 certified
  tightenings); post-D6 frontier cells (27,12)/(28,12) are Delsarte-ties (bound-blocked, not solver-blocked).
- **Next increments.** (a) *Truncated-dual stall-rescue generalization* — audit, widens the exact-tier cell set;
  gate = regression asserting stalled truncations are gated out and zero-blocks certify. (b) F2b/F2c → T2.
- **Do not relitigate.** Table-beating on this family (DEAD); the (22,10)/(26,10) anomaly (CLOSED as our
  dual-source gap, not a Table I error); GMS quadruple (GATE 0 RED); the ~N≈60 ceiling (fundamental, T3).

## T2 — The audit→Q.E.D. formalization ladder

- **Capability today.** F1 GREEN (the *whole* certificate in-kernel: β re-verified vs eq.(7), 55 stationarity
  identities, nonneg, bound — A(19,6) all obligations True, 6/6 corrupted controls False). F2a GREEN (weak
  duality machine-checked in Mathlib: `tw_weak_duality`, `gram_pairing_nonneg`, both controls fail).
- **Exit test today.** `tests/test_terwilliger_kernel_full.py` (F1: all obligations True + all controls False),
  `tests/test_terwilliger_f2a.py` (REPL-gated).
- **Trust.** F1/F2a touch no trusted surface. The gap to a statement *about codes* is F2b (block-diagonalization
  Theorem 1). F2c (Q.E.D. wiring) is the sole trust-touching step, DECIDED-DEFERRED (ADR 0046).
- **Measured EV.** Amplification — the three attested bounds reproduce Table I (Schrijver n≤28).
- **Next increments.** F2b-M1 (forward-only skeleton, admitted lemma) → **F2b-M2 ✅ DISCHARGED (the PSD engine
  lemma, see below)** → F2b-M3 (full sorry-free discharge, empty project-axiom footprint) → F2c (gated). **Each
  gate = `#print axioms` closure** (H0). Full-F2b external formalization round still in flight (brief finalized;
  Aristotle full-M0 = honest 0/1). Consensus cost for the *full* theorem: ~3–6 months.
- **F2b discharge validator ✅ GREEN (2026-07-03; `scripts/f2b_validate.py`, `tests/test_f2b_validate.py`).**
  The M-gate above is now a *mechanical, re-runnable* classifier, not a manual `#print axioms` read: it labels
  any F2b attempt DISCHARGED (only std axioms) / SCAFFOLD (rests on the single named engine lemma) / BROKEN
  (sorry / unexpected axiom / error), verified against the real kernel on three demonstration cases.
- **F2b-M2 — the PSD engine lemma ✅ DISCHARGED, kernel-verified (2026-07-03; `scripts/f2b_engine_lemma_lean.py`,
  `tests/test_f2b_engine_lemma.py`, `docs/f2b/block_diag_posSemidef_iff.lean`).** The self-contained block-
  diagonal PSD-iff `(Matrix.fromBlocks A 0 0 D).PosSemidef ↔ A.PosSemidef ∧ D.PosSemidef` over ℝ is proved with
  **0 sorries and `#print axioms = [propext, Classical.choice, Quot.sound]`** — it classifies **DISCHARGED** under
  the validator above. This supersedes the earlier in-session "not dischargeable" finding: the Finsupp-`PosSemidef`
  wall was dissolved by the plain-function characterization `PosSemidef.of_dotProduct_mulVec_nonneg` +
  `fromBlocks_mulVec` + `isHermitian_fromBlocks_iff` (Mathlib had the Schur-complement `fromBlocks₁₁/₂₂` but no
  clean block-diagonal iff; this fills the gap, inverse-free). **This is the engine lemma only, not full F2b** —
  the Schrijver Theorem-1 block-diagonalization of the 2ⁿ Terwilliger algebra remains the external round.
- **Do not relitigate.** F2c is deferred by ADR 0046; the 2ⁿ×2ⁿ ambient-matrix target (DEAD, GLM); baking
  `IsTripleDistribution` into the algebra (DEAD, Fugu).

## T3 — Trust-tier expansion: the kernel-PSD ceiling & the bridge

- **Capability today.** `lowRankOK` (strict sound generalization of `ldltOK`, ~2× the N ceiling, ~50× smaller
  source); the ~N≈60 wall is measured and **accepted as a deliberate trust boundary** (ADR 0047).
- **Exit test today.** `tests/test_terwilliger_psd_lowrank.py` (valid accepted / corrupted rejected; full-rank
  recovers ldltOK).
- **Trust.** No core edit. **Expansion beyond ~N≈60 is a NEW TRUST TIER**, deferred + gated; if ever revisited,
  an external verified PSD checker is preferred over `native_decide` (which stays forbidden).
- **Measured EV.** Amplification-enabling infra, not discovery. The proof-term probe proved the ceiling is a
  trust-model property, not an engineering gap.
- **Next increments.** (a) Non-promoting `ConstructionVerifier` (exercise the bridge, no core edit); gate =
  valid witness sets `construction_kernel_checked`, hollow/wrong-name/non-empty-axiom sources rejected.
  (b) External-verified-PSD-checker **feasibility spike** (docs only; a soundness-lemma type that type-checks +
  a cost estimate) — only if a live trigger appears. (c) Bit-length/chunked tightening *within* ~N≈60.
- **Do not relitigate.** "Scale the kernel `decide`" (DEAD — order-fixed); proof-term encoding (WORSE);
  Nat-vs-Int (marginal). No live trigger exists (GATE 0 RED + D3).

## T4 — The organic discovery loop

- **Capability today.** A sound producer/checker: reliably yields correct, diverse, **textbook** mathematics
  (the panel produced 12 sound N+1 promulgations with no human on the path — all Fermat-family/elementary).
  Novelty caught structurally (ADR 0031/0032).
- **Exit test today.** `tests/test_invariants.py` (byte-identical) + the novelty/faithfulness regressions.
- **Trust.** Proposal-side; audit. No boundary contact.
- **Measured EV.** **Amplification** — zero autonomous novelty across the widest sweep in the project.
- **Next increments.** (a) *Verification-amplification pipeline integration* — make the measured-GREEN capability
  first-class (`scripts/amplify.py` → kernel corpus); gate = N/N kernel-verified true witnesses + plausible-false
  rejected. (b) Walnut Observatory blind-novelty read (predicted RED). (c) SOS producer-side re-probe — the ONE
  pre-registered re-open gate; GREEN = non-empty (in-reach × box-out × plausibly-novel) in the default arm; a RED
  closes it permanently.
- **Do not relitigate.** Autonomous table-beating; widening the bounded-box DSL to reach novelty; L2
  truth-equivalence novelty (RETRACTED unsound); corpus-mining as a novelty escape.

## T5 — Daemon as external audit instrument

- **Capability today.** First real external target fully adjudicated (MCR whitepaper): 8/8 machine-checked
  verdicts, adversarially re-verified, Chimera-fileable deliverable + a self-describing Codex cycle.
- **Exit test today.** `python3 docs/audits/mcr_audit_artifacts.py` prints `all reproducible artifacts GREEN:
  True`; `tests/test_mcr_audit.py` (z3-gated) locks the verdicts.
- **Trust.** No boundary contact; promulgates nothing (an audit is a record, not a law — ADR 0017).
- **Measured EV.** **Measured-positive, now n=2** (MCR whitepaper + the SS-RS-GD COLT refutation). Positive
  precisely because it is verification-amplification — and the second target even yielded a kernel-caught erratum.
- **Next increments.** (a) ✅ **GREEN (2026-07-03)** — audit-runner harness + regression pack
  (`scripts/audit_runner.py`, `tests/test_audit_runner.py`, `docs/results/audit-runner-t5-2026-07-03.md`): the
  MCR audit is now a re-runnable, CI-guarded instrument (an audit = a spec of `(verdict, artifact)`; the runner
  reproduces the 8 verdicts, 6/8 artifacts re-run and pass). (b) ✅ **GREEN** — the P4 Lean leg is
  kernel-attested via `lean_leg_ok()` (0 errors/0 sorries; corrupted control fails), no longer doc-asserted.
  (c) **Second external target — ✅ GREEN (2026-07-03; n→2).** The daemon adjudicated a *second, independent*
  external target: the **SS-RS-GD refutation** (Yun–Sra–Jadbabaie, COLT-2021 open problem), from the
  `Pengbinghui/pipeline-math` repo (`scripts/ss_rs_gd_lean.py`, `tests/test_ss_rs_gd.py`,
  `docs/colt/ss_rs_gd_refutation.lean`). The refutation's algebraic core is **kernel-verified** (the gap identity
  1.8, positivity, the violation λ_SS > λ_RS on [1/4,1), a concrete witness at q=1/2 — all with only the standard
  axioms), so **Conjecture 1.1 is machine-refuted**. Two by-products vindicate the audit stance: the kernel
  **corrected an LLM scout** (which had falsely flagged a correct SOS identity), and **attested an erratum** in the
  paper's supporting identity (1.7) — which does not affect the main result (the intended inequality λ_RS ≥ μ_RS
  still holds). n=1 EV is now n=2, and *positive* — verification-amplification with a found erratum. (d) also
  GREEN — the F2b discharge validator applied the instrument to an *internal* claim (T2).
  (d) ✅ **GREEN (2026-07-03)** — the same audit instrument applied to an *internal* formal claim: the **F2b
  discharge validator** (`scripts/f2b_validate.py`, T2 above) classifies any F2b discharge attempt via the H0
  `#print axioms` gate. Honest audit verdict on the current F2b state: **SCAFFOLD, not discharged** (the engine
  lemma rests on an admitted lemma; kernel-verified on three demonstration cases). This is an audit *record*,
  not a law — it promulgates nothing and is the acceptance gate for a future external discharge.
- **Do not relitigate.** Autonomous novelty-at-the-producer; routing an audit into Le Leggi; weakening P7 back to
  REFUTED; posting the internal report verbatim.

## T6 — New-frontier / second-domain scouting

- **Capability today.** A 4-way admission criterion (MECHANISM ∧ HEADROOM ∧ ORACLE ∧ NON-COINCIDENCE); covering
  designs built at audit tier (reachable-band records proven optimal, 0 beats over 71 cells).
- **Exit test today.** `tests/test_terwilliger_gms_gate0.py` (GMS kill-gate RED pinned); the covering/Delsarte
  reach regressions.
- **Trust.** Audit throughout.
- **Measured EV.** Discovery EV measured **LOW→ZERO** on every domain taken to a residual gate.
- **Next increments.** (a) Delsarte LP dual-cert **polarity-flip probe P1** — highest-EV remaining discovery bet,
  BUT **only after a NEW provenance gate** (T1 Gate-P) finds ≥3 open cells sourced from a method weaker than the
  candidate — else it relitigates a measured-DRY channel. gate = kernel verifies a rational dual that
  matches/tightens a version-pinned UB; must also assert a floor-below-known-LB is REJECTED. (b) Large-block PSD
  primitive = T3 route-2 (guarded, dormant). (c) Human-supplied frontier-construction amplification onboarding.
- **Do not relitigate.** Table-beating as a new cheap-witness domain (DEAD); the covering swing (not justified);
  GMS build (NO-GO); deletion codes (fail ORACLE).

## T7 — Calculemus reading-room + publishing

- **Capability today.** Tier 4 complete; producer bridge (`calculemus_site.py` + `export_calculemus.py`),
  operator publish gate (ADR 0033), the MCR Il-Lavoro cycle + pipeline-ready fragment.
- **Exit test today.** `pytest tests/test_calculemus_r6.py tests/test_calculemus_site_r0017.py
  tests/test_calculemus_publish_r0033.py -q` → 17 passed.
- **Trust.** Non-guarded, read-only over the ledger.
- **Measured EV.** Presentation — zero discovery.
- **Next increments.** (a) `notify-site.yml` deploy hook (operator-gated). (b) Promote `export_calculemus.py
  --check` to a hard CI regression when Lean is present. (c) Surface cycle rich fields in the renderer.
- **Do not relitigate.** Auto-publishing (settled NON-GOAL, ADR 0008); re-deciding at render time; Python-generated site.

## T8 — Beyond-Markov process-complexity certificates *(proposed; external round returned 2026-07-03)*

- **The bet.** Markov *order* is the wrong invariant; the **Hankel-matrix rank** (prediction-state dimension) is
  the right one. Order-k Markov ⊊ finite-Hankel-rank (finite linear representation / OOM / WFA; **finite-state
  HMMs are the positive subclass** — the panel's correction: finite rank ≠ HMM in general). The MCR-P3 process
  has infinite order yet is a 2-state HMM. First genuinely new *domain* for the certificate architecture since
  covering designs.
- **Certificate shapes (grounded in the capability map, `beyond-markov-witness-review-2026-07-03.md`):**
  (1) Hankel-rank **lower** bounds via a nonsingular rational minor (`bareiss_minors`/`detSignOK`) — MATCH;
  (2) Markov order > K via cross-mult `det≠0` + denominator>0 — MATCH; (3) error floors: **linear** loss via
  Z3-LRA/exact-LP-dual, **quadratic** loss via a PSD/SOS cert (`ldltOK`) — never Z3-NRA; (4) rank **upper** bound
  via the linear-representation **bridge lemma** (`rank_le_of_factor : H=F·B ⇒ rank ≤ r`) — **✅ CLOSED, GREEN
  kernel-verified (2026-07-03)**, `docs/results/beyond-markov-rank-upper-2026-07-03.md`; composed with (1) it
  gives `rank = r` exactly; (5) process validity via a rational **HMM** (general-OOM validity is undecidable —
  DIVERGE, prefer HMMs).
- **Panel outcome (7 reviewers, GLM empty).** Two v1 errors corrected: **BM-2 is impossible on a stationary
  process (retracted)**; and **infinite-order is Q.E.D.-reachable via a recurrence + induction bridge lemma, NOT
  Observatory** (F2a already proves non-`decide` Mathlib theorems sorry-free through the REPL — the "Observatory
  ceiling" was our own pessimism). **Novelty = the end-to-end Lean-kernel trust chain**, not the math (textbook:
  Blackwell–Koopmans, Carlyle–Paz, Fliess, Jaeger, Crutchfield–Shalizi, Hsu–Kakade–Zhang, Rissanen).
- **EV split.** Hankel-rank separations are **verification-amplification** (unanimous). The **one discovery-shaped
  lever** (convergent — Qwen, Fugu Ultra, Kimi): the **Minimal Positive Realization Problem** — HMM/nonnegative
  rank is often > Hankel rank (NP-hard); a Farkas/LP-infeasibility cert that "no r-state positive HMM realizes
  this process" is genuinely open *and* certificate-shaped, and its checker already exists (`exact_simplex`
  infeasibility). Encoding is the unbuilt work.
- **Auditable increments.** (a) **T8-a ✅ GREEN, kernel-attested (2026-07-03)** — the minimal HMM certificate
  suite (validity + Hankel rank-lower minor + order>K) is built and the real Lean 4.31 kernel accepts the valid
  cert and rejects the corrupted control for BM-1 and the even process (`scripts/beyond_markov_cert.py`,
  `tests/test_beyond_markov_cert.py`, `docs/results/beyond-markov-t8a-2026-07-03.md`); audit tier, no trust
  surface touched. (b) **T8-b ✅ GREEN, kernel-verified (2026-07-03)** — the recurrence + induction bridge lemma
  (`two_step_recurrence_nonzero`, reusable for any two-step recurrence incl. geometric decay) + the even-process
  (q=1, **infinite Markov order**) and BM-4 excess-loss (q=1/2) instantiations elaborate 0-errors/0-sorries
  through the Mathlib REPL, all controls fail (`scripts/beyond_markov_recurrence.py`,
  `docs/results/beyond-markov-t8b-2026-07-03.md`). "order > K" is now a kernel `∀k` theorem; the
  process-identification stays audit (full in-Lean identification is the F2b-scale follow-on). (c) **T8-c ✅ GREEN, kernel-certified (2026-07-03) — resolved as AMPLIFICATION** — the necklace chain (valid
  stationary rational process, Hankel rank 3) has minimal positive realization **4 > 3**, kernel-certified via a
  **fooling-set** lower bound + rank minor (`scripts/beyond_markov_mprp.py`,
  `docs/results/beyond-markov-t8c-2026-07-03.md`), both controls rejected. Three honest corrections: the sound
  tool is the **combinatorial fooling `decide`**, NOT `exact_simplex`/LP (the panel's framing was wrong);
  deciding nonneg-rank is **ExR-complete** (deferred SOS territory), so autonomous *search* is unreachable —
  only *verification* of a supplied separation; and the gap is minimal (+1, fully-observed), **not** the deep
  finite-OOM-no-finite-HMM phenomenon (Jaeger's probability clock — irrational, **DEFERRED**). Verdict: the one
  discovery-shaped lever is amplification; **T8 is a verification-amplification domain**.
- **Full in-Lean process identification (rank story) ✅ GREEN, kernel-verified (2026-07-03)** — the F2b-scale
  follow-on, delivered for rank: the even process is **defined in Lean from its OOM operators** and its Hankel
  rank is **derived = 2 in the kernel** (`hankel_block_rank_le`: any r-dim OOM ⇒ every finite Hankel block has
  rank ≤ r, via `Tprod` being a monoid hom; `eB_det = 1/18` computed in-kernel ⇒ rank exactly 2). Lifts
  rank-upper/rank-exact from **audit to Q.E.D. about the actual process** (`scripts/beyond_markov_process_lean.py`,
  `docs/results/beyond-markov-process-lean-2026-07-03.md`).
- **Full in-Lean INFINITE ORDER ✅ GREEN, kernel-verified (2026-07-03)** — the even process's **infinite Markov
  order** is now derived in-kernel from its OOM operators: `eOp 1 · eOp 1 = ½I` ⇒ appending "11" halves every
  `P` ⇒ the cross-multiplied order-k gap obeys `D_{k+2}=¼D_k` (base cases `−1/18, 1/36` evaluated in-kernel),
  closed by the T8-b recurrence bridge (`even_infinite_order : ∀k, D_k ≠ 0`). Closes T8-b's audit link
  (`scripts/beyond_markov_infinite_order_lean.py`, `docs/results/beyond-markov-infinite-order-lean-2026-07-03.md`).
  **Both** the even process's rank=2 and its infinite order are now kernel-derived from its 2-dim OOM — the
  canonical infinite-order-but-finite-dimension separation, end-to-end.
- **Full in-Lean POSITIVE REALIZATION ✅ GREEN, kernel-verified (2026-07-03)** — the last audit-linked
  follow-on, closed. T8-c's fooling-set certificate is lifted from a **boolean** predicate to **proven
  theorems**: `fooling_le_of_nonneg_factor` (fooling set of size t ⇒ every nonneg factorization has inner dim
  ≥ t, via the injectivity argument), `necklace_no_rank3_nonneg_factor` (nonneg-rank(NM) ≥ 4),
  `hankel_nonneg_factor` (positive OOM ⇒ nonneg Hankel factorization), and the composition
  `positive_realization_of_NM_needs_4_states` (**no ≤3-state positive HMM/OOM produces the necklace
  co-occurrence matrix NM**). (`scripts/beyond_markov_positive_realization_lean.py`,
  `docs/results/beyond-markov-positive-realization-lean-2026-07-03.md`.) **All three audit-linked follow-ons
  (rank / infinite order / positive realization) are now kernel-verified.**
- **Necklace tie-off ✅ GREEN, kernel-verified (2026-07-03) — the whole track is now ZERO-AUDIT** — the
  necklace chain is defined as an OOM in Lean (`nInit`/`nOp`/`nFin`) and its positive-realization gap is derived
  from that definition: `necklace_block_no_rank3_nonneg_factor` (its own block's size-4 fooling set, evaluated
  in-kernel), `necklace_positive_realization_needs_4` (no ≤3-state positive HMM/OOM realizes it), and
  `necklace_is_positive_realization` (it IS a 4-state one) ⇒ minimal positive realization = 4 > 3 = rank
  (`scripts/beyond_markov_necklace_lean.py`, `docs/results/beyond-markov-necklace-lean-2026-07-03.md`). **Every
  beyond-Markov property of both witness processes (even process: rank=2, infinite order; necklace: positive
  realization gap) is now kernel-derived from a Lean process definition — no Python audit in the trust chain.**

---

## Honest-negative register (measured-dead — do not re-open without a NEW gate)

Autonomous positive-witness table-beating (~6 probes); the bounded-box faithfulness DSL as a novelty lever; L2
truth-equivalence novelty (unsound); GMS-2012 quadruple build (GATE 0 RED); scaling the kernel `decide` past
~N≈60; `native_decide`; deletion codes as a second domain; auto-publishing. Each has a recorded finding; a
re-open requires a *new* falsifiable gate, not a re-run.

## Sequencing (cheapest-falsifiable-gate-first)

1. **H0** — the axiom-closure gate + no-new-writer guard (low $, no compute, pure trust-integrity). Before any F2b scaffold.
2. **Cheap amplification hardening** — T1 truncated-dual generalization; T5 kernel-attest the P4 leg in CI; T7 `--check` as hard CI.
3. **The two cheap discovery re-measurements, run as clean pre-registered kills** — T6-P1 Delsarte *only after* T1 Gate-P fires GREEN; T4 Walnut blind-novelty read (pre-written decision rule).
4. **The one genuine measurement** — T5 second external target (is n=1 EV real?); must report HONEST-NEGATIVE if it fails the 50% threshold.
5. **Beyond-Markov (T8)** — external round → vetted conjectures → a first Hankel-rank/separation certificate probe.
6. **Deferred, gated, not funded now** — T2 F2b-M1/M2/M3 (months of expert Lean, zero discovery; fund only as a TCB-showcase decision); T3 external-checker spike + route-2; F2c.
7. **Never without a new gate** — autonomous table-beating; GMS quadruple; 2ⁿ-formulation F2b; `native_decide`.

## Perennial operator decisions

- **Trust tier for reproductions:** stay audit `DUAL_CERTIFICATE_CHECKED` vs. fund the F2b→F2c ladder to Q.E.D.
  (a trust-depth showcase, not new math).
- **Fund discovery or amplification?** The measured evidence says amplification is the product; the only
  discovery-shaped bets left (T6-P1, T8) are cheap probes, not builds — run them as pre-registered kills/gates.
