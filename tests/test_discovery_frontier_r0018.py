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


# --- DiscoveryNotebook persistence (ADR 0023) --------------------------------

def test_notebook_persists_and_resumes(tmp_path):
    nb = DiscoveryNotebook(capacity=6)
    nb.record(_prop("a proven law", promulgated=True, reason=FinishReason.PROMULGATED))
    nb.record(_prop("a near miss", reason=FinishReason.UNPROVEN))
    nb.record(_prop("a known one", reason=FinishReason.KNOWN))
    p = tmp_path / "notebook.json"
    nb.save(p)
    resumed = DiscoveryNotebook.load(p, capacity=6)
    assert resumed.proven == ["a proven law"]
    assert resumed.too_hard == ["a near miss"]   # the near-miss survives the run boundary
    assert resumed.avoid == ["a known one"]


def test_notebook_load_missing_is_fresh(tmp_path):
    nb = DiscoveryNotebook.load(tmp_path / "absent.json", capacity=9)
    assert nb.too_hard == [] and nb.proven == [] and nb.avoid == []
    assert nb.capacity == 9


def test_notebook_load_respects_capacity(tmp_path):
    big = DiscoveryNotebook(capacity=10)
    for i in range(10):
        big.record(_prop(f"hard {i}", reason=FinishReason.UNPROVEN))
    p = tmp_path / "notebook.json"
    big.save(p)
    small = DiscoveryNotebook.load(p, capacity=3)
    assert small.too_hard == ["hard 7", "hard 8", "hard 9"]  # capped to the most recent 3


def test_daemon_persists_notebook_across_run(tmp_path):
    path = str(tmp_path / "notebook.json")
    nb = DiscoveryNotebook()
    d = _daemon(notebook=nb, frontier=FrontierController())
    d.notebook_path = path
    d.run_cycles(2)
    assert (tmp_path / "notebook.json").exists()
    # the run's near-misses were written out (the _FormalizeNull settles UNPROVEN)
    assert DiscoveryNotebook.load(path).too_hard == nb.too_hard


def test_notebook_capacity_zero_keeps_nothing_not_unbounded():
    # ADR 0023 review (HIGH): del bucket[:-0] is a no-op -> a cap<=0 must DISABLE the
    # bucket (keep nothing), never grow without bound.
    nb = DiscoveryNotebook(capacity=0)
    for i in range(50):
        nb.record(_prop(f"hard {i}", reason=FinishReason.UNPROVEN))
    assert nb.too_hard == []


def test_notebook_load_tolerates_nondict_and_wrongtyped(tmp_path):
    # ADR 0023 review (MEDIUM): a forged/truncated non-dict payload -> fresh, no crash.
    for bad in ("[1, 2, 3]", "42", '"oops"', "null"):
        p = tmp_path / "nb.json"
        p.write_text(bad)
        nb = DiscoveryNotebook.load(p, capacity=6)
        assert nb.too_hard == [] and nb.proven == [] and nb.avoid == []
    # a string-valued bucket must degrade to empty, not iterate into per-char seeds.
    p.write_text('{"too_hard": "abc"}')
    assert DiscoveryNotebook.load(p).too_hard == []


def test_frontier_load_tolerates_nondict(tmp_path):
    # parity fix: FrontierController.from_dict had the identical latent crash.
    p = tmp_path / "fr.json"
    p.write_text("[1, 2, 3]")
    fc = FrontierController.load(p)
    assert fc.target == 0.45 and fc._recent == []


def test_env_int_falls_back_on_garbage(monkeypatch):
    # ADR 0023 review (LOW): an operator typo in LEIBNIZ_WEAKEN_K / LEIBNIZ_NOTEBOOK_CAP
    # must fall back to the default, not abort build_daemon with a ValueError.
    from leibniz.assembly import _env_int
    monkeypatch.setenv("X_KNOB", "notanint")
    assert _env_int("X_KNOB", 3) == 3
    monkeypatch.setenv("X_KNOB", "")
    assert _env_int("X_KNOB", 3) == 3
    monkeypatch.delenv("X_KNOB", raising=False)
    assert _env_int("X_KNOB", 3) == 3
    monkeypatch.setenv("X_KNOB", "5")
    assert _env_int("X_KNOB", 3) == 5


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

def test_weakening_seeds_target_the_most_recent_and_cap():
    # ADR 0023: weaken the FRESHEST k near-misses (the ones just seen to reach-proof
    # but not close), not the oldest.
    seeds = weakening_seeds(["claim one", "claim two", "claim three"], k=2)
    assert len(seeds) == 2
    assert all("STRICTLY WEAKER" in s for s in seeds)
    assert "claim two" in seeds[0] and "claim three" in seeds[1]


def test_weakening_echo_guard_stops_marked_instructions():
    once = weakening_seeds(["fresh claim"], k=2)
    assert len(once) == 1
    # the echo guard: a statement that already carries the weakening instruction is
    # never re-weakened (kills a verbatim-echoing provider's compounding loop).
    assert weakening_seeds(once, k=2) == []


def test_weakening_k_zero_returns_none_not_all(tmp_path=None):
    # ADR 0023 review (HIGH): fresh[-0:] is the WHOLE list — k<=0 must mean NONE, not
    # "weaken every accumulated near-miss" (a billable cost blowup).
    assert weakening_seeds(["a", "b", "c"], k=0) == []
    assert weakening_seeds(["a", "b", "c"], k=-1) == []


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


