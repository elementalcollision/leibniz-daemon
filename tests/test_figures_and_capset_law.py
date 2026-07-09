"""ADR 0064 (figures) + ADR 0050 Phase 2 (8th law) — CI-safe guards.

A figure is a RENDERING of kernel-checked data, never evidence: generators parse the witness lists
out of the audited artifact, are deterministic (byte-identical on regeneration), and — for the KS
graph — re-derive a kernel-decided fact in Python (every basis pair orthogonal, the twin of
``cabello_bases_orth``) so the figure's arithmetic can't silently diverge. ``figures`` is report-only
on ``law_payload``. Opt-in ``LEIBNIZ_LEAN_E2E=1`` anchor does the real capset discharge.
"""
from __future__ import annotations

import ast
import importlib.util
import os
import re
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT / "scripts"))

from figures.gen_capset_figures import eq64_figure, parse_vectors, set81_figure  # noqa: E402
from figures.gen_ks_graph import ks_graph_figure, orthogonal, parse_data  # noqa: E402

_spec = importlib.util.spec_from_file_location("capset_law", _ROOT / "scripts" / "export_capset_law.py")
cap = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cap)

from leibniz.calculemus_site import law_payload  # noqa: E402


# --- ADR 0064: figures are deterministic renderings of the certified data --------------------------

def test_figure_data_is_parsed_verbatim_from_the_artifacts():
    art = (_ROOT / "docs" / "crt" / "capset_subgroups.lean").read_text()
    for name, count in (("set81", 20), ("eq64", 9)):
        vecs = parse_vectors(name)
        assert len(vecs) == count
        lean_literal = re.search(rf"def {name} : List \(List Int\) := (\[.*\])", art).group(1)
        assert vecs == ast.literal_eval(lean_literal)   # exactly the lists the kernel decided over
    rays, bases = parse_data()
    assert len(rays) == 33 and len(bases) == 14


def test_figures_are_deterministic_and_wellformed():
    for gen in (set81_figure, eq64_figure, ks_graph_figure):
        a, b = gen(), gen()
        assert a == b, f"{gen.__name__} is not byte-identical on regeneration"
        assert a["svg"].startswith("<svg ") and a["svg"].endswith("</svg>")
        assert "<script" not in a["svg"]
        assert a["caption"] and "docs/crt/" in a["generated_by"]


def test_ks_figure_arithmetic_matches_the_kernel_decided_fact():
    # the Python twin of `cabello_bases_orth`: every pair inside each of the 14 bases is orthogonal
    rays, bases = parse_data()
    for (i, j, k) in bases:
        assert orthogonal(rays[i], rays[j]) and orthogonal(rays[i], rays[k]) and orthogonal(rays[j], rays[k])
    # and the negative control's flipped ray breaks SOME orthogonality (a1bad exists in the artifact),
    # i.e. orthogonality is not vacuously true under this arithmetic
    assert not orthogonal(rays[0], rays[3]) or any(
        not orthogonal(rays[a], rays[b]) for a in range(4) for b in range(a + 1, 5))


def test_capset_grid_mappings_are_injective_on_the_witnesses():
    assert len({(3 * v[0] + v[2], 3 * v[1] + v[3]) for v in parse_vectors("set81")}) == 20
    assert len({(4 * v[0] + 2 * v[1] + v[2], 4 * v[3] + 2 * v[4] + v[5]) for v in parse_vectors("eq64")}) == 9


# --- the capset law --------------------------------------------------------------------------------

def test_capset_theorem_restates_both_artifact_statements():
    src = cap.build_theorem_src()
    assert src.startswith("theorem capset_subgroup_caps : (")
    assert ":=" not in src and "\n" not in src
    assert src.count("(List.range 20).all") == 3 and src.count("(List.range 9).all") == 4
    assert "addm 3" in src and "addm 2" in src


def test_capset_preamble_is_the_whole_artifact_verbatim():
    pre = cap.build_preamble()
    assert pre == (_ROOT / "docs" / "crt" / "capset_subgroups.lean").read_text().rstrip("\n")
    assert "import " not in pre and "namespace" not in pre       # pure-core, namespace-free artifact


def test_capset_payload_carries_two_figures():
    prop = cap.build_propositio()                     # no discharge here → kernel_verified stays False
    payload = law_payload(prop, specimen=False, tier="kernel-decided", origination="amplified",
                          references=cap._REFERENCES, figures=[set81_figure(), eq64_figure()])
    assert payload["id"] == "capset_subgroup_caps"
    assert payload["domain"] == "finite_geometry" and payload["imports"] == []
    assert len(payload["figures"]) == 2
    assert all(f["svg"].startswith("<svg ") and f["caption"] for f in payload["figures"])
    assert len(payload["references"]) == 1 and "Kable" in payload["references"][0]["citation"]


def test_figures_default_to_empty_for_existing_callers():
    payload = law_payload(cap.build_propositio(), references=cap._REFERENCES)
    assert payload["figures"] == []                   # additive: older exports are unaffected


@pytest.mark.skipif(not os.environ.get("LEIBNIZ_LEAN_E2E"), reason="set LEIBNIZ_LEAN_E2E=1 for the Lean e2e")
def test_real_kernel_discharge_is_qed_and_clean():  # pragma: no cover
    from leibniz.backends.lean_axioms import axiom_closure
    from leibniz.backends.lean_repl import LeanReplBackend, available
    from leibniz.verifiers import LeanVerifier
    if not available():
        pytest.skip("Lean image unavailable")
    prop = cap.build_propositio()
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
