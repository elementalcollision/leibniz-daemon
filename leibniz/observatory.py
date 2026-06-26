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

    def _file(self, prop: Propositio, reason: FinishReason, verdict: Verdict, why: str,
              cert_data: str | None = None, numeration: str | None = None) -> Propositio:
        """Record a provenance edge (NEVER a promotion edge) with a diagnostic ``why`` and set
        the finish reason. Sets no ``promulgated``/``Demonstratio``/Q.E.D. (kernel-only)."""
        detail: dict = {"reason": why}
        if cert_data is not None:
            detail.update(automaton=cert_data, numeration=numeration)
        prop.record(EdgeEvidence(
            edge=WALNUT_DECISION_EDGE, tier=TrustTier.MECHANICAL, verdict=verdict,
            detail=detail, producer="walnut/decide",
        ))
        prop.finish_reason = reason
        return prop

    def decide(self, prop: Propositio) -> Propositio:
        """Run Walnut on the claim's predicate and file the outcome (with a diagnostic reason
        on a provenance edge). Returns ``prop`` with:
          * ``WALNUT_DECIDED`` — Walnut decided it TRUE over unbounded n: either a closed
            SENTENCE Walnut returned ``true`` (Walnut, the real runner, is the trusted decision
            procedure for this non-Q.E.D. tier), or a free-variable predicate whose agreement
            automaton an INDEPENDENT re-check confirms universal;
          * ``REFUTED`` — Walnut found it false (``false`` token, or a reachable rejecting state);
          * ``UNPROVEN`` — cannot be soundly decided (no result / numeration mismatch /
            indeterminate) — never guessed;
          * ``MALFORMED`` — the claim carries no Walnut predicate/numeration.
        NEVER sets ``promulgated`` and never creates a proof/Q.E.D. (kernel-only, invariants 1&7).

        TRUST: a closed-sentence ``true`` is trusted as Walnut's sound decision — sound only
        because the production ``runner`` is ``_default_runner`` (real Walnut with input
        sanitization + stale-file deletion + clean-exit + fresh-read guards). The injectable
        ``runner`` is for tests only; it is NOT a trust surface. The tier is non-Q.E.D.
        """
        # A prop that already carries a kernel proof belongs to the Q.E.D. path, NOT this tier.
        if prop.demonstratio is not None:
            return prop

        ex = prop.expressio
        if not (ex is not None and ex.walnut_predicate and ex.walnut_numeration):
            return self._file(prop, FinishReason.MALFORMED, Verdict.DEFER, "no_walnut_predicate")

        result_text = self.runner(ex.walnut_predicate, ex.walnut_numeration)
        if result_text is None:
            # Walnut unavailable, inputs unsafe, or a nonzero exit (e.g. a predicate syntax
            # error). Run with LEIBNIZ_WALNUT_DEBUG=1 to see Walnut's stderr.
            return self._file(prop, FinishReason.UNPROVEN, Verdict.DEFER, "no_result")

        aut = parse_walnut_automaton(result_text)

        # Closed-SENTENCE theorem (all variables bound): Walnut's true/false IS the decision.
        # There is no structural object to re-derive for a 0-track result; we trust Walnut
        # (the real runner; see TRUST above). This is the common form for combinatorics-on-words
        # theorems ("RS is overlap-free").
        if aut.is_sentence:
            if aut.is_true:
                return self._file(prop, FinishReason.WALNUT_DECIDED, Verdict.PASS,
                                  "decided_sentence", cert_data=result_text,
                                  numeration=ex.walnut_numeration)
            return self._file(prop, FinishReason.REFUTED, Verdict.FAIL, "refuted_sentence")

        # Free-variable predicate -> a structured agreement automaton. Require the numeration we
        # asked for, then INDEPENDENTLY verify universality (does not merely trust Walnut's say-so).
        if aut.numeration != ex.walnut_numeration:
            return self._file(prop, FinishReason.UNPROVEN, Verdict.DEFER, "numeration_mismatch")
        verdict = classify_agreement(aut)
        if verdict == "universal":
            cert = Certificate(kind=WALNUT_CERT_KIND, rechecked=False, data=result_text,
                               detail={"numeration": ex.walnut_numeration})
            if recheck_walnut_certificate(cert):
                return self._file(prop, FinishReason.WALNUT_DECIDED, Verdict.PASS,
                                  "decided_universal", cert_data=result_text,
                                  numeration=ex.walnut_numeration)
            return self._file(prop, FinishReason.UNPROVEN, Verdict.DEFER, "recheck_failed")
        if verdict == "refuted":
            return self._file(prop, FinishReason.REFUTED, Verdict.FAIL, "refuted_automaton")
        return self._file(prop, FinishReason.UNPROVEN, Verdict.DEFER, "indeterminate")


def is_walnut_decided(prop: Propositio) -> bool:
    """Tier membership: decided by Walnut, and emphatically NOT in the kernel Q.E.D. Codex."""
    return (
        prop.finish_reason is FinishReason.WALNUT_DECIDED
        and not prop.promulgated
        and prop.demonstratio is None
    )
