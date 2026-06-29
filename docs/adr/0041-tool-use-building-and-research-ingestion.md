# ADR 0041 — Trust boundary for tool use, tool building, and research ingestion

- **Status:** PROPOSED — **ready for operator sign-off.** The 7-model external-witness round is complete
  and reconciled (§10): it VALIDATED the trust architecture (no defect in E1–E7), and its surviving
  guidance is folded in (A1–A10). **No code is built from this ADR until the operator approves §5 + the
  §9 sign-off checklist.**
- **Date:** 2026-06-27
- **Deciders:** Operator (sign-off required before any DECIDER-admission or any change to `trust.py`)
- **Siblings:** ADR 0001 (charter & trust hierarchy), ADR 0013 (trust-edge provenance hardening),
  ADR 0037 (modular sound faithfulness backends). This ADR is a *re-instantiation* of 0001 §1 + 0037 §2,
  not a new principle.
- **Touches the proof edge:** NO. The existing seven invariants in `tests/test_invariants.py` stay
  byte-identical. New load-bearing guards must be **agent-unweakenable** (see §2.4 — open question for
  operator: extend the sealed suite vs. a new sealed file also covered by the PreToolUse hook).

---

## 1. Context & decision

### 1.1 The directive

The operator wants Leibniz to autonomously **discover, process, conjecture, and write** novel results,
seeded by (a) **ingested research** (e.g. an arXiv crawl) and (b) **its own capabilities, which it will
eventually build, assemble, test, and prove itself**. The near-term goal is to *lay the foundation for
how Leibniz USES tools*; the not-so-distant goal is for Leibniz to *build* them.

### 1.2 What already exists (the seed)

The FunSearch CWC pilot is one fully-worked instance of a general pattern:

```
untrusted PROPOSER  ->  isolated SANDBOX  ->  independent mechanical DECIDER
(LLM program)          (funsearch_sandbox)    (verify_cwc fitness, then Lean kernel via cwc_check.py + oracle)
```

Files: `scripts/funsearch_{sandbox,loop,llm_pilot}.py`, `scripts/cwc_check.py`,
`scripts/cwc_table_oracle.py`, `scripts/cwc_rosin_crosscheck.py`. The pilot returned 0 record-beats (a
bounded RED), but **the pipeline is sound and the trust boundary held.**

Two further pieces are already the generalization in embryo:

- **ADR 0037** abstracted the propose→check spine for the *faithfulness* gate into
  `SoundFaithfulnessBackend` (Protocol: `name`, `cost_rank`, `applies`, `check`) +
  `Certificate(kind, rechecked, data)` + a **gate-owned `CertificateRechecker` registry keyed by
  `certificate.kind`**. The load-bearing line in `leibniz/gates/faithfulness.py`: a backend PASS is
  accepted as `MECHANICAL` **only if** `recheckers.get(cert.kind)` exists **and** returns `True`; the
  backend's self-reported `rechecked` is *advisory*. With **no re-checker registered for a kind, a PASS
  of that kind cannot be accepted** — the dormant default is maximally safe.
- **Rosin 2026** (`cwc_rosin_crosscheck.py`) is one sound research ingestion: the paper's 24 claimed
  bounds were never trusted; they were cross-checked against the committed, ground-truth-validated
  Brouwer snapshot and used only as a **conservative novelty floor**
  (`effective_best_known = max(snapshot, rosin_floor)`), with `assert_post_rosin()` as a one-way guard.

### 1.3 The decision

Lift the ADR-0037 trio (`Tool`/`ToolResult`/`Certificate` + gate-owned `ToolRegistry` re-checker dict)
into a **domain-neutral `leibniz/tools/` package**, refactor `funsearch_sandbox.py` into a
contract-parameterized `SandboxedTool` that satisfies it, and add a **one-directional, authoring-time
research-seeding layer** (`leibniz/seeds.py`) that feeds only the existing proposer roles and the
conservative-floor seam. **No new trust principle is introduced.** The widening is solely of the word
*proposer*: an LLM, a USED tool, a BUILT tool, and an ingested paper are all the same category —
*untrusted producers of drafts* — and the only thing that ever DECIDES is a fixed, operator-owned,
kind-keyed mechanical re-checker (Lean kernel, Z3, the ground-truth-validated oracle).

If any part of this design *required* a genuinely new trust rule, that would be the signal the boundary
is being weakened. It does not. The proof edge stays sealed by the existing `producer == KERNEL_PRODUCER`
pin with **zero new code in `trust.py` for the proof edge**; the *only* `trust.py` change this ADR
mandates is a faithfulness-edge producer allowlist (§7, ATTACK 2), which strengthens — never relaxes —
the boundary.

**Framing as a decision criterion (A1; ratified 7/7 by the round-3 witness review, §10).** This ADR
builds the **trust boundary and the capability substrate**; it does **NOT** assert that tool-building
moves the producer wall — the measured binding constraint is the *producer* (mathematical taste /
representation), not infrastructure, and the FunSearch pilot was *already* autonomous tool-building that
beat zero records. Accordingly the validated near-term product is **verification amplification** of
human- and research-supplied targets; the *autonomous-discovery* phases (4–6) are gated on a measured
**producer-wall diagnostic (Gate D0, §4)**. Absent D0 evidence, do not justify Phases 4–6 as a discovery
unlock.

---

## 2. The trust model

### 2.1 The bright line

> **An untrusted tool, built tool, seed, or paper PROPOSES. A gate-owned, kind-keyed mechanical
> re-checker DECIDES.**

