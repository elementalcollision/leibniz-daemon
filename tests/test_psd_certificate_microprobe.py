"""Guard the exact-PSD certificate micro-probe (SDP gate). Free-CPU (numpy only; no SDP solver, no docker):
pins the exact integer LDLᵀ certificate mechanism and the rounding-recovery recipe. The kernel leg is
docker-gated and exercised by the probe's main()."""
from __future__ import annotations

import importlib.util
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent


def _load(mod, rel):
    import sys
    sys.path.insert(0, str(_ROOT))
    sys.path.insert(0, str(_ROOT / "scripts"))
    spec = importlib.util.spec_from_file_location(mod, _ROOT / rel)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


m = _load("psd_certificate_microprobe", "scripts/psd_certificate_microprobe.py")


def test_exact_psd_certificate_verifies():
    # a strictly-PD integer matrix must yield an exact integer LDLᵀ certificate that verifies
    M, M_int = m._exact_pd(0, 4)
    L, d = m.ldlt(M)
    Li, di, sc = m.clear_denoms(L, d)
    assert all(x >= 0 for x in di) and sc > 0
    assert m.verify_int_cert(M_int, Li, di, sc) is True


def test_non_psd_matrix_has_no_verifying_certificate():
    # a matrix with a negative eigenvalue (indefinite) must NOT verify under a bogus certificate: any d with
    # a negative entry fails d>=0, and no valid LDLᵀ with d>=0 reproduces scale*M.
    Mind = [[1, 2], [2, 1]]  # eigenvalues 3, -1 -> indefinite
    # a fabricated certificate cannot satisfy both d>=0 and the identity
    assert m.verify_int_cert(Mind, [[1, 0], [2, 1]], [1, -3], 1) is False   # d has a negative entry
    assert m.verify_int_cert(Mind, [[1, 0], [2, 1]], [1, 3], 1) is False    # identity fails


def test_rounding_recipe_recovers_across_sample():
    trials = [(seed, n) for n in (3, 4) for seed in range(4)]
    recovered = sum(m._rounding_recovers(seed, n) for (seed, n) in trials)
    assert recovered == len(trials)   # noisy-float -> exact PSD cert recovers every time


def test_render_is_core_lean_integer_checker():
    M, M_int = m._exact_pd(1, 3)
    L, d = m.ldlt(M)
    Li, di, sc = m.clear_denoms(L, d)
    src = m.render_ldlt_lean(M_int, Li, di, sc)
    assert "ldltOK" in src and src.rstrip().endswith("decide")
    assert "Nat.choose" not in src and "Mathlib" not in src   # core Lean only
