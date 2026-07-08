"""ADR 0050 Phase 2 (2nd law) + ADR 0062 — CI-safe guards for the complex-Hadamard-order-94 promotion.

The Example-1 witness theorem (Theorem-4 hypothesis: autocorrelation eq (1) + symmetry of A,B) is a
clean one-liner; its legible definitions ride in the Expressio preamble, read VERBATIM from the audited
artifact ``docs/crt/hadamard94.lean``. These tests pin the statement/preamble shape, the byte-identity
to the artifact, and the amplified-law payload. An opt-in ``LEIBNIZ_LEAN_E2E=1`` anchor does the real
discharge + axiom check.
"""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("had94_law", _ROOT / "scripts" / "export_hadamard94_law.py")
had = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(had)

from leibniz.calculemus_site import law_payload  # noqa: E402


def test_theorem_src_is_a_clean_one_liner():
    src = had.build_propositio().expressio.theorem_src
    assert src == "theorem had94_witness1 : (eq1 a1 b1 c1 d1 && symrow a1 && symrow b1) = true"
    assert ":=" not in src and "\n" not in src


def test_preamble_is_byte_identical_to_the_audited_artifact():
    # the law's definitions must not drift from docs/crt/hadamard94.lean — they are the same slice
    pre = had.build_preamble()
    artifact = (_ROOT / "docs" / "crt" / "hadamard94.lean").read_text()
    assert pre in artifact, "preamble is not a verbatim slice of the audited artifact"
    for sym in ("def rot", "def dotf", "def autocorr", "def eq1", "def symrow",
                "def a1", "def b1", "def c1", "def d1"):
        assert sym in pre, f"preamble missing {sym!r}"
    # excludes the Example-2 / negative-control data the witness theorem does not use
    assert "def a2" not in pre and "a1bad" not in pre
    assert pre.startswith("set_option maxHeartbeats 0")


def test_amplified_law_payload_shape():
    prop = had.build_propositio()                       # no discharge here → kernel_verified stays False
    payload = law_payload(prop, specimen=False, tier="kernel-decided", origination="amplified",
                          references=had._REFERENCES)
    assert payload["id"] == "had94_witness1"
    assert payload["claim_type"] == "existence"
    assert payload["domain"] == "combinatorial_design_theory"
    assert payload["tier"] == "kernel-decided" and payload["origination"] == "amplified"
    assert payload["proof_src"] == "by decide"
    assert "def eq1" in payload["preamble"]
    assert len(payload["references"]) == 1 and "Szöllősi" in payload["references"][0]["citation"]


def test_amplified_requires_a_citation():
    assert had._REFERENCES and all(r.get("citation") for r in had._REFERENCES)


@pytest.mark.skipif(not os.environ.get("LEIBNIZ_LEAN_E2E"), reason="set LEIBNIZ_LEAN_E2E=1 for the Lean e2e")
def test_real_kernel_discharge_is_qed_and_propext_clean():  # pragma: no cover
    from leibniz.backends.lean_axioms import axiom_closure
    from leibniz.backends.lean_repl import LeanReplBackend, available
    from leibniz.verifiers import LeanVerifier
    if not available():
        pytest.skip("Lean image unavailable")
    prop = had.build_propositio()
    be = LeanReplBackend(timeout_s=300)
    try:
        LeanVerifier(be).discharge(prop.expressio, prop.demonstratio)
        ax = axiom_closure(be, prop.expressio.theorem_src, prop.demonstratio.proof_src,
                           prop.expressio.imports, allowed=frozenset({"propext"}),
                           preamble=prop.expressio.preamble)
    finally:
        be.close()
    assert prop.demonstratio.kernel_verified is True
    assert prop.demonstratio.qed == "Q.E.D."
    assert ax["ok"] and set(ax["axioms"]) <= {"propext"}
