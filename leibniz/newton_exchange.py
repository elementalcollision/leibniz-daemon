"""ADR 0072 (Phase δ) — the Newton folio exchange, outbound side.

Newton (the sibling daemon of logic and discovery) is *classically designed to evaluate models*:
its Propositiones carry a falsifiable claim plus executable verification its gates can run. This
module exports each of Leibniz's promulgated, kernel-verified laws as a Newton-shaped Propositio
folio — YAML frontmatter in Newton's own vocabulary, the Enuntiatio prose, the full Lean 4.31
Expressio (statement + proof, ready for Newton's future ``check_proof`` federation capability),
and an **Auditio mechanica**: a self-contained, deterministic Python procedure that re-checks the
claim over a bounded box, generated from the claim's own DSL text (which is already Python).

Honesty rules (the whole design):
- ``verified: false`` in every folio — Newton's stamp is NEWTON's to make. We ship evidence
  (the Lean proof, the audit procedure, the provenance block), never a pre-made verdict.
- Every folio's audit is EXECUTED here before export; a law whose bounded audit fails is
  **refused** (returned as a defect, never shipped) — that would mean our rendered claim and our
  kernel-proved theorem disagree, which is a faithfulness alarm, not an export.
- Outbound only, report-only: nothing Newton says (yet) feeds any Leibniz gate. Verdict
  fold-back, Newton-side ingestion, and A2A registration (their ADR 0016 ceremony) are later
  increments in Newton's own repo.

stdlib only; deterministic; no LLM anywhere.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from leibniz.dsl_to_lean import RenderError, free_vars

#: Default exchange dir — a NEUTRAL location beside Newton's own filesystem seams
#: (their peer registry defaults to ~/.newton/peers/), outside both repos.
DEFAULT_EXCHANGE_DIR = Path("~/.newton/exchange/leibniz")
AUDIT_BOUND = 64          # the audit box mirrors Z3Backend.default_bound
_SELF_TEST_BOUND = 16     # cheap pre-export execution of every audit


def audit_source(claim_property: str, variables: list[str]) -> str:
    """A self-contained Python audit procedure for ``claim_property`` over the non-negative box.
    The DSL is Python syntax already (with ``^`` meaning power); ``gcd``/``factorial``/``min``/
    ``max`` are the only names beyond the variables. Newton can run this under its own sandbox
    discipline without trusting us."""
    expr = claim_property.replace("^", "**")
    vars_tuple = ", ".join(repr(v) for v in variables)
    return f'''def audit(bound: int = {AUDIT_BOUND}) -> bool:
    """True iff the claim holds at EVERY point of the [0, bound] box (a bounded re-check of a
    law proven for ALL values by the accompanying Lean theorem)."""
    from itertools import product
    from math import factorial, gcd
    names = ({vars_tuple},)
    for values in product(range(bound + 1), repeat=len(names)):
        env = dict(zip(names, values))
        env.update(factorial=factorial, gcd=gcd, min=min, max=max)
        if not eval({expr!r}, {{"__builtins__": {{}}}}, env):
            return False
    return True
'''


def _run_audit(src: str, bound: int) -> bool:
    ns: dict = {}
    exec(src, ns)  # noqa: S102 — our own generated text from our own kernel-verified ledger
    return bool(ns["audit"](bound))


def law_folio(row: dict) -> tuple[str, str] | None:
    """(filename, folio markdown) for one ledger row, or None when the row cannot be rendered
    honestly (no claim_property, render failure, or a FAILED bounded audit — the tripwire)."""
    pid, cp = row.get("pid", ""), row.get("claim_property") or ""
    if not (pid and cp and row.get("theorem_src")):
        return None
    try:
        variables = free_vars(cp)
    except RenderError:
        return None
    if not variables or len(variables) > 3:
        return None                                       # box audit stays tractable
    audit = audit_source(cp, variables)
    try:
        if not _run_audit(audit, _SELF_TEST_BOUND):
            return None                                   # claim/theorem disagreement → refuse
    except Exception:
        return None
    born = row.get("born")
    when = (datetime.fromtimestamp(float(born), tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            if born else "")
    thm_name = str(row["theorem_src"]).split(":", 1)[0].replace("theorem", "").strip()
    front = f"""---
propositio_id: leibniz_{pid[:12]}
title: "A kernel-verified law of the Leibniz daemon: {thm_name}"
domain: {row.get('domain') or 'number_theory'}
falsifiable_claim: "For all non-negative integers {', '.join(variables)}: {cp}. Bounded audit included; proven for ALL values by the included Lean theorem."
verified: false
benchmark:
  reference: null
  result: null
  reproducible: false
proof_status: discharged
supersedes: []
superseded_by: []
source_mode: federated_leibniz
authorship: leibniz_daemon
source: leibniz_daemon
voice_exemplar: false
language: en
leibniz:
  pid: {pid}
  kernel: "Lean 4.31 (Docker REPL)"
  kernel_verified: true
  promulgated_at: "{when}"
  trust_charter: "LLMs propose; only mechanical checkers (the Lean kernel, Z3) decide."
---
"""
    body = f"""
## Enuntiatio

{(row.get('statement') or cp).strip()}

## Expressio (Lean 4.31 — kernel-verified in the Leibniz pipeline)

```lean
{str(row['theorem_src']).strip()} :=
{str(row.get('proof_src') or '').strip()}
```

## Auditio mechanica

A deterministic bounded re-check of the claim, generated from the claim's own formal text.
Newton may execute it under its own discipline; `verified` above stays false until NEWTON says
otherwise.

```python
{audit.strip()}
```
"""
    return f"leibniz_{pid[:12]}.md", front + body


def export_new(db_path: str | Path, out_dir: str | Path | None = None) -> dict:
    """Export every promulgated, kernel-verified law not yet in the exchange manifest. Returns
    ``{"exported": n, "refused": r, "total": m}`` for the beat journal. Missing DB → zeros."""
    out = Path(out_dir or DEFAULT_EXCHANGE_DIR).expanduser()
    out.mkdir(parents=True, exist_ok=True)
    manifest_path = out / "manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text())
        if not isinstance(manifest, dict):
            manifest = {}
    except (OSError, ValueError):
        manifest = {}
    rows: list[dict] = []
    try:
        con = sqlite3.connect(f"file:{Path(db_path)}?mode=ro", uri=True)
        con.row_factory = sqlite3.Row
        rows = [dict(r) for r in con.execute(
            "SELECT pid, born, statement, theorem_src, proof_src, claim_property, domain "
            "FROM memory WHERE lower(finish_reason) = 'promulgated' AND kernel_verified = 1 "
            "ORDER BY rowid")]
        con.close()
    except Exception:
        rows = []
    exported = refused = 0
    for row in rows:
        if row["pid"] in manifest:
            continue
        folio = law_folio(row)
        if folio is None:
            refused += 1
            continue
        fname, text = folio
        (out / fname).write_text(text)
        manifest[row["pid"]] = {"file": fname,
                                "exported_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
        exported += 1
    manifest_path.write_text(json.dumps(manifest, indent=1, sort_keys=True))
    return {"exported": exported, "refused": refused, "total": len(manifest)}
