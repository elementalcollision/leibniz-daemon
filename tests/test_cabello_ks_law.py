"""ADR 0050 Phase 2 — CI-safe guards for the Kochen–Specker amplified-law promotion.

The discharge routes a single declaration through ``_join_proof``, which cuts at the FIRST ``:=``.
The promoted theorem needs 12 helper definitions, so its ``theorem_src`` MUST be ``:=``-free
(nested-λ + ``@Nat.rec``, no ``let``): if an edit reintroduces a ``let … :=`` the join would silently
truncate the statement and the discharge would check the wrong (or an ill-formed) theorem. These
tests pin that invariant and the amplified-law payload shape without Docker. An opt-in real-kernel
anchor (``LEIBNIZ_LEAN_E2E=1``) does the actual discharge + axiom check.
"""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("cabks_law", _ROOT / "scripts" / "export_cabello_ks_law.py")
cab = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cab)

from leibniz.backends.lean_repl import _join_proof  # noqa: E402
from leibniz.calculemus_site import law_payload  # noqa: E402
from leibniz.propositio import Expressio  # noqa: E402


def test_theorem_src_is_join_safe_single_declaration():
    src = cab.build_theorem_src()
    # the invariant that makes the existing discharge work: no `:=` and no `let` in the statement
    assert ":=" not in src, "theorem_src has a `:=` — _join_proof would truncate the statement"
    assert "let " not in src, "a `let` binding would carry a `:=`"
    assert src.startswith("set_option maxHeartbeats 0 in\nset_option maxRecDepth 4000000 in\n")
    assert "theorem cabello_uncolorable :" in src
    assert src.rstrip().endswith("= false")
    assert "@Nat.rec" in src, "the recursive solver must use the positional recursor (reduces under decide)"


def test_join_appends_proof_without_truncating():
    src = cab.build_theorem_src()
    joined = _join_proof(src, "by decide")
    # because there is no `:=` in the header, the join is exactly header + the appended proof
    assert joined == f"{src} := by decide"
    assert joined.count("theorem cabello_uncolorable") == 1


def test_helper_bodies_are_all_colon_equal_free():
    # every generated def body (and the inlined solver) must be `:=`-free
    for _name, _ty, body in cab._DEFS:
        assert ":=" not in body
    assert ":=" not in cab._SOLVE_AT_BASES


def test_amplified_law_payload_shape():
    prop = cab.build_propositio()                        # no discharge here → kernel_verified stays False
    payload = law_payload(prop, specimen=False, tier="kernel-decided", origination="amplified",
                          references=cab._REFERENCES)
    assert payload["id"] == "cabello_uncolorable"
    assert payload["claim_type"] == "invariant"
    assert payload["domain"] == "quantum_contextuality"
    assert payload["tier"] == "kernel-decided" and payload["origination"] == "amplified"
    assert payload["specimen"] is False
    assert len(payload["references"]) == 2 and all("citation" in r for r in payload["references"])
    assert payload["proof_src"] == "by decide"
    # the Expressio round-trips as a valid single declaration
    assert Expressio(theorem_src=payload["theorem_src"]).theorem_src == prop.expressio.theorem_src


def test_amplified_requires_a_citation():
    # ADR 0050: an `amplified` law asserts a re-decision of published work → it MUST cite its source.
    assert cab._REFERENCES and all(r.get("citation") for r in cab._REFERENCES)


@pytest.mark.skipif(not os.environ.get("LEIBNIZ_LEAN_E2E"), reason="set LEIBNIZ_LEAN_E2E=1 for the Lean e2e")
def test_real_kernel_discharge_is_qed_and_propext_clean():  # pragma: no cover
    from leibniz.backends.lean_axioms import axiom_closure
    from leibniz.backends.lean_repl import LeanReplBackend, available
    from leibniz.verifiers import LeanVerifier
    if not available():
        pytest.skip("Lean image unavailable")
    prop = cab.build_propositio()
    be = LeanReplBackend(timeout_s=300)
    try:
        LeanVerifier(be).discharge(prop.expressio, prop.demonstratio)
        ax = axiom_closure(be, prop.expressio.theorem_src, prop.demonstratio.proof_src,
                           prop.expressio.imports, allowed=frozenset({"propext"}))
    finally:
        be.close()
    assert prop.demonstratio.kernel_verified is True
    assert prop.demonstratio.qed == "Q.E.D."
    assert ax["ok"] and set(ax["axioms"]) <= {"propext"}
