"""Tool protocol + result/evidence types (ADR 0041 Phase 1).

Byte-for-byte the shape of ADR 0037's `SoundFaithfulnessBackend` + `FaithfulnessVerdict`, generalized
off the word "faithfulness." `Certificate` and `CertificateRechecker` are RE-EXPORTED from
`leibniz.gates.sound_backends` (single source of truth — never redefined, so faithfulness and tools
share one symbol and cannot drift).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional, Protocol, runtime_checkable

from leibniz.types import TrustTier, Verdict

# Single source of truth (ADR 0041 §3.1): the certificate + its gate-owned re-checker live in
# sound_backends; tools reuse the exact same types so the faithfulness gate and the tool registry
# share one re-check discipline.
from leibniz.gates.sound_backends import Certificate, CertificateRechecker  # noqa: F401


class Provenance(Enum):
    """Where a tool came from. The default for anything Leibniz proposes or builds is SELF_BUILT;
    research-derived tools are INGESTED_DERIVED; only operator-authored, separately-reviewed tools are
    HUMAN. Provenance never grants trust (a SELF_BUILT tool is as untrusted as any other); it gates
    what a tool may *become* — e.g. a re-checker must be HUMAN (ADR 0041 §6)."""

    HUMAN = "human"
    INGESTED_DERIVED = "ingested_derived"
    SELF_BUILT = "self_built"


@dataclass(frozen=True)
class ToolDescriptor:
    """Identity + routing for a tool. `result_kind` is what binds (in the registry) to a re-checker
    and an operator-owned statement template; `cost_rank` drives cheapest-first dispatch (inv 5)."""

    name: str
    provenance: Provenance
    cost_rank: int
    result_kind: str
    requires_sandbox: bool = True
    arg_schema: dict = field(default_factory=dict)


@dataclass(frozen=True)
class ToolResult:
    """A tool's verdict. EXACT-OR-DEFER: a PASS must carry a re-checked certificate; a heuristic/search
    tool with no certificate may only ever return FAIL or DEFER, never PASS."""

    verdict: Verdict                # PASS | FAIL | DEFER
    producer: str
    certificate: Optional[Certificate] = None
    detail: dict = field(default_factory=dict)

    def is_pass_with_certificate(self) -> bool:
        """Pre-filter (identical to FaithfulnessVerdict): PASS with a self-declared re-checked
        certificate. NOT sufficient — the REGISTRY runs its own re-checker + statement-template check."""
        return (
            self.verdict is Verdict.PASS
            and self.certificate is not None
            and self.certificate.rechecked
        )


@dataclass(frozen=True)
class ToolEvidence:
    """The registry's audited output for one tool run — a sibling of `EdgeEvidence`. It NEVER carries
    the proof edge and NEVER names KERNEL_PRODUCER (E3): a tool cannot decide a proof. `tier` is
    MECHANICAL only when the gate's own re-checker re-verified the certificate AND the statement matched
    the operator template; otherwise the verdict is DEFER."""

    tool: str
    verdict: Verdict
    tier: TrustTier
    producer: str
    provenance: Optional[Provenance] = None
    certificate_kind: Optional[str] = None
    rechecked_by_registry: bool = False
    detail: dict = field(default_factory=dict)


@runtime_checkable
class Tool(Protocol):
    """A registrable, UNTRUSTED producer. `applies` routes; `run` is exact-or-DEFER and a PASS must
    carry a re-checked certificate. A tool never receives the registry, the re-checkers, or the
    templates — it cannot reach the deciding machinery (structural barrier behind E2)."""

    descriptor: ToolDescriptor

    def applies(self, ctx: Any) -> bool: ...

    def run(self, ctx: Any) -> ToolResult: ...
