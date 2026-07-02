# Optimization Roadmap (post-R6)

The capability ladder R0–R6 is built: the trust boundary is real and the daemon
runs end-to-end live. The remaining work is **making it a productive discovery
engine** without ever weakening the boundary. Each optimization is captured as a
**Proposed** ADR so it can be approved deliberately before implementation (the
project's discipline: decisions get an ADR, and trust-guarded changes get operator
sign-off via the PreToolUse hook).

## Novelty frontier — measured conclusion (2026-06-25)

The post-R6 binding constraint was **novelty** (the daemon soundly *re-proves* textbook math but
does not *discover*). Two independent levers were then **built and measured** against a blind
4-rater human novelty panel, not argued:

- **Proposal source** (ADR 0034): mining true computed patterns vs. steering. A clean A/B —
  mining **doubled yield** (13→26 promulgations) and produced **0 genuinely-novel** laws.
- **Contract grammar** (ADR 0035 Stage A): soundly taught the faithfulness gate a new genre,
  `a^n mod m` (symbolic exponents, via multiplicative-order period reduction). The genre **moved**
  (16/23 promulgations in the new genre; structural coverage 100%→30%) and produced **0
  genuinely-novel** laws (standard cyclic-group facts).

**Conclusion (triangulated, re-checkable; refined 2026-06-25 after a 5-model external review):** the
bottleneck is **neither the proposer nor the grammar** — it is the faithfulness **test**: a
*pointwise, bounded-box* `[0,64]` linter over a tiny arithmetic DSL, used as the sole faithfulness
arbiter, can only certify elementary, locally-checkable facts. This is **not** a property of
mechanical trust in general — a small kernel can check arbitrarily deep proofs (Flyspeck /
Feit–Thompson / Robbins), so bounded *trust* ≠ bounded *domain*. The escape that preserves "nothing
false gets `Q.E.D.`" is **proof-carrying faithfulness**: kernel/CAS-checked *certificates* of the
statement↔claim link (including exact-**unbounded** algebraic-identity classes), with bounded Z3
demoted to lint; the residual gap then relocates to *validation* (human-intent → formalized-claim),
the right and auditable place. Scoped in **ADR 0036**. Soundness held throughout every experiment.

Disposition: the novelty quest is **paused with a measured finding** (ADR 0034 §12, ADR 0035 §7;
public account in `docs/cycles-report-novelty-frontier.md`). Both levers remain **sound and
opt-in/default-off** — useful as *yield* levers (proving large volumes of true elementary number
theory, e.g. seeding a Lean library) if breadth, not novelty, becomes the goal.

## Sound-backend discovery arc — CONCLUDED (2026-06-26)

The 0625 conclusion said the bottleneck was the faithfulness **test** (the bounded `[0,64]` box) and
the escape was **proof-carrying faithfulness** — pluggable *sound backends* that decide
unbounded/exact classes the box cannot (ADR 0036 → the `SoundFaithfulnessBackend` protocol, ADR 0037).
That escape was then **built and measured**, crawl-then-walk, each behind a measure-before-build gate:

- **Crawl — Walnut (automatic-sequence FO): built, run live.** Trust machinery validated end-to-end
  across three runs (3 artifacts filed → 2 caught by the ADR 0039 lint → 0 unsound, diverse, faithful).
  Run-3 = **11 sound, diverse, faithful decided records, all textbook** (12-agent verification, 0
  plausibly-novel). ADR 0038 (non-Q.E.D. Observatory tier) + ADR 0039 (faithfulness lint + formal-first).
- **Walk — SOS/Positivstellensatz: probed, build DEFERRED.** Soundness + box-OUT reach GREEN (exact
  rational re-check proven stdlib-only; reaches `∀x∈ℝⁿ`; and a genuinely-**Q.E.D.** *prover* seam exists,
  unlike Walnut). But the novelty go/no-go is **RED**: 0/12 in-reach + box-out + plausibly-novel in both
  default and frontier-steered arms (ADR 0037 §8/§8.1).

**Concluded finding (the capstone — `docs/discovery-ceiling-cross-backend-finding.md`):** across **two
independent sound backends**, the *soundly-checkable **and** finitely-encodable region is the textbook
region.* A perfect anti-correlation held — everything in-reach was textbook; everything plausibly-novel
left the backend's encodable class (graphon/flag moment bodies, non-existence meta-statements). The
binding constraint has moved one level deeper and is now empirically pinned: **novelty at the
*producer* — a structural ENCODING gap — not soundness, reach, or prover power.** The escape worked (the
box is no longer the wall); it revealed the next wall.

**Disposition:** the sound-backend discovery arc is **concluded with a measured finding.** The daemon's
honest standing: a **vindicated sound verification / non-Q.E.D. decision instrument** behind an unbroken
trust boundary (0 unsound across both backends; no LLM ever decided; `tests/test_invariants.py`
byte-identical throughout), that reliably produces correct, diverse, **textbook** mathematics — not (yet)
a novel-discovery engine.

