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
from leibniz.discovery import (
    DiscoveryNotebook,
    FrontierController,
    steer,
    weakening_seeds,
)
from leibniz.discovery import quality as _quality
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
    # D9 (ADR 0015): if set, multi-cycle runs rotate the survey across these domains
    # (one per cycle, round-robin). Empty -> the single `domain` above, unchanged.
    domains: tuple[str, ...] = ()
    # R2c: the judged-faithfulness budget (ADR 0001 §5). Optional — when absent the
    # daemon does not bound the residual (the fakes/demo run without it).
    budget: Optional[TrustBudget] = None
    # ADR 0011: coarse USD cost cap for multi-cycle autonomous runs. Optional.
    cost_budget: Optional[CostBudget] = None
    # ADR 0018 (discovery frontier): proposal-side steering. Both optional — when
    # absent the loop behaves exactly as before (cold start / deterministic fakes).
    notebook: Optional[DiscoveryNotebook] = None       # outcome-conditioned conjecture
    notebook_path: Optional[str] = None                # ADR 0023: persist near-misses across runs
    frontier: Optional[FrontierController] = None       # adaptive difficulty band
    frontier_path: Optional[str] = None                # persist the band across runs
    weaken_k: int = 2                                   # UNPROVEN -> weaker re-conjectures
    # ADR 0034 Stage 2: empirical pattern miner (proposal-side seeds from computed residue facts).
    # Optional — absent -> no mining, loop unchanged. When present, `mine_k` of each cycle's seeds
    # are mined patterns that REPLACE (not add to) survey seeds, so the conjecture budget is
    # unchanged vs a no-mining run (a clean A/B on volume). It seeds; the gates + kernel decide.
    pattern_miner: Optional[object] = None
    mine_k: int = 0

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
        active = self._active_domains()
        for i in range(n):
            if self.cost_budget is not None and self.cost_budget.exhausted():
                break  # ADR 0011: stop before starting a cycle that would exceed the cap
            fresh_only = i == 0 or stagnant >= stagnation_limit
            domain = active[i % len(active)]  # D9: round-robin across domains
            seeds = self._next_seeds(fresh_only, fresh_per_cycle, recombine_k, domain)
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
            if self.frontier is not None:
                self.frontier.update()  # ADR 0018 M2: retune the band from outcomes
                if self.frontier_path:
                    self.frontier.save(self.frontier_path)  # persist across runs
            if self.notebook is not None and self.notebook_path:
                self.notebook.save(self.notebook_path)  # ADR 0023: persist near-misses
        return reports

    def _active_domains(self) -> tuple[str, ...]:
        """D9: the domains a multi-cycle run rotates over (defaults to `domain`)."""
        return self.domains or (self.domain,)

    def _next_seeds(
        self, fresh_only: bool, fresh_per_cycle: int, recombine_k: int, domain: str | None = None
    ) -> list[str]:
        domain = domain or self.domain
        if fresh_only:
            return self._blend_mined(self.survey.run(domain))
        # ADR 0018 M3: mine UNPROVEN near-misses into strictly-weaker re-conjectures,
        # alongside the KFM recombinations and a few fresh survey seeds.
        weaken = weakening_seeds(self.notebook.too_hard, self.weaken_k) if self.notebook else []
        seeds = (self.kfm.recombination_seeds(recombine_k) + weaken
                 + self.survey.run(domain)[:fresh_per_cycle])
        return self._blend_mined(seeds or self.survey.run(domain))  # cold archive -> fresh survey

    def _blend_mined(self, base: list[str]) -> list[str]:
        """ADR 0034 Stage 2: REPLACE up to `mine_k` of this cycle's seeds with computed-pattern
        seeds, preserving the seed COUNT (so a mining run's conjecture budget matches a no-mining
        run — a clean A/B on volume). No miner / mine_k<=0 -> `base` unchanged."""
        if self.pattern_miner is None or self.mine_k <= 0 or not base:
            return base
        mined = self.pattern_miner.seeds(self.mine_k)
        if not mined:
            return base
        mined = mined[:len(base)]                 # never grow the seed list
        return mined + base[len(mined):]

    @staticmethod
    def _seed_origin(seed: str) -> str:
        """Classify a seed by its producer (ADR 0034 §5 provenance), by the markers each producer
        stamps: mined patterns, KFM recombinations, weakened near-misses, else the survey feed."""
        from leibniz.pattern_mining import MINED_SEED_PREFIX
        if seed.startswith(MINED_SEED_PREFIX):
            return "mined"
        if "STRICTLY WEAKER" in seed:
            return "weaken"
        if "combining features" in seed:
            return "kfm"
        return "survey"

    def _run_seeds(self, seeds: list[str], report: CycleReport) -> None:
        for seed in seeds:
            try:
                # ADR 0018 M1/M2: condition the conjecture on ledger lessons + the target
                # difficulty band (a no-op until the notebook/frontier have learned).
                origin = self._seed_origin(seed)  # ADR 0034 §5: provenance for the kill condition
                prop = self.conjecture.run(steer(seed, self.notebook, self.frontier))
                prop.seed_origin = origin
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
            except Exception as exc:  # noqa: BLE001 — resilience boundary (ADR 0029)
                # A transient provider/infra failure (e.g. a SUSTAINED Anthropic 529 that
                # outlasts both the SDK retries and the autoformalizer's failover backups)
                # on ONE seed must NOT crash a multi-cycle, hours-long run. Record it and
                # move to the next seed. KeyboardInterrupt/SystemExit are not Exception, so
                # an operator Ctrl-C still stops the run. The kernel/trust path is untouched —
                # a skipped seed simply yields no candidate.
                report.by_reason["errored"] = report.by_reason.get("errored", 0) + 1
                print(f"[daemon] seed errored ({type(exc).__name__}: {str(exc)[:140]}); "
                      f"skipping to next seed", flush=True)
                continue

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

        # ADR 0018 M1/M2: feed the outcome back to the proposal side (pass the
        # resolved reason so a reached-but-unproven candidate is mined, not lost).
        if self.notebook is not None:
            self.notebook.record(prop, reason)
        if self.frontier is not None:
            # Track PROVABILITY (did the kernel close it), not promulgation — a
            # budget-refused but kernel-proved candidate is a tractable difficulty, not
            # a miss (ADR 0018 review).
            self.frontier.record(bool(prop.demonstratio and prop.demonstratio.kernel_verified))

        # KFM disposition is recorded by placing the candidate in the archive above;
        # run_cycles() closes the loop by drawing recombined parents from the archive
        # as the next cycle's seeds (ADR 0009). RECOMBINE candidates (unproven but not
        # dead) stay as higher-quality stepping stones for that selection.
        _ = self.kfm.disposition(prop)
