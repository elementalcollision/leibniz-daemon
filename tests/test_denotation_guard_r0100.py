"""ADR 0100 -- the mint reads what the statement MEANS, not just what it costs in axioms.

`notation "False" => True` lets `theorem oops : False := trivial` elaborate reporting NO axioms at
all -- an EMPTY closure, cleaner than a legitimate proof by the only measure ADR 0097 applies. The
kernel is not wrong: it proved exactly the proposition it was handed. What changed is which
proposition that was.

Measured on `leanprover/lean4:v4.34.0-rc2`, the live attack surface is exactly two classes:

  * SYNTAX redefinition -- `notation`, `local notation`, `scoped notation` + `open`, `macro_rules`.
    All four make the statement's elaborated type literally the constant `True`.
  * SHADOWING through an UNCLOSED scope -- `def`/`abbrev`/`«False»`/`Nat` inside a `namespace` with
    no `end`. All four declare `Foo.oops` instead of `oops`.

Everything else tried is refused by LEAN ITSELF: `open`/`export`/`open ... in` after a closed
namespace give "Ambiguous term", a root `def False` is "already been declared", `variable (h :
False)` and an unclosed `section` give "unknown identifier". Lean does not silently prefer a
shadowing name; it refuses the ambiguity. That is why the scope check is sufficient for the
shadowing class rather than merely necessary.

These are the PARSER tests -- fast, no Docker. The end-to-end mint tests live in the kernel lane.
"""
from __future__ import annotations

import pytest

from leibniz.backends.lean_axioms import _parse_axcheck

N = "leibniz_axiom_probe_deadbeefdeadbeefdeadbeefdeadbeef"


def _report(axioms="[propext]", root="OK good", shadow="[]", denote="[Eq, Nat]",
            vacuous="no", decls=2):
    lines = [f"{N} AXIOMS {decls} {axioms}"]
    if root is not None:
        lines.append(f"{N} ROOT {root}")
    if shadow is not None:
        lines.append(f"{N} SHADOW {shadow}")
    if denote is not None:
        lines.append(f"{N} DENOTE {denote}")
    if vacuous is not None:
        lines.append(f"{N} VACUOUS {vacuous}")
    return "\n".join(lines)


def test_honest_report_passes():
    r = _parse_axcheck(_report(), N)
    assert r["ok"] is True
    assert r["root_ok"] is True and r["vacuous"] is False
    assert r["denotation"] == "Eq, Nat"


def test_shadowing_refused_when_the_statement_names_a_shadowing_constant():
    """Inside an open `namespace Foo`, a preamble `def False` resolves ahead of core `False`."""
    r = _parse_axcheck(_report(root="NESTED Foo.oops", shadow="[Foo.False]",
                               denote=None, vacuous=None), N)
    assert r["ok"] is False
    assert "Foo.False" in r["reason"] and r["shadowed"] == ["Foo.False"]


def test_a_nested_landing_alone_is_HONEST_and_must_not_be_refused():
    """Round 6 pinned `namespace LeibNS` (never closed) as an honest operator shape. Refusing every
    nested landing would drop real proofs -- a guard that does that is a defect even though it
    fails closed, which is the whole point of the round-6 regression set."""
    r = _parse_axcheck(_report(root="NESTED LeibNS.inns"), N)
    assert r["ok"] is True and r["nested"] is True


def test_declaration_absent_fails_closed():
    """A wrong expected name reads as 'absent' and REFUSES -- this is why reintroducing the name
    is safe where round 7's mis-aimable probe was not: that one reported cleanly on a decoy."""
    r = _parse_axcheck(_report(root="MISSING oops", shadow=None, denote=None, vacuous=None), N)
    assert r["ok"] is False and r["root_ok"] is False


def test_vacuous_statement_refused():
    """Every measured syntax attack collapses to this: the statement's type IS `True`."""
    r = _parse_axcheck(_report(axioms="[]", root="OK oops", denote="[True]", vacuous="yes"), N)
    assert r["ok"] is False
    assert "True" in r["reason"]


def test_empty_axiom_closure_is_not_a_pass_on_its_own():
    """The attack's closure is EMPTY -- cleaner than an honest proof. Axioms alone cannot see it."""
    r = _parse_axcheck(_report(axioms="[]", root="OK oops", denote="[True]", vacuous="yes"), N)
    assert r["axioms"] == [] and r["extra_axioms"] == []
    assert r["ok"] is False, "an empty closure must not carry the verdict by itself"


@pytest.mark.parametrize("missing", ["root", "shadow", "vacuous"],
                         ids=["no-ROOT-line", "no-SHADOW-line", "no-VACUOUS-line"])
def test_stale_reporter_image_fails_closed(missing):
    """A reporter that answers only the axiom question must NOT read as a pass. An image built
    before ADR 0100 emits no ROOT/VACUOUS line, and silently accepting that would reintroduce the
    whole class the moment someone ran an old image -- the ADR 0093 'a lane that cannot run must
    say so' shape, applied to a check rather than a lane."""
    kw = {missing: None}
    r = _parse_axcheck(_report(**kw), N)
    assert r["ok"] is False
    assert "stale image" in r["reason"]


def test_lines_from_a_different_nonce_are_ignored():
    """The nonce is chosen after the proposer's text is fixed; a forged line cannot carry it."""
    forged = ("OTHER ROOT OK oops\nOTHER SHADOW []\nOTHER VACUOUS no\n"
              + _report(root="MISSING oops", shadow=None, denote=None, vacuous=None))
    r = _parse_axcheck(forged, N)
    assert r["ok"] is False, "a report under another nonce must not satisfy the ROOT check"


def test_axiom_verdict_still_governs():
    """ADR 0100 ADDS a question; it must not weaken the ADR 0097 one."""
    r = _parse_axcheck(_report(axioms="[propext, sorryAx]"), N)
    assert r["ok"] is False and r["has_sorry"] is True
