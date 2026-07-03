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
  constructor (a recall, not a decision). **There is currently no mechanical guard test enforcing "only
  `discharge` mints a fresh verdict"** — see H0 below.
- Trust-touching increments (F2c, an external checker, a large-block PSD primitive) are gated behind a
  dedicated ADR + PreToolUse hook + operator sign-off + a witness round (0044/0045/0046 precedent).

---

## The tracks at a glance

| Track | Capability | Tier | Measured EV | Status |
|---|---|---|---|---|
| **T1** | Certificate amplification (Delsarte LP + Terwilliger 3-point SDP) | audit `DUAL_CERTIFICATE_CHECKED` | **amplification** | GREEN, measured DRY for discovery |
| **T2** | The audit→Q.E.D. formalization ladder (F1/F2a done; F2b/F2c open) | audit → (gated) Q.E.D. | amplification | F1+F2a GREEN; F2b out for external round |
| **T3** | Trust-tier expansion: the ~N≈60 kernel-PSD ceiling & the bridge | audit; expansion = new tier, gated | amplification-enabling | ADR 0047 HOLD |
| **T4** | The organic discovery loop (proposer / faithfulness / prover / novelty) | proposal-side; audit | amplification | CONCLUDED-RED for autonomous novelty |
| **T5** | Daemon as external audit instrument | audit (promulgates nothing) | **measured-positive (n=1)** | GREEN (MCR) |
| **T6** | New-frontier / second-domain scouting | audit | discovery EV measured LOW→ZERO | CONVERGED |
| **T7** | Calculemus reading-room + publishing | non-guarded, read-only | presentation | Tier 4 complete |
| **T8** | *Beyond-Markov process-complexity certificates* | audit | amplification (T8-c = discovery probe) | **T8-a GREEN kernel-attested; panel processed** |

---

## H0 — Cross-cutting trust-integrity hardening (recommended FIRST; cheap, no compute)

The critique's top finding. Two small guards that must land **before** any admitted-axiom scaffold (F2b) so a
scaffold can never be mislabeled:

1. **"No new fresh `kernel_verified` writer" guard.** A test (grep/AST) asserting that `discharge` is the only
   site that mints a *fresh* verdict; the `runtime.py` constructor is whitelisted as replay-only.
   **Gate:** GREEN = the guard passes on HEAD and RED-flags a planted second writer. Tier: pure trust-integrity,
   no core edit.
2. **Axiom-closure honesty gate.** A `#print axioms` closure assertion, wired into a test **and** into
   `export_calculemus.py --check`: GREEN iff the target theorem's axiom footprint is exactly the intended set
   (empty project-axioms for a discharged law; the single named admitted lemma for an F2b scaffold), RED on any
   stray `sorryAx` or unlisted axiom. **Gate:** an admitted-axiom scaffold cannot reach Observatory/reading-room
   labeled as discharged. Tier: audit, read-only.

Nothing else on the roadmap that produces an admitted axiom should land until H0 is green.

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
- **Next increments.** F2b-M1 (forward-only skeleton, admitted lemma) → F2b-M2 (discharge the PSD engine
  lemma / M0) → F2b-M3 (full sorry-free discharge, empty project-axiom footprint) → F2c (gated). **Each gate =
  `#print axioms` closure** (H0). External formalization round in flight (brief finalized; Aristotle M0 = honest
  0/1). Consensus cost: ~1–2 wks admitted-wiring, ~3–6 months full discharge.
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
- **Measured EV.** **Measured-positive — but n=1.** Positive precisely because it is verification-amplification.
- **Next increments.** (a) Audit-runner harness + regression pack; gate = re-drives MCR fixtures to
  byte-identical verdicts. (b) Kernel-attest the P4 Lean leg in CI (gated). (c) **Second external target** — the
  only increment that is genuine discovery *about the track* (is n=1 EV real?); gate = every verdict backed by a
  re-runnable artifact + independent adversarial re-verify + HONEST-NEGATIVE if <50% of sub-claims reduce to a
  mechanical artifact.
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
  needs a linear-representation **bridge lemma** (`linear_rep ⇒ hankel_rank_le`, an F2b-style slice) — DIVERGE;
  (5) process validity via a rational **HMM** (general-OOM validity is undecidable — DIVERGE, prefer HMMs).
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
  surface touched. (b) **T8-b** the recurrence bridge lemma for infinite order (the even-process separation dets
  alternate `−2,1,−2,1` — a clean two-step geometric recurrence, the ideal first target), gate = `#print
  axioms` closure on a `∀k` theorem (empty project axioms), Q.E.D.-reachable (F2b pattern). (c) **T8-c
  (discovery probe)** MPRP: reproduce a known HMM-rank > Hankel-rank gap via an `exact_simplex` infeasibility
  certificate; GREEN = the LP is certified infeasible for r-state and feasible for (r+1)-state; RED = no
  reachable gap — a cheap pre-registered kill, like the covering probes.

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
