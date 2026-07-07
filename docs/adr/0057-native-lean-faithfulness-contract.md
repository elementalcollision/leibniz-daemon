# ADR 0057 — A native-Lean faithfulness contract (Track B of the staged Lean-decided design)

**Status:** **PROPOSED — blocked on adversarial review.** This is the **deferred Track B of ADR 0056**
(§"Track B — the native-Lean faithfulness contract"), which ADR 0056's review outcome held back with the
verdict that Track B as first sketched *"relocates the TCB rather than shrinking it to a lint"* — it named
five missing pieces (the shared data model, an Expr-level fragment check, the reduction owner, the ℕ/coercion
discipline, novelty on a Lean AST). This ADR specifies exactly those pieces. Per the ADR 0051 / 0054 / 0055 /
0056 precedent, **no code ships on the faithfulness path until this design clears its own ≥3-lens adversarial
review.** It keeps everything ADR 0055's two rounds found sound — the kernel decides the pair; a
wrong/under-approximated reduction leaves open goals → DEFER; exact-only PASS; the fail-closed default
(`faithfulness.py:129-130`). Complements ADR 0002 (faithfulness gate), ADR 0037 (sound-backend seam), ADR 0050
(law provenance). Track A (the audited DSL→Lean renderer, ADR 0056) ships first as the bridge; Track B is the
target, and its cutover freezes and shrinks the renderer's trusted surface toward zero.

---

## Context — why native-Lean, and what 0056's review found missing

ADR 0055 established, across two adversarial rounds, that the Lean kernel can soundly *decide* a faithfulness
claim — the residual trust is not in the enumeration but in **producing the Lean statement the kernel decides.**
Track A audits a DSL→Lean *renderer* so today's DSL corpus can be kernel-decided; that renderer is real,
irreducible faithfulness TCB because it must *translate* Z3-DSL semantics into Lean semantics (`smt_z3.py`
floor-`/` at `:177-181`, the non-negativity box at `:279-280`, comparison chaining) without drift.

Track B removes the *translation* by authoring the claim in Lean from the start (the fleet's
"Leanstral-emits-Lean" reframing): a canonicalizer that only *normalizes* Lean has nothing to *mis-translate*.
But ADR 0056's review was right that "author in Lean" alone does not shrink the TCB — it **moves** it into
(i) whatever produces the elaborated term, and (ii) whatever certifies that term lies in the decidable fragment.
A head-symbol/surface whitelist is not that certifier: it cannot see truncated `-` (`Nat.sub`), floor `Nat.div`,
silent ℕ→ℤ→ℝ coercions, `Decidable` instances that diverge, or a forbidden construct hidden behind a
proposer-defined `def` and definitional unfolding. And the four faithfulness fields are today **four
independent free-text strings** — `Enuntiatio.claim_domain` (`propositio.py:44`), `claim_property` (`:45`),
`Expressio.theorem_src` (`:56`), `established_domain` (`:62`) — with no shared AST, so the decided pair can
silently denote something other than the published prose. This ADR specifies the data model, the checker, the
reduction owner, and the ℕ discipline that make "author in Lean" collapse the TCB to a lint-plus-kernel — and is
honest that the elaborator/data-model **is** new (smaller, auditable) faithfulness TCB, not zero TCB.

---

## Decision (proposed, pending review)

### 1. The single elaborated-term data model

The FORMALIZE proposer emits **one Lean source artifact** — a *contract module* — not four strings. It declares
the contract pieces as named `def`s over **one fixed binder context**:

```lean
namespace Faithful_<pid>
def ClaimDom  (a b : ℤ) : Prop := 0 ≤ a ∧ 0 ≤ b
def EstDom    (a b : ℤ) : Prop := 0 ≤ a ∧ 0 ≤ b
def ClaimProp (a b : ℤ) : Prop := (a^2 + b^2) % 4 ≠ 3
end Faithful_<pid>
```

The **gate is the sole elaborator.** It elaborates this module **once**, in the same Docker kernel image used
for proofs, yielding the three `Expr`s (`ClaimDom`, `EstDom`, `ClaimProp`) from **one** elaboration environment
pinned to a fixed import allow-list. Every downstream object is a **gate-computed projection** of those Exprs,
never an independent proposer input:

- the faithfulness **pair** the kernel decides (`probes.py:61-68`: coverage `∀ → ClaimDom → EstDom`;
  property `∀ → EstDom → ClaimDom → ClaimProp`) — built by the gate from the Exprs;
