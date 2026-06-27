"""leibniz/tools/ — the domain-neutral tool-use seam (ADR 0041, Phase 1).

A *re-instantiation* of the ADR 0037 SoundFaithfulnessBackend trio, generalized off the word
"faithfulness": an untrusted Tool PROPOSES; the gate-owned ToolRegistry DECIDES via a kind-keyed,
dormant-empty re-checker (+ operator-owned statement template, E7). No new trust principle. A tool can
be REGISTERED + RUN autonomously (State 1, TCB+0); its PASS is only accepted (State 2) when an operator
has registered both a re-checker and a statement template for its result_kind. See
docs/adr/0041-tool-use-building-and-research-ingestion.md.

Phase 1 is the seam proven in isolation: no Docker, no LLM, no sandbox — just the types, the dispatch,
and the structural guards that make TCB-growth-by-fiat impossible.
"""
from leibniz.tools.protocol import (  # noqa: F401
    Certificate,
    CertificateRechecker,
    Provenance,
    Tool,
    ToolDescriptor,
    ToolEvidence,
    ToolResult,
)
from leibniz.tools.registry import StatementTemplate, ToolRegistry  # noqa: F401

__all__ = [
    "Certificate", "CertificateRechecker", "Provenance", "Tool", "ToolDescriptor",
    "ToolEvidence", "ToolResult", "StatementTemplate", "ToolRegistry",
]
