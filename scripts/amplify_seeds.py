"""Bridge: validated CONSTRUCTION seeds → amplification feed (ADR 0042 Track A2).

Connects research ingestion (`leibniz.seeds.validate_seed`) to the amplification spine (`amplify.py`):
a VALIDATED CONSTRUCTION seed carrying a DIRECT witness (`payload['witness'] = {domain, n/d/w/code |
v/k/t/blocks}`) becomes an amplify feed entry tagged with the seed's provenance, so an ingested
construction gets kernel-verified into the corpus.

Proposer-side only and audit-tier: a seed is an UNTRUSTED hint; `amplify` re-checks every witness with
the Lean kernel and the corpus never promulgates. A construction seed that carries a PROGRAM rather than
a witness runs via the untrusted-code sandbox (`leibniz.seed_intake.construction_task` → `SandboxedTool`)
— that route is deliberately NOT duplicated here; this is the direct-witness bridge.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_ROOT / "scripts"))

import amplify  # noqa: E402  (the spine: amplify_one / merge_corpus / render)
from leibniz.seeds import SeedKind, SeedStatus  # noqa: E402


def construction_feed_from_seeds(seeds) -> list[dict]:
    """VALIDATED CONSTRUCTION seeds carrying a direct witness → amplify feed entries (with provenance).

    Skips non-validated / non-construction seeds and program-only construction seeds (those route through
    the sandbox, not here). The witness dict is passed through verbatim so amplify's domain dispatch +
    kernel re-check decide everything; a seed never bypasses a gate."""
    entries: list[dict] = []
    for s in seeds:
        if s.status is not SeedStatus.VALIDATED or s.kind is not SeedKind.CONSTRUCTION:
            continue
        w = (s.payload or {}).get("witness")
        if not isinstance(w, dict):
            continue  # program-carrying construction seed → sandbox route (seed_intake.construction_task)
        entries.append({**w,
                        "source": s.provenance.source_id or "ingested",
                        "note": (s.payload.get("title") or "ingested construction")[:80]})
    return entries


def amplify_construction_seeds(seeds, *, corpus_path: Path, run_kernel: bool = True,
                               stamp: str | None = None) -> dict:
    """End-to-end: validated construction seeds → feed → amplify (kernel re-check) → merged corpus.
    Returns a summary. Audit-tier; never promulgates."""
    feed = construction_feed_from_seeds(seeds)
    reports = [amplify.amplify_one(e, run_kernel=run_kernel, stamp=stamp) for e in feed]
    audited = [r for r in reports if "skipped" not in r]
    existing = json.loads(corpus_path.read_text()) if corpus_path.exists() else []
    merged = amplify.merge_corpus(existing, audited)
    corpus_path.parent.mkdir(parents=True, exist_ok=True)
    corpus_path.write_text(json.dumps(merged, indent=2) + "\n")
    return {"seeds": len(list(seeds)) if hasattr(seeds, "__len__") else None,
            "fed": len(feed), "audited": len(audited),
            "kernel_verified": sum(1 for r in audited if amplify._verified(r)),
            "corpus": len(merged)}


def main() -> int:
    ap = argparse.ArgumentParser(description="Amplify VALIDATED CONSTRUCTION seeds (direct-witness) into "
                                             "the kernel-checked corpus. Audit-tier; never promulgates.")
    ap.add_argument("--seeds", required=True, help="JSON: a list of seed records already validated "
                                                   "(domain witness under .payload.witness)")
    ap.add_argument("--corpus", default=str(amplify.DEFAULT_CORPUS))
    ap.add_argument("--no-kernel", action="store_true")
    ap.add_argument("--stamp")
    args = ap.parse_args()
    # NB: a real run constructs Seed objects via seeds.seed_from_feed_record + validate_seed; this CLI
    # accepts pre-validated seed dicts for convenience and re-wraps them minimally.
    from leibniz.seeds import Seed, SeedProvenance
    raw = json.loads(Path(args.seeds).read_text())
    seeds = [Seed(kind=SeedKind(s.get("kind", "construction")), payload=s.get("payload", {}),
                  provenance=SeedProvenance(source_id=s.get("source_id", "")),
                  proof_of_use=s.get("proof_of_use", "x"),
                  status=SeedStatus(s.get("status", "validated"))) for s in raw]
    summary = amplify_construction_seeds(seeds, corpus_path=Path(args.corpus),
                                         run_kernel=not args.no_kernel, stamp=args.stamp)
    print(f"amplify-seeds: {summary['fed']} construction witnesses fed, "
          f"{summary['kernel_verified']} kernel-verified; corpus -> {summary['corpus']} entries "
          f"[audit-tier; not promulgated]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
