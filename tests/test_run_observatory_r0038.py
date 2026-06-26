"""ADR 0038 — the opt-in Observatory run entrypoint (scripts/run_observatory.py).

Exercises the generate->decide->ledger loop with an injected conjecturer (no live LLM/Walnut),
and pins the safety property: the ledger never contains a promulgated (Q.E.D.) record.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from leibniz.observatory import WalnutObservatory
from leibniz.types import FinishReason
from leibniz.walnut_conjecture import WalnutConjecturer

# load scripts/run_observatory.py (scripts/ is not a package)
_SPEC = importlib.util.spec_from_file_location(
    "run_observatory", Path(__file__).resolve().parent.parent / "scripts" / "run_observatory.py")
run_observatory_mod = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(run_observatory_mod)

_UNIVERSAL = "msd_2\n\n0 1\n0 -> 0\n1 -> 0\n"
_NON_UNIVERSAL = "msd_2\n\n0 1\n0 -> 0\n1 -> 1\n\n1 0\n0 -> 1\n1 -> 1\n"


def _draft(stmt="Thue-Morse overlap-free", pred="A i p ...", num="msd_2"):
    return json.dumps({"statement": stmt, "walnut_predicate": pred,
                       "walnut_numeration": num, "falsifiable_claim": "c"})


class _CycleProvider:
    """Returns a fixed sequence of drafts (one per propose call)."""
    def __init__(self, drafts):
        self._drafts = list(drafts)
        self._i = 0

    def propose(self, role, context):
        d = self._drafts[self._i % len(self._drafts)]
        self._i += 1
        return d


def test_run_observatory_writes_ledger_and_counts(tmp_path):
    # one decidable (universal) + one refuted, deterministically alternating
    conj = WalnutConjecturer(
        provider=_CycleProvider([_draft(), _draft()]),
        observatory=WalnutObservatory(
            runner=lambda *a, **k: _UNIVERSAL if a[0] else _UNIVERSAL),  # universal -> DECIDED
    )
    out = tmp_path / "ledger.json"
    summary = run_observatory_mod.run_observatory(conj, count=3, out_path=out)
    assert summary["count"] == 3
    assert summary["decided"] == 3
    assert summary["by_reason"].get(FinishReason.WALNUT_DECIDED.value) == 3
    data = json.loads(out.read_text())
    assert len(data["records"]) == 3
    # SAFETY: no record is promulgated (the tier is strictly non-Q.E.D.)
    assert all(r["promulgated"] is False for r in data["records"])
    assert data["records"][0]["automaton_certificate"] == _UNIVERSAL


def test_run_observatory_refuted_and_unproven(tmp_path):
    conj_ref = WalnutConjecturer(
        provider=_CycleProvider([_draft()]),
        observatory=WalnutObservatory(runner=lambda *a, **k: _NON_UNIVERSAL))
    s = run_observatory_mod.run_observatory(conj_ref, count=2, out_path=tmp_path / "r.json")
    assert s["decided"] == 0
    assert s["by_reason"].get(FinishReason.REFUTED.value) == 2


def test_run_observatory_no_proposal(tmp_path):
    conj = WalnutConjecturer(provider=_CycleProvider(["garbage"]),
                             observatory=WalnutObservatory(runner=lambda *a, **k: _UNIVERSAL))
    s = run_observatory_mod.run_observatory(conj, count=2, out_path=tmp_path / "n.json")
    assert s["by_reason"].get("no_proposal") == 2
    assert s["decided"] == 0
