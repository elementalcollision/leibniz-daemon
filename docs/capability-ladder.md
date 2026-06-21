# Capability Ladder

The build order. Each rung is independently testable and leaves the daemon in a
working state. The principle: **stand up the trust boundary before the
intelligence.** A weak prover behind a sound gate produces few but trustworthy
laws; a strong prover behind a weak gate produces a polluted ledger. We build the
gate first.

---

### R0 — Scaffold (this repository)

The loop, the types, the gates, the trust policy, and a passing dry-run with
deterministic fakes. No real Lean/Z3/LLM yet.

- ✅ `Propositio` triad with active `proof_obligation`
- ✅ Six-stage pipeline; cheap-refutation-first ordering
- ✅ Three gates (faithfulness, novelty, verification) with tier tagging
- ✅ `TrustPolicy` enforced at promotion
- ✅ KFM over a MAP-Elites archive
- ✅ `demo.py` turns one cycle; every gate fires

**Exit test:** `python demo.py` shows one `Q.E.D.` and one of each quarantine
reason.

---

### R1 — Real kernel (the judge comes online)

Replace `FakeLean` with a Lean 4 + Mathlib toolchain behind `LeanBackend`, via
LeanDojo for proof-state access.

- `compile_statement` → real elaboration (syntactic validity for free)
- `check_proof` → real kernel verification; this is the only thing that may set
  `kernel_verified`
- `closed_by_decision_procedure` → the `aesop`/`simp`/`decide` triviality test
- `normalize_statement` → canonicalize via the elaborator so the novelty hash is
  structural, not textual

**Exit test:** a hand-written true theorem promulgates; a hand-written false one
is `UNPROVEN`; a tautology is `TRIVIAL`.

---

### R2 — Faithfulness hardening (close the residual)

The research-hard rung. Make the gaming-witness real and write the first
claim-type probes.

- Compile `falsifiable_claim` → a searchable Z3/Lean predicate; implement
  `_negate` for real
- `find_gaming_witness` over that predicate (the spine)
- Probes for `COMPLEXITY_BOUND` and `CORRECTNESS_OVER_DOMAIN` (the two most common
  in analysis of algorithms)
- Wire the JUDGED fallback (round-trip + independent judge) for `OPEN_FORM` only,
  with budget tracking

**Exit test:** a statement that is kernel-provable but unfaithful to its claim
(e.g. proves a vacuous specialization) is caught as `GAMED` or `UNFAITHFUL`,
*before* proof compute.

---

### R3 — Novelty corpus (stop rediscovering textbooks)

Stand up the known-results corpus as a real promotion gate.

- Index Mathlib + a curated analysis-of-algorithms set (CLRS-style bounds, named
  theorems) by `ClaimSignature`
- `contains_equivalent` / `nearest` over structural signatures, not embeddings of
  prose
- This fixes Newton's documented gap (internal, offline dedup only)

**Exit test:** a re-derivation of the Ω(n log n) comparison-sort bound is caught
as `KNOWN`.

---

### R4 — Proposal models (the variation operator)

Replace `FakeProvider` with real proposal-role models behind `ProviderAdapter`.

- CONJECTURE: an LLM as semantic variation operator over KFM-selected parents
- FORMALIZE: an autoformalizer (specialized formalizer model preferred over raw
  prompting) → Lean statement
- PROOF_DRAFT: a prover model (DeepSeek-Prover-V2 / Goedel-Prover-V2 / Leanstral
  class) drafting tactic scripts; subgoal decomposition encouraged
- All confined to proposal; the kernel still decides

**Exit test:** the daemon promulgates at least one true, novel, non-trivial
theorem end-to-end with no human in the loop on the critical path.

---

### R5 — Selection & open-endedness (sustained novelty)

Make KFM and the archive do real work so the search keeps finding new ground.

- Design the behavior descriptor (mathematical sub-area × proof technique ×
  statement complexity) so the archive's diversity axes are meaningful
- Curiosity-biased parent sampling toward sparse cells
- Recombination ("fuck") that genuinely combines parent features, not just mutates
- Stagnation/drift detection (borrowed from Chimera) to re-seed SURVEY when a
  region is exhausted

**Exit test:** over N cycles, archive coverage grows and promulgated theorems span
multiple sub-areas rather than clustering.

---

### R6 — The reading-room (*Calculemus*) + operator tier

Promotion ≠ publication. Stand up the public ledger and the operator-tier gate
that decides what leaves the building.

- Auto-render promulgated Propositiones (Enuntiatio / Expressio / Demonstratio,
  with the kernel certificate and the falsifiable claim) to the *Calculemus* site
- Operator-tier publish action (a separate mutation, per Newton ADR 0012); the
  daemon promulgates to the Codex, a human promotes Codex → public
- Provenance/colophon: what is held back and why

**Exit test:** a promulgated law appears in *Calculemus* with its proof open to
inspection, only after an explicit operator publish.

---

## The throughline

R0–R3 build and harden the **trust boundary** (kernel, faithfulness, novelty).
R4–R5 add the **intelligence** (proposal, selection) behind that boundary. R6
opens the **ledger**. Building in this order means the system is never capable of
producing a fast-flowing stream of unsound or unfaithful laws — the gate exists
before the firehose.
