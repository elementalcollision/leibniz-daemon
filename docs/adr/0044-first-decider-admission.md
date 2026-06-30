# ADR 0044 — First decider-admission: a kernel-backed valid-construction decider (Track C / ADR 0041 Phase 6)

- **Status:** PROPOSED — **requires operator sign-off per kind** (ADR 0041 §9 checklist item 5: "Phase 6
  returns for separate sign-off per kind"). **This PR is docs-only: no code, no registration, no
  `trust.py` change.** The two admission edits (below) are operator acts, both PreToolUse-guarded.
- **Date:** 2026-06-30
- **Deciders:** Operator (sign-off required before any State-2 admission or any `trust.py` change).
- **Siblings:** ADR 0041 (the trust model — §2.2 ritual, E1–E8, ATTACK 1/2), ADR 0042 (post-D0 program,
  Track C), ADR 0043 (the covering verifier this decider re-checks). ADR 0013 (trust-edge provenance).
- **Touches the proof edge:** NO. `tests/test_invariants.py` stays byte-identical. The proof edge stays
  Lean-only (E3); this admits a **faithfulness** decider for one finite-witness kind, nothing more.

---

## 1. Context & purpose
Track C of ADR 0042: admit the **first State-2 decider**, "aimed at amplification." The amplification
spine (ADR 0042/0043) verifies externally-supplied constructions through the Lean kernel but is
**audit-tier** — `amplify.py` records kernel verdicts and never promulgates. Decider-admission lets a
**kernel-re-checked construction certificate** become a **MECHANICAL faithfulness PASS** for its kind, so
that — *when amplification candidates flow through the promulgation pipeline's faithfulness gate* — the
gate can DECIDE faithfulness for these finite-witness kinds via a sound kind-specific re-checker instead
of the generic bounded-Z3 lint. It broadens *what the faithfulness gate can soundly decide*; it does not
touch proof or novelty.

**Honest forward-looking note:** today nothing routes amplification certificates into the pipeline's
faithfulness gate, so an admitted decider is **dormant infrastructure** until that integration exists.
The operator may (a) admit now so the seam is ready, or (b) defer admission until the integration lands.
This ADR makes the admission *correct and signed-off*; it does not assert it is *needed today*.

## 2. The first kind — `covering-construction` (generalizes to `cwc-construction`)
- **Witness (`certificate.data`):** `{v, k, t, blocks}` — a finite explicit covering (the ADR 0043
  object); no generators/compression (a cyclic construction must be expanded before the cert is formed).
- **Statement template (E7, operator-owned):** `C(v,k,t) <= len(blocks)` — recomputed FROM the data;
  the size is `len(blocks)`, never a tool-supplied number. The tool supplies witness DATA only.
- **Re-checker (kernel-backed):** re-derive validity by `covering_check.check(v,k,t,blocks,
  run_kernel=True)` and require `kernel == "KERNEL-VERIFIED"` — i.e. the Lean kernel re-checks the
  rendered `validCovering … = true` theorem (completeness of t-subsets is by construction; ADR 0043).

## 3. Why this satisfies the §2.2 ritual (a)–(d) + A6 + E6′/E7/E8
- **(b) thin re-checker over an existing fixed decider (A6 → lighter route).** The re-checker's
  TRUE/FALSE comes from the **Lean kernel** (the existing TCB), with `verify_covering` only as a
  pre-filter. It embodies **no new deciding logic**, so it is a *thin* re-checker (de Bruijn / LCF): it
  takes the lighter (a)–(d) route and does **not** require a kernel-checked soundness proof *of the
  re-checker itself* (which A6 reserves for non-thin re-checkers). The TCB grows by **zero** — the kernel
  was already trusted; only a shim is added.
- **(a) exact-or-DEFER + (d) adversarial soundness review — DEMONSTRATED.** Against a *local, test-only*
  registry with this decider registered (real kernel-backed re-checker, STS(9) C(9,3,2)=12 witness):

  | input | result |
  |---|---|
  | valid witness, honest statement `C(9,3,2) <= 12` | **PASS** (MECHANICAL, `rechecked_by_registry=True`) |
  | E7 laundering — claim a *stronger* bound `<= 11` with the 12-block witness | **DEFER** ("statement not produced by the operator-owned template") |
  | E6 invalid — drop a block (a pair uncovered) | **DEFER** ("independent re-check returned False") |

  The tool cannot claim a tighter bound than `len(blocks)` (E7), and an invalid witness never re-checks
  (E6). The str-subclass laundering path is already sealed in `registry._accept_or_defer` + the sealed
  `test_tool_trust.py`.
- **(c) honest strength tag:** `kernel-grade re-derivation` (the strongest tag; the kernel re-derives).
- **E6′ (axiom/native closure):** `render_covering_lean` emits `:= by decide` — **pure kernel
  reduction**, no `native_decide`, `sorry`, `axiom`, `@[extern]`, or unapproved imports. The Lean
  elaboration runs **inside the docker sandbox** (`LeanCliBackend`), per E6′ (the compiler is attack
  surface, not trusted infra).
- **E8 (held-out eval):** before admission, evaluate the decider's *utility* on a **pre-registered,
  agent-immutable** instance set — valid LJCR coverings it must accept + invalid/laundering inputs it
  must reject — drawn from independent config. Tool-generated cases are admission filters, never
  promotion evidence.

## 4. The TWO operator-gated admission edits (the keystone — both PreToolUse-guarded)
A decider-admission is **not** a single call. ATTACK 2 (sealed in `trust.py`) means a registry PASS
stamps the *tool's* producer, which `validate_edge` **rejects** on a MECHANICAL faithfulness edge. So a
re-checked PASS cannot promulgate until an operator performs **both**:

1. **Register the decider** (operator-only; `leibniz/tools/registry.py` is hook-guarded):
   `registry.register_decider("covering-construction", covering_rechecker, covering_template)` on the
   production registry. *(Until this, every covering PASS is DEFER — State 1.)*
2. **Admit the producer** (operator-only; `leibniz/trust.py` is hook-guarded): the integration that maps
   a registry PASS → a faithfulness `EdgeEvidence` must stamp an **operator-owned producer** for the
   admitted kind (recommended: `"covering/recheck"`), and that exact string is added to
   `FAITHFULNESS_PRODUCERS` in `trust.py`. *(Until this, `TrustPolicy.validate_edge` rejects the edge —
   ATTACK 2.)*

Both edits are deliberate, separate operator acts. Neither is performed in this ADR or by any autonomous
path. **No production code calls `register_decider`; `FAITHFULNESS_PRODUCERS` is unchanged.**

## 5. MONITOR + auto-demote (ADR 0041 §3.3 / A5)
Once admitted, the kind is replayed periodically against the held-out set; on **any** mismatch
(re-check drift, dependency/version drift, axiom-closure regression) the kind **auto-demotes to State 1**
(outputs revert to re-checked-only) and quarantines pending operator review. Demotion DOWN is autonomous
and safe; re-admission UP is operator-only.

## 6. Buildable slice — AFTER sign-off (precise enough to be mechanical)
On operator sign-off, in this order:
1. `scripts/covering_tool.py` — `covering_template`, `covering_rechecker` (the §2 pieces, the
   `cwc_tool.py` pattern), and a covering `SandboxedTool` (State 1). **Not registered.**
2. `tests/test_covering_decider.py` — the (a)/(d) guard test (the §3 table) on a **local** registry,
   sealed under the PreToolUse hook (it asserts the production default stays dormant-empty).
3. The E8 held-out set, pre-registered + committed-hash, agent-immutable.
4. **Operator** performs edits §4.1 + §4.2 and the integration mapping (ToolEvidence → faithfulness edge
   with the operator producer), each with its own review.

## 7. Consequences
- **Trust posture:** the proof edge is untouched (E3); the faithfulness TCB grows by a *thin shim to the
  already-trusted kernel*; both admission edits are operator-gated and reversible (auto-demote).
- **If declined / deferred:** the amplification spine stays audit-tier and fully useful; nothing is lost.
  The design is on the shelf, signed-off-ready, for when amplification feeds the promulgation pipeline.
- **Open question for the operator:** admit now (seam ready, dormant until integration) vs. defer until
  the amplification→pipeline integration exists. This ADR recommends **deferring the two live edits**
  until that integration is scoped, and meanwhile (optionally) landing the §6.1–6.3 *reviewable,
  non-registered* code so the admission is one signed-off step away.
