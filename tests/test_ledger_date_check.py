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
    return {"id": lid, "statement": "s", "theorem_src": "theorem t : True", "proof_src": "trivial",
            "imports": [], "qed": "Q.E.D.", "kernel_verified": False,   # kernel loop skips unclaimed laws
            "published_at": published_at}


def _check(tmp_path, laws, monkeypatch):
    # force the kernel-unavailable path: the date check must decide the verdict on its own
    import leibniz.backends.lean_repl as lr
    monkeypatch.setattr(lr, "available", lambda: False)
    p = tmp_path / "ledger.json"
    p.write_text(json.dumps({"laws": laws}))
    return ec.check_ledger(p)


def test_undated_law_fails_even_without_the_kernel(tmp_path, monkeypatch):
    assert _check(tmp_path, [_law("dated", "2026-07-09"), _law("undated", "")], monkeypatch) == 1


def test_whitespace_date_counts_as_undated(tmp_path, monkeypatch):
    assert _check(tmp_path, [_law("sneaky", "  ")], monkeypatch) == 1


def test_fully_dated_ledger_passes_the_date_check(tmp_path, monkeypatch):
    assert _check(tmp_path, [_law("a", "2026-07-08"), _law("b", "2026-07-09T23:09:07Z")], monkeypatch) == 0
