"""GATE-4 kernel arm — false-theorem rejection stress (validation plan Tier 2, the audit-tier soundness
backstop).

The whole amplification spine rests on one guarantee: **the Lean kernel never accepts a false bound.** This
test renders well-formed-but-FALSE `… = true := by decide` theorems across all three domains (covering /
CWC / Ramsey) and asserts the real kernel REJECTS every one, while accepting matched TRUE theorems built
from the same locked prelude + template.

WHY THE PAIRED TRUE/FALSE DESIGN IS SOUND: a `False` from `check_source` could in principle mean either
"the kernel disproved a false claim" (what we want to test) OR "the source did not compile" (a vacuous
pass). To exclude the latter, every FALSE source is built from the SAME `_LEAN_HELPERS` prelude and the
SAME `validX … = true := by decide` template as the domain's renderer — only the witness data / bound is
corrupted so the proposition reduces to `false = true`. The TRUE set (rendered by the validated
`render_*` functions) proves those exact templates compile and the kernel accepts them. So `False` here can
only be the kernel disproving a false mathematical claim.

RUNS WHERE: **operator machine with docker + `leibniz-lean:v4.31.0`** (or the self-hosted `lean` nightly
runner). It is in `scripts/run_kernel_tests.sh`. On the GitHub `ci` lane (no Lean image) it COLLECTS and
SKIPS cleanly. ~30 kernel invocations (~1-3 s each); budget a couple of minutes.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_ROOT / "scripts"))

import covering_verify as cov  # noqa: E402
import probe_beta_cwc_pilot as pb  # noqa: E402
import ramsey_verify as rv  # noqa: E402

try:
    from leibniz.backends.lean_cli import LeanCliBackend, available
    _DOCKER = available()
except Exception:  # pragma: no cover - import-environment dependent
    _DOCKER = False

pytestmark = pytest.mark.skipif(not _DOCKER, reason="Lean kernel (docker image) unavailable")


# ---- well-formed FALSE source builders (same prelude + template as each render_*; only data corrupted) --
def _cov_src(v, k, t, blocks, B):
    lits = "[" + ", ".join("[" + ", ".join(str(x) for x in sorted(b)) + "]" for b in blocks) + "]"
    return (f"{cov._LEAN_HELPERS}\n\ntheorem cov_false :\n"
            f"    validCovering {lits} {v} {k} {t} {B} = true := by\n  decide\n")


def _cwc_src(n, d, w, code, M):
    lits = "[" + ", ".join("[" + ", ".join(str(x) for x in sorted(c)) + "]" for c in code) + "]"
    return (f"{pb._LEAN_HELPERS}\n\ntheorem cwc_false :\n"
            f"    validCWC {lits} {n} {d} {w} {M} = true := by\n  decide\n")


def _ram_src(n, s, t, S):
    lits = "[" + ", ".join(str(x) for x in sorted({x % n for x in S})) + "]"
    return (f"{rv._LEAN_HELPERS}\n\ntheorem ram_false :\n"
            f"    ramseyWitness {n} {s} {t} {lits} = true := by\n  decide\n")


FANO = [(0, 1, 2), (0, 3, 4), (0, 5, 6), (1, 3, 5), (1, 4, 6), (2, 3, 6), (2, 4, 5)]
STS9 = [(0, 1, 2), (3, 4, 5), (6, 7, 8), (0, 3, 6), (1, 4, 7), (2, 5, 8),
        (0, 4, 8), (1, 5, 6), (2, 3, 7), (0, 5, 7), (1, 3, 8), (2, 4, 6)]


def _all_ksubsets(v, k):
    from itertools import combinations
    return [list(c) for c in combinations(range(v), k)]


# ---- ≥20 well-formed FALSE theorems (each must be kernel-REJECTED) -------------------------------------
FALSE_SOURCES = [
    # covering (10): coverage holes, length mismatch, out-of-range / wrong-size / non-distinct blocks
    ("cov coverage hole C(7,3,2)", _cov_src(7, 3, 2, FANO[:-1], 6)),
    ("cov length B too small", _cov_src(7, 3, 2, FANO, 6)),
    ("cov length B too big", _cov_src(7, 3, 2, FANO, 8)),
    ("cov out-of-range symbol", _cov_src(7, 3, 2, [[0, 1, 7]] + FANO[1:], 7)),
    ("cov wrong block size", _cov_src(7, 3, 2, [[0, 1]] + FANO[1:], 7)),
    ("cov non-distinct block", _cov_src(7, 3, 2, [[0, 0, 1]] + FANO[1:], 7)),
    ("cov coverage hole C(9,3,2)", _cov_src(9, 3, 2, STS9[:-1], 11)),
    ("cov length C(9,3,2)", _cov_src(9, 3, 2, STS9, 11)),
    ("cov too few blocks C(5,3,2)", _cov_src(5, 3, 2, [[0, 1, 2], [0, 3, 4]], 2)),
    ("cov single block C(7,3,2)", _cov_src(7, 3, 2, [[0, 1, 2]], 1)),
    # CWC (6): min-distance violation, length mismatch, weight mismatch
    ("cwc distance<d (overlap2)", _cwc_src(7, 4, 3, [(0, 1, 2), (0, 1, 3)], 2)),
    ("cwc distance<d (overlap2 b)", _cwc_src(7, 4, 3, [(0, 1, 2), (0, 1, 4)], 2)),
    ("cwc length M too small", _cwc_src(7, 4, 3, FANO, 6)),
    ("cwc length M too big", _cwc_src(7, 4, 3, FANO, 8)),
    ("cwc weight!=w", _cwc_src(4, 4, 3, [(0, 1), (2, 3)], 2)),
    ("cwc weight too big", _cwc_src(7, 4, 3, [(0, 1, 2, 3)], 1)),
    # Ramsey (4): SYMMETRIC complete circulants — every one is K_n, which contains a triangle, so
    # ramseyWitness is false. (Connection sets must be symmetric, i.e. s and n-s both present, to denote an
    # undirected graph; an asymmetric set renders a directed-edge predicate the kernel may accept — but
    # render_ramsey_lean would refuse such a witness via verify_ramsey, so it can never reach the spine.)
    ("ram K5 complete has triangle", _ram_src(5, 3, 3, [1, 2, 3, 4])),
    ("ram K6 complete has triangle", _ram_src(6, 3, 3, [1, 2, 3, 4, 5])),
    ("ram K4 complete has triangle", _ram_src(4, 3, 3, [1, 2, 3])),
    ("ram K7 complete has triangle", _ram_src(7, 3, 3, [1, 2, 3, 4, 5, 6])),
]

# ---- ≥10 well-formed TRUE theorems (rendered by the validated render_*; must be kernel-ACCEPTED) -------
def _true_sources():
    srcs = [
        ("cov FANO C(7,3,2)", cov.render_covering_lean(7, 3, 2, FANO)),
        ("cov STS9 C(9,3,2)", cov.render_covering_lean(9, 3, 2, STS9)),
        ("cov all-3 C(5,3,2)", cov.render_covering_lean(5, 3, 2, _all_ksubsets(5, 3))),
        ("cov all-3 C(6,3,2)", cov.render_covering_lean(6, 3, 2, _all_ksubsets(6, 3))),
        ("cov all-4 C(6,4,2)", cov.render_covering_lean(6, 4, 2, _all_ksubsets(6, 4))),
        ("cwc FANO A(7,4,3)", pb.render_cwc_lean(7, 4, 3, FANO)),
        ("cwc disjoint A(4,4,2)", pb.render_cwc_lean(4, 4, 2, [(0, 1), (2, 3)])),
        ("cwc disjoint A(6,4,2)", pb.render_cwc_lean(6, 4, 2, [(0, 1), (2, 3), (4, 5)])),
        ("ram C5 R(3,3)>5 [1,4]", rv.render_ramsey_lean(5, 3, 3, [1, 4])),
        ("ram C5 R(3,3)>5 [2,3]", rv.render_ramsey_lean(5, 3, 3, [2, 3])),
    ]
    return srcs


@pytest.mark.parametrize("label,src", FALSE_SOURCES, ids=[s[0] for s in FALSE_SOURCES])
def test_kernel_rejects_false_theorem(label, src):
    verdict = LeanCliBackend().check_source(src)
    assert verdict is False, (
        f"SOUNDNESS ALARM [{label}]: the kernel did NOT reject a false bound (got {verdict!r}). "
        f"check_source must return False for a well-formed false `= true := by decide` theorem.")


def test_kernel_accepts_true_theorems_proving_templates_compile():
    # the paired control: the same templates with valid witnesses must be ACCEPTED — otherwise a False
    # above could be a compile failure rather than the kernel disproving a false claim.
    bk = LeanCliBackend()
    accepted = 0
    for label, src in _true_sources():
        verdict = bk.check_source(src)
        assert verdict is True, f"true theorem [{label}] was not kernel-accepted (got {verdict!r})"
        accepted += 1
    assert accepted >= 10


def test_corpus_sizes_meet_gate4_floor():
    # the stress must be broad: >=20 false, >=10 true, all three domains represented.
    assert len(FALSE_SOURCES) >= 20
    assert len(_true_sources()) >= 10
    domains = {lbl.split()[0] for lbl, _ in FALSE_SOURCES}
    assert {"cov", "cwc", "ram"} <= domains
