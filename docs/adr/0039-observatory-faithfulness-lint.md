# ADR 0039 — Observatory faithfulness lint + formal-first record

**Status:** Accepted (implemented; lint always on, `require_descriptor` on for the live tier).
**Date:** 2026-06-26
**Predecessors:** ADR 0038 (the Walnut-decided Observatory tier — what this hardens), ADR 0037
(bounded-Z3-demoted-to-lint set the "a bounded check can only DOWNGRADE" precedent). Decision input:
the **first live Observatory run** (`docs/observatory-first-run-finding.md`,
`docs/results/observatory_first_run_verification.json`).
**Trust boundary:** untouched. This is a tier-internal faithfulness aid in the **non-Q.E.D.**
Observatory. It NEVER sets `kernel_verified`/`promulgated`/`Demonstratio`, never calls
`TrustPolicy.validate_path`; `tests/test_invariants.py` is byte-identical. The lint can only ever
**downgrade** a Walnut DECIDED-true to a quarantine — it never certifies and never upgrades.

---

## 1. Why this, why now

The Observatory channel (ADR 0038) ran end-to-end live for the first time: **3 DECIDED, 2 REFUTED, 0
errors.** The decider is sound — but adversarial verification found **all 3 DECIDED records are
faithfulness artifacts.** In each, Walnut soundly decided the *predicate*, but the conjecturer's
English→FO encoding mis-stated the bound, so the predicate is a *different — true — statement* while the
prose claim is FALSE for Rudin-Shapiro (RS):

| pid | bug | predicate decides | prose claims | prose true? |
|---|---|---|---|---|
| d4a4d22b | `t<4p` not `t<3p` | RS 5th-power-free (true) | RS 4th-power-free | **FALSE** (`0000` at 7–10) |
| d37eb690 | `i<n+4` not `i<n+3` | no alternating len-5 window | no alternating len-4 factor | **FALSE** (`1010` at 13–16) |
| baff1218 | window off-by-one | — | length-(n+1) factor non-constant | **FALSE at n=1** (`00`) |

This is the **3-body / formal-statement ↔ human-claim gap on the proposal side**, exactly as the
project's charter predicts. The kernel and Walnut both faithfully decide whatever predicate they are
handed; neither can catch a predicate that doesn't mean what its author intended. ADR 0038's only
defense was "formal-first publication" — but reading the prose misleads, and the prose was the thing the
operator's blind-novelty panel would have wasted budget reviewing. We need a *mechanical* check that the
predicate is faithful to the property it claims, **without trusting prose**.

## 2. Decision

Two coupled mechanisms, applied to **every Walnut DECIDED-true** before it is filed as
`WALNUT_DECIDED`:

1. **Property descriptor** (`Expressio.property_descriptor`). The conjecturer co-emits a HIGH-LEVEL,
   machine-checkable spec of the property the predicate is meant to encode, drawn from a **closed
   whitelist of families** — `power_free` (exponent e), `avoids_factor` (a literal block),
   `avoids_pattern` (alternating, length L). The descriptor carries **only high-level parameters**
   (`exponent=4`); the error-prone *bound arithmetic* lives solely in `walnut_predicate`. The descriptor
   therefore pins the predicate's INTENT **independently** of the bound the predicate actually used.

