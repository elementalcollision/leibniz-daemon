"""Covering-design decider pieces for the first State-2 admission (ADR 0044 / Track C) — NOT REGISTERED.

This provides the OPERATOR-OWNED statement template and the kernel-backed re-checker that an operator
would bind via `ToolRegistry.register_decider("covering-construction", covering_rechecker,
covering_template)` to admit the covering kind to the DECIDING path (State 2). Mirrors the Phase-6 CWC
pieces in `cwc_tool.py`: they are provided for the operator, deliberately **NOT registered** here.

Admission is TWO operator-gated, PreToolUse-guarded edits (ADR 0044 §4), NEITHER performed here:
  1. `register_decider(...)` on the production registry; and
  2. admitting an operator-owned producer (e.g. "covering/recheck") into `trust.py` FAITHFULNESS_PRODUCERS
     (ATTACK 2: a registry PASS stamps the tool's producer, which `validate_edge` rejects).
With no registration, `ToolRegistry.run` returns DEFER on any covering certificate (State 1) — exactly
as intended. No SandboxedTool is provided: there is no untrusted-code covering producer (no covering
FunSearch); the decider re-checks externally-supplied / separately-produced coverings.

The re-checker is THIN over the Lean kernel (ADR 0044 §3 / ADR 0041 A6): its True/False comes from
`covering_check.check(..., run_kernel=True)` (render `validCovering … = true` -> kernel `decide`), so the
TCB grows by zero and `verify_covering` is only a pre-filter. This is a VALID-CONSTRUCTION decider (any
kernel-verified covering of the claimed size), not a record-beat gate.
"""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_ROOT / "scripts"))

from leibniz.tools.protocol import Certificate  # noqa: E402

RESULT_KIND = "covering-construction"


def covering_statement(v: int, k: int, t: int, b: int) -> str:
    """The canonical proposition a covering of size b claims: C(v,k,t) <= b (matches render_covering_lean)."""
    return f"C({v},{k},{t}) <= {b}"


def covering_template(data: dict) -> str:
    """Operator-owned StatementTemplate (E7): recompute the statement FROM the witness data. The size is
    len(blocks) — never a tool-supplied number, so a tool cannot author a tighter bound than its witness."""
    return covering_statement(int(data["v"]), int(data["k"]), int(data["t"]), len(data["blocks"]))


def covering_certificate(v: int, k: int, t: int, blocks) -> Certificate:
    """Build a covering-construction certificate from a witness (statement via the operator template)."""
    data = {"v": int(v), "k": int(k), "t": int(t), "blocks": [sorted(int(x) for x in b) for b in blocks]}
    return Certificate(kind=RESULT_KIND, rechecked=True, data=data,
                       detail={"statement": covering_template(data)})


def covering_rechecker(cert: Certificate) -> bool:
    """PHASE-6 re-checker (provided, NOT registered). Independently re-derives the claim from the witness
    DATA: render the core-Lean `validCovering` theorem and require the Lean kernel to accept it
    (completeness of t-subsets is by construction; ADR 0043). Kernel-grade re-derivation; thin over the
    kernel. Operator binds this in State 2 only after the ADR 0044 ritual + sign-off."""
    try:
        from covering_check import check
        d = cert.data
        v, k, t, blocks = int(d["v"]), int(d["k"]), int(d["t"]), d["blocks"]
        return check(v, k, t, blocks, run_kernel=True).get("kernel") == "KERNEL-VERIFIED"
    except Exception:
        return False
