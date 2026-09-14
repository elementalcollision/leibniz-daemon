#!/usr/bin/env python3
"""Audit every RECORDED `Expressio.preamble` for constructs that change what a statement MEANS.

ADR 0062 gave laws an operator-authored definitional preamble and argued that a smuggled hole in
it "fails the honesty gate exactly as one in the proof would". That is true for an **axiom** and
false for a **notation**: measured on the pinned toolchain, `notation "False" => True` lets
`theorem oops : False := trivial` elaborate and report *does not depend on any axioms* -- an EMPTY
closure, cleaner than a legitimate proof by the only measure ADR 0097 applies. ADR 0099 records it.

TWO MECHANISMS, and the distinction is the point:

  1. **The pin is the enforcement.** Every non-empty preamble is hashed and must match a checked-in
     pin in `docs/audits/preamble-pins.json`. A new or altered preamble fails CI until an operator
     regenerates the pins (`--update-pins`), which is a reviewed act. This holds no matter how badly
     the lint below is fooled, because it makes no claim about Lean's grammar at all.

  2. **The lint is an authoring aid.** It catches the common mistake at the moment it is written.
     It is best-effort and it is NOT sound -- an adversarial review of its first version found seven
     working bypasses, every one of which is now a test. Treat a clean lint as "nothing obvious",
     never as "this preamble is safe". What makes a preamble safe is a human reading it before
     pinning it.

Allowlist, not denylist, for the commands the corpus needs -- the ADR 0097 lesson. But note what the
first version got wrong: it scanned by LINE POSITION, and three of the seven bypasses simply indented
a line or put two commands on one. Scanning is by TOKEN here, never by column, and the ADR 0097
round-4 lesson ("Lean parses a command at any column") applies to audits too.

Comments are stripped; string literals are NOT stripped for the keyword scan, so
`def m : String := "open ..."` raises a false finding. Deliberate: a false positive costs a one-line
conversation, a miss is silent. Balance counting DOES strip strings, because an `end` inside a string
literal is not a command and counting it let a preamble fake a closed namespace.

Read-only unless `--update-pins`. Exits non-zero on any finding, so CI can gate on it. See ADR 0099.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))   # so `python scripts/...` resolves the package, as CI invokes it

from leibniz.backends.lean_axioms import (  # noqa: E402  (after the sys.path setup above)
    _skip_string,
    _strip_comments,
    unterminated_block_comment,
)

PINS = ROOT / "docs" / "audits" / "preamble-pins.json"

# Derived from the live corpus census, not guessed at. Extending it is a deliberate act.
ALLOWED_COMMANDS = {"def", "theorem", "lemma", "abbrev", "namespace", "end", "set_option"}

# Lean command keywords that are NOT on the allowlist. A denylist cannot be complete -- that is why
# the pin exists -- but every entry here is one more thing an operator cannot do by accident.
DENIED_COMMANDS = {
    # change what existing syntax means
    "notation", "notation3", "macro", "macro_rules", "syntax", "elab", "elab_rules",
    "infix", "infixl", "infixr", "prefix", "postfix", "binder_predicate", "declare_syntax_cat",
    "unif_hint", "builtin_initialize", "initialize", "run_cmd",
    # change what names resolve to, or what the elaborator does with them
    "open", "export", "attribute", "instance", "scoped", "local", "deriving", "register_simp_attr",
    # introduce scopes the appended theorem can land inside, or assumptions it can use
    "section", "variable", "variables", "universe", "mutual",
    # holes
    "axiom", "opaque", "unsafe", "partial", "sorry", "extern", "implemented_by",
}

# `set_option` reaches the elaborator, so only resource options pass.
ALLOWED_OPTIONS = {"maxHeartbeats", "maxRecDepth", "synthInstance.maxHeartbeats", "maxSynthDepth"}

# Redefining any of these changes the meaning of a statement that mentions it. NOT complete, and
# cannot be made complete by adding names -- the sound check is "declares nothing that already
# resolves", which is the deferred Environment diff. These are the ones that flip a proof outright.
CORE_NAMES = {
    "False", "True", "Not", "And", "Or", "Iff", "Eq", "Ne", "HEq", "Exists",
    "Decidable", "decide", "ite", "dite",
    "Nat", "Int", "Rat", "Bool", "Prop", "List", "Array", "Fin", "Set", "Finset",
}

_COMPONENT = r"(?:«[^»]*»|[A-Za-z_][A-Za-z0-9_'!?]*)"
WORD = re.compile(r"«[^»]*»|[A-Za-z_][A-Za-z0-9_'!?]*")
DECL = re.compile(rf"\b(?:def|abbrev|theorem|lemma)\s+({_COMPONENT}(?:\.{_COMPONENT})*)")
SET_OPTION = re.compile(r"\bset_option\s+([A-Za-z_][A-Za-z0-9_.']*)")

findings: list[tuple[str, str]] = []
checked = 0
clean = 0


def _strip_strings(src: str) -> str:
    """Drop string literals. An `end` inside one is not a command, and counting it faked a close."""
    out, i, n = [], 0, len(src)
    while i < n:
        end = _skip_string(src, i) if src[i] in ('"', "r") else None
        if end is not None:
            i = end
            continue
        out.append(src[i])
        i += 1
    return "".join(out)


def audit(where: str, preamble: str) -> None:
    """Record every construct in `preamble` that could change a statement's meaning."""
    global checked, clean
    checked += 1
    before = len(findings)

    # 0. If our lexer and Lean's have disagreed, nothing below means anything. Fail closed.
    #    `def «z/-» := 1` is ONE identifier to Lean; to the old stripper it opened a comment that
    #    swallowed the rest of the preamble, and the lint reported clean on a notation redefinition.
    if unterminated_block_comment(preamble):
        findings.append((where, "unterminated block comment -- lexer desync, refusing to guess"))
        return

    src = _strip_comments(preamble)
    code = _strip_strings(src)

    # 1. Denied command keywords, scanned as TOKENS anywhere -- never by column, and never
    #    line-anchored. Indentation and two-commands-on-one-line were three of seven bypasses.
    for word in sorted(set(WORD.findall(src))):
        if word in DENIED_COMMANDS:
            findings.append((where, f"denied command `{word}`"))

    # 2. set_option may tune resources; it may not reach the elaborator.
    for opt in sorted(set(SET_OPTION.findall(src))):
        if opt not in ALLOWED_OPTIONS:
            findings.append((where, f"set_option outside the resource allowlist: `{opt}`"))

    # 3. The preamble is PREPENDED to theorem_src. An unclosed `namespace Foo` leaves the theorem
    #    elaborating inside Foo, where a preamble `def False` resolves ahead of core False.
    #    Counted as tokens over string-stripped code: `^\s*namespace` missed a mid-line namespace,
    #    and a literal "end" inside a String supplied a fake close.
    opens = len(re.findall(r"\bnamespace\b", code)) + len(re.findall(r"\bsection\b", code))
    closes = len(re.findall(r"\bend\b", code))
    if opens != closes:
        findings.append((where, f"unbalanced scope: {opens} namespace/section vs {closes} end"))

    # 4. No declaration may take a core name, in any namespace. `«False»` IS the name False.
    for name in sorted(set(DECL.findall(code))):
        base = name.split(".")[-1].strip("«»")
        if base in CORE_NAMES:
            findings.append((where, f"declaration shadows a core name: `{name}`"))

    if len(findings) == before:
        clean += 1