2. **The lint gate** (`leibniz/observatory_lint.py`). First **bind** the descriptor to the predicate —
   its `word` must be exactly the word(s) the predicate indexes (`RS[…]`, `T[…]`, …) — and guard the
   parameters (block symbols within the word's alphabet; non-degenerate exponent/length). Then
   brute-force the descriptor over a finite PREFIX of the (canonically-generated) sequence:
   - a prefix **counterexample** to a property the predicate was DECIDED-true on ⇒ the predicate is
     *not faithful* to the stated property ⇒ **quarantine** (`lint_counterexample`), never DECIDED.
     (This is the artifact catch: d4a4d22b/d37eb690 are caught; their counterexamples — `0000`, `1010` —
     are real refutations.)
   - **undescribable** (no descriptor / unknown family / unsupported word / bad params) ⇒ quarantine
     iff `require_descriptor` (the live tier): a formal-first record needs a machine-checkable anchor.
     (baff1218's contrived n-dependent property fits no standard family ⇒ refused.)
   - otherwise **pass**: file `WALNUT_DECIDED`, recording the lint status in the provenance edge.

3. **Formal-first record** (made explicit). The statement of record is the **predicate + descriptor**;
   the `Enuntiatio` prose is advisory commentary. The provenance edge detail carries
   `faithfulness = {mode: formal_first, lint, prefix_checked, …}`, and the live ledger labels the prose
   accordingly. A future blind-novelty panel assesses the predicate's meaning, not the prose.

## 3. Soundness argument

- **Only ever downgrades.** The lint never sets any kernel/promotion state and is not in
  `TrustPolicy.validate_path`. Its sole effects are `DECIDED-true → quarantine` or "annotate and pass".
  So it cannot weaken the tier and cannot fabricate a decision. (Same posture as bounded-Z3-as-lint,
  ADR 0037.)
- **Counterexamples are genuine.** For `power_free`/`avoids_factor`/`avoids_pattern`, a prefix
  occurrence is a literal witness that the universal property FAILS — a *sound* refutation of any
  DECIDED-true claim, independent of Walnut.
- **A clean prefix is NOT a proof.** Absence of a prefix counterexample is necessary, not sufficient;
  the lint never claims otherwise. Walnut's decision over unbounded n remains the actual decision; the
  lint only catches the case where the predicate provably encodes the *wrong* property.
- **The generators are the soundness root.** The sequence generators (`T`, `RS`, `F`, `TR`) must match
  Walnut's built-in words exactly, or the cross-check compares the wrong sequence. They are pinned to
  canonical definitions (popcount parity / morphism fixed points) and verified against canonical
  prefixes in `tests/test_observatory_lint_r0039.py` and by an independent computation
  (`docs/results/observatory_lint_verification.json`). Paperfolding (`P`) is intentionally **unsupported
  in v1** (subtle sign conventions); an unsupported word safely DEFERs rather than risk an unsound
  generator.
- **The descriptor is bound to the predicate's word** (adversarial-review fix). The lint chooses its
  canonical sequence from `descriptor.word` *and* requires that to equal the word(s) the predicate
  actually indexes; a mismatch (or a predicate over two words, or over an unsupported word like
  paperfolding) is `undescribable` ⇒ refused. Without this, a descriptor naming a *different* sequence
  (Thue-Morse, which is 4th-power-free) than the predicate (Rudin-Shapiro, which is not) would
  brute-force the wrong sequence and pass a real artifact. Parameter guards reject out-of-alphabet
  blocks and degenerate exponent/length (vacuous-true anchors).
- **The descriptor is a narrower trust surface than the predicate.** It does not carry the bound
  arithmetic where the observed errors live, and under formal-first the prose is not the record anyway.
  If the LLM emits a descriptor that matches its buggy predicate (e.g. exponent=5 to match `t<4p`), the
  lint passes and the record honestly states the *predicate's* true meaning — not an artifact, just a
  (textbook) true fact, correctly labeled.

## 3a. The residual the lint does NOT close (and what would)

The lint catches the **honest-but-buggy** conjecturer — the one whose descriptor faithfully states the
property it *intended* but whose predicate has a bound bug (exactly the three live artifacts). It does
**not** close *family-/parameter-shopping*: a conjecturer that emits, for the *right word*, a genuinely
true but **unrelated** property (e.g. `avoids_factor RS "00000"` for a claim that is really about
4th-powers) passes — because both the predicate (over all n) and the shopped property (over the prefix)
are *true*, so no bounded check can separate two true propositions. This residual is **irreducible in
the lint+formal-first design** (a single LLM authors both the predicate and its only statement of
intent). It is mitigated by — not eliminated by — the word binding, the closed family whitelist, and
the alphabet/degeneracy guards.

The **full** closure is the *templated-predicates* option (the alternative the operator did not pick):
the conjecturer chooses a family + parameters and the Observatory *renders* the predicate with
mechanically-correct bounds, so predicate and descriptor cannot disagree by construction. The two are
complementary; templated predicates can be layered on later. **Backstop today:** because this is a
non-Q.E.D. tier whose DECIDED records are reviewed by a *human* blind-novelty panel, a shopped record is
caught there — the lint's job is to cheaply filter the *bulk* honest-but-buggy artifacts so that scarce
human budget is not spent on them.

## 4. What this does NOT do

- It does not make the tier Q.E.D. (still ADR 0038: non-Q.E.D., kernel-bridge gated, task #54).
- It does not close family-/parameter-shopping (see §3a) — only templated predicates do.
- It does not check that the predicate is *structurally equivalent* to the descriptor beyond the word
  binding + prefix agreement. (A bounded predicate-FO interpreter would not help the residual: since
  Walnut decided the predicate true over all n, the predicate is *always* true on the prefix, so a
  bounded predicate↔descriptor check collapses to "is the descriptor also true on the prefix" — exactly
  the existing counterexample check.)
- It does not produce novelty. Even perfectly faithful, the families above are textbook; the lint's job
  is to make the records *trustworthy enough to measure*, so the scarce human blind-panel budget is
  never spent on artifacts.

## 5. Config / surface

- `WalnutObservatory(require_descriptor: bool = False)`. Default False keeps the pure decision-semantics
  tests (no descriptor) exercising the Walnut path; the live conjecturer and `scripts/run_observatory.py`
  set it **True**. The counterexample catch is always on regardless.
- New reasons in the run histogram: `lint_counterexample`, `lint_no_descriptor`.
- Prompt: `Role.WALNUT_CONJECTURE` now requires a `property_descriptor` from the whitelist.

## 6. Future work

- Add `recurrent` / appearance / additive families with sound bounded checkers.
- Support paperfolding once its generator is adversarially verified.
- Optional bounded predicate-FO interpreter to cross-check the predicate directly against the descriptor
  (defense in depth beyond prefix agreement).
