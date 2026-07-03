"""Serialize the Calculemus ledger to the codexcalculemus.com source ledger.

Bridges the daemon's in-memory `Calculemus` (R6) to the Astro site: it reads the
operator-published laws and the held-back Codex, and emits the JSON ledger the
site's `sync-ledger.mjs` consumes. Read-only over the ledger — it writes no
`kernel_verified` and no `promulgated`, and mints no edge; it only reports what
`Calculemus` already decided (promotion is gated there; publication is the
operator's act). `kernel_verified`/`qed` are read straight from the Demonstratio.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Optional

from leibniz.calculemus import Calculemus
from leibniz.propositio import Propositio
from leibniz.trust import PROOF_EDGE

_NAME_RE = re.compile(r"(?:theorem|lemma)\s+([^\s({\[:]+)")


def _slug(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")
    return s or "law"


def _law_id(prop: Propositio) -> str:
    if prop.expressio:
        m = _NAME_RE.search(prop.expressio.theorem_src)
        if m:
            return _slug(m.group(1))
    return _slug(prop.enuntiatio.statement)[:48]


def _consensus(prop: Propositio) -> int:
    """The N from the kernel proof edge, if the consensus prover recorded it."""
    for ev in prop.edges:
        if ev.edge == PROOF_EDGE and isinstance(ev.detail, dict):
            n = ev.detail.get("consensus")
            if isinstance(n, int):
                return n
    return 0


def law_payload(prop: Propositio, *, published_at: str = "", specimen: bool = False) -> dict:
    """One published law as the site's ledger shape (the Propositio triad)."""
    en, ex, de = prop.enuntiatio, prop.expressio, prop.demonstratio
    return {
        "id": _law_id(prop),
        "pid": prop.pid,
        "statement": en.statement,
        "claim_type": en.claim_type.value,
        "falsifiable_claim": en.falsifiable_claim,
        "domain": en.domain,
        "theorem_src": ex.theorem_src if ex else "",
        "proof_src": (de.proof_src or "") if de else "",
        "imports": list(ex.imports) if ex else [],
        "qed": de.qed if de else "Q.E.I.",
        "kernel_verified": bool(de and de.kernel_verified),
        "consensus": _consensus(prop),
        "published_at": published_at,
        "specimen": specimen,
    }


def cycle_payload(
    *,
    cycle: object,
    date: str,
    domain: str,
    kind: str,
    title: str,
    summary: str,
    findings: Optional[list] = None,
    artifacts: Optional[list] = None,
    links: Optional[list] = None,
    laws: Optional[list] = None,
) -> dict:
    """One work-log entry for *Il Lavoro* (the site's `/cycles` page, ADR 0017).

    A cycle records what the daemon *did* — seeds surveyed, candidates quarantined,
    and (when it happens) a law promulgated. It is descriptive, not a certificate:
    it carries **no** `kernel_verified`, mints **no** edge, and promulgates nothing.
    Any kernel/Z3 evidence a cycle references lives under `findings`/`artifacts` as
    *reported* results, tagged by the checker that produced them — never as a
    promulgated Q.E.D. (`laws` only lists ids of laws the gated pipeline already
    promulgated; publication remains the operator's separate, guarded act.)

    Core fields mirror the rendered work-log badge (cycle · date · domain · kind ·
    summary); `findings`/`artifacts`/`links` are optional and degrade gracefully if
    the renderer does not surface them yet."""
    return {
        "cycle": cycle,
        "date": date,
        "domain": domain,
        "kind": kind,
        "title": title,
        "summary": summary,
        "findings": list(findings or []),
        "artifacts": list(artifacts or []),
        "links": list(links or []),
        "laws": list(laws or []),
    }


def ledger_payload(calc: Calculemus, *, generated_at: str = "", cycles: Optional[list] = None) -> dict:
    """The full source ledger: operator-published laws + held-back colophon + cycles.

    Only laws the operator has published reach `laws`; promulgated-but-unpublished
    Codex laws are surfaced as `held_back` (colophon only)."""
    published = [calc.codex[pid] for pid in calc.codex if pid in calc.published]
    held = [calc.codex[pid] for pid in calc.codex if pid not in calc.published]
    return {
        "site": "Calculemus",
        "generated_at": generated_at,
        "laws": [law_payload(p) for p in published],
        "held_back": [
            {
                "statement": p.enuntiatio.statement,
                "qed": p.demonstratio.qed if p.demonstratio else "Q.E.I.",
                "reason": "promulgated to the Codex; awaiting operator publication",
            }
            for p in held
        ],
        "cycles": list(cycles or []),
    }


def write_ledger(calc: Calculemus, path: Path, *, generated_at: str = "", cycles: Optional[list] = None) -> dict:
    payload = ledger_payload(calc, generated_at=generated_at, cycles=cycles)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n")
    return payload
