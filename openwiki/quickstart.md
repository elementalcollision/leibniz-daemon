---
type: Guide
title: Quickstart
description: How to install, run the deterministic demo, and execute the trust-invariant test suite for the Leibniz agentic theorem daemon.
tags: [quickstart, getting-started, demo, tests]
---

# Quickstart

Leibniz · *Calculemus* is an agentic theorem daemon whose core value is **kernel-proven** results. Its defining rule: **LLMs propose; only mechanical checkers (the Lean kernel, Z3) decide.** The core package is pure stdlib by design so the trust boundary stays legible.

## Install

```bash
pip install -e ".[dev]"   # core is stdlib-only; the dev extra adds pytest + ruff
```

The real backends are optional extras that never touch the import path of the stdlib core:

```bash
pip install -e ".[verify,propose,dev]"   # adds z3-solver, lean-dojo, anthropic SDK
```

Distribution name is `leibniz-daemon`; the import package is `leibniz` (`pyproject.toml` wires `hatchling` to build the `leibniz` directory).

## Turn one circadian cycle (deterministic fakes)

```bash
python demo.py
```

`demo.py` wires deterministic fakes (a `FakeLean`, `FakeSMT`, `FakeProvider`, `FakeLeonardo`, `FakeCorpus`) and turns one circadian cycle. You should see each gate fire once — a conjecture killed at cheap refutation, one as `KNOWN`, one as `TRIVIAL`, one as `GAMED` (faithfulness), and one surviving to a kernel-checked `Q.E.D.` — with only the survivor paying for proof compute.

## Run the trust invariants

```bash
pytest -q
```

The 11 executable trust invariants in `tests/test_invariants.py` must stay green; they are the **enforcement**, not just documentation. A "0 collected" run is treated as a failure, not a vacuous pass (`pyproject.toml` pins `testpaths = ["tests"]`).

## Lint

```bash
ruff check .
```

## The real Lean kernel (R1)

The kernel runs in a pinned container; the host stays stdlib-only:

```bash
docker build -f docker/lean.Dockerfile -t leibniz-lean:v4.34.0-rc2 .   # OrbStack/Docker
pytest -q -m lean                                                  # R1 kernel exit tests
```

Tests tagged `lean` skip automatically where the image is absent (e.g. CI), so the stdlib invariant suite stays the universal gate.

## Run it live (autonomous)

The production daemon needs credentials in a gitignored `.env` and the Lean image:

```bash
cp .env.example .env && $EDITOR .env          # add ANTHROPIC_API_KEY, OPENROUTER_API_KEY, LEIBNIZ_PROVER_MODELS
python scripts/run_live.py 1 1                 # one bounded circadian cycle, real calls
```

See [Trust Invariants](trust-invariants.md) for the rules every change must preserve, [Instance Isolation](instance-isolation.md) for the prod/uat/dev split, and [Optimization Roadmap](roadmap.md) for the post-R6 discovery disposition.
