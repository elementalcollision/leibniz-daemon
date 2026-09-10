"""Shared axiom-closure check (H0), lifted from ``scripts/export_calculemus.py`` so the
faithfulness-time re-check (ADR 0056 Track A increment 2, build obligation 3) and the
publish-time ledger check run the SAME code — a proof accepted at faithfulness time and a
proof accepted at export time face one axiom discipline, not two drifting copies.

A kernel-accepted declaration may still rest on `sorryAx` (a hole) or on native computation
(``native_decide`` — trusting the compiled evaluator, not the kernel) or a project-admitted
axiom. `#print axioms <name>` reports the footprint; ``axiom_closure`` asserts it is a
subset of the standard Lean/Mathlib set. Anything else ⇒ not a proof for our purposes.

ADR 0095 rebuilt the plumbing here after two rounds of adversarial review. The reader must
survive three things that all turned out to be live on the pinned 4.31: a name read from
somewhere other than the real declaration, a report about some OTHER declaration standing in
for ours, and a transport that re-shapes Lean's output badly enough to change the verdict.
"""
from __future__ import annotations

import re
from typing import Optional

# The standard Lean/Mathlib axioms. NOTE native computation is deliberately NOT in this set: a
# "proof" by compiled evaluation is trusted-compiler, not kernel-decided. Since Lean 4.29 it is
# spelled `<theorem>._native.native_decide.ax_1` (leanprover/lean4#12216), not
# `Lean.ofReduceBool` — which is exactly why this is an ALLOWLIST and never a denylist.
STD_AXIOMS = frozenset({"propext", "Classical.choice", "Quot.sound"})

#: Lean 4.31 tags some diagnostics: `error(lean.unknownIdentifier): ...` as well as plain
#: `error: ...`. A literal `"error:" in output` test misses the tagged form.
_ERROR_RE = re.compile(r"\berror(?::|\()")

# --- naming the declaration --------------------------------------------------

#: ADR 0095 — the name must come from a real DECLARATION, not from anywhere in the text.
#: The original `_NAME_RE.search` took the first `theorem <name>` match anywhere, comments
#: included, and that name is what `#print axioms` is asked about. A `theorem_src` opening with
#:     -- theorem Nat.add_comm
#: made both `axiom_closure` and the backends report the footprint of MATHLIB's `Nat.add_comm`
#: — clean, and about a different declaration entirely — while the real theorem was proved by
#: `native_decide`. Measured on the pinned 4.31: `kernel_verified=True`, `Q.E.D.`, and
#: `axiom_closure(...)["ok"] is True`. `theorem_src` is proposer-authored, so this was reachable.
#:
#: `«guillemet names»` are captured whole; `set_option ... in` / `open ... in` may precede the
#: keyword (Lean accepts them on one line, and `gates/mixed_modulus_decided.py` emits that form);
#: whitespace including a NEWLINE may separate the keyword from the name.
_DECL_RE = re.compile(
    r"^[ \t]*(?:(?:set_option|open)[ \t]+[^\n]*?\bin\b[ \t]*)*"
    r"(?:@\[[^\]]*\][ \t\n]*)*"
    r"(?:(?:private|protected|noncomputable|scoped|local|nonrec|unsafe|partial)[ \t]+)*"
    r"(?:theorem|lemma)\s+(«[^»]+»|[^\s({\[:]+)", re.MULTILINE)

#: Namespaces opened by the OPERATOR-AUTHORED preamble (ADR 0062). Used to work out which
#: qualified forms of our name Lean may legitimately report — see `expected_report_names`.
_NS_RE = re.compile(r"^[ \t]*namespace[ \t]+([^\s]+)", re.MULTILINE)


def _strip_comments(src: str) -> str:
    """Remove Lean line (`--`) and block (`/- -/`, nesting) comments, respecting STRING LITERALS.

    ADR 0095 round 2: lexing `/-` without tracking string literals is itself an attack surface.
    A proof containing `have s : String := "/-"` opened a block comment that never closed, so the
    stripper swallowed the rest of the proof and `smuggles_top_level` saw nothing — while Lean,
    which lexes the string correctly, happily elaborated the `namespace M` / decoy that followed.
    Over-stripping is otherwise the safe direction (a lost name fails CLOSED), but silently
    discarding the text a GUARD is about to scan is not.
    """
    out: list[str] = []
    i, depth, n = 0, 0, len(src)
    in_str = False
    while i < n:
        c = src[i]
        if in_str:
            out.append(c)
            if c == "\\" and i + 1 < n:      # escaped char: copy both, never re-examine
                out.append(src[i + 1])
                i += 2
                continue
            if c == '"':
                in_str = False
            i += 1
        elif depth:
            if src.startswith("/-", i):
                depth += 1
                i += 2
            elif src.startswith("-/", i):
                depth -= 1
                i += 2
            else:
                i += 1
        elif src.startswith("/-", i):
            depth += 1
            i += 2
        elif src.startswith("--", i):
            j = src.find("\n", i)
            i = n if j < 0 else j
        elif c == '"':
            in_str = True
            out.append(c)
            i += 1
        else:
            out.append(c)
            i += 1
    return "".join(out)