A tool/seed output is admissible to a deciding path **only** as a `ToolResult` whose PASS carries a
`Certificate` of a **registered** kind that an **independent operator-owned re-checker re-derives True
from the certificate's raw `data`**. Self-reported success is advisory and is downgraded to DEFER.
Heuristic / search tools have no certificate kind and may therefore only ever return **FAIL or DEFER** —
never PASS.

### 2.2 The two trust states (the USE-vs-DECIDE gate)

This is the single staging axis. It is *identical to* the existing faithfulness accept/fall-through
logic — not a parallel mechanism.

**State 1 — REGISTERED-RUNNABLE (any built/ingested tool reaches this autonomously).**
The tool is in `ToolRegistry.tools`. Its output is UNTRUSTED DATA re-checked by a **pre-existing** fixed
decider (Lean kernel via `LeanVerifier.discharge`, Z3, the ground-truth-validated oracle). It may
search, construct, propose freely and **grows the TCB by zero**. A PASS of an *unregistered* kind is
structurally inert — `ToolRegistry.run()` has no re-checker entry, so it degrades to DEFER. **This single
fact covers the entire near-term goal**: FunSearch-style construction tools and arXiv-seeded search need
nothing more.

**State 2 — DECIDER-ADMITTED (a tool's own verdict is relied upon).**
Reachable **only** when an operator registers a kind→(statement template, re-checker, strength tag)
entry. Registration is an **operator act**, gated by ALL of:
(a) **exact-or-DEFER**, proven by the tool's own guard test (PASS-implies-certificate;
DEFER-never-becomes-PASS);
(b) the certificate's re-checker is an **independent, SMALLER, separately-reviewed, HUMAN-provenance**
checker — ideally only the small re-checker enters the TCB while the built engine stays a proposer (the
de Bruijn / LCF criterion; the ADR-0037 §8 SOS finding where the float SDP solver stays off-TCB and
`ring` re-checks). **A6 (round-3):** if the re-checker is *more than a thin wrapper* over the kernel or an
existing decision procedure (i.e. it embodies new deciding logic), the **PREFERRED** admission is a
**kernel-checked soundness statement** for the re-checker (Lean-implemented or proof-reconstructed), not
merely a strength tag + adversarial review; passing tests / being audited is **insufficient** for a
non-thin re-checker (`spec_author != proof_author`). Thin re-checkers keep the lighter (a)–(d) route;
(c) an **honest re-check-STRENGTH tag** bound to the kind (kernel-grade re-derivation vs
structural-property check vs engine-in-faithfulness-TCB), enforced at `validate_path`, not documentary;
(d) an **adversarial soundness review** that reproduces a kind-collision / weaker-statement laundering
input and asserts rejection (ADR-0037 §7 caught a string-compare-as-kernel-pin and a command-injection
laundering path across three rounds — that diligence is mandatory, not optional).

### 2.3 How TCB-growth-by-fiat is structurally blocked

Three barriers, two structural and one procedural:

1. **Kind-keyed re-checker registry.** A PASS of a kind with no registered re-checker is uninterpretable
   → DEFER. An agent can build and register a *tool*, but cannot reach into the re-checker dict, so its
   output is inert until an operator registers a kernel- or decision-procedure-backed re-checker.
2. **Operator-owned, dormant-empty registry — enforced in code, not convention.** The adversarial review
   (ATTACK 2) found that `field(default_factory=dict)` makes dormancy a *convention*. This ADR therefore
   mandates: (i) a **PreToolUse hard-block hook** committed in `.claude/` covering any write to a
   `recheckers` dict, any construction of `ToolRegistry`/`FaithfulnessGate` with a non-empty
   `recheckers`, and any mutation of the statement-template registry; (ii) an executable test that the
   default registry is empty AND that no module under `leibniz/` or `scripts/` imports a symbol that
   mutates it. The dormant default covers **both** the re-checker dict and the statement-template dict.
3. **The proof-edge TCB is sealed and untouched.** `kernel_verified` stays written only in
   `LeanVerifier.discharge`; `trust.py` rejects any `PROOF_EDGE` whose `producer != KERNEL_PRODUCER`. No
   tool — used or built — can ever be `KERNEL_PRODUCER`. This needs **zero new code** and keeps
   `tests/test_invariants.py` byte-identical.

### 2.4 Invariant extensions (consistent with the existing 7; each a re-instantiation)

These are stated as extensions, **not** edits to the seven. The seven are restated in `CLAUDE.md` and
enforced byte-identical by `tests/test_invariants.py`.

- **E1 — Tool PASS needs a re-checked certificate of a REGISTERED kind** (generalizes inv 1 / ADR 0037
  §2). A `ToolResult.PASS` with no registered re-checker for `certificate.kind`, or whose re-check
  returns False, is DEFER. *Blocks F1 (unverified tool becomes decider).*
- **E2 — The trusted-checker registry is closed under operator registration only** (generalizes inv 2).
  Default empty; no autonomous agent code path may add to it; enforced by the PreToolUse hook + a test.
  *Blocks F2 (silent TCB growth).*
- **E3 — No tool is ever `KERNEL_PRODUCER`; no tool touches the proof edge** (restates inv 1 & 7). A
  built tool may at most sit on the PROVER seam proposing a proof *term* the Lean kernel re-checks
  (against a fixed operator goal — §7 ATTACK 1), earn a FAITHFULNESS edge, or KILL on a refutation.
  *Blocks F3 (existential failure).*
