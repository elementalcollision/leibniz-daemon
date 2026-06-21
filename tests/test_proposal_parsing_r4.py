"""R4: the pipeline parses structured (JSON) proposals and falls back safely (CI-safe)."""
from __future__ import annotations

import json

from leibniz.pipeline import _parse_enuntiatio, _parse_expressio
from leibniz.types import ClaimType


def test_parse_enuntiatio_from_structured_json():
    draft = json.dumps({
        "statement": "comparison sort needs Omega(n log n)",
        "claim_type": "complexity_bound",
        "falsifiable_claim": "a comparison sort in o(n log n)",
        "claim_domain": "n >= 1",
        "claim_property": "cmps >= n",
    })
    en = _parse_enuntiatio(draft, "seed")
    assert en.statement.startswith("comparison sort")
    assert en.claim_type is ClaimType.COMPLEXITY_BOUND
    assert en.claim_domain == "n >= 1"
    assert en.claim_property == "cmps >= n"


def test_parse_enuntiatio_falls_back_for_prose():
    en = _parse_enuntiatio("just some prose seed", "seed")
    assert en.statement == "just some prose seed"
    assert en.claim_domain is None and en.claim_property is None


def test_parse_enuntiatio_unknown_claim_type_defaults():
    en = _parse_enuntiatio(json.dumps({"statement": "x", "claim_type": "nonsense"}), "seed")
    assert en.claim_type is ClaimType.COMPLEXITY_BOUND


def test_parse_expressio_from_structured_json():
    draft = json.dumps({
        "theorem_src": "theorem t : P",
        "imports": ["Mathlib.Tactic"],
        "established_domain": "n >= 1",
    })
    expr = _parse_expressio(draft)
    assert expr.theorem_src == "theorem t : P"
    assert expr.imports == ("Mathlib.Tactic",)
    assert expr.established_domain == "n >= 1"


def test_parse_expressio_falls_back_for_raw_string():
    expr = _parse_expressio("theorem t : P := by simp")
    assert expr.theorem_src == "theorem t : P := by simp"
    assert expr.established_domain is None
