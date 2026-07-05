"""Guard the cross-kernel Erdős-707 verification (scripts/verify_erdos_707_crosskernel.py): the Sidon +
non-extension finite core Lean decided in #295, independently re-decided in Rocq/Coq. Exact-integer checks +
cert well-formedness are CI-safe; the sound-Coq (rocqchk) leg is Docker-gated. Tier audit; no trust surface."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parent.parent


def _load():
    spec = importlib.util.spec_from_file_location("e707x", _ROOT / "scripts" / "verify_erdos_707_crosskernel.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_cross_check_sidon_and_nonextending():
    m = _load()
    cc = m.cross_check()
    assert cc["all_ok"] is True and len(cc["rows"]) == 4
    for r in cc["rows"]:
        assert r["sidon"] is True and r["non_extending"] is True


def test_cert_wellformed_and_no_cheating():
    import re
    m = _load()
    src, names = m.build_cert()
    assert len(names) == 12                                  # 4 sets × (sidon + 2 non-extension orders)
    assert src.count("vm_compute. reflexivity. Qed.") == 12
    assert "Definition isPDS" in src and "Definition extends1" in src
    assert "A_sidon" in src and "Hall_no_order6" in src
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
    assert d is not None and d["verified"] is True
    assert d["audit_ran"] is True and d["opens_axioms"] is False
