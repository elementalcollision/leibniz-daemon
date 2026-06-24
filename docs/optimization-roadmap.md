# Optimization Roadmap (post-R6)

The capability ladder R0–R6 is built: the trust boundary is real and the daemon
runs end-to-end live. The remaining work is **making it a productive discovery
engine** without ever weakening the boundary. Each optimization is captured as a
**Proposed** ADR so it can be approved deliberately before implementation (the
project's discipline: decisions get an ADR, and trust-guarded changes get operator
sign-off via the PreToolUse hook).

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
