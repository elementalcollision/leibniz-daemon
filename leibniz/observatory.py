"""The Walnut-decided Observatory tier (ADR 0038) — a SEPARATE, non-Q.E.D. ledger of
theorems mechanically DECIDED by Walnut over unbounded n.

This is NOT the kernel Codex and NOT the faithfulness gate. Here the claim's
``walnut_predicate`` IS the theorem (e.g. Thue-Morse overlap-freeness), and Walnut *decides*
it as a sound decision procedure (Büchi–Bruyère). A DECIDED result is MECHANICAL and
re-checked (the automaton-universality certificate, ADR 0037 §7), but it is **not** Q.E.D.:

  * it NEVER sets ``promulgated``, never produces a ``Demonstratio``/``kernel_verified``/Q.E.D.
    (invariants 1 & 7 keep those kernel-only);
  * it does NOT pass through ``Promulgate``/``TrustPolicy.validate_path`` — it is a parallel
    output identified solely by ``FinishReason.WALNUT_DECIDED``;
  * faithfulness (predicate ↔ human claim) is handled by FORMAL-FIRST publication: the Walnut
    predicate + numeration is the statement of record, prose is commentary. No renderer is
    promoted into any TCB (the reason the kernel bridge is deferred, ADR 0038 §1/§4).

Propose/decide separation holds: an LLM may PROPOSE the conjecture; **Walnut** (a decision
procedure, not an LLM) decides it, and the gate's own re-checker re-derives the verdict.

OFF BY DEFAULT: nothing wires this into the assembled pipeline; the operator opts in, and the
runner DEFERs (=> UNPROVEN) whenever Walnut is absent/errors.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional

from leibniz.backends.walnut import (
    WALNUT_CERT_KIND,
    _default_runner,
    classify_agreement,
    parse_walnut_automaton,
    recheck_walnut_certificate,
)
from leibniz.gates.sound_backends import Certificate
from leibniz.propositio import Propositio
from leibniz.types import EdgeEvidence, FinishReason, TrustTier, Verdict

# A provenance edge for a Walnut decision. Deliberately NOT one of the promotion edges
# (PROOF/FAITHFULNESS/NOVELTY), so a Walnut-decided record can never satisfy
# TrustPolicy.validate_path / VerificationGate.is_promotable even if mistakenly run through
# them — the tier stays strictly separate from the kernel Q.E.D. Codex.
WALNUT_DECISION_EDGE = "walnut_decision"


@dataclass
class WalnutObservatory:
    """Decide automatic-sequence claims with Walnut and file them in the non-Q.E.D. tier.

    ``runner`` (predicate, numeration) -> result-automaton text | None is injectable so the
    decision logic is unit-testable without the Walnut binary; the default shells to Walnut.
    """

    runner: Callable[..., Optional[str]] = field(default=_default_runner)

    def decide(self, prop: Propositio) -> Propositio:
        """Run Walnut on the claim's predicate and file the outcome. Returns ``prop`` with:
          * ``FinishReason.WALNUT_DECIDED`` iff Walnut decided it TRUE over unbounded n AND the
            gate's independent re-check confirms the certificate is a universal automaton;
          * ``FinishReason.REFUTED``       iff Walnut found it false (a reachable rejecting state);
          * ``FinishReason.UNPROVEN``      iff it cannot be soundly decided (no binary, malformed,
            indeterminate, numeration mismatch) — never guessed;
          * ``FinishReason.MALFORMED``     iff the claim carries no Walnut predicate/numeration.
        It NEVER sets ``promulgated`` and never creates a proof/Q.E.D. (kernel-only).
        """
        # A prop that already carries a kernel proof belongs to the Q.E.D. path, NOT this
        # tier: never re-file it as WALNUT_DECIDED (defense-in-depth so a proof and the tier
        # flag can never coexist on one record). Leave it untouched.
        if prop.demonstratio is not None:
            return prop

        ex = prop.expressio
        if not (ex is not None and ex.walnut_predicate and ex.walnut_numeration):
            prop.quarantine(FinishReason.MALFORMED)
            return prop

        result_text = self.runner(ex.walnut_predicate, ex.walnut_numeration)
        if result_text is None:
            prop.quarantine(FinishReason.UNPROVEN)  # Walnut unavailable / errored => cannot decide
            return prop

        aut = parse_walnut_automaton(result_text)
        # numeration self-consistency: the result must be over the numeration we asked for.
        if aut.is_sentence or aut.numeration != ex.walnut_numeration:
            prop.quarantine(FinishReason.UNPROVEN)
            return prop

        verdict = classify_agreement(aut)
        if verdict == "refuted":
            prop.quarantine(FinishReason.REFUTED)
            return prop
        if verdict != "universal":  # indeterminate: cannot be soundly decided
            prop.quarantine(FinishReason.UNPROVEN)
            return prop

        # DECIDED-TRUE: require the gate's OWN independent re-check (the certificate is a
        # universal automaton) before filing — a self-reported pass is never enough. The
        # `rechecked` flag starts False (the backend asserts nothing); the gate's re-check
        # below is authoritative and re-derives universality from cert.data, never the flag.
        cert = Certificate(
            kind=WALNUT_CERT_KIND, rechecked=False, data=result_text,
            detail={"numeration": ex.walnut_numeration, "predicate": ex.walnut_predicate},
        )
        if not recheck_walnut_certificate(cert):
            prop.quarantine(FinishReason.UNPROVEN)
            return prop

        # File in the non-Q.E.D. tier. The certificate is recorded as PROVENANCE (a
        # non-promotion edge), NOT a proof edge: this NEVER sets promulgated and never
        # creates a Demonstratio/Q.E.D. (kernel-only, invariants 1 & 7).
        prop.record(EdgeEvidence(
            edge=WALNUT_DECISION_EDGE,
            tier=TrustTier.MECHANICAL,           # a sound decision procedure, re-checked — not a judge
            verdict=Verdict.PASS,
            detail={"certificate_kind": cert.kind, "automaton": cert.data,
                    "numeration": ex.walnut_numeration},
            producer="walnut/decide",
        ))
        prop.finish_reason = FinishReason.WALNUT_DECIDED
        return prop


def is_walnut_decided(prop: Propositio) -> bool:
    """Tier membership: decided by Walnut, and emphatically NOT in the kernel Q.E.D. Codex."""
    return (
        prop.finish_reason is FinishReason.WALNUT_DECIDED
        and not prop.promulgated
        and prop.demonstratio is None
    )
