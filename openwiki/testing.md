---
type: Reference
title: Testing and Trust Invariants
description: The 11 byte-frozen trust invariants in tests/test_invariants.py that enforce the trust boundary in CI, the lean/z3 pytest markers that skip where the container/extra is absent, and the boundary guards that pin the sole kernel_verified writer.
tags: [testing, invariants, trust, ci, pytest, lean-tests, z3, boundary-guards, regressions]
---

# Testing and Trust Invariants

A memory file (CLAUDE.md) is *context, not enforcement*. `tests/test_invariants.py` is the **enforcement**: it turns each non-negotiable invariant into a test that fails CI if a future change breaks it. **If a change requires editing `tests/test_invariants.py` to pass, STOP — you are weakening the trust boundary. Surface it to the operator.**

## The 11 trust invariants

| # | Invariant | Test |
|---|---|---|
| 1 | A proof may only be settled by the kernel (MECHANICAL) | `test_proof_edge_must_be_mechanical`, `test_proof_edge_adversarial_also_rejected` |
| 2 | Novelty is never settled by an LLM judge | `test_novelty_edge_may_not_be_judged` |
| 3 | No promotion without a proof edge present | `test_promotion_requires_a_proof_edge` |
| 4 | No promotion without a faithfulness edge present | `test_promotion_requires_a_faithfulness_edge` |
| 5 | A non-PASS edge can never promote | `test_non_pass_edge_blocks_promotion` |
| 6 | JUDGED faithfulness is permitted but detected as residual | `test_judged_faithfulness_is_permitted_but_detectable` |
| 7 | `Q.E.D.` requires `kernel_verified`; the seal | `test_qed_requires_kernel_verification` |
| 8 | `is_promotable` true only on a complete mechanical path | `test_is_promotable_true_only_on_complete_mechanical_path` |
| 9 | `is_promotable` false when the proof edge is judged | `test_is_promotable_false_when_proof_is_judged` |
| 10 | `is_promotable` false without a proof edge | `test_is_promotable_false_without_proof` |
| 11 | (the invariant count; the suite is byte-frozen) | — |

## The boundary guards

`tests/test_boundary_guards.py` pins the **sole writer** discipline — `LeanVerifier.discharge` is the only place `kernel_verified` is set, and the promotion flag is written only on the two `TrustPolicy`-routed paths (not from a recalled memory). `tests/test_kernel_verified_writers.py` is the same discipline at the kernel-writer level.

## The lean/z3 markers

`pyproject.toml` registers two pytest markers:

- `lean` — requires the pinned Lean container (`leibniz-lean:v4.31.0`); skipped where absent (e.g. CI).
- `z3` — requires the `verify` extra (`z3-solver`); skipped where absent.

`testpaths = ["tests"]` pins discovery to `tests/` so `pytest -q` from the repo root always collects the invariant suite; a "0 collected" run is a failure, not a vacuous pass.

## Running

```bash
pip install -e ".[dev]"        # core is stdlib-only; the dev extra adds pytest + ruff
python demo.py                 # turn one circadian cycle (deterministic fakes)
pytest -q                      # ~11 invariant tests must stay green
ruff check .                   # lint

# Real kernel (R1):
docker build -f docker/lean.Dockerfile -t leibniz-lean:v4.31.0 .
pytest -q -m lean             # R1 kernel exit tests (skipped where the image is absent)
```

The stdlib invariant suite is the **universal gate** — it runs everywhere, with no extras and no container. The `lean`/`z3` tests deepen coverage where the real backends are present but never weaken the boundary where they are absent.

## The invariant count

The repo runs ~120 tests; the 11 invariants in `test_invariants.py` are **byte-identical across every change** (the CLAUDE.md discipline). The broader suite (~120 tests) covers the capability ladder rungs, the sound backends, the consensus/repair, the Walnut/Observatory tier, the instance isolation, the seed/tool ingestion, and the many formalized theorem families in `scripts/` (each `verify_*`/`export_*` script is a kernel-checked cycle).
