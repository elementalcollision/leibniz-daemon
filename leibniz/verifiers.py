"""The judges. These are the only components allowed to render MECHANICAL verdicts.

Two verifiers, two jobs:

  LeanVerifier  -- the proof kernel. Compiles a statement (syntactic validity is
                   free) and checks a tactic script. ``kernel_verified`` is set
                   here and nowhere else. This is the characteristica's arbiter.

  SMTVerifier   -- Z3. Two uses: (1) cheap refutation -- throw a bounded
                   counterexample search at a conjecture *before* paying for
                   proof; (2) the gaming-witness search behind the faithfulness
                   gate. Neither use ever *promotes* a claim; both only *kill*.

Both are seams. The integration with LeanDojo / a real Z3 build is left as a
clearly-marked adapter so the architecture can be exercised end-to-end with
deterministic fakes first (see ``demo.py``).
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Optional, Protocol

from leibniz.propositio import Demonstratio, Expressio
from leibniz.types import EdgeEvidence, TrustTier, Verdict
from leibniz.trust import KERNEL_PRODUCER, PROOF_EDGE


def normalize_statement(theorem_src: str) -> str:
    """Whitespace/alpha-normalize a Lean statement for structural hashing.

    A real implementation normalizes via Lean's elaborator (bound-variable
    renaming, definitional unfolding to a canonical form). The hash is what the
    novelty gate compares, so two prose-different statements of the same theorem
    must collide here.
    """
    collapsed = " ".join(theorem_src.split())
    return hashlib.sha256(collapsed.encode()).hexdigest()[:16]


class LeanBackend(Protocol):
    """What a concrete Lean integration must provide (LeanDojo, Lean server, ...)."""

    def compile_statement(self, expr: Expressio) -> bool: ...
    def check_proof(self, expr: Expressio, proof_src: str) -> bool: ...
    def closed_by_decision_procedure(self, expr: Expressio) -> bool: ...


@dataclass
class LeanVerifier:
    backend: LeanBackend

    def validate_statement(self, expr: Expressio) -> bool:
        """Syntactic validity. Free: it compiles or it does not."""
        expr.compiles = self.backend.compile_statement(expr)
        if not expr.normalized_hash:
            expr.normalized_hash = normalize_statement(expr.theorem_src)
        return bool(expr.compiles)

    def discharge(self, expr: Expressio, demo: Demonstratio) -> EdgeEvidence:
        """Check the proof. This is the ONLY place kernel_verified is set.

        ADR 0097 — `kernel_verified` means KERNEL-decided, so the backend must also have read the
        proof's axiom footprint. It was previously set from `check_proof` alone, and `check_proof`
        bottomed out in "no error and no sorry"; the axiom footprint was a separate call each
        provider and gate made BY CONVENTION. Measured on the pinned Lean 4.31 image, that gap is
        not theoretical: a proof of Fermat's Last Theorem built on the Trail of Bits
        `String.Pos.Raw.extract` compiler/kernel disagreement came back from this method with
        `kernel_verified=True`, `MECHANICAL`, `PASS`, sealed `Q.E.D.` — while `axiom_closure`
        rejected the very same proof. The writer was permissive and only the gate was strict.

        A backend must now assert `enforces_axiom_closure`, i.e. that its `check_proof` returns
        True only for a clean `#print axioms` footprint. Absent that assertion this FAILS CLOSED:
        a future backend cannot be wired in and silently mint kernel verdicts, and the places that
        opt out are greppable by that one name rather than invisible.
        """
        ok = (bool(demo.proof_src)
              and bool(getattr(self.backend, "enforces_axiom_closure", False))
              and self.backend.check_proof(expr, demo.proof_src))
        # ADR 0097 — the INDEPENDENT footprint, and the last word on the stamp.
        #
        # `check_proof` reads `#print axioms` from the same file the proof lives in, and five
        # rounds of adversarial review showed that file is not a trustworthy place to ask: a proof
        # can print a report-shaped line, or redefine the `#print axioms` elaborator outright
        # (`elab_rules : command | `(#print axioms $i:ident) => ...`), which defeats even an
        # unpredictable probe name because it matches `$i:ident`. Every one of those ended in
        # `kernel_verified=True`. So a backend that CAN answer without elaborating proposer syntax
        # must do so here, and its answer binds. A missing or unreadable answer is a REFUSAL:
        # `independent_axiom_footprint` returns None when the reporter is unavailable, and None is
        # not a pass. Costs ~5 s, paid once per stamp rather than once per candidate.
        if ok and getattr(self.backend, "mint_requires_independent_check", False):
            probe = getattr(self.backend, "independent_axiom_footprint", None)
            report = probe(expr, demo.proof_src) if callable(probe) else None
            ok = bool(report and report.get("ok"))
        demo.kernel_verified = ok
        demo.seal()
        return EdgeEvidence(
            edge=PROOF_EDGE,
            tier=TrustTier.MECHANICAL,
            verdict=Verdict.PASS if ok else Verdict.FAIL,
            detail={"obligation": demo.proof_obligation, "qed": demo.qed},
            cost_units=10.0,  # proof search is the expensive edge
            producer=KERNEL_PRODUCER,  # ADR 0013: kernel provenance
        )

    def is_trivial(self, expr: Expressio) -> bool:
        """Non-triviality, mechanized: a statement an automated tactic closes on
        its own is vacuous (the `aesop` test from LeanConjecturer)."""
        return self.backend.closed_by_decision_procedure(expr)


class SMTBackend(Protocol):
    def find_counterexample(self, claim: str, bound: int) -> Optional[dict]: ...
    def find_gaming_witness(
        self, statement: str, negated_claim: str, bound: int
    ) -> Optional[dict]: ...


@dataclass
class SMTVerifier:
    backend: SMTBackend

    def cheap_refute(self, falsifiable_claim: str, bound: int = 64) -> EdgeEvidence:
        """Bounded counterexample search. Cheap; runs before proof. Only kills."""
        cx = self.backend.find_counterexample(falsifiable_claim, bound)
        return EdgeEvidence(
            edge="cheap_refutation",
            tier=TrustTier.MECHANICAL,
            # PASS here means "survived refutation", not "proven".
            verdict=Verdict.FAIL if cx is not None else Verdict.PASS,
            detail={"counterexample": cx},
            cost_units=1.0,
        )
