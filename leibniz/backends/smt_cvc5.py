"""ADR 0067 — cvc5 cross-solver attestation for the Z3 probe layer.

Every probe verdict in this codebase (cheap refutation's "no counterexample", the gaming spine's
"no witness", ClaimProbe faithfulness) rests on a Z3 ``unsat``. A ``sat`` verdict is self-validating —
the model can be re-evaluated against the predicate — but ``unsat`` is a bare solver claim: single-
solver trust. This module re-decides the SAME query (the exact SMT-LIB2 script Z3 solved, serialized
by ``Solver.to_smt2()``) in **cvc5**, an independently-developed solver (BSD-3; ``pip install cvc5``,
the project's ``cvc5`` extra). Agreement upgrades the verdict's provenance; disagreement is treated as
"one of the solvers is wrong" and the caller DEGRADES the verdict to ``unknown`` — kill-only in every
consumer (a lost refutation, a lost PASS: yield, never soundness).

**Posture (mirrors ADR 0048's cross-kernel tier, at the SMT layer):** this cross-checks the SOLVER'S
verdict on the exact query, not the DSL encoding — the encoding is validated separately by the
conformance suites. Report-only + kill-only: nothing here can create a PASS, mint an edge, or touch
the trust core. Fail-closed: without the ``cvc5`` package (or on any parse/solve surprise) the
re-decision returns ``None`` and the Z3 verdict stands unchanged.
"""
from __future__ import annotations

from dataclasses import dataclass

try:  # the `cvc5` extra — fail-closed to unavailable, exactly like the z3 import above this layer
    import cvc5
except ImportError:  # pragma: no cover
    cvc5 = None


def available() -> bool:
    """True iff the cvc5 python package (the ``cvc5`` extra) is importable."""
    return cvc5 is not None


@dataclass
class Cvc5CrossCheck:
    """Re-decide an SMT-LIB2 script in cvc5. One instance per query (cvc5 solvers are cheap to
    construct and this keeps every re-decision hermetic)."""

    timeout_ms: int = 10_000

    def redecide(self, smt2: str) -> str | None:
        """``'sat' | 'unsat' | 'unknown'`` — or ``None`` when cvc5 is absent or anything about the
        parse/solve surprises us (report-only: a cross-check must never crash a probe)."""
        if cvc5 is None:
            return None
        try:
            tm = cvc5.TermManager()
            slv = cvc5.Solver(tm)
            slv.setOption("produce-models", "false")
            slv.setOption("tlimit-per", str(self.timeout_ms))
            parser = cvc5.InputParser(slv)
            script = smt2 if "set-logic" in smt2 else f"(set-logic ALL)\n{smt2}"
            parser.setStringInput(cvc5.InputLanguage.SMT_LIB_2_6, script, "crosscheck")
            sm = parser.getSymbolManager()
            while True:
                cmd = parser.nextCommand()
                if cmd.isNull():
                    break
                cmd.invoke(slv, sm)
            r = slv.checkSat()
            if r.isSat():
                return "sat"
            if r.isUnsat():
                return "unsat"
            return "unknown"
        except Exception:
            return None
