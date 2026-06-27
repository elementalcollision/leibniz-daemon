"""LLM-free evolutionary loop for CWC construction search (the FunSearch harness, no spend).

This is the island/evolutionary DRIVER that the (billable, gated) LLM proposer will drop into. Here it
runs with a DETERMINISTIC proposer over the STRUCTURAL template space (prescribed-group constructions —
the proven lever that matched 53% of records where brute search plateaued). No LLM, no GPU, no spend.

It serves three purposes:
  1. the reusable harness (genome -> evaluate -> select -> mutate/crossover -> islands + migration);
  2. a cheap measure-before-build PROBE: does an evolutionary search over our best deterministic
     templates beat anything? (Expected RED — the templates' reach was already measured at 0 beats —
     which is exactly the point: it BOUNDS what a non-LLM loop can do and is the baseline the LLM
     proposer must exceed to be worth the spend.);
  3. a baseline + integration surface so wiring the LLM proposer later is a one-component swap.

Trust posture: the loop only SEARCHES. Every candidate's witness is re-validated by verify_cwc (inside
probe_beta_automorphism.attempt), the novelty floor is the automated oracle (post-Rosin; see
cwc_rosin_crosscheck), and a flagged beat is NOT promulgated — it would go to the Lean kernel re-check
(scripts/cwc_check.py) + the ADR 0040 carve-out + operator review. Nothing here sets kernel_verified.
The evaluator is pluggable: this deterministic path runs OUR OWN trusted templates in-process (fast);
the future LLM path MUST use the untrusted-code sandbox (scripts/funsearch_sandbox.py).

Pure stdlib + project modules; deterministic (seeded LCG, no os.urandom / Math.random).
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cwc_table_oracle as ora  # noqa: E402
import probe_beta_automorphism as pa  # noqa: E402
from cwc_rosin_crosscheck import rosin_floor  # noqa: E402


class _LCG:
    """Deterministic PRNG (reproducible; no external randomness)."""

    def __init__(self, seed: int):
        self.s = seed & 0x7FFFFFFF

    def nxt(self) -> int:
        self.s = (1103515245 * self.s + 12345) & 0x7FFFFFFF
        return self.s

    def pick(self, n: int) -> int:
        return self.nxt() % max(1, n)


@dataclass(frozen=True)
class Genome:
    """A candidate construction. For the deterministic structural proposer, `gene` is a prescribed
    group kind (e.g. 'cyclic', 'affine', 'sub:3', 'affsub:5', 'fixcyc'). The LLM proposer would
    instead carry program source in a sibling template — same loop, different proposer."""
    template: str
    gene: str


def effective_best_known(n: int, d: int, w: int, snap) -> int | None:
    """Post-Rosin novelty floor = max(committed snapshot, Rosin 2026). The snapshot already dominates
    Rosin (verified, cwc_rosin_crosscheck), so this is defensive; a beat must exceed BOTH."""
    bk = ora.best_known(n, d, w, snap)
    rf = rosin_floor(n, d, w)
    if bk is None:
        return rf
    return max(bk, rf) if rf is not None else bk


class DeterministicProposer:
    """LLM-free proposer over the structural template space. Genes are prescribed group kinds; mutation
    walks to a different kind; crossover picks one parent's gene (structural genes do not blend)."""

    def __init__(self, n: int):
        self.kinds = pa.candidate_groups_rich(n)

    def seed(self, rng: _LCG, k: int) -> list[Genome]:
        pool = list(self.kinds)
        out = []
        for _ in range(min(k, len(pool))):
            g = pool.pop(rng.pick(len(pool)))
            out.append(Genome("structural", g))
        return out

    def mutate(self, g: Genome, rng: _LCG) -> Genome:
        return Genome("structural", self.kinds[rng.pick(len(self.kinds))])

    def crossover(self, a: Genome, b: Genome, rng: _LCG) -> Genome:
        return a if rng.pick(2) == 0 else b


