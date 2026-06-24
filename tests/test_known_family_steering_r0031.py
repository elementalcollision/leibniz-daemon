"""ADR 0031 Layer 3: steer the conjecturer AWAY from the classic known families.

The organic run rediscovered Fermat's little theorem because the CONJECTURE prompt even
used a consecutive-product divisibility as its positive example. Layer 3 names the known
families as territory to avoid (they are now corpus-quarantined as KNOWN) and replaces the
example with one NOT in those families. Prompt-only / proposal-side — CI-safe.
"""
from __future__ import annotations

from leibniz.providers.anthropic_provider import _PROMPTS
from leibniz.types import Role


def test_conjecture_prompt_names_the_known_families_to_avoid():
    low = _PROMPTS[Role.CONJECTURE].lower()
    assert "fermat" in low
    assert "power-residue" in low or "n^k" in low
    assert "consecutive" in low
    assert "do not propose" in low and "known" in low


def test_conjecture_prompt_example_is_not_a_known_family():
    # the FORMAT example must NOT be the old consecutive-product classic; it is now the
    # n^2+3 mod 4 fact (off the seeded families).
    p = _PROMPTS[Role.CONJECTURE]
    assert "(n^2 + 3) % 4 != 2" in p
    # the old example asserted 6 | n(n+1)(n+2) as the thing to DO — that exact positive
    # exemplar is gone (the expression now appears only in the AVOID list).
    assert 'claim_property "n*(n+1)*(n+2) % 6 == 0"' not in p
