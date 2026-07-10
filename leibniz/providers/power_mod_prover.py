"""ADR 0065 — the deterministic LAW generator + DEMONSTRATE fast-path for power-mod claims.

Mirrors `residue_prover` (ADR 0058) for the symbolic-exponent fragment: `power_law` renders the
canonical ℤ-box LAW `∀ n, 0 ≤ n → claim_domain → claim_property` for a classified `base**n % m`
claim and emits the kernel-validated order-split proof; `PowerModDemonstrate` proves it and promotes
on the single kernel verification — gated on a `power_mod/kernel` faithfulness PASS edge (the
statement-binding backend for THIS fragment), with the same A1/A2/A4 obligations as the residue
fast-path. Fail-closed: constructed only by `assembly.maybe_wrap_power_mod` (operator opt-in).
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, replace
from typing import Optional

from leibniz.backends.lean_axioms import axiom_closure
from leibniz.gates.lean_decided import IMPORTS
from leibniz.gates.power_mod_decided import classify_power, power_proof
from leibniz.dsl_to_lean import RenderError, _binder, _nonneg, free_vars, render_pred
from leibniz.propositio import Demonstratio
from leibniz.trust import FAITHFULNESS_EDGE
from leibniz.types import EdgeEvidence, Verdict
from leibniz.verifiers import normalize_statement

POWER_MOD_PRODUCER = "power_mod/kernel"


def law_statement(claim_domain: str, claim_property: str, vs: list[str]) -> str:
    """The canonical ℤ-box LAW proposition: `∀ vars, 0 ≤ vars → claim_domain → claim_property`."""
    cd, cp = render_pred(claim_domain), render_pred(claim_property)
    return f"{_binder('∀', vs)} {_nonneg(vs, '→')}{cd} → {cp}"


def power_law(name: str, claim_domain: str, claim_property: str) -> Optional[tuple[str, str]]:
    """`(theorem_src, proof_src)` for the canonical law of a power-mod claim, or None (abstain) when
    the claim is outside the fragment. Total-or-abstain; never raises. Soundness is not this
    function's responsibility: the Lean kernel re-verifies whatever it emits — a wrong or malformed
    proof fails to elaborate → not kernel-verified → discarded."""
    try:
        if not (claim_domain and claim_property):
            return None
        skel = classify_power(claim_property)
        if skel is None:
            return None
        vs = free_vars(claim_domain, claim_property)
        if vs != [skel.var]:
            return None                                  # single variable: the exponent, nothing else
        theorem_src = f"theorem {name} : {law_statement(claim_domain, claim_property, vs)}"
        return theorem_src, power_proof(skel, n_domain=1)
    except RenderError:
        return None


def _law_name(claim_domain: str, claim_property: str) -> str:
    h = hashlib.sha256(f"{claim_domain}␟{claim_property}".encode()).hexdigest()[:12]
    return f"power_law_{h}"


@dataclass
class PowerModDemonstrate:
    """DEMONSTRATE fast-path (decision procedure, promote-on-one) for power-mod claims — the exact
    `ResidueDemonstrate` design (ADR 0058; see its docstring for the A1/A2/A4 argument), with the
    fragment classifier, LAW generator and gating producer swapped for the ADR 0065 ones. The
    promoted `theorem_src` is re-rendered HERE from the DSL contract the `power_mod/kernel`
    faithfulness backend byte-bound; `LeanVerifier.discharge` remains the sole `kernel_verified`
    writer; a promotion-time `axiom_closure` rejects `sorryAx`/`native_decide`."""

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
                   and e.producer == POWER_MOD_PRODUCER for e in prop.edges):
            return False
        gen = power_law(_law_name(en.claim_domain, en.claim_property), en.claim_domain, en.claim_property)
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
            detail={**ev.detail, "decision_procedure": "power-mod-order-split", "consensus": 1},
            cost_units=ev.cost_units, producer=ev.producer,
        ))
        return True