- `theorem_src` (`propositio.py:56`) the prover later discharges — the same elaborated statement;
- the published Enuntiatio prose — pretty-printed from the *same* Exprs.

The `propositio.py` fields keep their types for back-compat but, on a native-Lean claim, are **populated by the
gate from the elaboration** and tagged `native_lean=True`; the proposer's direct free-text setters are refused
for such a claim. This closes the four-independent-strings gap **at the source** rather than by re-derivation:
there is one object, and prose / pair / theorem are all functions of it.

The proposer never hands over pre-elaborated `Expr`s (it is untrusted). It hands over Lean *source*; the gate
elaborates. **Honesty:** the gate-owned elaborator plus the two projection functions (Expr→pair-statement,
Expr→prose) are now faithfulness-critical TCB. The claim is only that this is a *smaller, single-purpose,
auditable* surface than a DSL→Lean semantic translator — it *normalizes and projects* one term, it does not
*translate* between two semantics.

### 2. An Expr-level fragment checker (not a head-symbol whitelist)

Faithfulness admissibility is decided by walking the **elaborated `Expr`** — after elaboration has made
coercions, `OfNat`, and `Decidable`/`instance` terms explicit — and recursively certifying every node against an
allow-list of **fully-qualified constants**, not surface tokens. Accept only: `Int.add/Int.sub/Int.mul` (genuine
total ℤ ops), `HMod.hMod`/`Int.emod` and `Int.gcd`/`Int.ediv` **with a literal `Int` numeral second argument**,
`Eq/Ne/LE.le/LT.lt` over ℤ, `And/Or/Not`, integer literals via `Int.ofNat`, and the gate-owned bounded binder of
§3. The checker **fails closed**: its default arm on any `Expr` constructor without an explicit ACCEPT rule is
REJECT → the gate DEFERs. Specifically it rejects, by construction:

- **every `Nat.*` arithmetic node** — no `Nat.sub` (truncated), no floor `Nat.div`; subtraction is total `Int.sub`;
- **every coercion node** — `Nat.cast`, `Int.cast`, `Rat.cast`, any `↑` — no silent ℕ→ℤ→ℝ domain shift;
- **any `Decidable` instance** that is not the canonical `Int.decEq`/`Int.decLe`/… for a whitelisted relation
  (an opaque or divergent `Decidable` instance → REJECT, so a "decides but loops/means-something-else" instance
  cannot ride in);
- **a `%`/`gcd`/`ediv` whose divisor `Expr` is not a literal numeral** (a variable modulus is not finitely reducible);
- **any free `∀`/`∃`/`Exists`/`Forall`** not enclosed by §3's gate-owned finite reduction (blocks a hidden
  unbounded quantifier);
- **unfold-and-recheck:** before accepting an application of a `def` from the claim module, the checker `whnf`/
  `delta`-unfolds it (against the module's **own** decls only, never Mathlib) and re-checks the unfolded `Expr`.
  A `def` that unfolds to anything off the allow-list → REJECT. Recursion is depth-capped → DEFER on cap.

This is what a surface whitelist cannot do: the forbidden constructs (`Nat.sub`, floor div, coercions, divergent
`Decidable`, `def`-hidden escapes) are only visible **in the elaborated term**, and only a fail-closed
constant-level walk over that term can certify their absence.

### 3. The gate-owned unbounded→finite reduction owner

ADR 0055's soundness came from the **renderer** emitting the residue case-split, so a wrong period left open goals
and the kernel DEFERred. Track B sunsets the renderer, so the reduction owner must be re-assigned — and it **must
be the gate, never the proposer.** A proposer-authored finite surrogate with a wrong modulus (`∀ a b : Fin 4, …`
when the true period is 8) is a false PASS no lint catches.

Mechanism: the proposer supplies **only the contract statement** (§1) — no proof, no tactic, no finite surrogate.
The **gate** constructs both the goal *and* the reduction tactic:

```lean
theorem faithful_<hash> :
    (∀ a b : ℤ, 0 ≤ a → 0 ≤ b → ClaimDom a b → EstDom a b) ∧
    (∀ a b : ℤ, 0 ≤ a → 0 ≤ b → EstDom a b → ClaimDom a b → ClaimProp a b) := by
  <gate-owned reduction tactic, templated from the moduli read out of the elaborated Expr>
```

The gate reads the set of **literal moduli** `M` appearing in `%`/`gcd` **out of the checked Expr** (§2
guarantees they are all literal), and templates a fixed, proposer-immutable `Fin m`/`ZMod m` case-split over
`∏ M`, discharging each residue cell by pure-kernel `decide`/`omega`. Soundness has two independent legs, either
sufficient:

1. **Completeness-by-construction, checked by the kernel.** If the gate's own modulus extraction ever
   under-approximates (a bug reads too few moduli), the residue split does not cover the residual `∀ a b : ℤ`
   goal, `decide` leaves open goals, and **the kernel refuses to close the theorem → DEFER**, never a false PASS.
2. **No proposer surrogate is ever accepted.** The kernel only ever sees the **gate-constructed unbounded
   `∀ a b : ℤ` pair.** A certificate carrying a proposer proof of any *finite* statement in place of that pair is
   rejected at the binding step, which **reuses the E7 template-pin** (`registry.py:106-129`,
   `register_decider` at `:49-67`): the proposer supplies witness DATA (the contract module), never the
   proposition it is graded on; the gate's template renders the canonical unbounded pair, and a claimed statement
   not byte-/Expr-identical to it DEFERs.

So the reduction ownership moves from "the renderer (audited TCB)" to "a case-split tactic the gate templates from
literal moduli," and the TCB shrinks from a semantic translator to (that tactic + the §2 checker that guarantees
only literal moduli exist).

