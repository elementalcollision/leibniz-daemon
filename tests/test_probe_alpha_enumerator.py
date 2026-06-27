"""Probe α enumerator — guard the zero-LLM producer (no LLM, pure stdlib).

Pins the soundness/correctness-critical pieces: uniform-morphism enumeration + relabel dedup,
the degeneracy filters, the named-sequence flagging, the e-th-power-free bound (t<(e-1)p), and
that the emitted Walnut commands use morphism/promote + the correct `?msd_k` numeration (the base
`promote` actually assigns to a uniform k-morphism, per Morphism.toWordAutomaton).
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "probe_alpha", Path(__file__).resolve().parent.parent / "scripts" / "enumerate_walnut_probe_alpha.py")
pa = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pa)


def test_thue_morse_prefix_is_correct():
    tm = {0: (0, 1), 1: (1, 0)}
    assert pa.fixed_point_prefix(tm, 16) == [0, 1, 1, 0, 1, 0, 0, 1, 1, 0, 0, 1, 0, 1, 1, 0]


def test_enumeration_requires_fixed_point_from_zero_and_dedups():
    got = list(pa.uniform_morphisms(2, 2))
    # every morphism has h(0) starting with 0
    assert all(h[0][0] == 0 for _, h in got)
    # Thue-Morse appears exactly once (relabel dedup; m=2 has only identity perm but still unique)
    tm = [h for _, h in got if h == {0: (0, 1), 1: (1, 0)}]
    assert len(tm) == 1
    # canonical keys are unique
    keys = [k for k, _ in got]
    assert len(keys) == len(set(keys))


def test_canonical_dedups_relabeled_morphisms():
    # any morphism and its relabel under a 0-fixing permutation share a canonical key
    h1 = {0: (0, 1), 1: (2, 0), 2: (1, 2)}
    sigma = {0: 0, 1: 2, 2: 1}                                   # swap letters 1<->2
    h2 = {sigma[a]: tuple(sigma[x] for x in img) for a, img in h1.items()}
    assert h2 != h1                                              # genuinely relabeled
    assert pa._canon(h1, 3) == pa._canon(h2, 3)                 # but canonically identical


def test_eventually_periodic_filter():
    assert pa.eventually_periodic([0, 1] * 64) is True           # period 2
    assert pa.eventually_periodic([0] * 128) is True             # constant
    tm = pa.fixed_point_prefix({0: (0, 1), 1: (1, 0)}, 1024)
    assert pa.eventually_periodic(tm) is False                   # Thue-Morse is aperiodic


def test_named_flagging_catches_thue_morse_and_period_doubling():
    pa._init_named()
    assert pa.named_match(pa._canon({0: (0, 1), 1: (1, 0)}, 2)) == "Thue-Morse"
    assert pa.named_match(pa._canon({0: (0, 1), 1: (0, 0)}, 2)) == "period-doubling"
    # an un-named (k=2,m=3) morphism is not flagged
    assert pa.named_match(pa._canon({0: (0, 1), 1: (0, 2), 2: (0, 0)}, 3)) is None


def test_power_free_bound_is_e_minus_one_p():
    assert pa._power_free_bound(2) == "p"        # square-free: t<p
    assert pa._power_free_bound(3) == "2*p"      # cube-free:   t<2p
    assert pa._power_free_bound(4) == "3*p"      # 4th-power-free: t<3p


def test_emitted_commands_use_promote_and_correct_numeration():
    h = {0: (0, 1, 2), 1: (1, 0, 0), 2: (2, 1, 0)}   # a 3-uniform morphism over {0,1,2}
    lines, rows = pa.commands_for(7, h, 3)
    assert lines[0].startswith("morphism ha7 ") and lines[0].rstrip().endswith('";')
    assert lines[1] == "promote WA7 ha7;"
    # one eval per exponent, each declaring ?msd_3 (k=3) and indexing the promoted word WA7
    assert sum(1 for ln in lines if ln.startswith("eval ")) == len(pa.POWER_FREE_EXPONENTS)
    for ln in lines[2:]:
        assert "?msd_3 " in ln and "WA7[i+t]" in ln and "WA7[i+t+p]" in ln
    assert {r["numeration"] for r in rows} == {"msd_3"}


def test_smoke_batch_carries_known_answers():
    lines, rows = pa.smoke_batch()
    assert any('morphism ha0 "0->01 1->10"' in ln for ln in lines)   # Thue-Morse
    expected = {r["exponent"]: r["expected"] for r in rows}
    assert expected == {2: "FALSE", 3: "TRUE", 4: "TRUE"}            # square-ful, cube/4-free


def test_build_is_deterministic_and_filters(tmp_path):
    s1 = pa.build(tmp_path / "a", max_morphisms=30)
    s2 = pa.build(tmp_path / "b", max_morphisms=30)
    assert s1 == s2                                                   # deterministic (no LLM, no RNG)
    assert s1["kept"] <= 30 and s1["dropped_periodic"] > 0
    assert (tmp_path / "a" / "probe_alpha_batch.txt").exists()
    assert (tmp_path / "a" / "probe_alpha_manifest.json").exists()
