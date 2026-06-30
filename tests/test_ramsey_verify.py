"""Guard the scoped Ramsey verifier framework (Gate B2). Audit-tier; kernel parts docker-gated.

Pins the untrusted VT-reduced checker (verify_ramsey / omega_alpha), the render's refusal of a false
witness, and the tractability cap that keeps `decide` in the toy regime (the B2 finding: frontier Ramsey
needs a certificate architecture, not `decide`).
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parent.parent


def _load(mod_name: str, rel: str):
    spec = importlib.util.spec_from_file_location(mod_name, _ROOT / rel)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


rv = _load("ramsey_verify", "scripts/ramsey_verify.py")
try:
    from leibniz.backends.lean_cli import LeanCliBackend, available
    _DOCKER = available()
except Exception:
    _DOCKER = False


def _qr(p):
    return sorted({(x * x) % p for x in range(1, p)})


def test_c5_is_a_valid_r33_witness():
    ok, reason = rv.verify_ramsey(5, 3, 3, [1, 4])
    assert ok, reason


def test_paley_omega_alpha_and_validity():
    assert rv.omega_alpha(13, _qr(13)) == (3, 3)
    assert rv.omega_alpha(17, _qr(17)) == (3, 3)
    assert rv.verify_ramsey(17, 4, 4, _qr(17))[0] is True   # R(4,4) > 17


def test_rejects_clique_and_asymmetric():
    assert rv.verify_ramsey(5, 3, 3, [1, 2, 3, 4])[0] is False   # K5 has a triangle
    assert rv.verify_ramsey(5, 3, 3, [1])[0] is False            # asymmetric connection set


def test_render_emits_decidable_theorem_for_toy():
    src = rv.render_ramsey_lean(5, 3, 3, [1, 4])
    assert "ramseyWitness 5 3 3" in src and ":= by\n  decide" in src and "ramsey_3_3_gt_5" in src


def test_render_refuses_false_witness():
    with pytest.raises(ValueError):
        rv.render_ramsey_lean(5, 3, 3, [1, 2, 3, 4])


def test_render_refuses_frontier_beyond_cap():
    with pytest.raises(ValueError, match="decide cap"):
        rv.render_ramsey_lean(17, 4, 4, _qr(17))   # 4760 subsets > cap (frontier needs certificates)


@pytest.mark.skipif(not _DOCKER, reason="Lean kernel (docker) unavailable")
def test_c5_render_is_kernel_verified():
    assert LeanCliBackend().check_source(rv.render_ramsey_lean(5, 3, 3, [1, 4])) is True
