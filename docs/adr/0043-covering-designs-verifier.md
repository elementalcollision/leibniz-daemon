# ADR 0043 — Covering-designs verifier: the second amplification domain (Track B1)

- **Status:** BUILT (audit-tier; 2026-06-29). Realizes **Track B1** of [ADR 0042](0042-post-d0-program.md)
  after [Gate B0](../gate-b0-second-domain-finding.md) recommended covering designs. Audit-tier, exactly
  the `cwc_check.py` posture — **no trust-boundary change**.
- **Date:** 2026-06-29
- **Deciders:** Operator (chose "Build covering-designs B1").
- **Siblings:** ADR 0042 (post-D0 program), ADR 0040 (CWC record-triviality carve-out — the dormant
  promulgation path if a real beat ever appears).
- **Touches the proof edge:** NO. `tests/test_invariants.py` byte-identical. This module never sets
  `kernel_verified` and never promulgates; it reports the kernel verdict + an automated oracle lookup.

## 1. Context
Gate B0 measured the producer wall to be **domain-specific**, and recommended **covering designs
C(v,k,t)** as the second finite-witness domain: best oracle (the La Jolla Covering Repository — a single
DOI-pinned table of record that ships witnesses), the largest small-witness headroom (5,460 cells
small-witness ∩ gap≥2), and the simplest sound verifier. A (v,k,t)-covering of size B is a witness that
**C(v,k,t) ≤ B** — the *upper-bound* mirror of CWC's lower bound (fewer blocks is better).

## 2. Decision
Build the covering-designs analog of the CWC audit assets, reusing the proven pattern:
- **`scripts/covering_verify.py`** — `verify_covering` (untrusted pre-check) + `render_covering_lean`
  (core Lean 4, no Mathlib).
- **`scripts/covering_table_oracle.py`** + **`scripts/data/covering_snapshot.json`** — the LJCR
  best-known mirror (9,482 cells, snapshot 2026-04-21); `is_improvement` = **strictly fewer blocks**.
- **`scripts/covering_check.py`** — the audit CLI (blocks → verify → render → kernel → oracle).
- **`scripts/amplify.py`** — extended to dispatch the `covering` domain into the same kernel-checked
  corpus (the corpus key is now domain-agnostic, keyed on `cell`).

## 3. Soundness — completeness by construction (the load-bearing property)
The Lean checker **generates every t-subset of {0..v-1} itself** (`combs t (List.range v)`) and checks
each is covered; the witness supplies *only the blocks*. A malicious witness therefore **cannot omit an
uncovered t-subset** to launder a false upper bound past the kernel — completeness is structural, not
trusted. Verified against the real **Lean 4.31 kernel**:
- valid STS(9) covering → `validCovering … = true` **kernel-accepted** (≈4 s);
- the same covering with one block removed (an uncovered pair) → **kernel-rejected** (False).

**Witness contract:** a finite explicit list of blocks (k-subsets of {0..v-1}); **no
generators/compression** — a cyclic/base-block construction must be *fully expanded* by the producer
before the kernel sees it (never trust "develop under the group"). **Oracle:** novelty = strictly fewer
blocks than the mirrored LJCR best-known integer — exact integer comparison, never an LLM (invariant 4).
**Scope:** the small-witness band (v, t with `C(v,t)` renderable; start t≤4, modest v) so `decide` stays
tractable in the kernel; the million-block heavy corner is out of scope.

## 4. What this is / is NOT
- It **is** the verification-amplification mode for a second domain: a stronger/human/research producer
  proposes a covering, the kernel re-checks it, the corpus records it with provenance. This is valuable
  for **Track A regardless of the producer swing**.
- It is **NOT** the production promulgation path. Audit-tier: never sets `kernel_verified`, never
  promulgates. The trust boundary (`LeanVerifier.discharge`; `TrustPolicy.validate_path`) is untouched.
- A record-**beating** covering (strictly fewer blocks than LJCR) is flagged "BEATS record" but is **not**
  auto-promulgated.

## 5. Sequencing — the Track-D gate stays in front of any spend
The verifier confirms the *structural* overlap (clean oracle + renderable witnesses at the beatable
band). It does **not** establish that *our* producer can reduce a current best-known. Before any billable
producer swing (Track D), a **CPU reproduction probe** must show a baseline search reproducing/approaching
several current LJCR best-knowns. RED → bank Track A; GREEN → the swing is a priced, operator-gated bet.

## 6. Status
- **BUILT** — verifier + oracle + CLI + amplify dispatch + tests; kernel-validated on STS(7)/STS(9).
- **Next (not in this ADR):** the CPU reproduction probe (gates Track D); optional Ramsey as B2.
