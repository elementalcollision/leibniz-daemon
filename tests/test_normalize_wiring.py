"""Pure-stdlib test of the R1c normalize wiring (always runs in CI).

The pipeline prefers a backend's elaborator-canonical structural hash and falls
back to the textual hash when the backend can't normalize (fakes, or a statement
that doesn't elaborate).
"""
from __future__ import annotations

from leibniz.pipeline import _normalized_hash
from leibniz.propositio import Expressio
from leibniz.verifiers import normalize_statement


class _Lean:
    def __init__(self, backend):
        self.backend = backend


class _BackendStructural:
    def normalize_statement(self, expr):
        return "STRUCTURAL_HASH"


class _BackendNoNormalizer:
    pass


class _BackendNormalizerReturnsNone:
    def normalize_statement(self, expr):
        return None


def test_prefers_backend_structural_hash():
    expr = Expressio(theorem_src="theorem t : P")
    assert _normalized_hash(_Lean(_BackendStructural()), expr) == "STRUCTURAL_HASH"


def test_falls_back_when_backend_has_no_normalizer():
    expr = Expressio(theorem_src="theorem t : P")
    assert _normalized_hash(_Lean(_BackendNoNormalizer()), expr) == normalize_statement(expr.theorem_src)


def test_falls_back_when_normalizer_returns_none():
    expr = Expressio(theorem_src="theorem t : P")
    assert _normalized_hash(_Lean(_BackendNormalizerReturnsNone()), expr) == normalize_statement(expr.theorem_src)
