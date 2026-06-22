"""ADR 0024: lemma-decomposition proving strategy.

A DecompositionProver reshapes a PROOF_DRAFT into a structured `have`/`suffices` proof
and slots into the ensemble as an extra independent attempt. Pure proposal-side: the
kernel (LeanVerifier.discharge) still solely decides and checks the whole structured
proof. CI-safe — no network (provider construction and prompt reshaping are local)."""
from __future__ import annotations

from leibniz.providers.decomposition_prover import _DECOMPOSE_INSTRUCTION, DecompositionProver
from leibniz.types import Role


class _FakeBase:
    def __init__(self):
        self.calls: list[tuple] = []

    def available(self) -> bool:
        return True

    def propose(self, role: Role, context: str) -> str:
        self.calls.append((role, context))
        return "by\n  have h : 1 = 1 := rfl\n  exact h"


def test_proof_draft_is_decomposed():
    base = _FakeBase()
    out = DecompositionProver(base).propose(Role.PROOF_DRAFT, "theorem t : 1 = 1")
    role, ctx = base.calls[-1]
    assert role is Role.PROOF_DRAFT
    assert ctx.startswith(_DECOMPOSE_INSTRUCTION)   # the strategy is injected
    assert "theorem t : 1 = 1" in ctx               # the real goal is preserved
    assert out.startswith("by")                     # base output passed through


def test_non_proof_roles_pass_through_unchanged():
    base = _FakeBase()
    DecompositionProver(base).propose(Role.CONJECTURE, "a seed")
    assert base.calls[-1] == (Role.CONJECTURE, "a seed")  # verbatim


def test_instruction_is_about_lemma_decomposition():
    assert "have" in _DECOMPOSE_INSTRUCTION
    assert "DECOMPOSITION" in _DECOMPOSE_INSTRUCTION
    assert "by" in _DECOMPOSE_INSTRUCTION  # still asks for a tactic block


def test_available_delegates_and_defaults_true():
    class _NoAvail:
        def propose(self, role, ctx):
            return ""
    assert DecompositionProver(_NoAvail()).available() is True  # base has none -> assume usable

    class _Unavail:
        def available(self):
            return False

        def propose(self, role, ctx):
            return ""
    assert DecompositionProver(_Unavail()).available() is False  # delegates


def test_decomposed_output_flows_through_normalize_proof():
    # the structured `have` proof survives normalization (no fence / no restated theorem),
    # so it reaches discharge exactly like a flat proof — the kernel checks it whole.
    from leibniz.consensus import normalize_proof
    s = "by\n  have h : 1 = 1 := rfl\n  exact h"
    assert normalize_proof(s) == s


def test_ensemble_adds_decomposition_variants(monkeypatch):
    from leibniz.assembly import prover_ensemble
    from leibniz.providers.huggingface_provider import HuggingFaceProvider
    monkeypatch.setenv("LEIBNIZ_HF_PROVER_MODELS", "m1,m2")
    monkeypatch.setenv("LEIBNIZ_DECOMPOSE", "1")
    ens = prover_ensemble()
    assert len(ens) == 3  # 2 base + 1 decomposition variant
    assert isinstance(ens[0], HuggingFaceProvider)
    assert isinstance(ens[2], DecompositionProver)
    assert ens[2].base is ens[0]  # wraps the first (strongest) base prover


def test_ensemble_decompose_can_be_disabled(monkeypatch):
    from leibniz.assembly import prover_ensemble
    monkeypatch.setenv("LEIBNIZ_HF_PROVER_MODELS", "m1,m2")
    monkeypatch.setenv("LEIBNIZ_DECOMPOSE", "0")
    ens = prover_ensemble()
    assert len(ens) == 2
    assert not any(isinstance(p, DecompositionProver) for p in ens)
