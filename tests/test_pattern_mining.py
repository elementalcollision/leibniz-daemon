"""ADR 0034 Stage 2: empirical pattern mining (CI-safe; pure, no LLM/Lean/network).

Pins the miner's arithmetic and the load-bearing soundness properties: every mined pattern is
TRUE (independently re-verified), is a proper restriction, carries a real signature, is never a
corpus restatement, and the dispenser is diverse + non-repeating. Also guards the Prohibition-1
property (the module decides nothing) and the daemon's volume-preserving seed blend.
"""
from __future__ import annotations

import inspect

from leibniz import pattern_mining as pm
from leibniz.structural import congruence_signature as sig


# --- residue arithmetic ------------------------------------------------------

def test_residue_set_is_exact():
    assert pm._residue_set([0, 0, 1], 4) == frozenset({0, 1})       # n^2 mod 4
    assert pm._residue_set([0, 0, 1], 3) == frozenset({0, 1})       # n^2 mod 3
    assert pm._residue_set([0, 1, 1], 2) == frozenset({0})          # n^2+n always even


def test_poly_str_renders_dsl():
    assert pm._poly_str([0, 0, 1]) == "n^2"
    assert pm._poly_str([1, 0, 3, 0, 1]) == "n^4 + 3*n^2 + 1"
    assert pm._poly_str([-3, -2, 2]) == "2*n^2 - 2*n - 3"
    assert pm._poly_str([0, -1]) == "-n"


def test_property_shapes():
    assert pm._property("n^2", 4, frozenset({0, 1})) == "(n^2) % 4 in {0, 1}"
    assert pm._property("n^2 + n", 2, frozenset({0})) == "(n^2 + n) % 2 == 0"          # singleton
    assert pm._property("n^2 + 2", 5, frozenset({1, 2, 3, 4})) == "(n^2 + 2) % 5 != 0"  # all-but-one
    assert pm._property("n", 3, frozenset({0, 1, 2})) is None                           # vacuous |R|==m


# --- mine(): soundness (the load-bearing properties) -------------------------

_RANKED = pm.mine(limit=400)


def test_every_mined_pattern_is_actually_true():
    # independently re-verify each pattern over a WIDE range (well past one period) — a mined
    # claim the daemon would prove must in fact hold.
    def _eval(poly_residues, m):
        return poly_residues
    for p in _RANKED:
        R = set(p.residues)
        # recompute the residue set from the rendered polynomial by safe arithmetic eval
        expr = p.poly.replace("^", "**")
        actual = {eval(expr, {"__builtins__": {}}, {"n": n}) % p.m for n in range(0, 4 * p.m)}
        assert actual <= R, f"{p.prop}: observed {actual} escapes declared {R}"
        assert actual == R, f"{p.prop}: declared {R} but only {actual} occur (not tight)"


def test_mined_patterns_are_proper_restrictions_with_real_signatures():
    for p in _RANKED:
        assert len(p.residues) < p.m                       # never vacuous
        assert sig(p.prop) is not None                     # recognized DSL shape
        assert sig(p.prop) == p.signature                  # the stored signature matches the prop


def test_mined_signatures_are_unique():
    sigs = [p.signature for p in _RANKED]
    assert len(sigs) == len(set(sigs))                     # dedup by signature held


def test_mine_drops_corpus_signatures():
    # take a pattern the miner WOULD surface, feed its signature in as "known" -> it must vanish.
    target = _RANKED[0].signature
    again = pm.mine(corpus_signatures={target}, limit=400)
    assert all(p.signature != target for p in again)


# --- dispenser: diversity + cursor ------------------------------------------

def test_dispensing_spans_multiple_moduli():
    miner = pm.PatternMiner()
    import re
    seeds = miner.seeds(12)
    mods = {int(re.search(r"mod (\d+)", s).group(1)) for s in seeds}
    assert len(mods) >= 5, f"first 12 seeds only span moduli {mods}"


def test_monic_is_preferred_over_scaled_sibling():
    # n^2 mod 8 (monic) should outrank 2*n^2 mod 8 in the ranking
    by_prop = {p.prop: p.score for p in pm.mine(limit=2000)}
    monic = next((s for p, s in by_prop.items() if p.startswith("(n^2) % 8")), None)
    scaled = next((s for p, s in by_prop.items() if p.startswith("(2*n^2) % 8")), None)
    if monic is not None and scaled is not None:
        assert monic > scaled


