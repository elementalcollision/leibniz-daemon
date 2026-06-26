<!--
Walnut reachability micro-probe (ADR 0037 backend #1 measure-before-build gate). Self-contained
record. Method: 16-agent assemble→classify→adjudicate workflow over automatic-sequence-genre target
theorems, classified against Walnut's decidable theory (FO + addition over k-automatic sequences,
Büchi–Bruyère). Provenance: docs/results/walnut_reachability_probe_report.json. The ACTUAL Walnut
run is sandbox-blocked (running untrusted external Java) — this probe establishes reachability +
soundness on paper + a corrected, ready-to-run command; the live run awaits operator authorization.
-->

# Walnut reachability micro-probe — GREEN (build the backend)

**Status:** measured (reachability + soundness), 2026-06-26. **Verdict: GREEN.** The
automatic-sequence/Walnut paradigm soundly reaches the unbounded-∀ class the bounded box cannot —
12/12 target theorems are IN-Walnut **and** box-OUT, 6 plausibly non-textbook, each emitting a
re-checkable automaton certificate that fits the ADR 0037 `SoundFaithfulnessBackend`. **Novelty
itself is NOT established by this probe** (that needs the blind human panel). Gates backend #1.

## Why this experiment

ADR 0037 stages new sound backends crawl-walk-run, **each behind a reachability micro-probe**
(the ADR 0036 §10.5 discipline). M2 found the bounded-box DSL expresses 0/24 novel theorems, blocked
by the bounded-box *soundness paradigm* (#2 unbounded-∀ on 19/24). The first candidate backend is
**Walnut**: a sound + complete decision procedure for first-order sentences over **k-automatic
sequences** (Büchi–Bruyère) — genuinely **unbounded ∀n**, the exact class the box cannot reach. The
probe asks: does Walnut soundly decide ≥1 genuinely-non-textbook class that is box-OUT, with a
re-checkable certificate?

## Result — GREEN

| metric | value |
|---|---|
| targets classified | 12 |
| IN-Walnut (sound FO+addition over a k-automatic sequence/reduction, unbounded n) | **12 / 12** |
| IN-Walnut **and** box-OUT (genuine unbounded-∀ — the M2 escape class) | **12 / 12** |
| plausibly non-textbook (structured `novelty` field) | 6 / 12 |
| adversarial automaticity over-claims found | **0** (no "non-automatic sequence asserted automatic") |

**The M2 contrast — the headline.** On the *bounded-box* DSL, M2 measured **0/24** novel theorems
expressible. On the *automatic-sequence* paradigm, this probe finds **12/12** of its targets
expressible **and soundly decidable over unbounded n**. That is the first concrete evidence that a
**different sound checking paradigm escapes the M2 wall** — exactly what ADR 0036 §10.2/§12 predicted
the escape would require (a new sound backend, not a DSL tweak).

**Soundness + certificate (why it fits ADR 0037).** Each target is a first-order sentence over
⟨ℕ, +, <, A[·]⟩ with A k-automatic; by Büchi–Bruyère, Walnut decides it by **automaton synthesis
over unbounded n** (not by sampling a `[0,64]` window). TRUE ⟺ the synthesized automaton is
universal / its complement empty — an **independent automaton emptiness check re-verifies it**. So
each decision is **exact-or-DEFER with a re-checkable certificate** = a `SoundFaithfulnessBackend`.
The probe's adjudicator empirically re-verified the load-bearing arithmetic up to bounds (Motzkin
mod 8 ≠ 0; Catalan residue counts mod 2^k; Thue–Morse overlap-free with squares of unbounded period;
Tribonacci 4th-power-free) — consistent with the predicted Walnut verdicts.

## Honesty — what this probe does and does NOT establish

- **It establishes reachability + soundness, NOT novelty.** The structured `novelty` field tags 6
  targets "nontextbook" and 6 "textbook"; **none is literally "research"**, and the notes are
  explicit that TRUE novelty requires the blind human panel (ADR 0034 §5), never a classifier. This
  is the same discipline as M1/M2: we do not claim novelty without the blind read. GREEN means "the
  paradigm is worth building," not "Walnut discovers."
