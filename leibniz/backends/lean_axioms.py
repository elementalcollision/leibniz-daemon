"""Shared axiom-closure check (H0), lifted from ``scripts/export_calculemus.py`` so the
faithfulness-time re-check (ADR 0056 Track A increment 2, build obligation 3) and the
publish-time ledger check run the SAME code — a proof accepted at faithfulness time and a
proof accepted at export time face one axiom discipline, not two drifting copies.

A kernel-accepted declaration may still rest on `sorryAx` (a hole) or `Lean.ofReduceBool`
(``native_decide`` — trusting the compiled evaluator, not the kernel) or a project-admitted
axiom. `#print axioms <name>` reports the footprint; ``axiom_closure`` asserts it is a
subset of the standard Lean/Mathlib set. Anything else ⇒ not a proof for our purposes.
"""
from __future__ import annotations

import re

# The standard Lean/Mathlib axioms. NOTE `Lean.ofReduceBool` (native_decide) is deliberately
# NOT in this set: a "proof" by compiled evaluation is trusted-compiler, not kernel-decided.
STD_AXIOMS = frozenset({"propext", "Classical.choice", "Quot.sound"})

_NAME_RE = re.compile(r"(?:theorem|lemma)\s+([^\s({\[:]+)")
_AXIOMS_RE = re.compile(r"depends on axioms:\s*\[([^\]]*)\]")


def axiom_closure(backend, theorem_src: str, proof_src: str, imports, allowed=STD_AXIOMS) -> dict:
    """Elaborate ``<theorem_src> := <proof_src>`` and run ``#print axioms``. ok = it elaborates
    with no error AND its axiom footprint contains no ``sorryAx`` and no axiom outside
    ``allowed`` (the standard Lean/Mathlib set). A law that secretly rests on ``sorry``, on
    ``native_decide``, or on an admitted lemma fails here even if the kernel elaborates the
    (open) term. Read-only: mints nothing, edits no core file."""
    m = _NAME_RE.search(theorem_src)
    if not m:
        return {"ok": False, "reason": "no theorem name in theorem_src", "axioms": []}
    name = m.group(1)
    body = proof_src if proof_src.lstrip().startswith(":=") else f":= {proof_src}"
    src = f"{theorem_src} {body}\n#print axioms {name}"
    r = backend._run(src, tuple(imports))
    if r is None:
        return {"ok": False, "reason": "no response from REPL", "axioms": [], "name": name}
    msgs = r.get("messages", []) or []
    errors = [(mm.get("data") or "") for mm in msgs if mm.get("severity") == "error"]
    axioms: list = []
    for mm in msgs:
        am = _AXIOMS_RE.search(mm.get("data") or "")
        if am:
            axioms = [a.strip() for a in am.group(1).split(",") if a.strip()]
    has_sorry = "sorryAx" in axioms or any("sorry" in e.lower() for e in errors)
    extra = [a for a in axioms if a not in allowed]
    return {"ok": bool(not errors and not has_sorry and not extra), "axioms": axioms,
            "extra_axioms": extra, "has_sorry": has_sorry, "errors": errors[:2], "name": name}