### 4. A ℕ/coercion semantics-conformance discipline

"Nothing to mis-translate" is false for *authored* ℕ-Lean: `Nat.sub` truncates (`3 - 5 = 0`), `Nat.div` floors,
coercions shift domain — all silently. Track B therefore does **not** accept arbitrary authored Lean; it commits
to the **same ℤ-with-explicit-non-negativity-box world Track A landed on** (ADR 0055 amendment 4; ADR 0056's ℤ/ℕ
reconciliation): every binder is `∀ v : ℤ, 0 ≤ v → …` / `∃ v : ℤ, 0 ≤ v ∧ …`, never `ℕ`. The §2 checker
*enforces* this by rejecting every `Nat.*` node and every coercion node, so by construction there is no truncated
subtraction, no floor-div ambiguity (division is banned unless it is `Int.emod`/`Int.ediv` by a literal, whose
non-negative-residue semantics ADR 0055 already leaned on), and no ℕ→ℤ→ℝ coercion. The published Enuntiatio prose
(§1's projection) is rendered from the **same** boxed-ℤ Expr, so "for all non-negative integers a, b" and
`∀ a b : ℤ, 0 ≤ a → 0 ≤ b → …` cannot diverge. A **semantics-conformance suite** — shared with Track A per ADR
0056 — pins, per whitelisted constant, that its ℤ-boxed meaning equals the intended arithmetic (`Int.emod`
non-negativity, `Int.gcd`, chained-comparison desugaring) as build-time regressions. **Honesty:** this safety is
a *discipline enforced by the checker*, not a free property of "native Lean." Authored Lean is safe only because
the checker refuses everything whose ℤ-boxed semantics is not pinned.

**Novelty (`structural.py` / `novelty.py`).** Today the structural signature keys on the DSL `claim_property`
string (`novelty.py:81` calls `structural_known(en.claim_property)`; `structural.py:320` parses the DSL). Under
Track B `claim_property` is a Lean `Expr`. The `congruence_signature` canonicalizer therefore moves to
canonicalize the **elaborated Lean Expr** (α-normalized, coefficients reduced mod m, exact one-period residue set
per `structural.py:200-234`). It must preserve the module's soundness invariant: two claims share a signature IFF
they assert the same congruence, so the only error direction stays a *missed KNOWN* (false-NOVEL, benign, and
novelty only demotes reversibly). A canonicalizer meaning-shift here would be a **false-KNOWN** that suppresses a
real discovery — a first-class red-team target below, not a free win.

---

## What Track B keeps from ADR 0055 (do not relitigate)

- **The kernel decides the pair** (`probes.py:61-68`) over `established_domain`; both conjuncts, always.
- **Wrong/under-approximated reduction → open goals → DEFER**, never a false PASS (ADR 0055 round-1 sound).
- **Exact-only PASS**; TIMEOUT / UNKNOWN → DEFER, never a bounded law tier.
- **Pure-kernel `decide`/`omega`, never `native_decide`** — the registered rechecker runs `axiom_closure`
  (`export_calculemus.py:51-75`) as a hard step, rejecting `sorryAx`/`Lean.ofReduceBool` at faithfulness time.
- **Fail-closed default:** no rechecker registered for the kind ⇒ a backend PASS is never accepted
  (`faithfulness.py:129-130`; `sound_backends.py:77-86`). Nothing is at risk until a reviewed rechecker registers.
- **∃-witness positive-content control** (ADR 0055 amendment 2, ADR 0056 Track A #2): the gate re-renders and
  identity-binds `∃ v:ℤ, 0≤v ∧ ClaimDom` and `∃ v:ℤ, 0≤v ∧ EstDom ∧ ClaimDom` before the kernel re-check; an
  empty `ClaimDom` yields no witness → DEFER (vacuity control).
- **The E7 binding**: the proposer authors DATA, never the graded proposition (`registry.py:106-129`).

## Red-team targets for the adversarial review

- **Fragment-escape (critical class).** Can an authored contract elaborate to a `Prop` outside the decidable
  fragment yet pass §2? Attempt each: a coercion `↑` re-introducing ℝ; a hidden unbounded `∀`/`∃`; a divergent or
  opaque custom `Decidable` instance; a variable modulus laundered through a `def`; a forbidden construct hidden
  behind a `def` that the unfold-and-recheck must expose. Every one must REJECT/DEFER, never PASS.
- **Reduction ownership.** Confirm the proposer cannot supply a finite surrogate that the gate accepts: the kernel
  must only ever see the gate-constructed unbounded `∀ a b : ℤ` pair, and a wrong-modulus split must leave open
  goals → DEFER. Attack the modulus extraction (too few moduli read out of the Expr).
- **The data-model elaborator as new TCB.** An elaborator/import-environment bug, or an Expr→prose projection that
  diverges from the Expr→pair projection, could publish prose that does not match the decided pair. Pin the
  projections to one Expr; adversarially seek a claim where prose and pair disagree.
- **Canonicalizer meaning-shift.** Does the Lean-AST normalization (α-renaming, notation resolution, coefficient
  reduction) ever change meaning — for the binding-identity check (a false-identity PASS) or for novelty (a
  false-KNOWN that suppresses a discovery)?
- **Novelty on the Lean AST.** Does `congruence_signature` retain its "same signature IFF same congruence"
  soundness after moving from the DSL string to the elaborated Expr (`structural.py:200-234`, `novelty.py:79-92`)?
- **Shared:** vacuity (empty `ClaimDom` over the *decided* domain → DEFER via the ∃-witness control);
  discrimination (deferred to the non-triviality gate, which runs first, `pipeline.py` ordering — pin as a
  regression); resource exhaustion (huge `∏ M` residue product → DEFER at parse time, never OOM); imports/notation
  (the fixed import allow-list must pin the elaboration environment so notation resolves to the whitelisted
  constants and nothing else).

## Consequences

- **The renderer leaves the trust path for native-authored claims.** For claims authored after cutover, the
  DSL→Lean *translator* (Track A's TCB) is not consulted; faithfulness TCB is the elaborator + the fail-closed
  Expr checker + the gate-owned reduction tactic + the two projections — a **smaller, single-purpose, auditable**
  surface than a semantic translator, but **not zero.** This ADR does not claim it removes all TCB.
- The trusted surface keeps ADR 0056's **downward trajectory** (renderer-touch fraction → 0), now with a concrete
  target: a lint (§2) + a kernel-checked reduction (§3) over one elaborated term (§1).
- Every ADR 0055 soundness property is preserved unchanged, and the trust invariants hold: LLMs still only
  *propose* (they author the contract module; the gate elaborates, checks, reduces, and the kernel decides);
  `kernel_verified` is still written only by the kernel; `TrustPolicy.validate_path` and
  `tests/test_invariants.py` are untouched on the proved path.
- **Not implemented until this design clears its own ≥3-lens adversarial review.** If the review finds a
  fragment-escape (§2), a reduction-ownership hole (§3), an elaborator/projection divergence (§1), or a
  canonicalizer meaning-shift (§4), that piece is amended or Track B is dropped in favour of the Track-A bridge —
  not shipped on optimism. The fail-closed default means the daemon keeps running, soundly, throughout.