def evaluate_structural(genome: Genome, n: int, d: int, w: int, snap, budget_s: float) -> dict:
    """Evaluate a structural genome by running the prescribed-group construction (verify_cwc-checked
    inside attempt) and scoring fitness = valid code size. Beat is judged against the post-Rosin floor."""
    r = pa.attempt(n, d, w, snap, kind=genome.gene, budget_s=budget_s)
    floor = effective_best_known(n, d, w, snap)
    size = r["found"] if r["verified"] else 0
    beats = bool(r["verified"] and floor is not None and size > floor)
    return {"gene": genome.gene, "fitness": size, "size": size, "verified": r["verified"],
            "floor": floor, "beats": beats,
            "witness": r["witness"] if beats else None}


def evolve(n: int, d: int, w: int, *, snap=None, pop: int = 8, generations: int = 6,
           islands: int = 2, budget_s: float = 3.0, seed: int = 0xC0FFEE,
           proposer=None, evaluate=evaluate_structural) -> dict:
    """Island evolutionary search. Deterministic. Returns the best valid code found, the post-Rosin
    floor, whether anything beat it, and a per-generation history. Caches by gene (the structural
    space is small) so repeated kinds are not re-run."""
    snap = snap if snap is not None else ora.load_snapshot()[0]
    proposer = proposer or DeterministicProposer(n)
    rng = _LCG(seed ^ (n * 2654435761) ^ (d * 40503) ^ (w * 77777))
    cache: dict[str, dict] = {}

    def ev(g: Genome) -> dict:
        if g.gene not in cache:
            cache[g.gene] = evaluate(g, n, d, w, snap, budget_s)
        return cache[g.gene]

    pops = []
    for _ in range(islands):
        members = [(g, ev(g)) for g in proposer.seed(rng, pop)]
        pops.append(members)

    history = []
    best = {"size": 0, "gene": None, "beats": False, "witness": None}
    beats_found = []
    for gen in range(generations):
        for i in range(islands):
            members = sorted(pops[i], key=lambda m: m[1]["fitness"], reverse=True)
            survivors = members[: max(1, pop // 2)]
            children = []
            while len(survivors) + len(children) < pop:
                pa_g = survivors[rng.pick(len(survivors))][0]
                pb_g = survivors[rng.pick(len(survivors))][0]
                child = proposer.mutate(proposer.crossover(pa_g, pb_g, rng), rng)
                children.append((child, ev(child)))
            pops[i] = survivors + children
        # migration: copy each island's champion to the next island
        champs = [max(p, key=lambda m: m[1]["fitness"]) for p in pops]
        for i in range(islands):
            pops[i].append(champs[(i - 1) % islands])
        # bookkeeping
        for p in pops:
            for g, r in p:
                if r["fitness"] > best["size"]:
                    best = {"size": r["size"], "gene": r["gene"], "beats": r["beats"],
                            "witness": r["witness"]}
                if r["beats"] and r["gene"] not in [b["gene"] for b in beats_found]:
                    beats_found.append({"gene": r["gene"], "size": r["size"], "witness": r["witness"]})
        history.append({"gen": gen, "best_size": best["size"], "evals": len(cache)})

    return {"n": n, "d": d, "w": w, "floor": effective_best_known(n, d, w, snap),
            "best_size": best["size"], "best_gene": best["gene"], "beats": bool(beats_found),
            "beats_detail": beats_found, "evals": len(cache), "kinds_available": len(proposer.kinds),
            "history": history}


def main() -> int:
    snap, _ = ora.load_snapshot()
    # probe cells: tractable-known (sanity the loop matches records) + near-miss cells from the
    # structural sweep (does evolution find a beat? expected RED — bounds the non-LLM loop).
    cells = [(14, 6, 6), (13, 6, 5), (17, 6, 4), (21, 6, 4), (18, 10, 6)]
    budget = float(sys.argv[2]) if len(sys.argv) > 2 else 3.0
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("probe_beta_out/funsearch_llmfree_probe.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for n, d, w in cells:
        r = evolve(n, d, w, snap=snap, pop=8, generations=5, islands=2, budget_s=budget)
        rows.append(r)
        tag = "*** BEAT ***" if r["beats"] else "no beat"
        print(f"   A({n},{d},{w}) floor={r['floor']} best={r['best_size']} "
              f"via {r['best_gene']} evals={r['evals']}/{r['kinds_available']} -> {tag}")
    summary = {"cells": len(rows), "beats": sum(r["beats"] for r in rows), "rows": rows}
    out.write_text(json.dumps(summary, indent=2))
    print(f"  BEATS: {summary['beats']}/{summary['cells']}  -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
