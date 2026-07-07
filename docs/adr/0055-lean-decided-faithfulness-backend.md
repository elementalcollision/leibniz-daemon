# ADR 0055 — A Lean-decided faithfulness backend (v2 redesign of ADR 0054)

**Status:** **NEEDS FURTHER AMENDMENT → v2.2 (2026-07-07).** Two adversarial review rounds have run.
Round 1 (`needs-amendment`) validated the Lean-decided **architecture** but found two false-EXACT-PASS
paths; six bounded amendments were folded in (below). Round 2 — the re-review gate — returned
**`needs-further-amendment`, high confidence, `safe_to_implement: false`:** the amendments only
*partially* closed the holes and **relocated the trust boundary into an (unbuilt) DSL→Lean renderer
that becomes faithfulness TCB** — where DSL/Lean semantic drift (`Int.div` truncation, comparison
chaining) yields a NEW *critical* false-EXACT-PASS string identity cannot detect, amendment 2's
∃-witnesses are an unbound side-channel, and the ℤ/ℕ gap reopens. **The crux is now named: the hard
part is the renderer, not the enumeration.** The **fail-closed default is intact** (no rechecker
registered → a backend PASS is never accepted), so nothing is at risk today. See "**v2.1 re-review
outcome — the renderer crux**" below for the v2.2 obligations and the strategic fork (audit a DSL→Lean
renderer vs. author claims natively in Lean). Amendments 3, 5, 6 are sound and may proceed as build-time
regressions. Per the ADR 0051 / ADR 0054 precedent, **no code ships on the faithfulness path until a
v2.2 clears re-review.** This is the "v2 ADR" ADR 0054 (NEEDS REDESIGN, 2026-07-07) called for; it
folds in all seven ADR 0054 mitigations plus the nine-reviewer external fleet review's dominant
correction. Supersedes the design in **ADR 0054** (the rejected v1). Complements ADR 0002 (faithfulness
gate), ADR 0037 (sound-backend seam), ADR 0020/0022 (contract encodability / probe), ADR 0050 (law
provenance tier/origination).

---

## Review outcome & v2.1 amendments (do not implement §Decision-4 or the residual must-builds as first written)

A five-lens adversarial soundness review (vacuity/discrimination · statement-binding/AST ·
typed-AST/period-traps · seam/ordering/fall-through · reduction/kernel-trust), each verified **against
the code**, returned **`needs-amendment` · high confidence · `safe_to_implement: false`**. It confirmed
the core reduction argument is sound (a wrong/under-approximated period leaves open goals → the kernel
rejects → DEFER, never a false PASS; `Int.emod`'s non-negative residues genuinely cover the negatives;
the gaming spine at `faithfulness.py:90` runs *before* the backend loop at `:111`) — but found two
kernel-clean EXACT-PASS paths the Lean pivot does **not** close, plus four smaller gaps.

### Confirmed holes (verified against the code)

- **CRITICAL — the binding binds the wrong object.** §Decision-4 (as first written) compares a
  **backend-supplied `canonical_statement_hash`** to a gate recomputation — a field **disjoint from the
  `theorem_src := proof_src` the kernel actually checks** (`CertificateRechecker` is prop-blind,
  `sound_backends.py:48`; the accept path `faithfulness.py:125-143` calls `rechecker(v.certificate)`
  with no `prop`). An untrusted backend puts `hash(real statement)` in the bound field and a provable
  **narrowed/bounded/weaker** pair in `theorem_src`; both checks pass and never meet. This also
  subsumes the "bounded-binder emission" attack (a shared canonicalizer would replicate the narrowing
  on both sides so the hashes still match).
