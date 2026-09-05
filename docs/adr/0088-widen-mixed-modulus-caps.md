# ADR 0088 — Widen the mixed-modulus caps to admit covering systems

- Status: **proposed — measured against live Lean 4.31, not yet landed**
- Date: 2026-09-05
- Depends on: ADR 0060 (the LCM/castHom mixed-modulus procedure this widens), ADR 0056–0059
  (the decision-procedure lineage and the shared residue budget), ADR 0069 / 0083 (the feed
  and the steering that were supposed to surface targets like this one)

## Context

A covering system is a claim of the exact shape ADR 0060 was built for: `∀n. (n%m₁==a₁) ∨ … ∨
(n%mₖ==aₖ)`, one free variable, an or-structure over modular atoms with **distinct** moduli,
decided over `ZMod(lcm)` by `castHom` reduction. Every published covering system has lcm in the
thousands. `MAX_LCM = 64` excluded all of them. The procedure has therefore never once been
pointed at the literature that matches its own fragment.

Two findings sit behind this ADR.

**The feed is blind to this family.** All 18 rows in the live amplification queue are
combinatorial (srg, Latin squares, pseudoline arrangements). Running `finite_core_score` on
arXiv 2607.19029 — a July 2026 math.NT paper squarely inside the sweep window and the fragment —
returns **0**, against `QUEUE_THRESHOLD = 3`. It was fetched and silently dropped. The misses are
all near-misses: the abstract says *"certified by"* where `_SIGNALS` wants `certificate`,
*"minimum modulus"* where the pattern wants `minimum (number|size|order|counterexample)`,
*"complete Gurobi computations"* where it wants `complete (list|enumeration)`. `_SIGNALS` is tuned
for finite combinatorial structures and has no vocabulary for the three arithmetic kernel
procedures the daemon actually built (ADRs 0060, 0065, 0070).

**The fragment fits; only the caps did not.** arXiv 2607.19029 gives an explicit distinct covering
system with minimum modulus 7 and lcm 10080 — 66 congruences, transcribed from the PDF's Section 7
and verified exhaustively before use (moduli distinct, lcm exactly 10080, **0 uncovered residues**).
Its moduli are *exactly* the 66 divisors of 10080 that are ≥ 7; the moduli set is forced, not chosen.

## Decision

Four changes, all measured. None touches a trust edge.

| constant | now | proposed | evidence |
|---|---|---|---|
| `MAX_LCM` (`mixed_modulus_decided.py:69`) | 64 | **20160** | 10080 closes in 16s; measured safe to 100800 (47s); OOM before 262080 |
| mixed residue budget | shares `MAX_RESIDUE_CELLS` = 4096 | **own constant, 20160** | see below |
| `MAX_ATOMS` (`boolean_decided.py:74`) | 8 | **72** | the real system has 66 |
| template `decide` | `by decide` | `by decide +kernel` + three `set_option`s | 5.5× faster; the options are load-bearing |

**The residue budget must not be raised in place.** `MAX_RESIDUE_CELLS` lives in
`lean_decided.py:83` and is shared by the single-modulus, boolean and mixed classifiers, which all
test `modulus ** nvars`. Raising it to 20160 to admit a **1-variable** claim at M=10080 would
silently also admit 2-variable claims at M≈142 and 3-variable at M≈27 for the *other* procedures —
untested cells of a budget that grows as `M^nvars`. The mixed backend gets its own constant; the
shared one stays at 4096.

**`MAX_ATOMS` should be read off the divisor structure, not picked.** A covering system with lcm
`M` and minimum modulus `m` has at most `#{d : d | M, d ≥ m}` congruences. For M=10080, m=7 that is
66 — and the paper's system attains it. 72 is that bound with margin, not a round number.

**The template is missing three options and the wrong `decide`.** Measured at M=10080:

- `set_option maxRecDepth` — without it, `decide` dies at M≈120 with `maximum recursion depth has
  been reached`. **This, not compute, is the wall `MAX_LCM = 64` has been sitting behind.** The
  real ceiling is ~1500× further out.
- `set_option synthInstance.maxSize` / `synthInstance.maxHeartbeats` — without them, 66 nested
  `Or`s fail with `failed to synthesize Decidable`. Instance synthesis, not compute.
- `decide +kernel` instead of `decide` — 6.8s vs 37.5s at 20 atoms.

## Evidence

Live Lean 4.31 (`leibniz-lean:v4.31.0`, Mathlib pinned to v4.31.0), Docker, 15.66 GiB. Every
covering system was verified exhaustively in Python before being handed to the kernel.

| case | atoms | wall | axioms |
|---|---|---|---|
| M=2520, proxy | 18 | 2.9s | clean |
| M=10080, proxy | 20 | 6.5s (full template) | clean |
| M=10080, proxy | 32 | 9.0s (full template) | clean |
| **M=10080, arXiv 2607.19029 §7** | **66** | **16s (full template)** | **clean** |
| M=100800, key line | 25 | 47s | clean |
| M=262080, key line | 33 | OOM (exit 137) | — |