def declaration_name(theorem_src: str) -> Optional[str]:
    """The name of the declaration ``theorem_src`` actually declares, or None (fail closed)."""
    m = _DECL_RE.search(_strip_comments(theorem_src))
    if not m:
        return None
    # `theorem upoly.{u} ...` — the char class stops at `{` and leaves a trailing dot, and
    # `#print axioms upoly.` is a syntax error (a silent DEFER on an honest proof). Lean names
    # never end in a dot, so trimming one is safe.
    return m.group(1).rstrip(".") or None


def expected_report_names(name: str, preamble: str = "") -> frozenset:
    """The reported names that may legitimately stand for our declaration.

    ADR 0095 round 2, and the structural half of the decoy fix. `_report_re` allows an optional
    qualifier because an ADR 0062 preamble may open a namespace, so Lean reports
    `'Ns.thm'` for a theorem the source calls `thm` — without that allowance every namespaced
    preamble would silently DEFER. But "any qualifier" also accepts `'M.thm'` for a decoy the
    PROOF declared in a namespace of its own, which is how round 1's exploit stood up a clean
    report for a dirty theorem.

    The preamble is operator-authored and trusted; `proof_src` is not. So the qualifiers we accept
    are exactly the ones the preamble could have introduced. Anything else is a different
    declaration wearing our name.
    """
    names = {name}
    parts = _NS_RE.findall(_strip_comments(preamble or ""))
    for i in range(len(parts)):
        names.add(".".join(parts[: i + 1]) + "." + name)
        names.add(parts[i] + "." + name)
    return frozenset(names)


def _name_acceptable(reported: str, name: str, expected: Optional[frozenset]) -> bool:
    """Is a `#print axioms` report about ``reported`` a report about OUR declaration?"""
    if expected is None:
        return True                                   # caller opted out (legacy callers)
    if reported in expected:
        return True
    # Lean mangles a `private theorem` as `_private.<Module>.<n>.<name>`. The prefix comes from
    # Lean's module system, not from any user-supplied text, so it cannot be spoofed by a proof.
    return reported.startswith("_private.") and reported.endswith("." + name)


# --- reading the report ------------------------------------------------------

#: ADR 0089 — positive evidence that `#print axioms` actually REPORTED on our theorem. Lean emits
#: one of two forms, and the second matches no axiom list at all:
#:     'foo' depends on axioms: [propext, Classical.choice, Quot.sound]
#:     'foo' does not depend on any axioms
#: Requiring a non-empty `axioms` list would therefore false-DEFER every axiom-free proof (verified
#: against live Lean 4.31: `theorem t : 1 + 1 = 2 := rfl` prints the second form). Both forms count.
def _report_re(name: str):
    """Match a `#print axioms` report about ``name``, capturing the REPORTED NAME and its list.

    ADR 0095: these used to be two independent searches — one found the report, a separate
    axiom-list regex then found "an" axiom list in the same message. That decoupling is only safe
    while one message holds exactly one report, and the CLI transport holds the WHOLE FILE, so
    the second search returned whichever list was printed FIRST: an ADR 0062 preamble carrying its
    own `#print axioms` (16 of the `docs/crt/*.lean` artifacts do) handed its clean list to a
    dirty theorem, with no adversary involved. Capturing name and list in ONE match ties them
    together and no neighbouring report can prise them apart.

    `[^\\]]*` spans newlines by construction, which matters: Lean's pretty-printer BREAKS a long
    axiom list across lines (measured: a 3-axiom footprint wraps once the theorem name reaches 60
    characters, and a native-axiom footprint at 15), and `set_option format.width` does not
    suppress it. Group 1 is the reported name; group 2 is the axiom list, or None for the
    axiom-free form.
    """
    return re.compile(r"'((?:[^']*\.)?" + re.escape(name)
                      + r")'\s*(?:depends on axioms:\s*\[([^\]]*)\]"
                      + r"|does not depend on any axioms)")


