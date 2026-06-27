"""ToolRegistry — the gate-owned dispatch + dormant-empty deciding registries (ADR 0041 Phase 1).

Generalizes the faithfulness accept/fall-through loop (`leibniz/gates/faithfulness.py`). The two
deciding registries — `recheckers` (kind -> independent re-checker) and `templates` (kind -> operator
statement template, E7) — are **dormant-empty by default**. A tool can be REGISTERED + RUN (State 1,
TCB+0); its PASS is accepted as MECHANICAL (State 2) ONLY when an operator has registered BOTH a
re-checker and a statement template for the certificate's kind, the re-checker re-derives True FROM the
certificate data, AND the certificate's claimed statement is byte-identical to the operator template
applied to that data. Anything short of all of that is DEFER — never a silent PASS.

This is the structural barrier against TCB-growth-by-fiat: a tool never receives the registry, so it
cannot reach `recheckers`/`templates`; and `register_decider` (the State-2 seam) is operator-only,
hard-blocked from agent edit paths by the PreToolUse hook on this file. No tool ever sets
kernel_verified or touches the proof edge.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from leibniz.types import TrustTier, Verdict
from leibniz.tools.protocol import (
    Certificate,
    CertificateRechecker,
    Tool,
    ToolEvidence,
    ToolResult,
)

# An operator-owned statement template (E7): given a certificate's raw `data`, it returns the canonical
# statement string the kind's re-checker must have decided. The registry rejects a certificate whose
# claimed statement (cert.detail["statement"]) is not byte-identical to template(cert.data) — so an
# untrusted tool cannot author the proposition it gets graded on; it supplies only the witness DATA.
StatementTemplate = Callable[[Any], str]


@dataclass
class ToolRegistry:
    tools: tuple[Tool, ...] = ()
    recheckers: dict[str, CertificateRechecker] = field(default_factory=dict)  # DORMANT-EMPTY (E2)
    templates: dict[str, StatementTemplate] = field(default_factory=dict)      # DORMANT-EMPTY (E7)

    # --- operator-only registration seams (PreToolUse-guarded on this file) ------------------
    def register_tool(self, tool: Tool) -> None:
        """Add a tool as a PROPOSER (State 1). Autonomous/agent code may call this — it grows the TCB
        by zero, since a registered tool with no registered re-checker can only ever DEFER."""
        self.tools = self.tools + (tool,)

    def register_decider(self, kind: str, rechecker: CertificateRechecker,
                         template: StatementTemplate) -> None:
        """ADMIT a kind to the DECIDING path (State 2). OPERATOR-ONLY: binds BOTH a re-checker and a
        statement template for `kind`. Operator-only is enforced by the PreToolUse file-edit hook on
        this file + the structural fact that a tool never receives the registry (no runtime caller
        check); the re-checker must be HUMAN-provenance, separately-reviewed, proposer-immutable code
        (ADR 0041 §2.2b, §6).

        ADMISSION CONTRACT (operator MUST satisfy before registering a kind — the gate cannot verify
        these, so they are preconditions of registration, not runtime checks):
          - SOUNDNESS BINDING (E6=>E7): `rechecker(cert)` returns True ONLY IF `template(cert.data)` is
            a TRUE proposition. The registry checks data-shape (re-checker) and statement-rendering
            (template) separately; nothing else forces "re-check True => the rendered statement holds."
            A weak re-checker lets a tool steer WHICH true statement is stamped by choosing the data.
          - PURE TEMPLATE: `template` is deterministic and side-effect-free; `cert.data` is treated as
            immutable (re-checker and template read it independently — a mutable/non-deterministic
            payload could present different values to each).
          - (Phase-2 hardening, ADR 0041 S3) prefer binding a canonical STRUCTURED key over rendered
            prose, so two distinct data values cannot collide to the same statement string."""
        self.recheckers[kind] = rechecker
        self.templates[kind] = template

    # --- dispatch (generalized faithfulness accept/fall-through) ------------------------------
    def run(self, ctx: Any) -> ToolEvidence:
        """Run applicable tools cheapest-first. A FAIL is a mechanical refutation (KILL). A PASS is
        accepted as MECHANICAL only via `_accept_or_defer`; otherwise fall through. If nothing
        decides, return a registry-level DEFER (never a silent PASS)."""
        last_defer: ToolEvidence | None = None
        for tool in sorted(self.tools, key=lambda t: t.descriptor.cost_rank):
            if not tool.applies(ctx):
                continue
            r: ToolResult = tool.run(ctx)
            if r.verdict is Verdict.FAIL:
                return ToolEvidence(
                    tool=tool.descriptor.name, verdict=Verdict.FAIL, tier=TrustTier.MECHANICAL,
                    producer=r.producer, provenance=tool.descriptor.provenance, detail=r.detail)
            if r.is_pass_with_certificate():
                ev = self._accept_or_defer(tool, r)
                if ev.verdict is Verdict.PASS:
                    return ev
                last_defer = ev          # a rejected PASS: keep its reason (E6/E7 diagnostics)
            # PASS w/o cert, rejected PASS, or DEFER: fall through to the next tool.
        return last_defer or ToolEvidence(
            tool="(none)", verdict=Verdict.DEFER, tier=TrustTier.MECHANICAL,
            producer="ToolRegistry", detail={"reason": "no tool decided"})

    def _accept_or_defer(self, tool: Tool, r: ToolResult) -> ToolEvidence:
        cert: Certificate = r.certificate
        rechecker = self.recheckers.get(cert.kind)
        template = self.templates.get(cert.kind)

        def _defer(reason: str) -> ToolEvidence:
            return ToolEvidence(
                tool=tool.descriptor.name, verdict=Verdict.DEFER, tier=TrustTier.MECHANICAL,
                producer=r.producer, provenance=tool.descriptor.provenance,
                certificate_kind=cert.kind, detail={"defer_reason": reason})

        # E1/E2: a kind with no registered re-checker AND template is uninterpretable -> DEFER.
        if rechecker is None or template is None:
            return _defer("no operator-registered re-checker/template for this kind (State 1 only)")
        # E6: the gate's own re-checker must RE-DERIVE True from cert.data (never trusts cert.rechecked).
        if not rechecker(cert):
            return _defer("independent re-check returned False")
        # E7: the certificate's claimed statement must be EXACTLY the operator template applied to the
        # data — the tool supplies witness DATA, never the proposition it is graded on. The claimed
        # statement is tool-controlled, so PIN it to a builtin `str` (reject None and any str subclass)
        # and compare with `str.__ne__` — otherwise a tool could supply a str-subclass overriding
        # __eq__/__ne__ to launder a stronger statement past this check. `rendered` is computed once
        # (the template MUST be pure/deterministic; see register_decider).
        claimed = (cert.detail or {}).get("statement")
        if type(claimed) is not str:
            return _defer("certificate statement is missing or not a builtin str")
        rendered = template(cert.data)
        if type(rendered) is not str:
            return _defer("operator template did not return a builtin str")
        if str.__ne__(rendered, claimed):
            return _defer("certificate statement not produced by the operator-owned template")
        return ToolEvidence(
            tool=tool.descriptor.name, verdict=Verdict.PASS, tier=TrustTier.MECHANICAL,
            producer=r.producer, provenance=tool.descriptor.provenance,
            certificate_kind=cert.kind, rechecked_by_registry=True, detail=r.detail)
