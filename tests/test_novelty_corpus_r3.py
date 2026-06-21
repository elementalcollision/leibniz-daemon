"""R3 exit test: a re-derivation of the Omega(n log n) comparison-sort bound is
caught KNOWN by the real corpus, end-to-end through the NoveltyGate.

The candidate restates the corpus theorem with renamed variables; the R1c
structural hash collides, so the novelty gate marks it KNOWN — exactly the
"stop rediscovering textbooks" behaviour. Lean-gated.
"""
from __future__ import annotations

import pytest

from leibniz.backends.lean_cli import LeanCliBackend, available
from leibniz.corpus import CorpusBackend
from leibniz.gates.novelty import NoveltyGate
from leibniz.propositio import Enuntiatio, Expressio, Propositio
from leibniz.types import ClaimSignature, ClaimType, FinishReason, TrustTier, Verdict
from leibniz.verifiers import LeanVerifier

pytestmark = [
    pytest.mark.lean,
    pytest.mark.skipif(
        not available(), reason="Lean container leibniz-lean:v4.31.0 not available"
    ),
]


def test_omega_n_log_n_rederivation_is_caught_known():
    backend = LeanCliBackend()
    corpus = CorpusBackend.from_json()
    known_hash = next(e.formal_hash for e in corpus.entries
                      if e.name == "comparison_sort_lower_bound")

    # Re-derive the bound with renamed binders (n->a, h->b): structurally identical.
    restated = Expressio(
        theorem_src=(
            "theorem my_rediscovery : forall a b : Nat, "
            "2 ^ b >= Nat.factorial a -> b >= Nat.log 2 (Nat.factorial a)"
        ),
        imports=("Mathlib.Tactic",),
    )
    h = backend.normalize_statement(restated)
    assert h is not None
    assert h == known_hash, "alpha-renamed restatement must hash to the known result"
    restated.normalized_hash = h

    prop = Propositio(
        enuntiatio=Enuntiatio(
            statement="comparison sort needs Omega(n log n) comparisons",
            claim_type=ClaimType.COMPLEXITY_BOUND,
            falsifiable_claim="a comparison sort using o(n log n) comparisons",
        ),
        expressio=restated,
        signature=ClaimSignature(
            claim_type=ClaimType.COMPLEXITY_BOUND,
            subject="comparison_sort",
            relation="lower_bound",
            formal_hash=h,
        ),
    )

    ev = NoveltyGate(corpus, LeanVerifier(backend)).check(prop)
    assert ev.tier is TrustTier.MECHANICAL
    assert ev.verdict is Verdict.FAIL
    assert prop.finish_reason is FinishReason.KNOWN
