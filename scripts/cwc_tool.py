"""CWC as the first SandboxedTool (ADR 0041 Phase 2 — unify the FunSearch instance under the seam).

This wires the existing, validated CWC FunSearch pieces into the domain-neutral tool seam, WITHOUT
moving or duplicating the security-critical docker isolation (it stays in scripts/funsearch_sandbox.py)
and WITHOUT admitting CWC to the deciding path. The CWC tool is registered at STATE 1 only:

  - run_fn   = funsearch_sandbox.run_program  (the untrusted-code sandbox; single source of truth)
  - oracle   = verify_cwc (UNTRUSTED validity) + the post-Rosin floor -> a ToolResult
  - PASS only for a valid code that strictly beats the post-Rosin floor (a candidate beat), carrying a
    Certificate whose data is the witness and whose statement is the operator template A(n,d,w) >= M.

The re-checker (a Lean kernel re-check via cwc_check) and the statement template are provided here for
the OPERATOR to register in Phase 6 (State 2) — they are deliberately NOT registered. With no decider
registered, ToolRegistry.run returns DEFER even on a candidate beat (State 1), exactly as intended.

This module lives under scripts/ (not the leibniz/ package) precisely because it depends on scripts/
sandbox + checker code; the package stays dependency-clean.
"""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_ROOT / "scripts"))

import cwc_table_oracle as ora  # noqa: E402
import funsearch_sandbox as fs  # noqa: E402
from funsearch_loop import effective_best_known  # noqa: E402  (post-Rosin floor = max(snapshot, rosin))
from probe_beta_cwc_pilot import verify_cwc  # noqa: E402

from leibniz.tools.protocol import Certificate, Provenance, ToolDescriptor, ToolResult  # noqa: E402
from leibniz.tools.sandbox import SandboxedTool  # noqa: E402
from leibniz.types import Verdict  # noqa: E402

RESULT_KIND = "cwc-construction"

_SNAP = None


def _snap():
    """Load + cache the validated Brouwer snapshot once (effective_best_known needs it)."""
    global _SNAP
    if _SNAP is None:
        _SNAP = ora.load_snapshot()[0]
    return _SNAP


def cwc_statement(n: int, d: int, w: int, m: int) -> str:
    """The operator-owned statement template (E7): the canonical proposition a witness of size m claims.
    Matches the Lean theorem render (`A(n,d,w) >= m`)."""
    return f"A({n},{d},{w}) >= {m}"


def cwc_template(data: dict) -> str:
    """StatementTemplate for Phase-6 registration: recompute the statement FROM the witness data, so a
    tool cannot author it. The size is len(code) — never a tool-supplied number."""
    return cwc_statement(int(data["n"]), int(data["d"]), int(data["w"]), len(data["code"]))


def _run_fn(program_src: str, args: dict):
    """Adapt funsearch_sandbox.run_program (the injected, single-source sandbox) to the SandboxRunner
    shape (ok, code, error)."""
    r = fs.run_program(program_src, int(args["n"]), int(args["d"]), int(args["w"]))
    return (r.ok, r.code, r.error)


def _oracle(args: dict, code) -> ToolResult:
    """UNTRUSTED fitness: verify_cwc validity + post-Rosin floor. PASS (with a witness certificate) only
    for a valid code that strictly beats the floor; else DEFER. Never promulgates; the registry (Phase 6)
    re-checks any PASS with the Lean kernel before it can decide."""
    n, d, w = int(args["n"]), int(args["d"]), int(args["w"])
    if code is None:
        return ToolResult(Verdict.DEFER, "cwc/sandbox", detail={"reason": "no code produced"})
    ok, reason = verify_cwc([frozenset(c) for c in code], n, d, w)
    if not ok:
        return ToolResult(Verdict.DEFER, "cwc/verify", detail={"invalid": reason})
    size = len(code)
    floor = effective_best_known(n, d, w, _snap())   # max(committed snapshot, Rosin 2026)
    if floor is None or size <= floor:
        return ToolResult(Verdict.DEFER, "cwc/verify",
                          detail={"size": size, "floor": floor, "beats": False})
    witness = {"n": n, "d": d, "w": w, "code": [sorted(c) for c in code]}
    cert = Certificate(kind=RESULT_KIND, rechecked=True, data=witness,
                       detail={"statement": cwc_statement(n, d, w, size)})
    return ToolResult(Verdict.PASS, "cwc/sandbox-construct", certificate=cert,
                      detail={"size": size, "floor": floor})


def cwc_tool() -> SandboxedTool:
    """The CWC SandboxedTool (State 1). Register it with ToolRegistry.register_tool(); do NOT register a
    decider for RESULT_KIND unless an operator is performing the Phase-6 admission."""
    return SandboxedTool(
        descriptor=ToolDescriptor(name="cwc-funsearch", provenance=Provenance.SELF_BUILT,
                                  cost_rank=50, result_kind=RESULT_KIND, requires_sandbox=True,
                                  arg_schema={"n": "int", "d": "int", "w": "int"}),
        run_fn=_run_fn, oracle=_oracle)


def cwc_rechecker(cert: Certificate) -> bool:
    """PHASE-6 re-checker (provided, NOT registered). Independently re-derives the claim from the witness
    DATA: re-run verify_cwc, then the Lean kernel (cwc_check) on the witness, and require the
    kernel-accepted witness to strictly beat the post-Rosin floor. Operator registers this in State 2."""
    try:
        from cwc_check import check
        data = cert.data
        n, d, w, code = int(data["n"]), int(data["d"]), int(data["w"]), data["code"]
        if not verify_cwc([frozenset(c) for c in code], n, d, w)[0]:
            return False
        floor = effective_best_known(n, d, w, _snap())
        if floor is None or len(code) <= floor:
            return False
        return check(n, d, w, code, run_kernel=True).get("kernel") == "KERNEL-VERIFIED"
    except Exception:
        return False
