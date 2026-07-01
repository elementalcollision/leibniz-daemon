"""Guard the Delsarte LP dual-certificate probe (P1, certificate-architecture pivot). Free-CPU: pins
Krawtchouk, the exact-integer certificate re-check (the SOUND leg), and the key soundness invariant — a
verified certificate is ALWAYS a valid upper bound, so no verified cert_bound is ever below a known A(n,d).
The kernel leg is docker-gated and exercised by the probe's main()."""
from __future__ import annotations

import importlib.util
from math import comb
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parent.parent

# ortools is an operator-local dependency (not in CI); the LP-solving tests skip cleanly when it is absent.
# The Krawtchouk + render tests below are ortools-free and always run.
_HAS_ORTOOLS = importlib.util.find_spec("ortools") is not None
_needs_ortools = pytest.mark.skipif(not _HAS_ORTOOLS, reason="ortools is operator-local; LP probe skipped in CI")


def _load(mod, rel):
    import sys
    sys.path.insert(0, str(_ROOT)); sys.path.insert(0, str(_ROOT / "scripts"))  # noqa: E702
    spec = importlib.util.spec_from_file_location(mod, _ROOT / rel)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


dl = _load("delsarte_lp_probe", "scripts/delsarte_lp_probe.py")


def test_krawtchouk_identities():
    n = 9
    assert all(dl.krawtchouk(0, i, n) == 1 for i in range(n + 1))      # K_0(i) = 1
    assert all(dl.krawtchouk(k, 0, n) == comb(n, k) for k in range(n + 1))  # K_k(0) = C(n,k)


@_needs_ortools
def test_verify_rejects_bogus_and_accepts_valid():
    n, d = 7, 3
    sol = dl.solve_dual_lp(n, d)
    assert sol is not None
    cert = dl.rationalize_and_verify(n, d, sol[0])
    assert cert is not None, "no exact certificate produced for A(7,3)"
    p, bound, q, _D = cert
    ok, b, _ = dl.verify_integer_cert(n, d, p, q)
    assert ok and b == bound == 16                     # valid cert reproduces A(7,3)=16
    bad_ok, _, probs = dl.verify_integer_cert(n, d, [0] * n, q)
    assert bad_ok is False and probs                   # all-zero cert must fail the exact re-check


@_needs_ortools
def test_probe_green_and_no_cert_below_known():
    res = dl.probe()
    assert res["gate"] == "GREEN"
    assert res["reproduced"] >= 4
    assert res["oracle_suspect"] == 0
    # SOUNDNESS INVARIANT: a verified Delsarte cert is a valid upper bound => cert_bound >= true A(n,d).
    for r in res["rows"]:
        if r.get("status") == "verified" and r.get("known") is not None:
            assert r["cert_bound"] >= r["known"], f"{r['cell']} cert {r['cert_bound']} < known {r['known']}"


def test_render_is_self_contained_core_lean():
    src = dl.render_cert_lean(7, 3, 10, [6, 3, 1, 0, 0, 1, 3], 16)
    assert "certOK 7 3 10" in src and src.rstrip().endswith("decide")
    assert "Nat.choose" not in src   # core Lean has no Mathlib; binomial is defined via Pascal's rule (cc)
    assert "def cc" in src
