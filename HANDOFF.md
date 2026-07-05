# Leibniz · *Calculemus* — Handoff & Porting Manual

**Audience:** Claude Code (and the operator directing it).
**State (updated 2026-06-26):** the rung climb **R1 → R6 is substantially complete**; the
project is now in the **post-R6 optimization phase** (discovery yield — see
`docs/optimization-roadmap.md`, the live work plan). **The sound-backend discovery arc is now
CONCLUDED with a measured finding** (`docs/discovery-ceiling-cross-backend-finding.md`): across two
independent sound backends (Walnut automatic-sequences, built + run live; SOS/Positivstellensatz,
probed), the *soundly-checkable **and** finitely-encodable region is the textbook region*. The binding
constraint is **novelty at the producer — a structural encoding gap** — not soundness, reach, or prover
power. The daemon is a **vindicated sound verification / non-Q.E.D. decision instrument** (0 unsound; no
LLM ever decided; `test_invariants.py` byte-identical), producing correct, diverse, **textbook**
mathematics. More sound backends will not help; the kernel bridge stays gated (task #54); the only
identified lever left is producer-side (a frontier-encoder), unauthorized/unstarted. The original
assembly note is kept in §12 for history. Capsule of what is real now (all behind the unchanged trust
boundary):
- **R1 — real kernel: DONE, but via Docker, NOT LeanDojo.** The `LeanBackend` is
  `backends/lean_cli.py` + `backends/lean_repl.py`, shelling out to a pinned Lean 4.31 +
  Mathlib container (`leibniz-lean:v4.31.0` / `leibniz-lean-repl:v4.31.0`), per ADR 0003/0011.
  `lean-dojo` in `pyproject` is vestigial — the §6 table below said "via LeanDojo"; that plan
  was superseded. `LeanVerifier.discharge` is still the sole `kernel_verified` writer.
- **R2 — faithfulness: DONE.** Z3 backend (`backends/smt_z3.py`) + the bounded, sound DSL
  (ADR 0021/0022, min/max added ADR 0030), gaming-witness search, claim probes, and the
  budget-bounded OPEN_FORM judged fallback.
- **R3 — novelty: live** (retrieval + decision procedure; KNOWN dispositions fire).
- **R4 — proposal models: DONE.** Anthropic CONJECTURE/FORMALIZE; a prover ensemble
  (DeepSeek-Prover-V2 / Goedel / OpenRouter / HF) under N+1 consensus; the Harmonic Aristotle
  agent (ADR 0028); the ADR 0029 agentic **repair loop + distinct-reasoner panel** with
  failover. Exit test (≥1 novel non-trivial theorem, no human on the path): the panel produces
  N+1-sound promulgations (measurement runs audited — each close re-discharged +
  non-triviality-checked); a first **organic** funnel promulgation is being validated.
- **R5 — selection: DONE.** KFM + MAP-Elites archive (`selection.py`: descriptor, curiosity,
  recombination).
- **R6 — reading-room (*Calculemus*) + operator publish gate:** present (promotion ≠
  publication; the daemon never auto-publishes).
- **Multi-kernel deciders (ADR 0048): report-only backends built + live-validated; promotion DEFERRED.**
  Real *report-only* Coq (`backends/coq_docker.py`, Rocq 9.0) and Isabelle (`backends/isabelle_docker.py`,
  Isabelle2025) backends. Both kernels genuinely gate (self-laundered `Admitted`/`sorry` and broken proofs
  rejected — `scripts/verify_multi_kernel.py`, GREEN). Live for **verification-amplification** (audit
  tier). **Promulgation is DEFERRED and operator-gated:** the `CoqVerifier`/`IsabelleVerifier` mirrors +
  `VerifierRegistry` + `Expressio.target_checker` that would *write* `kernel_verified` and *mint* a proof
  edge are **NOT landed** — prototyping them tripped the structural trust guards
  (`test_kernel_verified_writers.py` / `test_boundary_guards.py`), whose whitelist edits are **operator-
  only** (same class as the `KERNEL_PRODUCER`→`KERNEL_PRODUCERS` trust edit and task #54; ADR 0045 8/8
  precedent). All three structural guards + `test_invariants.py` stay byte-identical. See the ticket below.
Tracked at `github.com/elementalcollision/leibniz-daemon`, branch protection on `main`, a
PreToolUse trust-edge hook, and CI (see §4). **The live work plan is now
`docs/optimization-roadmap.md`, not §8** — §8's rung tickets are retained as the original
climb plan (with status notes).
**Goal (achieved through R6; ongoing in optimization):** climb R1 → R6 replacing marked seams
with real backends, **without ever weakening the trust boundary**.

> **Ticket — ADR 0048 promotion layer (operator-gated, DEFERRED).** The report-only backends already
> *amplify*; to let a Coq/Isabelle proof *promulgate*, the operator lands the promotion layer as a
> PreToolUse-guarded keystone: (1) add `CoqVerifier`/`IsabelleVerifier` (mirrors of `LeanVerifier`, each
> running its own kernel) + a `VerifierRegistry` routing by a new `Expressio.target_checker` (default
> `"lean"`, fail-closed) — these add `kernel_verified` write + `PROOF_EDGE` mint sites, so this step **also**
> edits the two structural trust guards (add `CoqVerifier::discharge`/`IsabelleVerifier::discharge` to
> `test_kernel_verified_writers.py::_WHITELIST` and `test_boundary_guards.py`), which are **themselves trust
> decisions**; (2) refactor `trust.py` `KERNEL_PRODUCER` (scalar) → `KERNEL_PRODUCERS` (frozenset) + alias,
> `validate_edge` → `not in KERNEL_PRODUCERS` (exact ADR 0041 `FAITHFULNESS_PRODUCERS` shape — does **not**
> touch `test_invariants.py`), and add the producer string **one act per kernel** after a per-kernel witness
> round (ADR 0045: the analogous Lean edit was deferred 8/8); (3) wire the live pipeline/consensus/
> proof_repair discharge calls through the registry, and pin images by immutable `sha256`. Recommend
> `target_checker` stays `"lean"` until a proposer opts in. Exit test: a Coq **and** an Isabelle N+1-sound
> promulgation, all four structural guards still byte-identical. A working prototype of layer (1) exists in
> this session's history if needed as a reference. Until then the amplification backends stand alone.

This document is the porting manual and work plan. It deliberately lives *outside*
`CLAUDE.md` (memory files should not carry execution plans). Read `CLAUDE.md` first
for the always-on rules, then this for what to build.

---

## 0. Read order

1. `CLAUDE.md` — the always-on rules and commands (small, imperative).
2. `README.md` — the mission and the one idea.
3. `docs/adr/0001-charter-and-trust-hierarchy.md` — why the trust tiers exist.
4. `docs/adr/0002-faithfulness-gate.md` — the crux design.
5. `docs/architecture.md` — the organ map and per-cycle data flow.
6. This file, §6 (work plan) — pick a rung.

Then: run `python demo.py` and `pytest -q` to see green before changing anything.

---

## 1. Mission, compressed

Leibniz discovers **novel, tractable, kernel-proven** theorems. It is the sibling
of `newton-daemon`: where Newton *demonstrates* (runs a mutation-hardened
acceptance test in a sandbox and stamps a literal `"Q.E.D."` string), Leibniz
*calculates* (discharges a formal proof obligation against the Lean kernel). The
flip happens at one seam Newton pre-wired and left dormant: `proof_obligation`.

The single existential risk is a **kernel-valid proof of a mis-stated theorem** —
authoritative exactly when it is most wrong, and permanent once in a public
ledger. The architecture exists to defuse that. See §3.

---

## 2. How the extant code maps in

| Extant system | Role here | Attaches at | Status |
|---|---|---|---|
| **Chimera** | runtime / body: scheduler, SQLite memory, witness, drift | `adapters.py::RuntimeAdapter` | seam |
| **Newton** | loop + ledger / spine: six stages, Propositio triad | `pipeline.py`, `propositio.py` | ported (shape kept; Demonstratio backend flipped) |
| **KFM** | selection: kill / recombine / commit over a QD archive | `selection.py` | scaffolded |
| **Leonardo** | survey + analogy / eyes — **TENTATIVE, confirm identity** | `adapters.py::LeonardoAdapter` | seam, flagged |
| **NEW** | verification / the judge: Lean kernel + Z3 | `verifiers.py` | seam |

**Leonardo is the one open assumption.** The role assigned (frontier survey +
cross-domain analogy) is inferred from the name, not from its code. Confirm what
Leonardo actually is and rewire `LeonardoAdapter`; it is isolated so that is a
one-file change. Do not assume the role is correct just because the scaffold names
it that way.

---

## 3. The trust hierarchy (the spine)

Every decision edge carries a `TrustTier`. A candidate may be promulgated only if
every edge on its path is `MECHANICAL`, with one permitted exception.

| Edge | Decider | Tier | Code |
|---|---|---|---|
| proof ↔ statement | Lean kernel | **MECHANICAL** (never an LLM) | `verifiers.py::LeanVerifier.discharge` |
| novelty / non-triviality | retrieval + decision procedure | **MECHANICAL** | `gates/novelty.py` |
| statement ↔ Enuntiatio | gaming-witness → claim-probe → judge | **ADVERSARIAL → MECHANICAL → JUDGED** | `gates/faithfulness.py` |

LLMs occupy only the proposal roles in `types.py::Role`. The only LLM judgment
that can reach a promulgated law is the OPEN_FORM faithfulness fallback, and it is
budget-bounded (`TrustPolicy.max_judged_faithfulness_fraction`).

---

## 4. Non-negotiable invariants & their enforcement stack

The invariants (full list in `CLAUDE.md` §"Trust invariants"). What matters for
porting is the **four-layer enforcement** — because a memory file is context, not
enforcement:

1. **`CLAUDE.md`** — keeps the rules in the agent's context (adherence, not a block).
2. **`leibniz/trust.py::TrustPolicy.validate_path`** — raises `TrustViolation` at
   promotion time. This is the runtime guard.
3. **`tests/test_invariants.py`** — 11 tests that fail CI if a change weakens the
   boundary. **Treat a change that requires editing this file as a red flag.**
4. **(IMPLEMENTED 2026-06-21)** a Claude Code **PreToolUse hook**
   (`.claude/hooks/guard-trust-files.py`, wired in `.claude/settings.json`) that
   prompts for operator sign-off on edits to `trust.py` / `verifiers.py` /
   `types.py` / the three gates / `test_invariants.py`; a **CI** job
   (`.github/workflows/ci.yml`) running `pytest -q` + a ≥11-collected guard +
   `ruff`; and **`CODEOWNERS` + branch protection** on `main` (CI required, code-owner
   review required, force-push/deletion blocked). This is the only layer that is a
   true block. Caveat: the hook matches Edit/Write/MultiEdit, not Bash — a
   `sed`/`ruff --fix`/shell rewrite of a guarded file is not intercepted; CODEOWNERS
   + CI cover the merge path.

---

## 5. Repository map (assets)

```
leibniz-daemon/
├── CLAUDE.md                  # always-on rules + commands (read first)
├── HANDOFF.md                 # this file: porting manual + work plan
├── README.md                  # mission + the one idea
├── pyproject.toml             # core = stdlib only; extras: verify / propose / dev
├── demo.py                    # runnable one-cycle dry run with deterministic fakes
├── docs/
│   ├── adr/0001-charter-and-trust-hierarchy.md
│   ├── adr/0002-faithfulness-gate.md
│   ├── capability-ladder.md   # R0–R6, prose form (this file has the tickets)
│   └── architecture.md        # organ map + per-cycle data flow diagram
├── tests/
│   └── test_invariants.py     # 11 trust-invariant tests (green)
└── leibniz/
    ├── __init__.py            # entrypoints: Leibniz, Propositio, TrustPolicy
    ├── types.py               # TrustTier, Role, ClaimType, Verdict, FinishReason, ClaimSignature, EdgeEvidence
    ├── trust.py               # TrustPolicy.validate_path — the runtime guard
    ├── propositio.py          # Enuntiatio / Expressio / Demonstratio (active proof_obligation)
    ├── pipeline.py            # 6 stages: Survey→Conjecture→Formalize→Derive→Demonstrate→Promulgate
    ├── daemon.py              # Leibniz.circadian_cycle — sequences the stages
    ├── selection.py           # KFM + Archive (MAP-Elites)
    ├── verifiers.py           # LeanVerifier (the judge) + SMTVerifier (cheap refuter / gaming-witness)
    ├── adapters.py            # RuntimeAdapter (Chimera) / ProviderAdapter / LeonardoAdapter
    └── gates/
        ├── faithfulness.py    # THE CRUX: gaming-witness → claim-probe → judge
        ├── novelty.py         # external dedup + non-triviality
        └── verification.py    # deterministic promotion verdict (pure fn of evidence)
```

---

## 6. The seams to implement (the tactical core)

Each seam is a `Protocol`; the scaffold runs against fakes (`demo.py`). Implement
these concrete classes behind the Protocols. Listed with the rung that needs them.

**Status (2026-06-23): R1/R2/R4/R5 seams DONE; R3 live. The R1 backend ships via Docker, NOT
LeanDojo (the "Real backend" cell below is the original plan).** Table kept for reference.

| Protocol | File | Methods to implement | Real backend | Rung |
|---|---|---|---|---|
| `LeanBackend` | `verifiers.py` (impl `backends/lean_cli.py`, `backends/lean_repl.py`) | `compile_statement`, `check_proof`, `closed_by_decision_procedure` | ✅ Lean 4.31 + Mathlib via **Docker** (superseded LeanDojo) | **R1** |
| `SMTBackend` | `verifiers.py` | `find_counterexample`, `find_gaming_witness` | Z3 (`z3-solver`) | **R2** |
| `ClaimProbe` table + `_negate` | `gates/faithfulness.py` | one probe per `ClaimType`; real `_negate` | Z3/Lean predicate compilation | **R2** |
| `FaithfulnessJudge` | `gates/faithfulness.py` | `round_trip_agrees` | bounded LLM (OPEN_FORM only) | **R2** |
| `KnownCorpus` | `gates/novelty.py` | `contains_equivalent`, `nearest` | Mathlib + CLRS index, keyed by `ClaimSignature` | **R3** |
| `ProviderAdapter` | `adapters.py` | `propose` | proposal models (formalizer + prover class) | **R4** |
| `RuntimeAdapter` | `adapters.py` | `now_phase`, `remember`, `recall_recent`, `witness` | Chimera | ongoing |
| `LeonardoAdapter` | `adapters.py` | `survey_frontier`, `cross_domain_analogies` | **confirm Leonardo first** | R4/R5 |

**Contract reminders that the tests and policy depend on:**
- `LeanVerifier.discharge` is the *only* writer of `Demonstratio.kernel_verified`.
  Keep it that way when you wire the real backend.
- `SMTVerifier` methods may only ever *kill* a candidate, never promote one. A
  passing SMT result means "survived refutation," not "proven."
- Every gate returns an `EdgeEvidence` with an honest `TrustTier`. The policy and
  tests read that tier; do not tag a JUDGED check as MECHANICAL to get it past the
  gate.

---

## 7. ADRs (decisions already made — do not relitigate in code)

Full text at the paths below. Condensed so the agent has them without a file open.

### ADR 0001 — Charter & Trust Hierarchy → `docs/adr/0001-charter-and-trust-hierarchy.md`
- LLMs propose; they never decide. Roles confined to `types.py::Role`.
- Three trust tiers: MECHANICAL (kernel/decision-procedure), ADVERSARIAL
  (falsification search), JUDGED (bounded LLM, one edge only).
- proof = MECHANICAL always; novelty = MECHANICAL; statement↔claim =
  ADVERSARIAL→MECHANICAL→JUDGED.
- Enforced at promotion by `TrustPolicy.validate_path`. Judged-faithfulness
  fraction is budget-bounded and tracked.
- Non-goals: empirical/symbolic-regression law discovery; trusting an LLM as a
  proof oracle under any framing.

### ADR 0002 — The Faithfulness Gate → `docs/adr/0002-faithfulness-gate.md`
- The kernel closes proof↔statement; nothing else closes statement↔Enuntiatio.
  That residual is the whole risk surface. A concordance-judge gate is theater.
- Strategy, strongest first: (1) **gaming-witness** (adversarial — find an object
  satisfying the statement while violating the claim → FAIL/GAMED); (2)
  **claim-type probe** (mechanical, dispatched by `ClaimType` — the router belongs
  *here*, on the gate, not as a prover backend); (3) **judge** (round-trip +
  independent review, OPEN_FORM only, logged).
- A measurable claim with no decisive probe returns DEFER, never PASS — we refuse
  to launder it through a judge.
- Runs inside FORMALIZE, before proof compute (cheap-refutation-first).
- Open: `_negate` (compiling `falsifiable_claim` into a searchable predicate) is a
  placeholder and is the primary R2 research task. Alternative retained:
  claim-from-verification (derive the Enuntiatio from what is provable).

When you make a new architectural decision, write ADR 0003+ rather than encoding a
reversible choice silently.

---

## 8. Work plan — rung tickets

> **STATUS (2026-06-23): R1–R6 are substantially built (see the State capsule at the top).**
> These tickets are the *original* climb plan, retained for context + exit tests. R1 shipped
> via **Docker, not LeanDojo**. The **live work plan is now `docs/optimization-roadmap.md`**
> (post-R6 discovery-yield optimization: faithfulness DSL, weaken-retry, decomposition, the
> lever-3 prover work — Aristotle + the ADR 0029 repair panel). Treat the per-rung text below
> as the spec each seam was built to, with the exit tests still valid as regressions.

Do them in order. Each leaves the daemon working. **Principle: the gate exists
before the firehose** — stand up and harden the trust boundary (R1–R3) before
adding proposal/selection intelligence (R4–R5).

### R1 — Real kernel (the judge comes online)
- **Goal:** replace `FakeLean` with Lean 4 + Mathlib behind `LeanBackend` via LeanDojo.
- **Files:** `verifiers.py` (new `LeanDojoBackend`), `pyproject.toml` (already lists
  `lean-dojo`), a thin Lean project for Mathlib, new `tests/test_lean_backend.py`.
- **Steps:** wire `compile_statement` → elaboration; `check_proof` → kernel
  verification (the only `kernel_verified` writer); `closed_by_decision_procedure`
  → `aesop`/`simp`/`decide`; `normalize_statement` → canonicalize via the
  elaborator so the novelty hash is structural.
- **Also:** add the PreToolUse hook + CI (`pytest -q`) from §4.
- **Exit test:** a hand-written true theorem promulgates; a false one is UNPROVEN;
  a tautology is TRIVIAL — and `tests/test_invariants.py` still green.

### R2 — Faithfulness hardening (close the residual) — research-hard
- **Goal:** make the gaming-witness real and write the first claim-type probes.
- **Files:** `gates/faithfulness.py` (`_negate`, probe table), `verifiers.py`
  (`Z3Backend.find_gaming_witness`), new `tests/test_faithfulness.py`.
- **Steps:** compile `falsifiable_claim` → a Z3/Lean predicate and implement
  `_negate`; implement `find_gaming_witness` over it; write probes for
  `COMPLEXITY_BOUND` and `CORRECTNESS_OVER_DOMAIN`; wire the JUDGED fallback for
  OPEN_FORM only, with budget tracking.
- **Exit test:** a statement that is kernel-provable but unfaithful to its claim
  (e.g. a vacuous specialization) is caught as GAMED/UNFAITHFUL **before** proof.

### R3 — Novelty corpus (stop rediscovering textbooks)
- **Goal:** real known-results corpus as a promotion gate.
- **Files:** `gates/novelty.py` (`CorpusBackend`), an index build script.
- **Steps:** index Mathlib + curated CLRS-style results by `ClaimSignature`;
  implement `contains_equivalent`/`nearest` over structural signatures (not prose
  embeddings).
- **Exit test:** a re-derivation of the Ω(n log n) comparison-sort bound → KNOWN.

### R4 — Proposal models (the variation operator)
- **Goal:** replace `FakeProvider` with real proposal-role models.
- **Files:** `adapters.py` (`ProviderAdapter` impl), maybe `pipeline.py` parsing.
- **Steps:** CONJECTURE = semantic variation over KFM-selected parents; FORMALIZE =
  autoformalizer → Lean statement; PROOF_DRAFT = prover-class model → tactic script
  with subgoal decomposition. All proposal-only; the kernel still decides.
- **Exit test:** the daemon promulgates ≥1 true, novel, non-trivial theorem
  end-to-end with no human on the critical path.

### R5 — Selection & open-endedness (sustained novelty)
- **Goal:** make KFM + the archive do real work.
- **Files:** `selection.py` (behavior descriptor, recombination, curiosity sampling).
- **Steps:** design the descriptor (sub-area × technique × statement complexity);
  curiosity-bias parents toward sparse cells; real recombination; stagnation/drift
  re-seeding of SURVEY (borrow Chimera's drift).
- **Exit test:** over N cycles, archive coverage grows and promulgated theorems
  span multiple sub-areas.

### R6 — The reading-room (*Calculemus*) + operator tier
- **Goal:** the public ledger and the publish gate. Promotion ≠ publication.
- **Steps:** auto-render promulgated Propositiones (triad + kernel certificate +
  falsifiable claim) to *Calculemus*; operator-tier publish action (separate
  mutation, per Newton ADR 0012); colophon of what is held back and why.
- **Exit test:** a law appears in *Calculemus* with its proof open, only after an
  explicit operator publish.

---

## 9. Environment & setup

```bash
# Python package (core is stdlib-only; extras pull the real backends)
pip install -e ".[verify,propose,dev]"

# Verify the scaffold before changing anything
python demo.py        # expect: 1 Q.E.D., one each of refuted/trivial/known/gamed
pytest -q             # expect: 11 passed
ruff check .
```

External system dependencies (install per their upstream docs; not pip-only):
- **Lean 4 + Mathlib** — install the toolchain via `elan`, build Mathlib with
  `lake`. Required for R1. The Python `lean-dojo` extra needs a built Lean project
  to trace proof states.
- **Z3** — the `z3-solver` extra is pip-installable; required for R2.
- **Proposal models** — set `ANTHROPIC_API_KEY` (or the relevant provider creds)
  for the `propose` extra; required for R4. Keep these in proposal roles only.

Tip for long Claude Code sessions: rules in `CLAUDE.md` survive `/compact` (they
are re-read from disk); the rung you are mid-way through does not, so commit
progress and keep the active ticket in the conversation or an issue tracker, not
in `CLAUDE.md`.

---

## 10. Conventions

- **Latin ledger vocabulary:** Enuntiatio (human claim) / Expressio (formal
  statement) / Demonstratio (proof obligation + proof). Persona = Leibniz; public
  reading-room = Calculemus. Mirrors `newton-daemon`'s Newton/Principia.
- **Tier-tag everything:** every decision returns an `EdgeEvidence` with an honest
  `TrustTier`. The policy and tests trust that tag.
- **Quarantine, never delete:** failed candidates keep a `FinishReason`.
- **ADR for decisions:** new architectural choices get ADR 0003+.
- **Stub → seam → real:** the fakes in `demo.py` define the contract each real
  backend must satisfy. Read the fake before writing the real one.

---

## 11. Open questions to resolve with the operator

1. **What is Leonardo, actually?** The survey/analogy role is an inference from the
   name. Confirm against its code before R4/R5; rewire `LeonardoAdapter`.
2. **`_negate` encoding (R2).** Turning a `falsifiable_claim` into a searchable
   predicate is the research crux of the whole system; it determines how strong the
   gaming-witness is. Expect to iterate.
3. **Behavior descriptor (R5).** The diversity axes are a design choice that shapes
   what "novel" means in practice.
4. **Known-results corpus (R3).** Source, scope, and licensing of the curated
   analysis-of-algorithms set beyond Mathlib.
5. **Domain reach.** Initial target is analysis of algorithms (what Mathlib + the
   probes support well). Expanding the domain expands the probe table.

---

## 12. First moves for Claude Code

R0 assembly **and** the enforcement stack (§4) are **done** (2026-06-21); the repo
is green and protected. What is actually next:

1. `pip install -e ".[dev]"`, then `pytest -q` (expect **11 passed**) and
   `python demo.py` (expect one `Q.E.D.` + one each of refuted/known/trivial/gamed).
   `main` is protected — branch off it; changes land via PR with CI green + a
   code-owner review.
2. Read ADR 0001 and 0002.
3. **Close the faithfulness hole before enabling real promulgation.** `_negate`
   (in `gates/faithfulness.py`) is a literal-string placeholder, so the adversarial
   gaming-witness passes *vacuously*. Do **not** let R1's real kernel promulgate
   against it: force the faithfulness edge to `DEFER` for measurable claims that
   have no real probe until R2 lands the real `_negate` + the
   vacuous-specialization regression test. (Worth an **ADR 0003** recording this
   sequencing rule.)
4. Take the **R1** ticket: implement `LeanDojoBackend` **in Docker** (Apple-Silicon
   interactive Dojo is unreliable; Python 3.11 venv — LeanDojo needs <3.12),
   keeping `discharge` the sole writer of `kernel_verified` (a cache *hit* must
   carry a kernel certificate, never a bare boolean), **and** wire
   `normalize_statement` to the elaborator so the novelty hash is structural — R3's
   "catch the Ω(n log n) re-derivation as KNOWN" exit test depends on it. Re-run
   `pytest -q` — the 11 invariant tests must stay green.
5. Enforce the `max_judged_faithfulness_fraction` budget at **R4** (when a real
   judge first goes live), not R6.
6. Leonardo is **deferred to R3**. Its real identity is a deployed autonomous agent
   (see `leonardo-do-study` / `leonardo-uat` and the GitHub repos), **not** the
   survey/analogy oracle the organ map assumes — confirm and rewire
   `LeonardoAdapter` then.
