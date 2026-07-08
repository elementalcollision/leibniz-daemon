"""ADR 0050 Phase 2 + ADR 0062 — CI-safe guards for the Kochen–Specker amplified-law promotion.

The law's legible top-level definitions ride in the Expressio PREAMBLE (ADR 0062), so the
``theorem_src`` is a clean one-liner. These tests pin (a) the preamble/statement shape, (b) that the
discovery path is byte-identical when ``preamble == ""`` (the change is additive), and (c) the
amplified-law payload. An opt-in real-kernel anchor (``LEIBNIZ_LEAN_E2E=1``) does the actual discharge
+ axiom check over preamble ⊕ theorem_src.
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


def test_theorem_src_is_a_clean_one_liner():
    src = cab.build_theorem_src()
    assert src == "theorem cabello_uncolorable : solve rays bases [] [] 30 = false"
    assert ":=" not in src            # no proof/defs in the statement → _join_proof appends the proof intact
    assert "\n" not in src            # legible single line, unlike the old inlined blob


def test_preamble_defines_every_symbol_the_statement_uses():
    pre = cab._PREAMBLE
    for sym in ("def solve", "def rays", "def bases", "def emul", "def orth", "def pickable", "abbrev Eis"):
        assert sym in pre, f"preamble missing {sym!r}"
    # the statement references solve / rays / bases — all defined in the preamble
    assert "solve rays bases" in cab.build_theorem_src()
    assert pre.startswith("set_option maxHeartbeats 0")


def test_discovery_path_is_byte_identical_when_no_preamble():
    # ADR 0062 is additive: with the default empty preamble, _join_proof is unchanged from before.
    t, p = "theorem foo : 0 < 1", "by decide"
    assert _join_proof(t, p) == _join_proof(t, p, "") == "theorem foo : 0 < 1 := by decide"
    assert Expressio(theorem_src=t).preamble == ""      # the discovery-path default


def test_preamble_is_prepended_only_when_present():
    joined = _join_proof("theorem foo : 0 < 1", "by decide", "def x := 1")
    assert joined == "def x := 1\ntheorem foo : 0 < 1 := by decide"


def test_amplified_law_payload_carries_preamble_and_clean_statement():
    prop = cab.build_propositio()                        # no discharge here → kernel_verified stays False
    payload = law_payload(prop, specimen=False, tier="kernel-decided", origination="amplified",
                          references=cab._REFERENCES)
    assert payload["id"] == "cabello_uncolorable"
    assert payload["claim_type"] == "invariant" and payload["domain"] == "quantum_contextuality"
    assert payload["tier"] == "kernel-decided" and payload["origination"] == "amplified"
    assert payload["theorem_src"] == "theorem cabello_uncolorable : solve rays bases [] [] 30 = false"
    assert payload["preamble"] == cab._PREAMBLE and "def solve" in payload["preamble"]
    assert payload["proof_src"] == "by decide"
    assert len(payload["references"]) == 2 and all("citation" in r for r in payload["references"])


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
                           prop.expressio.imports, allowed=frozenset({"propext"}),
                           preamble=prop.expressio.preamble)
    finally:
        be.close()
    assert prop.demonstratio.kernel_verified is True
    assert prop.demonstratio.qed == "Q.E.D."
    assert ax["ok"] and set(ax["axioms"]) <= {"propext"}
