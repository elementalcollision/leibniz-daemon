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
  - **Lever 3 — stronger/longer prover**: more consensus depth / tokens per attempt.
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
- **Decomposition** — lemma extraction (a deeper form of M3) for genuinely hard
  conjectures.

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
