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
#: ADR 0089 — positive evidence that `#print axioms` actually REPORTED on our theorem. Lean emits
#: one of two forms, and the second matches no axiom list at all:
#:     'foo' depends on axioms: [propext, Classical.choice, Quot.sound]
#:     'foo' does not depend on any axioms
#: Requiring a non-empty `axioms` list would therefore false-DEFER every axiom-free proof (verified
#: against live Lean 4.31: `theorem t : 1 + 1 = 2 := rfl` prints the second form). Both forms count.
#: The name may be reported FULLY QUALIFIED while `_NAME_RE` reads the short one out of the source
#: (this repo's own recorded output has both: 'SO_cube.cube_not_self_ordered' and 'steiner_s8_225_s9_289').
#: An ADR 0062 preamble that opens a namespace so the statement can use short names would otherwise
#: turn a clean footprint into a silent DEFER, so an optional qualifier is allowed.
def _report_re(name: str):
    return re.compile(r"'(?:[^']*\.)?" + re.escape(name)
                      + r"'\s*(?:depends on axioms:|does not depend on any axioms)")


def axiom_closure(backend, theorem_src: str, proof_src: str, imports, allowed=STD_AXIOMS,
                  preamble: str = "") -> dict:
    """Elaborate ``<preamble> <theorem_src> := <proof_src>`` and run ``#print axioms``. ok = it
    elaborates with no error AND its axiom footprint contains no ``sorryAx`` and no axiom outside
    ``allowed`` (the standard Lean/Mathlib set). A law that secretly rests on ``sorry``, on
    ``native_decide``, or on an admitted lemma fails here even if the kernel elaborates the
    (open) term. ADR 0062: the WHOLE assembled source — the operator-authored ``preamble`` (defs/
    set_options) included — is elaborated, so a smuggled hole/axiom in the preamble is caught too.
    Read-only: mints nothing, edits no core file."""
    m = _NAME_RE.search(theorem_src)
    if not m:
        return {"ok": False, "reason": "no theorem name in theorem_src", "axioms": [],
                "saw_axiom_report": False}
    name = m.group(1)
    body = proof_src if proof_src.lstrip().startswith(":=") else f":= {proof_src}"
    decl = f"{theorem_src} {body}\n#print axioms {name}"
    src = f"{preamble.rstrip()}\n{decl}" if preamble.strip() else decl
    return axiom_report(backend._run(src, tuple(imports)), name, allowed)


def axiom_report(response, name: str, allowed=STD_AXIOMS) -> dict:
    """Analyse ONE REPL response for the axiom footprint of declaration ``name``.

    Split out of ``axiom_closure`` (ADR 0090) so a caller that assembles its OWN Lean source —
    ``scripts/counterexample_domain.py`` emits whole namespaced certs, which cannot be split into
    the ``theorem_src``/``proof_src`` shape without re-writing the Lean — shares the HARDENED
    analysis instead of open-coding a fresh one. That script's open-coded scan was the third copy
    of this logic and the only one to publish a false record: its ``(r or {})`` turned a dead-REPL
    ``None`` into ``ok=True``, and ``docs/results/counterexample_domain.json`` recorded GREEN /
    ``kernel.status: checked`` for certificates whose Mathlib import does not exist in the pinned
    image and which therefore were never elaborated at all.

    ``ok`` requires ALL of: a response at all; no error message; no ``sorry`` in ANY message
    (Lean reports it as a WARNING); every axiom inside ``allowed``; and a ``#print axioms`` report
    that NAMES this declaration — without that last clause an empty message list satisfies the
    rest vacuously, which is the ADR 0089 fail-open."""
    if response is None:
        return {"ok": False, "reason": "no response from REPL", "axioms": [], "name": name,
                "saw_axiom_report": False}
    msgs = response.get("messages", []) or []
    errors = [(mm.get("data") or "") for mm in msgs if mm.get("severity") == "error"]
    # Read the footprint ONLY from the report about our own declaration. An ADR 0062 preamble may
    # carry its own `#print axioms` (16 of the docs/crt/*.lean artifacts do), so a name-blind scan
    # could hand back the preamble's list for our theorem — including for an axiom-free one.
    rep = _report_re(name)
    axioms: list = []
    saw_report = False
    for mm in msgs:
        data = mm.get("data") or ""
        if not rep.search(data):
            continue
        saw_report = True
        am = _AXIOMS_RE.search(data)
        axioms = [a.strip() for a in am.group(1).split(",") if a.strip()] if am else []
    # Scan EVERY message, not just errors: Lean reports `declaration uses 'sorry'` as a WARNING,
    # so an error-only scan was weaker here than `_kernel_ok` (which scans all of them) — an
    # asymmetry that let this check be the laxer of the two it is meant to reinforce.
    has_sorry = "sorryAx" in axioms or any("sorry" in (mm.get("data") or "").lower() for mm in msgs)
    extra = [a for a in axioms if a not in allowed]
    # ADR 0089 — this function exists to READ the axiom footprint, so it must not pass without
    # having seen one. Before this check `ok` was `not errors and not has_sorry and not extra`,
    # all three of which a response with NO messages satisfies vacuously: a REPL answering
    # `{"messages": []}` returned ok=True for a FALSE theorem proved `by sorry`, and since
    # `decide_certificate` gates every leg on this, that is the whole faithfulness certificate.
    # `#print axioms` always reports on success, so no report means something went wrong.
    # The report must name OUR theorem, so a report about some other declaration (e.g. one the
    # operator-authored preamble elaborated, ADR 0062) cannot stand in for it.
    ok = bool(not errors and not has_sorry and not extra and saw_report)
    return {"ok": ok, "axioms": axioms, "saw_axiom_report": saw_report,
            "extra_axioms": extra, "has_sorry": has_sorry, "errors": errors[:2], "name": name}
