# ADR 0048 — Coq and Isabelle as proof-edge deciders alongside Lean (multi-kernel admission)

- **Status:** ACCEPTED for the **report-only backends + amplification demo** (landed, live-validated);
  **PROMOTION DEFERRED** — the verifier/registry seam and the trust edits that would let a Coq/Isabelle
  proof *promulgate* are an operator act and are **not made** by this ADR.
- **Date:** 2026-07-05
- **Deciders:** Operator (sign-off required before any `trust.py` / trust-guard edit and before registering
  a non-Lean verifier in the live pipeline).
- **Siblings:** ADR 0001 (charter / trust hierarchy), ADR 0003 (R1 Lean backend — the pattern the backends
  mirror), ADR 0013 (trust-edge provenance — the producer pin), ADR 0041 (trust model; §2.2 the
  `FAITHFULNESS_PRODUCERS` frozenset admission pattern to reuse), ADR 0044 (first decider-admission),
  ADR 0045 (§2/§10 — the `LeanVerifier.discharge` proof-edge admission, unanimously **deferred 8/8** on
  2026-06-30).
- **Touches the proof edge:** the **landed layer does NOT** — it adds *report-only* backends that only
  observe the Coq/Isabelle kernels; it writes no `kernel_verified`, mints no proof edge, and touches no
  trust file. `tests/test_invariants.py`, `tests/test_boundary_guards.py`, and
  `tests/test_kernel_verified_writers.py` all stay **byte-identical and green**. **Promotion DOES** — that
  is the deferred §4.2 operator keystone.

## 1. Context

Leibniz's proof edge has one decider: the Lean 4.31 kernel, via `LeanVerifier.discharge`. Two forces argue
for more:

1. **Verification-amplification is the vindicated role.** Independently re-deciding a published result in a
   *different* kernel is strictly stronger evidence than re-running the same one — a Coq or Isabelle
   re-check is an independent implementation of the trusted-core idea, catching translation and
   kernel-specific errors a Lean-only pipeline cannot.
2. **Reach.** Some corpora are native to Coq (SSReflect / mathcomp) or Isabelle/HOL (the AFP); meeting a
   result in its home kernel avoids a lossy port.

The backend layer is already multi-checker (`lean_repl`, `lean_cli`, `smt_z3`, `walnut`), and ADR 0041
already generalised the *faithfulness* producer pin from a scalar to an operator-owned frozenset
(`FAITHFULNESS_PRODUCERS`). Adding Coq/Isabelle *proof-edge* deciders is the same move on the proof edge —
but the proof edge is the sacred one, so the trust-sensitive half is gated, not autonomous.

## 2. What actually landed (this ADR)

Real, **live-validated**, **report-only** backends and an amplification harness — no trust surface:

- `leibniz/backends/coq_docker.py` — Rocq 9.0 (`rocq/rocq-prover:9.0`), source on stdin → `rocq compile`.
  `check_source` / `check_proof` / `check_source_with_detail` only **report** the kernel verdict.
- `leibniz/backends/isabelle_docker.py` — Isabelle2025, native arm64
  (`makarius/isabelle:Isabelle2025_ARM`), a one-theory HOL session → `isabelle build`. Same report-only
  surface. (`image`/`platform` are overridable for an amd64 host.)
- `scripts/verify_multi_kernel.py` + `docs/crt/{coq_demo.v,isabelle_demo.thy}` — genuine theorems
  kernel-verified end-to-end via `backend.check_source`, **with self-laundered and broken proofs correctly
  rejected**. Audit tier; no `Demonstratio`, no `kernel_verified`, no proof edge.
- `tests/test_{coq,isabelle}_backend.py` — CI-safe parsing/scan tests + Docker-gated live-kernel gating.

The live demo (gate GREEN) shows both kernels *gate*, not rubber-stamp:

| Case | Rocq 9.0 | Isabelle2025 |
|---|---|---|
| valid theorem | `Print Assumptions` → *Closed under the global context* → **PASS** | `isabelle build` exit 0 → **PASS** |
| self-laundered | `Admitted` → open axiom exposed → **REJECT** | `sorry` → hard error (`quick_and_dirty=false`) → **REJECT** |
| broken | unification error, exit 1 → **REJECT** | *Failed to finish proof*, exit 1 → **REJECT** |

The trust rule per kernel mirrors Lean's `#print axioms` / no-`sorry` discipline, **hardened after an
adversarial review (2026-07-05) found and closed two false-PASS holes** (both now pinned as regression tests):

- **Coq** = compile-clean **and** closed-under-global-context (or only operator-approved axioms) **and** no
  `Admitted`/`admit`/`Axiom`/`Parameter`/`Hypothesis`/`Variable`/`Context`. The review showed a proof could
  hide an axiom (`Require Import Classical; apply classic`) by omitting `Print Assumptions`; the backend now
  **injects `Print Assumptions <thm>.` for every declared theorem**, so the audit runs on kernel output the
  prover cannot suppress. `Variable`/`Context` (section hypotheses the stated theorem secretly rests on)
  were added to the forbidden set.
- **Isabelle** = build-clean at `quick_and_dirty=false` (hard-errors on `sorry`) **and** no
  `oops`/`axiomatization`/`quick_and_dirty` **and none of the ML/oracle escape hatches**
  (`tactic`/`ML*`/`oracle`/`Skip_Proof`/`cheat_tac`). The review showed `by (tactic ‹Skip_Proof.cheat_tac …›)`
  — the oracle `sorry` desugars to — proves `2+2=5` with exit 0 and no error marker; the scan now keeps
  PROOF cartouches (stripping only comments and DOC cartouches) so such a cheat is caught.

## 3. Decision

