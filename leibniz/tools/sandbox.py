"""SandboxedTool — a Tool whose proposer runs untrusted code in an isolated sandbox (ADR 0041 Phase 2).

This is the domain-neutral generalization of the FunSearch loop: an untrusted program runs in isolation,
its (untrusted) output is turned into a `ToolResult` by a pluggable oracle, and the gate-owned
`ToolRegistry` re-checks any PASS certificate before it can DECIDE. To keep the SECURITY-CRITICAL docker
isolation single-sourced, this module does NOT contain or duplicate the sandbox primitives — they live
in their validated home (`scripts/funsearch_sandbox.py`) and are INJECTED here as `run_fn`. The package
therefore never imports the sandbox/docker code; a concrete instance (e.g. CWC) wires it in.

Trust posture (unchanged from Phase 1): the SandboxedTool is an UNTRUSTED proposer. Its `ToolResult`
PASS carries a certificate, but the certificate is only believed when an operator has registered a
re-checker + statement template for its kind (State 2). With no decider registered (State 1) every PASS
is DEFER at the registry. Nothing here sets kernel_verified or promulgates.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from leibniz.types import Verdict
from leibniz.tools.protocol import ToolDescriptor, ToolResult


@dataclass(frozen=True)
class SandboxTask:
    """The ctx a SandboxedTool consumes: an untrusted program plus the keyword args it is called with."""

    program: str
    args: dict = field(default_factory=dict)


# (program_src, args) -> (ok, code_or_None, error). `ok` is whether the sandbox ran the program at all
# (not whether the output is valid — that is the oracle's job). Injected so the docker primitives stay
# in scripts/funsearch_sandbox.py.
SandboxRunner = Callable[[str, dict], "tuple[bool, Optional[Any], str]"]

# (args, code_or_None) -> ToolResult. Turns the UNTRUSTED sandbox output into a verdict: PASS (with a
# re-checkable Certificate) only for a genuine, oracle-confirmed claim; otherwise DEFER (no claim) or
# FAIL (a sound refutation). The oracle never decides trust — the registry re-checks any PASS.
SandboxOracle = Callable[[dict, Optional[Any]], ToolResult]


@dataclass
class SandboxedTool:
    """A Tool (satisfies leibniz.tools.protocol.Tool) backed by a sandboxed runner + an oracle."""

    descriptor: ToolDescriptor
    run_fn: SandboxRunner
    oracle: SandboxOracle

    def applies(self, ctx: Any) -> bool:
        return isinstance(ctx, SandboxTask)

    def run(self, ctx: Any) -> ToolResult:
        ok, code, error = self.run_fn(ctx.program, ctx.args)
        if not ok:
            # the sandbox could not run the program (timeout/crash/unavailable/flood): no claim -> DEFER.
            return ToolResult(Verdict.DEFER, f"{self.descriptor.name}/sandbox",
                              detail={"sandbox_error": error})
        return self.oracle(ctx.args, code)
