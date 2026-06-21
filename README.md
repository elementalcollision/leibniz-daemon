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

- **Chimera → runtime (the body).** Circadian scheduler, SQLite memory, the
  cross-model *witness* mechanism, drift/trust telemetry. → `leibniz.adapters.RuntimeAdapter`
- **Newton → loop + ledger (the spine).** The six stages and the
  Enuntiatio/Expressio/Demonstratio triad, kept wholesale; only the Demonstratio
  backend flips from execution-gate to kernel proof. → `leibniz.pipeline`, `leibniz.propositio`
- **KFM → selection.** Kill / recombine / commit as a quality-diversity operator
  over a MAP-Elites archive of conjectures. → `leibniz.selection`
- **Leonardo → survey/analogy front-end (the eyes).** *Tentative role, pending
  confirmation of what Leonardo actually is* — isolated behind one adapter so
  rewiring is a one-file change. → `leibniz.adapters.LeonardoAdapter`
- **NEW → verification (the judge).** Lean kernel + LeanDojo, Z3. The organ Newton
  deliberately omitted. → `leibniz.verifiers`

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
  types.py        # trust tiers, claim types, verdicts, finish reasons
  trust.py        # the enforceable trust policy (the invariant)
  propositio.py   # Enuntiatio / Expressio / Demonstratio (active proof obligation)
  pipeline.py     # survey → conjecture → formalize → derive → demonstrate → promulgate
  gates/
    faithfulness.py  # the crux: gaming-witness → claim-probe → judge
    novelty.py       # external dedup + non-triviality
    verification.py  # deterministic promotion verdict
  selection.py    # KFM over a MAP-Elites archive
  verifiers.py    # Lean (the judge) + Z3 (cheap refuter / gaming-witness)
  adapters.py     # Chimera, provider, Leonardo seams
  daemon.py       # the circadian loop
docs/
  adr/0001-charter-and-trust-hierarchy.md
  adr/0002-faithfulness-gate.md
  capability-ladder.md   # R0..R6 build order
  architecture.md
```

## Status

This is the **R0 scaffold**: interfaces, the loop, the gates, and a passing
dry-run — **assembled and green as of 2026-06-21** (`pytest -q` → 11 passed;
`python demo.py` → one `Q.E.D.` plus one each of refuted/known/trivial/gamed).
Tracked at `github.com/elementalcollision/leibniz-daemon` with branch protection,
a PreToolUse trust-edge hook, and CI. The real Lean/Z3/provider backends are
marked seams. See `docs/capability-ladder.md` for the rung-by-rung build order.
