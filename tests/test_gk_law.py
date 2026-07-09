"""ADR 0050 Phase 2 (4th law) — CI-safe guards for the Guo–Krattenthaler divisibilities promotion.

Second law at tier ``cross-kernel``: all 17 promoted facts (both (6n−1) families n=1..8 + the 330/88
instance) are re-decided by the Rocq 9.0 kernel in ``docs/crt/gk_coq_crosscheck.v`` — a test pins that
backing per fact so the tier can never go stale. The bounded-∀ theorem is mathematically identical to
the audited artifact's 17 per-instance theorems. §(B) Sun witnesses are deliberately NOT promoted
(different claim; not crosschecked). Opt-in ``LEIBNIZ_LEAN_E2E=1`` anchor does the real discharge.
"""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("gk_law", _ROOT / "scripts" / "export_guo_krattenthaler_law.py")
gk = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gk)

from leibniz.calculemus_site import law_payload  # noqa: E402


def test_theorem_src_is_a_join_safe_one_liner():
    src = gk.build_propositio().expressio.theorem_src
    assert src.startswith("theorem gk_divisibilities : (∀ n < 8, ")
    assert "Nat.choose 330 88" in src
    assert ":=" not in src and "\n" not in src


def test_preamble_is_the_artifacts_set_option_verbatim():
    pre = gk.build_preamble()
    artifact = (_ROOT / "docs" / "crt" / "guo_krattenthaler_certificate.lean").read_text()
    assert pre == "set_option maxRecDepth 8000" and pre in artifact
    assert "namespace" not in pre


def test_cross_kernel_tier_is_backed_per_fact_by_the_rocq_artifact():
    rocq = (_ROOT / "docs" / "crt" / "gk_coq_crosscheck.v").read_text()
    names = ([f"div_12_3_n{i}" for i in range(1, 9)]
             + [f"div_12_4_n{i}" for i in range(1, 9)] + ["div_330_88_n1"])
    for ex in names:                     # all 17 promoted facts re-decided in the second kernel
        assert ex in rocq, f"Rocq crosscheck missing {ex} — cross-kernel tier would be unbacked"


def test_sun_witnesses_are_not_in_the_promoted_statement():
    # §(B) is a different claim and is not crosschecked — it must not ride into this law.
    src = gk.build_propositio().expressio.theorem_src
    assert "¬" not in src and "sun" not in src.lower()


def test_amplified_law_payload_shape():
    prop = gk.build_propositio()                        # no discharge here → kernel_verified stays False
    payload = law_payload(prop, specimen=False, tier="cross-kernel", origination="amplified",
                          references=gk._REFERENCES)
    assert payload["id"] == "gk_divisibilities"
    assert payload["claim_type"] == "invariant" and payload["domain"] == "number_theory"
    assert payload["tier"] == "cross-kernel" and payload["origination"] == "amplified"
    assert payload["proof_src"] == "by decide"
    assert payload["imports"] == ["Mathlib.Tactic"]
    assert len(payload["references"]) == 1 and "Krattenthaler" in payload["references"][0]["citation"]


def test_amplified_requires_a_citation():
    assert gk._REFERENCES and all(r.get("citation") for r in gk._REFERENCES)


@pytest.mark.skipif(not os.environ.get("LEIBNIZ_LEAN_E2E"), reason="set LEIBNIZ_LEAN_E2E=1 for the Lean e2e")
def test_real_kernel_discharge_is_qed_and_clean():  # pragma: no cover
    from leibniz.backends.lean_axioms import axiom_closure
    from leibniz.backends.lean_repl import LeanReplBackend, available
    from leibniz.verifiers import LeanVerifier
    if not available():
        pytest.skip("Lean image unavailable")
    prop = gk.build_propositio()
    be = LeanReplBackend(timeout_s=300)
    try:
        LeanVerifier(be).discharge(prop.expressio, prop.demonstratio)
        ax = axiom_closure(be, prop.expressio.theorem_src, prop.demonstratio.proof_src,
                           prop.expressio.imports, allowed=frozenset({"propext"}),
                           preamble=prop.expressio.preamble)
    finally:
        be.close()
    assert prop.demonstratio.kernel_verified is True and prop.demonstratio.qed == "Q.E.D."
    assert ax["ok"] and set(ax["axioms"]) <= {"propext"}