`clean` = `[propext, Classical.choice, Quot.sound]`, no `sorryAx`.

**A proxy is not evidence.** Chain-constructed proxies at 20 and 32 atoms passed and gave a false
sense of headroom. The real 66-atom system **failed** on the first run — `failed to synthesize
Decidable` — and only closed once the `synthInstance` limits were raised. The third required
`set_option` would not have been found without the paper's actual congruence list. Any future cap
widening in this family should be measured on a real instance, not a constructed one.

## Two things the widening broke, found while landing it

**`_content_free` is exponential.** `boolean_decided._content_free` decides non-triviality by
enumerating every truth assignment — `2**len(atoms)`. At the boolean fragment's `MAX_ATOMS = 8`
that is 256 and its docstring calls it "bounded". At 72 it is `2**72`. Raising the atom cap does
not slow the classifier down, it **hangs** it, which is strictly worse than a DEFER: the cycle
stops instead of moving on. The mixed fragment therefore gets its own `_mixed_content_free`:
delegate at `<= MAX_ATOMS` (so nothing that classified before ADR 0088 changes), and above it
admit **only a flat disjunction of modular atoms** — the covering-system shape — where constancy
is exact and O(n), since such a formula is false when every atom is false and true when any one
holds, hence constant iff some atom appears both as `==` and `!=`. Any other large shape is
refused. The guard gets cheaper, not weaker, and the failure direction is closed.

**`MAX_NODES` blocks the target, and is deliberately NOT raised.** `dsl_to_lean._parse` refuses
any predicate over `smt_z3.MAX_NODES = 200` AST nodes. The paper's 66-congruence system is **531
nodes**, so it is refused *before the classifier ever sees it*. Every cap above is a compute
budget on a finite `decide`; this one is not. Its stated job is to bound "recursion on untrusted
input", and `dsl_to_lean` imports it from `smt_z3` precisely so the renderer and the Z3 backend
admit **exactly** the same grammar — a lockstep property the module documents in its own header.
Raising it widens Z3's parse boundary too and relaxes a guard on untrusted LLM output. That is a
different kind of decision from a compute budget and it gets its own ADR and its own adversarial
review; it is not landing on the back of this one.

The consequence is stated plainly: **`MIXED_MAX_ATOMS = 72` is currently unreachable.** `MAX_NODES`
binds first, at **24 congruences** (~8 AST nodes each). The widened `MAX_LCM` is fully reachable and
does real work — a covering system at lcm 2520 with 18 congruences classifies and is 39x the old cap
— but the specific paper that motivated this ADR cannot yet be posed to the daemon in its own DSL.

**The prototype could not have caught this.** It generated Lean directly and handed it to the
kernel, so it exercised the proof template and never once crossed the DSL parse boundary. "The
kernel can check it" and "the daemon can pose it" are different claims, and only the first was
measured. Any future increment in this family should classify through `classify_mixed` before
declaring a fragment reachable.

## The negative controls, including the one that crashes

| control | uncovered residues | result |
|---|---|---|
| perturb `6 (mod 7)` → `5 (mod 7)` | 252 | clean reject: `is false`, `sorryAx`, exit 1 |
| drop `7193 (mod 10080)` | **1** | **`Stack overflow detected. Aborting.`, exit 134** |

The tightest possible negative control — one uncovered residue out of 10080 — **kills the Lean
process** instead of returning a verdict.

**Fail-closed is preserved.** `LeanResult.kernel_ok` requires `returncode == 0`
(`lean_cli.py:112`, read by `kernel_ok` at `lean_cli.py:121`), so exit 134 maps to not-verified ⇒ DEFER. A crash can never be mistaken for a
proof. But at this scale a near-miss conjecture can abort the kernel rather than answer it, and an
unattended 02:30 cycle should expect that. Recorded here so it is a known property, not a 02:30
discovery.

This is also the one concrete argument for the Lean 4.33 bump: PR #13956 bounds kernel type
checking by `maxRecDepth` rather than the physical stack, turning exactly this abort into a
deterministic error. **Deliberately decoupled** — this ADR lands on 4.31, where the result is
already verified end-to-end. Re-validating ADRs 0056–0060, 0065, 0066 and 0070 against a
two-minor-version Mathlib bump is its own ticket with its own regression surface; those templates
are tactic-fragile by their own admission (ADR 0070 records a lemma name that never existed; ADR
0065 records `simpa` failing at reducible transparency).

## Adversarial review

Run before this was called done, per the standing gate. It found two defects in the change as
first written, both now fixed, and both of a kind reasoning had missed.

**1. The cell-budget regression test was vacuous — and pinned the wrong behaviour.** Its negative
case, `(a % 143 == 0) == (b % 143 == 0)`, has ONE distinct modulus, so `classify_mixed` refuses it
at `len(moduli) < 2` and the budget is never reached; the test passed with the budget effectively
removed. Worse, its positive case asserted that a 2-variable claim at M=140 (19600 cells) *was*
admitted — pinning as correct exactly the widening finding 2 says nothing measured.

