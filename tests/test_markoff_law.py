"""ADR 0050 Phase 2 (11th law) + ADR 0064 — CI-safe guards for the Markoff-cage promotion.

Whole-artifact-verbatim preamble (pure core, namespace-free; the p = 11 hyperbolic control rides
along); the figure generators mirror the artifact's exact matrix arithmetic and assert the Python
twins of the kernel-decided facts (posCheck for all nine certified primes, matOrder(7) = 8,
pisano(7) = 16) before drawing. Opt-in ``LEIBNIZ_LEAN_E2E=1`` anchor does the real discharge.
"""
from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT / "scripts"))

from figures.gen_markoff_figures import (  # noqa: E402
    IDEN, amat, mat_order, mersenne_figure, mpow, orbit7_figure, parse_primes, pisano, pos_check,
)

_spec = importlib.util.spec_from_file_location("mk_law", _ROOT / "scripts" / "export_markoff_law.py")
mk = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mk)

from leibniz.calculemus_site import law_payload  # noqa: E402


def test_certified_prime_lists_parse_verbatim():
    assert parse_primes("markoff_div_small") == [7, 13, 17, 23, 43, 47]
    assert parse_primes("markoff_div_mersenne") == [127, 524287, 2147483647]


def test_python_twin_matches_the_kernel_decided_facts():
    for p in parse_primes("markoff_div_small") + parse_primes("markoff_div_mersenne"):
        assert pos_check(p), f"posCheck({p}) diverges from the kernel"
    assert mat_order(7) == 8 and pisano(7) == 2 * 8
    assert pisano(127) == 2 * mat_order(127)
    # the hyperbolic control (p = 11 ≡ 1 mod 5): the order does NOT divide p+1 — as the kernel decided
    assert mpow(11, amat(11), 12) != IDEN


def test_figures_deterministic_and_wellformed():
    for gen in (orbit7_figure, mersenne_figure):
        a, b = gen(), gen()
        assert a == b, f"{gen.__name__} not byte-identical on regeneration"
        assert a["svg"].startswith("<svg ") and a["svg"].endswith("</svg>") and "<script" not in a["svg"]
        assert a["caption"] and "docs/crt/" in a["generated_by"]
    assert "A^8 = I" in orbit7_figure()["svg"]


def test_preamble_is_the_whole_artifact_verbatim():
    pre = mk.build_preamble()
    assert pre == (_ROOT / "docs" / "crt" / "markoff_cage.lean").read_text().rstrip("\n")
    assert "import " not in pre and "namespace" not in pre
    assert "markoff_control" in pre                     # the negative control rides along


def test_theorem_restates_the_three_positive_facts_and_is_join_safe():
    src = mk.build_propositio().expressio.theorem_src
    assert "allPos [7, 13, 17, 23, 43, 47] = true" in src
    assert "allPos [127, 524287, 2147483647] = true" in src
    assert "pisano 7 == 2 * matOrder 7" in src
    assert "markoff_control" not in src and "11" not in src   # the control is not promoted
    assert ":=" not in src and "\n" not in src


def test_payload_shape():
    payload = law_payload(mk.build_propositio(), specimen=False, tier="kernel-decided",
                          origination="amplified", references=mk._REFERENCES,
                          figures=[orbit7_figure(), mersenne_figure()])
    assert payload["id"] == "markoff_cage_core" and payload["domain"] == "arithmetic_dynamics"
    assert len(payload["figures"]) == 2 and payload["imports"] == []
    assert any("Bellah" in r["citation"] for r in payload["references"])


@pytest.mark.skipif(not os.environ.get("LEIBNIZ_LEAN_E2E"), reason="set LEIBNIZ_LEAN_E2E=1 for the Lean e2e")
def test_real_kernel_discharge_is_qed_and_clean():  # pragma: no cover
    from leibniz.backends.lean_axioms import axiom_closure
    from leibniz.backends.lean_repl import LeanReplBackend, available
    from leibniz.verifiers import LeanVerifier
    if not available():
        pytest.skip("Lean image unavailable")
    prop = mk.build_propositio()
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
