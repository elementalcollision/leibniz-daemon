"""ADR 0089 — two guards that could report OK without having checked the thing they name."""
from __future__ import annotations

import ast
import math
import sys

import pytest

from leibniz.backends.lean_axioms import axiom_closure
from leibniz.gates import mixed_modulus_decided as mm

sys.path.insert(0, "tests")
from test_mixed_modulus_decided import COVERING_2520, COVERING_10080  # noqa: E402


class _Repl:
    def __init__(self, messages): self.messages = messages
    def _run(self, src, imports):
        # ADR 0095 round 3: the caller asks about an unpredictable PROBE, not the theorem name --
        # retarget canned reports about OUR theorem onto it. Reports about OTHER declarations are
        # left alone: several tests assert a preamble's report must not become our footprint.
        import re
        mm = re.search(r"def (\S+) := @(\S+)", src or "")
        msgs = self.messages
        if not mm:
            return {"messages": msgs}
        probe, nm = mm.group(1), mm.group(2)
        pat = re.compile(r"'(?:[^']*\.)?" + re.escape(nm)
                         + r"'(\s*(?:depends on axioms:|does not depend on any axioms))")
        return {"messages": [{**x, "data": pat.sub(lambda g: f"'{probe}'" + g.group(1),
                                                   x.get("data") or "")} for x in msgs]}


def _info(data): return {"severity": "info", "data": data}


# --- Decision 1: axiom_closure must have seen a report about OUR theorem -------------------------

def test_silent_repl_no_longer_passes_a_false_theorem():
    """The defect: `ok` was `not errors and not has_sorry and not extra`, all vacuous on an empty
    message list. A REPL answering {"messages": []} returned ok=True for a FALSE theorem proved
    `by sorry` — and `decide_certificate` gates every leg on this."""
    r = axiom_closure(_Repl([]), "theorem bogus : 1 = 2", "by sorry", ("Mathlib",))
    assert r["ok"] is False
    assert r["saw_axiom_report"] is False


def test_axiom_free_proof_still_passes():
    """The trap in the obvious fix. Lean prints `'t' does not depend on any axioms` for a proof
    with an empty footprint (verified against live Lean 4.31: `theorem t : 1 + 1 = 2 := rfl`), and
    that form matches no axiom list. Requiring a non-empty `axioms` list would false-DEFER every
    axiom-free proof."""
    r = axiom_closure(_Repl([_info("'t' does not depend on any axioms")]), "theorem t : 1 = 1", "rfl", ())
    assert r["ok"] is True and r["axioms"] == [] and r["saw_axiom_report"] is True


def test_report_about_a_different_declaration_does_not_count():
    """The report must name OUR theorem, so one about another declaration — e.g. something the
    operator-authored preamble elaborated (ADR 0062) — cannot stand in for it."""
    r = axiom_closure(_Repl([_info("'other' depends on axioms: [propext]")]), "theorem t : 1 = 1", "rfl", ())
    assert r["ok"] is False and r["saw_axiom_report"] is False


def test_normal_and_sorry_footprints_unchanged():
    ok = axiom_closure(_Repl([_info("'t' depends on axioms: [propext, Classical.choice, Quot.sound]")]),
                       "theorem t : 1 = 1", "rfl", ())
    assert ok["ok"] is True and ok["axioms"] == ["propext", "Classical.choice", "Quot.sound"]
    bad = axiom_closure(_Repl([_info("'t' depends on axioms: [sorryAx]")]), "theorem t : 1 = 1", "by sorry", ())
    assert bad["ok"] is False and bad["has_sorry"] is True
    extra = axiom_closure(_Repl([_info("'t' depends on axioms: [Lean.ofReduceBool]")]),
                          "theorem t : 1 = 1", "by native_decide", ())
    assert extra["ok"] is False and extra["extra_axioms"] == ["Lean.ofReduceBool"]


# --- Decision 2: content-free by construction, and what the criterion is NOT ----------------------

def _flat(system):
    return [("eq", ast.Name(id="n", ctx=ast.Load()), m, c) for m, c in system]


PADDED = ("(n % 4 == 0) or (n % 4 == 1) or (n % 4 == 2) or (n % 4 == 3) or (n % 9 == 0) "
          "or (n % 9 == 1) or (n % 9 == 2) or (n % 6 == 5) or (n % 8 == 7) or (n % 12 == 11)")


