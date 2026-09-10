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
from typing import Optional

# The standard Lean/Mathlib axioms. NOTE `Lean.ofReduceBool` (native_decide) is deliberately
# NOT in this set: a "proof" by compiled evaluation is trusted-compiler, not kernel-decided.
STD_AXIOMS = frozenset({"propext", "Classical.choice", "Quot.sound"})

#: ADR 0095 — the name must come from a real DECLARATION, not from anywhere in the text.
#: `_NAME_RE.search` takes the first `theorem <name>` match anywhere, comments included, and the
#: name is what `#print axioms` is asked about. So a `theorem_src` opening with the comment
#:     -- theorem Nat.add_comm
#: made both `axiom_closure` and the backends report the footprint of MATHLIB's `Nat.add_comm`
#: — clean, and about a different declaration entirely — while the real theorem was proved by
#: `native_decide`. Measured on the pinned 4.31: `kernel_verified=True`, `Q.E.D.`, and
#: `axiom_closure(...)["ok"] is True`. `theorem_src` is proposer-authored, so this was reachable.
#: Strip comments (nesting-aware — Lean's block comments nest) and require the keyword to open
#: a line, so only an actual declaration can name the thing we certify.
_DECL_RE = re.compile(
    r"^[ \t]*(?:@\[[^\]]*\][ \t]*)*"
    r"(?:(?:private|protected|noncomputable|scoped|local|nonrec|unsafe|partial)[ \t]+)*"
    r"(?:theorem|lemma)[ \t]+([^\s({\[:]+)", re.MULTILINE)


def _strip_comments(src: str) -> str:
    """Remove Lean line (`--`) and block (`/- -/`, nesting) comments. Over-stripping is the safe
    direction: it can only lose the name, and a lost name fails CLOSED."""
    out: list[str] = []
    i, depth, n = 0, 0, len(src)
    while i < n:
        if src.startswith("/-", i):
            depth += 1
            i += 2
        elif depth and src.startswith("-/", i):
            depth -= 1
            i += 2
        elif depth:
            i += 1
        elif src.startswith("--", i):
            j = src.find("\n", i)
            i = n if j < 0 else j
        else:
            out.append(src[i])
            i += 1
    return "".join(out)


def declaration_name(theorem_src: str) -> Optional[str]:
    """The name of the declaration `theorem_src` actually declares, or None (fail closed)."""
    m = _DECL_RE.search(_strip_comments(theorem_src))
    if not m:
        return None
    # `theorem upoly.{u} ...` — the char class stops at `{` and leaves a trailing dot, and
    # `#print axioms upoly.` is a syntax error (a silent DEFER on an honest proof). Lean names
    # never end in a dot, so trimming one is safe.
    return m.group(1).rstrip(".") or None
#: ADR 0089 — positive evidence that `#print axioms` actually REPORTED on our theorem. Lean emits
#: one of two forms, and the second matches no axiom list at all:
#:     'foo' depends on axioms: [propext, Classical.choice, Quot.sound]
#:     'foo' does not depend on any axioms
#: Requiring a non-empty `axioms` list would therefore false-DEFER every axiom-free proof (verified
#: against live Lean 4.31: `theorem t : 1 + 1 = 2 := rfl` prints the second form). Both forms count.
#: The name may be reported FULLY QUALIFIED while `declaration_name` reads the short one out of the source
#: (this repo's own recorded output has both: 'SO_cube.cube_not_self_ordered' and 'steiner_s8_225_s9_289').
#: An ADR 0062 preamble that opens a namespace so the statement can use short names would otherwise
#: turn a clean footprint into a silent DEFER, so an optional qualifier is allowed.
def _report_re(name: str):
    """Match a `#print axioms` report about ``name`` AND capture its axiom list in one go.

    ADR 0095: these used to be two independent searches — `_report_re` found the report and
    a separate axiom-list regex then found "an" axiom list in the same message. That decoupling is only safe
    while one message holds exactly one report. It does not, and the CLI transport holds the
    WHOLE FILE in one message, so that search returned whichever list was printed FIRST:
    an ADR 0062 preamble carrying its own `#print axioms` (16 of the `docs/crt/*.lean` artifacts
    do) handed its clean list to our dirty theorem. Capturing the list as part of the same match
    ties the name to its own footprint and cannot be confused by neighbouring reports.

    Group 1 is the axiom list, or None for the axiom-free form ("does not depend on any axioms").
    """
    return re.compile(r"'(?:[^']*\.)?" + re.escape(name)
                      + r"'\s*(?:depends on axioms:\s*\[([^\]]*)\]"
                      + r"|does not depend on any axioms)")


#: Lean reports a hole as the WARNING `declaration uses 'sorry'`, and as `sorryAx` in the axiom
#: footprint. A blind `"sorry" in message` scan also matches the declaration's own NAME, which
#: `#print axioms <name>` echoes back — so `theorem sorry_free_addition ... := by decide` was a
#: silent DEFER on a genuine kernel proof. Match what Lean actually says. The footprint check is
#: the real backstop here: a proof that uses `sorry` carries `sorryAx`, which no allowlist admits.
_SORRY_RE = re.compile(r"sorryAx|uses\s+'sorry'|declaration uses sorry", re.IGNORECASE)


def mentions_sorry(text: str) -> bool:
    """True iff ``text`` is Lean REPORTING a hole (not merely containing the letters "sorry")."""
    return bool(_SORRY_RE.search(text or ""))


