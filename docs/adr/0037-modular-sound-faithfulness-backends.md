# ADR 0037 — Modular sound-faithfulness backends (crawl-walk-run)

**Status:** Proposed (design only — no code, awaiting operator approval).
**Date:** 2026-06-26
**Predecessors:** ADR 0002 (faithfulness gate), ADR 0036 (genuine discovery — §10.2 located the escape
in a *different sound checking paradigm*; §11/§12 measured M1/M2, which converge on the bounded-box
check-as-sole-arbiter as the wall). ADR 0004 (claim contract), ADR 0013 (SMT verifier), ADR 0035
(the bounded DSL, order-reduction).
**Trust boundary:** untouched. Nothing here lets an LLM decide a proof or a faithfulness PASS;
every backend is a *checker* (exact-or-DEFER, re-verified certificate), never a judge. The eventual
builds keep `LeanVerifier.discharge` the sole `kernel_verified` writer, `TrustPolicy.validate_path`
and `tests/test_invariants.py` byte-identical on the proved path.

---

## 1. Context — why now

The measured arc has triangulated the wall. ADR 0034 (richer proposer) and ADR 0035 (richer in-box
grammar) each measured **0 blind-novel**. ADR 0036's two round-2 pre-tests then converged:

- **M1 (§11):** mining the corpus is mechanically viable but recovers only the **textbook genre**;
  novelty is input-diversity-gated; the syntactic compressor is a floor, not a ceiling.
- **M2 (§12):** the sound-faithfulness DSL cannot even **state** 0/24 genuinely-novel theorems, and
  the binding constraint is the **bounded-box soundness *paradigm***, not the vocabulary — #2
  unbounded-∀ blocks 19/24 and no bounded extension repairs it.

Both name the same root cause ADR 0036 §10 identified: **the pointwise bounded-box `[0,64]` check
used as the sole *sound* faithfulness arbiter.** The escape (§10.2/§12) is not a DSL tweak but a
*different sound checking paradigm* — and there is more than one candidate (automatic-sequence
decision, SOS/Positivstellensatz, the kernel bridge), each reaching a different class. The operator's
direction: build for **modularity** so these arrive **crawl-walk-run**, and treat the trust-preserving
multi-backend architecture as a first-class, low-regret investment.

This is feasible because the faithfulness layer is *already* partly modular: `SMTBackend`
(`leibniz/verifiers.py`) is a `Protocol` with one implementation (`smt_z3`); `ClaimProbe`
(`leibniz/gates/faithfulness.py`) is a per-`ClaimType` router; the proposal side (`prover_ensemble`)
is already multi-prover. This ADR generalizes the *checker* seam to admit multiple **sound**
backends behind the unchanged trust boundary.

## 2. Decision — the `SoundFaithfulnessBackend` protocol

One protocol unifies every sound check of the statement↔claim correspondence:

```python
class SoundFaithfulnessBackend(Protocol):
    name: str
    cost_rank: int                                   # cheapest first

    def applies(self, prop: Propositio) -> bool: ...
        # routing: does this backend handle this claim's shape at all?

    def check(self, prop: Propositio) -> FaithfulnessVerdict: ...
        # EXACT-OR-DEFER. PASS requires a re-checkable certificate. Never a judge.


@dataclass(frozen=True)
class FaithfulnessVerdict:
    verdict: Verdict                  # PASS | FAIL | DEFER
    certificate: Optional[Certificate]  # REQUIRED iff PASS — re-checkable, not trusted
    tier: TrustTier                   # always MECHANICAL for PASS/FAIL
    producer: str                     # provenance, e.g. "walnut/0.7+recheck"
```

**Three invariants the protocol enforces (the whole point):**

1. **Exact-or-DEFER.** A backend returns `PASS` only when it has *soundly decided* the claim;
   otherwise `DEFER`. `DEFER` **never** silently becomes `PASS`. (This is the ADR 0020/0030
   vacuous-PASS rule, made structural.)
2. **PASS carries a re-checked certificate.** Like a Lean proof, the certificate is *re-verified by
   an independent checker*, not trusted because the backend said so. `PASS` without a certificate
   that re-checks is a bug, caught by a guard test.
3. **MECHANICAL, never JUDGED.** A `SoundFaithfulnessBackend` is by definition not the LLM judge.
   The existing OPEN_FORM judge fallback stays exactly as today (flagged, budget-bounded), reached
   only when *every* sound backend `DEFER`s.

### Dispatch (the faithfulness gate, generalized)

The gate becomes an ordered pipeline, cheapest-first, over registered backends:

