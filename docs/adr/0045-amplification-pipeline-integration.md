# ADR 0045 — Amplification → promulgation pipeline integration (Track C continuation)

- **Status:** PROPOSED — **design only; requires operator sign-off + a witness round before any build.**
  An adversarial soundness review (§9) found the FIRST draft **unsound** (3 CRITICAL/HIGH paths to a
  false/unwarranted promulgation). The architecture below is the **corrected** design; one of its
  must-fixes (the oracle snapshot validation) is *already landed* in this PR. This PR is otherwise
  docs-only; the build touches the faithfulness wiring, `trust.py`, and ADR 0040 — all operator-gated.
- **Date:** 2026-06-30
- **Deciders:** Operator (sign-off + the trust-edit gates in §5).
- **Siblings:** ADR 0044 (the decider), ADR 0037 (faithfulness sound-backend seam), ADR 0040 (record-beat
  triviality carve-out), ADR 0041 (trust model — E7, ATTACK 2), ADR 0042/0043 (amplification spine),
  ADR 0008/0033 (publish gate).
- **Touches the proof edge:** NO. Proof stays Lean-only via `LeanVerifier.discharge` (inv 1/7, E3).
  `tests/test_invariants.py` byte-identical.

---

## 1. Why — make the amplification spine non-dormant
ADR 0044's decider is dormant: nothing routes amplification certificates into the promulgation pipeline.
This scopes that route — an externally-supplied **construction** (a CWC/covering witness) becomes a
`Propositio` flowing `→ DEMONSTRATE → PROMULGATE`, so a genuine **record-beating** construction would
promulgate soundly, and every verified construction earns a proper `Propositio` (quarantined-not-novel,
never deleted — inv 6).

**Forward-looking honesty:** D0 + the exact-producer escalation proved the reachable CWC/covering records
**optimal** — no beats exist to promulgate today. Promulgation payoff is contingent on a future beat;
present value is first-class sound `Propositio`s for verified constructions. Build when that payoff is
wanted; it is correct either way.

## 2. The corrected core — three edges, ONE bound statement
The keystone the review exposed: in the first draft the three edges could each attest a *different*
statement. The corrected design pins a **single canonical tuple `(domain, n/v, d/k, w/t, size)`** derived
**from the kernel-verified theorem**, and every edge is computed against that one statement. No edge may
attest anything other than what the kernel proved.

### 2.1 Mechanical triad with a LOCKED, operator-owned Lean prelude  *(fixes CRITICAL #1/#2)*
A construction is given, so its triad is rendered mechanically — but the helper definitions
(`combs`, `validCovering`, …) that give the theorem its meaning **must never travel inside the
witness-influenced statement string** (a hollowed `def validCovering _ := true` would make `by decide`
stamp Q.E.D. on `C(9,3,2) ≤ 1`). Therefore:
- the helpers become a **committed, version-pinned trusted library module** — `CoveringPrelude.lean` /
  `CwcPrelude.lean` — imported by **module name** into `Expressio.imports`. The witness can never supply
  or edit it.
- `Expressio.theorem_src` is **only** `theorem <name> : validCovering [<witness literals>] v k t B = true`
  — **no `def`/`axiom`/`macro`/`notation`/`set_option`/`instance`/`@[…]`, exactly one top-level theorem,
  exactly one `:=`** (so `discharge`'s `_join_proof`, which splits on the first `:=`, behaves; the
  self-contained-blob route `check_source` warns against is NOT used).
- a strict **structural guard** in intake rejects any `theorem_src` outside that shape;
- `Demonstratio.proof_src = by decide`.

