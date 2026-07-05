"""Guard the cross-kernel amplification (scripts/verify_gk_crosskernel.py): the Guo–Krattenthaler
divisibilities Lean decided in #293, independently re-decided in Rocq/Coq. Exact-integer checks + cert
well-formedness are CI-safe; the sound-Coq (rocqchk) leg is Docker-gated. Tier audit; no trust surface."""
from __future__ import annotations

import importlib.util
from math import comb
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parent.parent


def _load():
    spec = importlib.util.spec_from_file_location("gkx", _ROOT / "scripts" / "verify_gk_crosskernel.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_cross_check_matches_lean_census_instances():
    m = _load()
    cc = m.cross_check()
    assert cc["all_ok"] is True and cc["count"] == 17     # (12,3) n1..8 + (12,4) n1..8 + (330,88) n1
    for top, bot, dz, ns in m.CASES:
        for n in ns:
            assert comb(top * n, bot * n) % (dz * n - 1) == 0, (top, bot, dz, n)


def test_cert_wellformed_and_no_cheating():
    import re
    m = _load()
    src, names = m.build_cert()
    assert len(names) == 17
    assert "Definition binom" in src and src.count("vm_compute. reflexivity. Qed.") == 17
    assert "div_12_3_n1" in src and "div_330_88_n1" in src
    code = re.sub(r"\(\*.*?\*\)", " ", src, flags=re.DOTALL)   # strip Coq comments (inert prose)
    for banned in ("Admitted", "admit", "Axiom", "Variable", "Context"):
        assert banned not in code


def test_live_coq_reverifies_sound():
    m = _load()
    from leibniz.backends import coq_docker
    if not coq_docker.available():
        pytest.skip("Docker + rocq/rocq-prover image unavailable")
    src, _ = m.build_cert()
    d = coq_docker.CoqDockerBackend(timeout_s=300).check_source_with_detail(src)
    assert d is not None and d["verified"] is True         # rocq compile + rocqchk audit
    assert d["audit_ran"] is True and d["opens_axioms"] is False   # axiom-free, name-agnostic audit