1. **Bounded-Z3 lint** (today's `find_counterexample` / `find_gaming_witness`) — **demoted from
   *arbiter* to a cheap kill-only *lint*** (ADR 0036 §10.2). It can `FAIL` (a witness refutes) but
   its survival is no longer a faithfulness `PASS` on its own.
2. **Sound backends in `cost_rank` order**, gated by `applies`. The **first `PASS` with a
   re-checking certificate wins**; `FAIL` quarantines (`GAMED`/witness); collect `DEFER`s.
3. **All DEFER → the existing judge fallback** (JUDGED tier, flagged) or quarantine `UNFAITHFUL` —
   unchanged from today.

The bounded box is thus no longer the *sole* arbiter: it is one lint plus *n* sound backends.

### The certificate per backend (crawl-walk-run)

| Stage | Backend | Decidable class (the unbounded-∀ etc. it reaches) | Certificate | Re-checked by |
|---|---|---|---|---|
| **Crawl** | **Walnut / automatic-sequences** | FO statements over k-automatic sequences — genuine sound **∀n** (Büchi–Bruyère decidable) | the synthesized automaton / Walnut transcript | independent automaton emptiness/equivalence check |
| **Walk** | **SOS / Positivstellensatz** | real multivariate polynomial nonnegativity / semialgebraic | rational SOS decomposition `P = Σ cᵢ Qᵢ²` | `ring` (kernel) expands & checks the identity |
| **Run** | **Kernel bridge (Stage B)** | general `claim_prop ↔ statement` | a Lean proof term | the Lean kernel (`LeanVerifier`-style re-check) |

All three are the *same shape*: an external engine *proposes* a certificate; an independent, smaller
checker *re-verifies* it. That is the project's core pattern (LLM proposes, kernel disposes) applied
to faithfulness. The bounded Z3 box stays as the cheapest lint.

## 3. Why the trust boundary is intact

| Concern | How it holds |
|---|---|
| LLM never decides a faithfulness PASS | every backend is exact-or-DEFER with a *re-checked* certificate; the judge is reached only when all DEFER, exactly as today |
| `kernel_verified` / `Q.E.D.` | untouched — still written only in `LeanVerifier.discharge`; this ADR is on the *faithfulness* edge, not the proof edge |
| `validate_path` / `is_promotable` | unchanged — promotion still requires PROOF + FAITHFULNESS edges; we only add *more ways to earn the faithfulness edge soundly* |
| `tests/test_invariants.py` | byte-identical (proved-path guards untouched); **each new backend ships with its own guard test** that PASS implies a re-checking certificate and DEFER never becomes PASS (the M2/§3a "new path is unguarded, not safe" lesson) |
| new TCB surface | each backend's *certificate re-checker* is the only added trusted code; it ships behind an **adversarial soundness review** (ADR 0021/0030 precedent), like the Stage-B renderer |

## 4. Staging — and the measure-before-build gate on each rung

Crawl-walk-run, each rung **gated on its own reachability micro-probe** (the ADR 0036 §10.5
discipline — do not build a backend until a cheap probe shows it soundly reaches a class the box
cannot, *and* that class is plausibly non-textbook, to be confirmed by a later blind read):

1. **Crawl — Walnut.** Narrowest, but a genuine unbounded-∀ sound class and the cheapest new engine
   (a mature external tool). Its micro-probe (this cycle) gates the build.
2. **Walk — SOS/Positivstellensatz.** The round-2 reviewers' favored certifying fragment; real
   domain. Gated on its own probe after Walnut.
3. **Run — kernel bridge (Stage B).** Most powerful, but undecidable-in-general (wide DEFER) and the
   renderer is a load-bearing TCB → the heaviest review. Last.

The protocol is what makes this incremental: each rung is a new `SoundFaithfulnessBackend`
registration, not a rewrite.

## 5. Consequences

- **If approved:** a single trust-preserving seam lets sound checkers be added one at a time,
  cheapest-first, each behind a reachability probe and a soundness review. The bounded box is
  correctly demoted to a lint. This is low-regret infrastructure — valuable even if the discovery
  upside (still unproven per M1/M2) does not materialize, because it is the right factoring of the
  faithfulness gate regardless.
- **It does not by itself produce novelty.** Whether *any* backend reaches blind-novel output is the
  open question; this ADR only makes the backends *pluggable and sound*. Each rung's novelty is
  measured by the unchanged blind human panel (ADR 0034 §5), never asserted.
- **No code until the protocol + the first backend's micro-probe are approved.** The protocol lands
  first (small, pure interface + the dispatch refactor + guard tests); Walnut lands only if its probe
  is green.

*Calculemus — and build the seam before the engine.*