def collect() -> dict[str, str]:
    """Every non-empty recorded preamble in the repo, keyed by `<file>::<json path>`.

    Keyed by PATH, not by file. The first version keyed by file and so kept only the LAST preamble
    it walked into -- measured: a ledger-shaped `{"laws": [{"preamble": <hostile>}, {"preamble":
    <benign>}]}` collapsed to the benign one, and a nested `novelty_attestation.preamble` silently
    overwrote the law's own. Either way the hostile preamble was never linted and never pinned while
    still reaching the kernel, which defeats both mechanisms at once.

    Keyed by path rather than by content hash so that EDITING a preamble keeps its key and shows up
    as a pin mismatch; a content key would make every edit look like a new preamble plus a stale pin.
    """
    found: dict[str, str] = {}

    def walk(where: str, path: str, obj) -> None:
        if isinstance(obj, dict):
            pre = obj.get("preamble")
            if isinstance(pre, str) and pre.strip():
                found[f"{where}::{path or '$'}.preamble"] = pre
            for k, v in obj.items():
                if k != "preamble":
                    walk(where, f"{path}.{k}", v)
        elif isinstance(obj, list):
            for n, v in enumerate(obj):
                walk(where, f"{path}[{n}]", v)

    for p in sorted(ROOT.rglob("*.json")):
        if ".git" in p.parts or "node_modules" in p.parts or p == PINS or not p.is_file():
            continue
        try:
            walk(str(p.relative_to(ROOT)), "", json.loads(p.read_text(encoding="utf-8")))
        except Exception:
            continue                      # not valid JSON -- no preamble to audit
    return found


def digest(preamble: str) -> str:
    return hashlib.sha256(preamble.encode("utf-8")).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--update-pins", action="store_true",
                    help="rewrite the pin manifest to match the corpus (a REVIEWED operator act)")
    args = ap.parse_args()

    corpus = collect()

    if args.update_pins:
        PINS.parent.mkdir(parents=True, exist_ok=True)
        PINS.write_text(json.dumps(
            {"_comment": "ADR 0099. sha256 of each recorded Expressio.preamble. A change here is a "
                         "change to what a published law MEANS -- review the diff, do not rubber-stamp.",
             "pins": {k: digest(v) for k, v in sorted(corpus.items())}},
            indent=2, sort_keys=False) + "\n", encoding="utf-8")
        print(f"pinned {len(corpus)} preamble(s) -> {PINS.relative_to(ROOT)}")
        return 0

    for where, pre in sorted(corpus.items()):
        audit(where, pre)

    # The pin is the enforcement; the lint above is the authoring aid.
    pinned = json.loads(PINS.read_text(encoding="utf-8"))["pins"] if PINS.exists() else {}
    for where, pre in sorted(corpus.items()):
        if where not in pinned:
            findings.append((where, "NOT PINNED -- a new preamble must be reviewed and pinned"))
        elif pinned[where] != digest(pre):
            findings.append((where, "PIN MISMATCH -- this preamble changed since it was reviewed"))
    for where in sorted(set(pinned) - set(corpus)):
        findings.append((where, "stale pin -- pinned preamble no longer present"))

    print(f"preambles checked: {checked}  lint-clean: {clean}  pinned: {len(pinned)}  "
          f"findings: {len(findings)}")
    for where, why in findings:
        print(f"  !! {where}: {why}")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
