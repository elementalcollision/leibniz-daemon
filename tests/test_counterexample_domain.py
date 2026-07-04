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


def test_three_tier1_families_registered():
    m = _load()
    assert set(m.FAMILIES) == {"monomial_normal", "self_ordered", "n_absorbing"}


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
    assert "≠ 0 := by decide" in cube["kernel"]["lean"]
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
    assert all(any("Cahen" in r["citation"] for r in m.FAMILIES[f][1]) for f in m.FAMILIES)


def test_emitted_lean_has_no_stray_sorry():
    m = _load()
    for obj in m.registry():
        k = m.certify(obj).get("kernel")
        if k:
            for banned in ["sorry", "native_decide", "admit"]:
                assert banned not in k["lean"]


@pytest.mark.skipif(not os.environ.get("LEIBNIZ_RUN_LEAN"), reason="real-kernel test; set LEIBNIZ_RUN_LEAN=1")
def test_real_kernel_elaborates_all_emitted_certs():
    m = _load()
    from leibniz.backends.lean_repl import LeanReplBackend, available
    if not available():
        pytest.skip("Lean REPL image unavailable")
    bk = LeanReplBackend(timeout_s=500)
    std = {"propext", "Classical.choice", "Quot.sound"}
    try:
        for obj in m.registry():
            k = m.certify(obj).get("kernel")
            if not k:
                continue
            r = bk._run(k["lean"] + f"\n#print axioms {k['theorem']}\n", tuple(k["imports"]))
            msgs = (r or {}).get("messages", []) or []
            assert not [x for x in msgs if x.get("severity") == "error"], (obj, msgs[:1])
            ax = set()
            for x in msgs:
                am = m._AX.search(x.get("data") or "")
                if am:
                    ax |= {a.strip() for a in am.group(1).split(",") if a.strip()}
            assert ax <= std, (obj, ax)
    finally:
        bk.close()
