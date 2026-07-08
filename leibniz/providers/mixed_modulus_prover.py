"""ADR 0060 — the DEMONSTRATE fast-path for mixed-modulus (LCM/castHom) laws.

After `mixed_modulus_decided` certifies a mixed-modulus claim, the same LCM/castHom proof that certifies
faithfulness proves the theorem. Structurally identical to the residue / minmax / boolean fast-paths — a
separate path gated on a `mixed_modular/kernel` faithfulness edge and re-rendering the LAW from the DSL:

- **A1 (masquerade):** none — a fixed, operator-activated code path, no registrable prover.
- **A2 (statement binding):** the promulgated `theorem_src` is re-rendered here from the DSL contract the
  gate vetted; the fast-path promotes ONLY a claim carrying a `mixed_modular/kernel` faithfulness PASS edge.
- **A4 (axiom footprint):** a promotion-time `axiom_closure` rejects `sorryAx`/`Lean.ofReduceBool`.
- **Kernel-gated:** `LeanVerifier.discharge` is the sole `kernel_verified` writer; a generator bug ⇒ the
  kernel rejects ⇒ fall-through, never an unsound law. `validate_path`/`test_invariants` byte-identical.

Fail-closed: nothing constructs this unless the operator opts in (`assembly.maybe_wrap_mixed_modulus`).
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, replace
from typing import Optional

from leibniz.backends.lean_axioms import axiom_closure
from leibniz.dsl_to_lean import RenderError, free_vars
from leibniz.gates.lean_decided import MAX_RESIDUE_CELLS, MAX_VARS, MIN_VARS
from leibniz.gates.mixed_modulus_decided import classify_mixed, mixed_proof
from leibniz.propositio import Demonstratio
from leibniz.providers.residue_prover import law_statement    # the DSL law renderer (classifier-agnostic)
from leibniz.trust import FAITHFULNESS_EDGE
from leibniz.types import EdgeEvidence, Verdict
from leibniz.verifiers import normalize_statement

IMPORTS = ("Mathlib.Tactic",)
MIXED_DECIDED_PRODUCER = "mixed_modular/kernel"


def mixed_law(name: str, claim_domain: str, claim_property: str) -> Optional[tuple[str, str]]:
    """Deterministic generator: `(theorem_src, proof_src)` for the canonical ℤ-box LAW of a mixed-modulus
    claim, or None (abstain). Total-or-abstain; never raises. The kernel re-verifies whatever it emits."""
    try:
        if not (claim_domain and claim_property):
            return None
        skel = classify_mixed(claim_property)
        if skel is None:
            return None
        vs = free_vars(claim_domain, claim_property)
        if not (MIN_VARS <= len(vs) <= MAX_VARS) or skel.M ** len(vs) > MAX_RESIDUE_CELLS:
            return None
        theorem_src = f"theorem {name} : {law_statement(claim_domain, claim_property, vs)}"
        return theorem_src, mixed_proof(skel, vs, n_domain=1)
    except RenderError:
        return None


def _law_name(claim_domain: str, claim_property: str) -> str:
    h = hashlib.sha256(f"{claim_domain}␟{claim_property}".encode()).hexdigest()[:12]
    return f"mixed_law_{h}"


@dataclass
class MixedModulusDemonstrate:
    """DEMONSTRATE fast-path for mixed-modulus laws (ADR 0060). Proves the gate-rendered canonical LAW
    (`mixed_law`) and, on the single kernel verification, records the proof edge (promote-on-one);
    everything else falls through to `inner` (the N+1 ensemble). No change to `consensus.py`/`trust.py`/
    `validate_path`/`test_invariants`."""

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
            return False

    def _promote(self, prop) -> bool:
        en, expr = prop.enuntiatio, getattr(prop, "expressio", None)
        if expr is None or not (en.claim_domain and en.claim_property):
            return False
        if not any(e.edge == FAITHFULNESS_EDGE and e.verdict is Verdict.PASS
                   and e.producer == MIXED_DECIDED_PRODUCER for e in prop.edges):
            return False
        gen = mixed_law(_law_name(en.claim_domain, en.claim_property), en.claim_domain, en.claim_property)
        if gen is None:
            return False
        theorem_src, proof = gen
        law_expr = replace(expr, theorem_src=theorem_src, imports=IMPORTS,
                           established_domain=en.claim_domain,
                           normalized_hash=normalize_statement(theorem_src))
        demo = Demonstratio(proof_obligation=self.obligation, proof_src=proof)
        ev = self.lean.discharge(law_expr, demo)
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
            detail={**ev.detail, "decision_procedure": "mixed-modulus-lcm-casthom", "consensus": 1},
            cost_units=ev.cost_units, producer=ev.producer,
        ))
        return True