**2. The widening violated this ADR's own rationale, inside this ADR's own fragment.** The
argument against raising the shared `MAX_RESIDUE_CELLS` is that 20160 would "silently also admit
2-var claims at M≈142 and 3-var at M≈27 — cells nobody measured". A flat `MIXED_MAX_CELLS` did
precisely that here: 2-variable mixed claims went from M ≤ 64 to M ≤ 141, 3-variable from M ≤ 16
to M ≤ 27, while every row of the evidence table above and every motivating covering system is
single-variable. The budget is now `_cell_budget(nvars)`: widened where it was measured, shared
4096 above. Both fixes are mutation-checked — reverting either turns its test red.

**3. A near-miss abort wedges the REPL for the life of the backend** (operational, not soundness).
The fail-closed argument above cites `lean_cli.py`, but production wires `lean_repl`. There,
`_send`'s timeout path tears the process down while its EOF and BrokenPipe paths do not, and
`_start` returned `self._proc` whenever it was non-None with no liveness check. Reproduced with a
simulated exit-134 process: three consecutive `_send` calls all return `None` and the corpse stays
installed. Every later check then reads EOF, returns `None` and DEFERs — silently, with nothing in
the journal — so one aborting candidate costs an entire unattended cycle. Fail-closed throughout,
but only *reachable* because of this ADR: at `MAX_LCM = 64` the decide cannot overflow the kernel
stack. Fixed by a liveness check in `_start`, with tests.

### Recorded, not fixed here

**Non-triviality is propositional, and this fragment is where that stops being the right notion.**
`_mixed_content_free` matches `_content_free` exactly — 2497 flat formulas below the branch point,
400 above it, plus 4000 in a monotonicity diff: zero disagreements, zero cases where the new guard
admits what the old rejects, and zero claims admitted before that are refused now (the change is a
strict widening). But both guards are propositional, so a *padded* covering system passes: the
first four atoms of `(n%4==0) ∨ (n%4==1) ∨ (n%4==2) ∨ (n%4==3) ∨ …` already cover ℤ and the rest is
filler. It is true, so the kernel accepts it, and it would promulgate as a law carrying no content.
Pre-existing in kind; ADR 0088 is what makes the shape reachable at scale. An exact fix is cheap
here — in the flat-Or branch M ≤ 20160, so subset-covering is O(M·k) — but it is a new semantic
guard, not a cap change, and it gets its own ADR.

**`axiom_closure` is fail-OPEN on a silent REPL.** It scans for a `depends on axioms:` line and
never asserts it saw one, so a response of `{"messages": []}` yields `ok: True, axioms: []` — on a
false theorem proved `by sorry`. `_kernel_ok` returns True on the same response. `_env_for`'s canary
already guards the documented coreless-env path, so this is narrower than it first looks, but the
functions are fail-open by construction and `axiom_closure` always appends `#print axioms`, which
always emits on success — so an empty response means something is wrong and should never be a PASS.
Untouched by this ADR and pre-existing, but it sits directly on the trust boundary, so it is the
operator's call, not a fix to smuggle in here.

## Consequences

The mixed-modulus procedure can express covering systems at all: lcm 2520 with 18 congruences now
classifies, against a former ceiling of 64. The construction half of arXiv 2607.19029 is
kernel-checkable in 16s with a clean axiom footprint **when the Lean is generated directly** — it is
not yet reachable through the DSL, which refuses it at `MAX_NODES`. This ADR moves the fragment; it
does not, on its own, deliver the amplification.

**No trust surface.** All four caps bound a `decide` over a finite `ZMod`. `TrustPolicy.validate_path`
and `tests/test_invariants.py` stay byte-identical; the procedure remains exact-or-DEFER behind
`LEIBNIZ_LEAN_DECIDED`; a false formula still makes the `decide` refuse. The kernel decides, and the
measurements above include the negative controls proving it still says no.

**What this does not do:**

- It does not touch the paper's **minimality** claim — that no smaller lcm exists — which rests on
  "complete Gurobi computations", a commercial ILP black box standing where a mechanical checker
  should. That is the more interesting target and it stays far out of reach. Only the construction
  is in scope.
- It does not raise `MAX_NODES`, so the motivating paper stays out of reach and the new atom cap
  stays unreachable. That is the next decision, and it is a guard on untrusted input rather than a
  compute budget, so it wants its own ADR and a skeptic.
- It does not fix the feed. `_SIGNALS` remains blind to the arithmetic families, so the next such
  paper will also score 0. Widening the signal set is proposal-side, touches no gate, and belongs
  in its own change — the ADR 0086 precedent of not letting a consumer ride along on the predicate
  that enables it.
- It does not raise the shared residue budget, so the single-modulus and boolean procedures are
  unaffected and their cells stay as tested.
- It does not, on its own, amplify anything. Formalize → kernel → ADR 0033 publish remains the
  operator's act.
