"""ADR 0018: the discovery frontier — proposal-side steering toward novel-yet-
tractable conjectures (CI-safe; no Lean, no network)."""
from __future__ import annotations

from leibniz.discovery import (
    DiscoveryNotebook,
    FrontierController,
    difficulty,
    quality,
    steer,
    weakening_seeds,
)
from leibniz.daemon import Leibniz
from leibniz.gates.verification import VerificationGate
from leibniz.propositio import Demonstratio, Enuntiatio, Expressio, Propositio
from leibniz.selection import KFM, Archive
from leibniz.trust import TrustPolicy
from leibniz.types import ClaimType, FinishReason


def _prop(statement="claim", *, src=None, promulgated=False, reason=None) -> Propositio:
    p = Propositio(
        enuntiatio=Enuntiatio(statement=statement, claim_type=ClaimType.STRUCTURAL, falsifiable_claim="no"),
        expressio=Expressio(theorem_src=src) if src else None,
    )
    p.promulgated = promulgated
    p.finish_reason = reason
    return p


# --- difficulty (mechanical proxy) -------------------------------------------

def test_difficulty_is_bounded_and_orders_simple_below_complex():
    simple = _prop(src="theorem t : 0 < 1")
    complex_ = _prop(src="theorem t : forall a b c : Nat, a <= b -> b <= c -> a + b * c <= c ^ 2 + a")
    assert 0.0 <= difficulty(simple) <= 1.0
    assert 0.0 <= difficulty(complex_) <= 1.0
    assert difficulty(simple) < difficulty(complex_)


def test_difficulty_handles_empty():
    assert difficulty(Propositio(enuntiatio=Enuntiatio(statement="", claim_type=ClaimType.STRUCTURAL, falsifiable_claim=""))) == 0.0


# --- graded quality ----------------------------------------------------------

def test_quality_promulgated_is_one():
    assert quality(_prop(promulgated=True, reason=FinishReason.PROMULGATED)) == 1.0


def test_quality_peaks_at_moderate_difficulty_not_simplest():
    # A frontier near-miss must outrank BOTH a vacuous trivially-shaped statement and
    # a wild open-problem shape (the plain 1-difficulty form rewarded simpler text).
    vacuous = _prop(src="theorem t : 0 < 1", reason=FinishReason.UNPROVEN)
    moderate = _prop(src="theorem t : forall a b : Nat, a <= b -> a + b * 2 <= 3 * b + a", reason=FinishReason.UNPROVEN)
    wild = _prop(src="theorem t : forall a b c d : Nat, a <= b -> b <= c -> c <= d -> a + b * c <= d ^ 3 + a * b * c", reason=FinishReason.UNPROVEN)
    qv, qm, qw = quality(vacuous), quality(moderate), quality(wild)
    assert qm > qv and qm > qw
    assert all(0.40 <= q <= 0.60 for q in (qv, qm, qw))


def test_notebook_treats_kernel_proved_as_proven_even_if_over_budget():
    nb = DiscoveryNotebook()
    p = _prop("budget-refused law")
    p.demonstratio = Demonstratio(proof_obligation="t", kernel_verified=True, qed="Q.E.D.")
    nb.record(p, FinishReason.OVER_BUDGET)  # kernel proved, held back at promotion
    assert nb.proven == ["budget-refused law"]  # a tractable shape to emulate, not dropped
    assert nb.too_hard == [] and nb.avoid == []


def test_quality_dead_end_is_zero():
    assert quality(_prop(reason=FinishReason.KNOWN)) == 0.0
    assert quality(_prop(reason=FinishReason.TRIVIAL)) == 0.0


# --- DiscoveryNotebook -------------------------------------------------------

def test_notebook_routes_outcomes_and_steers():
    nb = DiscoveryNotebook(capacity=3)
    assert nb.steering() == ""  # cold start: no steering
    nb.record(_prop("a proven law", promulgated=True, reason=FinishReason.PROMULGATED))
    nb.record(_prop("a hard one", reason=FinishReason.UNPROVEN))
    nb.record(_prop("a known one", reason=FinishReason.KNOWN))
    assert nb.proven == ["a proven law"]
    assert nb.too_hard == ["a hard one"]
    assert nb.avoid == ["a known one"]
    s = nb.steering()
    assert "PROVEN" in s and "a proven law" in s
    assert "TRIVIAL or already KNOWN" in s and "a known one" in s
    assert "TOO HARD" in s and "a hard one" in s


def test_notebook_is_bounded_and_dedups():
    nb = DiscoveryNotebook(capacity=2)
    for i in range(5):
        nb.record(_prop(f"hard {i}", reason=FinishReason.UNPROVEN))
    nb.record(_prop("hard 4", reason=FinishReason.UNPROVEN))  # dup of last
    assert nb.too_hard == ["hard 3", "hard 4"]  # only most-recent `capacity`, no dup


# --- FrontierController (thermostat) -----------------------------------------

def test_frontier_eases_off_when_nothing_proves():
    fc = FrontierController(target=0.45, window=8)
    for _ in range(8):
        fc.record(False)
    before = fc.target
    fc.update()
    assert fc.target < before  # all failures -> aim easier
    assert fc.target >= fc.floor


