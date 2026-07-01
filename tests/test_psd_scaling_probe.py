"""Guard the PSD scaling probe (SDP compute-trap measurement). Free-CPU (no numpy/ortools/docker): the
certificate must VERIFY at each size, and the bit-length must be monotone in n (the measured compute trap)."""
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


sp = _load("psd_scaling_probe", "scripts/psd_scaling_probe.py")


def test_rounded_pd_is_symmetric_and_diagonally_dominant():
    N = sp.rounded_pd(0, 6, 10 ** 6)
    n = len(N)
    for i in range(n):
        for j in range(n):
            assert N[i][j] == N[j][i]
        assert N[i][i] >= sum(abs(N[i][j]) for j in range(n) if j != i)   # PD by Gershgorin


def test_certs_verify_and_bitlength_grows():
    res = sp.probe(sizes=(6, 10, 14), kernel_upto=0)   # no kernel (free-CPU / CI)
    rows = [r for r in res["rows"] if "max_cert_bits" in r]
    assert all(r["exact_verifies"] is True for r in rows)     # the mechanism is correct at each size
    bits = [r["max_cert_bits"] for r in rows]
    assert bits == sorted(bits) and bits[-1] > bits[0]        # compute trap: bit-length grows with n
