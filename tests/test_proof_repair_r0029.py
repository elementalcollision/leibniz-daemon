"""ADR 0029: agentic proof repair — bounded draft → kernel-error → repair loop.

A frontier reasoner PROPOSES a proof; the kernel's error is fed back so it can repair,
a few bounded rounds. The trust boundary is unchanged and these tests pin it down:

- ``LeanVerifier.discharge`` is still the sole ``kernel_verified`` writer (the loop's
  ``check_proof_with_error`` is advisory; discharge re-checks before the stamp).
- N+1 is preserved: a repaired proof counts as ONE more *distinct* prover identity, so it
  can supply a deciding consensus vote but never lower the bar — a lone repaired proof
  never self-satisfies the default N+1=2.

CI-safe: the provider and the Lean backend are fakes; no network, no Docker.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from leibniz.consensus import ConsensusResult
from leibniz.propositio import Demonstratio, Enuntiatio, Expressio, Propositio
from leibniz.proof_repair import ProofRepairer, RepairingDemonstrate, RepairStats
from leibniz.trust import KERNEL_PRODUCER, PROOF_EDGE
from leibniz.types import ClaimType, EdgeEvidence, Role, TrustTier, Verdict
from leibniz.verifiers import LeanVerifier


# --- fakes -------------------------------------------------------------------

class _FakeBackend:
    """A Lean backend driven by a script: proof_src -> (ok, error). check_proof and
    check_proof_with_error agree (same script), so the real discharge stays consistent
    with the loop's advisory pre-check."""

    def __init__(self, script: dict):
        self.script = script
        self.checks: list[str] = []

    def check_proof_with_error(self, expr, proof_src):
        self.checks.append(proof_src)
        return self.script.get(proof_src, (False, "unknown proof"))

    def check_proof(self, expr, proof_src) -> bool:
        return self.script.get(proof_src, (False, ""))[0]

    def compile_statement(self, expr) -> bool:
        return True

    def closed_by_decision_procedure(self, expr) -> bool:
        return False


class _NoErrorBackend:
    """A backend WITHOUT check_proof_with_error — the loop must safely no-op."""

    def check_proof(self, expr, proof_src) -> bool:
        return True

    def compile_statement(self, expr) -> bool:
        return True

    def closed_by_decision_procedure(self, expr) -> bool:
        return False


class _FakeProvider:
    """Returns queued proof strings in order: [draft, repair1, repair2, ...]."""

    def __init__(self, outputs):
        self.outputs = list(outputs)
        self.calls: list[tuple] = []

    def propose(self, role: Role, ctx: str) -> str:
        self.calls.append(("propose", role, ctx))
        return self.outputs.pop(0)

    def repair_proof(self, theorem_src: str, failed_proof: str, error: str) -> str:
        self.calls.append(("repair", theorem_src, failed_proof, error))
        return self.outputs.pop(0)


def _expr(src="theorem t (n : Nat) : n + 0 = n") -> Expressio:
    return Expressio(theorem_src=src, imports=("Mathlib.Tactic",))


# --- ProofRepairer: the loop -------------------------------------------------

def test_repairer_closes_on_initial_draft():
    prov = _FakeProvider(["by good"])
    lean = LeanVerifier(_FakeBackend({"by good": (True, "")}))
    rep = ProofRepairer(provider=prov, lean=lean)
    out = rep.prove(_expr())
    assert out is not None
    demo, ev = out
    assert demo.kernel_verified and ev.verdict is Verdict.PASS     # discharge stamped it
    assert ev.producer == KERNEL_PRODUCER                          # kernel provenance preserved
    assert (rep.stats.attempted, rep.stats.closed, rep.stats.repairs) == (1, 1, 0)
    assert rep.stats.rounds_to_close == [0]
    assert [c[0] for c in prov.calls] == ["propose"]              # no repair needed


def test_repairer_repairs_against_the_kernel_error_then_closes():
    prov = _FakeProvider(["by bad", "by good"])
    lean = LeanVerifier(_FakeBackend({"by bad": (False, "type mismatch X"), "by good": (True, "")}))
    rep = ProofRepairer(provider=prov, lean=lean)
    out = rep.prove(_expr())
    assert out is not None and out[0].kernel_verified
    assert (rep.stats.closed, rep.stats.repairs) == (1, 1)
    assert rep.stats.rounds_to_close == [1]
    # the repair call received the failed proof AND the kernel's actual error
    repair_call = next(c for c in prov.calls if c[0] == "repair")
    assert repair_call[2] == "by bad" and repair_call[3] == "type mismatch X"


