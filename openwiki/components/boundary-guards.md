---
type: Component
title: Boundary Guards
description: The structural AST guards (test_boundary_guards.py, test_kernel_verified_writers.py) that pin who may write kernel_verified and promulgated, and who may mint a PROOF_EDGE — sole-source enforcement that complements the runtime TrustPolicy checks.
tags: [boundary-guards, kernel-verified, promulgated, proof-edge, ast-guards, sole-source, tests, enforcement]
---

# Boundary Guards

`tests/test_boundary_guards.py` and `tests/test_kernel_verified_writers.py` complement `tests/test_invariants.py` by pinning **who may write** the two most security-relevant fields, so a stray writer added during a later rung's backend wiring is caught **mechanically** rather than by review alone. They are pure-AST, CI-safe, and run on every `pytest -q`.

## The sole-fresh-writer guard (`kernel_verified`)

`Demonstratio.kernel_verified` is the field that gates promotion (invariant 1). The AST guard scans every `<something>.kernel_verified = ...` assignment and every `Demonstratio(kernel_verified=...)` constructor kwarg across `leibniz/` and asserts the write sites are exactly the sanctioned whitelist (`tests/test_kernel_verified_writers.py::_WHITELIST`):

| Site | Kind | Role |
|---|---|---|
| `leibniz/verifiers.py::LeanVerifier::discharge` | `attr_assign` | **MINTS** the fresh verdict from a real kernel check |
| `leibniz/runtime.py::_row_to_prop` | `ctor_kwarg` | **REPLAYS** a persisted verdict (recall, not a decision) |

Any other write site — an attribute assignment or a constructor kwarg anywhere else — is a trust-boundary red flag and fails the guard. The guard also has positive tests that a planted writer is detected.

## The `promulgated` write guard

`tests/test_boundary_guards.py::test_promulgated_is_set_only_in_policy_routed_paths` scans every `promulgated = ...` assignment and asserts it is set only in the two paths that route through `TrustPolicy.validate_path`:

| Site | What it does |
|---|---|
| `pipeline.py::Promulgate.run` | sets `promulgated` iff `is_promotable` (which calls `validate_path`) |
| `gates/verification.py::VerificationGate.finalize` | sets `promulgated` iff `is_promotable` |

A new writer here would bypass the policy. The runtime's `remember` deliberately **never** sets it — a recalled memory is a historical record, not a live promotion.

## The `kernel_verified` single-writer guard (R1)

`tests/test_boundary_guards.py::test_kernel_verified_has_a_single_writer` asserts only `LeanVerifier.discharge` may assign `kernel_verified`. No backend, cache, or retry path may write it directly — the backend only **reports** what the kernel said; `discharge` is the sole writer of the stamp.

## The PROOF_EDGE construction-site guard (ADR 0013 §3)

`tests/test_boundary_guards.py::test_proof_edge_is_constructed_only_in_kernel_paths` scans every `EdgeEvidence(edge=PROOF_EDGE, ...)` construction and asserts it is constructed only in:

- `verifiers.py::discharge` — the kernel.
- `consensus.py::prove` — which copies `discharge`'s edge (annotating it with the consensus count).

Any other construction site would let a non-kernel verdict masquerade as a proof — caught here **structurally**, closing the `producer=None` gap that the runtime provenance check alone cannot.

## Why both layers

`TrustPolicy.validate_edge` checks the `producer` string on an `EdgeEvidence` at promotion time (runtime, per-edge). The AST guards check the **source** for who may even construct the evidence (compile-time, across the whole package). Together they close both the "a mislabeled producer" gap and the "an unauthorized writer" gap. See [Trust Invariants](../trust-invariants.md) for the behavioral invariants and [Verifiers](verifiers.md) for the `discharge` seam.
