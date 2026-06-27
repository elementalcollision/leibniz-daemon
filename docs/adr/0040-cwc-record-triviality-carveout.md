# ADR 0040 — CWC record-beating witness: the `decide`-triviality carve-out

**Status:** Proposed (SURFACED, implementation DEFERRED — no genuine record beat exists yet; 0 beats
across the entire autonomous arc). This ADR records the decision and the *safe* implementation shape
so the landmine is documented before it is ever stepped on. **Do not implement until a real beat
exists** and the operator approves.
**Date:** 2026-06-27
**Predecessors:** ADR 0025 (the triviality set `DEFAULT_TRIVIAL_TACTICS`; why `decide`/`ring` are in
it), ADR 0037/0038/0039 (the sound-backend / non-Q.E.D. tier precedents). Decision input: the Probe β
record-factory arc (`docs/probe-beta-result-finding.md`,
`docs/autonomous-discovery-arc-capstone.md`) and the continuation-strategy workflow (Option E build).
**Trust boundary:** this ADR changes NOTHING yet. The carve-out it describes, *when implemented*, must
leave `tests/test_invariants.py` byte-identical, must NOT touch `LeanVerifier.discharge` (the sole
`kernel_verified` writer), and must keep novelty an automated-oracle decision (invariant 4). It is a
quarantine-RELEASE / FAIL-only policy refinement, never a new promotion path.

---

## 1. The landmine

A constant-weight-code lower bound `A(n,d,w) ≥ M` is proved by exhibiting a witness code and checking
it: `validCWC <code> n d w M = true`, closed by `by decide` (the witness IS the proof; core Lean, no
Mathlib — see `scripts/probe_beta_cwc_pilot.py::render_cwc_lean` and the committed
`lean-project/CwcFanoWitness.lean`). This is genuinely Q.E.D. — the kernel accepts it.

But `decide` is in `DEFAULT_TRIVIAL_TACTICS` (`leibniz/backends/lean_cli.py:49`). The promulgation
pipeline runs a non-triviality gate FIRST (`leibniz/gates/novelty.py:50` →
`LeanVerifier.is_trivial` → `backend.closed_by_decision_procedure`): **any statement a single trivial
tactic closes on its own is quarantined `FinishReason.TRIVIAL`.** So a record-*beating* CWC witness —
the exact thing we would want to promulgate — would be thrown out as "trivially closed," indistinguishable
from the vacuous `ring`-identities that gate exists to catch (ADR 0025).

This is correct behaviour *today* (a `decide`-closed arithmetic identity usually IS vacuous), and it has
never bitten us because **the arc produced 0 beats**. It would bite the moment a genuine beat appears.

## 2. The decision

A `decide`-closed CWC witness theorem is **non-trivial iff it beats the table-of-record.** The
criterion already exists, unused, at `scripts/probe_beta_search.py:113`:

```python
def record_is_nontrivial(n, d, w, found, snap=None) -> bool:
    return ora.is_improvement(n, d, w, found, snap)   # found > best_known(n,d,w)
```

The carve-out: when (and only when) the quarantined statement is a CWC witness whose size strictly
exceeds the automated Brouwer oracle's `best_known`, the triviality gate RELEASES it (does not
quarantine) so it can proceed to the proof edge. Everything else `decide` closes stays quarantined.

**We adopt the decision but defer the wiring.** Surfacing it now (this ADR + the standalone audit CLI
`scripts/cwc_check.py`, which already prints "BEATS record — NOT auto-promulgated; needs the ADR 0040
carve-out") means a future beat is recognized, not silently lost. Implementing it now would be a
trust-edge change with no live justification.

## 3. The safe implementation shape (when a beat exists)

When the trigger fires (a verified, oracle-confirmed beat), implement exactly this and no more:

1. **Release, never certify.** The carve-out only converts a TRIVIAL quarantine into "proceed to the
   proof edge." It does NOT set `kernel_verified`, does NOT mark `promulgated`, does NOT call
   `TrustPolicy.validate_path`. The kernel via `LeanVerifier.discharge` still independently re-checks
   the proof and remains the sole arbiter; the policy still gates promotion. The carve-out is a
   FAIL-only-style filter run in reverse: it can only *withhold a quarantine*, never *add an approval*.
2. **Novelty stays the oracle.** "Beats the record" is decided by `cwc_table_oracle.is_improvement`
   against the committed snapshot — an automated retrieval + comparison, never an LLM judge
   (invariant 4). The carve-out reads the same oracle; it introduces no new judgment.
3. **Scope it to the CWC claim genre.** Gate the carve-out on the statement actually being a
   `validCWC … = true` witness (by claim-contract / structural shape), so it cannot accidentally
   un-quarantine an unrelated `decide`-closed vacuity. A generic "decide is fine if some oracle says
   so" would re-open the ADR 0025 hole.
4. **`tests/test_invariants.py` byte-identical.** The triviality criterion lives in
   `lean_cli.py` / the novelty gate, NOT in the invariants file — so byte-identity is necessary but
   **not sufficient**. Add dedicated tests in the gate's own suite covering: a beat is released, a
   non-beat `decide`-vacuity stays quarantined, and a released beat still goes through `discharge`
   (kernel re-check) and `validate_path` before any promulgation.
5. **The snapshot must be current at decision time.** A beat is only genuine against an up-to-date
   table-of-record. Rosin 2026 (arXiv 2603.00174) reports 24 improved CWC lower bounds; whether the
   committed snapshot already reflects those specific values is **unverified** and must be confirmed
   for the target cells before any beat is claimed. The oracle refresh + Rosin cross-check is a
   precondition of *claiming* a beat — tracked in the FunSearch decision package, not bypassed here.

## 4. The circularity trap (how NOT to validate this)

The carve-out **cannot be validated by reproducing a published record.** If the oracle is refreshed to
include the record, reproducing it yields `found == best_known` (a MATCH — `is_improvement` is False,
carve-out never fires). If the oracle is stale, reproducing it yields a *false* "beat" — exercising the
carve-out on fake novelty, which is worse than not testing it. Therefore the carve-out must be exercised
by a **synthetic unit test**: a witness of size `M` against a deliberately-lowered oracle entry `M-1`,
asserting (a) the gate releases it, and a non-beating `decide`-vacuity is still quarantined. Never wire
the test to a real run.

## 5. Status / trigger

- **Now:** documented; the audit CLI flags a hypothetical beat; nothing in the pipeline changed.
- **Implement when:** a search run (e.g. the gated FunSearch pilot — see
  `docs/funsearch-decision-package.md`) produces a verified witness that the *current* oracle confirms
  beats the record, AND the operator approves the trust-edge change.
- **On implement:** land the §3 shape with the §4 synthetic test, its own ADR status bump to Accepted,
  and operator sign-off via the PreToolUse trust hook.
