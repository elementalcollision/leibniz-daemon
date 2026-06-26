"""Sound faithfulness backends (ADR 0037).

A ``SoundFaithfulnessBackend`` is a *mechanical, exact-or-DEFER* checker of the
statement<->claim correspondence. It is **not** a judge: a PASS must carry a
*re-checked* certificate (independently re-verified, not trusted because the
backend asserts it), and its trust tier is MECHANICAL. DEFER -- the backend
cannot soundly decide this claim -- **never** silently becomes PASS.

This generalizes the existing checker seam so additional sound engines can be
registered behind the unchanged trust boundary, crawl-walk-run:

  * the bounded-Z3 gaming-witness spine (already kill-only / lint-shaped),
  * the per-``ClaimType`` ``ClaimProbe`` (already a mechanical PASS path),
  * Walnut (FO over k-automatic sequences -- sound over *unbounded* n),
  * SOS / Positivstellensatz, a kernel bridge, ...

Trust invariants this module preserves (and the gate enforces):
  1. **PASS requires a re-checked certificate.** ``is_sound_pass()`` is the gate's
     gate: a PASS whose certificate is missing or not ``rechecked`` is downgraded
     to DEFER. A backend cannot launder a pass it did not independently verify.
  2. **MECHANICAL, never JUDGED.** The LLM judge stays exactly where it is in
     ``FaithfulnessGate`` -- reached only when every sound backend DEFERs.
  3. **exact-or-DEFER.** The backend returns DEFER, never a guess, when it cannot
     soundly decide; a FAIL is a sound *refutation* (statement diverges from claim).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Optional, Protocol, runtime_checkable

from leibniz.propositio import Propositio
from leibniz.types import Verdict

# An independent re-checker for a certificate KIND, owned by the gate (not the
# backend): automaton-emptiness for "walnut-automaton", `ring` for "sos", the Lean
# kernel for "kernel-bridge". The gate accepts a PASS only if the re-checker for the
# certificate's kind exists AND returns True -- so `Certificate.rechecked` (set by
# the backend) is ADVISORY; the gate's own re-check is authoritative. This pins
# soundness structurally, the way the proof edge pins producer == KERNEL_PRODUCER,
# rather than trusting an honest tag.
CertificateRechecker = Callable[["Certificate"], bool]


@dataclass(frozen=True)
class Certificate:
    """A re-checkable witness for a sound faithfulness decision.

    ``rechecked`` is True iff ``data`` was *independently re-verified* by a checker
    smaller than the engine that produced it -- an automaton-emptiness check for
    Walnut, ``ring`` for an SOS decomposition, the Lean kernel for a bridge proof.
    It is the faithfulness analogue of re-running a proof through the kernel: the
    certificate is checked, not trusted. The gate refuses a PASS whose certificate
    is not ``rechecked``.
    """

    kind: str                       # "walnut-automaton" | "sos" | "kernel-bridge" | ...
    rechecked: bool                 # was `data` independently re-verified?
    data: Any = None                # the certificate payload (automaton, SOS decomp, proof term)
    detail: dict = field(default_factory=dict)


@dataclass(frozen=True)
class FaithfulnessVerdict:
    """A sound backend's verdict. A *trusted* PASS requires a rechecked certificate."""

    verdict: Verdict                # PASS | FAIL | DEFER
    producer: str                   # provenance, e.g. "walnut/recheck" (ADR 0013 §2)
    certificate: Optional[Certificate] = None
    detail: dict = field(default_factory=dict)

    def is_pass_with_certificate(self) -> bool:
        """A backend-side pre-filter: verdict PASS with a self-declared re-checked
        certificate. NOT sufficient for the gate to accept -- the gate ALSO runs its
        own independent re-checker for ``certificate.kind`` (see CertificateRechecker).
        A PASS without a certificate is never a pass."""
        return (
            self.verdict is Verdict.PASS
            and self.certificate is not None
            and self.certificate.rechecked
        )


@runtime_checkable
class SoundFaithfulnessBackend(Protocol):
    """A registrable sound checker of statement<->claim. See module docstring."""

    name: str
    cost_rank: int                  # cheapest first; the gate runs in this order

    def applies(self, prop: Propositio) -> bool:
        """Does this backend handle this claim's shape at all? (routing)"""
        ...

    def check(self, prop: Propositio) -> FaithfulnessVerdict:
        """EXACT-OR-DEFER. PASS must carry a re-checked certificate. Never a judge."""
        ...