- **HIGH — empty `claim_domain` vacuity; the named control is mis-targeted.** Both pair conjuncts carry
  `claim_domain` as a hypothesis (`∀ … → claim_domain → …`). With an **unsatisfiable** `claim_domain`
  (the ADR's own headline `(a²+b²)%4==3`, which is unsat), both conjuncts are **vacuously kernel-true**
  with a clean axiom footprint → EXACT-PASS. The ADR's only vacuity control is `established_domain`-SAT
  — fully satisfied here, so it cannot catch it. This is a **regression inside 0055's target fragment**:
  the Z3 probe returns `unknown` on this two-variable nonlinear-modular UNSAT and safely DEFERs
  (`probes.py:61-68`); 0055's kernel enumeration turns that DEFER into a PASS on a claim that asserts
  nothing. And the non-triviality gate does **not** save us — closing `∀ a b:ℤ, (a²+b²)%4==3 → …`
  needs the very modular case-split only this backend provides, so `is_trivial` (decide/simp/omega)
  misses it. **The fix cannot be a Z3 SAT call** (Z3 is inert on this fragment) — it must be a
  **Lean-side non-emptiness ∃-witness**.
- **HIGH — "reject on Nat/Int mismatch" is unimplementable against an untyped DSL.** The DSL compiles
  `−` to true Z3 `Int` subtraction with non-negativity added only as an out-of-band solver box
  (`smt_z3.py:160,279-280`); there is **no signal** for residual must-build #2 to detect. The emitted
  `∀ … : ℤ` proves the ℤ proposition faithfully, but an Enuntiatio whose prose reads "for all *naturals*"
  is a *different, false* claim under ℕ truncation. Replace the detector with a **typing discipline**.
- **MEDIUM — tautological `claim_property` (e.g. `x % 1 == 0`).** **Pre-defended by ordering**: the
  theorem `∀ … → x%1==0` is `simp`-closable, so the non-triviality gate (which runs *before*
  faithfulness, `pipeline.py:103→113`) quarantines it TRIVIAL. Crucially, `is_trivial` is the *right*
  discriminator — it closes the vacuous `x%1==0` but not the genuine `(a²+b²)%4≠3` — so the fix is to
  **pin the ordering as a regression, not add a faithfulness-level tautology control** (which would
  false-reject real universal laws; see amendment 3).

### PLAUSIBLE (guard-if-built)

- **`native_decide` / `Lean.ofReduceBool` at faithfulness time.** `axiom_closure` genuinely rejects it
  (`export_calculemus.py:46,73`) — but that runs at ledger export, **disjoint from the faithfulness
  re-check**. Sound *if built to spec*; the risk is a rechecker wired to plain elaboration.
- **OPEN_FORM-tagged structured claim reaches the judge.** `applies()` is AST-shape-only; an
  OPEN_FORM-mistagged modular claim that DEFERs falls through to `self.judge` (`faithfulness.py:164-176`).
  Not a false-EXACT-PASS, but it enlarges the judged surface (invariant 3).

### v2.1 amendments (these are the spec; they supersede §Decision-4 and the residual must-builds)

1. **Binding = string/AST identity against the kernel-checked theorem, in `check()`.** In the
   faithfulness gate's PASS-acceptance path (`FaithfulnessGate.check`, `faithfulness.py:125-143`), the
   gate must (a) render `prop`'s canonical **unbounded `∀ (vars : ℤ)`** faithfulness pair from a
   **single gate-owned canonicalizer** over the elaborated AST, and (b) assert **exact identity**
   between that render and `certificate.data["theorem_src"]` — the *same string* handed to the kernel
   re-checker — then (c) run the kernel re-check on that identical `theorem_src := proof_src`. **Delete
   the backend-supplied `canonical_statement_hash`.** The bound object is the theorem the kernel checks,
   nothing else. This closes cross-statement replay *and* the narrowed-binder attack (a narrowed binder
   is not string-identical to the canonical unbounded `∀:ℤ` pair → REJECT).
2. **Lean-side positive-content control (replaces the `established_domain`-SAT control).** No EXACT-PASS
   unless the certificate **also** carries kernel-checked ∃-witness proofs of `∃ (vars:ℤ), claim_domain`
   **and** `∃ (vars:ℤ), established_domain ∧ claim_domain`. Unsatisfiable `claim_domain` → no witness →
   the ∃ cannot be proved → DEFER. (Not a Z3 SAT call — Z3 is inert on this fragment.)
3. **Discrimination is the non-triviality gate's job — and it already runs first.** Do **not** add a
   "reject if `∀ (vars:ℤ), claim_property` is kernel-provable" control: that would **false-reject the
   genuine universal laws this backend exists to find** — `(a²+b²)%4 ≠ 3` is true for *all* integers,
   so its `∀` *is* provable, yet it is a real law, not a vacuous one. The correct discriminator between
   a content-free tautology (`x%1==0`, closed by `simp`) and a genuine universal law (`(a²+b²)%4≠3`,
   which needs the modular case-split) is exactly what `is_trivial` computes — and the non-triviality
   gate runs **before** faithfulness (`pipeline.py:103→113`). So break #5 is closed **by ordering**, not
   by a new faithfulness-level control. The only spec obligation here: assert the pipeline ordering as a
   permanent regression (non-triviality precedes faithfulness), so a refactor cannot silently let a
   `simp`-closable property reach an EXACT-PASS.
4. **Typing discipline (replaces "detect Nat/Int mismatch").** Pin `ℤ` end-to-end — DSL → pair →
   `theorem_src` → **published Enuntiatio** — from **one elaborated AST**, so prose and formal cannot
   diverge. Forbid any construct whose Lean rendering is ℕ-sensitive unless the Enuntiatio is likewise
   ℤ. This also closes the four-independent-strings gap (`propositio.py`: `Enuntiatio.claim_domain/
   claim_property` vs `Expressio.theorem_src/established_domain` are today independent free text).
5. **Axiom footprint inside the rechecker.** The registered `lean-decided-faithfulness` re-checker must
   call the shared `axiom_closure` (the one in `export_calculemus.py`) as a **hard step**, rejecting
   `Lean.ofReduceBool` / `sorryAx` **at faithfulness time**, not only at export.
6. **Hard resource cap + claim-type predicate on `applies()`.** A residue-product cap → DEFER at parse
   time (name the constant; the Z3 path's analogue is `MAX_ORDER=64`, `smt_z3.py:46`); and
   `applies()` must carry a claim-type predicate so an OPEN_FORM-tagged structured claim routes to the
   backend/DEFER, never the judge.

**Re-review gate:** the v2.1 spec must **re-clear the vacuity and statement-binding lenses** (the two
that found criticals) against the amended text before any implementation. Everything the review found
sound — the reduction argument, the wrong-period-DEFERs guarantee, the Python-decider elimination — is
**kept unchanged**.

### v2.1 re-review outcome — STILL NEEDS AMENDMENT → v2.2 (the renderer crux)

The two critical-finding lenses re-ran against the amended v2.1 spec and returned
**`needs-further-amendment` · high confidence · `safe_to_implement: false`.** Both original holes are
only **partially** closed, and the amendments introduce a NEW critical and a NEW high **inside the
target fragment.** The fail-closed default is intact (no rechecker is registered for
`lean-decided-faithfulness`, so `recheckers.get()` is None and a backend PASS is never accepted —
`faithfulness.py:129-130`), so **nothing is at risk today**; the block is purely on shipping the
capability.

**The crux, now named.** Amendment 1 did not *eliminate* the trust boundary — it **relocated it into a
gate-owned DSL→Lean renderer.** String identity checks `render(prop) == theorem_src`, but **both come
from that one renderer**, so a *mis-encoding* renderer passes identity while both strings denote the
wrong proposition, the kernel proves it cleanly, and the check gives zero protection (it never consults
the human claim). And DSL vs Lean integer semantics genuinely diverge on whitelisted constructs:

- **`/const`** is floor / Euclidean in the DSL (`smt_z3.py:177-181`) but `Int.div` **truncates toward
  zero** in Lean (`-7/2 = -4` vs `-3`) — a real false-EXACT-PASS the identity check cannot see.
- **comparison chaining** `0 ≤ a ≤ n` parses as a conjunction in the DSL (`smt_z3.py:193-201`) but is
  not valid/equivalent Lean.
- **`imports`** are LLM free text and un-canonicalized; a `notation`/`macro_rules` can reinterpret a
  token so a string-identical `theorem_src` elaborates to a weaker proposition (`axiom_closure` catches
  `sorryAx`/`ofReduceBool`, not a notation redefinition).

So **the hard part of a Lean-decided faithfulness gate is not the enumeration** (the kernel does that
soundly) — **it is the DSL→Lean renderer, which is irreducibly faithfulness TCB and does not exist**
(the only DSL compiler in the tree targets Z3, `smt_z3.py::_conv`; `Propositio` carries no AST — four
independent free-text fields). The confirmed v2.1 gaps:

- **NEW critical** — the DSL→Lean renderer is unaudited faithfulness TCB; DSL/Lean semantic drift
  (`Int.div`, comparison chaining) → false-EXACT-PASS that string identity cannot detect.
- **NEW high** — amendment 2's ∃-witness statements are an **unbound side-channel**: amendment 1 binds
  only the pair (`theorem_src`), so a backend supplies decoupled `∃(a b:ℤ), 0==0` payloads that
  kernel-check clean and "satisfy" the vacuity control → false PASS on a vacuous claim.
- **RESIDUAL high** — the ℤ/ℕ gap reopens: `∃(a b:ℤ), a+5==0` is proved by `a=-5`, but the domain is
  empty over the non-negative box every other gate pins (`smt_z3.py:279-280`); amendment 4's fix is
  unbuilt and *contradicts* that box.

**v2.2 obligations (before any re-review):** (i) specify the DSL→Lean renderer as **audited TCB** with
a semantics-conformance suite pinning `Int.div` truncation, comparison chaining, and `%`/`/` sign
conventions against DSL semantics; (ii) extend the re-render + string-identity check to **both
∃-witness statements**, in `check()`, before the kernel re-check; (iii) reconcile ℤ-end-to-end with the
ℕ non-negativity box, and specify where the single AST originates and how the gate re-derives the
canonical statement independently of the human Enuntiatio fields; (iv) canonicalize / whitelist
`imports`. **Amendments 3, 5, 6 are sound and may proceed as build-time regressions regardless.**

**Strategic note.** The renderer crux raises a real fork: authoring claims **natively in Lean** (per the
fleet's Leanstral-emits-Lean reframing) would make the DSL→Lean renderer *disappear* — there is no
separate DSL to mis-translate when the claim is Lean from the start, and the faithfulness gate shrinks
to a fragment/well-formedness lint. That may be the sounder long road than auditing a DSL→Lean
renderer. This is an operator decision, recorded here, not settled by this ADR.

---

## The one correction that reshapes the design

ADR 0054 proposed a **trusted Python enumeration backend**: a closed interpreter would enumerate the
residue period, a gate-derived period would bound the domain, and a certificate re-checker would
re-run the enumeration. The ADR 0054 review found three unsound decision points; the fleet review then
found the deeper problem — **the architecture keeps a Python decider on the trust path at all.**

Six substantive reviewers (Fugu, Fugu Ultra, Kimi, Gemini 3.1 Pro, MiniMax M3, Nex AGI N2) converged
on one instruction, stated most bluntly by Kimi — *"Kill it with Lean"* — and by Gemini — *"Let Lean
do the exact enumeration; this collapses the TCB back entirely into the Lean kernel."* MiniMax gave the
decisive attack: a re-checker that re-runs the **same buggy** interpreter confirms `gcd(12,18)=4` — so
an *independent Python* re-check (ADR 0054 mitigation 3) is not enough; the Lean bridge must be a
**design requirement, not an option.** Nex framed a four-level assurance ladder and set the promulgation
floor at Level 3+ (the kernel checks each residue case).

**v2 decision, in one sentence:** the backend does **not decide** — it **constructs a Lean proof of
the faithfulness pair over `established_domain`**, and the **kernel decides**, exactly as every proof
in this system is decided.

Why this is not just "more mitigations": it **structurally dissolves four of the seven** ADR 0054
mitigations, because a wrong period or a buggy evaluator can no longer produce a false PASS — it
produces a **DEFER** (the kernel refuses to close the proof). See §"How v2 satisfies the seven
mitigations".

---

## Context — the empirical finding still holds (unchanged from ADR 0054)

The richer two-variable / composite-modulus claims the daemon now conjectures (ADR 0053) **die at the
faithfulness gate**, not the prover (`reached_proof = 0`; the FORMALIZE exit with no disposition). Z3
`encodable`s the two-variable predicates but `decide_unsat` on `[a≥0 ∧ b≥0, (a²+b²) % 4 == 3]` returns
**`None` (unknown)** — two-variable nonlinear-modular UNSAT is outside Z3's decidable fragment, so
`coverage_probe` DEFERs (`probes.py:61-68`). These claims **are** decidable by finite residue
enumeration: `(a²+b²) % 4` depends only on `(a mod 2, b mod 2)`. That was correct in ADR 0054 and is
the reason the capability is worth building. What changes is **who enumerates** — the Lean kernel, not
a Python interpreter.

The faithfulness *contract* the gate must certify is the **pair** in `probes.py:61-68`, both conjuncts
referencing `established_domain`:

- **coverage** — `(claim_domain) ∧ ¬(established_domain)` is UNSAT (the claim domain is inside what the
  theorem established), and
- **property** — `(established_domain) ∧ (claim_domain) ∧ ¬(claim_property)` is UNSAT (on the
  established domain, the claimed property holds).

ADR 0054's fatal v1 bug was enumerating `claim_domain ∧ ¬claim_property` alone — a claim-**truth**
check that **drops `established_domain`**, a *regression* that would false-PASS a strong-contract /
weak-theorem claim the current `coverage_probe` safely DEFERs. **v2 certifies the pair, never the
truth check.**

---

## Decision (proposed, pending review)

Add a `SoundFaithfulnessBackend` (ADR 0037 seam, **unchanged seam**) — `LeanDecidedFaithfulness` —
that, for a claim in the periodic/modular whitelist fragment, **emits a self-contained Lean theorem
plus proof that entails the faithfulness pair, and returns it as a kernel-bridge `Certificate`.** The
gate's registered re-checker for that certificate kind is a **Lean kernel re-check of the proof term**
(the seam already documents this exact strength for a kernel bridge: `sound_backends.py:40-47`).

### 1. When it applies (`applies()`, cheap + structural)

`applies(prop)` is True **iff** every free variable enters `claim_domain`, `established_domain`, and
`claim_property` only through whitelisted **periodic or finite** constructs — `v mod c` (fixed integer
`c`), integer `+ − *`, `^` by a fixed exponent, `min`/`max` of periodic subterms, comparisons
**between periodic subterms**, and `gcd(v, c)` (fixed `c`) — **and** the claim is a shape Z3 already
DEFERs on (multivariable modular, or `gcd`). Single-variable single-modulus claims that the Z3 probe
already decides stay on the cheap Z3 path (invariant 5: cheap gate before the kernel call). Any raw
variable outside a `mod`/`gcd`-by-constant, any `mod`/`/` by a **variable**, `Nat` truncated
subtraction, unbounded `Σ/Π`, `isqrt`/`log`, or any unrecognised construct ⇒ `applies()` is **False**
⇒ the backend abstains and the gate falls through to the existing probe (which DEFERs) — never a PASS.

### 2. What it emits (a Lean proof of the pair, not an enumeration result)

From the **single canonical elaborated AST** (the same AST that will produce the eventual
`theorem_src` the prover discharges — single-source, so faithfulness and the proved theorem cannot
diverge), the backend emits **one Lean theorem** whose statement is the conjunction of the two
faithfulness-pair obligations over `established_domain`, expressed as universally-quantified integer
propositions, e.g.

```lean
theorem faithful_<hash> :
    (∀ a b : ℤ, ({claim_domain}) → ({established_domain})) ∧         -- coverage
    (∀ a b : ℤ, ({established_domain}) → ({claim_domain}) → ({claim_property})) := by
  refine ⟨?cov, ?prop⟩
  all_goals intro a b …
  -- reduce each ∀ over ℤ to its residues (omega / Int.emod case-split, or ZMod),
  -- then discharge every residue cell by `decide` / `norm_num`.
```

The **period case-split is part of the proof, not a trusted input.** If the split is incomplete (the
deriver under-approximated the true period), `decide`/`omega` leaves open goals and the **kernel
rejects the proof** → the backend returns no certificate → DEFER. A wrong period therefore costs
*yield*, never *soundness*.

Enumeration is a **pure kernel reduction** (`decide` / `omega` / `Finset.forall_range`), **not
`native_decide`** — the latter introduces `Lean.ofReduceBool`, which the existing axiom-closure
honesty gate (`export_calculemus.py:_STD_AXIOMS`) already rejects. That pre-existing gate is a free
guard: a `native_decide` "shortcut" fails promulgation automatically. (If a period is ever too large
for kernel `decide`, the backend **DEFERs**; it does not reach for `native_decide`.)

### 3. EXACT-only PASS, exactly as ADR 0054 (kept)

The backend never issues a bounded PASS. Either the kernel closes the pair-proof (**EXACT PASS**) or
it does not (**DEFER**). TIMEOUT and UNKNOWN both map to DEFER, never PASS (Kimi/Gemini taxonomy). A
bounded "verified to N" signal, if ever wanted, is a COMPUTE conjecture-ranking artifact in a separate
table that `TrustPolicy.validate_path` rejects — never a law tier.

### 4. Certificate + re-check (fits the unchanged seam)

A PASS emits `Certificate(kind="lean-decided-faithfulness", data={theorem_src, proof_src, imports,
canonical_statement_hash})`. Two independent checks, both required:

- **Gate-side statement binding (new gate code, in `discharge`, which holds `prop`).** The gate
  recomputes the canonical pair-statement from `prop`'s AST and asserts it **equals** the
  certificate's `canonical_statement_hash`. This binds the proof to *this* claim's
  `established_domain` and statement — closing certificate-laundering / cross-statement replay
  (ADR 0054 mitigations 2 and the fleet's non-replayability point). This is the one honest piece of
  **new gate code**; the `CertificateRechecker` signature stays prop-blind because the proof is
  self-contained.
- **Kernel re-check (the registered re-checker for this kind).** Runs the Lean kernel on
  `theorem_src := proof_src` and confirms it elaborates with a **clean axiom footprint** (no
  `sorryAx`, no admitted axiom, no `ofReduceBool`) — the same check `export_calculemus.py`'s
  `axiom_closure` already performs. A self-reported PASS whose kernel re-check fails is **not a PASS**
  (`faithfulness.py:127-150` already falls through to the probe → DEFER).

### 5. DSL expansion rides on the same kernel bridge (kept, re-scoped)

A construct is admissible **iff** it has a Lean-side `Nat`/`Int` definition the kernel can evaluate
(MiniMax's Lean-bridge rule): `gcd → Nat.gcd`/`Int.gcd`, later `isqrt → Nat.sqrt`, `min/max →`
list folds. The construct is added only when its residue/finite reduction is kernel-`decide`-able.

---

## Scope — first increment and backlog (fleet-adjudicated)

**First increment (tight):** **multivariable modular polynomials + `gcd(v, c)`**, emitted as a Lean
`decide` proof of the pair. This is the exact fragment the daemon already conjectures and that dies at
the gate today.

**Strip bounded `Σ/Π` from this increment** (Gemini's decisive point, adjudicated in the fleet
synthesis): bounded sums/products are generally **not periodic**, so under EXACT-only they **always
DEFER** → zero yield while enlarging the DSL and TCB. They do not belong in the first increment.

**Ordered backlog:** (1) `isqrt` via `Nat.sqrt` (MiniMax — trivial Lean bridge, distinct
square-root territory); (2) periodic-bounded `Σ` where the *bound itself* is periodic and statically
capped (Nex's narrow admissible case only); (3) variable-variable `gcd(a, b)` **only** when both args
are proven periodic **and** bounded (Nex's "Maybe" tier); (4) full Lean reflection of the period lemma
(Nex Level 4) so even completeness is kernel-checked; (5) cross-kernel replay (Coq/Rocq + HOL Light or
Metamath) for the trust-critical slice, given the honest "Lean 4 kernel is trusted, not verified"
caveat MiniMax raised.

---

## How v2 satisfies the seven ADR 0054 mitigations

| # | ADR 0054 required mitigation | How v2 satisfies it |
|---|---|---|
| 1 | Certify the faithfulness **pair over `established_domain`**, never `claim_domain ∧ ¬claim_property` | §Context + §Decision-2: the emitted Lean theorem **is** the two `probes.py:61-68` conjuncts, both over `established_domain`. |
| 2 | Bind the certificate to `established_domain` + statement hash (no replay for a broader claim) | §Decision-4: gate recomputes the canonical pair-statement from `prop` and asserts hash-equality; a Lean proof only proves its own stated theorem. |
| 3 | Thread `prop` into the re-check; admit it is new gate code | §Decision-4: statement-binding is **new gate code in `discharge`** (which has `prop`); the kernel re-check itself stays prop-blind because the proof is self-contained — so the seam signature is **unchanged**, honestly. |
| 4 | Replace "lcm of the `mᵢ`" with a per-op period contract; DEFER on `/const` on a decisive path | **Dissolved.** The period split is inside the proof; an under-derived period → open goals → kernel rejects → DEFER. `/const`, nested `mod`, `gcd`-second-arg period bugs can no longer false-PASS — they DEFER. |
| 5 | **Build** vacuity/discrimination controls on the EXACT-PASS path | §Red-team must-builds: an `established_domain`-SAT positive control (empty domain → DEFER, because the property goal is *vacuously* kernel-true — the one false-PASS the kernel does **not** catch), plus a non-tautology control and a positive/negative/DEFER regression triple. **Retained in full — Lean-replay does not close this.** |
| 6 | Treat period-deriver + interpreter as inside the TCB; pin with adversarial regressions | **Mostly dissolved** (no Python interpreter; deriver is not soundness-critical). Retained as *yield/robustness* regressions + the typed-AST fidelity suite (mitigation 7 / trap G below). |
| 7 | Move the AST periodicity/DEFER screen into the gate; DEFER on any non-whitelisted construct before an exact PASS | §Decision-1: `applies()` abstains (→ probe → DEFER) on any non-whitelisted construct; the whitelist is structural and cheap. |

**Residual must-builds that Lean-replay does NOT close (carry into the review):**

1. **Vacuity (empty `established_domain`).** `∀ x, False → …` is *vacuously* kernel-true. The kernel
   will accept it. **Keep the explicit `established_domain`-SAT control**: no EXACT PASS unless the
   established domain is non-empty.
2. **Typed-AST fidelity (Fugu Ultra trap G).** Lean `Nat` truncated subtraction and `ℤ`/`ℕ`
   mismatches would prove a *different* statement than displayed. Single-source the elaborated AST;
   emit integer (`ℤ`) semantics matching the DSL; a Nat/Int mismatch ⇒ REJECT. Permanent regression.
3. **Discrimination / non-tautology.** A property true over all of `ℤ`/`m` asserts nothing; require a
   negative control the checker must FAIL.

---

## Red-team targets for the fresh adversarial review

The v1 review and the fleet already surfaced these; the v2 review must re-verify each **against the
v2 code**, not the abstract:

- **Ordering / invariant 5.** v2 puts a **bounded Lean kernel call in FORMALIZE** for the richer
  fragment (before DERIVE's open-ended proof search). Confirm `applies()` fires *only* for claims the
  Z3 probe would DEFER, so the common single-variable path keeps its cheap Z3 gate; confirm the
  faithfulness kernel call is decidable/terminating (a residue `decide`, not a search) and hard-capped.
- **Vacuity** (empty `established_domain` → vacuous kernel PASS) — the one false-PASS the kernel does
  not catch. Verify the SAT positive control blocks it.
- **Statement binding** — verify the gate's `prop`-derived canonical statement genuinely matches the
  certificate's, with a canonicalization that a maliciously-shaped AST cannot spoof (hash the
  gate-canonical form, not the backend's emitted text — MiniMax).
- **Single-source AST** — verify the faithfulness goal and the eventual `theorem_src` derive from one
  AST, so a PASS cannot certify a statement different from the one proved.
- **Typed-AST traps** — Nat subtraction, `ℤ`/`ℕ`, nested `mod`, `/const`, `gcd` second-arg: each must
  DEFER or REJECT, never EXACT-PASS. Permanent regressions.
- **Resource exhaustion** — attacker-chosen huge modulus / huge period product must **DEFER at parse
  time or via a hard cap**, never OOM/crash into a fall-through PASS (Gemini/Nex).
- **`native_decide` smuggling** — confirm the axiom-closure gate rejects any proof whose footprint
  includes `Lean.ofReduceBool`.

Adopt Nex's **assurance-ladder Level 3 as the promulgation floor** (the kernel checks each residue
cell), with **Level 4** (kernel-checked period lemma) as the backlog end-state.

---

## Consequences

- Unblocks the richer batch the daemon already conjectures (two-variable modular, `gcd`) from **one**
  reviewed backend, with the **soundness burden moved onto the kernel** rather than a new trusted
  Python decider — the strongest posture the fleet identified.
- The faithfulness decision for the richer fragment now inherits the **same trust tier as a proof**
  (`MECHANICAL`, kernel-checked). Faithfulness and provability are decided by the same authority.
- Honest ordering: **[this backend, reviewed] → prover (Leanstral, repair)**. Only once richer claims
  can be *certified faithful* does prover reach become the limiting factor.
- Cost: one bounded kernel call per richer-fragment claim in FORMALIZE. Accepted because it is the
  only sound way to certify those claims and it fires only where Z3 DEFERs.
- Not implemented until this design clears its own ≥3-lens adversarial soundness review. If the review
  finds an unguarded false-EXACT-PASS path (vacuity, statement-binding, or a typed-AST trap), the ADR
  is amended or rejected, not shipped on optimism.

---

## Fleet-review provenance (for the record)

Nine external reviewers were solicited on the ceiling-raiser thesis.

- **Substantive (drove this design):** Fugu, Fugu Ultra, Kimi, Gemini 3.1 Pro Deep Thinking,
  MiniMax M3, Nex AGI N2 — all *endorse-with-caveats*, converging on the Lean-decided pivot.
- **Non-substantive (excluded):** Deepseek v4 Pro, GLM 5.2, Qwen 3.7 Max — each was given only the
  repo name/URL, could not fetch it, and reviewed a **hallucinated** "multi-agent society" thesis
  bearing no relation to the faithfulness backend. **Operational lesson, now standing policy: fleet
  reviewers receive the full text inline, never a bare URL.**

Distinct fleet contributions folded in beyond the ADR 0054 mitigations: the Lean-decided pivot
(Kimi/Gemini/MiniMax/Nex); the over-approximation/divisibility invariant "syntactic period is a
multiple of the true period" (Kimi/Nex) — here enforced *by the kernel closing the proof*; the
two-mode Leanstral (CONSTRAINED for yield / EXPLORATION for territory) with a named `DEFER_REASON`
taxonomy fed back to the proposer (Nex/MiniMax/Gemini constrained-decoding); demoting cvc5 to a
disagreement-signal (Kimi/MiniMax); and the novelty critique that dedup-against-own-ledger is not
novelty — promote OEIS/zbMATH to first-tier with an "exercise-vs-law" test (MiniMax). The geometry
(§2) and toolchain (§3) tracks are captured in the fleet synthesis and warrant their own ADRs (0056+),
separate from this faithfulness-backend decision.
