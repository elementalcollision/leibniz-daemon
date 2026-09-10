"""H1 date-honesty guard — an undated law in the published ledger fails the honesty gate.

Regression for the 2026-07-09 rectification: ten amplified laws were published with
``published_at=""`` (the appends never stamped the date) and rendered undated. The gate now refuses
an undated ledger law — kernel-independently, so the failure fires even where the Lean image is
absent (CI). Producer-side law JSONs remain legitimately undated (publication hasn't happened yet);
only the LEDGER — the record of the publish act — is held to this.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("exp_calc", _ROOT / "scripts" / "export_calculemus.py")
ec = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ec)


def _law(lid: str, published_at: str) -> dict:
    # kernel_verified False so the kernel loop skips it -- and therefore NO `qed` stamp, because
    # charter invariant 7 is "Q.E.D. is stamped iff kernel_verified". The fixture used to carry
    # both, which the H1b cross-check below (rightly) now reads as a ledger defect.
    return {"id": lid, "statement": "s", "theorem_src": "theorem t : True", "proof_src": "trivial",
            "imports": [], "qed": "", "kernel_verified": False,
            "published_at": published_at}


def _check(tmp_path, laws, monkeypatch, dates_only=True):
    # force the kernel-unavailable path: the date check must decide the verdict on its own.
    # `dates_only=True` is the EXPLICIT opt-in to a kernel-less run -- see the strict-default
    # regressions below, which pin that the same call without it reports UNVERIFIED, not 0.
    import leibniz.backends.lean_repl as lr
    monkeypatch.setattr(lr, "available", lambda: False)
    p = tmp_path / "ledger.json"
    p.write_text(json.dumps({"laws": laws}))
    return ec.check_ledger(p, dates_only=dates_only)


def test_undated_law_fails_even_without_the_kernel(tmp_path, monkeypatch):
    assert _check(tmp_path, [_law("dated", "2026-07-09"), _law("undated", "")], monkeypatch) == 1


def test_whitespace_date_counts_as_undated(tmp_path, monkeypatch):
    assert _check(tmp_path, [_law("sneaky", "  ")], monkeypatch) == 1


def test_fully_dated_ledger_passes_the_date_check(tmp_path, monkeypatch):
    assert _check(tmp_path, [_law("a", "2026-07-08"), _law("b", "2026-07-09T23:09:07Z")], monkeypatch) == 0


# --- the gate must not report green when it did not run -------------------------------------------
# Both of these returned 0 before: an absent ledger and an absent kernel were "non-fatal", so a
# caller reading the exit status could not tell a verified ledger from a gate that checked nothing.
# `export_calculemus.py --check` against a missing sibling checkout printed a stderr line and
# exited 0. ADR 0093's rule -- a lane that cannot run must say so -- applied to the publish gate.

def test_missing_ledger_is_unverified_not_pass(tmp_path):
    assert ec.check_ledger(tmp_path / "nope.json") == ec.EXIT_UNVERIFIED


def test_missing_ledger_is_unverified_even_with_dates_only(tmp_path):
    # --dates-only opts into a kernel-less run, NOT into a ledger-less one; there is nothing to date-check.
    assert ec.check_ledger(tmp_path / "nope.json", dates_only=True) == ec.EXIT_UNVERIFIED


def test_absent_kernel_is_unverified_unless_dates_only(tmp_path, monkeypatch):
    # a fully dated ledger + no kernel: the proofs were NOT re-checked, so this is not a pass.
    assert _check(tmp_path, [_law("a", "2026-07-08")], monkeypatch, dates_only=False) == ec.EXIT_UNVERIFIED
    # ...and the same ledger with the opt-in IS a 0, because the caller asked for dates alone.
    assert _check(tmp_path, [_law("a", "2026-07-08")], monkeypatch, dates_only=True) == 0


def test_a_real_failure_outranks_could_not_verify(tmp_path, monkeypatch):
    # an undated law is a hard defect the date check CAN see without a kernel, so it must stay 1
    # rather than being masked as "unverified".
    assert _check(tmp_path, [_law("undated", "")], monkeypatch, dates_only=False) == 1


def test_the_three_exit_codes_are_distinct():
    assert ec.EXIT_UNVERIFIED not in (0, 1)


# --- the strict DEFAULT is the contract, so pin it without naming it ------------------------------
# Every test above passes dates_only explicitly, so flipping the default to True left them all green.
# The docstring's claim -- "it must be asked for, never inferred from the kernel being missing" --
# is carried entirely by that default, so something has to read it.

def test_strict_is_the_default(tmp_path, monkeypatch):
    import leibniz.backends.lean_repl as lr
    monkeypatch.setattr(lr, "available", lambda: False)
    p = tmp_path / "ledger.json"
    p.write_text(json.dumps({"laws": [_law("a", "2026-07-08")]}))
    assert ec.check_ledger(p) == ec.EXIT_UNVERIFIED          # no kwarg: the default must be strict


# --- the CLI is how the ADR 0033 publish act is actually performed --------------------------------

def test_main_wires_the_strict_default(tmp_path, monkeypatch):
    import leibniz.backends.lean_repl as lr
    monkeypatch.setattr(lr, "available", lambda: False)
    p = tmp_path / "ledger.json"
    p.write_text(json.dumps({"laws": [_law("a", "2026-07-08")]}))
    assert ec.main(["--check", str(p)]) == ec.EXIT_UNVERIFIED
    assert ec.main(["--check", "--dates-only", str(p)]) == 0


def test_main_rejects_an_unknown_flag(tmp_path, monkeypatch):
    # `--chek` used to be dropped by the `not a.startswith("-")` filter, run the help path, exit 0.
    assert ec.main(["--chek", str(tmp_path / "x.json")]) == ec.EXIT_UNVERIFIED
    # ...and an unknown flag ALONGSIDE --check must not be silently dropped either. This is the case
    # the help-path guard cannot cover: without the unknown-flag check the run proceeds and passes.
    import leibniz.backends.lean_repl as lr
    monkeypatch.setattr(lr, "available", lambda: False)
    p = tmp_path / "ledger.json"
    p.write_text(json.dumps({"laws": [_law("a", "2026-07-08")]}))
    assert ec.main(["--check", "--dates-only", "--bogus", str(p)]) == ec.EXIT_UNVERIFIED


# --- a gate that checked nothing must not print the tick -----------------------------------------

def _rc(tmp_path, obj, name="l.json", **kw):
    p = tmp_path / name
    p.write_text(json.dumps(obj) if not isinstance(obj, str) else obj)
    return ec.check_ledger(p, **kw)


def test_empty_laws_list_is_not_a_pass(tmp_path):
    assert _rc(tmp_path, {"laws": []}) == ec.EXIT_UNVERIFIED


def test_ledger_without_a_laws_key_is_not_a_pass(tmp_path):
    assert _rc(tmp_path, {"site": "Calculemus"}) == ec.EXIT_UNVERIFIED


def test_unreadable_ledger_is_unverified_not_a_traceback(tmp_path):
    assert _rc(tmp_path, "{not json") == ec.EXIT_UNVERIFIED
    assert ec.check_ledger(tmp_path) == ec.EXIT_UNVERIFIED     # a DIRECTORY: what deploy/profiles set


def test_qed_without_kernel_verified_is_a_failure(tmp_path, monkeypatch):
    # the loop only visits kernel_verified laws, so the boolean could silently shrink the gate.
    import leibniz.backends.lean_repl as lr
    monkeypatch.setattr(lr, "available", lambda: False)
    law = {"id": "x", "statement": "s", "qed": "Q.E.D.", "kernel_verified": False,
           "published_at": "2026-01-01"}
    assert _rc(tmp_path, {"laws": [law]}, dates_only=True) == 1


def test_non_string_published_at_is_undated(tmp_path, monkeypatch):
    # str(None) == "None" -- non-empty, so null/0/False used to read as DATED.
    import leibniz.backends.lean_repl as lr
    monkeypatch.setattr(lr, "available", lambda: False)
    for bad in (None, 0, False, []):
        law = {"id": "x", "statement": "s", "kernel_verified": False, "published_at": bad}
        assert _rc(tmp_path, {"laws": [law]}, dates_only=True) == 1, f"published_at={bad!r} passed"


def test_dates_only_skips_the_kernel_even_when_it_is_available(tmp_path, monkeypatch):
    """The 2x2 cell every other test here misses: dates_only=True with the kernel PRESENT.

    `--dates-only` means "do not re-verify proofs", not merely "tolerate a missing kernel". If it
    were only consulted inside `if not available():` the flag would be inert on any box with
    Docker, and a caller asking for the cheap date check would silently pay a full kernel re-verify
    -- and could get an exit 1 from proofs they explicitly asked not to check. Proven by a sentinel
    backend that raises if the kernel loop is ever entered.
    """
    import leibniz.backends.lean_repl as lr
    monkeypatch.setattr(lr, "available", lambda: True)          # kernel PRESENT

    class _Boom:
        def __init__(self, *a, **k):
            raise AssertionError("kernel loop ran despite dates_only=True")
    monkeypatch.setattr(lr, "LeanReplBackend", _Boom)

    law = dict(_law("a", "2026-07-08"), kernel_verified=True, qed="Q.E.D.")
    p = tmp_path / "ledger.json"
    p.write_text(json.dumps({"laws": [law]}))
    assert ec.check_ledger(p, dates_only=True) == 0
    assert ec.main(["--check", "--dates-only", str(p)]) == 0