- **More sound backends will not help** — the constraint is the producer, confirmed twice. The **kernel
  bridge** (the "run" rung, task #54) stays **gated** for the same reason; this finding strengthens, not
  weakens, that gate.
- **Re-open gate:** the SOS build (and the discovery quest generally) goes GREEN only when a re-run of the
  WALK novelty micro-probe shows a non-empty in-reach + box-out + plausibly-novel intersection in even the
  default arm — which requires **producer-side** work (a flag-algebra/graphon-moment encoder that emits
  finite SDP-ready objects; an in-loop symbolic self-check to kill false/misformalized claims), **not**
  another checker. That is the one identified lever left, a substantial domain-specific bet, and is
  **not** authorized here.

## Witness round + Probe α — the producer-bias confound, tested and closed (2026-06-26)

A 7-model external-witness round (`docs/external-witness-round-synthesis-2026-06-26.md`) narrowed the
above conclusion: maybe the wall was the LLM *producer's* catalogue bias, not finite-encodability. The
test — **Probe α, the zero-LLM enumeration audit** (`docs/probe-alpha-result-finding.md`,
`docs/results/probe_alpha_result.json`): remove the LLM, exhaustively enumerate un-named uniform morphisms,
have Walnut decide power-freeness of their fixed points. Result (adversarially verified, run `wyfd15i8b`):

- **The decider is sound** — 61/61 decided-TRUE prefix-clean (0 contradictions), 83/83 decided-FALSE
  corroborated; 12/12 k=3 exponents match Khodier 2026 (Waterloo) Table 5.1's published critical exponents.
- **Two slogans, separated:** *"unreachable unless the LLM names it"* is **falsified** (36 sound, aperiodic,
  LLM-never-proposed decided-true theorems exist). But *"soundly-checkable ∧ finitely-encodable ⇒ textbook"*
  — the binding claim — is **corroborated, not broken**: 8/8 sampled survivors are catalogued OEIS sequences
  (0 un-catalogued); the k=3 family is fully prior art (A064990 Mephisto Waltz is stated 4th-power-free in
  the Allouche–Shallit textbook). The probe's "non-named" was a false negative of its own detector.
- **Shallow by construction** (min exponent 3-or-4; integer-only e∈{2,3,4} forecloses critical-exponent
  surprises; 75% survival = generic). Only sliver: a ~2–3 k=2 ternary theorem-level cases, exercise-class.

**This is the fourth converging probe** (genre A/B, Walnut run-3, SOS, zero-LLM enumeration) and the
strongest: removing the LLM still yields catalogued/textbook. **Autonomous discovery by "enumerate +
decide the cheap questions" is concluded as a measured negative.** The only remaining autonomous lever is
**search over externally-meaningful objects with an automated table-of-record oracle** (Probe β — a *side*
track, not the main line); **verification amplification stays the strategic home.** Per invariant 4 the
novelty verdict on the thin sliver is the human panel's, not an agent's.

## Probe β + the autonomous arc — CONCLUDED (2026-06-26)

The remaining autonomous lever from Probe α — *search over externally-meaningful objects with an automated
table-of-record oracle* — was then built and swept end-to-end on **binary constant-weight codes**
(A(n,d,w) lower bounds vs Brouwer's public table, 839 cells). This removed the encoding excuse: the
witnesses **are** finite, self-contained, Lean-checkable, and novelty is an objective lookup. So the
*producer's construction method* became the variable, and it was swept exhaustively:

- **Exact** (CP-SAT max-clique) → matched/proved-optimal, **0 beats**; even found only 30 vs known 42 on
  A(14,6,6) (a strong solver can't match a clever construction).
- **Heuristic** (greedy + local search) → *weaker* than CP-SAT (25 on A(14,6,6)), **0 beats** (kills the
  naive-parallel-construction sleeper).
- **Structural** (automorphism-prescribed: cyclic/affine/subgroups) → the positive: reached **42 instantly**
  on A(14,6,6) and **MATCHED 41/78 (53%) of records** where brute search plateaued — **0 beats**.
- **Richer-structural** (multiplier-subgroups/dihedral/fixed-point) → closed 6 more near-misses to MATCH,
  pushed A(21,6,4) to **one codeword short (30 vs 31)** — **0 beats**.

**The refinement this adds:** even with encoding free, the producer constraint holds — **matching records
is structural; beating them is research-grade.** The first Q.E.D. of the whole arc landed here (a
kernel-accepted `A(7,4,3) ≥ 7` witness; a false witness kernel-rejected), and two reusable sound assets
ship (the Lean witness-checker + the automated table oracle), both exactly what verification amplification
needs.

**Disposition — the autonomous discovery arc is concluded.** Three independent sound backends (Walnut,
SOS, CWC record-factory), one consistent verdict: the daemon reliably produces correct, diverse
mathematics behind an unbroken trust boundary (22 PRs #140–#161; `tests/test_invariants.py` byte-identical
throughout; no LLM ever decided) and does **not** autonomously reach novelty — the constraint is the
producer. Full synthesis: **`docs/autonomous-discovery-arc-capstone.md`**.

- **Strategic home: verification amplification** (human proposes frontier content; daemon soundly checks) —
  the built assets already support this mode today.
- **The last lever — FunSearch learned construction — was pulled (operator GO) and is RED too
  (2026-06-27).** A bounded CPU-first tranche: an LLM (`qwen/qwen3-coder-next`) proposed construction
  *programs* → untrusted-code sandbox → `verify_cwc` → post-Rosin oracle → kernel re-check on any beat.
  **240 programs / 12 pre-registered cells / 0 records beaten** (matched 11/12; out-reached the
  structural baseline on 5; below it on the one open flagship cell). Closed per the pre-registered stop
  rule — a bounded-tranche RED, re-open only on a *separate* GO (GPU/island, stronger model, wider
  cells). Detail: `docs/funsearch-pilot-result-finding.md`. The reusable assets (sandbox, LLM-free
  evaluator, harness, post-Rosin oracle cross-check) stand.
- **Kernel bridge (task #54) stays gated.** A fourth backend faces the same producer constraint, now
  confirmed three times.

## ADR 0041 tool-use substrate + Gate D0 — built, and the producer-wall confirmed (2026-06-27)

ADR 0041 hardened the trust boundary for *tool use, tool building, and research ingestion* and shipped
its first four phases, all State-1 (autonomous, TCB+0): the tool seam (`leibniz/tools/`), FunSearch
unified as the first `SandboxedTool`, sound research-seeding (`leibniz/seeds.py`, FLOOR raise-only), and
seed intake to proposer seams only (`leibniz/seed_intake.py`). Then its falsifiable precondition,
**[Gate D0](gate-d0-producer-wall-finding.md)**, ran and came back **RED**: exact CP-SAT found + the Lean
kernel verified the record on 5/5 cells the daemon's structural search missed (incl. A(21,6,4) 30→31).
**No representation gap; the producer is the wall; stronger producers match records but never beat them**
(and where exact ran to optimality the record is *proven optimal* — nothing to beat). Autonomous novelty
stays RED. Disposition recorded in ADR 0041 (Phases 5–6 frozen as autonomous-novelty bets).

## Post-D0 program — verification amplification spine, second-domain scout, decider-admission (2026-06-29)

Operator decision after D0 RED: pursue the three preconditions that make a producer-strength swing
*meaningful*, sequenced **A → B → C → meaningful-D**. Scoped in **[ADR 0042](adr/0042-post-d0-program.md)**:

- **Track A — verification amplification as the spine** (build first; highest certainty). Batch intake →
  existing sound audit path (`verify_cwc → render_cwc_lean → Lean kernel`) → a provenance'd
  kernel-checked corpus + reading-room. Audit-tier, never promulgates. *(A1 in flight.)*
- **Track B — second-domain scout.** ✅ **Gate B0 MEASURED (2026-06-29):** the producer wall is
  *domain-specific*. Triangulated (7-model panel + 43-agent scout + 4 zero-spend probes), the criterion
  sharpened to a 4-way conjunction (MECHANISM ∧ HEADROOM ∧ **ORACLE** ∧ NON-COINCIDENCE). **Covering
  designs** and **Ramsey** clear it; deletion codes + LABS do not (oracle leg). **Recommended B1 =
  covering designs** (LJCR single DOI-pinned oracle; 5,460 small-witness gap≥2 cells; simplest sound
  verifier). Residual gate before any billable swing: a CPU reproduction probe. Full finding:
  `docs/gate-b0-second-domain-finding.md`.
- **Track C — sound decider-admission** (ADR 0041 Phase 6), aimed at amplification: admit a *verified*
  stronger checker as a State-2 decider so a re-checked certificate becomes PASS not DEFER. ✅ **DESIGNED
  (ADR 0044, 2026-06-30):** a kernel-backed valid-construction decider (covering-first), thin-over-the-
  kernel, with the §2.2 ritual + a live adversarial-review demo. PROPOSED, awaiting per-kind operator
  sign-off; the two admission edits (`register_decider` + `trust.py` allowlist) are operator-only and not
  performed. Reviewable machinery landed (covering decider pieces, NOT registered).
  **Integration scoped (ADR 0045, 2026-06-30):** how a construction becomes a `Propositio` through the
  promulgation pipeline (proof=kernel, faithfulness=admitted decider, novelty=table oracle). A 3-vector
  adversarial review found the first draft UNSOUND (3 CRITICAL/HIGH); the corrected design (locked Lean
  prelude, E7-enforcing faithfulness route, tri-edge statement binding, validated oracle, release-only
  carve-out) is folded in. One must-fix landed immediately: covering oracle snapshot validation
  (ground-truth anchors + Schönheim floor + RAISE) — a real defect in shipping code.
  **PROOF EDGE DEFERRED — 8/8 witness round (ADR 0045 §10, 2026-06-30):** the `LeanVerifier.discharge`
  construction branch (the sole `kernel_verified` writer) went to an 8-model external panel; *unanimous*
  verdict = **defer** — editing the trust core for **dormant** infrastructure (no reachable record beat,
  per Track D) is negative-EV, and even the corrected §2 design was judged too source-text-centric. The
  panel's corrected design (generate-from-typed-data, object-hash tri-edge binding, AST/`Environment`-diff
  guard, empty-axiom-closure audit, semantically-bridged hash-pinned prelude, the actual-claim/existential
  theorem, a certificate architecture for large cells) is recorded in ADR 0045 §10 for when a beat
  arrives. **Disposition: constructions stay audit-tier; discharge HELD; `test_invariants.py`
  byte-identical.** The constructive intermediate (a non-promoting `ConstructionVerifier` /
  `construction_kernel_checked`) is available if wanted before a beat.
- **Track D — the producer-strength swing**, made meaningful by A (verify a beat) + B (beatable frontier)
  + C (admit a stronger producer). Operator-gated, billable. ✅ **Reproduction gate GREEN (2026-06-29):**
  a generic baseline reproduces the LJCR best-known on 6/10 pre-registered cells (9/10 within 2 blocks),
  so the producer *reaches the frontier* (unlike CWC) — the swing is now a priced, operator-gated bet
  (reproduction ≠ beating). Finding: `docs/covering-reproduction-probe-finding.md`.
  **Escalation (2026-06-29):** "stronger CPU producer first" → an exact CP-SAT set-cover beats nothing
  and **proves 4/6 reachable records optimal** — the Gate-B0 headroom was Schönheim weakness, not
  beatable slack. **The swing is not justified on the reachable small-witness band** (no producer can
  beat a proven-optimal record), established for *zero billable spend*. Bank Track A (+ C). Finding:
  `docs/covering-exact-producer-finding.md`.
  **GATE-1 broadened — validation-plan Tier 1 (2026-06-30): NO-REACHABLE-BEAT.** The exact ladder
  (greedy → CP-SAT, free-CPU) ran over **71 tractable OPEN cells spanning t=2..8** (vs the prior 6 cells
  at t=2) — every cell with best_known above the strongest cheap lower bound, within `C(v,k)≤2000,
  C(v,t)≤5000, best≤50`. **0 beats** anywhere; 22 records machine-proven optimal, 39 reproduced-not-proven,
  10 above-record (all budget-limited, none a beat). No reachable-and-beatable covering frontier exists on
  the tractable band; the deferred proof-edge stays dormant (no beat to make it non-dormant). The only
  remaining beat-path is the *larger-headroom* OPEN cells beyond the tractable band (exact intractable,
  operator-gated/billable, low-but-nonzero EV). Findings: `docs/results/tier1-results-2026-06-30.md`,
  `docs/validation-plan-2026-06-30.md`.
  **DECISION — D-line BANKED (2026-06-30):** the covering producer-strength swing is **CLOSED** on the
  reachable+tractable band — no producer can beat a record sitting at/above the exact optimum (0 beats / 22
  proven-optimal over 71 cells, $0 spent). The **amplification spine (Track A) is the product**; the
  construction proof-edge stays **deferred** (ADR 0045 §10) until a real record beat materializes (which now
  requires the larger-headroom band or a new domain). Binding constraint reframed: not "producer too weak"
  but **"no reachable-and-beatable frontier in this domain."** Post-bank work pivots to *hardening and
  bounding the amplification spine* (Tier 2: soundness backstop + decide-wall + continuous CI guard), not
  proof-edge enablement.

## Discovery-frontier direction — external round (2026-06-30)
After the 7-family scout returned all-DEAD, the discovery question went to a 5-model external panel
(`docs/external-round-discovery-frontier-synthesis.md`). Convergent outcome:
- **Positive-witness table-beating is confirmed dead**, but the "structural law" was **overstated** — it is
  a **scoped hypothesis** (positive/lower-bound public-table domains). It does NOT cover the escape bands.
- **The escape is a NEGATIVE-witness / CERTIFICATE architecture:** stop *constructing* optimal objects;
  *verify small certificates* from untrusted SOTA solvers for the **upper-bound / non-existence** band humans
  don't dominate. Top new idea: **Delsarte LP dual polynomial** certificates (untrusted SDP finds a dual;
  kernel checks it in exact rational arithmetic) — small certificate, attacks table UBs, ortools-reachable.
- **The decide wall is part artifact** — Qwen's "naive-formalization wall" is *confirmed* by our GATE-2
  maxRecDepth finding; the durable fix is an **external verified LRAT/DRAT certificate checker** (keeps the
  TCB tight *and* scales). A TCB policy call (external-checker vs `native_decide` vs pure-`Array`) is now due.
- **Reconstruction = amplification, not discovery** (unanimous); **Z3/Walnut identities = dead (oracle
  wall)**; **new-domain scouting = don't fund**. **Falsification** is possible but carries a fatal H→S
  *error-of-commission* risk (refuting a strawman = a false claim about the literature) → **deferred behind a
  human-lock on the formalized statement.**
- **Recommended first probe (measure-before-build, $0):** **P1 Delsarte LP dual-certificate reproduction** —
  reproduce a known code/covering upper bound via an untrusted LP dual + exact-rational kernel check; GREEN
  if the kernel verifies a rational dual matching/tightening a table UB. This is the make-or-break for the
  certificate pivot. (Aligns with the already-gated certificate item: Gate B2 / ADR 0045 §10 / kernel-bridge.)
- **P1 RESULT — GREEN, sound end-to-end (#209):** 9/9 exact integer Delsarte certificates verified &
  reproduced known A(n,d); the real kernel verifies a valid cert and rejects a bogus one; clearing
  denominators keeps it integer → no decide-wall. The certificate architecture is mechanically feasible
  under the trust boundary — the first non-dead discovery direction since covering.
- **REACH RESULT — NO-TIGHTENING (#210):** across 39 open A(n,d) (n=12..24), 0 tightenings, 9 reproduce
  best-known, 34/38 beat sphere-packing, certs kernel-verify to n=24. Plain 2-point LP is a sound, scalable
  **verification** tool, not a discovery engine (tables already bake in the classical LP bound).
- **DECISION (2026-07-01) — bank LP + scope SDP (operator chose "both"):**
  - **BANKED:** the LP certificate architecture as an audit-tier **upper-bound verification asset** —
    `scripts/delsarte_bank.py` builds a kernel-checked Delsarte UB-certificate corpus
    (`docs/results/delsarte_ub_corpus.json`, 18/18 kernel-verified); the UB analog of the construction
    amplification annex. Audit-tier (kernel checks certificate validity; the `certOK ⇒ A≤f(0)` Delsarte
    bridge lemma is a deferred formalization slice, like the pending covering bridge).
  - **NEXT (scoped, gated):** the **Schrijver SDP three-point certificate** — the real discovery bet
    (strictly improves LP; source of modern best-known UBs). The hard part is an exactly-kernel-checkable
    PSD certificate (integer LDLᵀ, denominators cleared). Scoping + first probe (reproduce an SDP-improved
    cell e.g. A(12,5) 40→32 via a rational PSD certificate): `docs/sdp-three-point-scoping-2026-07-01.md`.
    Recommend an external mini-round OR a $0 exact-PSD micro-probe before committing the multi-day build.
  - **SDP GATE #212 — mechanism GREEN:** exact-PSD certs (integer LDLᵀ) kernel-verify; float→exact PSD
    rounding recovers 18/18 (`docs/results/psd-certificate-microprobe-2026-07-01.md`).
  - **EXTERNAL CRITIQUE + measurements (2026-07-01, REVISES the risk):** an external agent flagged the
    micro-probe GREEN as a *mechanism* result, not a discovery one. (1) mechanism = Strict-PD + rational
    Cholesky (validated; not LDLᵀ-on-boundary). (2) **compute trap measured real** — naive rational Cholesky
    cert bit-length 944→30,773 bits (n=6→30), `scripts/psd_scaling_probe.py`; mitigable by **Bareiss
    fraction-free** elimination (required build technique, untested). (3) **Irrationality Wall = the primary,
    untested, plausibly-fatal risk** — on open cells the SDP optimal dual may have no rational point, so a
    rational cert + εI margin can overshoot the integer and fail to certify the tightening; the A(12,5) probe
    is a *False GREEN* (small/symmetric). **Revised gate (needs an SDP solver): reproduce A(12,5) with
    Bareiss, then falsify the False-GREEN on a non-tight cell (A(14,5)/A(16,5)) by measuring the irrationality
    margin.** Recommendation: do NOT commit the build on the mechanism GREEN alone; run the margin test or
    bank LP and treat SDP discovery as a low-confidence deferred bet. Synthesis of the critique in
    `docs/sdp-three-point-scoping-2026-07-01.md` (Addendum).
  - **REVISED GATE — irrationality-margin test GREEN (2026-07-01):** ran the agent's primary risk directly on
    genuinely-irrational SDP optima (Lovász ϑ of odd cycles, ϑ(C₅)=√5) — a kernel-checked *rational* PSD
    certificate floored to the correct integer α on 4/4 graphs with an achievable **irrationality tax ≈
    0.002** (≪ 0.01). The irrationality wall is **surmountable**, not fatal (downgrades the agent's 95%). Both
    SDP gates now GREEN (mechanism #212 + irrationality-margin). Residual = ordinary engineering (SDP solver +
    Terwilliger three-point + Bareiss for scale) + the actual open-code-cell margin (measurable only in-build).
    Proxy caveat: odd-cycle ϑ, not the code three-point SDP. **The three-point SDP build is now justified.**
    Findings: `docs/results/irrationality-margin-test-2026-07-01.md` (needs cvxpy, operator-local).
  - **FOUNDATION built (2026-07-01, multi-agent workflow, Sonnet 5 agents + adversarial verify):** the
    achievable+validatable pieces are landed audit-tier — `scripts/bareiss_ldlt.py` (fraction-free
    determinant-bounded PSD certificate: n=30 cert bits 30,773→10,982; form (b) minors-positive is cheaper
    and the kernel recomputes the minors itself) and `scripts/sdp_code_bound.py` (real code-SDP → dual →
    rational-cert → kernel, reproduced A(4,2)/A(4,4)/A(5,2) kernel-verified). Two build-shaping findings:
    (i) the core-Lean checker walls at matrix dim N≈32–64 → the three-point dual must be checked
    block-by-block ((n+1)×(n+1)), so the Terwilliger reduction is essential for the *kernel check*, not just
    the solve; (ii) plain full-graph Lovász ϑ can be *weaker* than Delsarte LP (A(8,5): ϑ=6 vs 4) → the
    three-point bound must include the LP constraints (k=0 block = Delsarte). Findings:
    `docs/results/sdp-foundation-2026-07-01.md`.
  - **EXTERNAL ROUND COMPLETE (2026-07-01) — synthesis + corrected plan:**
    `docs/results/terwilliger-review-synthesis-2026-07-01.md` (6 substantive reviews). **§1 formulation
    confirmed 6/6** (integer β, two block families, k=0=Delsarte); both foundation findings (#215 block-wall
    escape + LP-inclusion) **validated**. **DROP A(12,5)** (6/6: illustrative/hallucinated). Two load-bearing
    corrections: **(D1)** constant-weight A(17,6,7) needs the **Johnson scheme** (a *different* algebra) — first
    target must be **unrestricted (Hamming)**: **A(19,6) 1289→1280** (4/6 canonical Table I), or the cheaper
    **A(12,4) 135→132** (Gemini, unverified) if it text-checks against Table I; **(D2)** the **εI margin is
    invalid for the full dual** (it breaks feasibility — #214's trick only worked for a *free* scalar t) →
    replace with **feasibility-SDP-at-target** (margin restores strict-PD, no kernel change) + **pivoted LDLᵀ**
    (`P·S·Pᵀ=L·D·Lᵀ`, D≥0; gated) as fallback for a singular optimal slack. Also: kernel must **recompute the
    slack S_k(y,β) itself** and check a *system* of per-orbit identities (not "one scalar identity"); derive the
    dual **mechanically**; solve **normalized** blocks and transform back exactly (SCS conditioning is the top
    engineering risk); β anchors conflict → validate the generator's k=0 slice vs #209 Krawtchouk and publish
    our own oracle.
  - **REFRAMING (Fugu, echoed Qwen):** the kernel checks certificate *arithmetic*, not the *formulation* — a
    consistent wrong-sign transcription yields a valid cert for the wrong SDP. So outputs are audit-tier
    **`DUAL_CERTIFICATE_CHECKED`** (de-risked by reproduce-a-known-cell-before-discovery + k=0≡Delsarte
    regression + primal-dual cross-check), **not Q.E.D.**, until a Lean **bridge theorem** formalizes the
    Terwilliger reduction. **Two operator decisions open:** (1) trust tier — audit-now vs bridge-theorem-first;
    (2) first cell — verify-then-A(12,4)-else-A(19,6). Soundness stays kernel-protected throughout.
  - **OPERATOR DECISIONS (2026-07-01):** (1) **audit-tier now** (`DUAL_CERTIFICATE_CHECKED`, bridge theorem a
    later rung); (2) **verify-then-A(12,4)-else-A(19,6)**.
  - **PHASE 0 COMPLETE (2026-07-01) — GREEN, free-CPU:** `docs/results/terwilliger-phase0-2026-07-01.md`.
    (a) **Table I gate from Schrijver's actual paper:** **A(19,6) 1289→1280 CONFIRMED** (smallest-n row);
    **A(12,4) is NOT in Table I** (Gemini hallucinated it — the table starts at n=19), so the verify-leg fails
    and **the first cell resolves to A(19,6)**; A(12,5) absent (dropped); Table I is from (19)+(20), **no
    split-Terwilliger**; constant-weight is a separate Johnson construction (confirms D1). Authoritative
    **eq.(7)** extracted: `β=Σ_u (−1)^{u−t} C(u,t) C(n−2k,u−k) C(n−k−u,i−u) C(n−k−u,j−u)` — it is **C(u,t)**,
    settling the reviewer conflict. (b) **Integer β generator** (`scripts/terwilliger_beta.py`) **validated
    against combinatorial ground truth**: every real code's β-blocks (both families, all k) are exactly PSD
    (16/16 across n=3..6), the transposed-binomial corruption breaks PSD (teeth), reviewer anchors settled
    (GLM right, Kimi/Gemini wrong). Oracle published (`terwilliger_beta_oracle.tsv`, 372 entries); CI-guarded
    (`tests/test_terwilliger_beta.py`).
  - **PHASE 1 COMPLETE (2026-07-01) — GREEN, free-CPU:** `docs/results/terwilliger-phase1-2026-07-01.md`,
    `scripts/terwilliger_dual.py`. Mechanically-derived dual + checker: primal (eq.19/20/22, orbit/(iv)/even-d
    reduction) → Lagrangian dual (PSD `Z_k,Z'_k`; nonneg `α,β1,γ`; free `ν`; bound `A(n,d) ≤ Σγ−ν`). Checker
    `dual_check` **recomputes** the stationarity *system* + bound from `(duals,β)` (D3) and checks PSD + nonneg;
    a dual-feasible point certifies the bound with **no primal witness** (weak duality). Validated three ways,
    each with a corrupt-control: **Lagrangian identity** (collected==direct for all random points), **weak
    duality** (`c·x ≤ L` on real-code x + feasible duals), **Delsarte tie** (k=0 objective vars = inner-dist
    weights); GREEN on A(4,2)/A(5,2)/A(6,2)/A(6,4)/A(7,4). Adversarial panel (4 lenses): primal-fidelity,
    dual-correctness, code/edge-cases all **SOUND**; the one CONCERN was scope-restatement (formulation not
    machine-checked = the audit caveat; β validated in Phase 0). CI-guarded (`tests/test_terwilliger_dual.py`).
  - **PHASE 2a COMPLETE (2026-07-01) — GREEN, operator-local (cvxpy):**
    `docs/results/terwilliger-phase2a-2026-07-01.md`, `scripts/terwilliger_sdp.py`. The cvxpy/Clarabel solve of
    the Schrijver primal **reproduces Table I: A(19,6) 1289→1280 and A(20,8)→274** — the empirical
    formulation-faithfulness check (the panel's #1 concern), verified against *published* values. **Caught +
    fixed a real formulation bug:** impossible triples (`binom(n;i−t,j−t,t)=0`, i.e. `i+j−t>n`; Schrijver
    eq.10) were admitted as phantom variables (key `(8,8,8)` at n=8), making A(8,4) floor to an *invalid*
    13.7<16; the `possible()`/`i+j−t≤n` fix (in `terwilliger_dual.py` + the SDP build) restores A(8,4)=16 and a
    GREEN soundness sweep (no bound floors below a known lower bound). Free-CPU regression guards it. Caveats →
    Phase 2b: float floors are indicative (A(6,2)→31.9999) and the n≈20 k=0 solve is ill-conditioned (Q-pit-2).
  - **PHASE 2b PIPELINE VERIFIED (2026-07-01) — AMBER(nonneg-LP-pending), operator-local (cvxpy):**
    `docs/results/terwilliger-phase2b-2026-07-01.md`, `scripts/terwilliger_cert.py`. The exact-rational
    dual-certificate pipeline is built and **verified 4/4** on small cells: dual extraction + the pinned sign
    convention (**ν = −ν_cvxpy**), exact-PSD rationalized blocks, a min-norm exact-rational correction that
    zeroes **every** stationarity residual, and an exact bound Σγ−ν that **floors to the correct A(n,d)**
    (A(4,2)→8, A(6,4)→4, A(7,4)→8, A(8,4)→16). The **one** remaining step is boundary-multiplier
    nonnegativity: the min-norm correction leaves complementary-slackness-zero multipliers at vanishing
    negatives (~1e-3@P=1e5 → ~1e-9@P=1e10), so an **exact rational LP** (min Σγ−ν s.t. stationarity + α,β1,γ≥0)
    is needed — the panel's predicted hard step (Kimi Q-dual-3; SDPA-GMP territory). Guarded by
    `tests/test_terwilliger_cert.py`.
  - **PHASE 2b GREEN for small cells (2026-07-01):** the nonneg step is solved by **high-precision iterative
    clamping** (at P≥1e6 the complementary-slackness negatives are ~1e-7; clamp-to-0 + re-solve converges,
    `dual_check` validates exactly). Full exact certificates A(4,2)→8, A(6,4)→4, A(7,4)→8, A(8,4)→16
    (`certified 4/4`). **A(19,6) hits the #213 compute-trap** (measured: >10 min, no result) — the 20×20 blocks
    × hundreds of clamp iterations blow up `Fraction` bit-length, exactly the panel's Q-pit-2 warning.
  - **PATH B DONE (Phase 3 kernel, 2026-07-01):** `kernel_verify()` renders a small-cell exact cert's PSD
    blocks to Lean (reusing #212/#215 `ldltOK`) and the **real Lean 4.31 kernel accepts the valid cert and
    REJECTS a corrupted block** (`sound: True`) for A(4,2)/A(6,4) — the full **SDP→dual→exact-cert→kernel**
    chain is GREEN on small cells. Docker-gated test added. (Kernel-attests the PSD content; the full
    stationarity-in-Lean per D3 is a follow-on, Path B2.)
  - **PATH C DIAGNOSED (2026-07-01) — A(19,6) is compute-bound, not impossible:**
    `docs/results/terwilliger-phasec-2026-07-01.md`, `scripts/terwilliger_scale_probe.py`. Three walls isolated:
    (1) conditioning **surmountable** — the dual rounds to exactly-PSD at **P=1e8**; (2) restoration **cheap** —
    residuals→0 in ~1s and **⌊Σγ−ν⌋ = 1280** (the cert exists and floors to Schrijver's bound); (3) the wall is
    **exact non-negativity** — 655 negative multipliers after restoration, so the one-at-a-time clamp (fine ≤
    n≈8) is O(hundreds×s) = hours. Completing A(19,6) needs **(a)** a bit-controlled rational LP
    (min Σγ−ν s.t. stationarity + α,β1,γ≥0; Bareiss/integer-preserving pivoting to bound #213 bit-growth),
    self-contained, **or (b)** SDPA-GMP high-precision (operator-local install; panel D6). Guarded by
    `tests/test_terwilliger_scale_probe.py`.
  - **PATH C COMPLETE (2026-07-01) — A(19,6) ≤ 1280 exact certificate, self-contained:**
    `docs/results/terwilliger-phasec-exact-lp-2026-07-01.md`, `scripts/terwilliger_exact_lp.py`. Option (a) —
    an **exact two-phase rational simplex** (`min Σγ−ν s.t. stationarity + α,β1,γ≥0`) — replaces the O(hundreds)
    clamp with ONE solve and, at **P=1e10/1e12**, returns a dual that `dual_check` validates exactly
    (feasible + PSD + nonneg + residual-0) with **⌊Σγ−ν⌋ = 1280** in ~17s, **no `Fraction` bit-blowup** (the
    #213 trap did not materialize). So the Schrijver record bound **A(19,6): 1289→1280 is reproduced as a
    genuine exact-rational audit-tier certificate through our own SDP three-point pipeline — SDPA-GMP NOT
    needed** (float64 Clarabel + high-precision rational rounding + the exact LP suffice). Guarded by
    `tests/test_terwilliger_exact_lp.py` (incl. the A(19,6) test).
  - **PATH B2 DONE (2026-07-01) — the A(19,6) certificate is KERNEL-ATTESTED:**
    `docs/results/terwilliger-pathb2-2026-07-01.md`. The n=19 "scaling wall" was a **render artifact**: one
    `decide` over the 20-block `&&` conjunction blew the elaborator budget, and `check_source` misread the
    resource error as a rejection (the GATE-2 trap again) — the largest 20×20 block alone verifies in ~5 s.
    Fix: `render_cert_lean` emits **one theorem per block** (+ `maxHeartbeats 0`); soundness identical (any
    failed block fails the file). Measured: exact-LP A(19,6) cert ~17 s → **kernel True on all 20 blocks in
    16 s; corrupted-block control False in 13 s** (`kernel_verify_lp`; docker-gated test added). No Bareiss /
    native_decide needed.
  - **"All three" — RESOLVED, all legs:** (A) exact cert — done incl. A(19,6); (B) kernel verify — **done
    incl. A(19,6)**; (C) scale — done. **The full SDP→dual→exact-cert→kernel chain is GREEN on the record
    cell.** Tier stays audit (`DUAL_CERTIFICATE_CHECKED`).
  - **FORMALIZATION SCOPE (2026-07-01) — the audit→Q.E.D. ladder, scoped for fresh sessions:**
    `docs/terwilliger-formalization-scope-2026-07-01.md`. Measured sizing on the actual A(19,6) cert: the
    LP-optimal dual is **sparse** (55/4621 multipliers nonzero — a basic vertex), 55 stationarity identities,
    47-bit multipliers, 34-bit common denominator, 8076 nonzero β entries. Rungs: **F1** whole-cert-in-kernel
    (β table verified against eq.7 in Lean + 55 integer identities + nonneg + bound; M, one session, no trust
    touch); **F2a** weak duality over the abstract primal in Lean/Mathlib (M); **F2b** codes⇒feasible incl.
    the block-diagonalization Theorem 1 (XL; **external formalization round candidate**, brief drafted);
    **F2c** trust wiring for Q.E.D. (GATED: guarded-core edits, hook + operator + witness round; alternative =
    Observatory tier per ADR 0038). **Discovery outlook (honest):** Table I reproduction validates machinery,
    not new math — Schrijver computed n≤28; discovery needs the beyond-Table-I reach probe (cheap, first),
    eq.(25) sharpenings, the Johnson-scheme build (D1), or post-2005 hierarchies. Recommended order:
    ① reach probe ② F1 ③ F2a ④ operator decision on F2b/F2c.
  - **SESSION HANDOFF (2026-07-01):** `docs/handoff-terwilliger-sessions-2026-07-01.md` — the first file a
    fresh session should read: state snapshot at `c666c8f`, code map, measured numbers not to re-derive, the
    five standing traps (check_source-False-on-resource-error; `td.possible()`; macOS timeout; dep gating;
    process constants), and per-ticket kickoff prompts + gates for ① (#99, full probe spec incl. the Brouwer
    snapshot protocol and the GREEN(candidate)/DRY gate) ② (#100) ③ (#101).
  - **TICKET ① DONE (2026-07-01) — reach probe verdict: DRY, and the wall is the SOLVE LEG:**
    `docs/results/terwilliger-reach-probe-2026-07-01.md` (task #99). 44 cells (n=20..30, d∈{6,8,10,12})
    against a twice-cross-checked Brouwer snapshot (`docs/data/brouwer-snapshot-2026-07.json`; context only,
    never a decider): **0 certified tightenings**; 9 valid floats (d∈{6,8} plus the d=10 survivor
    A(21,10)→50, n≤27; all at/above published ubs except the two refuted candidates below; A(20,8)=274
    reproduces Table I through the harness); **35/44 solve-leg failures** — CLARABEL crash onset ≈4600 free
    vars, SCS under-converges up to ~88× below known lbs; both float "candidates" ((23,6)→13626,
    (27,8)→12445) were solver artifacts and neither certified: **(27,8) actively refused by the
    exact-rational decider** (feasible dual, bound 5.9e7 ≫ target), **(23,6) rejected fail-closed** (its
    CLARABEL dual crashed → no cert; no exact arithmetic ran) — trust chain held; 0 invalid floors enshrined
    thanks to the floor≥lb acceptance gate + monotonicity lb at n=29,30. Sharper findings: the pre-SDP-ub
    frontier cells (27,12)≤169 / (28,12)≤288 are unreachable
    until the **solve leg is fixed (normalized β blocks / SDPA-GMP — D6/Q-pit-2)**, and **d≥10 formulation
    faithfulness is UNVALIDATED** ((22,10)=87 unreproducible; k_max-bisect scatter says conditioning-first,
    but a d≥10 transcription hole is not excluded from float evidence — no d≥10 output is trustworthy until
    that reproduces). Decision input: **F2b is infrastructure, not discovery-motivated, today**; D6 is the
    prerequisite for ANY beyond-Table-I attempt. Harness: `scripts/terwilliger_reach_probe.py`; test:
    `tests/test_terwilliger_reach_probe.py`.
  - **D6/Q-pit-2 DONE (2026-07-02) — solve leg FIXED; d≥10 faithfulness VALIDATED (one measured anomaly);
    frontier cells closed:** `docs/results/terwilliger-solve-leg-2026-07-02.md`,
    `scripts/terwilliger_solve_leg.py`. Fix = **Schrijver's eq.(8) block normalization restored float-side
    only** (exact PSD-equivalence; a per-block max-coeff scalar was tried and REJECTED — measured regression)
    **+ SDPA-GMP** (`sdpa-multiprecision`, gated) at measured-tight `SDPA_TIGHT`; CLARABEL fallback stays raw
    (byte-compatible; its equilibration fights the congruence). Gate passed: **A(19,6)→1280.036 and
    A(20,8)→274.086 now at true `optimal`**, and the probe's crash cell **(23,6)→13766.139 `optimal`**
    (Table I 13766) in ~10 s. **Two new exact certs banked: A(23,6) ≤ 13766 and the first d≥10 cert
    A(25,10) ≤ 503** (certify_lp @ P=1e14). d≥10: (25,10) exact at both tiers → the suspected γ-substitution
    hole is a **non-bug** (proved valid + present in the paper's program); (26,10) still stalls
    (precision-independent, recorded); **(22,10) anomaly**: our transcription **certifies ≤ 88 exactly and
    87 does not certify** — floats stall on BOTH sides (87.97 under-solve attractor across two solvers —
    floors to Table I's "87"! — and a −7e-19-audit pseudo-optimum at 88.63 refuted by the exact cert's
    1.5e9-scale multipliers: **no float audit is a bound at this conditioning**); eq.(25) caps provably
    can't bridge 88→87. Open question + resolution paths recorded; not claimed as a Table I error. Frontier:
    **(27,12)/(28,12) are now measured Delsarte-ties** — three-point adds nothing there, so discovery at the
    probe's headroom cells is **bound-blocked, not solver-blocked** (needs D1 / hierarchies, not more
    precision). Guarded by `tests/test_terwilliger_sdp.py` (normalization-equivalence, defaults pairing,
    crash cell, d≥10 cell); invariants byte-identical.

## The ADRs

**Status: all five implemented and merged (2026-06-21).** ADRs 0009–0013 are
Accepted; two follow-ups remain (see below). The trust boundary held throughout —
`tests/test_invariants.py` byte-identical across every change.

| ADR | Decision | Theme | Guarded? | Status |
|---|---|---|---|---|
| **0009** | Close the KFM → SURVEY loop (re-seed from recombined parents; curiosity + difficulty targeting) | Discovery yield | no | ✅ done |
| **0010** | Expand the faithfulness probe table (OPTIMALITY + INVARIANT adjudicated mechanically) | Faithfulness | no¹ | ✅ done |
| **0011** | Proving throughput & cost (concurrent ensemble; cross-cycle cache; USD cap; **Lean REPL import-caching**) | Performance / cost | no | ✅ done² |
| **0012** | Autoformalization robustness (mechanical import-resolver before LLM repair; output normalization) | Robustness | no | ✅ done |
| **0013** | Trust-edge provenance (EdgeEvidence.producer + construction-site AST-guard + §2 gate stamping) | Trust defense-in-depth | **yes** (types/trust/verifiers) | ✅ done³ |

¹ Turned out **probe-table-only** (`probes.py`) — the gate dispatch is generic, so no guarded edit.
² **Fully landed** — incl. the Lean REPL backend (`backends/lean_repl.py`,
  `docker/lean-repl.Dockerfile`): Mathlib loads once per import-set, measured 3x on a
  4-check Mathlib batch. Thread-safe persistent container also composes with the ensemble.
³ Adversarial-review-hardened: the load-bearing AST-guard landed, **and §2 general
  judge-producer stamping** on faithfulness/novelty edges shipped (PR #25).

## Tier 3 — substrate maturity (complete)

Making sustained autonomous discovery affordable, honest, and broad before the
discovery-frontier push.

| ADR | Decision | Theme | Guarded? | Status |
|---|---|---|---|---|
| **0014** | Real (token-based) cost accounting (meter provider usage; price table; exact USD cap) | Cost governance | no | ✅ done |
| **0015** | Corpus (D4: 3→34 known results) + domain (D9: 1→3, round-robin) expansion | Discovery inputs | no | ✅ done |
| **0016** | Chimera runtime — `PersistentRuntime` (SQLite memory + circadian phase) vs the `SimpleRuntime` stub | Substrate | no | ✅ done⁴ |

⁴ Self-contained per operator decision: no external Chimera checkout in-env, so the
  real runtime is built behind the `RuntimeAdapter` Protocol; external-Chimera
  wiring stays a documented drop-in. **Tier 3 complete.**

## Tier 4 — the public reading-room (complete)

| ADR | Decision | Theme | Guarded? | Status |
|---|---|---|---|---|
| **0017** | Codex Calculemus — standalone private Astro repo (codexcalculemus.com) rendering the published ledger, mirroring codex-vitruvianus | Presentation (R6) | no | ✅ done⁵ |

⁵ Separate private repo
  [`codex-calculemus`](https://github.com/elementalcollision/codex-calculemus) (the
  renderer); Leibniz keeps the producer bridge `leibniz/calculemus_site.py` +
  `scripts/export_calculemus.py`. Specimens are genuinely kernel-checked (REPL);
  `export_calculemus.py --check` re-verifies every Q.E.D. against the kernel.
  Read-only over the ledger; invariants byte-identical. **Tier 4 complete** — only
  Tier 1 (discovery) remains.

## Tier 1 — the discovery frontier (the mission)

| ADR | Decision | Theme | Guarded? | Status |
|---|---|---|---|---|
| **0018** | Discovery frontier — outcome-conditioned conjecture + difficulty thermostat + weakening seeds + graded quality | Discovery yield | no | ✅ done⁶ |

⁶ Closes the learning loop on the **proposal** side (ADR 0009 closed it on selection):
  `leibniz/discovery.py` — `DiscoveryNotebook` (M1), `FrontierController` (M2),
  `weakening_seeds` (M3, depth-1 bounded), graded tent `quality`/`difficulty` (M4),
  `scripts/measure_discovery.py` (M5, shows the thermostat lifts yield 0%→~50% on a
  hidden tractable window and recovers from overshooting a narrow one). Adversarially
  reviewed (4 lenses): trust-safety clean, robustness defects fixed. All proposal-side;
  the kernel + Z3 still decide;
  invariants byte-identical. **Tier 1 landed** — remaining work is live calibration
  and deeper decomposition (ADR 0018 open questions).

## Tier 1 — live calibration (first pass)

| ADR | Decision | Theme | Guarded? | Status |
|---|---|---|---|---|
| **0019** | HuggingFace prover backend + certifi SSL + first live calibration | Discovery (live) | no | ✅ done⁷ |

⁷ The pipeline runs **end-to-end on the real stack** (Anthropic conjecture/formalize,
  HF prover ensemble — DeepSeek-Prover-V2 et al., Lean REPL under N+1 consensus, Z3),
  feed-seeded from the curated arXiv feed. First run (2 cycles, $0.72): 10/10 reached
  proof, **0 promulgated, disposition pure `unproven`** — proving is the sole
  bottleneck (research-seeded conjectures above the ensemble's reach). The frontier
  mechanisms fired (weakening + recombination grew the seeds) but the thin-evidence
  guard held the band over 2 cycles — the controller needs ≥5. Proposal-side only;
  invariants byte-identical.

| **0020** | Faithfulness gate refuses vacuous passes (encodability gate) | Faithfulness (trust) | no | ✅ done⁸ |

⁸ The ADR 0019 calibration's "10/10 passed faithfulness" was **vacuous** — the
  single-variable arithmetic DSL can't encode richer contracts (^, multi-variable,
  functions), so the gaming-witness silently returned "no witness" and the probe read
  PASS. Now the probe DEFERs unless the whole contract is encodable (non-guarded fix in
  `probes.py`/`smt_z3.py`; `gates/` untouched; invariants byte-identical). The gate is
  honest — and this **exposes the faithfulness DSL as the headline discovery blocker**.

| **0021** | Widen the faithfulness DSL soundly (multi-variable, constant powers, constant mod/div) | Faithfulness (trust) | no | ✅ done⁹ |

⁹ The gate can now *honestly certify* the bulk of real conjectures (not just single-`n`
  arithmetic), unblocking the path to proof. An adversarial **soundness review** (3
  lenses, 8 findings) caught + fixed a CRITICAL wrong-UNSAT (`^` parsed as BitXor →
  vacuous PASS), z3-`unknown`-as-UNSAT, and non-boolean/recursion crashes: searches are
  now timed-out + tri-state, and the probe certifies only on **conclusive UNSAT** of
  both coverage and no-gaming. `gates/` untouched; invariants byte-identical.

| **0022** | Conjecturer contract encodability — steer claims into the faithfulness DSL | Discovery (proposal) | no | ✅ done¹⁰ |

¹⁰ The deeper calibration showed the binding blocker had moved *upstream* to faithfulness
  DEFER (research-seeded contracts exceed even the widened DSL). ADR 0022 steers the
  **proposal** side: the CONJECTURE/FORMALIZE prompts now carry the DSL grammar, and a
  bounded, mechanical **contract-repair** pass in `Formalize` rewrites an un-encodable
  contract toward the DSL — committing a repair ONLY if every field is encodable, the
  `claim_domain` stays satisfiable, AND `claim_property` is not weakened (it must imply
  the original); it **fails closed** without a decider. The adversarial review (3 lenses,
  4 fixed findings) also closed a *pre-existing* gate hole: `coverage_probe` now tests the
  property **inside** `established_domain` (it was vacuously satisfied once coverage held),
  and `smt_z3` no longer crashes a cycle on a non-boolean predicate. Entirely
  proposal-side / strictly-tightening on the gate: the honest gate still decides,
  `theorem_src` unchanged, `trust.py`/invariants byte-identical.

  **Measured (clean A/B vs the deeper run, band reset to 0.45, ADR 0022 the only
  changed variable; 6 cycles, 39 conjectures, $3.19):** `reached_proof` **0 → 31**
  (0% → 79%); the faithfulness DEFER fraction collapsed from ~95% to ~20%; 0 unfaithful,
  0 gamed (the hardened gate did not false-reject). ADR 0022 did exactly what it was
  designed to do — it pulled conjectures out of faithfulness DEFER and into proof. The
  binding blocker has now moved **downstream to the prover**: conjectures reach the
  kernel but the HF ensemble cannot close them under N+1 consensus (0 promulgated).

## Remaining follow-ups

- **Faithfulness DSL — next increment** — ADR 0021 widened it to multi-variable +
  constant powers + constant mod/div; still DEFERred: symbolic exponents (`2^n`),
  named functions (`Nat.log`, `factorial`, `gcd`). A bounded definitional encoding
  would bring them in.
- ✅ **Persist the frontier band** across runs (ADR 0019 follow-up) — `FrontierController.save/load`,
  wired through `build_daemon` + `run_cycles` (`.leibniz/frontier.json`), so calibration
  accumulates instead of resetting to the default band. Done.
- ✅ **Deeper live calibration** (6 cycles, $1.97, 4096-tok proof budget) — done. Decisive
  shift from the first run: **reached_proof 10 → 0**. The honest+widened faithfulness gate
  no longer vacuously passes (it DEFERred 40/42, caught 1 unfaithful, killed 1 trivial),
  so the binding blocker moved *upstream* to **faithfulness DEFER**: research-seeded
  contracts exceed even the widened DSL. The band/controller/persistence all worked live
  — it adapted 0.45→0.34→0.24→0.15(floor)→re-explored to 0.73, persisted at 0.625. So the
  next lever is **conjecturer contract steering** (emit fully-encodable contracts so
  candidates reach proof), not prover/band tuning.
- ✅ **Conjecturer contract encodability** — ADR 0022: prompts carry the DSL grammar +
  a bounded, sound contract-repair pass in `Formalize`. Done + **measured**: `reached_proof`
  0 → 31/39 (the DEFER fraction collapsed ~95% → ~20%). Proposal-side; invariants
  byte-identical.
- **Prover reach (new headline blocker)** — with faithfulness no longer the bottleneck,
  conjectures reach the kernel but the HF ensemble can't close them (0/31 proved). This
  is the normal discovery regime — the path to a first promulgation now runs through
  proving power, not the gate. Levers, in order:
  - ✅ **Lever 1 — weaken-and-retry (ADR 0023)**: persist the `DiscoveryNotebook` so
    near-misses accumulate across runs, raise weaken throughput (`weaken_k` 2→3,
    `capacity` 6→12), and weaken the *freshest* near-misses. Proposal-side; invariants
    byte-identical. Pending a billable weaken-heavy run to attempt a first promulgation.
  - ✅ **Lever 2 — lemma decomposition (ADR 0024)**: a `DecompositionProver` adds a
    structured-proof strategy to the ensemble — prove via `have`/`suffices` lemmas, then
    compose — closing goals one-shot drafts miss. Kernel-checks the whole proof
    (`discharge` untouched); composes with N+1 consensus; `LEIBNIZ_DECOMPOSE` (default 1).
    Proposal-side; invariants byte-identical. Deferred to a future guarded-core ADR:
    *independent* sub-lemma proving + a verified preamble for reuse as stepping stones.
  - 🔶 **Lever 3 — stronger prover (ADR 0028/0029, in progress)**: researched the
    current Lean-4 landscape and wired the access paths (all proposal-side; our kernel
    re-verifies under N+1). **(A)** OpenAI-compatible client now takes
    `LEIBNIZ_PROVER_BASE_URL`/`LEIBNIZ_PROVER_KEY_ENV` so Goedel-Prover-V2 (beats
    DeepSeek-Prover-V2-671B) drops in by config — `scripts/measure_goedel.py`. **(B)**
    `AristotleProver` (Harmonic Aristotle agent) + `scripts/try_aristotle.py` (submits a
    goal, **our kernel re-verifies** the returned proof) — env-gated `LEIBNIZ_ARISTOTLE`.
    **(C)** agentic proof-repair loop (frontier reasoner + kernel-error feedback;
    HILBERT/LEAP pattern) **built in ADR 0029** (`leibniz/proof_repair.py`) — the
    highest-leverage path — opt-in via `LEIBNIZ_PROOF_REPAIR`, layered as the outermost
    DEMONSTRATE fallback (consensus → decomposition → repair). N+1 is preserved: a repaired
    proof counts as one more *distinct* prover identity **only if its model differs from every
    base verifier** (canonical model-name dedup, ADR 0024) — so it can supply a deciding vote
    but never lowers the bar; `discharge` stays the sole stamper. Now **measured live** (C,
    below), including a frontier-reasoner **failover** chain (opus → glm-5.2 → kimi-k2.6 →
    gpt-5.5) added after an Anthropic outage stalled the first run.

    **Measured (live):**
    - **(B) Aristotle — works, on our OWN near-misses.** `try_aristotle.py` on
      `6 ∣ n(n+1)(n+2)`: Aristotle returned a complete proof and **our 4.31 kernel
      re-verified it** (Q.E.D.). Then a harvest of **3 real daemon near-misses** (Lean
      goals the ensemble formalized but never closed) — `(n³+5n)%6=0`,
      `4 ∣ (2n)(2n+1)(2n+2)(2n+3)`, `n(n+1)(2n+1)%6=0` — came back **3/3 closed AND
      re-verified by our kernel** (≈6–7 min each; tactics like `norm_num … interval_cases
      n%6` and `grind`). A hosted *agentic* prover closes the exact non-trivial goals our
      ensemble misses — the trust boundary holds end-to-end (proposer's output is worthless
      until our kernel re-checks it).
    - **(A) Goedel-V2-32B — marginal.** 3 cycles, 12 conjectured, 11 reached proof,
      **1 promulgated** (`(n²+n+2) % 2 = 0`, proof persisted). But that run used
      consensus=1 (single model), so the lone promulgation is partly a lower-bar artifact;
      the apples-to-apples metric — the decomposition funnel — is essentially unchanged vs
      the HF ensemble (sub-lemmas **2/17** proven ≈ 12% vs 3/22 ≈ 14%; composed **0/2**).
      So a stronger *open model* is an **incremental** lift, not the unlock.
    - **(C) In-house repair loop — strong on REACH, gated on PROMULGATION.** Measured two
      ways. *Targeted* (`scripts/measure_repair.py`, the in-house Claude+kernel loop run
      directly on the daemon's real Lean near-misses — head-to-head with Aristotle's 3/3):
      the scaffold closes **~half** — opus **6/11**, and during an Anthropic outage the
      failover backups **5/11** (glm-5.2 / gpt-5.5 / kimi-k2.6 + opus), **union 7/11**;
      **every closed proof re-verified by our kernel AND non-trivial**; round distributions
      (`[1,1,0,1,0,1]`, `[2,0,0,2,1]`) show **~half the wins come *from* repair rounds**, not
      the draft. *Integrated* (calibration, `LEIBNIZ_PROOF_REPAIR=1`): repair closes **~47%**
      of goals the ensemble+decomposition missed (14/30, 19/39). **But sound N+1=2
      promulgations ≈ 0**: promulgation needs *two distinct models to close the same goal* —
      when opus is also a base prover the repair correctly adds nothing (the dedup that fixed
      a real double-count bug; a pre-fix run's "9 promulgations" were the opus+opus artifact),
      and when the base is distinct (deepseek+glm) the specialized provers rarely close the
      *same* hard goals repair closes, so repair is the lone closer (1<2). The live run also
      exposed three integration bugs unit tests missed (proof roles returned JSON not bare
      scripts; no failover; the N+1 double-count) — all fixed (#60/#62/#63).
    - **Conclusion (confirms HILBERT/LEAP):** the lever is the **scaffold, not the raw
      model** — Aristotle and the in-house repair loop both close goals the ensemble misses
      (~50% reach), while a stronger raw open model (Goedel) was marginal. **But reach ≠
      promulgation:** under N+1=2 a promulgation needs two *independent* models on the *same*
      goal, which a single reasoner can't supply.
    - ✅ **(C-v2) Repair PANEL — built + demonstrated.** The repair stage now runs a panel of
      distinct reasoners (`LEIBNIZ_REPAIR_PANEL`) and counts *distinct* closers, so two
      independent models closing the same goal satisfy N+1 by themselves (#65,
      `scripts/measure_panel.py`). **Demonstrated 2/2:** panel `[opus, gpt-5.5]` with an empty
      base promulgated two known-non-trivial goals at consensus=2 — each independently
      kernel-verified (Q.E.D.), `repair_models=[claude-opus-4-8, gpt-5.5]`, $0.15. This
      converts the measured ~50% reach into **sound** promulgations. Next: run the panel
      through the live discovery funnel for a first *organic* promulgation; Aristotle remains
      a candidate second independent proposer. Raw-model swaps (A) stay deprioritized.
    - ✅ **(C-v2) Organic funnel run — the panel works end-to-end.** Full live calibration,
      panel `[opus, gpt-5.5, glm-5.2]`, isolated state (8 cycles, 61 conjectured, $23.44,
      ~3.6 h): **42 reached proof (69%), 12 promulgated, all kernel-verified.** The repair
      panel is the whole engine — decomposition closed **0/85** sub-lemmas (still
      reach-bottlenecked), repair **closed 17, promulgated 12** (N+1 filtered the 5 closes that
      lacked a 2nd distinct closer); `rounds_to_close` = **8 initial-draft, 9 via repair
      rounds**. The faithfulness gate caught **16 gamed**; the band thermostat walked
      0.45→0.18→0.26. **Audit of all 12: SOUND 12/12 (re-discharged Q.E.D.), NON-TRIVIAL
      12/12, but NOVEL 0/12** — every one is Fermat's little theorem (p=3,5,7) or an elementary
      divisibility. So the mission MECHANISM is proven (sound N+1 promulgation, no human on the
      path) but the **novelty filter is the binding gap** (the daemon rediscovers textbooks).
    - 🔶 **Novelty hardening (ADR 0031), partial.** L1 (corpus broadened 34→48 with the
      elementary-NT families; seeded hashes match the run's canonical promulgations) + L3
      (conjecturer steered off the classic families) shipped and are **sound**. **L2
      (decision-procedure equivalence) was implemented then RETRACTED same-day as unsound** —
      every theorem's property is a tautology over its domain, so box-equivalence matched *any*
      true claim to a tautological known (would suppress all novelty).
    - ✅ **Restatement matching — STRUCTURAL, sound (ADR 0032).** Replaces the retracted L2 with
      a *form*-based matcher: canonicalize a univariate polynomial congruence to a signature
      `(relop, m, coeffs mod m)` and match signature-to-signature. Two claims match IFF they
      assert the *same* congruence — by form, never truth — so it **cannot false-KNOWN**, the
      flaw that killed L2. The organic run's restatements (`(n^5+4n)%5==0` → Fermat-5, etc.) now
      classify KNOWN, while genuinely-novel congruences (Euler's `n^2+n+41`), identities
      (`n+0==n`), and multivariate claims stay NOVEL. Pure stdlib (no Z3/Lean/rebuild).
      Process this time matched the stakes: design → adversarial design review → implement →
      adversarial impl review, all three SOUND. **Novelty restatement gap: closed.**
- **First promulgations + the trivia correction (ADR 0025)** — the lever-1 weaken-heavy
  run (8 cycles, 64 conjectured, $6.06) **promulgated 32 laws** — the first end-to-end
  kernel-verified promulgations. An audit confirmed the verification is **sound** (true
  identities verify via `ring` under `Mathlib.Tactic`; false statements and `sorry` are
  rejected; `discharge` still the sole writer) but found the 32 are **ring-trivial**
  polynomial identities that slipped the non-triviality gate (its tactic set lacked
  `ring`/`nlinarith`), and that proofs weren't persisted (ledger showed `(none)`). ADR
  0025 fixes both: `ring`/`nlinarith` join the triviality decision procedures (the 32's
  pattern now reads TRIVIAL), and `proof_src` is persisted (with a DB migration).
  Strictly more conservative; invariants byte-identical. Expect far fewer, higher-quality
  promulgations next — the honest state.
- ✅ **Non-trivial conjecture steering (ADR 0026)** — resolves the 0022↔0025 tension:
  the CONJECTURE prompt no longer steers toward elementary (ring-trivial) arithmetic. It
  now names the full trivial-tactic set (incl. `ring`/`nlinarith`), forbids polynomial
  identities/inequalities, and steers toward induction/case-analysis/lemma-requiring
  claims (divisibility/modular facts about non-linear expressions) — while keeping the
  in-DSL contract so faithfulness still certifies. Prompt-only; invariants byte-identical.
  **Validated** (4 cycles, 25 conjectured, fresh notebook/band, $2.16): the disposition
  shifted decisively — **0 TRIVIAL** (the conjecturer left the ring-trivial space),
  24/25 reached proof, **1 promulgated**, 1 gamed (the faithfulness gate caught it). The
  one promulgation — `4 ∣ (2n)³·(2n+1)²`, proved `by use 2*n^3*(2*n+1)^2; ring` — is a
  genuine divisibility fact (not one-shot-closable; needs a cofactor witness) and its
  proof is now **persisted** (ADR 0025), shown in the ledger rather than `(none)`. So the
  steering + integrity fixes work end-to-end; the binding blocker is now squarely **prover
  reach**: 23/24 non-trivial conjectures reached the kernel but the ensemble + decomposition
  could not close them → lever 3 (stronger/longer prover) + deeper decomposition.
- ✅ **Decomposition — independent sub-lemmas (ADR 0027)** — the deeper M3: a
  `LemmaDecomposer` asks for helper lemmas, proves each INDEPENDENTLY via N+1 consensus,
  then re-proves the main with the proven lemmas offered as `have`-block **hints**. The
  kernel only ever checks ONE self-contained declaration (`theorem_src := proof`); the
  hints are prover context and NEVER enter the Lean source — so there is no
  separate-declaration surface to poison (`discharge` unchanged, sole writer; N+1
  preserved). `DecomposingDemonstrate` runs it as a fallback after normal consensus
  (`LEIBNIZ_LEMMA_DECOMPOSE`, default 1), recording exactly one proof edge.
  **An adversarial review CRITICALLY rejected the first ("preamble") cut** — prepending
  the lemmas as separate declarations let a preamble poison elaboration via
  `attribute`/`notation`/`run_cmd` with no denylisted keyword; the hints redesign
  eliminates the vulnerability class rather than guarding it. Invariants byte-identical.
  **Measured (focused run, 2 cycles × 2 seeds, $1.01): 6 conjectured, 6 reached proof, 0
  promulgated** — decomposition did NOT close any on this small sample (all 6 stayed
  unproven; blocker still prover reach). **Inconclusive, with a measurement gap**: the
  harness does not instrument decomposition, so it cannot distinguish "decomposition fired
  but the sub-lemmas/composition also failed" from "decomposition silently no-op'd"
  (bad-JSON / unprovable sub-lemmas). Small N (6) on a low base rate (prior: 1/25).
  ✅ **Decomposition is now INSTRUMENTED** (`DecompositionStats`), and the larger
  measurable run (3 cycles × 2 seeds, 12 conjectured, $2.12) gave a **decisive diagnosis**
  via the funnel `attempted 11 · planned 11 · sub-lemmas 3/22 proven · composed 0/3 closed`:
  - decomposition **fires and works mechanically** — 11/11 produced a valid, parsed plan
    (no silent no-op; the prompt/JSON path is sound);
  - the wall is **sub-lemma provability**: only **3 of 22** proposed sub-lemmas proved
    independently (~14%) — the pieces are about as hard as the whole, so decomposition
    isn't finding *easier* sub-goals;
  - and the 3 composed attempts (≥1 lemma proven) **closed 0** — partial decomposition
    doesn't suffice.

  Conclusion: decomposition is a sound multiplier but is **bottlenecked on PROVER REACH** —
  the HF ensemble reliably closes only decision-procedure-trivial goals (it closed 32
  ring-trivia in the lever-1 run), which the non-triviality gate (correctly) filters; for
  genuinely non-trivial goals it closes ~0–1 per run, and even their sub-lemmas at ~14%.
  The binding constraint *was* **lever 3 (a stronger prover)** — now **resolved**: the ADR 0029
  repair panel closes ~50% of missed goals and, in the organic funnel run, produced **12 sound
  N+1 promulgations with no human on the path** (decomposition still contributes ~0; the panel
  is the engine). The binding constraint then **moved to NOVELTY** (the daemon proved things but
  rediscovered textbooks — all 12 were Fermat-family / elementary divisibility). That is now
  **addressed**: ADR 0031 (corpus broadening + steering; the L2 equivalence heuristic was
  retracted as unsound) + **ADR 0032's sound STRUCTURAL matcher** catch the canonical knowns and
  their restatements by form. Remaining open work is **breadth, not soundness**: grow the known
  corpus, and extend the structural matcher beyond univariate polynomial congruences as the
  conjecture mix demands. A fresh organic run is the next measurement (does the KNOWN fraction
  rise and do genuinely novel survivors appear).

## Sequencing (as built)

The mission is *novel, tractable, kernel-proven* theorems — so **discovery yield was
the top priority**; implemented in this order:

1. **0009 — discovery loop** (highest leverage; turns "runs end-to-end" into
   "learns and promulgates"). No guarded edits.
2. **0012 — autoformalization robustness** (gets candidates past MALFORMED reliably
   and cheaply; enables 0009 to bear fruit). No guarded edits.
3. **0010 — probe expansion** (more claims pass faithfulness *mechanically* rather
   than DEFER). Guarded — operator sign-off; depends on 0004's structured contract.
4. **0011 — throughput & cost** (matters once 0009 produces candidates at volume;
   also the USD cap should land before sustained autonomous runs).
5. **0013 — trust hardening** (orthogonal defense-in-depth; do anytime). Guarded.

Dependencies: 0010 builds on ADR 0004 (structured faithfulness contract). 0011's
budget and 0012's robustness are prerequisites for a *sustained* autonomous run.
0009 + 0012 together are the minimum to demonstrate the R4 exit test
(promulgate ≥1 novel non-trivial theorem with no human on the critical path).

## Success metrics

- **0009/0012:** over N cycles, ≥1 novel, non-trivial theorem promulgated; archive
  coverage grows; promulgation rate trends up across cycles.
- **0010:** fraction of measurable claims adjudicated MECHANICAL (vs DEFER) rises;
  no measurable claim ever promulgated via a judge.
- **0011:** per-candidate wall-clock and $/promulgation fall; a per-cycle USD cap
  is enforced.
- **0013:** a mutation test (flip any edge tier) makes `validate_path` raise; proof
  edges carry discharge provenance.

## Invariant (applies to every ADR)

None of these may weaken the trust boundary. `tests/test_invariants.py` must stay
byte-identical and green; guarded-core changes (0010, 0013) land behind the
PreToolUse hook + CODEOWNERS review; any change that would require editing the
invariant tests to pass is a STOP.
