"""ADR 0079 — a re-rendering certificate binds the statement that gets promulgated.

When a re-rendering fragment certifies faithfulness, its certificate binds a canonical statement
derived from (claim_domain, claim_property). But DEMONSTRATE may still fall through to the LLM
ensemble, which proves the autoformalizer's OWN theorem_src — a statement the certificate never
bound. Promotion now requires the two to be the same bytes. REFUSE-ONLY: it can reject a
promotion, never create one.
"""
from __future__ import annotations

from leibniz.gates.verification import VerificationGate, _canonical_theorem_src
from leibniz.propositio import Demonstratio, Enuntiatio, Expressio, Propositio
from leibniz.providers.residue_prover import _law_name, residue_law
from leibniz.trust import FAITHFULNESS_EDGE, NOVELTY_EDGE, PROOF_EDGE, TrustPolicy
from leibniz.types import ClaimType, EdgeEvidence, TrustTier, Verdict

CD, CP = "a >= 0 and b >= 0", "(a^2 + b^2) % 4 != 3"
CANON = residue_law(_law_name(CD, CP), CD, CP)[0]


def _prop(theorem_src, producer="lean_decided/kernel"):
    en = Enuntiatio(statement="t", claim_type=ClaimType.INVARIANT, falsifiable_claim="x",
                    claim_domain=CD, claim_property=CP)
    p = Propositio(enuntiatio=en, expressio=Expressio(theorem_src=theorem_src,
                                                      established_domain=CD))
    p.demonstratio = Demonstratio(proof_obligation="claim", proof_src="by decide")
    p.demonstratio.kernel_verified = True
    for edge, prod in ((NOVELTY_EDGE, "NoveltyGate"), (FAITHFULNESS_EDGE, producer),
                       (PROOF_EDGE, "LeanVerifier.discharge")):
        p.record(EdgeEvidence(edge=edge, tier=TrustTier.MECHANICAL, verdict=Verdict.PASS,
                              detail={}, producer=prod))
    return p


def _gate():
    return VerificationGate(policy=TrustPolicy())


def test_the_canonical_statement_is_promotable():
    assert _gate().is_promotable(_prop(CANON)) is True


def test_a_different_statement_under_a_rerendering_certificate_is_REFUSED():
    """The gap: the ensemble proved the autoformalizer's own theorem, which the certificate
    never bound. Kernel-valid, but not the certified claim."""
    other = "theorem llm_authored : ∀ (a b : ℤ), (0 ≤ a) → (0 ≤ b) → (a + b ≥ 0)"
    assert _gate().is_promotable(_prop(other)) is False


def test_a_non_rerendering_producer_is_unconstrained():
    """walnut and the ClaimProbe have no canonical form, so nothing is required of them —
    this change must not narrow anything outside the re-rendering fragments."""
    other = "theorem llm_authored : ∀ (n : ℤ), (0 ≤ n) → (n ≥ 0)"
    assert _gate().is_promotable(_prop(other, producer="ClaimProbe")) is True
    assert _gate().is_promotable(_prop(other, producer="walnut/recheck")) is True


def test_an_uncomputable_canonical_form_imposes_no_constraint():
    """A prose-only contract (no DSL) cannot be rendered, so the binding must not fire."""
    p = _prop("theorem anything : True")
    p.enuntiatio.claim_domain = ""
    p.enuntiatio.claim_property = ""
    assert _canonical_theorem_src("lean_decided/kernel", p) is None
    assert _gate().is_promotable(p) is True


def test_the_binding_only_ever_refuses():
    """Sanity: a prop the base gate already rejects is not rescued by this code."""
    p = _prop(CANON)
    p.edges = [e for e in p.edges if e.edge != PROOF_EDGE]      # drop the proof edge
    assert _gate().is_promotable(p) is False


# --- findings from adversarial review -------------------------------------------------------

import importlib  # noqa: E402

import pytest  # noqa: E402

from leibniz.gates.verification import _CANONICAL_BY_PRODUCER  # noqa: E402


def test_every_table_entry_resolves():
    """THE test that was missing: a stale entry silently unbinds its whole fragment, because
    `_canonical_theorem_src` degrades to 'no constraint'. Review found exactly that —
    `mixed_modular/kernel` named `mixed_modulus_law`, but the generator is `mixed_law`, so
    mixed-modulus claims were unconstrained and nothing failed."""
    for producer, (module, fn_name) in _CANONICAL_BY_PRODUCER.items():
        mod = importlib.import_module(module)
        assert callable(getattr(mod, fn_name, None)), f"{producer}: {module}.{fn_name} missing"
        assert callable(getattr(mod, "_law_name", None)), f"{producer}: {module}._law_name missing"


def test_the_table_covers_exactly_the_rerendering_producers():
    """Keep this map and the gate's allowlist in step: a fragment in one and not the other is
    either an unbound gap or a dead entry."""
    from leibniz.gates.faithfulness import _RERENDERING_BACKENDS
    assert len(_CANONICAL_BY_PRODUCER) == len(_RERENDERING_BACKENDS)


@pytest.mark.parametrize("producer,cd,cp", [
    ("lean_decided/kernel", CD, CP),
    ("mixed_modular/kernel", "a >= 0 and b >= 0",
     "((a+b)**2 % 4 == 1) == ((a+b) % 2 == 1)"),        # the fragment review found unbound
])
def test_each_fragment_binds_its_own_canonical_statement(producer, cd, cp):
    canonical = _canonical_theorem_src(producer, _contract(cd, cp))
    assert canonical is not None, f"{producer} computes no canonical form"
    good, bad = _contract(cd, cp, canonical), _contract(cd, cp, "theorem llm : True")
    for p in (good, bad):
        for edge, prod in ((NOVELTY_EDGE, "NoveltyGate"), (FAITHFULNESS_EDGE, producer),
                           (PROOF_EDGE, "LeanVerifier.discharge")):
            p.record(EdgeEvidence(edge=edge, tier=TrustTier.MECHANICAL, verdict=Verdict.PASS,
                                  detail={}, producer=prod))
    assert _gate().is_promotable(good) is True
    assert _gate().is_promotable(bad) is False


def _contract(cd, cp, theorem_src="t"):
    en = Enuntiatio(statement="t", claim_type=ClaimType.INVARIANT, falsifiable_claim="x",
                    claim_domain=cd, claim_property=cp)
    p = Propositio(enuntiatio=en, expressio=Expressio(theorem_src=theorem_src,
                                                      established_domain=cd))
    p.demonstratio = Demonstratio(proof_obligation="claim", proof_src="by decide")
    p.demonstratio.kernel_verified = True
    return p
