"""ADR 0026: steer the conjecturer toward non-trivial structure.

ADR 0025 made `ring`/`nlinarith`-decidable identities TRIVIAL; ADR 0022 had been
steering toward exactly that elementary-arithmetic space. This realigns the CONJECTURE
prompt: keep the in-DSL contract (so faithfulness can certify) but demand claims a
single decision procedure cannot close. Prompt-only / proposal-side — CI-safe."""
from __future__ import annotations

from leibniz.providers.anthropic_provider import _DSL, _PROMPTS
from leibniz.types import Role


def test_conjecture_prompt_names_the_full_trivial_tactic_set():
    p = _PROMPTS[Role.CONJECTURE]
    # the model must know every tactic that would get its claim filtered as TRIVIAL
    for tac in ("decide", "simp", "omega", "trivial", "aesop", "ring", "nlinarith"):
        assert tac in p
    assert "TRIVIAL" in p


def test_conjecture_prompt_steers_toward_nontrivial_structure():
    p = _PROMPTS[Role.CONJECTURE]
    low = p.lower()
    assert "induction" in low
    assert "helper lemma" in low or "lemma" in low
    assert "polynomial" in low          # explicitly forbids the ring-trivial class
    assert "divisibility" in low or "modular" in low  # the non-trivial-yet-encodable band


def test_conjecture_prompt_still_requires_the_encodable_contract():
    # the ADR 0022 requirement must survive: non-triviality + encodability TOGETHER.
    p = _PROMPTS[Role.CONJECTURE]
    assert _DSL in p
    assert "claim_domain" in p and "claim_property" in p