def mentions_sorry(text: str, ignore=None) -> bool:
    """True iff ``text`` looks like Lean reporting a hole. BROAD by design.

    ADR 0095 round 2 — this was briefly narrowed to Lean's warning wording and that was a
    material regression. Lean writes the warning with BACKTICKS (``declaration uses `sorry` ``,
    verified on 4.31.0, 4.33.1 and 4.34.0-rc2), so the narrowed regex matched nothing at all and
    `LeanCliBackend.check_source("theorem t : 2 + 2 = 5 := by sorry")` started returning **True**
    — on the path ~20 audit scripts call "the trusted re-check", which has no footprint backstop.

    So the scan stays broad. The false-DEFER it was narrowed to fix had one cause: appending
    `#print axioms <name>` echoes the declaration's NAME back, so a theorem named
    `sorry_free_addition` looked like a hole. ``ignore`` (the report regex) removes exactly that
    echo and nothing else. `sorryAx` is tested BEFORE the removal, so a hole named in the
    footprint is still caught.
    """
    t = text or ""
    if "sorryax" in t.lower():
        return True
    if ignore is not None:
        t = ignore.sub(" ", t)
    return "sorry" in t.lower()


# --- guarding the proof ------------------------------------------------------

#: Top-level command keywords. A tactic/term proof is an EXPRESSION; any of these opening a line
#: inside `proof_src` is a new top-level declaration, not part of the proof.
_TOP_LEVEL_CMDS = (
    "theorem", "lemma", "def", "abbrev", "example", "instance", "axiom", "axioms",
    "namespace", "end", "section", "open", "import", "structure", "inductive", "class",
    "macro", "macro_rules", "notation", "syntax", "elab", "attribute", "set_option",
    "deriving", "mutual", "universe", "variable", "variables", "private", "protected",
    "noncomputable", "nonrec", "scoped", "local", "partial", "unsafe", "builtin_initialize",
    "initialize", "register_simp_attr", "declare_syntax_cat",
)
#: Leading whitespace is ALLOWED before the keyword — see `smuggles_top_level`.
_SMUGGLE_RE = re.compile(
    r"^[ \t]*(?:@\[|#\w|(?:" + "|".join(_TOP_LEVEL_CMDS) + r")\b)", re.MULTILINE)
#: `set_option x in` / `open X in` are TERM MODIFIERS, not new declarations, and honest proofs
#: use them (`gates/mixed_modulus_decided.py` emits `set_option ... in`). Recognised by the
#: trailing `in` on the same line.
_MODIFIER_RE = re.compile(r"^[ \t]*(?:set_option|open)\b[^\n]*\bin\b", re.MULTILINE)


def smuggles_top_level(proof_src: str) -> bool:
    """True iff ``proof_src`` opens a new TOP-LEVEL declaration or command (ADR 0095).

    `propositio.Expressio` claimed the kernel "only ever sees one self-contained declaration ...
    a smuggled top-level command would be a parse error inside the proof". That was false, and it
    was load-bearing: nothing guarded `proof_src`. Lean happily elaborates

        by native_decide

        namespace M
        theorem margin : True := trivial

    as a proof FOLLOWED BY two more commands. The `#print axioms margin` appended afterwards then
    lands inside the still-open namespace and reports on the decoy `M.margin` — clean, and a
    different declaration. Measured on the pinned 4.31: `kernel_verified=True`, `Q.E.D.` from
    `discharge` AND `ok=True` from `axiom_closure`, driven to `False` via the Trail of Bits bug.

    Round 2 then showed the first version of this guard was a COLUMN-0 scan, and that its stated
    rationale ("a proof's own continuation lines are indented, a new command is not") was simply
    wrong: Lean parses a command at any column, so one leading space walked straight past it.
    Leading whitespace is now allowed.

    This is defence in depth, not the load-bearing check — a keyword scan cannot be complete.
    `expected_report_names` is what structurally prevents a decoy report from standing in for
    ours, whatever syntax introduced it.
    """
    src = _strip_comments(proof_src or "")
    modifiers = {m.start() for m in _MODIFIER_RE.finditer(src)}
    return any(m.start() not in modifiers for m in _SMUGGLE_RE.finditer(src))


# --- the two entry points ----------------------------------------------------

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
    return axiom_report(backend._run(src, tuple(imports)), name, allowed,
                        expected_report_names(name, preamble))