### 2.2 PROOF edge — discharge, bound to THIS theorem
`LeanVerifier.discharge(expressio, demonstratio)` kernel-checks the theorem with the locked prelude
imported; `kernel_verified` set only here (inv 1/7). **Hardening (fixes CRITICAL #2):** for the
construction genre, discharge must confirm the kernel elaborated a declaration whose **name == the
expected theorem name** (the `__leibniz_candidate__` technique `normalize_statement` already uses), so the
proof is bound to *this* statement, not a silently-substituted one. E6′: no `native_decide`/`sorry`/
`axiom` (prelude is operator-owned; the structural guard bans them in `theorem_src`).

### 2.3 FAITHFULNESS edge — via the E7-enforcing path, cross-bound to the proof  *(fixes CRITICAL #3)*
The review found `FaithfulnessGate.recheckers` has **no** statement/template (E7) check — that guard lives
only in `ToolRegistry._accept_or_defer` (type-pinned builtin-`str` + byte-identical `template(data)`).
The first draft's claim of "identical guard logic" was false. Corrected:
- construction certificates are decided through **`ToolRegistry._accept_or_defer`** (E1/E6/E7 enforced),
  not the bare `recheckers` seam; the resulting MECHANICAL faithfulness edge carries the
  **operator-admitted producer** (§5);
- **cross-bind:** the `(v,k,t,size)` the faithfulness re-checker validates MUST equal the `(v,k,t,size)`
  parsed from the **kernel-verified `theorem_src`** (the re-checker is handed only the certificate, so the
  intake performs this bind; a faithfulness PASS whose tuple ≠ the proved tuple is rejected).
- `Certificate.rechecked` is advisory only (the gate re-derives; never trust the flag — already the
  registry's posture).

### 2.4 NOVELTY edge — validated oracle, tuple bound to the proof, carve-out RELEASE-only
- novelty PASS **iff** `is_improvement` on the `(v,k,t,size)` **parsed from the kernel-verified theorem**
  (not the cert independently); equals/below → FAIL → quarantine not-novel (inv 6).
- the oracle is now **snapshot-validated** (ground-truth anchors + Schönheim floor + RAISE) — **landed in
  this PR** (`covering_table_oracle.py`); fixes must-fix #4 (a stale/mis-parsed cell could otherwise
  promulgate a non-record).
- the **ADR 0040 carve-out is RELEASE-only**: it converts a `TRIVIAL` quarantine into *proceed*; it
  **never sets NOVELTY=PASS**. It needs a **covering-side structural gate** (ADR 0040 is written for the
  CWC `validCWC … = true` shape; the covering shape must be added before the carve-out applies to it).

## 3. The path is opt-in + instance-gated
A separate `ConstructionIntake` (PROD-only, like the publish gate), parallel to audit-tier `amplify.py`.
The default LLM loop is untouched.

## 4. Soundness — per invariant (corrected wiring)
- **inv 1/7:** PROOF = `discharge` only, bound to the named theorem; locked prelude means the kernel
  checks the *operator's* `validCovering`, not the witness's.
- **inv 3/E3:** no tool/backend is `KERNEL_PRODUCER`; faithfulness earns only a faithfulness edge.
- **inv 4:** novelty = the validated public-table oracle (decision procedure), never a judge.
- **inv 6:** verified-but-not-novel → quarantined with a reason, retained.
- **E7:** statement + renderer + prelude operator-owned; the witness supplies block/codeword **literals**
  only; the faithfulness decision runs through the E7-enforcing registry path.
- **tri-edge bind:** one `(v,k,t,size)` from the kernel-verified theorem drives all three edges — no edge
  can attest a statement the kernel did not prove.
- **untrusted surface = the witness literals.** A false construction fails the kernel (PROOF) or the
  re-checker (FAITHFULNESS); a non-beat fails the oracle (NOVELTY); a laundered/hollowed statement fails
  the structural guard + E7 + the name-bind. No path from untrusted literals to a false promulgated law.

## 5. Operator-only trust edits (each its own gate; none performed here)
1. Commit the **locked prelude** module(s) + the structural guard.
2. Build `ConstructionIntake` + the **tri-edge binding** + the construction-novelty path.
3. **Admit the producer** in `trust.py` `FAITHFULNESS_PRODUCERS` — **gated on the statement-binding fix
   landing first** (admitting it before the bind would harden the wrong half).
4. **Activate the ADR 0040 carve-out** for the covering kind (add the covering structural gate; keep it
   release-only).

## 6. Buildable slices — AFTER sign-off + witness round
1. ✅ **DONE in this PR:** covering oracle snapshot validation (anchors + Schönheim floor + RAISE) + tests
   (must-fix #4 — a real defect in shipping code, fixed independently of the rest).
2. The locked prelude module(s) + the strict structural guard + the discharge name-bind. Tests incl. a
   *hollowed-def*, a *multi-`:=`*, and a *wrong-name* source all FAILING to earn a proof edge.
3. `ConstructionIntake` (witness → `Propositio`, tri-edge bind) + the construction-novelty path +
   carve-out activation (release-only, covering structural gate). Tests incl. *false-beat*, *non-beat*,
   *stale-oracle*, *laundered-statement* all failing to promulgate.
4. The faithfulness decision through `ToolRegistry._accept_or_defer` + the operator producer admission.

## 7. Recommendation
Promulgation payoff is contingent on a beat that does not exist on reachable cells, **and** the review
showed the integration is subtle enough to be unsound if rushed. So: **scope now (this ADR), build only
when a beat is plausible**, and route the build through a **witness round** like ADR 0041. This ADR is now
*designed and adversarially hardened*; it does not assert it should be built today.

## 8. Status of the must-fixes
- #4 oracle validation — ✅ landed (this PR).
- #1 locked prelude / no defs in `theorem_src` — folded into §2.1 (build item).
- #2 discharge name-bind / one-`:=` — folded into §2.1/§2.2 (build item).
- #3 E7-enforcing faithfulness + tri-edge bind — folded into §2.3 (build item).
- carve-out release-only + covering structural gate — folded into §2.4 (build item).

## 9. Adversarial soundness review (folded in)
A 3-vector adversarial review (proof-edge, faithfulness, novelty/ADR-0040), reading the real code,
returned **`design_is_sound: False`** on the first draft, with concrete exploits:
- **CRITICAL** — no carrier for the helper `def`s except `theorem_src`; a hollowed `validCovering`
  makes `by decide` stamp Q.E.D. on a false bound. → §2.1 locked prelude + structural guard.
- **HIGH** — `discharge`'s `_join_proof` splits on the first `:=` (inside a helper `def`), silently
  dropping/rewriting the real theorem (the code's own docstring forbids this route). → §2.1 (one `:=`) +
  §2.2 name-bind.
- **CRITICAL** — `FaithfulnessGate.recheckers` has no E7 statement bind; proof and faithfulness could
  attest different theorems. → §2.3 route via `ToolRegistry._accept_or_defer` + tri-edge bind.
- **HIGH** — `covering_table_oracle` had no snapshot validation; a stale/mis-parsed cell promulgates a
  non-record. → §2.4 / fixed in this PR.
Every must-fix is now reflected in the design above; the live risk stayed fully contained (design-only,
operator-gated). Full findings: the run's transcript; provenance recorded here.
