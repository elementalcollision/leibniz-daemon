"""The faithfulness gate -- the one irreducible residual, handled carefully.

The Lean kernel guarantees proof <-> statement. Nothing guarantees
statement <-> Enuntiatio (the human-readable claim the public ledger is held
accountable to). That is the 3-body faithfulness problem, and it is the entire
risk surface of a system whose proofs are otherwise mechanical: a kernel-valid
proof of a *mis-stated* theorem is strictly worse than no proof, because it is
most authoritative exactly when it is most wrong, and the ledger makes it
permanent.

A naive gate -- "ask an LLM whether the statement matches the claim" -- is
theater: the judge shares the formalizer's blind spots and rubber-stamps. So the
gate tries, strongest first:

  1. ADVERSARIAL (gaming-witness). Try to satisfy the formal statement while
     *violating* the Enuntiatio. If such a witness exists, the statement
     underspecifies the claim -> FAIL (FinishReason.GAMED). Generative, so it
     catches gaps a concordance judge waves through. This is the spine.

  2. MECHANICAL (claim-type probe). For claims that assert a *measurable*
     property, check the property directly -- no LLM in the loop. Dispatched by
     ClaimType. This is where the 'claim-type router' actually belongs.

  3. JUDGED (round-trip + independent judge). Only for claims that resist
     operationalization (ClaimType.OPEN_FORM). Logged against the trust budget so
     the residual stays bounded and visible.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional, Protocol

from leibniz.gates.sound_backends import CertificateRechecker, SoundFaithfulnessBackend
from leibniz.propositio import Propositio
from leibniz.types import ClaimType, EdgeEvidence, FinishReason, TrustTier, Verdict
from leibniz.trust import FAITHFULNESS_EDGE, JUDGE_PRODUCER
from leibniz.verifiers import SMTVerifier


class ClaimProbe(Protocol):
    """A mechanical check that the formal statement actually encodes the property
    the Enuntiatio asserts -- e.g. that a 'complexity bound' statement really
    quantifies over input size and bounds an operation count."""

    def __call__(self, prop: Propositio) -> Optional[bool]: ...


class FaithfulnessJudge(Protocol):
    """Last-resort LLM judgment. Returns confidence in [0,1] that statement and
    Enuntiatio agree, via round-trip back-translation + independent review."""

    def round_trip_agrees(self, prop: Propositio) -> float: ...


#: Sound-backend names whose promotion path RE-RENDERS the promoted law from
#: (claim_domain, claim_property) and discards the autoformalizer's statement — each has a
#: `maybe_wrap_*` fast-path in assembly.py gated on the SAME activation as its
#: `maybe_register_*`. That re-rendering is the whole soundness argument for the ADR 0074
#: retry, so the list is explicit and operator-visible (the idiom of trust.py's
#: FAITHFULNESS_PRODUCERS) rather than inferred from `applies()` — which is strictly broader:
#: `walnut` is also a registered sound backend and has NO such prover.
_RERENDERING_BACKENDS = frozenset({
    "lean-decided",           # ADR 0056 / 0058 -> residue_prover
    "minmax-decided",         # ADR 0059        -> minmax_prover
    "boolean-decided",        # ADR 0059        -> boolean_prover
    "mixed-modulus-decided",  # ADR 0060        -> mixed_modulus_prover
    "power-mod-decided",      # ADR 0065        -> power_mod_prover
    "factgcd-decided",        # ADR 0070        -> factgcd_prover
})


@dataclass
class FaithfulnessGate:
    smt: SMTVerifier
    probes: dict[ClaimType, ClaimProbe]
    judge: FaithfulnessJudge
    judge_threshold: float = 0.9
    gaming_bound: int = 64
    # ADR 0037: additional SOUND checkers (Walnut, SOS, kernel bridge). Each is
    # exact-or-DEFER with a re-checked certificate; run cheapest-first AFTER the
    # gaming spine (kept as a kill-only lint) and BEFORE the claim-type probe.
    sound_backends: tuple[SoundFaithfulnessBackend, ...] = ()
    # The gate's OWN independent re-checkers, keyed by certificate.kind. A backend
    # PASS is accepted only if a re-checker for its certificate kind exists and
    # returns True -- the backend's self-reported `rechecked` flag is advisory. With
    # no re-checker registered for a kind, a PASS of that kind cannot be accepted
    # (the dormant default is therefore maximally safe). This pins soundness
    # structurally rather than trusting an honest tag.
    recheckers: dict[str, CertificateRechecker] = field(default_factory=dict)
    # ADR 0056 Track A increment-2 obligation 5: gate-side STATEMENT BINDING, keyed by
    # kind. The template renders this claim's canonical statement from PROP'S OWN fields
    # (never from the certificate); a PASS additionally requires the certificate's claimed
    # statement to be byte-identical (builtin `str`, compared with `str.__ne__` so a
    # str-subclass __eq__ cannot spoof — the tools-registry E7 discipline replicated on
    # this accept path). Binding a kind can only REFUSE passes it would previously have
    # accepted (tightening-only); kinds with no template behave exactly as before.
    templates: dict[str, Callable[[Propositio], Optional[str]]] = field(default_factory=dict)

    def _accept_certificate(self, prop: Propositio, backend, v) -> Optional[EdgeEvidence]:
        """The gate's authoritative acceptance of a sound-backend PASS, or None.

        Extracted verbatim from the dispatch loop so the ADR 0074 retry below CANNOT
        drift from it: there is exactly one place where a certificate becomes a PASS.
        The GATE independently re-checks the certificate via its own re-checker for this
        kind. A self-reported PASS with no registered re-checker, or one whose re-check
        fails, is NOT a pass. For kinds with a registered statement TEMPLATE, the PASS
        additionally requires the certificate's claimed statement to be byte-identical to
        the canonical statement the gate renders from PROP'S OWN fields — binding the
        certificate to THIS claim (ADR 0056 obligation 5; the E7 discipline).
        Tightening-only: template-less kinds behave as before.
        """
        if not v.is_pass_with_certificate():
            return None
        rechecker = self.recheckers.get(v.certificate.kind)
        template = self.templates.get(v.certificate.kind)
        bound = True
        if template is not None:
            expected = template(prop)
            claimed = (v.certificate.detail or {}).get("statement")
            bound = (type(expected) is str and type(claimed) is str
                     and not str.__ne__(expected, claimed))
        if bound and rechecker is not None and rechecker(v.certificate):
            return EdgeEvidence(
                edge=FAITHFULNESS_EDGE,
                tier=TrustTier.MECHANICAL,
                verdict=Verdict.PASS,
                detail={
                    "backend": backend.name,
                    "certificate_kind": v.certificate.kind,
                    "rechecked_by_gate": True,
                    "statement_bound": template is not None,
                    **v.detail,
                },
                cost_units=2.0,
                producer=v.producer,  # ADR 0013 §2 (mechanical, never a judge)
            )
        return None

    def _retry_with_derived_domain(self, prop: Propositio, backend) -> Optional[EdgeEvidence]:
        """ADR 0074: re-ask THIS backend with a mechanically-derived
        ``established_domain`` (:= ``claim_domain``), committing it only on a full PASS.

        WHY. ``established_domain`` is autoformalizer free text. When the model folds the
        claim property into it, the pair's coverage leg becomes the theorem itself and the
        kernel refuses it, so the candidate DEFERs before any proof compute. Measured on the
        live ledger: 25-29 of 54 DEFERred rows are decidable by procedures already shipped.

        WHY IT IS SOUND — and why an earlier draft that derived the field in FORMALIZE was
        NOT. The derived value must never be visible to anything except the backend that
        justifies it:

        * It is applied PROVISIONALLY and rolled back byte-exactly unless this backend
          returns a PASS that ``_accept_certificate`` accepts (re-checked AND statement-
          bound). A DEFER, a FAIL, a failed re-check or an exception all restore the
          original field, so every later consumer sees exactly what it sees without this
          code.
        * The ADR 0004 adversarial gaming spine has ALREADY run (step 1, above the loop) on
          the ORIGINAL contract, so it is never disarmed by the derived value.
        * The ``ClaimProbe`` fast path and the OPEN_FORM judge are only reached on
          fall-through — i.e. after rollback — so their coverage leg
          ``decide_unsat([claim_domain, not(established_domain)])`` is never handed the
          vacuous ``D and not D``.

        Deriving in FORMALIZE broke all three: the mutation survived a DEFER into paths where
        nothing re-renders the statement, the spine's target became empty by construction,
        and a bounded ``ClaimProbe`` search over an unrepresentative box then PASSed a FALSE
        claim through to ``kernel_verified`` + Q.E.D. (demonstrated in review).

        Restricted to backends whose ``*Demonstrate`` fast-path RE-RENDERS the promoted law
        from ``(claim_domain, claim_property)`` and discards the autoformalizer's statement
        (ADR 0058 A2) — an explicit allowlist, since ``walnut`` is also a sound backend and
        has no such prover. Refuses unless ``claim_domain`` is CONCLUSIVELY satisfiable; an
        empty domain would launder a vacuous PASS, and ``None`` (unknown) fails closed.
        """
        if getattr(backend, "name", None) not in _RERENDERING_BACKENDS:
            return None
        en, expr = prop.enuntiatio, prop.expressio
        cd = en.claim_domain
        # LLM-authored fields are not guaranteed to be str (_parse_expressio passes JSON
        # through), so type-check BEFORE any str operation: a non-str must DEFER, not raise.
        if not all(type(x) is str and x
                   for x in (cd, en.claim_property, expr.established_domain)):
            return None
        if not str.__ne__(expr.established_domain, cd):
            return None  # already canonical: this DEFER is not the contract's fault
        decide = getattr(getattr(self.smt, "backend", None), "decide_unsat", None)
        if decide is None:
            return None
        try:
            if decide([cd]) is not False:
                return None  # unsat (empty domain) or unknown -> refuse, fail closed
        except Exception:
            return None
        original = expr.established_domain
        expr.established_domain = cd  # PROVISIONAL — never observed unless accepted below
        try:
            accepted = self._accept_certificate(prop, backend, backend.check(prop))
        except Exception:
            accepted = None
        if accepted is None:
            expr.established_domain = original  # byte-exact rollback
            return None
        accepted.detail["established_domain_derived"] = True  # provenance for the ledger
        return accepted

    def check(self, prop: Propositio) -> EdgeEvidence:
        assert prop.expressio is not None, "formalize before faithfulness"
        en = prop.enuntiatio

        # 1. Adversarial spine. Always run; cheap relative to proof.
        # When the claim carries a structured contract (ADR 0004), search the real
        # gaming target: an input the claim covers, the proof leaves unconstrained,
        # and on which the claimed property fails. Otherwise fall back to the legacy
        # (prose) call so prose-only claims and the deterministic fakes still work.
        if en.claim_domain and en.claim_property and prop.expressio.established_domain:
            statement = f"not ({prop.expressio.established_domain})"
            negated_claim = f"({en.claim_domain}) and {_negate(en.claim_property)}"
        else:
            statement = prop.expressio.theorem_src
            negated_claim = _negate(en.falsifiable_claim)
        witness = self.smt.backend.find_gaming_witness(
            statement=statement,
            negated_claim=negated_claim,
            bound=self.gaming_bound,
        )
        if witness is not None:
            prop.quarantine(FinishReason.GAMED)
            return EdgeEvidence(
                edge=FAITHFULNESS_EDGE,
                tier=TrustTier.ADVERSARIAL,
                verdict=Verdict.FAIL,
                detail={"gaming_witness": witness},
                cost_units=2.0,
                producer="SMTVerifier.gaming_witness",  # ADR 0013 §2
            )

        # 1b. Sound faithfulness backends (ADR 0037), cheapest first. Each is
        # exact-or-DEFER with a RE-CHECKED certificate. A PASS lacking one is NOT
        # a pass (downgraded to fall-through); DEFER never becomes PASS. MECHANICAL,
        # never a judge -- the LLM judge below is reached only when all of these
        # (and the probe) decline.
        for backend in sorted(self.sound_backends, key=lambda b: b.cost_rank):
            if not backend.applies(prop):
                continue
            v = backend.check(prop)
            if v.verdict is Verdict.FAIL:
                prop.quarantine(FinishReason.UNFAITHFUL)
                return EdgeEvidence(
                    edge=FAITHFULNESS_EDGE,
                    tier=TrustTier.MECHANICAL,
                    verdict=Verdict.FAIL,
                    detail={"backend": backend.name, **v.detail},
                    cost_units=2.0,
                    producer=v.producer,  # ADR 0013 §2 (mechanical, never a judge)
                )
            accepted = self._accept_certificate(prop, backend, v)
            if accepted is not None:
                return accepted
            # ADR 0074: a DEFER here is often caused SOLELY by an autoformalizer-authored
            # `established_domain` that restates the claim property, which makes the pair's
            # coverage leg the theorem itself so the kernel refuses it. Retry ONCE on a
            # mechanically-derived contract — and commit that contract only if the retry
            # earns a fully re-checked, statement-bound PASS from THIS backend.
            if v.verdict is Verdict.DEFER:
                derived = self._retry_with_derived_domain(prop, backend)
                if derived is not None:
                    return derived
            # PASS with no/failed independent re-check, or DEFER: not a pass. Fall
            # through to the next backend, then the probe / DEFER / judge logic.

        # 2. Mechanical fast path, dispatched by claim type.
        probe = self.probes.get(en.claim_type)
        if probe is not None:
            result = probe(prop)
            if result is not None:  # probe was decisive
                if not result:
                    prop.quarantine(FinishReason.UNFAITHFUL)
                return EdgeEvidence(
                    edge=FAITHFULNESS_EDGE,
                    tier=TrustTier.MECHANICAL,
                    verdict=Verdict.PASS if result else Verdict.FAIL,
                    detail={"probe": en.claim_type.value},
                    cost_units=2.0,
                    producer="ClaimProbe",  # ADR 0013 §2 (mechanical, never a judge)
                )

        # 3. Judged fallback. Only legitimate for open-form claims. Logged.
        if en.claim_type is not ClaimType.OPEN_FORM:
            # A measurable claim with no decisive probe is a DEFER, not a pass:
            # we refuse to launder it through a judge.
            return EdgeEvidence(
                edge=FAITHFULNESS_EDGE,
                tier=TrustTier.MECHANICAL,
                verdict=Verdict.DEFER,
                detail={"reason": "no decisive probe for measurable claim"},
                cost_units=2.0,
                producer="FaithfulnessGate",  # ADR 0013 §2 (a refusal, not a judge)
            )

        confidence = self.judge.round_trip_agrees(prop)
        passed = confidence >= self.judge_threshold
        if not passed:
            prop.quarantine(FinishReason.UNFAITHFUL)
        return EdgeEvidence(
            edge=FAITHFULNESS_EDGE,
            tier=TrustTier.JUDGED,
            verdict=Verdict.PASS if passed else Verdict.FAIL,
            detail={"round_trip_confidence": confidence, "residual": True},
            cost_units=3.0,
            producer=JUDGE_PRODUCER,  # ADR 0013 §2: the one bounded judged edge
        )


def _negate(predicate: str) -> str:
    """Boolean negation of a predicate, for the gaming-witness search target.

    For a structured claim (ADR 0004) ``predicate`` is the DSL ``claim_property``
    and this yields a Z3-searchable ``not (...)``. For a prose ``falsifiable_claim``
    it yields ``not (...)`` too; the Z3 backend cannot parse prose and degrades to
    "no witness" (the structured path is what makes the spine real)."""
    return f"not ({predicate})"
