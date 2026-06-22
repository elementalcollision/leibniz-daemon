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

## Remaining follow-ups

- **Deeper live calibration** — a ≥5-cycle run so the frontier band adapts past the
  warm-up and the prover's reach is found, plus a larger proof-draft budget / more
  attempts; persist the band across runs (ADR 0019 open questions).
- **Decomposition** — lemma extraction (a deeper form of M3) for genuinely hard
  conjectures.
- **Faithfulness on prose claims** — confirm the gaming-witness bites on the
  structured contract rather than passing vacuously (ADR 0019 open question).

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
