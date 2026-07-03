"""Guard T8-a — the minimal rational-HMM beyond-Markov certificate suite (scripts/beyond_markov_cert.py).
CI-safe: the exact-rational producer legs (HMM validity, Hankel rank-lower minor, Markov-order>K separation,
and the corrupted-control being Python-rejectable) run everywhere; the real-Lean-kernel attestation leg is
docker-gated and CI-skips, mirroring the terwilliger/bareiss kernel tests. No trust surface is touched."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parent.parent


def _load():
    spec = importlib.util.spec_from_file_location("beyond_markov_cert", _ROOT / "scripts" / "beyond_markov_cert.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _lean_available() -> bool:
    try:
        from leibniz.backends.lean_cli import available
        return bool(available())
    except Exception:
        return False


def test_both_witnesses_certify():
    m = _load()
    for hmm in (m.bm1_two_mode(), m.even_process()):
        c = m.certify(hmm, K=8)
        assert c["validity"]["valid"] is True                       # a genuine stochastic process (HMM)
        assert c["rank_cert"]["ok"] and c["rank_cert"]["det_int"] != 0   # rank(H) >= 2 by a nonsingular minor
        assert all(o["ok"] for o in c["order_certs"])               # order > 8, all separation certs hold
        assert all(o["num_h1"] > 0 and o["num_h2"] > 0 for o in c["order_certs"])  # denominator positivity
        assert c["certified"] is True


def test_validity_is_load_bearing():
    # A signed operator (not a valid HMM) must be rejected by the validity leg — the panel's #1 mandate.
    m = _load()
    from fractions import Fraction as Fr
    bad = m.even_process()
    bad["T"][0][0][0] = Fr(-1, 2)                                    # negative entry -> not a valid HMM
    assert m.hmm_valid(bad)["valid"] is False


def test_corrupted_rank_minor_is_python_rejectable():
    # The corrupted control (used for the kernel leg) makes the rank minor singular -> det 0.
    m = _load()
    hmm = m.bm1_two_mode()
    c = m.certify(hmm)
    bad_H = [c["rank_cert"]["H_int"][0][:], c["rank_cert"]["H_int"][0][:]]   # row 1 := row 0
    det = bad_H[0][0] * bad_H[1][1] - bad_H[0][1] * bad_H[1][0]
    assert det == 0                                                 # so the kernel's minorNZ returns false


def test_order_separation_is_a_real_conditional_difference():
    # D_k != 0 <=> P(a|h1) != P(a|h2): cross-check the cleared determinant against the exact conditionals.
    m = _load()
    hmm = m.bm1_two_mode()
    oc = hmm["order"]
    for k in (0, 3, 7):
        cert = m.order_separation_cert(hmm, k, a=oc["a"], pre1=oc["pre1"], pre2=oc["pre2"], suffix=oc["suffix"])
        h1, h2, a = tuple(cert["h1"]), tuple(cert["h2"]), cert["sym"]
        cond1 = m.prob(hmm, h1 + (a,)) / m.prob(hmm, h1)
        cond2 = m.prob(hmm, h2 + (a,)) / m.prob(hmm, h2)
        assert (cert["det_int"] != 0) == (cond1 != cond2)           # the det witness tracks the real difference


@pytest.mark.skipif(not _lean_available(), reason="Lean/docker unavailable; kernel-attest leg is operator-local")
def test_kernel_attests_and_rejects_corruption():
    m = _load()
    from leibniz.backends.lean_cli import LeanCliBackend
    bk = LeanCliBackend(timeout_s=120)
    for hmm in (m.bm1_two_mode(), m.even_process()):
        c = m.certify(hmm)
        assert bk.check_source(m.render_cert_lean(hmm, None, c["rank_cert"], c["order_certs"])) is True
        assert bk.check_source(m.render_cert_lean_bogus(hmm, c["rank_cert"], c["order_certs"])) is False
