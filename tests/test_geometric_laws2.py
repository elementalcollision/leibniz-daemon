"""ADR 0050 Phase 2 (9th + 10th laws) + ADR 0064 — CI-safe guards for the Steiner and
double-blocking promotions and their figures.

Whole-artifact-verbatim preambles (both artifacts are pure-core, namespace-free); each figure
generator asserts a Python twin of a kernel-decided fact before drawing (difference-family
completeness; every-line-blocked-twice). Opt-in ``LEIBNIZ_LEAN_E2E=1`` anchors do the real
discharges.
"""
from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT / "scripts"))

from figures.gen_double_blocking_figures import (  # noqa: E402
    assert_double_blocking, db13_figure, db19_figure, parse as db_parse,
)
from figures.gen_steiner_figures import (  # noqa: E402
    assert_diff_family, parse as st_parse, s8_225_figure, s9_289_figure,
)


def _load(name, fname):
    spec = importlib.util.spec_from_file_location(name, _ROOT / "scripts" / fname)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


st = _load("steiner_law", "export_steiner_law.py")
db = _load("db_law", "export_double_blocking_law.py")

from leibniz.calculemus_site import law_payload  # noqa: E402


# --- figures: certified-data provenance + kernel-twin assertions -----------------------------------

def test_steiner_figure_data_and_kernel_twin():
    assert len(st_parse("blocks8")) == 4 and all(len(b) == 8 for b in st_parse("blocks8"))
    assert len(st_parse("blocks9")) == 4 and all(len(b) == 9 for b in st_parse("blocks9"))
    assert assert_diff_family(st_parse("mods8"), st_parse("blocks8")) == 224
    assert assert_diff_family(st_parse("mods9"), st_parse("blocks9")) == 288


def test_double_blocking_figure_data_and_kernel_twin():
    for q in (13, 19):
        B, lines = db_parse(f"B{q}"), db_parse(f"lines{q}")
        assert len(B) == 3 * q - 1
        assert_double_blocking(q, B, lines)              # every line meets B ≥ 2 — the kernel's fact


def test_all_four_figures_deterministic_and_wellformed():
    for gen in (s8_225_figure, s9_289_figure, db13_figure, db19_figure):
        a, b = gen(), gen()
        assert a == b, f"{gen.__name__} not byte-identical on regeneration"
        assert a["svg"].startswith("<svg ") and a["svg"].endswith("</svg>") and "<script" not in a["svg"]
        assert a["caption"] and "docs/crt/" in a["generated_by"]


# --- the two laws ----------------------------------------------------------------------------------

def test_preambles_are_whole_artifacts_verbatim():
    assert st.build_preamble() == (_ROOT / "docs" / "crt" / "steiner_designs.lean").read_text().rstrip("\n")
    assert db.build_preamble() == (_ROOT / "docs" / "crt" / "double_blocking.lean").read_text().rstrip("\n")
    for pre in (st.build_preamble(), db.build_preamble()):
        assert "import " not in pre and "namespace" not in pre


def test_theorems_restate_the_audited_facts_and_are_join_safe():
    s = st.build_propositio().expressio.theorem_src
    assert s == ("theorem steiner_s8_225_s9_289 : (isDiffFamily mods8 blocks8 224 = true) "
                 "∧ (isDiffFamily mods9 blocks9 288 = true)")
    d = db.build_propositio().expressio.theorem_src
    for frag in ("doubleBlocking 13 B13 lines13 = true", "minimalDBS 13 B13 lines13 = true",
                 "doubleBlocking 19 B19 lines19 = true", "minimalDBS 19 B19 lines19 = true"):
        assert frag in d
    for src in (s, d):
        assert ":=" not in src and "\n" not in src


def test_payload_shapes():
    p1 = law_payload(st.build_propositio(), specimen=False, tier="kernel-decided",
                     origination="amplified", references=st._REFERENCES,
                     figures=[s8_225_figure(), s9_289_figure()])
    assert p1["id"] == "steiner_s8_225_s9_289" and p1["domain"] == "combinatorial_design_theory"
    assert len(p1["figures"]) == 2 and "Hetman" in p1["references"][0]["citation"]
    p2 = law_payload(db.build_propositio(), specimen=False, tier="kernel-decided",
                     origination="amplified", references=db._REFERENCES,
                     figures=[db13_figure(), db19_figure()])
    assert p2["id"] == "double_blocking_3qm1" and p2["domain"] == "finite_geometry"
    assert len(p2["figures"]) == 2 and any("Hill" in r["citation"] for r in p2["references"])


@pytest.mark.skipif(not os.environ.get("LEIBNIZ_LEAN_E2E"), reason="set LEIBNIZ_LEAN_E2E=1 for the Lean e2e")
@pytest.mark.parametrize("mod", [st, db], ids=["steiner", "double_blocking"])
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