def test_frontier_pushes_when_too_easy():
    fc = FrontierController(target=0.45, window=8)
    for _ in range(8):
        fc.record(True)
    fc.update()
    assert fc.target > 0.45 and fc.target <= fc.ceil


def test_frontier_holds_on_thin_evidence():
    fc = FrontierController(target=0.45, window=8)
    fc.record(False)
    fc.update()  # only 1 sample -> no lurch
    assert fc.target == 0.45


def test_frontier_persists_and_resumes(tmp_path):
    fc = FrontierController(target=0.45)
    for _ in range(8):
        fc.record(False)
    fc.update()  # moves the band + holds the outcome window
    p = tmp_path / "frontier.json"
    fc.save(p)
    resumed = FrontierController.load(p)
    assert resumed.target == fc.target
    assert resumed._recent == fc._recent[-resumed.window:]


def test_frontier_load_missing_is_default(tmp_path):
    fc = FrontierController.load(tmp_path / "absent.json")
    assert fc.target == 0.45 and fc._recent == []  # cold start unchanged


def test_daemon_persists_band_across_run(tmp_path):
    path = str(tmp_path / "frontier.json")
    fc = FrontierController()
    d = _daemon(notebook=DiscoveryNotebook(), frontier=fc)
    d.frontier_path = path
    d.run_cycles(2)
    assert (tmp_path / "frontier.json").exists()
    assert FrontierController.load(path).target == fc.target  # the run's band persisted


def test_frontier_reexplores_when_pinned_at_floor():
    # Overshot a narrow window down to the floor with nothing proving: must jump back
    # and re-search, not pin at the floor at 0% forever (ADR 0018 review).
    fc = FrontierController(target=0.15)  # at the floor
    for _ in range(8):
        fc.record(False)
    fc.update()
    assert fc.target > 0.15
    assert fc._recent == []  # evidence window reset for the new region


def test_frontier_band_is_descriptive():
    assert "difficulty" in FrontierController(target=0.5).band()


# --- weakening seeds + steer -------------------------------------------------

def test_weakening_seeds_reference_statements_and_cap():
    seeds = weakening_seeds(["claim one", "claim two", "claim three"], k=2)
    assert len(seeds) == 2
    assert all("STRICTLY WEAKER" in s for s in seeds)
    assert "claim one" in seeds[0] and "claim two" in seeds[1]


def test_weakening_is_depth_one():
    once = weakening_seeds(["fresh claim"], k=2)
    assert len(once) == 1
    # a statement that is already a weakening instruction is never re-weakened
    assert weakening_seeds(once, k=2) == []


def test_steer_is_noop_without_signals():
    assert steer("raw seed", None, None) == "raw seed"


def test_steer_prepends_band_and_lessons():
    nb = DiscoveryNotebook()
    nb.record(_prop("proven law", promulgated=True, reason=FinishReason.PROMULGATED))
    fc = FrontierController()
    out = steer("raw seed", nb, fc)
    assert "Seed: raw seed" in out
    assert "Aim for difficulty" in out          # band
    assert "Lessons from the ledger" in out      # notebook


# --- daemon integration ------------------------------------------------------

class _CaptureConjecture:
    def __init__(self):
        self.seen: list[str] = []

    def run(self, seed):
        self.seen.append(seed)
        return _prop("conjecture-stmt")  # fixed statement; no finish_reason -> UNPROVEN


class _Survey:
    def run(self, domain):
        return ["seed-a", "seed-b"]


class _FormalizeNull:
    def run(self, prop):
        return None  # quarantine before proof -> settles as UNPROVEN


class _Runtime:
    def remember(self, p):
        pass


class _Stage:
    def run(self, *a, **k):
        return a[0] if a else None


def _daemon(*, notebook=None, frontier=None, conjecture=None) -> Leibniz:
    return Leibniz(
        runtime=_Runtime(), survey=_Survey(), conjecture=conjecture or _CaptureConjecture(),
        formalize=_FormalizeNull(), derive=_Stage(), demonstrate=_Stage(), promulgate=_Stage(),
        verification=VerificationGate(TrustPolicy()), kfm=KFM(Archive()),
        notebook=notebook, frontier=frontier,
    )


def test_daemon_without_steering_passes_raw_seeds():
    conj = _CaptureConjecture()
    d = _daemon(conjecture=conj)
    d.circadian_cycle()
    assert conj.seen == ["seed-a", "seed-b"]  # backward-compatible: no steering


def test_daemon_records_outcomes_and_steers_next_cycle():
    conj = _CaptureConjecture()
    nb, fc = DiscoveryNotebook(), FrontierController()
    d = _daemon(notebook=nb, frontier=fc, conjecture=conj)
    d.run_cycles(2)
    # outcomes flowed back to the proposal side
    assert nb.too_hard == ["conjecture-stmt"]
    assert fc._recent and fc.success_rate() == 0.0
    # the difficulty band steered from the very first conjecture
    assert any("Aim for difficulty" in s for s in conj.seen)
    # ledger lessons + a weakening seed reached the conjecturer on the second cycle
    assert any("Lessons from the ledger" in s for s in conj.seen)
    assert any("STRICTLY WEAKER" in s for s in conj.seen)
