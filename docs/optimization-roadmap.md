# Optimization Roadmap (post-R6)

The capability ladder R0–R6 is built: the trust boundary is real and the daemon
runs end-to-end live. The remaining work is **making it a productive discovery
engine** without ever weakening the boundary. Each optimization is captured as a
**Proposed** ADR so it can be approved deliberately before implementation (the
project's discipline: decisions get an ADR, and trust-guarded changes get operator
sign-off via the PreToolUse hook).

## The ADRs

| ADR | Decision | Theme | Touches guarded core? |
|---|---|---|---|
| **0009** | Close the KFM → SURVEY feedback loop (re-seed from recombined/proven parents; curiosity + difficulty targeting) | Discovery yield | no |
| **0010** | Expand the faithfulness claim-type probe table (more measurable claims adjudicated mechanically) | Discovery yield / faithfulness | **yes** (gates/faithfulness.py) |
| **0011** | Proving throughput & cost (persistent Lean + REPL; concurrent prover ensemble; cross-cycle cache; USD budget) | Performance / cost | no |
| **0012** | Autoformalization robustness (mechanical import-resolver before LLM repair; prover-output normalization) | Robustness | no |
| **0013** | Trust-edge provenance hardening (EdgeEvidence.producer + mutation tests) | Trust defense-in-depth | **yes** (types.py, trust.py, tests) |

## Priority & sequencing

The mission is *novel, tractable, kernel-proven* theorems — so **discovery yield is
the top priority** (the daemon currently runs but rarely promulgates):

1. **0009 — discovery loop** (highest leverage; turns "runs end-to-end" into
   "learns and promulgates"). No guarded edits.
2. **0012 — autoformalization robustness** (gets candidates past MALFORMED reliably
   and cheaply; enables 0009 to bear fruit). No guarded edits.
3. **0010 — probe expansion** (more claims pass faithfulness *mechanically* rather
   than DEFER). Guarded — operator sign-off; depends on 0004's structured contract.
4. **0011 — throughput & cost** (matters once 0009 produces candidates at volume;
   also the USD cap should land before sustained autonomous runs).
5. **0013 — trust hardening** (orthogonal defense-in-depth; do anytime). Guarded.

Dependencies: 0010 builds on ADR 0004 (structured faithfulness contract). 0011's
budget and 0012's robustness are prerequisites for a *sustained* autonomous run.
0009 + 0012 together are the minimum to demonstrate the R4 exit test
(promulgate ≥1 novel non-trivial theorem with no human on the critical path).

## Success metrics

- **0009/0012:** over N cycles, ≥1 novel, non-trivial theorem promulgated; archive
  coverage grows; promulgation rate trends up across cycles.
- **0010:** fraction of measurable claims adjudicated MECHANICAL (vs DEFER) rises;
  no measurable claim ever promulgated via a judge.
- **0011:** per-candidate wall-clock and $/promulgation fall; a per-cycle USD cap
  is enforced.
- **0013:** a mutation test (flip any edge tier) makes `validate_path` raise; proof
  edges carry discharge provenance.

## Invariant (applies to every ADR)

None of these may weaken the trust boundary. `tests/test_invariants.py` must stay
byte-identical and green; guarded-core changes (0010, 0013) land behind the
PreToolUse hook + CODEOWNERS review; any change that would require editing the
invariant tests to pass is a STOP.