**Adopt Coq and Isabelle as proof-edge deciders in two separable layers**, and land only the first now:

### 4.1 Amplification layer — report-only, NOT trust-sensitive (LANDED)

The backends only *observe* the Coq/Isabelle kernels. They never write `Demonstratio.kernel_verified`, never
construct a `PROOF_EDGE`, and import nothing from `trust.py`. This is why the three structural trust guards
(`test_invariants.py`, `test_boundary_guards.py`, `test_kernel_verified_writers.py`) stay byte-identical and
green — there is no new mint site to whitelist. This layer is sufficient for the vindicated role
(independent verification-amplification, audit tier).

### 4.2 Promotion layer — trust-sensitive, operator-gated (DEFERRED, NOT landed)

To let a Coq/Isabelle proof *promulgate* (route through `TrustPolicy` into a promulgated law), the operator,
as a PreToolUse-guarded keystone, must:

1. Add `CoqVerifier` / `IsabelleVerifier` (exact structural mirrors of `LeanVerifier`: each runs its **own**
   kernel through its own backend, sets `kernel_verified` **only** from that real result, stamps
   `tier=MECHANICAL` and its **own** producer string) and a `VerifierRegistry` that routes `discharge` by a
   new `Expressio.target_checker` field (default `"lean"`) and **fails closed** on an unregistered kernel.
   *These add new `kernel_verified` write sites and new `PROOF_EDGE` mint sites,* so this step also updates
   the two structural trust guards — adding `CoqVerifier::discharge` / `IsabelleVerifier::discharge` to
   `test_kernel_verified_writers.py::_WHITELIST` and the corresponding sites in `test_boundary_guards.py`.
   Those whitelist edits are **themselves trust decisions** (the guard says so) and are the operator's, not
   the agent's — the guards deliberately failed when the agent prototyped this layer, which is the guard
   working as designed.
2. Refactor `trust.py`'s `KERNEL_PRODUCER` (scalar) → `KERNEL_PRODUCERS` (frozenset) + keep the alias, and
   change `validate_edge` from `!= KERNEL_PRODUCER` to `not in KERNEL_PRODUCERS` — the **exact** shape ADR
   0041 used for `FAITHFULNESS_PRODUCERS`, which did **not** touch `test_invariants.py` (it asserts *tier*
   and *consequence*, never the producer string). Then add the admitted kernel's producer string — **one act
   per kernel**.
3. Wire the live `pipeline.py` / `consensus.py` / `proof_repair.py` discharge calls through the registry
   (Lean-only until a second kernel is registered → byte-identical), and pin the images by immutable
   `sha256` digest.

Per the ADR 0045 precedent (the analogous `LeanVerifier.discharge` proof-edge admission was **deferred
8/8**), each kernel's admission should route through a per-kernel witness round, and is **recommended
deferred** until a real beat needs Coq/Isabelle *promulgation* (amplification is live now).

## 5. Trust analysis — why the boundary is not weakened

- **All three structural guards stay byte-identical.** The landed layer adds no `kernel_verified` writer and
  no `PROOF_EDGE` constructor (confirmed: 0 diff lines in `trust.py`, `test_invariants.py`,
  `test_boundary_guards.py`, `test_kernel_verified_writers.py`). The §4.2 promotion layer *does* add mint
  sites — and that is exactly why it is fenced behind an operator whitelist edit, not landed here.
- **No LLM decides.** Coq/Isabelle proof text is DRAFTED by a proposer and DECIDED by `coqc`/`isabelle`; the
  backend only reports the kernel verdict.
- **Fail-closed.** `available()` returns `False` (never raises) when Docker is down → the kernel is simply
  unavailable and nothing is verified — never a false PASS. Self-laundering (`Admitted`/`sorry`) is
  rejected, as the live demo shows.
- **N+1 independence is unaffected.** A Lean proof and a Coq proof are *different obligations*, not two
  votes on one; cross-kernel consensus needs a sound cross-language statement-equivalence relation and is
  **out of scope** here (a future ADR).

## 6. Consequences

- **Now:** independent Coq/Isabelle re-decision is available for verification-amplification (audit tier) via
  the report-only backends. Images are pinned: `makarius/isabelle:Isabelle2025_ARM` runs **native arm64**;
  `rocq/rocq-prover:9.0` is amd64-only, so it runs under Rosetta on arm64 hosts (`platform` is overridable).
- **Deferred / open (HANDOFF ticket):** the §4.2 promotion layer — verifier/registry classes, the
  `Expressio.target_checker` field, the two trust-guard whitelist edits, the `KERNEL_PRODUCERS` refactor +
  per-kernel witness round, live-pipeline wiring, `sha256` image pinning, who sets `target_checker`
  (recommend: always `"lean"` until a proposer opts in), per-kernel forbidden-construct ratification, and
  cross-kernel consensus.

## 7. Alternatives considered

- **Land the verifier/registry now (behind `available()`)** — rejected: those classes *write*
  `kernel_verified` and *mint* proof edges, so landing them trips (and would require editing) the
  `test_kernel_verified_writers.py` / `test_boundary_guards.py` trust guards — an operator-only trust
  decision. The report-only backends deliver the amplification value without crossing that line.
- **A single generic "proof backend" with a mode flag** — rejected: collapses three kernels into one code
  path, creating the shared-decision surface the per-verifier design avoids.
- **Admit the producers now (land §4.2 trust edit)** — rejected: it touches the proof edge, and the ADR
  0045 witness round deferred the analogous edit 8/8 as premature absent a live promulgation demand.
- **Translate Coq/Isabelle corpora into Lean and re-check in Lean only** — rejected for amplification: it
  re-runs the *same* kernel and imports translation risk, forfeiting the independence that is the point.
