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
2. **PASS carries a certificate re-checked by the *gate*, not self-reported.** Like a Lean proof, the
   certificate is *re-verified by an independent checker*, not trusted because the backend said so.
   The gate holds its **own** registry of re-checkers keyed by `certificate.kind`
   (automaton-**universality** for `walnut-automaton`, `ring` for `sos`, the kernel for
   `kernel-bridge`) and accepts a backend PASS only when a re-checker for that kind exists **and
   returns True**. The backend's `Certificate.rechecked` flag is *advisory*; the gate's own re-check is
   authoritative, defeating a backend that merely *reports* a pass. **Honest strength varies by kind:**
   the kernel-bridge re-check re-derives everything (a full kernel re-check, like the proof edge's
   `producer == KERNEL` pin); the Walnut/SOS re-checks verify a *structural property* of the produced
   certificate (e.g. the agreement automaton is universal) while the underlying decision procedure
   (Walnut, like Z3 on the gaming spine) stays in the **faithfulness** TCB — not a kernel-style
   re-derivation of that engine's decision. With no re-checker
   registered for a kind, a PASS of that kind **cannot** be accepted, so the dormant default (no
   backends, no re-checkers) is maximally safe. `PASS` without a certificate, of an unregistered kind,
   or whose re-check fails, is downgraded to fall-through — caught by guard tests. *(This is the
   hardening the Slice-1 adversarial soundness review recommended; adopted in Slice 1 rather than
   deferred, so the honor-system flag is never load-bearing.)*
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
| **Crawl** | **Walnut / automatic-sequences** | FO over k-automatic sequences — genuine sound **∀n** (Büchi–Bruyère) | the synthesized **agreement automaton** | independent automaton-**universality** check (Walnut itself trusted, like Z3) |
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

---

## 6. Backend #1 (Walnut) reachability gate — GREEN

The §4 measure-before-build gate for the crawl rung is run. Full record:
`docs/walnut-reachability-probe-finding.md`; provenance
`docs/results/walnut_reachability_probe_report.json`.

- **GREEN: 12/12** target theorems are IN-Walnut **and** box-OUT — soundly decidable over
  **unbounded n** (FO + addition over k-automatic sequences, Büchi–Bruyère), the exact unbounded-∀
  class M2 found the bounded box cannot reach (M2: 0/24 expressible; Walnut: 12/12). 6 are plausibly
  non-textbook; the adversarial automaticity check found **0** dangerous over-claims. Each decision
  emits a re-checkable **automaton certificate** (TRUE ⟺ synthesized automaton universal /
  complement empty) → exact-or-DEFER, fits the §2 protocol exactly.
- **Honest bound:** the probe establishes *reachability + soundness*, **not novelty** — the
  structured novelty field has 0 literal "research" tags, and true novelty needs the blind human
  panel (ADR 0034 §5). GREEN means "the paradigm is worth building," not "Walnut discovers."
- **Caveats carried forward:** the genuinely-novel headlines (Motzkin mod 8 never divisible by 8 — a
  named former conjecture; Gessel/Apéry mod 8; odd-Catalan residue count) need custom DFAOs
  (Rowland–Yassawi) and can DEFER on engineering; a first smoke-test (Tribonacci 4th-power-free,
  built-ins only) is queued; the actual run is sandbox-blocked (untrusted external Java) and awaits
  operator authorization.

**Decision:** the crawl rung is cleared to build — the Walnut backend (protocol + lint-demotion
dispatch + Walnut integration with the automaton-universality re-checker behind an adversarial soundness
review), then a blind-panel novelty read on its output. The walk rung (SOS) and run rung (kernel
bridge) remain gated on their own probes.

---

## 7. Slice 2 landed — the Walnut backend (`leibniz/backends/walnut.py`)

Built and merged **OFF BY DEFAULT** (not wired into `assembly.py`; no re-checker registered → the gate
cannot accept a `walnut-automaton` PASS until the operator opts in). Faithfulness is rendered as a
free-variable **agreement predicate** `claim(n) ↔ statement(n)`; Walnut emits the agreement automaton;
the gate-owned re-checker independently verifies it is **universal** (a tri-state classifier —
`universal`/`refuted`/`indeterminate` — returns `universal` only for a *complete, deterministic* DFAO
over a modeled numeration alphabet, every reachable state accepting).

**Soundness took three adversarial-review rounds** (the discipline working): round 1 caught a string-
compare re-checker over-claimed as a kernel-style pin (fixed → real universality check); round 2 caught
that universality was unsound for *partial/dangling* automata + a command-injection surface (fixed →
completeness enforced via kept transition labels + numeration alphabet; predicate/numeration sanitized);
round 3 returned **safe_to_merge, 0 blocking, no laundering paths**. Both reproduced laundering strings
(`msd_2\n\n0 1\n0 -> 0\n`; `… 0 -> 7 …`) and the injection now DEFER, with regression tests. Walnut +
the renderer are honestly placed in the **faithfulness** TCB (like Z3); the proof-edge TCB (Lean kernel)
is untouched; `tests/test_invariants.py` byte-identical.