#: Top-level command keywords. A tactic/term proof is an EXPRESSION; anything here starting a line
#: at column 0 inside `proof_src` is a new top-level declaration, not part of the proof.
_TOP_LEVEL_CMDS = (
    "theorem", "lemma", "def", "abbrev", "example", "instance", "axiom", "axioms",
    "namespace", "end", "section", "open", "import", "structure", "inductive", "class",
    "macro", "macro_rules", "notation", "syntax", "elab", "attribute", "set_option",
    "deriving", "mutual", "universe", "variable", "variables", "private", "protected",
    "noncomputable", "nonrec", "scoped", "local", "partial", "unsafe", "builtin_initialize",
    "initialize", "register_simp_attr", "declare_syntax_cat",
)
_SMUGGLE_RE = re.compile(
    r"^(?:@\[|#\w|(?:" + "|".join(_TOP_LEVEL_CMDS) + r")\b)", re.MULTILINE)


def smuggles_top_level(proof_src: str) -> bool:
    """True iff ``proof_src`` opens a new TOP-LEVEL declaration or command (ADR 0095).

    `propositio.Expressio` claimed the kernel "only ever sees one self-contained declaration ...
    a smuggled top-level command would be a parse error inside the proof". That was false, and it
    was load-bearing: nothing guarded `proof_src`. Lean happily elaborates

        by native_decide

        namespace M
        theorem margin : True := trivial

    as a proof FOLLOWED BY two more commands. The `#print axioms margin` this module appends then
    lands inside the still-open namespace and reports on the decoy `M.margin` — clean, and a
    different declaration. Measured on the pinned 4.31, that returned `kernel_verified=True`,
    `Q.E.D.` from `discharge` AND `ok=True` from `axiom_closure`, and was driven to `False` via
    the Trail of Bits bug. Column 0 is the discriminator: a proof's own continuation lines are
    indented, a new command is not. Comments are stripped first so a commented example cannot
    trip it.
    """
    return bool(_SMUGGLE_RE.search(_strip_comments(proof_src or "")))


def axiom_closure(backend, theorem_src: str, proof_src: str, imports, allowed=STD_AXIOMS,
                  preamble: str = "") -> dict:
    """Elaborate ``<preamble> <theorem_src> := <proof_src>`` and run ``#print axioms``. ok = it
    elaborates with no error AND its axiom footprint contains no ``sorryAx`` and no axiom outside
    ``allowed`` (the standard Lean/Mathlib set). A law that secretly rests on ``sorry``, on
    ``native_decide``, or on an admitted lemma fails here even if the kernel elaborates the
    (open) term. ADR 0062: the WHOLE assembled source — the operator-authored ``preamble`` (defs/
    set_options) included — is elaborated, so a smuggled hole/axiom in the preamble is caught too.
    Read-only: mints nothing, edits no core file."""
    name = declaration_name(theorem_src)
    if not name:
        return {"ok": False, "reason": "no theorem name in theorem_src", "axioms": [],
                "saw_axiom_report": False}
    if smuggles_top_level(proof_src):
        return {"ok": False, "reason": "proof_src opens a top-level declaration", "axioms": [],
                "saw_axiom_report": False}
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
        # LAST report about this name wins: our own `#print axioms` is appended after any the
        # preamble carries. The list comes from the SAME match, never from a neighbouring report.
        last = None
        for m in rep.finditer(data):
            last = m
        if last is None:
            continue
        saw_report = True
        lst = last.group(1)
        axioms = [a.strip() for a in lst.split(",") if a.strip()] if lst is not None else []
    # Scan EVERY message, not just errors: Lean reports `declaration uses 'sorry'` as a WARNING,
    # so an error-only scan was weaker here than `_kernel_ok` (which scans all of them) — an
    # asymmetry that let this check be the laxer of the two it is meant to reinforce.
    has_sorry = "sorryAx" in axioms or any(mentions_sorry(mm.get("data") or "") for mm in msgs)
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


def axiom_report_text(output: Optional[str], name: str, allowed=STD_AXIOMS) -> dict:
    """``axiom_report`` for a backend whose transport yields flat TEXT.

    The CLI backend talks to `lake env lean <file>` and gets stdout, not the REPL's message
    list. ADR 0090 split the analysis out precisely so a second transport reuses the HARDENED
    reader instead of open-coding a fresh scan — the open-coded third copy was the only one
    ever to publish a false record. This wraps the text as a single message so that one reader
    serves both, and marks it error-severity when Lean printed a diagnostic, so a report that
    coexists with an error cannot pass.
    """
    if output is None:
        return {"ok": False, "reason": "no output from lean", "axioms": [], "name": name,
                "saw_axiom_report": False}
    # One message PER LINE, not one message for the whole file. Flattening defeated the ADR 0090
    # per-message name filter: with the entire stdout in a single message, any report naming our
    # theorem anywhere satisfied the filter while the axiom list was read from the first report in
    # the file. Line-splitting restores the invariant the reader was written against, and the
    # atomic capture in `_report_re` makes it robust even if a line ever holds two reports.
    msgs = [{"severity": "error" if "error:" in ln else "info", "data": ln}
            for ln in output.splitlines()] or [{"severity": "info", "data": ""}]
    if "error:" in output and not any(m["severity"] == "error" for m in msgs):
        msgs.append({"severity": "error", "data": output})
    return axiom_report({"messages": msgs}, name, allowed)
