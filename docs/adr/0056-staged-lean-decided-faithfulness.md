# ADR 0056 — Staged Lean-decided faithfulness: an audited renderer (bridge) + a native-Lean contract (target)

**Status:** **Track A: AMENDED, ready for a scoped first-increment re-review (2026-07-07). Track B:
DEFERRED to ADR 0057.** The ≥3-lens adversarial review returned **per-track** verdicts (both
`needs-amendment`, `safe_to_implement: false` as first written). Track A — the audited DSL→Lean renderer
— had two concrete, fixable unguarded false-EXACT-PASSes; the amendments below (chiefly **ℤ-with-explicit-box
instead of ℕ** and **routing the binding through the existing tool-registry E7 template pin**) close them,
and Track A is now a near-term bridge pending a scoped re-review. Track B — the native-Lean contract — is
**a direction, not yet a design**: it billed unbuilt TCB (an elaborated-term data model, an Expr-level
fragment checker, and a gate-owned unbounded→finite reduction owner) as a "lint," so it is **carved out to
ADR 0057** and not scoped for code here. The **fail-closed default holds** (no rechecker registered for the
kind ⇒ no PASS accepted, `faithfulness.py:129-130`) — nothing is at risk today. Per the ADR 0051 / 0054 /
0055 precedent, **no code ships on the faithfulness path until the amended Track A clears its scoped
re-review.** Supersedes the open "v2.2 vs native-Lean" question in **ADR 0055**; keeps everything ADR 0055's
two review rounds found sound (the reduction argument, the wrong-period-DEFERs guarantee, the fail-closed
default). Complements ADR 0002 (faithfulness gate), ADR 0037 (sound-backend seam), ADR 0050 (law provenance).

---

## Review outcome & amendments (2026-07-07) — supersede Track A points 2–3 and defer Track B

A five-lens adversarial review (renderer-conformance · binding-completeness · ℕ/ℤ-coherence ·
Track-B-fragment-escape · migration-interface), each verified **against the code**, returned per-track
`needs-amendment` / `safe_to_implement: false`. It re-confirmed the sound core (residue enumeration over
`Fin m`; wrong/under-approximated period → open goals → DEFER; `decide` cannot be forced false by an unsound
`Decidable` — `of_decide_eq_true` extracts a real proof and a smuggled `sorryAx`/`Lean.ofReduceBool` is
caught by `axiom_closure` transitivity; the fail-closed default protects the daemon today). It found two
Track-A criticals and showed Track B rests on unbuilt TCB.

### Confirmed criticals (Track A) and their fixes

- **`Nat.sub` monus false-EXACT-PASS.** The DSL admits real ℤ subtraction (`ast.Sub`, `smt_z3.py:160`) and
  unary minus (`ast.USub`, `:152-153`), and the search box constrains only **variables** to be non-negative
  (`:279-280`), not subexpressions. So Track A point 3's **ℕ-end-to-end** decision was unsound: rendering
  `a - b` over ℕ is truncated **monus**, a *different Boolean function* — e.g. `(a-b)%5==0` is DSL-false at
  `(a=0,b=1)` (`-1 % 5 = 4`) but ℕ-true (`0 % 5 = 0`), and `(a-b+1==0)` is DSL-SAT but ℕ-empty (vacuous
  pair). The kernel then decides a different predicate than the Enuntiatio denotes. **Amendment 1 (below)
  replaces ℕ with ℤ-with-explicit-box**, which is the *one conformant integer world* — it fixes subtraction
  (real ℤ sub) **and** the ∃-witness non-emptiness (guarded `∃ v:ℤ, 0≤v ∧ …`) simultaneously.
