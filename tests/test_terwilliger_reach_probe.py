"""Guard the task-#99 discovery reach probe (scripts/terwilliger_reach_probe.py). The snapshot, candidate
classification, lb derivation, escalation gate, and verdict are free-CPU (run in CI); the solve legs need
cvxpy (operator-local, SKIP in CI). The trust points under test: the Brouwer snapshot is targeting context
only — a candidate needs a floor >= the known lower bound (solver noise below lb is INVALID, not a
discovery); nothing counts without the exact-LP certificate downstream (verdict_of / escalate); and a
kernel-attestation failure never erases an exact-LP certification."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parent.parent
_HAS = importlib.util.find_spec("cvxpy") is not None and importlib.util.find_spec("numpy") is not None
_needs = pytest.mark.skipif(not _HAS, reason="cvxpy/numpy are operator-local; solve legs skipped in CI")


def _load():
    spec = importlib.util.spec_from_file_location("terwilliger_reach_probe",
                                                  _ROOT / "scripts" / "terwilliger_reach_probe.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


rp = _load()


def test_snapshot_shape_and_trust_note():
    snap = json.loads((_ROOT / "docs" / "data" / "brouwer-snapshot-2026-07.json").read_text())
    cells = snap["cells"]
    assert len(cells) == 36                                  # n=20..28 x d in {6,8,10,12}
    for n in range(20, 29):
        for d in (6, 8, 10, 12):
            c = cells[f"{n},{d}"]
            assert c["lb"] <= c["ub"] and c["ub_source"]
    # the snapshot must carry its own quarantine label: context, never a decider
    assert "never a decider" in snap["_meta"]["trust_note"]
    # spot-check two cells against the page's prose (Schrijver Table I record; GMS2012 quadruples)
    assert cells["28,8"]["ub"] == 32151
    assert cells["23,6"]["ub"] == 13674


def test_lb_for_cell_snapshot_and_monotonicity():
    cells = {"27,12": {"lb": 128, "ub": 169, "ub_source": "x"},
             "28,12": {"lb": 178, "ub": 288, "ub_source": "x"}}
    assert rp.lb_for_cell(27, 12, cells) == (128, None)      # in-table: the snapshot lb, no note
    lb, note = rp.lb_for_cell(30, 12, cells)                 # beyond the table: A(30,12) >= A(28,12)
    assert lb == 178 and "monotonicity" in note
    assert rp.lb_for_cell(29, 4, cells) == (None, None)      # d not tabulated at all: no gate derivable


def test_classify_row_candidate_and_soundness():
    cells = {"27,12": {"lb": 128, "ub": 169, "ub_source": "x"},
             "20,12": {"lb": 6, "ub": 6, "ub_source": "exact"},
             "23,6": {"lb": 8192, "ub": 13674, "ub_source": "x"}}
    # genuine candidate: floor strictly below ub, at/above lb
    r = rp.classify_row({"n": 27, "d": 12, "sdp_floor": 150}, cells, {})
    assert r["candidate"] is True and r["above_known_lb"] is True and r["margin_vs_ub"] == -19
    # solver noise below the known lower bound: INVALID, never a candidate
    r = rp.classify_row({"n": 20, "d": 12, "sdp_floor": 5}, cells, {})
    assert r["candidate"] is False and r["above_known_lb"] is False
    # weaker-than-published floor: above the lb, no candidate
    r = rp.classify_row({"n": 23, "d": 6, "sdp_floor": 13766}, cells, {"table_I": None, (23, 6): 13766})
    assert r["candidate"] is False and r["above_known_lb"] is True and r["reproduces_table_I"] is True
    # beyond the table (n>28): scaling data only
    r = rp.classify_row({"n": 29, "d": 6, "sdp_floor": 500000}, cells, {})
    assert r["snapshot"] is None and r["candidate"] is False
    # unsolved cell (time cap): no candidate
    r = rp.classify_row({"n": 27, "d": 12, "status": "time_cap"}, cells, {})
    assert r["candidate"] is False and "margin_vs_ub" not in r


def test_verdict_requires_a_certified_escalation():
    cand = [{"n": 27, "d": 12, "sdp_floor": 150, "candidate": True}]
    assert rp.verdict_of([], [], False) == "DRY"
    # candidates refused (or failed) by the exact-LP decider are still DRY — floats never count alone
    assert rp.verdict_of(cand, [{"certified": False}], False) == "DRY"
    assert rp.verdict_of(cand, [{"certified": True}], False) == "GREEN(candidate)"
    # skipping the decider must not report dry — the question is undecided, not answered
    assert rp.verdict_of(cand, [], True).startswith("UNESCALATED")


def test_escalate_kernel_failure_never_erases_certification(monkeypatch):
    # the exact LP is the decider; a kernel-attestation crash is recorded, not allowed to flip GREEN->DRY
    class FakeLP:
        @staticmethod
        def certify_lp(n, d, target=None, **kw):
            return {"certified": True, "exact_bound": str(target), "floor": target, "target": target}

        @staticmethod
        def kernel_verify_lp(n, d, target=None, timeout_s=900):
            raise RuntimeError("docker exploded")

    monkeypatch.setattr(rp, "_load", lambda mod, rel: FakeLP)
    row = rp.escalate(27, 12, 150)
    assert row["certified"] is True
    assert str(row["kernel"]).startswith("error: RuntimeError")


def test_escalate_kernel_leg_runs_only_when_certified(monkeypatch):
    kernel_calls = []

    class FakeLP:
        @staticmethod
        def certify_lp(n, d, target=None, **kw):
            return {"n": n, "d": d, "target": target, "status": "no exact LP cert at tried precisions"}

        @staticmethod
        def kernel_verify_lp(n, d, target=None, timeout_s=900):
            kernel_calls.append((n, d))
            return {"kernel": True}

    monkeypatch.setattr(rp, "_load", lambda mod, rel: FakeLP)
    row = rp.escalate(27, 12, 150)
    assert row["certified"] is False and "kernel" not in row and kernel_calls == []


def test_nonfinite_solver_value_is_a_failed_attempt_not_a_crash(monkeypatch, capsys):
    # cvxpy reports infeasible/unbounded as +/-inf (not None); the ladder must fall through, not die
    class FakeTS:
        @staticmethod
        def solve_primal(n, d, k_max=None, solver="CLARABEL"):
            if solver == "CLARABEL":
                return {"value": float("-inf"), "status": "infeasible"}
            return {"value": 42.2, "status": "optimal"}

    monkeypatch.setattr(rp, "_load", lambda mod, rel: FakeTS)
    rp.solve_cell(9, 9, lb=40)
    lines = [json.loads(x) for x in capsys.readouterr().out.splitlines()]
    final = lines[-1]
    assert final["sdp_floor"] == 42 and final["solver"] == "SCS"
    assert "non-finite" in final["attempts"][0]["status"] and final["attempts"][0]["floor"] is None
    # a JSON line was emitted after the FIRST attempt too (mid-ladder cap can't erase completed attempts)
    assert len(lines[0]["attempts"]) == 1 and lines[0]["status"] == "ladder_in_progress"


@_needs
def test_capped_cell_solve_reproduces_a19_6():
    row = rp.run_cell_capped(19, 6, 120, lb=1024)
    assert row["sdp_floor"] == 1280                          # the validated record cell, through the cap harness
    assert row["solver"] == "CLARABEL"                       # first rung of the ladder suffices here
    assert row["cell_secs"] <= 120


@_needs
def test_lb_acceptance_gate_never_returns_a_floor_below_lb():
    # A(20,12)=6 exactly; Clarabel lands at 5.9999997 -> floor 5 < lb, so the gate must either fall through to
    # an SCS attempt that clears 6, or return NO float at all. It must never hand back a floor below the lb.
    row = rp.run_cell_capped(20, 12, 120, lb=6)
    assert len(row["attempts"]) >= 1
    assert row["sdp_floor"] is None or row["sdp_floor"] >= 6


@_needs
def test_time_cap_is_hard():
    row = rp.run_cell_capped(28, 6, 0.2)                     # nothing solves in 0.2s
    assert row["status"].startswith("time_cap")
    assert row.get("sdp_floor") is None
