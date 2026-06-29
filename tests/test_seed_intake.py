"""Guards for ADR 0041 Phase 4 seed intake: validated seeds reach ONLY proposer seams, never a decider.

Pins: a TARGET seed becomes proposal-side steering (gates nothing) and a quarantined/non-target seed
does not; a CONSTRUCTION seed becomes a sandbox job (runs only sandboxed) and a non-validated one does
not; nothing here produces a verdict or touches a gate.
"""
from __future__ import annotations

from leibniz.seed_intake import admissible_targets, construction_task, seed_steering
from leibniz.seeds import Seed, SeedKind, SeedProvenance, SeedStatus
from leibniz.tools.sandbox import SandboxTask

_PROV = SeedProvenance(source_id="arXiv:2606.1")


def _validated(kind, payload):
    return Seed(kind=kind, payload=payload, provenance=_PROV, proof_of_use="p",
                status=SeedStatus.VALIDATED)


def test_validated_target_becomes_steering_context():
    t = _validated(SeedKind.TARGET, {"title": "An open conjecture about A(n,d,w)"})
    block = seed_steering([t])
    assert "research target" in block and "A(n,d,w)" in block and "[arXiv:2606.1]" in block
    # it is framed as an UNTRUSTED hint, not a decision
    assert "gates still" in block.lower()


def test_only_validated_targets_steer():
    quar = Seed(kind=SeedKind.TARGET, payload={"title": "quarantined"}, provenance=_PROV,
                proof_of_use="p", status=SeedStatus.QUARANTINED)
    floor = _validated(SeedKind.FLOOR, {"cells": {(7, 4, 3): 5}})
    assert seed_steering([quar, floor]) == ""              # neither steers
    assert admissible_targets([quar, floor]) == []


def test_no_seeds_yields_empty_steering():
    assert seed_steering([]) == ""                         # a daemon with no seeds is unchanged


def test_validated_construction_becomes_a_sandbox_task():
    c = _validated(SeedKind.CONSTRUCTION,
                   {"program_source": "def construct(n,d,w): return []", "args": {"n": 7, "d": 4, "w": 3}})
    task = construction_task(c)
    assert isinstance(task, SandboxTask) and "def construct" in task.program and task.args["n"] == 7


def test_non_validated_or_non_construction_yields_no_task():
    unval = Seed(kind=SeedKind.CONSTRUCTION, payload={"program": "x"}, provenance=_PROV,
                 proof_of_use="p")                          # status=UNTRUSTED (default)
    target = _validated(SeedKind.TARGET, {"title": "t"})
    assert construction_task(unval) is None                # only VALIDATED constructions run
    assert construction_task(target) is None               # a target is not a construction