def test_repairer_gives_up_after_max_rounds():
    prov = _FakeProvider(["by b0", "by b1", "by b2"])  # draft + 2 repairs, all fail
    lean = LeanVerifier(_FakeBackend({}))  # everything fails (unknown proof)
    rep = ProofRepairer(provider=prov, lean=lean, max_rounds=2)
    assert rep.prove(_expr()) is None
    assert (rep.stats.attempted, rep.stats.closed, rep.stats.repairs) == (1, 0, 2)


def test_repairer_is_a_safe_noop_without_check_proof_with_error():
    prov = _FakeProvider(["by good"])
    rep = ProofRepairer(provider=prov, lean=LeanVerifier(_NoErrorBackend()))
    assert rep.prove(_expr()) is None
    assert rep.stats.attempted == 0 and prov.calls == []  # never even drafted


def test_repairer_survives_a_provider_that_raises():
    class _Boom:
        def propose(self, role, ctx):
            raise RuntimeError("provider down")

    rep = ProofRepairer(provider=_Boom(), lean=LeanVerifier(_FakeBackend({})))
    assert rep.prove(_expr()) is None  # a dead provider never blocks the pipeline


# --- RepairingDemonstrate: N+1-preserving fallback ---------------------------

@dataclass
class _FakeConsensus:
    result: ConsensusResult
    obligation: str = "claim"
    min_consensus: int = 2
    lean: object = None
    calls: int = 0

    def prove(self, expr) -> ConsensusResult:
        self.calls += 1
        return self.result


@dataclass
class _StubRepairer:
    result: object                      # (demo, edge) or None
    identity: str = "repair:anthropic"
    stats: RepairStats = field(default_factory=RepairStats)

    def prove(self, expr):
        return self.result


def _consensus_result(count, required=2, reached_proof=None, identities=frozenset()):
    if count >= required:
        demo = reached_proof or Demonstratio(
            proof_obligation="claim", proof_src="by base", kernel_verified=True, qed="Q.E.D.")
        edge = EdgeEvidence(edge=PROOF_EDGE, tier=TrustTier.MECHANICAL, verdict=Verdict.PASS,
                            detail={"consensus": count}, cost_units=10.0, producer=KERNEL_PRODUCER)
        return ConsensusResult(count, required, 2, edge, demo, identities, demo)
    edge = EdgeEvidence(edge=PROOF_EDGE, tier=TrustTier.MECHANICAL, verdict=Verdict.FAIL,
                        detail={"consensus": count}, cost_units=10.0)
    return ConsensusResult(count, required, 2, edge, None, identities, None)


def _repair_pass():
    demo = Demonstratio(proof_obligation="claim", proof_src="by repaired",
                        kernel_verified=True, qed="Q.E.D.")
    edge = EdgeEvidence(edge=PROOF_EDGE, tier=TrustTier.MECHANICAL, verdict=Verdict.PASS,
                        detail={"obligation": "claim", "qed": "Q.E.D."},
                        cost_units=10.0, producer=KERNEL_PRODUCER)
    return (demo, edge)


def _prop(src="theorem t (n:Nat) : n + 0 = n") -> Propositio:
    return Propositio(
        enuntiatio=Enuntiatio(statement="c", claim_type=ClaimType.INVARIANT, falsifiable_claim="n"),
        expressio=Expressio(theorem_src=src, imports=("Mathlib.Tactic",)),
    )


def _proof_edges(prop):
    return [e for e in prop.edges if e.edge == PROOF_EDGE]


def test_demonstrate_uses_consensus_when_it_reaches_and_skips_repair():
    con = _FakeConsensus(_consensus_result(2, identities=frozenset({"model:a", "model:b"})))

    class _Boom:
        identity = "repair:anthropic"
        stats = RepairStats()

        def prove(self, expr):
            raise AssertionError("repair must not run when consensus already reached")

    out = RepairingDemonstrate(con, _Boom()).run(_prop())
    edges = _proof_edges(out)
    assert len(edges) == 1 and edges[0].verdict is Verdict.PASS
    assert out.demonstratio.kernel_verified


def test_repair_supplies_the_deciding_vote_when_consensus_is_one_short():
    # base ensemble got ONE distinct kernel proof; repair (a distinct identity) makes two.
    con = _FakeConsensus(_consensus_result(1, identities=frozenset({"model:a"})))
    rep = _StubRepairer(_repair_pass())
    out = RepairingDemonstrate(con, rep).run(_prop())
    edges = _proof_edges(out)
    assert len(edges) == 1 and edges[0].verdict is Verdict.PASS      # exactly one, the PASS
    assert edges[0].detail["consensus"] == 2 and edges[0].detail["via"] == "repair"
    assert edges[0].producer == KERNEL_PRODUCER                      # kernel provenance kept
    assert out.demonstratio.proof_src == "by repaired" and out.demonstratio.kernel_verified
    assert rep.stats.promulgated == 1


