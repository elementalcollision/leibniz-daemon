# Leibniz · *Calculemus*

> *"When there are disputes among persons, we can simply say: let us calculate, without further ado, to see who is right."* — G.W. Leibniz

An agentic theorem daemon for **novel, tractable, kernel-proven** results. Where its
predecessor *Newton* (`newton-daemon`) *demonstrates* — runs a mutation-hardened
acceptance test in a sandbox — Leibniz *calculates*: it discharges a formal proof
obligation against the Lean kernel. The difference is a deliberate inversion of one
seam Newton pre-wired and left dormant (`proof_obligation`).

The daemon now **runs itself**: a nightly beat turns capped, journaled cycles against
`origin/main`, files what it promulgates into a review queue, and alarms on its own
anomalies. Nothing publishes itself — publication is an explicit operator act.

The public reading-room of a deployment is named **Calculemus** (analogous to Newton's
*Principia*): the ledger of theorems settled by calculation →
[codexcalculemus.com](https://codexcalculemus.com).

## The one idea

A system whose value is *proven* results has exactly one existential risk: a
**kernel-valid proof of a mis-stated theorem**. It is most authoritative exactly when it
is most wrong, and a public ledger makes that failure permanent. Newton's agent
identified this as a 3-body problem; Leibniz is built around defusing it.

So the architecture's spine is a **trust hierarchy** that confines LLMs to *proposing*
and lets only mechanical checkers *decide*:

| Edge | Who decides | Trust tier |
|---|---|---|
| proof ↔ formal statement | the Lean 4.34 kernel | **mechanical** (never an LLM) |
| novelty / non-triviality | retrieval + a decision procedure | **mechanical** |
| **formal statement ↔ claim (Enuntiatio)** | gaming-witness → claim-probe (Z3 / kernel-decided / exact) → judge | **adversarial → mechanical → (bounded) judged** |

LLMs occupy only the proposal roles in `leibniz.types.Role` (survey, conjecture,
formalize, proof-draft, analogy). Every draft crosses a mechanical or adversarial gate
before it can become a law. That is the literal meaning of "without relying on capricious
LLMs," and `leibniz.trust.TrustPolicy` enforces it at promotion — no cycle can promulgate
a law whose proof was not kernel-checked.

The boundary has held across every change: `tests/test_invariants.py` (11 tests) is
**byte-identical** from R0 to today, alongside two structural guards
(`test_boundary_guards.py`, `test_kernel_verified_writers.py`) that pin *who may write*
`kernel_verified` and mint a proof edge. Four enforcement layers back it — the tests, a
PreToolUse hook on the trust files, `CODEOWNERS` + branch protection, and a blocking CI
job that also refuses a vacuous 0-collected pass.

## What it actually does today

Two output paths, both behind the same boundary:

- **Verification-amplification (the vindicated role, and most of the ledger).**
  Independently *re-deciding* a recently published mathematical result's finite core with
  an exact mechanical decider, and publishing the ones that survive. Tiers:
  **kernel-decided** (Lean `decide`, axiom-audited), **exact-procedure** (exact ℚ /
  GF(pᵏ) / exact enumeration), and **cross-kernel** (the same core re-decided in Rocq).
  This has produced kernel-attested **disproofs of published conjectures** (Stanley's
  dimer conjecture, Brualdi–Friedland–Pothen, Ziegler's cross-polytope, Mason's
  log-concavity, a 2025 Kochen–Specker PRL conjecture, a 1984 Hill conjecture),
  resolutions of open existence questions (complex Hadamard order 94), and a record
  (kissing number k(19) ≥ 11948) — plus real *faithfulness catches*, where the exact
  decider found a dropped sign or a table typo before anything was published.
- **Origination (ADR 0050/0063).** A fact the daemon conjectured itself, carrying no
  source citation, which must instead **pass the full mechanical novelty gate** and carry
  that PASS as its `novelty_attestation`. Fail-closed: no gate PASS, no originated law.

And one honest negative, because it is load-bearing: **autonomous *novelty* is not
solved.** Four converging probes — a genre A/B, three live Walnut runs, an SOS/
Positivstellensatz reach probe, and a zero-LLM enumeration audit — plus a full
producer-*method* sweep on a record-factory backend, all concluded that the region that is
*soundly checkable **and** finitely encodable* is the *textbook* region. The binding
constraint is the **producer** (a structural encoding gap), not soundness, prover reach,
or compute. Read `docs/autonomous-discovery-arc-capstone.md` and
`docs/discovery-ceiling-cross-backend-finding.md` before proposing "another checker" —
that lever is measured and closed.

## The organ map

- **Newton → loop + ledger (the spine).** Six stages — Survey · Conjecture · Formalize ·
  Derive · Demonstrate · Promulgate — over the Enuntiatio/Expressio/Demonstratio triad,
  kept wholesale; only the Demonstratio backend flips from execution-gate to kernel proof.
  → `leibniz.pipeline`, `leibniz.propositio`
- **Chimera → runtime (the body).** Scheduler, memory, drift. Real today:
  `leibniz.runtime.PersistentRuntime` (SQLite memory that survives restarts + clock-based
  circadian phase, ADR 0016), with a write-barrier that fails closed if a UAT run is
  pointed at the PROD ledger (ADR 0033). → `leibniz.runtime`, `leibniz.instance_config`
- **KFM → selection.** Kill / recombine / commit as a quality-diversity operator over a
  MAP-Elites archive; the discovery loop re-seeds SURVEY from recombined parents (ADR
  0009), steered by a frontier band that escapes its own saturation (ADR 0018, 0080).
  → `leibniz.selection`, `leibniz.discovery`, `leibniz.daemon.run_cycles`
- **Proposal → the variation operator.** Anthropic (Claude) for CONJECTURE/FORMALIZE with
  mechanical import-repair (ADR 0012); an OpenRouter/HF prover ensemble plus the Harmonic
  Aristotle agent for PROOF_DRAFT under **N+1 kernel-verified consensus** (ADR 0005/0006/
  0028); and the ADR 0029 agentic **repair panel** that feeds the kernel's actual complaint
  back to a distinct reasoner. → `leibniz.providers`, `leibniz.consensus`,
  `leibniz.proof_repair`
- **Verification → the judge.** The real Lean 4 kernel in a pinned container (`lake env
  lean` and a long-lived REPL, ADR 0003/0011) + Z3 gaming-witness (ADR 0004) + six
  kernel-decided faithfulness procedures + a structural-hash novelty corpus. Report-only
  Rocq/Coq and Isabelle backends observe a second kernel but may never stamp anything (ADR
  0048). → `leibniz.verifiers`, `leibniz.backends`, `leibniz.gates`, `leibniz.corpus`
- **Feed → the moving frontier.** A deterministic, deliberately **LLM-free** arXiv sweep
  that scores abstracts for finite-core signals and queues amplification targets for the
  operator; queued targets then steer the conjecturer (ADR 0069, 0083, 0084, 0091).
  → `leibniz.arxiv_feed`, `leibniz.seed_intake`
- **Calculemus → the reading-room (the public face).** The operator-published ledger (the
  triad + kernel certificate) rendered as an illuminated codex by the sibling repo
  [`codex-calculemus`](https://github.com/elementalcollision/codex-calculemus), in
  continuity with the Codex Vitruvianus (ADR 0017). This repo is the producer:
  `leibniz.calculemus_site` + `scripts/export_*.py` serialize and kernel-re-verify.
- **Newton exchange → the dialogue.** Each promulgated law also exports as a Newton-shaped
  Propositio folio — YAML frontmatter in Newton's vocabulary, the full Lean Expressio, and
  a self-contained *Auditio mechanica* Newton can re-run. Every folio ships
  `verified: false`; Newton's stamp is Newton's to make (ADR 0072).
  → `leibniz.newton_exchange`

## Quickstart

```bash
pip install -e ".[dev]"    # core is stdlib-only by design; dev adds pytest + ruff
python demo.py             # turn one circadian cycle (deterministic fakes)
pytest -q                  # 1,885 tests; the 11 byte-frozen trust invariants are the gate
ruff check .               # lint (rule set pinned in pyproject; CI is blocking)
```

The demo wires deterministic fakes and turns one cycle. You should see each gate fire
once — a conjecture killed at cheap refutation, one as known, one as trivial, one as
*gamed* (faithfulness), and one surviving to a kernel-checked `Q.E.D.` — with only the
survivor paying for proof.

Tests that need the Lean container, Z3, cvc5, or a network provider **skip cleanly** where
those are absent, so the stdlib invariant suite stays the universal gate. Extras:
`".[verify]"` (Z3), `".[cvc5]"`, `".[propose]"` (Anthropic + Aristotle).

## The Lean kernel

The real kernel runs in a pinned container — the host stays stdlib-only, Lean lives in the
container (ADR 0003; the REPL image amortizes Mathlib import cost per ADR 0011):

```bash
docker build -f docker/lean.Dockerfile      -t leibniz-lean:v4.34.0-rc2      .
docker build -f docker/lean-repl.Dockerfile -t leibniz-lean-repl:v4.34.0-rc2 .
pytest -q -m lean            # R1 kernel exit tests
scripts/run_kernel_tests.sh  # kernel lane: an absent image or a silent skip is a FAILURE
```

`LeanVerifier.discharge` is the **sole** writer of `kernel_verified`. `native_decide` is
forbidden; `sorry`, admitted lemmas and unaudited axioms are never accepted. Every kernel
theorem is `#print axioms`-audited — Lean's canonical trusted axioms at most (`propext`,
`Classical.choice`, `Quot.sound`), **never `sorryAx`** (`leibniz.backends.lean_axioms`).
A self-hosted `kernel-nightly` CI lane runs the Docker-gated tests that GitHub-hosted
runners cannot; it never reports a false green when no runner is registered.

## The faithfulness gate

The crux (ADR 0002): does the Lean statement actually say what the claim says? The gate
runs in layers, cheapest and most adversarial first:

1. **Gaming-witness search** (Z3, adversarial) — can the statement be satisfied in a way
   that betrays the claim?
2. **Claim probes** (mechanical) — a coverage leg and a property leg, both universally
   quantified, both now decided **without a bounded box**, and a vacuous `claim_domain` is
   refused (ADR 0075 + amendment). `established_domain` is derived inside the gate loop
   with byte-exact rollback rather than trusted as autoformalizer free text (ADR 0074).
3. **Kernel-decided fragments** — where Z3 returns *unknown*, the Lean kernel decides the
   faithfulness pair itself by finite residue enumeration, through an audited DSL→Lean
   renderer (`leibniz.dsl_to_lean`, conformance-tested because a mis-encoding renderer
   passes any string check). Six procedures ship: single-modulus (ADR 0055/0056), min/max
   order-split (0059), same-modulus boolean combinations incl. `↔` (0059), mixed-modulus
   via lcm/castHom (0060), symbolic exponents `base^n % m` via multiplicative order (0065),
   and factorial/gcd (0070).
4. **cvc5 second opinion** (ADR 0067/0071) — opt-in, **kill-only**: a cross-solver
   disagreement can refuse, never admit.
5. **OPEN_FORM judged fallback** — the single place LLM judgment may reach a promulgated
   law, and it is budget-bounded (0.15, enforced).

A parallel **Observatory tier** (ADR 0038/0039) records results *decided* by Walnut over
unbounded n. It is deliberately **not Q.E.D.**: it never sets `promulgated`, never mints a
Demonstratio, and never passes through `TrustPolicy.validate_path`.

## The nightly beat (autonomy)

`scripts/heartbeat.py` is one autonomous, capped, journaled beat (ADR 0068). A launchd
agent runs it nightly from a worktree hard-synced to `origin/main`, so unattended runs
execute only **operator-merged** code, never a working tree.

```
PREFLIGHT (Docker up, Lean image present, Z3 importable)
   → N capped cycles through the full steering loop (run_cycles)
   → a JSONL journal entry (funnel, dispositions, cross-solver delta, steering, duration)
   → a regenerated review queue of promulgated-but-held laws
   → an optional arXiv amplification sweep
   → anomaly alarms
```

State lives in the canonical `.leibniz/`: `journal.jsonl`, `review_queue.md`,
`amplification_queue.md`, `alarms.log`, `notebook.json`, `frontier.json`, `memory.db`.
Spend is capped (`LEIBNIZ_DAILY_USD_CAP`). Anomaly detection watches for cross-solver
disagreement, errored cycles, leaked containers, preflight degradation, **equilibria** — a
daemon that stopped exploring (ADR 0082) — and **silence**: a watchdog that journals
*before* it kills a hung beat, a soft between-cycle budget, and a stale-journal alarm for
the beats that never happened (ADR 0092). The review queue is annotated with structural
subsumption but never filtered or reordered; the operator decides (ADR 0086/0087).

```bash
scripts/install_heartbeat.sh                      # install the launchd agent
PYTHONPATH=. python scripts/heartbeat.py          # one beat, by hand
```

## Publication is a separate, human act

**Promulgation ≠ publication.** A law that clears every gate lands in the Codex and the
review queue and stops there. Reaching the public *Calculemus* ledger requires an explicit
operator publish (ADR 0008/0033) — the daemon has no path to the reading-room on its own.
Published laws carry their provenance tier and origination (`amplified` vs `originated`),
the kernel certificate, its axiom footprint, and a re-rendering certificate binding the
statement that was actually promulgated (ADR 0079). As of 2026-09-08 the reading-room
holds **17 laws** (15 amplified, 2 originated) under `site/src/content/laws/`; thirty
Calculemus cycles have been packaged (`scripts/export_*_cycle.py`) — see `HANDOFF-NEXT.md`
§3 for exactly what is published and what awaits the operator's act.

## Run it live

The production daemon wires the real backends. It needs credentials in a gitignored `.env`
(`ANTHROPIC_API_KEY`, `OPENROUTER_API_KEY`, `LEIBNIZ_PROVER_MODELS`; see `.env.example`)
and the Lean images:

```bash
cp .env.example .env && $EDITOR .env    # add your keys
python scripts/run_live.py 1 1          # one bounded circadian cycle, real calls
```

It surveys → conjectures (Claude) → formalizes (with import-repair) → runs the mechanical
gates → proves under N+1 consensus → promulgates. Deploy profiles for dev / uat / prod
live in `deploy/profiles/`; `leibniz.deploy` refuses a profile that would point a non-prod
instance at PROD state, and `leibniz.instance_config` ignores kernel/corpus overrides in
prod entirely — moving PROD's pin is a reviewed code change, not an env var.

## Layout

```
leibniz/
  types.py · trust.py · propositio.py         # vocabulary, policy, ledger triad (guarded core)
  pipeline.py · daemon.py                     # six stages; circadian loop + run_cycles discovery
  gates/{faithfulness,novelty,verification}.py            # the three decision gates (guarded)
  gates/{lean,boolean,minmax,mixed_modulus,power_mod,factgcd}_decided.py  # kernel-decided fragments
  gates/sound_backends.py                     # the exact-or-DEFER backend protocol (ADR 0037)
  verifiers.py                                # LeanVerifier (sole kernel writer) + SMTVerifier
  backends/{lean_cli,lean_repl,lean_axioms}.py            # real Lean: CLI, REPL, axiom audit
  backends/{smt_z3,smt_cvc5,walnut,coq_docker,isabelle_docker}.py  # Z3 · cvc5 · Walnut · report-only kernels
  probes.py · dsl_to_lean.py · imports.py     # claim probes · audited DSL→Lean renderer · import repair
  corpus.py · structural.py · novelty_metrics.py          # novelty corpus · signatures · diversity tripwire
  selection.py · discovery.py · pattern_mining.py         # KFM/MAP-Elites · frontier band · mined seeds
  consensus.py · proof_repair.py · lemma_decomposition.py # N+1 consensus · repair panel · decomposition
  providers/                                  # Anthropic · OpenRouter · HF · Aristotle · decided provers
  arxiv_feed.py · seeds.py · seed_intake.py   # the moving frontier: sweep → validate → steer
  observatory.py · observatory_lint.py · walnut_conjecture.py   # the non-Q.E.D. decided tier
  calculemus.py · calculemus_site.py · origination.py     # ledger, publish tier, originated provenance
  newton_exchange.py                          # Newton folio export (Phase δ)
  runtime.py · instance_config.py · deploy.py # persistent runtime · pinned instances · profile guard
  budget.py · cost.py · pricing.py · env.py   # judged budget · USD cap · pricing · .env loader
  tools/                                      # sandboxed tool use (ADR 0041)
demo.py                                       # one cycle, deterministic fakes
scripts/                                      # heartbeat · run_live · amplify · verify_* · export_*
docker/{lean,lean-repl}.Dockerfile · lean-project/          # the pinned kernel
deploy/{heartbeat,profiles}/                  # launchd beat · dev/uat/prod profiles
docs/adr/0001..0096 · docs/{architecture,capability-ladder,optimization-roadmap}.md
docs/{results,crt,runbooks,audits}/           # per-cycle findings · Lean certificates · runbooks
tests/                                        # 11 byte-frozen invariants + ~1,870 more
```

## Where to read next

| You want | Read |
|---|---|
| the always-on rules | `CLAUDE.md` |
| **to start a fresh session** | `HANDOFF-NEXT.md` — self-contained launchpad, current state, playbook |
| why the trust tiers exist | `docs/adr/0001-charter-and-trust-hierarchy.md` |
| the crux design | `docs/adr/0002-faithfulness-gate.md` |
| the organ map + per-cycle data flow | `docs/architecture.md` |
| the build order (R0–R6) | `docs/capability-ladder.md` |
| **the live work plan** | `docs/optimization-roadmap.md` |
| the porting history and rung tickets | `HANDOFF.md` |
| why autonomous novelty is a closed question | `docs/autonomous-discovery-arc-capstone.md` |
| how to contribute | `CONTRIBUTING.md`, `SECURITY.md` |

## Status (2026-09-08)

The capability ladder **R0–R6 is built and merged**; the project is in the **post-R6
optimization phase**, and the **four-phase autonomy plan is complete** (α heartbeat ·
β moving frontier · γ reach · δ Newton exchange; ADRs 0068–0081). The binding constraint
is **novelty / discovery yield** — not prover reach and not the trust boundary.

- **Trust boundary (R0–R3):** real Lean 4.34 kernel with an axiom audit · Z3
  gaming-witness + unbounded claim probes · six kernel-decided faithfulness fragments ·
  cvc5 kill-only second opinion · enforced 0.15 judged budget · structural-hash novelty
  corpus, including novelty against the daemon's own ledger (ADR 0052/0077/0078).
- **Intelligence (R4–R5):** Anthropic + OpenRouter/HF proposal models · N+1 kernel
  consensus · the ADR 0029 repair panel · MAP-Elites selection with a closed discovery loop.
- **Ledger (R6):** *Calculemus* renderer, provenance tiers, and the operator publish gate.
- **Autonomy:** nightly journaled beats against `origin/main`, review queue, arXiv
  amplification feed, drift and hang detection, Newton folio export.
- **Multi-kernel (ADR 0048):** Rocq/Coq and Isabelle backends are live but **report-only**;
  promotion to a promulgating verifier is deferred and operator-gated. Isabelle has a
  blocking prerequisite: its axiom audit is a source blocklist, not a kernel proof-term
  audit, and three review rounds each found a fresh laundering route.

**What review actually taught us.** In the 2026-07-24→28 sweep, eight of seventeen merged
changes were *defects found by looking*, not planned features — and every trust-edge defect
was surfaced by a skeptic agent with a kernel, never by re-reading. One was found *after*
the change had been declared safe; one hid inside a fail-open `except` whose failure mode
was indistinguishable from success. **Adversarial review is a standing gate on the trust
surface, not a judgment call.** The same discipline keeps finding things: recent work
retracted an unearned GREEN whose record was never kernel-checked, closed two more
fail-open guards (ADR 0089), bounded what the predicate guard *admits* rather than only
how large it is (ADR 0090), and stopped a review-queue feature from blanking the
operator's primary artifact on a pre-migration database (ADR 0087).

Tracked at `github.com/elementalcollision/leibniz-daemon` — public and hardened (ADR 0049),
with branch protection on `main`, `CODEOWNERS` review on every trust file, a PreToolUse
trust-edge hook, least-privilege CI, and a self-hosted kernel lane that never runs fork PRs.

## License

Source-available under the **PolyForm Noncommercial License 1.0.0** — read it, run it,
verify it, use it noncommercially; commercial use needs a separate license. See
`LICENSE.md`. Contributions are welcome under the rules in `CONTRIBUTING.md`; the trust
boundary is off-limits to ordinary PRs by design.
