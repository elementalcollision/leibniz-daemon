"""R4: proposal providers are env-gated and routed correctly (CI-safe).

No network: these check availability gating and RoleRouter dispatch with fakes.
A creds-gated live smoke documents the FORMALIZE->kernel path for when creds land.
"""
from __future__ import annotations

import os

import pytest

from leibniz.providers import ProviderUnavailable
from leibniz.providers.anthropic_provider import AnthropicProvider
from leibniz.providers.prover import ProverClient
from leibniz.providers.router import RoleRouter
from leibniz.types import Role


def test_anthropic_unavailable_and_raises_without_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    p = AnthropicProvider()
    assert p.available() is False
    with pytest.raises(ProviderUnavailable):
        p.propose(Role.CONJECTURE, "seed")


def test_prover_unavailable_and_raises_without_url(monkeypatch):
    monkeypatch.delenv("LEIBNIZ_PROVER_URL", raising=False)
    pc = ProverClient()
    assert pc.available() is False
    with pytest.raises(ProviderUnavailable):
        pc.propose(Role.PROOF_DRAFT, "theorem t : P")


class _Recorder:
    def __init__(self, tag: str) -> None:
        self.tag = tag
        self.calls: list[Role] = []

    def propose(self, role: Role, context: str) -> str:
        self.calls.append(role)
        return self.tag

    def available(self) -> bool:
        return True


def test_router_dispatches_proof_draft_to_prover_else_autoformalizer():
    af, pr = _Recorder("af"), _Recorder("prover")
    router = RoleRouter(autoformalizer=af, prover=pr)
    assert router.propose(Role.PROOF_DRAFT, "x") == "prover"
    assert router.propose(Role.CONJECTURE, "x") == "af"
    assert router.propose(Role.FORMALIZE, "x") == "af"
    assert pr.calls == [Role.PROOF_DRAFT]
    assert af.calls == [Role.CONJECTURE, Role.FORMALIZE]


def test_router_available_requires_both_legs():
    class Up:
        def available(self):
            return True

    class Down:
        def available(self):
            return False

    assert RoleRouter(Up(), Up()).available() is True
    assert RoleRouter(Up(), Down()).available() is False


@pytest.mark.lean
@pytest.mark.skipif(
    not os.environ.get("ANTHROPIC_API_KEY"),
    reason="live: needs ANTHROPIC_API_KEY (and the Lean image)",
)
def test_formalize_then_kernel_runs_live():
    from leibniz.backends.lean_cli import LeanCliBackend, available
    from leibniz.pipeline import _parse_expressio
    from leibniz.verifiers import LeanVerifier

    if not available():
        pytest.skip("Lean image not available")
    draft = AnthropicProvider().propose(Role.FORMALIZE, "for all natural numbers n, n + 0 = n")
    expr = _parse_expressio(draft)
    # The wiring runs end to end; the statement elaborates or not, but the kernel is consulted.
    assert isinstance(LeanVerifier(LeanCliBackend()).validate_statement(expr), bool)