- **E4 — Research is directional: it may tighten / seed / suggest, never loosen / decide** (generalizes
  inv 4 + the Rosin one-way guard). A floor may only RAISE the bar via `max()`. A *lowering* from
  ingested data is ignored unless mechanically re-derived. A *raising above the validated snapshot* is
  **quarantined unless mechanically re-derived** (ATTACK 1's floor-raising-abuse guard: `assert_post_rosin`
  must guard snapshot-vs-seed in BOTH directions). *Blocks F5.*
- **E5 — Untrusted tool code executes ONLY inside the sandbox isolation boundary; the host never execs
  it in-process** (restates a precondition as invariant). The real backstops are the host wall-clock
  deadline + bounded stdout read + force-reap + no `-v` mount + sha256-digest-pinned image; the
  in-container SIGALRM is best-effort only. **A7 (round-3, build-surface ban):** the proposer supplies the
  tool BODY and witness DATA only — it MUST NOT generate build scripts, compiler/linker flags,
  container/manifest entries, or dependency specs (all operator-owned). Builds use pinned deps,
  reproducible images, no dynamic/network downloads, a credential-free workspace, and record an SBOM.
  Re-checking the *output* does not cover a compiler/build side-channel. *Blocks F6 (sandbox escape /
  supply-chain).*
- **E6 — Certificate-kind honesty: claimed re-check strength must match the re-checker's actual
  strength** (new explicit guard for the generalization). Kernel-grade re-derivation, structural-property
  check, and engine-in-faithfulness-TCB are tagged distinctly and never conflated; the re-checker must
  **re-derive from `certificate.data`, never trust `certificate.kind` or `certificate.rechecked`**.
  *Blocks F7 (certificate-kind laundering).*
