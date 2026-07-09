"""ADR 0050 Phase 2 (3rd law) — CI-safe guards for the Erdős-707 finite-core promotion.

The first law at tier ``cross-kernel`` (ADR 0048): the same Alexeev–Mixon witness facts are re-decided
by the Rocq 9.0 kernel in ``docs/crt/erdos_707_crosscheck.v``. The Lean defs ride in the ADR 0062
preamble as a VERBATIM contiguous slice of the audited ``docs/crt/erdos_707_certificate.lean`` — minus
its ``namespace Erdos707`` wrapper (``_join_proof`` appends the theorem after the preamble, so an
opened namespace could never be closed). An opt-in ``LEIBNIZ_LEAN_E2E=1`` anchor does the real
discharge + axiom check.
"""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("e707_law", _ROOT / "scripts" / "export_erdos707_law.py")
e707 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(e707)

from leibniz.calculemus_site import law_payload  # noqa: E402


def test_theorem_src_is_a_join_safe_one_liner():
    src = e707.build_propositio().expressio.theorem_src
    assert src.startswith("theorem erdos707_am_witness : (diffsZ [1, 2, 4, 8, 13]).Nodup ∧ ")
    assert ":=" not in src and "\n" not in src


def test_preamble_is_a_verbatim_namespace_free_slice_of_the_artifact():
    pre = e707.build_preamble()
    artifact = (_ROOT / "docs" / "crt" / "erdos_707_certificate.lean").read_text()
    set_opt, _, defs_block = pre.partition("\n\n")
    assert set_opt.startswith("set_option maxHeartbeats") and set_opt in artifact
    assert defs_block in artifact, "def block is not a verbatim contiguous slice of the audited artifact"
    for sym in ("def diffsZ", "def diffsMod", "def isPDS"):
        assert sym in defs_block, f"preamble missing {sym!r}"
    # the namespace wrapper must NOT ride along — it could never be closed after _join_proof
    assert "namespace" not in pre and "end Erdos707" not in pre


def test_cross_kernel_tier_is_backed_by_the_rocq_artifact():
    # tier=cross-kernel is honest only while the second-kernel re-decision of the SAME witness facts
    # exists in-repo (ADR 0048). Pin the artifact + its AM5 examples.
    rocq = (_ROOT / "docs" / "crt" / "erdos_707_crosscheck.v").read_text()
    for ex in ("AM5_sidon", "AM5_no_order5", "AM5_no_order6"):
        assert ex in rocq, f"Rocq crosscheck missing {ex} — cross-kernel tier would be unbacked"


def test_amplified_law_payload_shape():
    prop = e707.build_propositio()                       # no discharge here → kernel_verified stays False
    payload = law_payload(prop, specimen=False, tier="cross-kernel", origination="amplified",
                          references=e707._REFERENCES)
    assert payload["id"] == "erdos707_am_witness"
    assert payload["claim_type"] == "invariant"
    assert payload["domain"] == "additive_combinatorics"
    assert payload["tier"] == "cross-kernel" and payload["origination"] == "amplified"
    assert payload["proof_src"] == "by decide"
    assert "def isPDS" in payload["preamble"]
    assert payload["imports"] == ["Mathlib.Tactic"]
    assert len(payload["references"]) == 2 and "Alexeev" in payload["references"][0]["citation"]


def test_amplified_requires_a_citation():
    assert e707._REFERENCES and all(r.get("citation") for r in e707._REFERENCES)


@pytest.mark.skipif(not os.environ.get("LEIBNIZ_LEAN_E2E"), reason="set LEIBNIZ_LEAN_E2E=1 for the Lean e2e")
def test_real_kernel_discharge_is_qed_and_axiom_free():  # pragma: no cover
    from leibniz.backends.lean_axioms import axiom_closure
    from leibniz.backends.lean_repl import LeanReplBackend, available
    from leibniz.verifiers import LeanVerifier
    if not available():
        pytest.skip("Lean image unavailable")
    prop = e707.build_propositio()
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
    assert ax["ok"] and set(ax["axioms"]) <= {"propext"}   # measured: [] — no axioms at all
