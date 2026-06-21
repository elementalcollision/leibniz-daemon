"""Shared vocabulary for the Leibniz daemon.

These types are deliberately small and total. Everything that can be a
mechanical check should be representable here without reference to an LLM, so
that the trust boundary (see ``leibniz.trust``) is enforceable by construction.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class TrustTier(Enum):
    """How much we trust the *decision* made at a given edge.

    The central rule of the system: a candidate may only be promulgated if every
    edge on its promotion path is MECHANICAL, with the single permitted exception
    of the Enuntiatio<->statement faithfulness edge, which may fall back through
    ADVERSARIAL to JUDGED. No proof is ever JUDGED.
    """

    MECHANICAL = "mechanical"   # kernel / decision procedure. Zero LLM trust.
    ADVERSARIAL = "adversarial"  # falsification search. LLM proposes, search refutes.
    JUDGED = "judged"           # irreducible LLM judgment. Minimized, logged, bounded.


class Role(Enum):
    """The only roles an LLM is permitted to occupy. All are *proposal* roles.

    An LLM never adjudicates. It surveys, conjectures, drafts a formal statement,
    or drafts a proof script -- and a mechanical gate decides whether the draft
    survives.
    """

    SURVEY = "survey"
    CONJECTURE = "conjecture"
    FORMALIZE = "formalize"       # draft a Lean statement from an Enuntiatio
    PROOF_DRAFT = "proof_draft"   # draft a tactic script for the kernel to check
    ANALOGY = "analogy"           # cross-domain stepping stones (Leonardo seam)


class ClaimType(Enum):
    """What *kind* of property an Enuntiatio asserts.

    This is the router that drives the faithfulness gate's mechanical fast path
    (``leibniz.gates.faithfulness``). Claims that assert a measurable property can
    have their Enuntiatio<->statement edge checked mechanically; only claims that
    resist operationalization fall back to a judge.
    """

    COMPLEXITY_BOUND = "complexity_bound"        # e.g. sorting is Omega(n log n)
    CORRECTNESS_OVER_DOMAIN = "correctness"      # forall x in D, P(f(x))
    OPTIMALITY = "optimality"                    # no algorithm does better than X
    INVARIANT = "invariant"                      # quantity preserved under op
    EXISTENCE = "existence"                      # a witness/construction exists
    STRUCTURAL = "structural"                    # algebraic / order-theoretic shape
    OPEN_FORM = "open_form"                      # resists operationalization -> judge


class Verdict(Enum):
    PASS = "pass"
    FAIL = "fail"
    DEFER = "defer"  # could not be decided cheaply; escalate, do not promote


class FinishReason(Enum):
    """Why a candidate left the active pipeline. Candidates are quarantined with a
    reason, never deleted (inherited from Newton's discipline)."""

    PROMULGATED = "promulgated"
    REFUTED = "refuted"                       # counterexample found
    TRIVIAL = "trivial"                       # closed by a decision procedure
    KNOWN = "known"                           # already in Mathlib / known corpus
    UNFAITHFUL = "unfaithful"                 # statement does not match Enuntiatio
    UNPROVEN = "unproven"                     # proof search exhausted budget
    MALFORMED = "malformed"                   # did not compile
    GAMED = "gamed"                           # statement satisfiable while claim false
    OVER_BUDGET = "over_budget"               # judged-faithfulness residual would exceed budget


@dataclass(frozen=True)
class ClaimSignature:
    """A machine-comparable fingerprint of what a Propositio actually establishes.

    Used by the novelty gate for dedup and by the faithfulness gate to tie the
    formal statement back to a checkable property. Kept structural, not textual,
    so 'restatements' of a known result collide.
    """

    claim_type: ClaimType
    subject: str                  # canonical name of the object, e.g. "comparison_sort"
    relation: str                 # canonical relation, e.g. "lower_bound"
    formal_hash: str              # hash of the normalized Lean statement
    properties: tuple[str, ...] = field(default_factory=tuple)


@dataclass
class EdgeEvidence:
    """Evidence and tier for a single trust edge, for the audited ledger."""

    edge: str
    tier: TrustTier
    verdict: Verdict
    detail: dict = field(default_factory=dict)
    cost_units: float = 0.0  # relative compute spent -- drives cheap-refutation-first
