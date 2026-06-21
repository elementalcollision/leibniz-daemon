"""R5: real MAP-Elites selection — descriptor, coverage, curiosity, recombine (CI-safe)."""
from __future__ import annotations

from leibniz.propositio import Demonstratio, Enuntiatio, Expressio, Propositio
from leibniz.selection import KFM, Archive, Disposition, descriptor
from leibniz.types import ClaimType, FinishReason


def _prop(bd=None, statement="some claim", finish_reason=None, promulgated=False,
          proof=None, theorem="theorem t : P"):
    p = Propositio(
        enuntiatio=Enuntiatio(statement=statement, claim_type=ClaimType.COMPLEXITY_BOUND,
                              falsifiable_claim="x"),
        expressio=Expressio(theorem_src=theorem),
    )
    if proof:
        p.demonstratio = Demonstratio(proof_obligation="t", proof_src=proof)
    if bd is not None:
        p.behavior_descriptor = bd
    p.finish_reason = finish_reason
    p.promulgated = promulgated
    return p


def test_descriptor_is_3d_in_unit_range():
    d = descriptor(_prop(proof="by induction", theorem="theorem t : " + "x" * 300))
    assert len(d) == 3
    assert all(0.0 <= x < 1.0 for x in d)


def test_descriptor_technique_axis_tracks_the_proof_tactic():
    assert descriptor(_prop(proof="by induction"))[1] != descriptor(_prop(proof="by simp"))[1]


def test_archive_keeps_the_higher_quality_elite_per_cell():
    arc = Archive()
    assert arc.consider(_prop(bd=(0.0, 0.0, 0.0)), 0.3) is True
    assert arc.consider(_prop(bd=(0.0, 0.0, 0.0)), 0.9) is True   # beats -> replaces
    assert arc.consider(_prop(bd=(0.0, 0.0, 0.0)), 0.5) is False  # worse -> kept
    assert len(arc.cells) == 1
    assert arc.cells[(0, 0, 0)].quality == 0.9


def test_coverage_is_over_the_full_grid():
    arc = Archive()  # resolution 8, dims 3 -> 512 cells
    arc.consider(_prop(bd=(0.0, 0.0, 0.0)), 1.0)
    assert arc.coverage() == 1 / 512


def test_select_parents_prefers_sparse_cells_over_quality():
    arc = Archive()
    arc.consider(_prop(bd=(0.0, 0.0, 0.0)), 0.9)    # cell (0,0,0)
    arc.consider(_prop(bd=(0.15, 0.0, 0.0)), 0.9)   # cell (1,0,0) — adjacent
    isolated = _prop(bd=(0.9, 0.9, 0.9))
    arc.consider(isolated, 0.1)                      # cell (7,7,7) — no neighbours
    assert KFM(arc).select_parents(k=1)[0] is isolated


def test_disposition_mapping():
    kfm = KFM(Archive())
    assert kfm.disposition(_prop(promulgated=True, finish_reason=FinishReason.PROMULGATED)) is Disposition.COMMIT
    assert kfm.disposition(_prop(finish_reason=FinishReason.KNOWN)) is Disposition.KILL
    assert kfm.disposition(_prop(finish_reason=FinishReason.OVER_BUDGET)) is Disposition.KILL
    assert kfm.disposition(_prop(finish_reason=None)) is Disposition.RECOMBINE


def test_recombine_combines_both_parents():
    ctx = KFM(Archive()).recombine(_prop(statement="claim A"), _prop(statement="claim B"))
    assert "claim A" in ctx and "claim B" in ctx
