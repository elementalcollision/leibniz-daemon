"""Guard the Delsarte upper-bound certificate bank. The corpus build is ortools-gated (operator-local);
the render + posture checks are free-CPU. Soundness: every banked cert must exact-verify and reproduce the
best-known (a below-best-known entry would be flagged TIGHTENS-INVESTIGATE, never silently banked)."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parent.parent
_HAS_ORTOOLS = importlib.util.find_spec("ortools") is not None
_needs_ortools = pytest.mark.skipif(not _HAS_ORTOOLS, reason="ortools is operator-local; skipped in CI")


def _load(mod, rel):
    import sys
    sys.path.insert(0, str(_ROOT))
    sys.path.insert(0, str(_ROOT / "scripts"))
    spec = importlib.util.spec_from_file_location(mod, _ROOT / rel)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


bank = _load("delsarte_bank", "scripts/delsarte_bank.py")
dl = _load("delsarte_lp_probe", "scripts/delsarte_lp_probe.py")


@_needs_ortools
def test_bank_all_certs_exact_verify_and_reproduce():
    res = bank.build(run_kernel=False)   # kernel step is docker-gated; the exact re-check is the sound leg
    assert res["n_entries"] == len(bank.CELLS)
    for r in res["rows"]:
        assert "skipped" not in r, f"{r['cell']} skipped: {r.get('skipped')}"
        ok, b, _ = dl.verify_integer_cert(r["n"], r["d"], r["cert_p"], r["cert_q"])
        assert ok and b == r["bound"]                       # the sound re-check passes
        assert r["novelty"] == "reproduces best-known"       # banked cells reproduce (no unverified beats)


def test_reading_room_is_audit_tier():
    fixture = {"n_entries": 1, "rows": [{"cell": "A(7,3)", "claim": "A(7,3) <= 16",
               "kernel": "KERNEL-VERIFIED", "novelty": "reproduces best-known",
               "method": "Delsarte LP dual certificate", "n": 7, "d": 3, "bound": 16}]}
    md = bank.render_reading_room(fixture)
    assert "Audit Annex" in md and "not\n" not in md.lower()[:0]  # banner present
    assert "not promulgated" in md.lower() and "A(7,3) <= 16" in md
