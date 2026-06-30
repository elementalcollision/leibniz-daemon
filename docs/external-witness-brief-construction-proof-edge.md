<!--
External-witness brief: the construction PROOF-EDGE / discharge trusted-surface expansion (ADR 0044/0045
implementation). Composed 2026-06-30. An internal 4-vector adversarial pass found the FIRST sketch
UNSOUND (2 CRITICALs, demonstrated false-Q.E.D.); this brief reviews the HARDENED design + those findings.
Advisory only (invariant 4). The discharge edit is HELD until this round is reconciled.
-->

# External-witness brief — the construction PROOF-EDGE (hardened after an internal CRITICAL)

**Status:** composed 2026-06-30 for the 7-model witness round. **Advisory only** — a human approves; no
model's verdict is binding (invariant 4). **The `discharge` edit is on hold.**

**Why now:** implementing the construction PROOF edge (ADR 0044/0045) means editing
`LeanVerifier.discharge` — the *sole* place `kernel_verified` is set — and **expanding the kernel's
trusted surface**. An internal adversarial pass against the first sketch returned **`sound: False`**, with
two CRITICALs **confirmed against the real Lean 4.31 kernel**. The design below is the *hardened* version;
we want external eyes on it before the edit.

## Internal adversarial findings (the first sketch — DO NOT implement that version)
1. **CRITICAL — axiom injection through a denylist guard.** The guard was a *denylist* (ban `def`/`axiom`/
   `sorry`/…); it admits `run_cmd`/`elab`/`macro_rules`/`inductive`/`attribute`/`namespace`/… A remainder
   `run_cmd … addDecl (axiom cheatAx <false stmt>)` + `theorem … := cheatAx` passes the guard, and with any
   `import` present the kernel **stamps `kernel_verified=True` on a FALSE bound** (demonstrated: C(4,2,2)≤1).
   A plain axiom isn't `sorry`, so the sorry-check misses it.
2. **CRITICAL — no tri-edge binding.** A bare-bool `discharge_construction` proves whatever literals are in
   `theorem_src` and never binds the proved `(v,k,t,size)` to the witness's `canonical_claim` — a
   true-but-different theorem launders a non-record into a Q.E.D. proof edge bound to another cell.
3. **HIGH — routing by `theorem_src` bytes** (`is_construction` = prefix match) overloads the *shared*
   `discharge`; a proposer-controlled prefix reroutes a normal candidate into the construction branch
   (which ignores `proof_src`); prelude drift / a leading `import` misroutes a real construction out.
4. **HIGH — no parameter-domain guard.** Degenerate cells (`t>v`, `w=0`, …) make `validCovering`/`validCWC`
   **vacuously** true, so `by decide` legitimately stamps a meaningless "bound."
5. Plus: the proof term isn't pinned to `by decide`; `is_trivial`→`_join_proof` corrupts the
   multi-declaration source; the kernel verdict's `"error:"`-substring check is fragile.

## The HARDENED design (what the panel should attack)
- **Explicit typed genre, not byte-detection.** A construction is marked by an explicit
  `Demonstratio`/`Expressio` construction field set **only** inside the operator-gated `ConstructionIntake`;
  `discharge` branches on that flag (still the *sole* `kernel_verified` writer — same method, no second
  writer). A normal candidate can never be misrouted in, nor a construction out.
- **Allowlist parse, not denylist.** After the locked prelude, the remainder must match **exactly**
  `theorem <ident> : (validCovering|validCWC) <literals> = true := by decide` and nothing else — reject any
  other token/declaration/metaprogram. Equivalently, assert via an `Environment` diff that the source adds
  **exactly one** declaration (a `theorem`) and the proof is exactly `by decide`.
- **Axiom-closure check (E6′).** After `check_source` passes, require the discharged theorem's axiom set
  (`#print axioms` / `collectAxioms`) to be **empty** (no `sorryAx`, no injected axiom) — quarantine
  otherwise. Defense-in-depth that catches axiom injection regardless of how it entered.
- **Import-free construction source.** The locked prelude is the literal byte-0 prefix; constructions never
  go through `Expressio.imports`; assert no leading `import` (removes the metaprogramming capability).
- **Tri-edge binding.** `discharge_construction` is handed the witness, **parses `(params,size)` from the
  kernel-verified `theorem_src`, and returns False unless it equals `canonical_claim(witness)`** — so
  proof, faithfulness, and novelty attest the *same* cell.
- **Parameter-domain guard in `canonical_claim`.** Reject (don't render) degenerate cells: covering
  `1≤t≤k≤v ∧ B==len(blocks)`; CWC `1≤w≤n ∧ 0<d≤2w ∧ M==len(code)`.

## The standing design delta (also for the panel)
ADR 0045 specified the prelude as a Lean **library module imported by name** (theorem-only source). That
needs a change to the operator-built Lean **docker image** (no in-repo Dockerfile), so we use an
**inlined** locked prelude verified via `check_source`. Is the inlined-prelude-with-allowlist-parse +
axiom-closure acceptable, or must it be the in-image module?

## The prompt (verbatim to each of the 7 witnesses)
> You are advising on the single most consequential trust change in **Leibniz** (LLMs PROPOSE; only the
> Lean kernel / Z3 / table-oracles DECIDE; `kernel_verified` is set in exactly one function,
> `LeanVerifier.discharge`; today the kernel sees one self-contained declaration). We want **constructions**
> (a code witnessing `A(n,d,w)≥M`, a design witnessing `C(v,k,t)≤B`) to earn a real PROOF edge so a genuine
> *record beat* can promulgate. Doing so expands the kernel's trusted surface to **a LOCKED operator-owned
> prelude (helper defs) + one theorem**. An internal adversarial pass found our first sketch UNSOUND (two
> CRITICALs, confirmed on the real kernel: a denylist guard let `run_cmd` inject an axiom that stamped a
> FALSE bound; and the proof edge wasn't bound to the witness's claimed cell). The HARDENED design uses: an
> explicit typed construction genre (not byte-detection) branched inside the sole-writer `discharge`; an
> ALLOWLIST parse (exactly `theorem … : validCovering/validCWC <lits> = true := by decide`, one declaration
> via Environment-diff); an axiom-closure check (axiom set must be empty); an import-free source (locked
> prelude byte-0); a tri-edge bind (parsed params == canonical_claim); and a parameter-domain guard.
> **Answer, structured:**
> 1. Attack the HARDENED design: the strongest remaining path to a false `kernel_verified=True`. Is the
>    allowlist-parse + Environment-diff-one-declaration + empty-axiom-closure + import-free set
>    **sufficient**, or what's missing?
> 2. Inlined locked prelude (+ allowlist + axiom-closure) vs an in-image library module (theorem-only
>    source). Your bright line.
> 3. Is an explicit typed construction genre the right call (it touches the trust-core `Propositio` types),
>    vs any byte/shape detection?
> 4. Is the tri-edge bind (parse params from the kernel-verified theorem == canonical_claim) the right
>    place + sufficient to stop a true-but-different-cell laundering?
> 5. **Should we do this at all now?** The promulgation payoff is contingent on a record beat that our
>    measurements show does NOT exist on reachable cells — so this is **dormant** trust-core surgery today.
>    Greenlight, or keep constructions audit-tier until a beat is in hand? Your condition.
> 6. One contrarian warning.
> Be concrete, cite mechanisms; hold the soundness line absolutely.

**Disposition:** the operator runs the 7 responses, an adversarial synthesis folds in surviving guidance,
and only then is the (hardened) `discharge` edit implemented — or deferred. Until then the edit is HELD;
no construction earns a proof edge.
