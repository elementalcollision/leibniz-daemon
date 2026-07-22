"""ADR 0070 — the deterministic LAW generator + DEMONSTRATE fast-path for factorial/gcd claims.

Mirrors ``power_mod_prover`` (ADR 0065) for the named-function fragment: ``factgcd_law`` renders the
canonical ℤ-box LAW ``∀ n, 0 ≤ n → claim_domain → claim_property`` for a classified factorial/gcd
claim and emits the kernel-validated two-regime/period-split proof; ``FactGcdDemonstrate`` proves it
and promotes on the single kernel verification — gated on a ``factgcd/kernel`` faithfulness PASS edge
(the statement-binding backend for THIS fragment), with the same A1/A2/A4 obligations as the residue
fast-path. Fail-closed: constructed only by ``assembly.maybe_wrap_factgcd`` (operator opt-in).
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, replace
from typing import Optional

from leibniz.backends.lean_axioms import axiom_closure
from leibniz.gates.factgcd_decided import classify_factgcd, factgcd_proof
from leibniz.gates.lean_decided import IMPORTS
from leibniz.dsl_to_lean import RenderError, free_vars
from leibniz.propositio import Demonstratio
from leibniz.providers.power_mod_prover import law_statement
from leibniz.trust import FAITHFULNESS_EDGE
from leibniz.types import EdgeEvidence, Verdict
from leibniz.verifiers import normalize_statement

FACTGCD_PRODUCER = "factgcd/kernel"


def factgcd_law(name: str, claim_domain: str, claim_property: str) -> Optional[tuple[str, str]]:
    """``(theorem_src, proof_src)`` for the canonical law of a factorial/gcd claim, or None (abstain)
    when the claim is outside the fragment. Total-or-abstain; never raises. Soundness is not this
    function's responsibility: the Lean kernel re-verifies whatever it emits — a wrong or malformed
    proof fails to elaborate → not kernel-verified → discarded."""
    try:
        if not (claim_domain and claim_property):
            return None
        skel = classify_factgcd(claim_property)
        if skel is None:
            return None
        vs = free_vars(claim_domain, claim_property)
        if vs != [skel.var]:
            return None                                  # single variable: the function's argument
        theorem_src = f"theorem {name} : {law_statement(claim_domain, claim_property, vs)}"
        return theorem_src, factgcd_proof(skel, n_domain=1)
    except RenderError:
        return None


def _law_name(claim_domain: str, claim_property: str) -> str:
    h = hashlib.sha256(f"{claim_domain}␟{claim_property}".encode()).hexdigest()[:12]
    return f"factgcd_law_{h}"


@dataclass
class FactGcdDemonstrate:
    """DEMONSTRATE fast-path (decision procedure, promote-on-one) for factorial/gcd claims — the
    exact ``ResidueDemonstrate`` design (ADR 0058; see its docstring for the A1/A2/A4 argument), with
    the fragment classifier, LAW generator and gating producer swapped for the ADR 0070 ones. The
    promoted ``theorem_src`` is re-rendered HERE from the DSL contract the ``factgcd/kernel``
    faithfulness backend byte-bound; ``LeanVerifier.discharge`` remains the sole ``kernel_verified``
    writer; a promotion-time ``axiom_closure`` rejects ``sorryAx``/``native_decide``."""

    inner: object
    lean: object
    obligation: str = "claim"

    def run(self, prop):
        if self._fastpath(prop):
            return prop
        return self.inner.run(prop)

    def _fastpath(self, prop) -> bool:
        try:
            return self._promote(prop)
        except Exception:
            return False       # any non-kernel surprise → fall through to the ensemble, never crash

    def _promote(self, prop) -> bool:
        en, expr = prop.enuntiatio, getattr(prop, "expressio", None)
        if expr is None or not (en.claim_domain and en.claim_property):
            return False
        # A2 (statement binding): promote-on-one ONLY when THIS fragment's statement-binding backend
        # certified faithfulness (it byte-binds the canonical statement and DEFERs vacuous domains).
        if not any(e.edge == FAITHFULNESS_EDGE and e.verdict is Verdict.PASS
                   and e.producer == FACTGCD_PRODUCER for e in prop.edges):
            return False
        gen = factgcd_law(_law_name(en.claim_domain, en.claim_property), en.claim_domain, en.claim_property)
        if gen is None:
            return False
        theorem_src, proof = gen
        law_expr = replace(expr, theorem_src=theorem_src, imports=IMPORTS,
                           established_domain=en.claim_domain,
                           normalized_hash=normalize_statement(theorem_src))
        demo = Demonstratio(proof_obligation=self.obligation, proof_src=proof)
        ev = self.lean.discharge(law_expr, demo)          # sole kernel_verified writer
        if not (demo.kernel_verified and ev.verdict is Verdict.PASS):
            return False
        backend = getattr(self.lean, "backend", None)
        if backend is None or not axiom_closure(backend, theorem_src, proof, IMPORTS).get("ok"):
            return False
        if getattr(prop, "signature", None) is not None:
            prop.signature = replace(prop.signature, formal_hash=law_expr.normalized_hash)
        prop.expressio = law_expr
        prop.demonstratio = demo
        prop.record(EdgeEvidence(
            edge=ev.edge, tier=ev.tier, verdict=ev.verdict,
            detail={**ev.detail, "decision_procedure": "factgcd-two-regime", "consensus": 1},
            cost_units=ev.cost_units, producer=ev.producer,
        ))
        return True