def test_full_residue_block_is_refused():
    """Modulus 4 appears with all four residues: the formula restates "every integer has some
    residue mod 4", padded with filler. True, so the kernel accepts it; it would promulgate as a
    law with no content. Propositionally non-constant, so no earlier guard saw it."""
    assert mm.classify_mixed(PADDED) is None
    assert mm._padded_covering(_flat([(4, 0), (4, 1), (4, 2), (4, 3), (9, 0)])) is True


def test_the_criterion_is_NOT_redundancy_and_the_paper_proves_why():
    """ADR 0089 first specified "reject when a proper subset already covers ℤ". Testing that
    against the system it exists to admit refuted it: arXiv 2607.19029 §7 contains a REDUNDANT
    congruence — drop `233 (mod 1120)` and the remaining 65 still cover ℤ with distinct moduli,
    minimum modulus 7 and lcm 10080. Not an error in the paper, whose theorem is about the minimal
    LCM and not about the witness being irredundant — but it means redundancy does not imply
    absence of content, and that criterion would have rejected the target of the whole exercise."""
    M = 10080
    count = [0] * M
    for m, c in COVERING_10080:
        for x in range(c % m, M, m):
            count[x] += 1
    assert all(count)                                   # it does cover
    redundant = [(m, c) for m, c in COVERING_10080 if all(count[x] >= 2 for x in range(c % m, M, m))]
    assert redundant == [(1120, 233)]                   # exactly one, and this is why
    drop = [(m, c) for m, c in COVERING_10080 if (m, c) != (1120, 233)]
    hit = [False] * M
    for m, c in drop:
        for x in range(c % m, M, m):
            hit[x] = True
    assert all(hit) and len({m for m, _ in drop}) == 65 and math.lcm(*[m for m, _ in drop]) == 10080

    # ...and the landed criterion admits it anyway, because no modulus carries a full residue set
    assert mm._padded_covering(_flat(COVERING_10080)) is False
    assert mm._padded_covering(_flat(COVERING_2520)) is False


def test_criterion_cannot_fire_on_a_distinct_covering_system():
    """A full residue block needs a modulus repeated m times, so it cannot occur where the moduli
    are distinct — precisely the property the redundancy test lacked."""
    assert len({m for m, _ in COVERING_10080}) == len(COVERING_10080)
    assert mm._padded_covering(_flat(COVERING_10080)) is False


@pytest.mark.parametrize("flat", [
    [("neq", ast.Name(id="n", ctx=ast.Load()), 4, 0), ("eq", ast.Name(id="n", ctx=ast.Load()), 4, 1)],
    [("eq", ast.Name(id="a", ctx=ast.Load()), 4, 0), ("eq", ast.Name(id="b", ctx=ast.Load()), 4, 1)],
    [("eq", ast.BinOp(left=ast.Name(id="n", ctx=ast.Load()), op=ast.Add(),
                      right=ast.Constant(value=1)), 4, 0)],
])
def test_out_of_scope_shapes_keep_the_propositional_verdict(flat):
    """Only all-`==` atoms over one bare variable. Elsewhere coverage is not the right question and
    guessing at it would be a new way to be wrong."""
    assert mm._padded_covering(flat) is False


def test_minimal_covering_systems_still_classify():
    assert mm.classify_mixed("(n % 2 == 0) or (n % 4 == 1) or (n % 4 == 3)") is not None
    assert mm.classify_mixed(" or ".join(f"(n % {m} == {c})" for m, c in COVERING_2520)) is not None


# --- ADR 0089 adversarial review: five defects in the first implementation -----------------------

