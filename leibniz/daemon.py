"""Leibniz -- the daemon. Calculemus.

On a slow circadian cycle it surveys the frontier, conjectures, formalizes into
the characteristica (Lean), and -- where a claim survives cheap refutation, is
novel and non-trivial, and is faithful to its statement -- asks the kernel to
*calculate* whether it holds. What the kernel confirms is promulgated to the
Codex as a Propositio; everything else is quarantined with a reason and fed back
to KFM as a stepping stone.

The loop is deliberately thin. All judgment lives in the gates and the kernel;
the daemon only sequences work and enforces the promotion order. The trust
policy is checked at promotion, so no cycle can promulgate a law whose proof was
not kernel-checked.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from leibniz.adapters import RuntimeAdapter
from leibniz.budget import TrustBudget
from leibniz.cost import CostBudget
from leibniz.gates.verification import VerificationGate
from leibniz.pipeline import (
    Conjecture,
    Demonstrate,
    Derive,
    Formalize,
    Promulgate,
    Survey,
)
from leibniz.propositio import Propositio
from leibniz.selection import KFM, descriptor
from leibniz.types import FinishReason


@dataclass
class CycleReport:
    seeds: int = 0
    conjectured: int = 0
    reached_proof: int = 0
    promulgated: int = 0
    by_reason: dict[str, int] = field(default_factory=dict)

    def tally(self, reason: FinishReason) -> None:
        self.by_reason[reason.value] = self.by_reason.get(reason.value, 0) + 1


@dataclass
class Leibniz:
    runtime: RuntimeAdapter
    survey: Survey
    conjecture: Conjecture
    formalize: Formalize
    derive: Derive
    demonstrate: Demonstrate
    promulgate: Promulgate
    verification: VerificationGate
    kfm: KFM
    domain: str = "analysis_of_algorithms"
    # R2c: the judged-faithfulness budget (ADR 0001 §5). Optional — when absent the
    # daemon does not bound the residual (the fakes/demo run without it).
    budget: Optional[TrustBudget] = None
    # ADR 0011: coarse USD cost cap for multi-cycle autonomous runs. Optional.
    cost_budget: Optional[CostBudget] = None

    def circadian_cycle(self) -> CycleReport:
        report = CycleReport()
        seeds = self.survey.run(self.domain)
        report.seeds = len(seeds)
        self._run_seeds(seeds, report)
        return report

    def run_cycles(
        self,
        n: int,
        *,
        fresh_per_cycle: int = 2,
        recombine_k: int = 4,
        stagnation_limit: int = 2,
    ) -> list[CycleReport]:
        """Open-ended discovery (ADR 0009): turn N circadian cycles, re-seeding each
        cycle from the KFM archive — recombined curiosity-biased parents plus a few
        fresh SURVEY seeds. If archive coverage stops growing for `stagnation_limit`
        cycles, fall back to a fresh SURVEY to escape the rut."""
        reports: list[CycleReport] = []
        prev_coverage = -1
        stagnant = 0
        for i in range(n):
            if self.cost_budget is not None and self.cost_budget.exhausted():
                break  # ADR 0011: stop before starting a cycle that would exceed the cap
            fresh_only = i == 0 or stagnant >= stagnation_limit
            seeds = self._next_seeds(fresh_only, fresh_per_cycle, recombine_k)
            report = CycleReport()
            report.seeds = len(seeds)
            self._run_seeds(seeds, report)
            reports.append(report)
            if self.cost_budget is not None:
                # coarse estimate: CONJECTURE+FORMALIZE per candidate, plus the prover
                # ensemble per candidate that reached proof.
                self.cost_budget.record_calls(report.conjectured * 2 + report.reached_proof * 4)
            coverage = len(self.kfm.archive.cells)
            stagnant = 0 if coverage > prev_coverage else stagnant + 1
            prev_coverage = coverage
        return reports

    def _next_seeds(self, fresh_only: bool, fresh_per_cycle: int, recombine_k: int) -> list[str]:
        if fresh_only:
            return self.survey.run(self.domain)
        seeds = self.kfm.recombination_seeds(recombine_k) + self.survey.run(self.domain)[:fresh_per_cycle]
        return seeds or self.survey.run(self.domain)  # cold archive -> fresh survey

    def _run_seeds(self, seeds: list[str], report: CycleReport) -> None:
        for seed in seeds:
            prop = self.conjecture.run(seed)
            report.conjectured += 1

            survivor = self.formalize.run(prop)  # cheap gates run inside
            if survivor is None:
                self._settle(prop, report)
                continue

            survivor = self.derive.run(survivor)        # expensive: proof draft
            survivor = self.demonstrate.run(survivor)   # kernel check
            report.reached_proof += 1

            promotable = self.verification.is_promotable(survivor)
            # R2c: even a promotable candidate is refused if its faithfulness edge
            # is JUDGED and admitting it would breach the trust budget.
            if promotable and self.budget is not None:
                if not self.budget.try_admit(survivor.edges):
                    survivor.quarantine(FinishReason.OVER_BUDGET)
                    promotable = False
            self.promulgate.run(survivor, promotable)
            self._settle(survivor, report)

    def _settle(self, prop: Propositio, report: CycleReport) -> None:
        """Persist, tally, and hand to KFM for kill/recombine/commit."""
        reason = prop.finish_reason or FinishReason.UNPROVEN
        report.tally(reason)
        if reason is FinishReason.PROMULGATED:
            report.promulgated += 1

        quality = _quality(prop)
        # R5: place by the real behavior descriptor (computed now that the full
        # Propositio — statement, proof technique — is available).
        prop.behavior_descriptor = descriptor(prop)
        self.kfm.archive.consider(prop, quality)
        self.runtime.remember(prop)

        # KFM disposition is recorded by placing the candidate in the archive above;
        # run_cycles() closes the loop by drawing recombined parents from the archive
        # as the next cycle's seeds (ADR 0009). RECOMBINE candidates (unproven but not
        # dead) stay as higher-quality stepping stones for that selection.
        _ = self.kfm.disposition(prop)


def _quality(prop: Propositio) -> float:
    """Scalar quality for archive competition. Promulgated > faithful-unproven >
    dead. A real version weights proof difficulty and statement generality."""
    if prop.promulgated:
        return 1.0
    if prop.finish_reason in {FinishReason.UNPROVEN}:
        return 0.5  # survived every cheap gate, only lacks a proof -- valuable
    return 0.0
