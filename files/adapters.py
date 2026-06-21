"""Adapters -- the seams where extant code attaches. Clean-room interfaces only.

These define *what Leibniz needs* from the existing systems, so their real
modules drop in behind a stable boundary. Nothing here assumes the internals of
those repos; each is a Protocol the integration must satisfy.

  RuntimeAdapter  -- Chimera. The body: circadian scheduler, SQLite memory, the
                     cross-model witness mechanism, drift/trust telemetry.
  ProviderAdapter -- the LLM, confined to PROPOSAL roles only (see leibniz.types.
                     Role). It may draft; it may never decide. The faithfulness
                     judge is the *only* place provider output is trusted as a
                     verdict, and even there it is the bounded residual.
  LeonardoAdapter -- TENTATIVE. Assigned the survey/analogy role pending
                     confirmation of what Leonardo actually is. Isolated here so
                     rewiring it is a one-file change.
"""

from __future__ import annotations

from typing import Optional, Protocol

from leibniz.propositio import Enuntiatio, Expressio, Propositio
from leibniz.types import Role


class RuntimeAdapter(Protocol):
    """Chimera. Provides scheduling, persistence, and witness/telemetry."""

    def now_phase(self) -> str: ...
    def remember(self, prop: Propositio) -> None: ...
    def recall_recent(self, n: int) -> list[Propositio]: ...
    def witness(self, prompt: str, n_models: int) -> list[str]:
        """Cross-model agreement: ask N independent models, return their outputs.
        Used by the gaming-witness and as an ensemble for proposal diversity."""
        ...


class ProviderAdapter(Protocol):
    """The LLM, in proposal-only roles. Every method returns a *draft*."""

    def propose(self, role: Role, context: str) -> str: ...


class LeonardoAdapter(Protocol):
    """TENTATIVE survey/analogy front-end. Confirm against the real Leonardo."""

    def survey_frontier(self, domain: str) -> list[str]:
        """Return open questions / live edges of the domain to seed conjecture."""
        ...

    def cross_domain_analogies(self, seed: str) -> list[str]:
        """Stepping stones drawn from other domains (the da Vinci move)."""
        ...