def test_lone_repair_proof_cannot_self_satisfy_n_plus_one():
    # nobody in the base ensemble proved it; repair alone is ONE identity < required 2.
    con = _FakeConsensus(_consensus_result(0, identities=frozenset()))
    rep = _StubRepairer(_repair_pass())
    out = RepairingDemonstrate(con, rep).run(_prop())
    edges = _proof_edges(out)
    assert len(edges) == 1 and edges[0].verdict is Verdict.FAIL      # NOT promulgated
    assert not (out.demonstratio and out.demonstratio.kernel_verified)
    assert rep.stats.promulgated == 0


def test_repair_promulgates_alone_only_when_operator_opts_into_consensus_one():
    con = _FakeConsensus(_consensus_result(0, required=1, identities=frozenset()), min_consensus=1)
    rep = _StubRepairer(_repair_pass())
    out = RepairingDemonstrate(con, rep).run(_prop())
    edges = _proof_edges(out)
    assert len(edges) == 1 and edges[0].verdict is Verdict.PASS
    assert edges[0].detail["consensus"] == 1


def test_repair_failure_records_the_short_consensus_fail_edge():
    con = _FakeConsensus(_consensus_result(1, identities=frozenset({"model:a"})))
    out = RepairingDemonstrate(con, _StubRepairer(None)).run(_prop())  # repair found nothing
    edges = _proof_edges(out)
    assert len(edges) == 1 and edges[0].verdict is Verdict.FAIL


def test_decomposition_layer_runs_before_repair():
    # direct consensus is short; the decomposer closes it -> repair must not run.
    con = _FakeConsensus(_consensus_result(1, identities=frozenset({"model:a"})))

    class _Decomposer:
        def prove(self, expr):
            return _consensus_result(2, identities=frozenset({"model:a", "model:b"}))

    class _Boom:
        identity = "repair:anthropic"
        stats = RepairStats()

        def prove(self, expr):
            raise AssertionError("repair must not run when decomposition closed it")

    out = RepairingDemonstrate(con, _Boom(), decomposer=_Decomposer()).run(_prop())
    edges = _proof_edges(out)
    assert len(edges) == 1 and edges[0].verdict is Verdict.PASS
    assert out.demonstratio.kernel_verified


def test_repair_runs_after_decomposition_also_comes_up_short():
    con = _FakeConsensus(_consensus_result(1, identities=frozenset({"model:a"})))

    class _Decomposer:
        def prove(self, expr):
            return _consensus_result(1, identities=frozenset({"model:a"}))  # still short

    rep = _StubRepairer(_repair_pass())
    out = RepairingDemonstrate(con, rep, decomposer=_Decomposer()).run(_prop())
    edges = _proof_edges(out)
    assert len(edges) == 1 and edges[0].verdict is Verdict.PASS and edges[0].detail["via"] == "repair"


# --- AnthropicProvider.repair_proof prompt (statement-fixed, error-fed) -------

def test_repair_proof_prompt_fixes_statement_and_feeds_error(monkeypatch):
    from leibniz.providers.anthropic_provider import AnthropicProvider, _PROOF_SYSTEM

    captured = {}

    def fake_chat(self, content, system=None):
        captured["content"] = content
        captured["system"] = system
        return "by exact rfl"

    monkeypatch.setattr(AnthropicProvider, "_chat", fake_chat)
    out = AnthropicProvider().repair_proof("theorem t : n + 0 = n", "by sorry", "error: unsolved goals")
    assert out == "by exact rfl"
    c = captured["content"]
    assert "theorem t : n + 0 = n" in c and "error: unsolved goals" in c
    assert "by sorry" in c
    # the reasoner is told to change only the proof, never the statement
    assert "do not change" in c.lower() or "do NOT change" in c
    # and it must use the PROOF system prompt (bare script), NOT the JSON one — else the
    # kernel gets `{"script": ...}` and can never elaborate it (ADR 0029 live-run bug).
    assert captured["system"] == _PROOF_SYSTEM


def test_proof_draft_uses_the_bare_script_system_not_json(monkeypatch):
    from leibniz.providers.anthropic_provider import AnthropicProvider, _PROOF_SYSTEM, _SYSTEM

    seen = {}

    def fake_chat(self, content, system=None):
        seen["system"] = system
        return "by simp"

    monkeypatch.setattr(AnthropicProvider, "_chat", fake_chat)
    out = AnthropicProvider().propose(Role.PROOF_DRAFT, "theorem t : True")
    assert out == "by simp"
    assert seen["system"] == _PROOF_SYSTEM and seen["system"] != _SYSTEM