- **E6′ — Axiom/`sorry`/native-mechanism closure audit + the Lean compiler is attack surface** (A8,
  round-3 — Gemini's strongest point + Qwen). A trusted re-check must REJECT any proof term containing
  `sorry`, a new `axiom`, or unapproved imports, and verify the **absence** of axioms against an explicit
  allowlist (presence of `Q.E.D.` is not enough). `native_decide`, `unsafeCast`, `@[extern]`,
  `@[implemented_by]`, and unsafe/native execution are **banned in trusted re-check paths** (they route to
  host code). The Lean elaboration/compilation step itself runs **inside the same sandbox isolation** as
  candidate code — the compiler is part of the attack surface, not trusted infrastructure. *Hardens F3/F7.*
- **E8 — Held-out evaluation integrity** (A3, round-3 — named by 6/7 as the top measurement-integrity
  failure). Any tool whose *utility* gates a phase transition is evaluated ONLY on a **held-out,
  pre-registered, cryptographically-committed-before-the-tool-is-built** instance set drawn from
  independent config the agent cannot read or modify. **Tool-generated test suites are admission filters,
  never promotion evidence.** *Blocks eval-on-self.*
- **E7 — Statement-template ownership** (new; the keystone the adversarial review demanded — §7 ATTACK
  1). For every result kind, the theorem-statement generator (the generalized `render_*_lean`) is
  **operator-owned, fixed, and proposer-inaccessible**. An untrusted tool/seed supplies ONLY the witness
  DATA fed into that fixed template — never the theorem text, the `result_decoder` logic, or any part of
  the proposition the kernel decides. A kind binds to **both** a fixed statement template AND a
  re-checker; the registry rejects a certificate whose statement was not produced by the operator-owned
  template, and `validate_path` re-derives the parameter tuple from `certificate.data` and asserts the
  rendered statement is byte-identical to `template(params)` for the claimed Enuntiatio. *Blocks F8
  (statement-template capture — an honestly-passing re-check of a tool-chosen weaker statement).*

**Open question for operator sign-off (§2.4 / checklist item 2):** the existing seven invariant tests
stay byte-identical. The adversarial review argues the NEW load-bearing guards (faithfulness-producer
allowlist; tool ≠ `KERNEL_PRODUCER`; recheckers empty-by-default; unregistered/laundered kind → DEFER)
must be **agent-unweakenable**. Two options: (A) append them to `tests/test_invariants.py` (breaks the
byte-identical convention but keeps one sealed file); (B) put them in a new `tests/test_tool_trust.py`
that the PreToolUse hook *also* protects from agent edits (keeps `test_invariants.py` byte-identical).
**Recommended: (B)** — it preserves the standing byte-identical rule and the hook gives the same
"agent-cannot-weaken" property. Operator chooses.

---

## 3. Architecture

### 3.1 The `leibniz/tools/` package (the seam)

A structural copy of `leibniz/gates/sound_backends.py` + the faithfulness dispatch loop, generalized off
the word "faithfulness."

- **`leibniz/tools/protocol.py`**
  - `ToolDescriptor` (frozen): `name`, `provenance: Provenance` (HUMAN | INGESTED_DERIVED | SELF_BUILT),
    `cost_rank: int` (cheapest-first, inv 5), `arg_schema: dict`, `result_kind: str`,
    `requires_sandbox: bool`.
  - `Tool` (runtime_checkable Protocol): `descriptor`, `applies(ctx) -> bool`, `run(ctx) -> ToolResult`.
    Byte-for-byte the shape of `SoundFaithfulnessBackend`, renamed `check`→`run`, `Propositio`→neutral
    `ctx`. EXACT-OR-DEFER.
  - `ToolResult`: `verdict (PASS|FAIL|DEFER)`, `producer: str`, `certificate: Optional[Certificate]`,
    `detail`. `is_pass_with_certificate()` identical to `FaithfulnessVerdict`.
  - **`Certificate` and `CertificateRechecker` are RE-EXPORTED from `sound_backends.py`, not redefined**
    (single source of truth; faithfulness keeps importing the same symbols — zero churn, no drift).
- **`leibniz/tools/registry.py`** — `ToolRegistry`, extracted from the faithfulness dispatch loop:
  - holds `tools: tuple[Tool, ...]` + `recheckers: dict[str, CertificateRechecker]` + `templates:
    dict[str, StatementTemplate]` (E7), all **dormant-empty by default**.
  - `run(ctx) -> ToolEvidence`: sort applicable tools by `cost_rank`; FAIL short-circuits to a mechanical
    refutation; a PASS-with-certificate is accepted as `MECHANICAL` **iff** the re-checker for
    `cert.kind` is registered AND returns True AND (E7) the certificate's statement matches
    `templates[kind](params)`; otherwise fall through (PASS-no-recheck → DEFER).
  - `register_tool` / `register_rechecker` are the operator opt-in seam, hard-blocked from agent paths.
- **`leibniz/tools/sandbox.py`** — the generalized `funsearch_sandbox.py`:
  - `SandboxContract(fn_name, arg_schema, result_decoder)` replaces the hardcoded `construct(n,d,w)`
    coupling. **`_docker_argv` (pure lock-down argv), `run_program` (host wall-clock deadline + bounded
    read + force-reap, never-raises), `_parse_output` (last-sentinel-wins), the stdin-as-DATA pattern,
    and the digest-pinned image move over BYTE-IDENTICAL** — they are already contract-agnostic and they
    are the E5/E6 enforcement; only the harness template string and the contract decoder are new code.
  - `SandboxedTool(Tool)`: `run()` invokes `run_program` for its contract, then hands UNTRUSTED stdout to
    a pluggable oracle to build a `Certificate`. CWC becomes the first registered instance.
- **`leibniz/tools/evidence.py`** — `ToolEvidence`, a sibling of `EdgeEvidence` carrying `producer`,
  `tier`, `certificate_kind`, `rechecked_by_registry`. It **never** sets `PROOF_EDGE` and **never** names
  `KERNEL_PRODUCER`. **A9 (round-3):** also records a reproducibility envelope — `tool_version_hash`,
  `image_digest`, `input_artifact_hashes`, `capabilities`, `sandbox_profile`, `resource_usage`,
  `nondeterminism_seed`, `environment_hash` — so promotions are replayable (A4).
- **`leibniz/tools/ledger.py`** (A4, round-3 — Fugu/Fugu-Ultra "text logs are not receipts") — an
  **append-only, replayable** record: every proposal, sandbox execution, certificate, re-checker
  decision, registration, promotion, and quarantine appends an immutable entry. A promotion MUST be
  **replayable from the ledger + pinned artifacts** (image digest, input hashes, seed, env hash) and
  requires a matching **re-check receipt carrying the exact decided-statement hash** (not a text log).
  Strengthens ATTACK-1 forensics.

### 3.2 The research-seeding pipeline (`leibniz/seeds.py`)

A one-directional, authoring-time layer. A seed only ever moves *rightward* into a PROPOSER slot;
nothing it carries reaches a decider except by independent mechanical re-derivation.

- **Stage 0 — CRAWL (authoring-time, fetch-only, OFF the runtime decision path).**
  `mcp__academic__arxiv_search` to discover; firecrawl / `WebFetch` to pull HTML + ar5iv. Output: raw
  text + a frozen provenance record `{arxiv_id, version, url, fetched_at, extraction_method,
  license_note}`. No provenance → no seed. License discipline: *restate in our own Lean, never
  redistribute prose*.
- **Stage 1 — EXTRACT to a typed, UNTRUSTED `Seed`** `{kind: floor|target|construction, payload,
  provenance, extraction_agreement: int, status}`. Born `status=UNTRUSTED`.
- **Stage 2 — VALIDATE (`validate_seed()`).** Three one-directional guards: (i) `extraction_agreement
  >= 2` independent extractions agree exactly, else quarantine; (ii) cross-check numeric seeds against
  the ground-truth-validated snapshot — refuse any *lowering*, quarantine any *raising above the
  snapshot* unless mechanically re-derived (E4); (iii) emit a committed one-way CI assertion (generalized
  `assert_post_rosin`). A **proof-of-use trace** linking the seed to the consumed source span is
  required (blocks fabricated grounding).
- **Stage 3 — ENTER THE DISCOVERY LOOP as a proposer.** FLOOR → raises `effective_best_known =
  max(snapshot, seed_floor)`. TARGET → a pre-registered cell list / `Enuntiatio` at proposal-only roles,
  routed through the **unchanged** faithfulness → novelty → proof chain. CONSTRUCTION → an untrusted
  program for `SandboxedTool`, re-validated, any beat re-decided by the Lean kernel.
- **Stage 4 — WRITE / quarantine.** Promulgation only via `TrustPolicy.validate_path` (inv 2). Rejected
  seeds are quarantined with a `FinishReason` (inv 6), removed from retrieval/composition so they cannot
  re-enter a feedback loop, never deleted. **A10 (round-3):** when an ingested claim and a mechanical
  re-check **disagree**, store the seed as **`CONFLICT`** (retained, surfaced, removed from the floor
  computation) — distinct from silent quarantine, so a paper-vs-checker contradiction is preserved for
  review.

### 3.3 The build → assemble → test → prove → register lifecycle (with its trust gate)

| Stage | What happens | Trust state |
|---|---|---|
| **PROPOSE** | `ProviderAdapter.propose(role, ctx) -> str` drafts tool source; or an arXiv CONSTRUCTION seed enters. Just text. | untrusted |
| **BUILD / ASSEMBLE** | LLM writes/composes it. Still just text. | untrusted |
| **TEST** | Runs **only** inside `SandboxedTool` against property/spec tests. Output is UNTRUSTED DATA; fitness re-validated by a **separate** checker (never the search-fitness fn — preserve the `verify_cwc` vs `cwc_check.py` split as an *enforced invariant*). | State 1 |
| **PROVE** (optional) | The tool emits a certificate. If its kind has a kernel-backed re-checker bound to an operator-owned statement template, this is the *path* to State 2 — but PROVE happening does **not** auto-admit. | State 1 |
| **REGISTER** | Adds the tool to `tools` (State 1) — always, autonomously, TCB+0. Adds a re-checker + template to the operator-owned registry (State 2) — **only on operator act**, gated by §2.2 (a)–(d). | State 1 always; State 2 only on operator opt-in |
| **MONITOR** (A5, round-3; continuous, for any State 2-admitted kind) | Periodic replay against held-out cases, dependency/version-drift detection, axiom-closure re-audit (E6′). On any mismatch the kind is **AUTO-DEMOTED to State 1** (outputs revert to re-checked-only) and quarantined pending operator review. Auto-demote DOWN is safe and needs no operator; re-admission UP stays operator-gated. | demotion autonomous; re-admission operator-only |

---

## 4. Phased roadmap (each phase behind a measure-before-build gate)

| Phase | Build | Gate to enter the NEXT phase | Status |
|---|---|---|---|
| **1 — The seam, proven in isolation** | `leibniz/tools/protocol.py` + `registry.py` (pure types + dispatch, re-exporting `Certificate`/`CertificateRechecker`); the load-bearing guards in the sealed `tests/test_tool_trust.py` (option B, under the hook); the faithfulness-producer allowlist in `trust.py` (ATTACK 2); the PreToolUse hook extended to the new files. **No Docker, no LLM, no sandbox.** | All guards green: empty registry → every PASS is DEFER; unregistered kind → DEFER; re-checker False → DEFER; str-subclass statement cannot launder (E7); DEFER never silently → PASS; a faithfulness edge with a non-allowlisted producer is rejected. | **✅ BUILT (operator-signed-off 2026-06-27; 17 sealed guards; full suite 716 green; `test_invariants.py` byte-identical)** |
| **2 — Unify the existing FunSearch instance** | `leibniz/tools/sandbox.py` (`SandboxedTool` + `SandboxTask`, docker runner INJECTED so the isolation code stays single-sourced in `scripts/funsearch_sandbox.py`); `scripts/cwc_tool.py` (CWC wired as the first SandboxedTool — State 1; the re-checker + template are provided for Phase 6, NOT registered). **No behavior change, no spend.** | CWC runs through `ToolRegistry.run` and matches `evaluate_program` (docker-gated test); with no decider, a candidate beat is DEFER (State 1); E7 template recomputes the statement from witness data. | **✅ BUILT (2026-06-27; 10 tests incl. docker-gated end-to-end; State 1 only — no decider admitted)** |
| **3 — Sound research-seeding (FLOOR only)** | `leibniz/seeds.py` (Seed + validate_seed: proof-of-use, ≥2 agreeing extractions for FLOOR, bidirectional snapshot cross-check, CONFLICT on failed re-derivation; `effective_floor` one-directional; `seed_from_feed_record` maps the scraper's `leibniz.json`); `scripts/cwc_rosin_crosscheck.py::rosin_bound_seed()` as the first `BoundSeed`. Scraper augmented with a Leibniz-only `--leibniz-topic` tactical pull (Stage 0). Sealed `tests/test_seed_trust.py` under the hook. | A dominated value is admitted but never lowers the floor; an un-re-derived raise above snapshot QUARANTINES; out-of-table → None (never fabricated); <2 extractions / missing proof-of-use quarantine; the seeds module imports no network client; the Rosin BoundSeed validates with the floor UNCHANGED. | **✅ BUILT (2026-06-27; 13 sealed guards; State-1 proposers only — seeds never decide)** |
| **4 — TARGET & CONSTRUCTION seeds** | `leibniz/seed_intake.py`: validated seeds → PROPOSER seams only — TARGET → `seed_steering` (proposal-side context, gates nothing, à la ADR 0034); CONSTRUCTION → a `SandboxTask` for the `SandboxedTool` (runs only sandboxed); FLOOR → `effective_floor`. Quarantined/un-validated → NOTHING. Sealed `tests/test_seed_intake.py`. | A CONSTRUCTION seed becomes a sandbox job (never in-process); only VALIDATED TARGETs steer; no seed reaches a decider; the faithfulness→novelty→proof chain + trust policy unchanged. | **✅ BUILT (2026-06-27; the seam/adapter; 5 sealed guards; State-1 proposers only). Live organic seeded-conjecture run pending re-calibration.** |
| **5 — Propose/repair-a-tool loop** | Promote `funsearch_llm_pilot.py::LLMProposer` to a first-class `leibniz/providers/` provider; reuse the single-source prompt builders. | Measured discovery yield justifies the loop. | DEFERRED |
| **6 — First DECIDER-ADMITTED tool (operator-gated)** | Operator registers one kind→(template, re-checker, strength tag) after the full §2.2 (a)–(d) ritual. | Only on operator sign-off, per ADR; never autonomous. | DEFERRED — explicitly behind operator review |

**Gate D0 — producer-wall / expressivity diagnostic (A2, round-3; the single most-requested new
mechanism, operationalizing the 7/7 strategic dissent). Runs BEFORE Phases 4–6.** Manually encode the
best-known *human* construction for ≥3 open Brouwer cells and attempt Lean verification through the
existing checker:
- **RED** (the kernel verifies a construction the autonomous proposer never found) ⇒ the bottleneck is
  the **producer**, not tooling ⇒ **HALT autonomous tool-building (Phases 4–6)** and pivot to
  verification amplification of human/research-supplied targets.
- **GREEN** (the checker/encoding cannot even *express* the known construction) ⇒ a genuine
  **expressivity/representation gap** exists ⇒ tool-building *targeting representation* (e.g. a richer
  encoder/DSL) is justified.

This converts the strategic dissent ("is this the right bet?") from a faith claim into a falsifiable
precondition. Phases 1–3 (boundary hardening + FunSearch unification + sound FLOOR seeds) are correct
and cheap **regardless** of D0; only the autonomous-discovery phases wait on it.

The **measure-before-build** discipline: Phase 1's value is *proving the anti-TCB-growth property is real
before a single tool exists*. Phases 3–6 are each gated on the prior phase's guards being green AND on
evidence the capability is on the binding constraint (Gate D0 + held-out yield per E8).

---

## 5. The first buildable slice (precise enough to implement next — AFTER sign-off)

**Ship Phase 1: the seam, proven in isolation, with zero Docker / Lean / LLM dependency.**

1. **`leibniz/tools/protocol.py`** — `ToolDescriptor`, `Tool` (Protocol), `ToolResult`, `ToolEvidence`,
   **re-exporting** the already-shipped `Certificate` and `CertificateRechecker` from
   `leibniz/gates/sound_backends.py`.
2. **`leibniz/tools/registry.py`** — `ToolRegistry` with `tools`, `recheckers` (dormant-empty),
   `templates` (dormant-empty), and a one-screen `run()` generalizing `faithfulness.py`'s accept/
   fall-through loop.
3. **`trust.py`** — add a **faithfulness-edge producer allowlist** mirroring the
   `PROOF_EDGE`/`KERNEL_PRODUCER` pin: a `MECHANICAL FAITHFULNESS_EDGE` must carry a producer from an
   explicit operator-owned frozenset. Closes ATTACK 2. Legacy edges with `producer=None` pass unaffected
   (same technique ADR 0013 used to keep the invariants green).
4. **Guard tests** (agent-unweakenable per §2.4) against a fake tool: (a) `recheckers={}` → PASS→DEFER;
   (b) unregistered kind → DEFER; (c) re-checker False → DEFER; (d) re-checker True → MECHANICAL; (e) a
   laundering certificate (correct kind label, false `data`, or valid-for-weaker-statement) → re-checker
   False / registry REJECTS; (f) `ToolEvidence` can never be on `PROOF_EDGE` / as `KERNEL_PRODUCER`.
5. **`.claude/` PreToolUse hard-block hook** — blocks any agent-initiated mutation of
   `recheckers`/`templates` and any construction of `ToolRegistry`/`FaithfulnessGate` with non-empty
   registries.

This proves the USE-vs-DECIDE gate and the anti-TCB-growth property **before any tool is built or any
sandbox is generalized.** It runs in CI in milliseconds. `tests/test_invariants.py` stays byte-identical
for the existing seven.

---

## 6. Out of scope / deferred (and why)

- **Fully-autonomous self-trusting tool-building.** An agent may build, assemble, test, and register a
  tool as a PROPOSER (State 1) autonomously — the whole near-term win, TCB+0. It may **never**
  autonomously admit a tool to DECIDE (State 2). *Why:* reward hacking is not patchable under sustained
  optimization; a self-verifying agent inherits its own blind spots; a single verifier is a proxy for
  intent, never the intent. The de Bruijn criterion is the only sound answer: the proposer may be
  arbitrarily clever and untrusted because a tiny fixed checker re-decides.
- **A tool on the proof edge / any tool as `KERNEL_PRODUCER`.** Forbidden permanently. The strongest
  legal admission for a built tool is the PROVER seam, proposing a proof *term* against a **fixed
  operator-supplied goal** that the Lean kernel re-checks; the kernel stays the decider.
- **Research input deciding anything** (novelty, faithfulness, proof) or **lowering any bar.** Research
  is directional only (E4).
- **A general MCP-style agent tool bus.** `ToolContext`/`arg_schema` stay minimal — a discovery-loop
  capability seam, not a general agent framework. Anything needing a genuinely new trust rule is a red
  flag.
- **Live runtime fetching of seeds.** Crawl/scrape are authoring-time only; the runtime decision path
  depends solely on committed snapshot JSON + frozen provenance. Enforced by a test that the seeds
  module imports no network client.
- **Self-built / ingested code as a re-checker.** A re-checker runs in-process on the host and *is* TCB
  growth; it must be HUMAN-provenance, separately reviewed, proposer-immutable code (ATTACK 2).

---

## 7. Required guards from the adversarial review (each mapped to enforcement)

### ATTACK 1 — Statement-template capture (`prevented_by_design=false` in the raw design; fixed by E7)

A SELF_BUILT tool registers `result_kind="cwc-construction"` and authors *both* the statement and a
witness valid for a **weaker** theorem (permuted/over-counted codewords; shifted n′,d′,w′; or a proof
term of a vacuously-true proposition). The operator's kernel re-checker honestly runs `decide` and
returns True — it re-checked the *wrong claim*. The MECHANICAL PASS flows to `validate_path`, which
checks tier/producer/PASS but not that the decided statement equals the operator-intended Enuntiatio.

| Required guard | Enforced in |
|---|---|
| **Statement-template ownership** — the statement generator is operator-owned, fixed, proposer-inaccessible; a tool supplies ONLY witness DATA. A kind binds to BOTH a template AND a re-checker. | `tools/registry.py` (`templates` dict, dormant-empty); E7; PreToolUse hook covers the template registry. |
| **statement == Enuntiatio binding in `validate_path`** — re-derive params from `certificate.data`, assert rendered statement is byte-identical to `template(params)`; reject otherwise. | `trust.py::validate_path` extension; guard test reproduces valid-for-weaker-statement → REJECT. |
| **PROVE-stage goal ownership** — a proof term must discharge a FIXED operator-supplied goal, never a tool-emitted goal. | `tools/registry.py` PROVER-seam path; §6. |
| **result_kind is NOT a capability grant** — registering a kind whose re-checker exists does not admit DECIDE; admission needs operator (template, re-checker, strength tag) + adversarial review + PreToolUse hard block on both dicts. | §2.2, §2.3; PreToolUse hook. |
| **Provenance transitivity / no laundering-by-composition** — a result whose ANY input is SELF_BUILT/INGESTED cannot promulgate on a stronger tier than an independent full re-derivation; a tool composed from a quarantined tool inherits quarantine; search-fitness code is separate from the deciding re-checker. | `tools/evidence.py` provenance; quarantine-not-delete (inv 6); enforced verify_cwc-vs-cwc_check split. |
| **Floor-raising abuse guard** — a raise above the validated snapshot is quarantined unless mechanically re-derived; `assert_post_rosin` guards BOTH directions. | `seeds.py::validate_seed`; E4; `test_seed_trust.py`. |
| **Network-off-the-decision-path as an executable test.** | `test_seed_trust.py`; Phase 1/3 gate. |

### ATTACK 2 — Faithfulness-edge producer laundering (`prevented_by_design=false`; fixed)

The raw design fixated on the proof edge and a "dormant-by-default" dict that is *convention, not code*.
`validate_edge` pins only the PROOF edge to `KERNEL_PRODUCER`; a tool-earned MECHANICAL **faithfulness**
edge with an arbitrary producer is fully admissible.

| Required guard | Enforced in |
|---|---|
| **Faithfulness-producer allowlist in `validate_edge`** — a MECHANICAL `FAITHFULNESS_EDGE` must carry a producer from an explicit operator-owned frozenset, mirroring the `KERNEL_PRODUCER` pin. | `trust.py::validate_edge` (Phase 1, slice item 3); sealed test. |
| **Structural operator-ownership of `recheckers`** — register-from-agent-path impossible; PreToolUse hook + executable test that the default registry is empty AND no `leibniz/`/`scripts/` module imports a mutator. | `.claude/` hook; `test_tool_trust.py`. |
| **Load-bearing guards are agent-unweakenable** (§2.4 option B recommended). | sealed guard file under the hook. |
| **Re-checker must re-derive from `certificate.data`** — never trust `kind`/`rechecked`. Guard test feeds a laundering certificate and asserts False. | E6; `tools/registry.py`; `test_tool_trust.py`. |
| **Honest re-check-strength tag**, with `validate_path` refusing a faithfulness edge weaker than kernel-grade unless policy explicitly tolerates it (same discipline as the JUDGED faithfulness budget). | E6; `trust.py::validate_path`. |
| **Ban SELF_BUILT/INGESTED code from ever being a re-checker.** | §2.2(b), §6; PreToolUse hook + provenance check. |
| **Proof-of-use + ≥2 agreeing extractions as preconditions of `validate_seed`**; committed network-isolation test. | `seeds.py`; `test_seed_trust.py`. |

### Catastrophic failure modes → blocking invariant

| Mode | Blocked by |
|---|---|
| **F1** unverified tool becomes a decider | E1 |
| **F2** built tool expands TCB silently | E2 |
| **F3** LLM/tool sets `kernel_verified` | E3 + existing `KERNEL_PRODUCER` pin (zero new code; byte-identical) |
| **F4** tool/research bypasses `validate_path` | inv 2 + faithfulness-producer allowlist + audit-CLI-never-promulgates discipline |
| **F5** research decides novelty / lowers a bar | E4 (directional; `max()` floor only; bidirectional `assert_post_rosin`) |
| **F6** sandbox escape / supply-chain | E5 (digest-pinned image, host backstops, no `-v` mount, in-process exec forbidden) |
| **F7** certificate-kind laundering | E6 (re-derive from `data`; honest strength tag) |
| **F8** statement-template capture | E7 (operator-owned fixed template; statement==Enuntiatio binding) |

---

## 8. Risk register (honest)

- **Naming/abstraction drift** between `tools/` and `gates/`: mitigated by re-exporting
  `Certificate`/`CertificateRechecker` from a single source.
- **The generalized sandbox harness widens the attack surface of the most security-critical file**:
  mitigated by keeping program+contract strictly as stdin JSON DATA, keeping `_docker_argv` pure and
  unit-tested, and reproducing laundering inputs in review.
- **Operator-opt-in fatigue / permission carry-over** socially re-creates TCB-growth-by-fiat: mitigated
  by the PreToolUse hard block on every re-checker/template mutation — each admission is its own act.
- **Capability-acquisition feedback loop**: a tool that games its TEST-stage fitness gets composed into
  later tools: mitigated by the enforced search-fitness-vs-decider split and quarantine-not-delete.
- **Stale-floor confound** (a fabricated raising masks a genuine beat): mitigated by bidirectional
  snapshot cross-check + re-derivation requirement for any raise.
- **Shipping the package without this ADR + operator opt-in on the registry** *would itself be* the
  TCB-growth-by-fiat the design forbids: ADR 0041 sign-off is a gating slice.

---

## 9. Consequences

- **Positive:** one unified seam for tool-use, tool-building, and research-seeding; the FunSearch
  instance and the faithfulness backends collapse under one registry; the near-term directive (USE
  tools, SEED from arXiv) is fully served by State 1 with TCB+0; the path to tool-building is concrete
  and gated.
- **Negative / cost:** a `trust.py` change (faithfulness-producer allowlist) — justified because it
  *strengthens* the boundary; a new PreToolUse hook to maintain; the operator becomes the sole gate for
  DECIDER-admission (intentional).
- **Reversible?** The package and seeds layer are reversible (no DECIDER-admitted tool exists until
  Phase 6). The `trust.py` allowlist and the sealed guards are *ratchets* — they only ever tighten.

---

### Operator sign-off checklist (before any Phase 1 code merges)
1. Approve the **`trust.py` faithfulness-producer allowlist** (the only trust-core change).
2. Decide §2.4 **agent-unweakenable guard placement** (recommended: option B — a new sealed file under
   the PreToolUse hook; keeps `tests/test_invariants.py` byte-identical).
3. Approve the **`.claude/` PreToolUse hard-block hook** for `recheckers`/`templates` mutation.
4. Confirm `tests/test_invariants.py` byte-identical for the existing seven.
5. Confirm no DECIDER-admission (State 2) in Phases 1–5; Phase 6 returns for separate sign-off per kind.
6. Endorse **Gate D0** (the producer-wall diagnostic) as the precondition for Phases 4–6, and **E8**
   (held-out, pre-registered eval) as the gate-transition evidence standard.
7. Endorse **E6′/A8** (axiom-closure audit + sandboxing the Lean compilation step; ban
   `native_decide`/`@[extern]`/unsafe in trusted paths) and **A7** (privileged-build-artifact ban).

---

## 10. Round-3 external-witness reconciliation (applied)

**Verdict: the 7-model round VALIDATES this ADR's trust architecture** — no witness found a defect in
E1–E7 / State1–State2 / ATTACK 1–2. The unanimous "framing" correction (verification-amplification, not
the discovery unlock) was already the ADR's position; the witnesses ratify it and ask it be held harder
(now A1). Fugu's "one thing you're getting wrong = specification authority" lands **exactly** on E7, the
keystone. Witnesses: Fugu, Fugu Ultra, Deepseek v4 Pro, Kimi, GLM 5.2, Gemini 3.5 Thinking, Qwen 3.7
Max. Source: `docs/external-witness-brief-tool-foundation.md`; raw responses retained by the operator.

**ADOPTED (folded in above):** A1 framing-as-criterion (§1.3); **A2 Gate D0** producer-wall diagnostic
with RED-HALT branch (§4, §9.6); **A3 E8** held-out/pre-registered eval (§2.4); **A8 E6′** axiom-closure
+ compiler-sandboxing + ban native_decide/extern/unsafe (§2.4); **A4** append-only replayable ledger +
statement-hash receipts (§3.1) and **A5** lifecycle MONITOR + auto-demote-to-State1 on drift (§3.3);
**A6** kernel-checked-soundness as the preferred route for *non-thin* re-checkers (§2.2b); **A7**
privileged-build-artifact ban (§2.4 E5); **A9** reproducibility envelope (§3.1); **A10** CONFLICT status
for paper-vs-checker disagreement (§3.2).

**NOTED (not adopted into the trust ADR; routed to phase tickets / optimization-roadmap):** specific
numeric phase thresholds (≥2×, ≥10×, etc.) — adopt the *principle* (pre-registered numeric gates) via
A2/A3, leave the constants to each phase ticket; TaskCard as a first-class schema (a discovery-yield
structure, not a trust mechanism); restricting the self-mod *language* to a Lean/WASM DSL (rides on the
D0 outcome); heavy external infra (MCP gateway / Cedar / SPIFFE / microVMs) — adopt the *properties*
(default-deny, signed identity) if Phase 5 lands, not the vendor stack; breadth-quota scheduling (belongs
in the KFM/MAP-Elites archive). A formal **capability-token API** (Fugu) is noted: the *property* is
already achieved structurally (E2/E3 + single `kernel_verified` writer); adopt the vocabulary, defer the
mechanism.

**REJECTED (would weaken the boundary or contradict measured findings):** autonomous proof-driven
self-promotion (a tool promoting itself by emitting a proof of its own correctness) — violates §6 / the
de Bruijn rationale; promotion stays operator-only. Compiling/static-linking a built tool *into the
kernel binary* (Kimi) — a larger, more brittle TCB expansion than the de Bruijn small-re-checker split;
keep the registry-admitted small re-checker instead. Abandoning tool-building outright now
(Deepseek/Qwen strongest form) — that strategic bet is what Gate D0 settles empirically; pre-committing
to abandonment discards the cheap, boundary-positive Phase 1–2 work that is correct regardless.
Mandatory human review on *every* seed (GLM) — seeds are HINTS that never decide (E4); the automated
guards keep them off the decision path without a human bottleneck; human review stays where it is
load-bearing (State 2 admission).

*All round-3 edits are additive ratchets (they only tighten). The proof edge and the existing seven in
`tests/test_invariants.py` are untouched. The ADR is now ready for the §9 operator sign-off.*