def test_publish_gate_uses_the_shared_axiom_closure():
    """DEFECT 1. `lean_axioms`'s docstring says it exists so faithfulness-time and publish-time run
    "the SAME code ... not two drifting copies". They HAD drifted: hardening the library copy left
    `scripts/export_calculemus.py`'s own copy — `check_ledger`'s H0 gate for the ADR 0033 publish
    act — still printing VERIFIED for a false theorem proved `by sorry` against a silent REPL. The
    duplicate is deleted, not patched, so it cannot drift again."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("expcal", "scripts/export_calculemus.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    assert m.axiom_closure.__module__ == "leibniz.backends.lean_axioms"
    assert m.axiom_closure(_Repl([]), "theorem bogus : 1 = 2", "by sorry", ("Mathlib",))["ok"] is False


@pytest.mark.parametrize("src", [
    "(n % 2 == 0) or (n % 2 == 1) or (n % 3 == 0)",                                     # 3 atoms
    "(n % 3 == 0) or (n % 3 == 1) or (n % 3 == 2) or (n % 5 == 4)",                     # 4
    "(n % 4 == 0) or (n % 4 == 1) or (n % 4 == 2) or (n % 4 == 3) or (n % 9 == 0)",     # 5
    ("(n % 4 == 0) or (n % 4 == 1) or (n % 4 == 2) or (n % 4 == 3) or (n % 9 == 0) "
     "or (n % 9 == 1) or (n % 9 == 2) or (n % 9 == 3)"),                                # 8
    PADDED,                                                                             # 10
])
def test_full_residue_block_refused_at_every_atom_count(src):
    """DEFECT 2. The check first ran only in the >8-atom branch, so the ADR's own example family
    classified at 3-8 atoms — the sizes the conjecturer most often emits — while
    `boolean_decided` refuses the same shape on a single modulus. The mixed gate was laxer than
    its sibling on the pathology it had just been hardened against. The check is O(k) and sound at
    any size, so it now runs at every atom count."""
    assert mm.classify_mixed(src) is None


def test_full_block_cannot_be_evaded_by_appending_a_neq_atom():
    """DEFECT 3. Requiring EVERY atom to be `==` made the guard evadable with one unrelated `!=`.
    A complete residue system among the `==` atoms is a tautology over Z whatever else is OR'd in."""
    evade = (PADDED.rsplit(" or ", 1)[0] + " or (n % 25 != 24)")
    assert mm.classify_mixed(evade) is None


def test_namespaced_report_is_not_a_false_defer():
    """DEFECT 4. Lean may print the FULLY QUALIFIED name while the source declares the short one
    (`docs/results/prob16_census.json` records `'SO_cube.cube_not_self_ordered'` for a law whose
    preamble opens `namespace SO_cube`). An ADR 0062 preamble opening a namespace must NOT turn a
    clean footprint into a silent DEFER, so the qualifier is allowed.

    ADR 0095 round 3 restored this to its original form. An intermediate version tried to police
    WHICH qualifiers were acceptable; that check turned out to be the last step of an exploit
    rather than a defence, because rejecting Lean's genuine namespaced report left a report the
    PROOF had printed as the only accepted one. Authentication now comes from asking about an
    unpredictable probe name instead, which makes the qualifier irrelevant.
    """
    r = axiom_closure(_Repl([_info("'Foo.t' depends on axioms: [propext]")]),
                      "theorem t : 1 = 1", "rfl", ())
    assert r["ok"] is True and r["axioms"] == ["propext"]


def test_preamble_report_does_not_become_our_footprint():
    """The footprint is read only from the report about OUR theorem. 16 of the docs/crt/*.lean
    artifacts carry their own `#print axioms`, and steiner/double_blocking ride in as
    whole-artifact preambles, so a name-blind scan could hand back the preamble's list."""
    r = axiom_closure(_Repl([_info("'preamble_lemma' depends on axioms: [propext, Classical.choice]"),
                             _info("'t' does not depend on any axioms")]),
                      "theorem t : 1 = 1", "rfl", ())
    assert r["ok"] is True and r["axioms"] == []          # ours, not the preamble's
    only_preamble = axiom_closure(_Repl([_info("'preamble_lemma' depends on axioms: [propext]")]),
                                  "theorem t : 1 = 1", "rfl", ())
    assert only_preamble["ok"] is False


def test_sorry_reported_as_a_warning_is_caught():
    """DEFECT 5's root asymmetry: Lean reports `declaration uses 'sorry'` as a WARNING, and
    `has_sorry` scanned only errors while `_kernel_ok` scans every message — making this check the
    laxer of the two it is meant to reinforce."""
    r = axiom_closure(_Repl([{"severity": "warning", "data": "declaration uses 'sorry'"},
                             _info("'t' depends on axioms: [propext]")]),
                      "theorem t : 1 = 1", "by sorry", ())
    assert r["ok"] is False and r["has_sorry"] is True
