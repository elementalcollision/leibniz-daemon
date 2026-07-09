"""ADR 0050 Phase 2 (6th + 7th laws) — CI-safe guards for the two census promotions.

Both use the whole-artifact-verbatim preamble: the audited certificate rides in FULL (closed namespace
blocks, its theorems included) minus only the ``import`` line, and the law theorem restates the census
facts by QUALIFIED names — so the law can never drift from the audit, and the census is pinned
COMPLETE (all 5 prob16 sequences; all 11 prob41 triples). Opt-in ``LEIBNIZ_LEAN_E2E=1`` anchors do the
real discharges.
"""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parent.parent


def _load(name, fname):
    spec = importlib.util.spec_from_file_location(name, _ROOT / "scripts" / fname)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


p16 = _load("p16_law", "export_prob16_census_law.py")
p41 = _load("p41_law", "export_prob41_census_law.py")

from leibniz.calculemus_site import law_payload  # noqa: E402


def _assert_whole_artifact_verbatim(preamble: str, artifact_path: Path):
    lines = artifact_path.read_text().splitlines()
    expected = "\n".join(ln for ln in lines if not ln.startswith("import "))
    assert preamble == expected, "preamble must be the WHOLE artifact verbatim minus import lines"
    assert "import " not in preamble.splitlines()[0]
    # namespaces ride along CLOSED (an open one could never be closed after _join_proof)
    assert preamble.count("namespace ") == preamble.count("end ")


# --- prob16 ----------------------------------------------------------------------------------------

def test_prob16_preamble_is_whole_artifact_verbatim():
    _assert_whole_artifact_verbatim(p16.build_preamble(), _ROOT / "docs" / "crt" / "prob16_census_certificate.lean")


def test_prob16_census_is_complete_and_join_safe():
    src = p16.build_propositio().expressio.theorem_src
    assert ":=" not in src and "\n" not in src
    for ns in ("SO_cube", "SO_quartic", "SO_factorial", "SO_fibonacci", "SO_primes"):
        assert f"{ns}.P" in src and f"{ns}.D" in src, f"census missing {ns}"
    # witnesses match the artifact's certified (m,n) per sequence
    assert "SO_cube.P 3 2 % SO_cube.D 2" in src
    assert "SO_quartic.P 4 3 % SO_quartic.D 3" in src
    assert "SO_fibonacci.P 4 3 % SO_fibonacci.D 3" in src


def test_prob16_payload_shape():
    payload = law_payload(p16.build_propositio(), specimen=False, tier="kernel-decided",
                          origination="amplified", references=p16._REFERENCES)
    assert payload["id"] == "prob16_census_refutations"
    assert payload["claim_type"] == "existence" and payload["domain"] == "number_theory"
    assert payload["proof_src"] == "by decide" and len(payload["references"]) == 2


# --- prob41 ----------------------------------------------------------------------------------------

def test_prob41_preamble_is_whole_artifact_verbatim():
    _assert_whole_artifact_verbatim(p41.build_preamble(), _ROOT / "docs" / "crt" / "prob41_census_certificate.lean")


def test_prob41_census_is_complete_and_join_safe():
    src = p41.build_propositio().expressio.theorem_src
    assert ":=" not in src and "\n" not in src
    triples = ["2_3_7", "3_4_5", "2_5_7", "3_5_8", "4_5_7", "3_7_8",
               "5_6_7", "5_6_8", "5_7_9", "5_8_9", "7_8_9"]
    for t in triples:                                   # all 11 non-normal triples ride in
        assert f"Prob41_{t}.wt" in src and f"Prob41_{t}.inI2 = false" in src, f"census missing {t}"
    # the headline smaller-than-textbook witnesses, with the artifact's thresholds
    assert "(84 ≤ Prob41_2_3_7.wt 1 2 6" in src
    assert "(120 ≤ Prob41_3_4_5.wt 2 3 3" in src


def test_prob41_witness_table_matches_the_artifact():
    artifact = (_ROOT / "docs" / "crt" / "prob41_census_certificate.lean").read_text()
    for t, thr, u in p41._WITNESSES:                    # each promoted fact is stated in the audit
        assert f"theorem triple_{t}_not_normal : {thr} ≤ wt {u[0]} {u[1]} {u[2]} ∧ inI2 = false" in artifact


def test_prob41_payload_shape():
    payload = law_payload(p41.build_propositio(), specimen=False, tier="kernel-decided",
                          origination="amplified", references=p41._REFERENCES)
    assert payload["id"] == "prob41_census_non_normal"
    assert payload["claim_type"] == "existence" and payload["domain"] == "commutative_algebra"
    assert payload["proof_src"] == "by decide"
    assert any("Ataka" in r["citation"] for r in payload["references"])


def test_amplified_requires_citations():
    assert p16._REFERENCES and all(r.get("citation") for r in p16._REFERENCES)
    assert p41._REFERENCES and all(r.get("citation") for r in p41._REFERENCES)


@pytest.mark.skipif(not os.environ.get("LEIBNIZ_LEAN_E2E"), reason="set LEIBNIZ_LEAN_E2E=1 for the Lean e2e")
@pytest.mark.parametrize("mod", [p16, p41], ids=["prob16", "prob41"])
def test_real_kernel_discharge_is_qed_and_clean(mod):  # pragma: no cover
    from leibniz.backends.lean_axioms import axiom_closure
    from leibniz.backends.lean_repl import LeanReplBackend, available
    from leibniz.verifiers import LeanVerifier
    if not available():
        pytest.skip("Lean image unavailable")
    prop = mod.build_propositio()
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
