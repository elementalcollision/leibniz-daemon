<!--
Soak / test / evaluate report for the post-ADR-approval build (seal + B2 framework + C scaffolding).
No trust-boundary change. test_invariants.py byte-identical.
-->

# Evaluation report — B2 framework + C scaffolding (2026-06-30)

After the operator approved ADRs 0044/0045 and directed "build out the framework for B2 and C, then
soak, test, evaluate." This records the soak/test/evaluate of what was built (the seal, the B2 framework,
the C non-trust scaffolding). **All green; the corrected ADR 0045 construction flow is sound end-to-end;
the trust boundary is untouched.**

## What was built (this arc)
- **Seal** (#193): `tests/test_covering_decider.py` is now PreToolUse-protected (operator-authorized).
- **B2 framework** (#194): `ramsey_verify.py` (untrusted VT-reduced checker + tractability-capped `decide`
  render) + the **kernel-`decide` wall finding** — frontier Ramsey needs a certificate architecture, not
  `decide` (`docs/gate-b2-ramsey-decide-wall-finding.md`).
- **C scaffolding** (#195): `construction_intake.py` — locked preludes (byte-pinned to the verifiers),
  the `theorem_structural_guard`, and `canonical_claim` (the tri-edge binding source).

## Test
- **Full suite:** `797 passed, 8 deselected` (docker/live), `tests/test_invariants.py` byte-identical.
- **Kernel lane** (`scripts/run_kernel_tests.sh`): 12 passed — render→kernel both directions, both domains.
- **Ramsey:** 7 passed incl. the C₅ render kernel-verified.

## Soak — construction-intake end-to-end (real Lean kernel), corrected ADR 0045 flow
| step | result |
|---|---|
| `canonical_claim` binds to the witness | `C(9,3,2) <= 12`, size=12 (from the witness, not tool-supplied) |
| structural guard: theorem-only **accepts**, self-contained blob **rejects** | ✅ (forces prelude-separate — review CRITICAL #1) |
| LOCKED prelude + theorem-only == the verified render → kernel | ✅ **True** |
| oracle novelty (equals record) | not an improvement → would **quarantine-not-novel** (no false promulgation) |
| E7 laundering (claim `<=11` with the 12-block witness) | **rejected** (canonical recomputes `<=12`) |
| false witness (block dropped) → kernel | **False** (kernel is the backstop) |

**Every negative control fails closed.** A valid construction verifies + binds + is correctly judged
not-novel; a laundered statement, a false witness, and the def-smuggling blob are all rejected. The
corrected design is sound on the real kernel.

## Evaluate — disposition
- The **frameworks + scaffolding are built, tested, and sound**; the audit-tier construction path
  (verify → kernel → oracle, no promulgation) works end-to-end and never produces a false verdict.
- The **B2 kernel-`decide` wall** redirects Ramsey: its sound verifier is gated on a certificate
  architecture (a separate, heavier build), so B2 ships at the toy regime + the untrusted checker.
- The **C live-promulgation wiring** (the `discharge` construction branch + the `trust.py` producer) is
  the remaining piece — it touches the *sole* `kernel_verified` writer and forces a trust-core
  architecture decision, and its payoff is contingent on a record beat that does not exist on reachable
  cells. It is therefore brought to the operator as an explicit decision (proceed now vs. defer until a
  beat is plausible), rather than performed at the tail of this build. See the checkpoint.
