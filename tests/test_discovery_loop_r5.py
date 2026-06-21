"""ADR 0009: the closed KFM → SURVEY discovery loop (CI-safe; stubs, no Lean/LLM).

circadian_cycle stays single-shot; run_cycles re-seeds each cycle from the archive
(recombined curiosity-biased parents + fresh survey), with stagnation fallback.
"""
from __future__ import annotations

from leibniz.daemon import CycleReport, Leibniz
from leibniz.gates.verification import VerificationGate
from leibniz.propositio import Enuntiatio, Propositio
from leibniz.selection import KFM, Archive
from leibniz.trust import TrustPolicy
from leibniz.types import ClaimType


def _prop(statement: str, bd=()) -> Propositio:
    p = Propositio(enuntiatio=Enuntiatio(statement=statement, claim_type=ClaimType.COMPLEXITY_BOUND,
                                         falsifiable_claim="x"))
    p.behavior_descriptor = bd
    return p


# --- KFM.recombination_seeds -------------------------------------------------

def test_recombination_seeds_pairs_parents():
    arc = Archive()
    arc.consider(_prop("alpha", (0.0, 0.0, 0.0)), 0.9)
    arc.consider(_prop("beta", (0.9, 0.9, 0.9)), 0.5)
    arc.consider(_prop("gamma", (0.4, 0.0, 0.0)), 0.3)
    seeds = KFM(arc).recombination_seeds(k=3)
    assert len(seeds) == 2  # N parents -> N-1 recombined seeds
    assert all("combining features" in s for s in seeds)


def test_recombination_seeds_empty_when_too_few_elites():
    assert KFM(Archive()).recombination_seeds() == []
    arc = Archive()
    arc.consider(_prop("solo", (0.0, 0.0, 0.0)), 1.0)
    assert KFM(arc).recombination_seeds() == []  # one elite -> no pair


# --- daemon stubs ------------------------------------------------------------

class _Survey:
    def __init__(self):
        self.calls = 0

    def run(self, domain):
        self.calls += 1
        return ["seed-a", "seed-b"]


class _Conjecture:
    def run(self, seed):
        return _prop(seed)  # descriptor is (re)computed at _settle


class _FormalizeNull:
    def run(self, prop):
        return None  # quarantine before proof -> cycles run fast, archive still fills


class _Runtime:
    def __init__(self):
        self.memory = []

    def remember(self, p):
        self.memory.append(p)

    def now_phase(self):
        return "WAKE"

    def recall_recent(self, n):
        return self.memory[-n:]

    def witness(self, p, n):
        return []


class _Stage:  # derive / demonstrate / promulgate are never reached here
    def run(self, *a, **k):
        return a[0] if a else None


def _daemon() -> Leibniz:
    return Leibniz(
        runtime=_Runtime(), survey=_Survey(), conjecture=_Conjecture(),
        formalize=_FormalizeNull(), derive=_Stage(), demonstrate=_Stage(),
        promulgate=_Stage(), verification=VerificationGate(TrustPolicy()), kfm=KFM(Archive()),
    )


def test_circadian_cycle_is_still_single_shot():
    d = _daemon()
    rep = d.circadian_cycle()
    assert rep.seeds == 2 and rep.conjectured == 2
    assert d.survey.calls == 1


def test_next_seeds_uses_survey_first_then_recombination():
    d = _daemon()
    assert d._next_seeds(True, 2, 4) == ["seed-a", "seed-b"]  # cold / fresh_only
    # populate two elites in distinct cells so recombination has a pair
    d.kfm.archive.consider(_prop("p1", (0.0, 0.0, 0.0)), 0.9)
    d.kfm.archive.consider(_prop("p2", (0.9, 0.9, 0.9)), 0.5)
    seeds = d._next_seeds(False, 1, 4)
    assert any("combining features" in s for s in seeds)  # archive re-seeded the cycle


def test_run_cycles_returns_n_reports_and_fills_the_archive():
    d = _daemon()
    reports = d.run_cycles(3)
    assert len(reports) == 3
    assert all(isinstance(r, CycleReport) for r in reports)
    assert len(d.kfm.archive.cells) >= 1
    assert d.survey.calls >= 1
