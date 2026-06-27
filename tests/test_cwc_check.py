"""Guard the standalone CWC audit CLI (Option E) and the committed witness .lean.

The CLI is a re-runnable verification asset, NOT the production trust path: it must (1) re-check a
witness end-to-end (verify -> render -> kernel -> oracle), (2) report the right novelty verdict from
the AUTOMATED oracle, (3) refuse/flag a false witness, and (4) never promulgate or set
kernel_verified. The committed witness file must stay byte-identical to the renderer's output so the
durable Q.E.D. artifact cannot silently drift from the checker.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent


def _load(mod_name: str, rel: str):
    spec = importlib.util.spec_from_file_location(mod_name, _ROOT / rel)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


cli = _load("cwc_check", "scripts/cwc_check.py")
pb = _load("probe_beta_cwc_pilot_for_cli", "scripts/probe_beta_cwc_pilot.py")

FANO = [(0, 1, 2), (0, 3, 4), (0, 5, 6), (1, 3, 5), (1, 4, 6), (2, 3, 6), (2, 4, 5)]


def test_parse_code_round_trips():
    assert cli.parse_code("0,1,2;3,4,5") == [(0, 1, 2), (3, 4, 5)]
    assert cli.parse_code(" 0, 1 ,2 ; ") == [(0, 1, 2)]


def test_valid_in_table_witness_equals_record_no_kernel():
    # Fano A(7,4,3): valid, and the oracle's record is 7 -> "equals record"
    r = cli.check(7, 4, 3, FANO, run_kernel=False)
    assert r["verify_ok"] is True
    assert r["size"] == 7
    assert r["best_known"] == 7
    assert "equals record" in r["novelty"]
    assert r["kernel"] == "not run (--no-kernel)"


def test_false_witness_is_rejected_before_kernel():
    # two weight-3 words sharing 2 elements => distance 2 < 4
    r = cli.check(7, 4, 3, [(0, 1, 2), (0, 1, 3)], run_kernel=False)
    assert r["verify_ok"] is False
    assert "distance 2" in r["verify_reason"]
    assert r["novelty"] == "n/a"
    assert "lean_theorem" not in r                       # never rendered a false theorem


def test_untabulated_cell_does_not_claim_novelty():
    # out-of-range cell: no table-of-record entry -> novelty not claimable (never fabricated)
    r = cli.check(100, 4, 3, [(0, 1, 2), (3, 4, 5)], run_kernel=False)
    assert r["best_known"] is None
    assert "untabulated" in r["novelty"]


def test_report_never_promulgates_or_sets_kernel_verified():
    # the audit report is pure data: no promotion/kernel_verified field, no ledger mutation
    r = cli.check(7, 4, 3, FANO, run_kernel=False)
    assert "kernel_verified" not in r and "promulgated" not in r and "qed" not in r


def test_committed_witness_lean_matches_renderer():
    # the durable Q.E.D. artifact must equal render_cwc_lean(...) verbatim (anti-drift).
    # Use the DEFAULT theorem name (no thm_name=) so the test exercises the shipped path.
    rendered = pb.render_cwc_lean(7, 4, 3, FANO)
    committed = (_ROOT / "lean-project" / "CwcFanoWitness.lean").read_text()
    assert rendered in committed, "committed CwcFanoWitness.lean drifted from render_cwc_lean output"
    assert "import Mathlib" not in committed              # core Lean only => minimal TCB
    assert committed.rstrip().endswith("decide")
    assert "render_cwc_lean" in committed and "v4.31.0" in committed  # provenance header intact


def test_beats_record_branch_flags_not_auto_promulgated(monkeypatch):
    # the single most load-bearing verdict: a beat must be flagged AND marked not-auto-promulgated.
    # No real beat exists, so synthesize one via the oracle (the only honest way — see ADR 0040 §4).
    monkeypatch.setattr(cli.ora, "load_snapshot", lambda *a, **k: ({}, {}))
    monkeypatch.setattr(cli.ora, "best_known", lambda *a, **k: 6)
    monkeypatch.setattr(cli.ora, "is_improvement", lambda *a, **k: True)
    r = cli.check(7, 4, 3, FANO, run_kernel=False)
    assert r["best_known"] == 6
    assert "BEATS record" in r["novelty"] and "NOT auto-promulgated" in r["novelty"]
    assert "kernel_verified" not in r and "promulgated" not in r   # still never promulgates


def test_below_record_branch(monkeypatch):
    monkeypatch.setattr(cli.ora, "load_snapshot", lambda *a, **k: ({}, {}))
    monkeypatch.setattr(cli.ora, "best_known", lambda *a, **k: 100)
    monkeypatch.setattr(cli.ora, "is_improvement", lambda *a, **k: False)
    r = cli.check(7, 4, 3, FANO, run_kernel=False)
    assert "below record" in r["novelty"]


def test_check_source_none_vs_false_contract(monkeypatch):
    # None (backend unavailable) must NOT be confused with False (genuine kernel reject)
    from leibniz.backends.lean_cli import LeanCliBackend, LeanResult
    b = LeanCliBackend()
    monkeypatch.setattr(b, "_run_lean", lambda src: None)
    assert b.check_source("x") is None                   # unavailable, not a verdict
    monkeypatch.setattr(b, "_run_lean", lambda src: LeanResult(1, "error: nope"))
    assert b.check_source("x") is False                  # genuine kernel reject
    monkeypatch.setattr(b, "_run_lean", lambda src: LeanResult(0, "ok"))
    assert b.check_source("x") is True


def test_cli_maps_kernel_none_to_unavailable_and_false_to_rejected(monkeypatch):
    import leibniz.backends.lean_cli as lc
    monkeypatch.setattr(lc, "available", lambda *a, **k: True)
    monkeypatch.setattr(lc.LeanCliBackend, "check_source", lambda self, src: None)
    assert cli.check(7, 4, 3, FANO, run_kernel=True)["kernel"] == "unavailable"
    monkeypatch.setattr(lc.LeanCliBackend, "check_source", lambda self, src: False)
    assert cli.check(7, 4, 3, FANO, run_kernel=True)["kernel"] == "KERNEL-REJECTED"


def test_exit_status_signal():
    assert cli._exit_status({"verify_ok": True, "kernel": "KERNEL-VERIFIED"}) == 0
    assert cli._exit_status({"verify_ok": True, "kernel": "not run (--no-kernel)"}) == 0
    assert cli._exit_status({"verify_ok": True, "kernel": "KERNEL-REJECTED"}) == 1
    assert cli._exit_status({"verify_ok": False, "kernel": "skipped"}) == 1
    # kernel could not run => 2 (NOT a kernel pass), distinct from a real pass and from --no-kernel
    assert cli._exit_status({"verify_ok": True, "kernel": "unavailable (no docker)"}) == 2


def test_render_refuses_false_witness_directly():
    import pytest
    with pytest.raises(ValueError):
        pb.render_cwc_lean(7, 4, 3, [(0, 1, 2), (0, 1, 3)])   # distance-2 pair => false theorem


# --- Docker-gated end-to-end kernel check (skipped when the Lean image is absent, e.g. CI) -------
def _lean_available() -> bool:
    try:
        from leibniz.backends.lean_cli import available
        return available()
    except Exception:
        return False


def test_cli_kernel_accepts_the_fano_witness():
    import pytest
    if not _lean_available():
        pytest.skip("Lean docker image not available")
    r = cli.check(7, 4, 3, FANO, run_kernel=True)
    assert r["kernel"] == "KERNEL-VERIFIED"               # genuinely Q.E.D., via the CLI path


def test_cli_kernel_rejects_a_false_witness_via_check_source():
    import pytest
    if not _lean_available():
        pytest.skip("Lean docker image not available")
    from leibniz.backends.lean_cli import LeanCliBackend
    # hand the kernel a false complete source directly (bypass the renderer guard)
    bad = (pb._LEAN_HELPERS + "\n\ntheorem bad :\n"
           "    validCWC [[0, 1, 2], [0, 1, 3]] 7 4 3 2 = true := by\n  decide\n")
    assert LeanCliBackend().check_source(bad) is False
