"""ADR 0059 (min/max half), amendment B.1 — the min/max identity DEMONSTRATE fast-path.

The prover-reach half for the second decision procedure. After `minmax_decided` (the order-split
faithfulness backend) certifies a min/max identity, the LLM ensemble still cannot prove it; the **same
order-split that certifies faithfulness proves the theorem**. Structurally identical to
`residue_prover.ResidueDemonstrate` (the modular fast-path) — a **separate** path, gated on a
**`minmax_identity/kernel`** faithfulness edge and re-rendering the LAW from the DSL — so the ADR 0058
A2 statement-binding hole the review flagged for a naive min/max fast-path cannot open:

- **A1 (masquerade):** none possible — the decision procedure is not a registrable prover; it is this
  hardcoded path, reached only when the operator activates it and only for claims `minmax_law` accepts.
- **A2 (statement binding):** the promulgated `theorem_src` is **re-rendered here** from the DSL contract
  the faithfulness gate vetted (never the autoformalizer's free text), and the fast-path promotes ONLY a
  claim carrying a `minmax_identity/kernel` faithfulness PASS edge — the sole backend that byte-binds the
  canonical statement for this fragment (B.2). `normalized_hash`/`established_domain` are refreshed so the
  ledger + self-dedup key the published statement.
- **A4 (axiom footprint):** a promotion-time `axiom_closure` rejects `sorryAx`/`Lean.ofReduceBool`; the
  order-split proof uses only `rcases`/`simp`/`ring`.
- **Kernel-gated:** `LeanVerifier.discharge` remains the sole `kernel_verified` writer; a generator bug ⇒
  the kernel rejects ⇒ fall-through, never an unsound law. `validate_path`/`is_promotable`/`test_invariants`
  are byte-identical.

Fail-closed: nothing constructs this unless the operator opts in (`assembly.maybe_wrap_minmax`).
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, replace
from typing import Optional

from leibniz.backends.lean_axioms import axiom_closure
from leibniz.dsl_to_lean import RenderError, free_vars
from leibniz.gates.lean_decided import MAX_VARS, MIN_VARS
from leibniz.gates.minmax_decided import classify_identity, identity_proof
from leibniz.propositio import Demonstratio
from leibniz.providers.residue_prover import law_statement   # the DSL law renderer (classifier-agnostic)
from leibniz.trust import FAITHFULNESS_EDGE
from leibniz.types import EdgeEvidence, Verdict
from leibniz.verifiers import normalize_statement

IMPORTS = ("Mathlib.Tactic",)   # max_eq_*/min_eq_*, le_total, ring resolve here
# The producer stamped by the STATEMENT-BINDING min/max faithfulness backend. The fast-path promotes on
# one kernel verification ONLY for a claim this backend certified — it alone byte-binds the canonical
# statement to the identity (obligation 5 / B.2).
MINMAX_DECIDED_PRODUCER = "minmax_identity/kernel"


def minmax_law(name: str, claim_domain: str, claim_property: str) -> Optional[tuple[str, str]]:
    """Deterministic generator: `(theorem_src, proof_src)` for the canonical ℤ-box LAW of a min/max
    identity, or None (abstain) when the claim is outside the fragment (reusing
    `minmax_decided.classify_identity`). Total-or-abstain; never raises. Soundness is not this
    function's responsibility — the kernel re-verifies whatever it emits against the actual
    `theorem_src`; a wrong proof fails to elaborate → not kernel-verified → discarded."""
    try:
        if not (claim_domain and claim_property):
            return None
        skel = classify_identity(claim_property)
        if skel is None:
            return None
        vs = free_vars(claim_domain, claim_property)
        if not (MIN_VARS <= len(vs) <= MAX_VARS):
            return None
        theorem_src = f"theorem {name} : {law_statement(claim_domain, claim_property, vs)}"
        return theorem_src, identity_proof(skel, vs, n_domain=1)
    except RenderError:
        return None


def _law_name(claim_domain: str, claim_property: str) -> str:
    """A stable, valid Lean identifier for the identity law, derived from its contract."""
    h = hashlib.sha256(f"{claim_domain}␟{claim_property}".encode()).hexdigest()[:12]
    return f"minmax_law_{h}"


@dataclass
class MinMaxDemonstrate:
    """DEMONSTRATE fast-path for min/max identities (ADR 0059 B.1) — the more conservative form of ADR
    0058 promotability: a single, fixed, operator-activated code path, no pluggable prover to masquerade
    as. Proves the gate-rendered canonical identity LAW (`minmax_law`, kernel-validated) and, on the
    **single** kernel verification, records the proof edge (promote-on-one). Everything else — non-identity
    claims, or a claim whose generated proof the kernel rejects — **falls through to `inner`** (the
    unchanged N+1 consensus ensemble). No change to `consensus.py`/`trust.py`/`validate_path`/
    `test_invariants` (all byte-identical)."""

    inner: object                 # the wrapped DEMONSTRATE stage (Consensus/Repairing/Decomposing)
    lean: object                  # the LeanVerifier (discharge = sole kernel_verified writer)
    obligation: str = "claim"

    def run(self, prop):
        if self._fastpath(prop):
            return prop
        return self.inner.run(prop)

    def _fastpath(self, prop) -> bool:
        try:
            return self._promote(prop)
        except Exception:
            return False   # any non-kernel surprise → fall through to the ensemble, never crash DEMONSTRATE

    def _promote(self, prop) -> bool:
        en, expr = prop.enuntiatio, getattr(prop, "expressio", None)
        if expr is None or not (en.claim_domain and en.claim_property):
            return False
        # A2: promote-on-one ONLY for a claim the STATEMENT-BINDING min/max backend certified. If
        # faithfulness passed some OTHER way (a probe, the gaming spine, the judge), the canonical LAW was
        # never vetted as a statement → fall through, no promote-on-one.
        if not any(e.edge == FAITHFULNESS_EDGE and e.verdict is Verdict.PASS
                   and e.producer == MINMAX_DECIDED_PRODUCER for e in prop.edges):
            return False
        gen = minmax_law(_law_name(en.claim_domain, en.claim_property), en.claim_domain, en.claim_property)
        if gen is None:
            return False
        theorem_src, proof = gen
        # A2: prove and promulgate the gate-rendered canonical statement; refresh normalized_hash and
        # established_domain so the ledger + ADR-0052 self-dedup key the PUBLISHED statement.
        law_expr = replace(expr, theorem_src=theorem_src, imports=IMPORTS,
                           established_domain=en.claim_domain,
                           normalized_hash=normalize_statement(theorem_src))
        demo = Demonstratio(proof_obligation=self.obligation, proof_src=proof)
        ev = self.lean.discharge(law_expr, demo)              # sole kernel_verified writer
        if not (demo.kernel_verified and ev.verdict is Verdict.PASS):
            return False                                      # kernel rejected → fall to the ensemble
        # A4: clean axiom footprint (no native_decide / sorry). backend needed for `#print axioms`.
        backend = getattr(self.lean, "backend", None)
        if backend is None or not axiom_closure(backend, theorem_src, proof, IMPORTS).get("ok"):
            return False
        if getattr(prop, "signature", None) is not None:      # keep novelty/dedup identity in sync
            prop.signature = replace(prop.signature, formal_hash=law_expr.normalized_hash)
        prop.expressio = law_expr                             # promulgate the canonical statement
        prop.demonstratio = demo
        prop.record(EdgeEvidence(
            edge=ev.edge, tier=ev.tier, verdict=ev.verdict,   # the kernel's own verdict, never hardcoded
            detail={**ev.detail, "decision_procedure": "minmax-order-split", "consensus": 1},
            cost_units=ev.cost_units, producer=ev.producer,   # KERNEL_PRODUCER, preserved from discharge
        ))
        return True
