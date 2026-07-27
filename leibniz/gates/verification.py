"""The verification gate -- the deterministic promotion verdict.

Like Newton's gate, ``is_promotable`` is a pure boolean over recorded edge
evidence; it renders no new judgments and re-runs nothing. Unlike Newton's gate,
the conjunction it checks is anchored on a *kernel proof*, and it delegates to
``TrustPolicy`` so the promotion can be rejected if any edge sits at the wrong
trust tier.

Promotion order is also enforced here, so the daemon spends compute in the
cheap-refutation-first order:

    cheap_refutation (SMT, cost~1)
        -> novelty/non-triviality (cost~1)
        -> faithfulness (cost~2-3)
        -> proof (Lean kernel, cost~10)

A failure at any earlier, cheaper edge short-circuits before the expensive proof.
"""

from __future__ import annotations

from dataclasses import dataclass

from leibniz.propositio import Propositio
from leibniz.types import FinishReason, Verdict
from leibniz.trust import (
    FAITHFULNESS_EDGE,
    NOVELTY_EDGE,
    PROOF_EDGE,
    TrustPolicy,
    TrustViolation,
)


#: ADR 0079 — faithfulness producers whose fragment RE-RENDERS the promoted law from
#: ``(claim_domain, claim_property)``. For these, and only these, a canonical statement is
#: computable, so promotion can require the proved statement to BE that statement. Each entry
#: names the module whose ``*_law`` generator and ``_law_name`` the fast-path itself uses, so
#: the binding is checked against exactly what the prover would have produced.
_CANONICAL_BY_PRODUCER = {
    "lean_decided/kernel":     ("leibniz.providers.residue_prover", "residue_law"),
    "minmax_identity/kernel":  ("leibniz.providers.minmax_prover", "minmax_law"),
    "boolean_modular/kernel":  ("leibniz.providers.boolean_prover", "boolean_law"),
    "mixed_modular/kernel":    ("leibniz.providers.mixed_modulus_prover", "mixed_law"),
    "power_mod/kernel":        ("leibniz.providers.power_mod_prover", "power_law"),
    "factgcd/kernel":          ("leibniz.providers.factgcd_prover", "factgcd_law"),
}


def _canonical_theorem_src(producer: str, prop: Propositio):
    """The statement the re-rendering fast-path for ``producer`` would have proved, or None
    when it is not computable (no such producer, no contract, or the generator abstains)."""
    entry = _CANONICAL_BY_PRODUCER.get(producer)
    en = prop.enuntiatio
    expr = getattr(prop, "expressio", None)
    if entry is None or expr is None or en is None:
        return None
    cd, cp = en.claim_domain, en.claim_property
    if not (type(cd) is str and type(cp) is str and cd and cp):
        return None
    module, fn_name = entry
    try:
        import importlib
        mod = importlib.import_module(module)
        gen, name_fn = getattr(mod, fn_name), getattr(mod, "_law_name")
    except (ImportError, AttributeError):
        # STRUCTURAL: the table no longer matches the providers. That is a bug, not an
        # abstention — a silently unbound fragment leaves this gap wide open, which is exactly
        # how a `mixed_modulus_law` typo survived review. `test_every_table_entry_resolves`
        # fails loudly on it; here we still degrade to "no constraint" so a stripped deployment
        # cannot brick promotion.
        return None
    try:
        out = gen(name_fn(cd, cp), cd, cp)
    except Exception:
        return None  # the generator legitimately abstains (out-of-fragment, render error)
    return out[0] if out else None


@dataclass
class VerificationGate:
    policy: TrustPolicy

    def is_promotable(self, prop: Propositio) -> bool:
        """Pure boolean over recorded evidence. No new judgments, no re-execution."""
        required = {PROOF_EDGE, FAITHFULNESS_EDGE, NOVELTY_EDGE}
        present = {e.edge for e in prop.edges}
        if not required.issubset(present):
            return False
        try:
            self.policy.validate_path(
                [e for e in prop.edges if e.edge in required]
            )
        except TrustViolation:
            return False
        # ADR 0079: when a RE-RENDERING fragment certified faithfulness, the certificate binds
        # a canonical statement derived from (claim_domain, claim_property) — but DEMONSTRATE
        # may still have fallen through to the ensemble, which proves the autoformalizer's own
        # `theorem_src`. Nothing otherwise ties the proved statement to the certified one, so a
        # kernel-valid proof of a DIFFERENT theorem could be promulgated under that certificate.
        # Require them to be the same bytes. REFUSE-ONLY: this can reject a promotion, never
        # create one, so it cannot manufacture a law (the failure mode that made the
        # FORMALIZE-time render unsound). Uncomputable canonical form -> no constraint, so
        # fragments without a generator and prose-only claims are untouched.
        for e in prop.edges:
            if e.edge != FAITHFULNESS_EDGE or e.verdict is not Verdict.PASS:
                continue
            canonical = _canonical_theorem_src(e.producer, prop)
            if canonical is None:
                continue
            proved = getattr(prop.expressio, "theorem_src", None)
            if type(proved) is not str or str.__ne__(proved, canonical):
                return False
        return all(
            e.verdict is Verdict.PASS
            for e in prop.edges
            if e.edge in required
        )

    def finalize(self, prop: Propositio) -> FinishReason:
        """Decide the candidate's terminal state and return the reason."""
        if self.is_promotable(prop):
            prop.promulgated = True
            prop.finish_reason = FinishReason.PROMULGATED
            return FinishReason.PROMULGATED
        # If a gate already quarantined with a specific reason, keep it.
        if prop.finish_reason is not None:
            return prop.finish_reason
        # Otherwise the proof simply wasn't found.
        prop.quarantine(FinishReason.UNPROVEN)
        return FinishReason.UNPROVEN