# === ADR 0034 Stage 1: steering graft (genre-kill + flavour exemplars) =======

from leibniz.discovery import _family, load_novelty_exemplars  # noqa: E402


def _proven(claim_property: str, stmt: str = "law") -> Propositio:
    p = Propositio(enuntiatio=Enuntiatio(statement=stmt, claim_type=ClaimType.INVARIANT,
                                         falsifiable_claim="x", claim_property=claim_property))
    p.finish_reason = FinishReason.PROMULGATED
    return p


def test_family_key_is_coarse_relop_and_modulus():
    # different polynomials, same relop+modulus -> ONE family (the genre-hop unit)
    a, b = _family("(n^2) % 2 == 0"), _family("(n^4 + n^2) % 2 == 0")
    assert a is not None and a[0] == b[0]
    # a residue-SET characterization is a DISTINCT family (relop differs), so it survives a == kill
    assert _family("(n^2) % 2 in {0}")[0] != a[0]
    # different modulus -> different family
    assert _family("(n^2) % 3 == 0")[0] != a[0]
    # outside the DSL -> no family (no kill)
    assert _family("gcd(n, n+1) == 1") is None
    assert _family(None) is None


def test_genre_kill_fires_after_threshold_proven_only():
    nb = DiscoveryNotebook(capacity=12, genre_threshold=3)
    # two proven in the family -> not yet killed
    nb.record(_proven("(n^2) % 2 == 0"))
    nb.record(_proven("(n^4) % 2 == 0"))
    assert nb.genre_kill == []
    # a NON-proven candidate in the family must NOT count toward exhaustion
    miss = Propositio(enuntiatio=Enuntiatio(statement="m", claim_type=ClaimType.INVARIANT,
                                            falsifiable_claim="x", claim_property="(n^6) % 2 == 0"))
    miss.finish_reason = FinishReason.UNPROVEN
    nb.record(miss)
    assert nb.genre_kill == []
    # the third PROVEN one trips the kill
    nb.record(_proven("(n^4 + n^2) % 2 == 0"))
    assert nb.genre_kill == ["== modular claims modulo 2"]


def test_genre_kill_is_bounded():
    nb = DiscoveryNotebook(capacity=50, genre_threshold=1, genre_capacity=2)
    for m in (2, 3, 5, 7):                       # four distinct families, cap is 2
        nb.record(_proven(f"(n^2) % {m} == 0"))
    assert len(nb.genre_kill) == 2


def test_steering_surfaces_exemplars_and_genre_kill():
    nb = DiscoveryNotebook(capacity=12, genre_threshold=1)
    nb.exemplars = ["squares are 0 or 1 mod 4 [(n^2) % 4 in {0, 1}]"]
    nb.record(_proven("(n^2) % 2 == 0"))        # trips a kill at threshold 1
    s = nb.steering()
    assert "FLAVOUR" in s and "squares are 0 or 1 mod 4" in s
    assert "EXHAUSTED FAMILIES" in s and "modulo 2" in s


def test_exemplars_are_not_persisted_but_genre_state_is():
    nb = DiscoveryNotebook(capacity=12, genre_threshold=1)
    nb.exemplars = ["flavour anchor"]
    nb.record(_proven("(n^3 + 5*n) % 3 == 0"))
    back = DiscoveryNotebook.from_dict(nb.to_dict(), capacity=12)
    assert back.genre_kill == nb.genre_kill                 # ledger state carries across runs
    assert back._family_counts == nb._family_counts
    assert back.exemplars == []                             # flavour anchors reload from corpus


def test_from_dict_is_defensive_against_forged_genre_payload():
    nb = DiscoveryNotebook.from_dict(
        {"genre_kill": "not-a-list", "family_counts": {"k": "not-an-int"}}, capacity=6)
    assert nb.genre_kill == [] and nb._family_counts == {}


def test_cold_start_steering_unchanged_without_exemplars_or_outcomes():
    nb = DiscoveryNotebook()                                # no exemplars, no outcomes
    assert nb.steering() == ""
    assert steer("SEED", nb, None) == "SEED"


# --- the curated corpus file itself stays sound ------------------------------

def test_novelty_exemplars_file_loads_and_is_valid_dsl():
    from leibniz.structural import congruence_signature
    import json as _json
    from pathlib import Path as _Path
    raw = _json.loads((_Path(__file__).resolve().parent.parent
                       / "corpus" / "novelty_exemplars.json").read_text())
    exemplars = raw["exemplars"]
    assert 1 <= len(exemplars) <= 8                         # "a handful" (ADR 0034 §9)
    for e in exemplars:
        # every curated anchor must be expressible in the recognized DSL (a real flavour anchor)
        assert congruence_signature(e["claim_property"]) is not None, e["claim_property"]
    # and the loader renders them as non-empty steering lines
    lines = load_novelty_exemplars()
    assert lines and all(isinstance(x, str) and x for x in lines)


def test_load_novelty_exemplars_missing_file_is_empty():
    assert load_novelty_exemplars("/nonexistent/path/exemplars.json") == []


def test_load_novelty_exemplars_is_defensive_against_malformed_payloads(tmp_path):
    # An explicit null or a non-list payload must yield [] — never a crash, never char-iteration
    # of a string (regression: data.get('exemplars', []) returns None for an explicit null).
    for payload in ('{"exemplars": null}', '{"exemplars": "foo"}', '[]', 'null', '"x"'):
        f = tmp_path / "ex.json"
        f.write_text(payload)
        assert load_novelty_exemplars(f) == [], payload
