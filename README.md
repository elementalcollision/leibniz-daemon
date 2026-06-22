# Leibniz · *Calculemus*

> *"When there are disputes among persons, we can simply say: let us calculate, without further ado, to see who is right."* — G.W. Leibniz

An agentic theorem daemon for the discovery of **novel, tractable, kernel-proven**
results. Where its predecessor *Newton* (`newton-daemon`) *demonstrates* — runs a
mutation-hardened acceptance test in a sandbox — Leibniz *calculates*: it
discharges a formal proof obligation against the Lean kernel. The difference is a
deliberate inversion of one seam Newton pre-wired and left dormant
(`proof_obligation`).

The public reading-room of a deployment is named **Calculemus** (analogous to
Newton's *Principia*): the ledger of theorems settled by calculation.

## The one idea

A system whose value is *proven* results has exactly one existential risk: a
**kernel-valid proof of a mis-stated theorem**. It is most authoritative exactly
when it is most wrong, and a public ledger makes that failure permanent. Newton's
agent identified this as a 3-body problem; Leibniz is built around defusing it.

So the architecture's spine is a **trust hierarchy** that confines LLMs to
*proposing* and lets only mechanical checkers *decide*:

| Edge | Who decides | Trust tier |
|---|---|---|
| proof ↔ formal statement | the Lean kernel | **mechanical** (never an LLM) |
| novelty / non-triviality | retrieval + a decision procedure | **mechanical** |
| **formal statement ↔ claim (Enuntiatio)** | gaming-witness → claim-probe → judge | **adversarial → mechanical → (bounded) judged** |

LLMs occupy only the proposal roles in `leibniz.types.Role` (survey, conjecture,
formalize, proof-draft, analogy). Every draft crosses a mechanical or adversarial
gate before it can become a law. That is the literal meaning of "without relying
on capricious LLMs," and `leibniz.trust.TrustPolicy` enforces it at promotion —
no cycle can promulgate a law whose proof was not kernel-checked.

## The organ map (combining the extant code)

- **Chimera → runtime (the body).** Scheduler, memory, cross-model witness, drift.
  Real today: `leibniz.runtime.PersistentRuntime` (SQLite memory that survives
  restarts + clock-based circadian phase, ADR 0016); external-Chimera wiring drops
  in behind the same `leibniz.adapters.RuntimeAdapter` Protocol.
- **Newton → loop + ledger (the spine).** The six stages and the
  Enuntiatio/Expressio/Demonstratio triad, kept wholesale; only the Demonstratio
  backend flips from execution-gate to kernel proof. → `leibniz.pipeline`, `leibniz.propositio`
- **KFM → selection.** Kill / recombine / commit as a quality-diversity operator
  over a MAP-Elites archive; the discovery loop re-seeds SURVEY from recombined
  parents (ADR 0009). → `leibniz.selection`, `leibniz.daemon.run_cycles`
- **Leonardo → cross-domain analogy (the eyes).** Confirmed: a live da-Vinci-voice
  journaling agent, **not** a survey oracle — so it supplies cross-domain analogies
  from its Forge, with frontier-survey from a curated source (ADR 0007). →
  `leibniz.leonardo.LeonardoForgeAdapter`
- **Proposal → the variation operator.** Anthropic (Claude) for CONJECTURE/FORMALIZE
  (with mechanical import-repair, ADR 0012); an OpenRouter prover ensemble for
  PROOF_DRAFT under **N+1 kernel-verified consensus** (ADR 0005/0006). →
  `leibniz.providers`, `leibniz.consensus`
- **Verification → the judge.** The real Lean 4 kernel (in an OrbStack container,
  via `lake env lean` — LeanDojo deferred, ADR 0003) + Z3 gaming-witness (ADR 0004) +
  a structural-hash novelty corpus (ADR 0007 corpus). → `leibniz.verifiers`,
  `leibniz.backends`, `leibniz.corpus`
- **Calculemus → the reading-room (the public face).** A standalone private repo,
  [`codex-calculemus`](https://github.com/elementalcollision/codex-calculemus) — an
  Astro static site that renders the operator-published ledger (the triad + kernel
  certificate) as an illuminated codex, in continuity with the sibling Codex
  Vitruvianus (ADR 0017). This repo is the producer: `leibniz.calculemus_site` +
  `scripts/export_calculemus.py` serialize and kernel-re-verify the ledger. →
  [codexcalculemus.com](https://codexcalculemus.com)

## Run the scaffold

```bash
pip install -e ".[dev]"   # core is stdlib-only; the dev extra adds pytest + ruff
python demo.py            # turn one circadian cycle (deterministic fakes)
pytest -q                 # 11 trust-invariant tests must stay green
```

The demo wires deterministic fakes and turns one circadian cycle. You should see
each gate fire once — a conjecture killed at cheap refutation, one as
known, one as trivial, one as *gamed* (faithfulness), and one surviving to a
kernel-checked `Q.E.D.` — with only the survivor paying for proof.

## Lean kernel (R1)

The real kernel runs in a pinned container (the host stays stdlib-only; Lean lives
in the container — see `docs/adr/0003-r1-lean-backend.md`):

```bash
docker build -f docker/lean.Dockerfile -t leibniz-lean:v4.31.0 .   # OrbStack/Docker
pytest -q -m lean                                                  # R1 kernel exit tests
```

Tests tagged `lean` skip automatically where the image is absent (e.g. CI), so the
stdlib invariant suite stays the universal gate.

## Layout

```
leibniz/
  types.py · trust.py · propositio.py        # vocabulary, policy, ledger triad (guarded core)
  pipeline.py · daemon.py                     # six stages; circadian loop + run_cycles discovery
  gates/{faithfulness,novelty,verification}.py# the three decision gates (guarded)
  verifiers.py                                # LeanVerifier (sole kernel writer) + SMTVerifier
  selection.py                                # KFM + MAP-Elites archive (descriptor, curiosity, recombine)
  probes.py · imports.py · corpus.py          # faithfulness probes · import-resolver · novelty corpus
  consensus.py                                # cascaded/witness provers, N+1 kernel consensus
  budget.py · cost.py                         # judged-faithfulness budget · USD cost cap
  backends/{lean_cli,smt_z3}.py               # real Lean (container) + Z3
  providers/{anthropic_provider,openrouter_provider,prover,router}.py  # proposal models
  leonardo.py · adapters.py                   # Leonardo analogy seam · Protocols
  assembly.py · calculemus.py                 # build_daemon (real stack) · public ledger + publish tier
demo.py                                       # one cycle, deterministic fakes
scripts/{run_live,build_corpus}.py            # live e2e run · corpus index builder
docs/adr/0001..0013 · docs/{architecture,capability-ladder,optimization-roadmap}.md
tests/                                        # 11 invariants (byte-frozen) + ~120 more
```

## Run it live (autonomous)

The production daemon wires the real backends (Lean kernel + Z3 + novelty corpus +
Anthropic/OpenRouter providers + consensus + Leonardo). It needs credentials in a
gitignored `.env` (`ANTHROPIC_API_KEY`, `OPENROUTER_API_KEY`, `LEIBNIZ_PROVER_MODELS`;
see `.env.example`) and the Lean image:

```bash
cp .env.example .env && $EDITOR .env          # add your keys
python scripts/run_live.py 1 1                 # one bounded circadian cycle, real calls
```

It surveys → conjectures (Claude) → formalizes (with import-repair) → runs the
mechanical gates → proves under N+1 consensus → promulgates. Promulgation ≠
publication: a law reaches the public *Calculemus* ledger only after an explicit
operator publish (`leibniz.calculemus`, ADR 0008).

## Status

The full capability ladder **R0–R6 is built and merged** (`docs/capability-ladder.md`),
plus the post-R6 optimizations **ADR 0009–0013** (`docs/optimization-roadmap.md`):

- **Trust boundary (R0–R3):** real Lean 4.31 kernel · Z3 gaming-witness + claim
  probes · enforced 0.15 judged budget · structural-hash novelty corpus.
- **Intelligence (R4–R5):** Anthropic + OpenRouter proposal models · cascaded/witness
  proving with N+1 kernel consensus · MAP-Elites selection with a closed discovery loop.
- **Ledger (R6):** *Calculemus* renderer + operator publish tier.
- **Hardening:** autoformalization import-resolver · concurrent ensemble + USD cap ·
  trust-edge provenance (construction-site AST-guard).

The daemon runs end-to-end live; **autonomous *discovery* (reliably promulgating a
novel theorem) is the open frontier** — a tuning matter, not a trust-boundary one.
The boundary held throughout: `tests/test_invariants.py` is byte-identical across
every change (~120 tests green). Tracked at `github.com/elementalcollision/leibniz-daemon`
with branch protection, a PreToolUse trust-edge hook, CODEOWNERS, and CI.
