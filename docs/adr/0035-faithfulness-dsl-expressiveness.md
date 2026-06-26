# ADR 0035 — Faithfulness-DSL expressiveness: widening what the gate can soundly state and decide

**Status:** Accepted & measured — Stage A built, A/B-measured, then KILLED as a novelty lever
(kept opt-in/default-off as a sound yield-of-order-facts lever). See §7 for the measured outcome,
and **§7.1 for a correction** (after a 5-model external review): the novelty ceiling is Leibniz's
**pointwise bounded-box faithfulness *test*** (not the proposer, not the grammar) — but **not**
mechanical trust in general; the sound escape is *proof-carrying faithfulness* (ADR 0036). Successor to ADR 0030 (bounded definitional encodings) and
ADR 0034 (conjecturer-side novelty, §12 finding).
**Date:** 2026-06-25
**Trust boundary:** untouched, and that is the design's central constraint. `kernel_verified` is
set only in `LeanVerifier.discharge`; `Q.E.D.` iff `kernel_verified`; `gates/` and
`tests/test_invariants.py` stay byte-identical. Every mechanism lives in the DSL→Z3 *encoding*
layer (`backends/smt_z3.py::_conv`), upstream of the gate's verdict. **But see §3: this design
grows the trusted computing base (a new arithmetic oracle), which the invariant tests do not
guard — the honest reason this ADR is gated behind an adversarial soundness review.**

Scoped by a 5-design panel → judge → synthesis → adversarial challenge. The challenge materially
corrected the synthesis; its findings are folded in below (§2 guards, §3 TCB risk, §4 downgrade).

---

## 1. The problem — the DSL is the novelty wall

ADR 0034 ran a clean A/B (Stage 0+1 steering vs +Stage 2 mining, pinned config) and had a blind
4-rater panel score all 39 promulgations. The result (§12): mining **doubled yield** (13→26) but
produced **0 genuinely-novel laws — every arm, every rater** (113 textbook / 41 variant / 0 novel
votes); the 10 mined-origin laws were quadratic-residue sets, found autonomously but textbook.

The load-bearing conclusion: **the bottleneck is not the proposal source (recall vs compute) — it
is the expressiveness of the bounded faithfulness DSL.** A polynomial-congruence grammar can only
*state* textbook-genre arithmetic, so everything provable inside it is textbook by construction.

**The faithfulness model.** The gate's adversarial spine searches the box `[0, gaming_bound]`
(`gaming_bound = 64`, `gates/faithfulness.py`) with Z3 for an input satisfying the formal statement
but violating the claim. A witness is returned only on a *conclusive* model; an un-encodable
predicate raises `PredicateError` → no witness → `Verdict.DEFER`. **Exact-or-DEFER:** `UNSAT`
genuinely means "no witness in the box"; we never trade a DEFER for a guess. The current DSL:
non-neg ints; `+ - *`; **constant** powers; **constant** div/mod; `min`/`max`; comparisons/booleans.

**The Tier B/C inert-at-bound lesson (ADR 0030) — the constraint this ADR must respect.** ADR 0030
built two *sound* extensions that were *useless at bound 64*: Tier B (symbolic exponents) encoded
`base^e` as a `B+1`-arm `If`-chain — exact, but `MAX_SYM_EXP_BOUND=16 < 64` ⇒ always DEFER, and
raising the cap to 64 makes a degree-64 nonlinear term Z3 times out on (DEFER anyway). Tier C
(`gcd`/`factorial`) shelved — `factorial` caps at 12 ≪ 64 (inert); `gcd`'s logarithmic Euclid
unroll *is* sound-and-active over [0,64] but had no demand. **The bar is therefore: sound AND
active at bound 64 AND reaching a genre `congruence_signature` cannot already represent.** Anything
whose encoding grows with the box dies on the solver.

## 2. Recommendation — build Stage A only; defer or reject the rest

The judge ranked five designs. The decisive, adopted distinction: **polynomial-period reduction
(proposed by three of the five) is redundant and risky** — Z3 already decides `P(n) mod m` over
[0,64] today (that *is* the 0-novel quadratic-residue genre), and re-encoding it reintroduces the
per-variable clamping ADR 0030 proved unsound, for zero novelty gain. **We do not build it.**

### Stage A (recommended) — multiplicative-order reduction for symbolic exponents

The sound-and-*active* repair of ADR 0030's inert Tier B. For a modular claim `base^n mod m` with
**constant `base`, constant `m`, and a single bare-variable exponent `n`**:

1. **Detect** by pattern-matching the **`ast.Mod` node** whose left child is `base^n` (a
   Pow-with-variable-exponent). *Not* a naive `ast.Pow` branch — the converter is bottom-up and a
   Pow branch cannot see the enclosing `mod` (challenge finding). `base^n` appearing **outside** a
   `mod m` (e.g. `base^n + k`, or compared directly) is **unbounded** → `PredicateError` → DEFER.
   A **compound** exponent (`base^(n+1)`, `base^(2n)`) → DEFER (ADR 0030 Tier B's rule). A
   **non-constant** base or modulus → DEFER (the order oracle needs constants).
2. **Compute the multiplicative order** `ord_m(base)` = smallest `k>0` with `base^k ≡ 1 (mod m)`,
   by trial over `k = 1..m-1` (cached per `(base, m)`). If `gcd(base, m) ≠ 1`, or no order ≤ a
   named cap `MAX_ORDER` (default 64) is found → `PredicateError` → DEFER.
3. **Encode** `base^n mod m` as an `If`-chain over the **period**:
   `[base^0 mod m, …, base^(ord-1) mod m]` indexed by `n mod ord` — **`ord` arms, not 64**.

**Soundness (exact-or-DEFER).** Once `gcd(base,m)=1`, the sequence `base^k mod m` is *purely*
periodic with period `ord_m(base)` (it lives in the cyclic group `(ℤ/mℤ)*`), so
`{base^k mod m : k ∈ ℤ} = {base^k mod m : k ∈ [0, ord-1]}`. The `If`-chain enumerates the complete
cycle ⇒ UNSAT over the period is genuine UNSAT over all naturals. Every failure mode degrades to
DEFER, never wrong-UNSAT: non-coprime base, order over cap, compound/out-of-mod shape, Z3 timeout
(conclusive-only witness). **The `n=0` arm is pinned explicitly:** `n=0` is a real point in the box
and index 0 of the table is `base^0 mod m = 1 mod m`; the gate searches it. If a claim intends
`n ≥ 1` it must say so in `claim_domain` (the gate honours the domain); getting `n=0` wrong toward a
spurious witness is *safe* (over-rejection → FAIL/DEFER), and a property test pins the `n=0` arm so
it can never suppress a real witness (the only unsafe direction).

**Why active at bound 64 (the exact thing Tier B failed).** Tier B's inertness was structural — a
degree-64 `If`-chain over `base^64` is nonlinear and times out. The order oracle cuts the chain to
the period, which is **3–20 for most bases** (`ord_7(2)=3`, `ord_13(2)=12`) — a short chain over
small residue constants, in Z3's modular sweet spot, solved in milliseconds.

**Honest scope of activation (challenge finding).** Stage A fires **only for single-variable,
constant-base, constant-modulus** `base^n mod m` claims. Multivariate claims (where base or m is
itself a search variable — which ADR 0032's signature machinery supports) cannot run the order
oracle (it needs compile-time constants) → DEFER. So this is a *thin, specific* band, not broad
symbolic-exponent support. It genuinely repairs Tier B's "inert for *all* symbolic exponents," but
only for that slice — stated plainly so the operator expects the right thing.

### Stage B (REJECTED as specified; deferred pending a soundness fix) — recurrence/Pisano residues

The synthesis proposed encoding linear-recurrence sequences (`fib`/`lucas`/`pell`) `mod m` over the
**Pisano period**. The adversarial challenge found this **unsound as written**: a linear recurrence
mod m is *eventually* periodic, not necessarily *purely* periodic — it can have a non-trivial
**pre-period (transient)** before entering the cycle. Indexing by `(n − init_len) mod P` silently
assumes the transient ends at `init_len`; if it extends further, a small-`n` value maps to the
wrong residue and a claim false exactly at a transient index reads as UNSAT → **vacuous PASS → trust
breach**. (Fibonacci/Lucas mod m happen to be purely periodic because the companion matrix has
det = −1, a unit, so the state map is invertible mod m — but the *general* argument does not
establish that; it asserts purity from an eventual-periodicity premise.)

**Decision: do not build Stage B as specified.** Revisit only with one of: (a) restrict the
whitelist to recurrences with a **provably invertible state map mod m** (det of the companion matrix
a unit mod m) *and prove it in the ADR*; or (b) honestly detect `(μ, λ)` (pre-period, cycle) and
DEFER whenever `μ > init_len`. And only if Stage A's blind read justifies the further surface.

### Also rejected

- **Polynomial-period reduction** (3 designs): redundant (Z3 already decides it) + reintroduces
  unsound clamping, for the 0-novel genre. Reject.
- **`divisor_count`** (highest vacuous-PASS surface — a 64-way `If`-chain table; a wrong table =
  wrong-UNSAT) for a textbook-adjacent unlock. Reject.
- **`lcm`**: rides on `gcd`; defer. **`gcd` alone** stays available under ADR 0030's standing
  condition (ship only if a real claim DEFERs for lack of it; its Euclid unroll is sound+active).
- **`quantifier-existential`**: a verbatim-duplicate, mis-titled design that builds no quantifier.
  Reject as vapor.

## 3. Why trust is preserved — and the honest TCB caveat

- **Faithfulness stays mechanical and exact-or-DEFER.** Every new construct is an exact finite
  encoding Z3 decides; no LLM touches the verdict. `gates/faithfulness.py` is unchanged — it calls
  `find_gaming_witness` as today and gets a decisive answer where it previously got a DEFER.
  `tests/test_invariants.py` stays byte-identical (this honours the CLAUDE.md "if you'd have to edit
  test_invariants.py, STOP" rule — we do not).
- **DEFER is never vacuous-PASS.** Every new failure mode (non-coprime base, order over cap,
  out-of-mod or compound exponent, timeout, un-whitelisted shape) raises `PredicateError` → no
  witness → DEFER. The one bug-prone surface (the order oracle) is failure-biased: a too-shallow or
  wrong computation that doesn't satisfy its self-check → DEFER, never a decided UNSAT.
- **The gaming-witness spine is intact.** A false-somewhere claim using the new construct still
  yields a real SAT witness in the box (a per-construct wrong-UNSAT regression verifies this).
- **The honest caveat (challenge finding): this grows the trusted computing base.** The order
  oracle is *new trusted arithmetic* whose output feeds a Z3 encoding the gate trusts. A bug (wrong
  order, short cycle) would be a wrong-UNSAT = vacuous PASS **without tripping `test_invariants.py`**,
  which guards the gate *wiring*, not the encoding's arithmetic. ADR 0030 Tier C named this exactly.
  Mitigations, required before merge: (1) an **exhaustive property test** that the oracle's order
  equals `pow`-derived order for **all `(base, m)` in `[0,64]²`**, with the `n=0` arm pinned;
  (2) a **wrong-UNSAT regression per construct** added to an **invariant-adjacent** suite (not only
  `test_smt_z3_*`); (3) an **adversarial soundness review** (ADR 0021 precedent, ≥3 independent
  lenses) — the bar for anything that can become a PASS. Security surface unchanged (Stage A is an
  `ast.Mod`/`ast.Pow` branch, no new `ast.Call` name; `MAX_NODES` still bounds AST size).

## 4. Honest verdict on the §4 recursion — moves the wall, unproven

ADR 0034 §4 named the trap: the metric and the polynomial-congruence generator share a coordinate
system, so any extension staying polynomial-congruence-shaped is drawer-hopping in the same cabinet.

The honest read, **downgraded from the synthesis after the adversarial pass**:

- Stage A reaches a genre `congruence_signature` returns `None` for (symbolic exponents aren't
  polynomials) — so the metric is **blind** to it. **But metric-blindness is not evidence of
  novelty** — it only means the tripwire stops indexing. Multiplicative order, Mersenne/Fermat
  divisibility, primitive roots are **standard elementary number theory** — a *second textbook
  cabinet* (the cyclic-group one) adjacent to the congruence cabinet. `ord_13(2)=12` is
  Fermat's-little-theorem-flavoured; textbook.
- So the honest claim is **"widening in kind into a genre the current metric can't see," NOT "a
  reach into non-textbook mathematics."** It is *more than fancier steering and less than genuine
  novelty* — the same honest band ADR 0034 drew. The earlier synthesis scored novelty 4/5; the
  defensible score is **2–3**.

**Why it is still worth doing (Stage A only): it is the cheapest *non-redundant* probe of the
deeper question — is the wall the DSL *grammar* or the bounded-Z3 *model* itself?** Stage A fixes
the *sound-but-inert* Tier B (so it is not re-proving what Z3 already decides) and unlocks a genre
the metric is blind to. A **positive** blind read would be the first real evidence the wall is the
grammar and is movable. A **negative** blind read (still 0 novel) is itself a sharp, publishable
result: it confirms the `honest-null` hypothesis that the ceiling is the **bounded-Z3 model**, not
the grammar — i.e. genuine novelty requires leaving bounded-mechanical faithfulness, which trades
against the trust boundary and is out of scope here. Either outcome teaches us something the
signature-distance dashboard cannot.

## 5. Staged plan, success measure, and kill condition

**Reuse the ADR 0034 apparatus.** Success signal = the **operator blind-rated genuine-novelty
fraction** (§5.1 — human, blind to origin, calibrated so QR/divisibility/parity/order **= textbook**
so this can actually fail). The mechanical Stage-0 metric is a **tripwire only**, with a sharpened
second job here: a **rising `None`-signature fraction** among promulgations is the leading indicator
that results are leaving the polynomial-congruence DSL (the intended effect) — necessary, not
sufficient. Persisted `claim_property` + `seed_origin` (already landed) make this measurable.

- **Stage A — multiplicative-order reduction (build first).** ~250–400 LOC in `smt_z3.py` (order
  oracle + cache + period `If`-chain + the `ast.Mod` detection guard) + property/wrong-UNSAT tests
  + the invariant-adjacent regression + adversarial review. **Prompt change to `AUTOFORMALIZE_DSL`
  is deferred until Stage A is validated live** (ADR 0030's lesson: don't invite a genre into the
  prompt before confirming it passes the gate at bound 64).
- **Stage B — recurrence/Pisano (only if Stage A's blind read is non-zero AND the invertibility
  soundness fix from §2 is done).** Larger surface; gated.

**Pre-registered kill condition (mirrors ADR 0034 §5; built to be able to fail):**

> Run a calibration arm with Stage A active (identical pinned config to the 0034 A/B). **Stage A is
> kept as a novelty lever iff** the operator blind-rated genuine-novelty fraction of promulgations
> *using the new construct* exceeds the 0/N baseline by a pre-set margin **AND** those promulgations
> clear the triviality gate at a rate distinguishable from chance. A rightward shift in
> signature-distance is **NOT** a success signal (it shifts on drawer-hopping — §4). A rising
> `None`-signature fraction with **still-zero** blind-novel is the explicit *failure-with-a-finding*:
> it confirms the bounded-Z3 ceiling, Stage A reverts to opt-in/default-off (like ADR 0034's
> mining), and Stage B is not built.

## 6. Consequences

- If approved and Stage A passes its kill condition: the gate certifies a genre it currently DEFERs
  (multiplicative-order / Mersenne-Fermat divisibility), the conjecturer prompt is widened *after*
  live validation, and we have the first evidence the novelty wall is the grammar (movable).
- If Stage A fails the kill condition: we will have *measured* that even leaving the polynomial
  genre for the cyclic-group genre yields no genuine novelty — strong evidence the ceiling is the
  bounded-mechanical-faithfulness **model**, and that genuine novelty is fundamentally in tension
  with the trust boundary. That is a real result for a *Calculemus*, and it bounds further DSL
  investment.
- Either way the trust boundary is unchanged: every new path is exact-or-DEFER, `gates/` and the
  invariant tests untouched, with the new oracle's arithmetic pinned by exhaustive tests + an
  adversarial review and an invariant-adjacent wrong-UNSAT regression.

This ADR, like 0034, ships its own strongest objections (§2 Stage B unsoundness, §3 TCB growth, §4
the downgrade). We do not oversell what we can measure.

## 7. Measured outcome (2026-06-25) — Stage A killed as a novelty lever; the ceiling is the model

Stage A was built (PRs #114 encoding, #115 env-gated prompt + the `SA` run arm) and the calibration
arm ran on the same pinned config as the 0034 A/B (feed `run_date 2026-06-23`, opus + the 3-model
repair panel; `LEIBNIZ_DSL_SYMBOLIC_EXP=1`, mining off).

**Mechanically, Stage A is a clear, sound success — the genre moved:**
- 59 conjectured → 23 promulgated, of which **16 are `base^n % m` symbolic-exponent laws** — a genre
  that DEFERred *entirely* before Stage A (e.g. `2^n % 7 ∈ {1,2,4}`, `7^n % 16 ∈ {1,7,9,15}`,
  `2^n % 15 ∈ {1,2,4,8}`). **0 gamed** among them — the order-reduction encoding let nothing through
  unsoundly, as the §3 review + tests required.
- The Stage-0 signature-coverage tripwire dropped from **100% (arm A) → 30% (SA)**: 16/23
  promulgations are invisible to the polynomial metric because they genuinely **left** that DSL.
  This is the exact leading indicator §5 named.

**On novelty (the actual target) — the kill condition is NOT met.** A blind 4-rater panel
(calibrated so quadratic-residue / divisibility / parity **and multiplicative-order / Fermat /
Mersenne** all count as textbook; blind to arm/origin) scored the 19 distinct SA promulgations
**15 textbook / 4 variant / 0 novel — zero novel votes, every law, every rater** (the 4 "variant"
are whitespace duplicates of textbook entries). The 16 symbolic-exponent laws are standard cyclic
behaviour of `a^n mod m` — provable by a first-year student from the multiplicative order of `a`.

**Verdict & disposition.** Per §5 this is the pre-registered *failure-with-a-finding*: the
`None`-signature fraction rose (genre changed) while blind-novel stayed **0**. **Stage A is killed
as a NOVELTY lever.** It is *already* default-off (the encoding is inert unless
`LEIBNIZ_DSL_SYMBOLIC_EXP` invites the genre, which `main` does not), so no revert is needed; it
stays as a sound, opt-in widening (a yield lever for order-facts) and the record that this genre is
textbook.

**The decisive, triangulated finding.** Two independent levers have now been *measured*, not argued:
ADR 0034 changed the proposal **source** (recall→compute mining) — 2× yield, **0 novel**; ADR 0035
changed the DSL **grammar** (added a whole new sound genre) — coverage 100%→30%, **0 novel**. The
bottleneck is therefore neither the proposer nor the grammar: it is the **bounded-mechanical-
faithfulness model itself**. The trust boundary — promulgate only what is mechanically
faithfulness-checkable over a bounded box *and* auto-provable — caps the daemon at elementary,
textbook mathematics *by construction*. Genuine novelty is in fundamental tension with that boundary;
reaching it would require a faithfulness model that admits claims not bounded-decidable (which
weakens the very guarantee the project exists for), or a different notion of "discovery" than
"a kernel-checked promulgated law." That is the honest frontier, and it is a research question, not
an engineering ticket. Stage B (recurrence/Pisano) is **not built** — it would only re-confirm the
same ceiling in a third genre.

### 7.1 Correction (2026-06-25) — the §7 finding over-generalized; the wall is the *test*, not mechanical trust

An independent five-model external review (Fugu, DeepSeek V4 Pro, Kimi, GLM 5.2, Gemini 3.5 Thinking;
`docs/external-review-novelty-frontier.md`) **unanimously** flagged that §7's phrasing
("the bounded-mechanical-faithfulness model itself … caps the daemon by construction") over-reaches.
The precise, defensible claim — which **supersedes** the "bounded-mechanical faithfulness / the model
itself caps novelty" framing wherever it appears above (§4, §6, §7):

- **The measured result stands.** Leibniz *as built* — a *pointwise, bounded-box* `[0,64]`
  faithfulness linter over a tiny arithmetic DSL, used as the *sole* faithfulness test — is capped at
  elementary/local facts (proved twice, blind-measured).
- **But "bounded-mechanical faithfulness caps novelty" is false as a general law.** Bounded *trust*
  (a small checker) ≠ bounded *domain* (a small evaluation box). A small kernel can check arbitrarily
  deep proofs — four-colour, Kepler/Flyspeck, Feit–Thompson, Robbins (auto-proved, not trivial),
  Boolean-Pythagorean (a vast SAT certificate). The wall is the *pointwise bounded-box linter*, not
  mechanical trust, and not the kernel.
- **The sound escape (→ ADR 0036): proof-carrying faithfulness.** Keep `Q.E.D.` brutally formal, but
  make the faithfulness *earner* a kernel/CAS-checked **certificate** of the statement↔claim
  correspondence — including **exact, unbounded** classes (polynomial-identity / Gröbner). Bounded Z3
  stays as cheap *lint*. The residual 3-body gap then relocates to **validation** (human-intent →
  formalized-claim) — irreducible, but auditable, and the correct place for it. So genuine novelty
  requires leaving the bounded-box *linter*, **not** the trust boundary. (Honest caveat: this removes
  the *expressiveness* ceiling soundly; whether it yields *blind-novel* results is unmeasured and
  must be tested, per ADR 0036's pre-registered kill.)