**Output-format validation — DONE.** The parser was validated against the Walnut serializer *source*
(`Automata/Automaton.java::write`/`writeAlphabet`/`writeState`): a TRUE/FALSE result is the literal
token; otherwise the header is the numeration name (`msd_2`), each state is `<q> <output>`, and each
transition is `<digit> -> <dest>` with **bare** space-separated digits (the reviewers' "bracketed
`[0],[1]`" concern was a misread — brackets are a separate display path, not the `.txt` writer). Our
parser matches this for the single-track numeration agreement automaton (confirmed also by the real
`Word Automata Library/T.txt`); multi-track/set-alphabet/NFA cases DEFER (sound). A regression test
(`test_parses_real_walnut_serializer_format`) pins the exact byte-format. Reading the serializer covers
every case, so it is a stronger check than a single live sample.

**STILL MUST-DO BEFORE THE OPERATOR ENABLES IT** (each errs to DEFER — sound): (1) **prop-binding** — a
partial numeration-match seam is in (`check` DEFERs on a numeration mismatch); the deeper automaton↔claim
binding remains the documented Walnut+renderer TCB; (2) **runner home derivation** hardening
(`$LEIBNIZ_WALNUT_HOME`). With the format validated, the live backend now classifies real single-track
output correctly — so once the operator registers it + the re-checker, a genuine universal agreement
automaton will PASS (and a non-universal one FAIL), rather than DEFERring everything.

---

## 8. Backend #2 (SOS / Positivstellensatz) reachability gate — AMBER

The §4 measure-before-build gate for the **walk** rung is run. Full record:
`docs/results/sos_walk_rung_probe_report.json` (4-dimension probe + synthesis, run `whha16dx0`).

**Composite verdict: AMBER — worth building as low-regret infrastructure, NOT on the strength of
discovery yield.** Two dimensions GREEN (the questions they answer), two AMBER (the question that
gates the build — novelty):

- **Soundness + tooling — GREEN, de-risked.** The exact-recheck path is *proven, not asserted*: a
  stdlib-only (`fractions.Fraction`) re-checker — polynomial-identity dict-equality over ℚ **+** exact
  rational **LDLᵀ** PSD test (no sqrt; pivots carry the squares) — was implemented and passed 6/6 cases
  including correct rejection of an indefinite Gram and a fabricated identity-failing cert. The float SDP
  solver, the only unsound component, stays entirely **off-TCB** (an optional propose-side extra, like
  Z3/Lean). Published precedent (`sostactic`) ships the literal §2 contract in Lean (`ring_nf` identity +
  `positivity`). For non-SOS-but-nonneg targets (Motzkin; Blekherman: *almost all* nonneg polys aren't
  SOS) the Positivstellensatz/denominator form `d·P = n` keeps the re-checker unchanged.
- **Box-OUT reach — GREEN, genuine.** SOS reaches `∀x∈ℝⁿ` polynomial nonnegativity: over ℝ (not ℤ),
  unbounded (not `[0,64]`), a universal-quantifier *proof* (not a finite enumeration) — three orthogonal
  axes of escape from the bounded-integer box, orthogonal to Walnut. (Caveat: the genuinely-unbounded ℝⁿ
  target is served by the *narrow* pure-SOS + Reznick-multiplier fragment; Putinar/Schmüdgen need
  compactness, so the constrained successes overstate coverage of the headline class.)
- **Novelty — AMBER, the binding constraint (same wall as Walnut).** The reachable class is **bimodal**:
  a RED sub-class (competition/olympiad inequalities — AM-GM, Schur, symmetric 3-var — *now actively
  automated* by AIPS/LIPS, the SOS analogue of run-3's textbook ceiling) and a GREEN sub-class
  (research-frontier: flag-algebra extremal combinatorics where SOS+SDP has resolved *open* conjectures,
  copositivity / SOS-Lyapunov, SOS proof-complexity lower bounds). **The current conjecturer/DSL emits
  the RED class out of the box and cannot render the GREEN class** without substantial new proposal-side
  machinery — "reachable in principle ≠ reachable by the current daemon," the same trap as Walnut's
  custom-DFAO caveat. AMBER not RED because SOS has a genuine open frontier (a *strictly higher* novelty
  ceiling than Walnut) *if routed there*.
- **Faithfulness — the rung's strongest dimension.** A polynomial inequality often *is* its own formal
  statement (`∀ x y z : ℝ, 0≤x → … → 0 ≤ P x y z`) — the 3-body gap is materially smaller than Walnut
  prose. Residual slack lives in the *statement* (constraint set; strict `<` vs non-strict `≤`), which is
  lint-able at routing, not in the trusted certificate path.

**The pivotal strategic finding — two seams, and only one is Q.E.D.:**
- **SOS as a faithfulness backend (this ADR's §2 placement) is NON-Q.E.D.** (faithfulness edge, not proof
  edge; invariants #1/#7 keep `kernel_verified` to `LeanVerifier.discharge`). *But* its re-check is the
  first **kernel-grade** faithfulness re-check — `ring` re-derives the SOS identity, strictly stronger
  than Walnut's structural automaton-universality check.
- **SOS as a *prover* (proof edge, alongside `nlinarith`/`polyrith`) is GENUINELY Q.E.D.** when the
  conjecture *itself* is a polynomial inequality: the cert re-checked by `ring`+`positivity` *is* a kernel
  proof. This is a sound path to **kernel-verified discovery without the run-rung renderer** — arguably
  the higher-value use and the real strategic upgrade over Walnut. It is a *different seam* (`prover_
  ensemble`), and must stay uncrossed from the faithfulness backend.

**The true go/no-go (still pending):** per §4/§10.5, the soundness-GREEN does **not** clear the build. The
gating measurement is a **WALK-rung novelty micro-probe** — does the conjecturer produce
polynomial-nonnegativity claims that are IN-SOS-reach **and** box-OUT **and** plausibly-non-textbook? If
they are all RED competition inequalities, defer the build until the proposal side can route to the GREEN
frontier. Recommended re-checker if built: **Option A** (stdlib `Fraction` identity + exact rational LDLᵀ,
zero float tolerance), cross-checked by Lean `ring`+`positivity` in the adversarial soundness review.
