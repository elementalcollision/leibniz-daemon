"""Guard the Tier-1 counterexample-certificate domain (scripts/counterexample_domain.py) — one certify(object)
interface over the finite/exact-decidable open-problem counterexamples. The certify() checks are CI-safe
(exact arithmetic, no Lean); the emitted Lean certs are exercised by a REPL-gated test. No trust surface."""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parent.parent


def _load():
    spec = importlib.util.spec_from_file_location("counterexample_domain",
                                                  _ROOT / "scripts" / "counterexample_domain.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_families_registered_across_two_tiers():
    m = _load()
    assert set(m.FAMILIES) == {"monomial_normal", "self_ordered", "n_absorbing", "pipeline_ring"}
    tiers = {f: m.FAMILIES[f]["tier"] for f in m.FAMILIES}
    assert tiers["monomial_normal"] == 1 and tiers["self_ordered"] == 1 and tiers["n_absorbing"] == 1
    assert tiers["pipeline_ring"] == 2


def test_pipeline_ring_tier2_is_attested_not_decided():
    m = _load()
    for prob, thm in [("4b", "problem4b_false"), ("20", "problem20_answer"),
                      ("27b", "problem27b_false"), ("30c", "problem30c_false")]:
        c = m.certify({"family": "pipeline_ring", "params": {"problem": prob}})
        assert c["tier"] == 2 and c["verdict"] == "attested"
        assert c["kernel"]["check"] == "lake-build" and thm in c["kernel"]["theorem"]
        assert set(c["kernel"]["axioms"]) == {"propext", "Classical.choice", "Quot.sound"}
        assert "git checkout" in c["kernel"]["reproduction"] and "verify.sh" in c["kernel"]["reproduction"]
        assert any("pipeline-math" in r.get("url", "") for r in c["references"])   # code trail cited


def test_monomial_normal_family():
    m = _load()
    c = m.certify({"family": "monomial_normal", "params": {"a": 4, "b": 5, "c": 7}})
    assert c["tier"] == 1 and c["verdict"] == "not-normal" and c["witness"] == [2, 4, 5]
    assert c["kernel"]["check"] == "decide" and "triple_4_5_7_not_normal" in c["kernel"]["theorem"]
    assert m.certify({"family": "monomial_normal", "params": {"a": 3, "b": 3, "c": 3}})["verdict"] == "normal"


def test_self_ordered_family_refutes_and_certifies():
    m = _load()
    cube = m.certify({"family": "self_ordered", "params": {"seq": "cube", "bound": 6}})
    assert cube["verdict"] == "not-self-ordered" and cube["witness"] == [3, 2]   # D_2 ∤ P_{3,2}
    # ADR 0090: pin the SHAPE, not the exact tactic line. The certs now carry
    # `set_option maxRecDepth` because NAbs9 hit the recursion wall, and Lean answers that by
    # stamping the declaration with `sorryAx` rather than failing loudly.
    lean = cube["kernel"]["lean"]
    assert "≠ 0 := by" in lean and "decide" in lean
    assert "set_option maxRecDepth" in lean
    tri = m.certify({"family": "self_ordered", "params": {"seq": "triangular", "bound": 6}})
    assert tri["verdict"].startswith("self-ordered") and tri["witness"] is None


def test_n_absorbing_family_computes_absorbing_number():
    m = _load()
    for mod, k in [(4, 2), (8, 3), (9, 2), (16, 4)]:
        c = m.certify({"family": "n_absorbing", "params": {"modulus": mod}})
        assert c["verdict"] == f"absorbingNumber(⊥ : ℤ/{mod}) = {k}"
        assert c["witness"]["absorbing_number"] == k
        assert f"isNAbs {k} ∧ ¬ isNAbs {k - 1}" in c["kernel"]["lean"]


def test_every_certificate_carries_apa_references():
    m = _load()
    for obj in m.registry():
        c = m.certify(obj)
        assert c["references"] and all("citation" in r and r["citation"] for r in c["references"])
    # the shared CFFG source is cited by every family
    assert all(any("Cahen" in r["citation"] for r in m.FAMILIES[f]["refs"]) for f in m.FAMILIES)


def test_emitted_lean_has_no_stray_sorry():
    m = _load()
    for obj in m.registry():
        k = m.certify(obj).get("kernel")
        if k and k.get("lean"):          # Tier-2 attestations carry a recipe, not Lean source
            for banned in ["sorry", "native_decide", "admit"]:
                assert banned not in k["lean"]


@pytest.mark.skipif(not os.environ.get("LEIBNIZ_RUN_LEAN"), reason="real-kernel test; set LEIBNIZ_RUN_LEAN=1")
def test_real_kernel_elaborates_all_emitted_certs():
    m = _load()
    from leibniz.backends.lean_repl import LeanReplBackend, available
    if not available():
        pytest.skip("Lean REPL image unavailable")
    from leibniz.backends.lean_axioms import axiom_report
    bk = LeanReplBackend(timeout_s=500)
    checked = 0
    try:
        for obj in m.registry():
            k = m.certify(obj).get("kernel")
            if not k or k.get("check") != "decide":     # Tier-2 attestations use lake build, not the REPL
                continue
            r = bk._run(k["lean"] + f"\n#print axioms {k['theorem']}\n", tuple(k["imports"]))
            # ADR 0090: the SHARED hardened analysis. This test used to open-code the same
            # `(r or {})` scan the script did, so it passed vacuously against a dead REPL -- the
            # exact failure it exists to catch. It agreed with the script by construction,
            # including when both were wrong.
            rep = axiom_report(r, k["theorem"])
            assert rep["ok"], (obj, k["theorem"], rep.get("errors"), rep["axioms"],
                               f"saw_axiom_report={rep['saw_axiom_report']}")
            checked += 1
    finally:
        bk.close()
    # An empty loop must be a FAILURE, not a pass. Without this, dropping every cert -- or every
    # cert silently failing to elaborate -- reads as green.
    assert checked == len([o for o in m.registry()
                           if (m.certify(o).get("kernel") or {}).get("check") == "decide"])
    assert checked >= 8, f"expected at least 8 decide-certs, checked {checked}"
