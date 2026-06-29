"""Seed intake — route VALIDATED seeds into the discovery loop's PROPOSER seams (ADR 0041 Phase 4).

This is the activation step: ingested research (via the scraper -> seeds.validate_seed) now *drives* the
daemon. A validated seed only ever feeds a PROPOSER — never a decider:

  FLOOR        -> the post-Rosin novelty floor (`seeds.effective_floor`; raise-only — Phase 3)
  TARGET       -> proposal-side STEERING for the conjecturer (a research target to emulate; gates
                  nothing, exactly like ADR 0034 genre steering / novelty exemplars)
  CONSTRUCTION -> a `SandboxTask` for the `SandboxedTool` (runs ONLY in the untrusted-code sandbox)

Quarantined / CONFLICT / un-validated seeds route to NOTHING. The faithfulness->novelty->proof chain,
the trust policy, and the tool registry are all UNCHANGED — this module adds no decider and touches no
gate. The conjecturer reads `seed_steering(...)` as extra prompt context; a CONSTRUCTION seed becomes a
sandbox job; the gates still decide everything downstream.
"""
from __future__ import annotations

from typing import Optional

from leibniz.seeds import Seed, SeedKind, SeedStatus
from leibniz.tools.sandbox import SandboxTask


def admissible_targets(seeds) -> list[Seed]:
    """The VALIDATED TARGET seeds — the only seeds that may steer the conjecturer."""
    return [s for s in seeds if s.status is SeedStatus.VALIDATED and s.kind is SeedKind.TARGET]


def seed_steering(seeds, *, cap: int = 6) -> str:
    """Turn VALIDATED TARGET seeds into a short, proposal-side steering block the conjecturer may emulate.

    Gates NOTHING (it only enters the CONJECTURE prompt as context, mirroring
    `discovery.DiscoveryNotebook.steering` / `load_novelty_exemplars`): a seed is an untrusted hint about
    *what to try*, and the faithfulness/novelty/proof gates still decide whether any resulting conjecture
    survives. Returns "" when there are no admissible targets (so a daemon with no seeds is unchanged)."""
    lines = []
    for s in admissible_targets(seeds):
        title = (s.payload.get("title") or "").strip()
        if title:
            lines.append(f"- research target [{s.provenance.source_id}]: {title}")
        if len(lines) >= cap:
            break
    if not lines:
        return ""
    return ("Ingested research targets (UNTRUSTED hints — propose toward these; the gates still "
            "decide):\n" + "\n".join(lines))


def construction_task(seed: Seed) -> Optional[SandboxTask]:
    """A VALIDATED CONSTRUCTION seed -> a `SandboxTask` (program + args) for the `SandboxedTool`.

    Returns None for any non-validated or non-CONSTRUCTION seed: a construction seed's code runs ONLY
    inside the untrusted-code sandbox (it is never exec'd in-process), and its output is re-checked by
    the registry exactly like any other tool. The seed cannot reach a decider."""
    if seed.status is not SeedStatus.VALIDATED or seed.kind is not SeedKind.CONSTRUCTION:
        return None
    prog = seed.payload.get("program_source") or seed.payload.get("program")
    if not prog:
        return None
    args = seed.payload.get("contract_args") or seed.payload.get("args") or {}
    return SandboxTask(program=prog, args=args)