def axiom_report(response, name: str, allowed=STD_AXIOMS, expected=None) -> dict:
    """Analyse ONE REPL response for the axiom footprint of declaration ``name``.

    Split out of ``axiom_closure`` (ADR 0090) so a caller that assembles its OWN Lean source —
    ``scripts/counterexample_domain.py`` emits whole namespaced certs, which cannot be split into
    the ``theorem_src``/``proof_src`` shape without re-writing the Lean — shares the HARDENED
    analysis instead of open-coding a fresh one. That script's open-coded scan was the third copy
    of this logic and the only one to publish a false record: its ``(r or {})`` turned a dead-REPL
    ``None`` into ``ok=True``, and ``docs/results/counterexample_domain.json`` recorded GREEN /
    ``kernel.status: checked`` for certificates whose Mathlib import does not exist in the pinned
    image and which therefore were never elaborated at all.

    ``ok`` requires ALL of: a response at all; no error message; no ``sorry`` outside the
    `#print axioms` echo; every axiom inside ``allowed``; and a report that names this declaration
    — without that last clause an empty message list satisfies the rest vacuously, which is the
    ADR 0089 fail-open.

    ``expected`` (ADR 0095) is the set of reported names that may stand for ours, from
    ``expected_report_names``. Pass it whenever the preamble is known; a report about any other
    declaration is then rejected rather than accepted on a suffix match.
    """
    if response is None:
        return {"ok": False, "reason": "no response from REPL", "axioms": [], "name": name,
                "saw_axiom_report": False}
    msgs = response.get("messages", []) or []
    errors = [(mm.get("data") or "") for mm in msgs if mm.get("severity") == "error"]
    # Read the footprint ONLY from the report about our own declaration. An ADR 0062 preamble may
    # carry its own `#print axioms`, so a name-blind scan could hand back the preamble's list for
    # our theorem — including for an axiom-free one.
    rep = _report_re(name)
    axioms: list = []
    saw_report = False
    rejected: list = []
    for mm in msgs:
        data = mm.get("data") or ""
        # LAST report about this name wins: our own `#print axioms` is appended after any the
        # preamble carries. The list comes from the SAME match, never from a neighbouring report.
        for m in rep.finditer(data):
            if not _name_acceptable(m.group(1), name, expected):
                rejected.append(m.group(1))
                continue
            saw_report = True
            lst = m.group(2)
            axioms = [a.strip() for a in lst.split(",") if a.strip()] if lst is not None else []
    # Scan EVERY message, not just errors: Lean reports a hole as a WARNING, so an error-only scan
    # would be weaker here than `_kernel_ok` (which scans all of them) — an asymmetry that once let
    # this check be the laxer of the two it is meant to reinforce. `rep` is excluded from the scan
    # because `#print axioms <name>` echoes the NAME, which is not evidence of a hole.
    has_sorry = "sorryAx" in axioms or any(
        mentions_sorry(mm.get("data") or "", ignore=rep) for mm in msgs)
    extra = [a for a in axioms if a not in allowed]
    # ADR 0089 — this function exists to READ the axiom footprint, so it must not pass without
    # having seen one. Before this check `ok` was `not errors and not has_sorry and not extra`,
    # all three of which a response with NO messages satisfies vacuously: a REPL answering
    # `{"messages": []}` returned ok=True for a FALSE theorem proved `by sorry`, and since
    # `decide_certificate` gates every leg on this, that is the whole faithfulness certificate.
    ok = bool(not errors and not has_sorry and not extra and saw_report)
    return {"ok": ok, "axioms": axioms, "saw_axiom_report": saw_report,
            "extra_axioms": extra, "has_sorry": has_sorry, "errors": errors[:2], "name": name,
            "rejected_reports": rejected}


def axiom_report_text(output: Optional[str], name: str, allowed=STD_AXIOMS, expected=None) -> dict:
    """``axiom_report`` for a backend whose transport yields flat TEXT.

    The CLI backend talks to `lake env lean <file>` and gets stdout, not the REPL's message list.
    ADR 0090 split the analysis out precisely so a second transport reuses the HARDENED reader
    instead of open-coding a fresh scan — the open-coded third copy was the only one ever to
    publish a false record.

    The text is passed as ONE message on purpose. Round 2 of the ADR 0095 review killed the
    obvious alternative: splitting per line looks safer, but Lean WRAPS a long axiom list across
    lines, so a per-line reader saw a report with no list and a list with no report. That made the
    two transports disagree on identical content in both directions — an honest 62-character-named
    proof got `Q.E.D.` from the REPL and `Q.E.I.` from the CLI, and a wrapped dirty footprint could
    lose to an earlier one-line report about the same short name. Keeping the blob intact is safe
    because `_report_re` captures the name and its list in a single match and spans newlines.
    """
    if output is None:
        return {"ok": False, "reason": "no output from lean", "axioms": [], "name": name,
                "saw_axiom_report": False}
    severity = "error" if _ERROR_RE.search(output) else "info"
    return axiom_report({"messages": [{"severity": severity, "data": output}]},
                        name, allowed, expected)