- **Identity target ≠ the kernel's decided goal.** The seam `CertificateRechecker = Callable[[Certificate],
  bool]` (`sound_backends.py:48`) returns a bare bool; the kernel elaborates the goal *inside* `cert.data`,
  and nothing forced the gate's re-rendered identity string to **be** that embedded goal — a backend could
  carry honest strings in `detail` while `cert.data` proves `∀ vars, True`. Re-render-from-`prop` alone
  (the v2.1/0056 amendment-2 mechanism) does not close it. **Amendment 2 routes the binding through the
  existing tool-registry E7 template pin** (`leibniz/tools/registry.py:106-129`): the certificate's claimed
  `statement` must equal `template(cert.data)` byte-for-byte, pinned to a builtin `str` and compared with
  `str.__ne__` (defeats str-subclass `__eq__` spoofs), with the re-checker (E6) independently re-deriving
  `True` from `cert.data`. That mechanism is already audited and already carries `provenance`.

### Track A amendments (these supersede Track A points 2–3 and add 7–9)

1. **ℤ-with-explicit-box, not ℕ (replaces point 3).** Render the pair as `∀ (v : ℤ), 0 ≤ v → …` and the
   positive-content witnesses as guarded `∃ (v : ℤ), 0 ≤ v ∧ …`. Subtraction/USub render to real `Int`
   ops; `/`,`%` by the DSL's always-positive divisor use `Int.fdiv`/`Int.emod` (which coincide with
   `Int.ediv`/`Int.fmod` for positive divisors — pin this in the suite; the previously-stated pairing was
   non-canonical). The non-negativity box is now *explicit in the proposition*, matching what every other
   gate assumes without a separate ℕ world.
2. **Bind via the tool-registry E7 template pin (replaces point 2).** Register the backend as a
   `ToolRegistry` decider with a pure/deterministic `template(cert.data)` that renders the canonical pair;
   acceptance requires E6 (independent re-derive `True`) **and** E7 (`str.__ne__(template(cert.data),
   cert.detail["statement"])` is False, builtin-`str`-pinned). The gate stops using the bare
   `Callable[[Certificate],bool]` path for this kind. This binds **the kernel's actual goal**, and the
   ∃-witnesses are bound the same way (each is its own registry-graded statement), closing the unbound
   side-channel for good.
3. **Conformance suite must cover subtraction, USub, and composition.** Add negative-adjacent cases for
   `-`/USub and compositional predicates (`min(a-b, c) % 3`) where a negative/again-clamped intermediate
   propagates through admitted ops — per-op tests do not catch compositional divergence. Enforce
   *structurally* that the renderer's admission set equals the conformance-pinned set (the renderer is a
   second parser of the same DSL; a construct without a pinned rendering must be un-admittable, not merely
   undocumented).
4. **Resolve `gcd`.** `gcd` has **no DSL referent** (`_conv`'s `Call` branch admits only `min`/`max`,
   `smt_z3.py:202-219`), so "conform to the DSL" is vacuous for it. **Drop `gcd(v,c)` from the first
   increment scope**; re-admit it only once the DSL itself gains a `gcd` op with Z3 semantics to conform
   against (backlog).
5. **Per-track certificate kind + provenance.** Fail-closed is per-**kind** (`recheckers.get(kind)`), so
   Track A uses a distinct kind from any future Track B, and registering Track A's re-checker must **not**
   make any other kind eligible. Route through `ToolRegistry` so `provenance` rides the evidence (the
   faithfulness `EdgeEvidence` has only `producer`, `types.py:106-117`), backing the ADR-0050
   renderer-touch metric and enabling targeted quarantine of a non-conformant op.
6. **`axiom_closure` at faithfulness time.** Confirm the shared `axiom_closure` (`export_calculemus.py:51-75`)
   runs inside the faithfulness re-check on a *named* pair theorem — today it runs only at ledger export.

**Track A first increment (scoped):** the ℤ-with-explicit-box renderer over the **modular-polynomial
fragment with real ℤ subtraction** (no `gcd` yet), binding via the E7 template pin, with a conformance
suite covering negative-argument and compositional cases and a faithfulness-time `axiom_closure`. This
increment must clear a **further ≥3-lens re-review** focused on (a) conformance completeness over
composition and (b) the E7 binding actually tying the identity string to `cert.data`.

### Track B — deferred to ADR 0057 (direction, not design)

The review found Track B **relocates** the TCB rather than shrinking it to a lint: "author in Lean, gate
is a lint" presupposes (i) a single elaborated-term data model (today `propositio.py` has four independent
free-text strings, no shared AST), (ii) an `Expr`-level fragment checker (a head-symbol whitelist cannot
see truncated `-`, floor `/`, silent `↑` coercions, or definitional unfolding in the *elaborated* term),
and (iii) **an owner for the unbounded→finite reduction** now that the renderer is gone — which must be
**gate-owned**, or a proposer-authored finite surrogate with a wrong modulus is a false PASS no lint
catches. None of these exist; each is new load-bearing faithfulness TCB. **ADR 0057 must specify the
data model, the Expr fragment checker, the reduction owner, and a ℕ/coercion conformance discipline
before Track B is reviewable.** It is removed from this ADR's implementation scope.

---

## Why one ADR for "both"

ADR 0055 established, across two adversarial rounds, that **the Lean kernel can soundly decide a
faithfulness claim by finite residue enumeration** — a wrong period leaves open goals so the kernel
DEFERs rather than false-passing. The re-review then showed the residual trust does not live in the
enumeration; it lives in **producing the Lean statement the kernel is asked to decide.** Two designs
were on the table; they are not alternatives but the two ends of one pipeline:

> In **every** version, the kernel decides the *same object* — the faithfulness **pair** over
> `established_domain` (coverage `∀ vars, claim_domain → established_domain`; property
> `∀ vars, established_domain → claim_domain → claim_property`, `probes.py:61-68`). The only variable
> is **how that pair's Lean text is produced, and what is trusted to produce it faithfully.**

- **Track A (bridge):** DSL string → `[audited renderer]` → Lean pair. Trust = a renderer that must
  *translate* Z3-DSL semantics into Lean semantics correctly. This is real, auditable TCB.
- **Track B (target):** claim authored in Lean → `[canonicalizer]` → Lean pair. The canonicalizer only
  *normalizes* Lean (α-renaming, notation, whitespace); it does not translate semantics, so there is
  nothing to *mis-translate*. Trust collapses to a fragment/well-formedness lint plus the kernel.

Track A unblocks the corpus we already have; Track B is where the trusted surface goes to zero. Running
them together lets A be the migration path that sunsets its own renderer as B takes over new authoring.
They **share** one artifact — the semantics-conformance discipline — so building A is not wasted when B
lands: the same conformance obligations (`Int.div` vs floor, comparison chaining, sign conventions,
ℕ/ℤ) are exactly what a reviewer must check to trust *any* Lean rendering of a DSL-shaped fact.

---

## Track A — the audited DSL→Lean renderer (near-term bridge)

**Goal:** let the *existing* DSL faithfulness contract (`Enuntiatio.claim_domain / claim_property`,
`Expressio.established_domain`) be kernel-decided, closing the four holes ADR 0055 v2.1 left open.

1. **The renderer is declared, audited faithfulness TCB — not incidental code.** A single module
   (`dsl_to_lean.py`, frozen like `probes.py`) is the *only* path from a DSL predicate to a Lean
   proposition. It ships with a **semantics-conformance test suite** that pins, against the DSL's Z3
   semantics (`smt_z3.py::_conv`), every construct where DSL and Lean integers diverge:
   - **`/` and `%` by a constant** — the DSL uses floor/Euclidean division (`smt_z3.py:177-181`); Lean
     `Int.div`/`Int.emod` differ (`Int.div` truncates toward zero: `-7/2 = -4` in the DSL sense vs `-3`
     for `Int.div`). The renderer MUST emit the Lean operator that matches the DSL (`Int.fdiv`/`Int.emod`
     or an explicitly-defined floor-div), and the suite MUST include the negative-argument cases.
   - **comparison chaining** — `0 ≤ a ≤ n` is a DSL conjunction (`smt_z3.py:193-201`); the renderer MUST
     emit the explicit `0 ≤ a ∧ a ≤ n`, and the suite MUST reject the mis-parse.
   - **sign / domain conventions** — see the ℕ/ℤ reconciliation below.
   A construct without a conformance-pinned rendering is **not admitted** (the renderer refuses → the
   gate DEFERs). This is the fix for the v2.1 re-review's NEW *critical* (a mis-encoding renderer passes
   string identity while both strings denote the wrong proposition — identity between two strings from
   the *same* renderer cannot detect a mis-encoding renderer; **only the conformance suite can**).
2. **Binding covers the pair AND both ∃-witnesses, by re-render + identity, in `check()`.** The gate
   (`FaithfulnessGate.check`, `faithfulness.py:125-143`, where `prop` is in scope) re-renders — from the
   audited renderer — the canonical unbounded `∀ (vars : ℤ)` pair **and** the two positive-content
   witnesses `∃ (vars:ℤ), claim_domain` and `∃ (vars:ℤ), established_domain ∧ claim_domain`, and asserts
   **string identity** of each against the certificate's corresponding statement **before** the kernel
   re-check. This closes the v2.1 NEW *high* (amendment 2's ∃-witnesses were an unbound side-channel a
   backend spoofed with `∃, 0==0`): every kernel-checked statement is now one the gate itself produced
   from `prop`.
3. **ℤ/ℕ reconciliation (one integer world, stated once).** The DSL pins a non-negative box
   (`smt_z3.py:279-280`); a naive `∃ (vars:ℤ)` witness proves non-emptiness over a domain broader than
   the human reads (`a+5==0` is empty over ℕ but has the ℤ witness `a=-5`). **Decision: the faithfulness
   contract is ℕ (non-negative) end-to-end** — the daemon's claims are over naturals — so the renderer
   emits `∀ (vars : ℕ)` / `∃ (vars : ℕ)` (or `∀ v : ℤ, 0 ≤ v → …` with the box explicit), matching the
   box every other gate already relies on. The published Enuntiatio is rendered over the *same* ℕ domain,
   so prose and formal cannot diverge. (`Int.emod` non-negativity that ADR 0055 leaned on holds a
   fortiori over ℕ; the residue case-split is over `Fin m`.) The conformance suite pins that the ℕ
   rendering of every whitelisted op agrees with the DSL box.
4. **`imports` are canonicalized / whitelisted.** `imports` are LLM free text (`Expressio`); an
   unaudited `notation`/`macro_rules` can make a string-identical `theorem_src` elaborate to a weaker
   proposition. The renderer emits from a **fixed import allow-list**; the certificate's `imports` must
   equal it, and `axiom_closure` runs inside the rechecker (below). This closes the v2.1 residual *high*.
5. **Axiom-closure inside the faithfulness rechecker.** The registered `lean-decided-faithfulness`
   rechecker calls the shared `axiom_closure` (`export_calculemus.py:51-75`) as a hard step — rejecting
   `sorryAx` / `Lean.ofReduceBool` **at faithfulness time**, so the enumeration stays pure-kernel
   `decide`/`omega` and never `native_decide`.
6. **Resource cap + claim-type predicate on `applies()`.** A named residue-product cap (analogue of the
   Z3 path's `MAX_ORDER=64`, `smt_z3.py:46`) → DEFER at parse time; `applies()` carries a claim-type
   predicate so an OPEN_FORM-tagged structured claim routes to the backend/DEFER, never the judge.

**Track A scope:** multivariable modular polynomials + `gcd(v, c)` (the fragment the daemon already
conjectures and that dies at the gate today). Bounded `Σ/Π` remain stripped (non-periodic → always
DEFER under exact-only → zero yield).

## Track B — the native-Lean faithfulness contract (target; renderer sunset)

**Goal:** for *new* conjectures, remove the DSL→Lean translation entirely, so the renderer is not on the
trust path for anything authored after the cutover.

1. **The contract is authored in Lean.** The FORMALIZE proposer emits `claim_domain` / `claim_property`
   / `established_domain` as **Lean expressions over a fixed context** (the same `(vars : ℕ)` binder as
   `theorem_src`), from **one elaborated term** shared with `theorem_src` — closing the
   four-independent-strings gap (`propositio.py`: today `Enuntiatio.claim_domain/claim_property` and
   `Expressio.theorem_src/established_domain` are independent free text) at the source rather than by
   re-derivation.
2. **The gate becomes a lint, not a translator.** Faithfulness = (a) a **fragment check** (the contract
   uses only the decidable whitelist — modular/`gcd`/finite), (b) a **well-formedness / type check** (it
   elaborates over the fixed context to `Prop` with the intended binder), (c) the **kernel decides the
   pair** by residue enumeration, (d) **`axiom_closure`** on the pair proof. There is no semantics
   translation to trust; the canonicalizer only *normalizes* Lean (α-equivalence, notation) for the
   binding-identity check and for novelty (ADR 0032's structural signatures move from DSL to Lean AST).
3. **Same kernel core as Track A.** The pair, the ∃-witnesses, the wrong-period-DEFERs guarantee, and
   the fail-closed default are identical; only the *provenance* of the Lean text changes (authored, not
   translated).
4. **Renderer sunset.** Once native-Lean authoring covers a claim class, that class no longer invokes
   the Track-A renderer; the renderer's trusted surface is *frozen* and shrinks to the legacy DSL corpus.
   A metric (fraction of promulgations that touched the renderer) tracks the sunset.

**Migration:** Track A ships first (unblocks the corpus, builds the conformance suite). Track B reuses
the conformance suite as its fragment/well-formedness spec and the same kernel-decide core, and takes
over new authoring. Neither ships before clearing review.

---

## What both tracks keep from ADR 0055 (do not relitigate)

- **The kernel decides the pair by residue enumeration; a wrong/under-approximated period → open goals →
  DEFER, never a false PASS.** (ADR 0055 round-1 confirmed sound.)
- **Exact-only PASS**; TIMEOUT/UNKNOWN → DEFER, never a bounded law tier.
- **Pure-kernel `decide`/`omega`, never `native_decide`** (guarded by `axiom_closure`).
- **Fail-closed default:** no rechecker registered for the kind ⇒ a backend PASS is never accepted
  (`faithfulness.py:129-130`). Nothing is at risk until a reviewed rechecker is registered.

## Red-team targets for the adversarial review (both tracks)

- **Track A renderer conformance (critical class).** For each whitelisted op, does the emitted Lean
  denote the *same* function as the DSL over the ℕ box — `/const`, `%const`, `min`/`max`, `gcd(v,c)`,
  `^const`, chained comparisons — including boundary/negative-adjacent cases? A single non-conformant op
  is a false-EXACT-PASS. Is the conformance suite *complete* over the admitted grammar (a construct with
  no pinned rendering must be un-admittable)?
- **Binding completeness.** Are the pair AND both ∃-witnesses ALL re-rendered by the gate and
  identity-checked before the kernel re-check? Any statement the kernel checks that the gate did not
  produce is an unbound channel.
- **ℕ/ℤ coherence.** Does the ℕ-end-to-end decision actually hold across the renderer, the published
  Enuntiatio, the residue case-split, and novelty — with no gate still assuming ℤ?
- **Track B fragment/well-formedness.** Can an authored-Lean contract elaborate to a `Prop` *outside*
  the decidable fragment yet pass the fragment check (e.g. a hidden unbounded quantifier, a coercion, a
  `Decidable` instance that diverges)? Does the canonicalizer's normalization ever change meaning?
- **Imports / notation.** Can a whitelisted import still redefine a token's meaning?
- **Shared:** vacuity (empty `claim_domain` over the *decided* domain), discrimination (deferred to the
  non-triviality gate, which runs first — `pipeline.py:103→113` — and must be pinned as a regression),
  resource exhaustion (huge residue product → DEFER, not OOM).

## Consequences

- **One coherent migration** instead of a false choice: audit the renderer to unblock today's corpus,
  author in Lean to shrink the TCB tomorrow, sharing the conformance discipline and the kernel core.
- The trusted surface has an explicit **downward trajectory** (renderer-touch fraction → 0), which no
  single-track design offered.
- Not implemented until the adversarial review clears **both** tracks. If the review finds a
  non-conformant renderer op (Track A) or a fragment-escape in authored Lean (Track B), that track is
  amended or dropped, not shipped on optimism. The fail-closed default means the daemon keeps running,
  soundly, throughout.