def test_miner_cursor_advances_without_repeats_and_exhausts():
    miner = pm.PatternMiner()
    first = miner.seeds(5)
    second = miner.seeds(5)
    assert len(first) == 5 and len(second) == 5
    assert set(first).isdisjoint(second)                   # fresh patterns each draw
    assert miner.seeds(0) == []


def test_seed_text_frames_as_data_to_formalize():
    p = _RANKED[0]
    s = pm.seed_text(p)
    assert "COMPUTED PATTERN" in s and "case analysis" in s
    assert p.poly in s and f"mod {p.m}" in s


# --- Prohibition 1: the module decides nothing (ADR 0034 §6) -----------------

def test_module_exposes_no_gate_surface():
    banned = ("accept", "reject", "quarantine", "drop", "filter", "gate", "decide",
              "promote", "demote", "verdict", "prove")
    names = [n for n, _ in inspect.getmembers(pm, callable) if not n.startswith("_")]
    offenders = [n for n in names if any(b in n.lower() for b in banned)]
    assert offenders == [], f"pattern_mining must decide nothing; found {offenders}"


# --- daemon seed blend: volume-preserving (clean A/B) ------------------------

class _FakeMiner:
    def __init__(self, seeds):
        self._s = list(seeds)

    def seeds(self, k):
        out, self._s = self._s[:k], self._s[k:]
        return out


def _daemon_with(miner, mine_k):
    from leibniz.daemon import Leibniz
    d = Leibniz.__new__(Leibniz)        # bypass full assembly; exercise _blend_mined directly
    d.pattern_miner = miner
    d.mine_k = mine_k
    return d


def test_blend_replaces_preserving_count():
    d = _daemon_with(_FakeMiner(["MINED-1", "MINED-2"]), mine_k=2)
    out = d._blend_mined(["feed-a", "feed-b", "feed-c"])
    assert len(out) == 3                                    # count preserved (no volume inflation)
    assert out[0] == "MINED-1" and out[1] == "MINED-2" and out[2] == "feed-c"


def test_blend_is_noop_without_miner_or_budget():
    assert _daemon_with(None, 0)._blend_mined(["a", "b"]) == ["a", "b"]
    assert _daemon_with(_FakeMiner(["M"]), 0)._blend_mined(["a", "b"]) == ["a", "b"]
    assert _daemon_with(_FakeMiner(["M"]), 2)._blend_mined([]) == []


def test_blend_caps_mined_at_base_length():
    d = _daemon_with(_FakeMiner(["M1", "M2", "M3", "M4"]), mine_k=4)
    out = d._blend_mined(["only-one"])
    assert out == ["M1"]                                    # never grows beyond the base count


# === ADR 0034 Stage 2 review fixes: exemplar exclusion, origin tagging, pool exhaustion ======

def test_exemplars_are_excluded_from_the_minable_pool():
    # a fact already injected as a Stage-1 exemplar must NOT also be mined (double-injection
    # would inflate apparent diversity); assembly seeds the miner with exemplar signatures.
    from leibniz.discovery import novelty_exemplar_properties
    ex_sigs = {sig(p) for p in novelty_exemplar_properties()}
    assert ex_sigs and all(s is not None for s in ex_sigs)
    mined_sigs = {p.signature for p in pm.mine(corpus_signatures=ex_sigs, limit=3000)}
    assert ex_sigs.isdisjoint(mined_sigs)


def test_seed_origin_classifier():
    from leibniz.daemon import Leibniz
    assert Leibniz._seed_origin(pm.MINED_SEED_PREFIX + " for every n ...") == "mined"
    assert Leibniz._seed_origin("Propose a STRICTLY WEAKER variant of: x") == "weaken"
    assert Leibniz._seed_origin("Synthesize ... combining features of two stepping stones") == "kfm"
    assert Leibniz._seed_origin("sorting lower bound") == "survey"


def test_real_miner_exhausts_cleanly():
    miner = pm.PatternMiner()
    drawn = 0
    for _ in range(pm.PatternMiner.POOL + 10):   # draw past the pool
        batch = miner.seeds(8)
        drawn += len(batch)
        if not batch:
            break
    assert drawn == len(miner)                    # dispensed exactly the pool, no more
    assert miner.seeds(8) == []                    # stays empty after exhaustion (no stale re-dispense)
