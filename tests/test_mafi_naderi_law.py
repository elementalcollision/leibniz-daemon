"""ADR 0050 Phase 2 (5th law) — CI-safe guards for the Mafi–Naderi embedded-prime promotion.

One law for the t=2 instance: the cap-sum closure strictly contains M_{3,2} and gains the embedded
prime (x,y,z), while M itself admits no such witness. The defs ride in the ADR 0062 preamble as a
VERBATIM contiguous slice of the audited ``docs/crt/mafi_naderi_certificate.lean`` (t=2 namespace
body; the wrapper is dropped as usual). The artifact also certifies t=3 — same def names, so only one
instance can ride in a single preamble; a test pins that the promoted slice is the t=2 one. Opt-in
``LEIBNIZ_LEAN_E2E=1`` anchor does the real discharge.
"""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("mn_law", _ROOT / "scripts" / "export_mafi_naderi_law.py")
mn = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mn)

from leibniz.calculemus_site import law_payload  # noqa: E402


def test_theorem_src_is_a_join_safe_one_liner():
    src = mn.build_propositio().expressio.theorem_src
    assert src.startswith("theorem mafi_naderi_t2_embedded_prime : ")
    assert ":=" not in src and "\n" not in src
    # the three audited t=2 facts all ride in the conjunction
    assert "inM 1 1 2 = false" in src                      # strict-containment witness
    assert "inClosure 1 1 1 = false" in src                # embedded-prime witness for the closure
    assert "inM (a+1) b c = true" in src                   # no-witness sweep for M itself


def test_preamble_is_the_verbatim_t2_slice():
    pre = mn.build_preamble()
    artifact = (_ROOT / "docs" / "crt" / "mafi_naderi_certificate.lean").read_text()
    assert pre in artifact, "preamble is not a verbatim contiguous slice of the audited artifact"
    for sym in ("def inClosure", "def gens", "def inM"):
        assert sym in pre
    # the t=2 instance specifically (cap 2, threshold 4) — not the t=3 block
    assert "min a 2 + min b 2 + min c 2" in pre and "(0,2,2)" in pre
    assert "min a 3" not in pre
    assert "namespace" not in pre and "end MafiNaderi" not in pre


def test_amplified_law_payload_shape():
    prop = mn.build_propositio()                        # no discharge here → kernel_verified stays False
    payload = law_payload(prop, specimen=False, tier="kernel-decided", origination="amplified",
                          references=mn._REFERENCES)
    assert payload["id"] == "mafi_naderi_t2_embedded_prime"
    assert payload["claim_type"] == "invariant" and payload["domain"] == "commutative_algebra"
    assert payload["tier"] == "kernel-decided" and payload["origination"] == "amplified"
    assert payload["proof_src"] == "by decide"
    assert payload["imports"] == ["Mathlib.Tactic"]
    assert len(payload["references"]) == 2 and "Mafi" in payload["references"][0]["citation"]


def test_amplified_requires_a_citation():
    assert mn._REFERENCES and all(r.get("citation") for r in mn._REFERENCES)


@pytest.mark.skipif(not os.environ.get("LEIBNIZ_LEAN_E2E"), reason="set LEIBNIZ_LEAN_E2E=1 for the Lean e2e")
def test_real_kernel_discharge_is_qed_and_clean():  # pragma: no cover
    from leibniz.backends.lean_axioms import axiom_closure
    from leibniz.backends.lean_repl import LeanReplBackend, available
    from leibniz.verifiers import LeanVerifier
    if not available():
        pytest.skip("Lean image unavailable")
    prop = mn.build_propositio()
    be = LeanReplBackend(timeout_s=300)
    try:
        LeanVerifier(be).discharge(prop.expressio, prop.demonstratio)
        ax = axiom_closure(be, prop.expressio.theorem_src, prop.demonstratio.proof_src,
                           prop.expressio.imports, allowed=frozenset({"propext"}),
                           preamble=prop.expressio.preamble)
    finally:
        be.close()
    assert prop.demonstratio.kernel_verified is True and prop.demonstratio.qed == "Q.E.D."
    assert ax["ok"] and set(ax["axioms"]) <= {"propext"}   # measured: [] — no axioms at all
