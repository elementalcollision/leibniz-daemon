"""Guard the independent verification of Mafi–Naderi (2021), arXiv:2112.02921 (scripts/verify_mafi_naderi.py):
closure(M_{3,t}) = the Veronese cap-sum ideal (Thm 1.6) and its embedded prime (x,y,z) (Cor 1.7). Exact checks
are CI-safe; the axiom-clean `decide` kernel leg is REPL-gated. Tier audit; no trust surface touched."""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parent.parent


def _load(name, rel):
    spec = importlib.util.spec_from_file_location(name, _ROOT / rel)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _v():
    return _load("verify_mn", "scripts/verify_mafi_naderi.py")


def test_closure_equals_veronese_and_capsum():
    v = _v()
    res = v.verify(v._instr())
    assert res["all_ok"] is True
    for r in res["rows"]:
        assert r["closure_eq_veronese"] is True          # Theorem 1.6
        assert r["capsum_eq_closure"] is True             # cap-sum predicate == true integral closure


def test_embedded_prime_gained_by_closure():
    v = _v()
    res = {r["t"]: r for r in v.verify(v._instr())["rows"]}
    # Corollary 1.7: closure has embedded prime (x,y,z) for t>=2; M itself never does (unmixed).
    assert res[1]["closure_embedded_witness"] is None     # honest: t=1 closure has no embedded prime
    assert res[2]["closure_embedded_witness"] == [1, 1, 1]  # xyz for t=2
    assert res[3]["closure_embedded_witness"] == [1, 2, 2]
    for t in (1, 2, 3, 4):
        assert res[t]["M_embedded_witness"] is None       # M_{3,t} is unmixed


def test_witnesses_re_derived_independently():
    # For t=2: xyz=(1,1,1) ∉ closure (cap-sum 3<4) but each variable-multiple is in (cap-sum 4>=4).
    cs = lambda u, t: min(u[0], t) + min(u[1], t) + min(u[2], t)  # noqa: E731
    assert cs((1, 1, 1), 2) < 4
    for e in [(2, 1, 1), (1, 2, 1), (1, 1, 2)]:
        assert cs(e, 2) >= 4


def test_certificate_wellformed_and_clean():
    v = _v()
    src, names = v.build_certificate(v.verify(v._instr()))
    assert len(names) == 6
    for thm in ["M_subsetneq_closure", "closure_embedded_prime", "M_no_embedded_prime"]:
        assert thm in src
    assert "arXiv:2112.02921" in src and src.count(":= by decide") == 6
    for banned in ["sorry", "native_decide", "admit"]:
        assert banned not in src


@pytest.mark.skipif(not os.environ.get("LEIBNIZ_RUN_LEAN"), reason="real-kernel test; set LEIBNIZ_RUN_LEAN=1")
def test_real_kernel_decides_all_clean_axioms():
    v = _v()
    from leibniz.backends.lean_repl import LeanReplBackend, available
    if not available():
        pytest.skip("Lean REPL image unavailable")
    src, names = v.build_certificate(v.verify(v._instr()))
    run_src = "".join(ln for ln in src.splitlines(keepends=True) if not ln.startswith("import "))
    run_src += "\n" + "\n".join(f"#print axioms {n}" for n in names) + "\n"
    bk = LeanReplBackend(timeout_s=400)
    try:
        r = bk._run(run_src, v.IMPORTS)
    finally:
        bk.close()
    msgs = (r or {}).get("messages", []) or []
    assert not [x for x in msgs if x.get("severity") == "error"]
    axiom_lines = [x.get("data", "") for x in msgs if "axiom" in (x.get("data") or "")]
    assert len(axiom_lines) == 6
    std = {"propext", "Classical.choice", "Quot.sound"}
    for ln in axiom_lines:
        if "does not depend on any axioms" in ln:
            continue
        toks = [t.strip() for t in ln.split("[", 1)[-1].rstrip("]").split(",") if t.strip()]
        assert all(t in std for t in toks), ln