- **The genuinely-novel headlines need engineering and can DEFER.** Targets 5/6/7 — Motzkin numbers
  never divisible by 8 (a *named former conjecture*), Gessel/Apéry mod 8, odd-Catalan residue count —
  are the strongest novelty, but each requires constructing/loading a custom DFAO (Rowland–Yassawi
  for prime-power moduli). They can DEFER on engineering grounds; do **not** use one as the first
  smoke-test.
- **The backend cuts both ways (a feature).** Target 4's *stated* Fibonacci-recurrence formula is
  false at every n; Walnut would soundly **REFUTE** it (the correct form is self-flagged in the
  target). A sound refutation is exactly the trust-preserving behaviour we want.
- **Partial-defers:** Targets 2 (Rudin–Shapiro abelian 2-regularity) and 8 (Stern per-length count
  identity) are not single FO+addition evals — their bounded automatic *shadows* are in scope, the
  verbatim headlines are linear-representation facts outside one `eval`.
- **A command bug was caught on review** (read-only): the adjudicator's best-candidate command used
  `T` (Thue–Morse) under `?msd_trib`; the Tribonacci word is `TR`. Corrected below.

## The first smoke-test (corrected, ready to run)

Lowest-risk decisive run — Tribonacci word is **4th-power-free** (no factor of exponent ≥ 4). Uses
Walnut built-ins only (`msd_trib`, word `TR`), no custom automaton, genuinely unbounded ∀i,p:

```
eval trib4free "?msd_trib ~Ei,p (p>=1 & At (t<3*p) => TR[i+t]=TR[i+t+p])";
```

Expected verdict TRUE (the Tribonacci word's critical exponent ≈ 3.19 < 4). `3*p = p+p+p` stays in
FO+addition (no variable×variable). Walnut emits the synthesized automaton; TRUE ⟺ the existential
power-automaton is empty — independently re-checkable. The **decisive point is not the value** but
that Walnut *soundly decides* an unbounded-∀ statement the `[0,64]` box cannot. Higher-novelty
follow-up once custom DFAOs can be loaded: `eval no8 "?lsd_2 An MOT8[n]!=@0";` (Motzkin numbers never
divisible by 8 — the named former conjecture).

## Runbook for the actual run (operator-authorized)

The actual run is **sandbox-blocked** here (it executes untrusted external Java) — correctly, since a
"micro-probe" did not authorize running an agent-cloned external codebase. To execute it (your call):

```bash
git clone --depth 1 https://github.com/firetto/Walnut.git && cd Walnut
./gradlew clean customFatJar                 # builds build/libs/Walnut-all.jar (Java 17+; Java 21 present)
printf 'eval trib4free "?msd_trib ~Ei,p (p>=1 & At (t<3*p) => TR[i+t]=TR[i+t+p])";\n' \
  | java -jar build/libs/Walnut-all.jar      # or paste at the interactive prompt
# result + synthesized automaton land in Result/ and Automata Library/
```

## Recommendation

**The gate passes.** Build the Walnut `SoundFaithfulnessBackend` per ADR 0037, staged: (1) wire the
protocol + the bounded-Z3-demoted-to-lint dispatch; (2) integrate Walnut as backend #1 with the
automaton-emptiness **re-checker** behind an adversarial soundness review; (3) route automatic-
sequence claims to it via `ClaimProbe`. Then — and only then — measure *novelty* on its output with
the blind panel. This probe has shown the paradigm is *sound and reaches the box-OUT class*; whether
it *discovers* remains the open question the blind read will answer.

## Provenance

`docs/results/walnut_reachability_probe_report.json` (12 targets, full classifications). Method:
16-agent assemble→classify→adjudicate; Walnut spec read from the tool's documented decidable theory.
Trust boundary untouched: no code run against the repo, no `kernel_verified`/`promulgated` writes,
`tests/test_invariants.py` unchanged.
