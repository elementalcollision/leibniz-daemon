"""The Propositio -- the unit of work and the unit of record.

Inherited wholesale from Newton's ledger triad, with one deliberate inversion:
the Demonstratio's ``proof_obligation`` is *active* here. In Newton it was
hardcoded ``"not_applicable"``; in Leibniz it carries a Lean theorem and is
discharged by the kernel. That single flip is the whole difference between the
two daemons.

Lifecycle of a Propositio:

    Conjecture -> Enuntiatio (human-readable claim, + ClaimType)
               -> Expressio  (formal statement in the characteristica, i.e. Lean)
               -> Demonstratio (proof obligation + kernel-checked proof)
               -> promulgated | quarantined(FinishReason)
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Optional

from leibniz.types import (
    ClaimSignature,
    ClaimType,
    EdgeEvidence,
    FinishReason,
)


@dataclass
class Enuntiatio:
    """The claim, stated for a human reader. The thing that ends up in the ledger
    and that a faithfulness gate must hold the formal statement accountable to."""

    statement: str
    claim_type: ClaimType
    falsifiable_claim: str           # the explicit refutation condition (Popper)
    domain: str = "analysis_of_algorithms"
    # R2 structured faithfulness contract (ADR 0004): machine-checkable predicates
    # over input `n`. The Enuntiatio asserts: for all n with claim_domain(n),
    # claim_property(n). Left None for prose-only / OPEN_FORM claims.
    claim_domain: Optional[str] = None
    claim_property: Optional[str] = None


@dataclass
class Expressio:
    """The formal statement in the characteristica universalis (Lean 4).

    ``theorem_src`` is the statement *only* -- the proof is the Demonstratio's job.
    ``normalized_hash`` lets the novelty gate compare structure, not prose.
    """

    theorem_src: str                 # `theorem foo (...) : ... := by ...` header
    imports: tuple[str, ...] = ("Mathlib",)
    normalized_hash: str = ""
    compiles: Optional[bool] = None  # syntactic validity is free: Lean says yes/no
    # R2 (ADR 0004): the domain over `n` the formal statement actually establishes
    # the claimed property on. Faithful iff it covers the Enuntiatio's claim_domain.
    established_domain: Optional[str] = None
    # ADR 0027: PROVER-CONTEXT-ONLY hints — independently-proven helper lemmas offered to
    # the prover (as copy-pasteable `have` blocks) when re-proving a hard goal. This is
    # NEVER placed in the Lean source the kernel checks: the kernel only ever sees one
    # self-contained declaration (`theorem_src := proof`), so a smuggled top-level command
    # would be a parse error inside the proof — there is no separate-declaration surface to
    # poison. Empty for ordinary proofs.
    proof_hints: str = ""


@dataclass
class Demonstratio:
    """The proof obligation and its discharge.

    In Newton: ``proof_obligation == "not_applicable"`` and the gate ran a test.
    In Leibniz: ``proof_obligation`` names what must be proven and ``proof_src`` is
    a tactic script the Lean kernel checks. ``kernel_verified`` is the only field
    that may gate promotion, and only the kernel may set it True.
    """

    proof_obligation: str            # e.g. "comparison_sort_lower_bound"
    proof_src: Optional[str] = None  # tactic script (LLM-drafted, kernel-checked)
    kernel_verified: bool = False    # set ONLY by leibniz.verifiers.lean
    qed: str = "Q.E.I."              # "Q.E.D." iff kernel_verified, see promulgate

    def seal(self) -> None:
        """Stamp the certificate. Q.E.D. is earned by the kernel, never by prose."""
        self.qed = "Q.E.D." if self.kernel_verified else "Q.E.I."


@dataclass
class Propositio:
    enuntiatio: Enuntiatio
    expressio: Optional[Expressio] = None
    demonstratio: Optional[Demonstratio] = None

    pid: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    born: float = field(default_factory=time.time)
    parents: tuple[str, ...] = ()    # lineage for KFM recombination + provenance

    signature: Optional[ClaimSignature] = None
    edges: list[EdgeEvidence] = field(default_factory=list)

    promulgated: bool = False
    finish_reason: Optional[FinishReason] = None

    # Quality-diversity coordinates KFM uses to place this in the archive.
    behavior_descriptor: tuple[float, ...] = ()

    # ADR 0034 Stage 2: which kind of seed produced this candidate (mined | weaken | kfm |
    # survey). Recorded so the §5 kill condition can measure the genuine-novelty fraction of
    # MINED-origin promulgations specifically. Proposal-side provenance; gates nothing.
    seed_origin: Optional[str] = None

    def record(self, ev: EdgeEvidence) -> None:
        self.edges.append(ev)

    def quarantine(self, reason: FinishReason) -> None:
        """Leave the active pipeline but stay in the record. Never deleted."""
        self.finish_reason = reason
