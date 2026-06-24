"""ADR 0032 follow-up — loose-phrasing canonicalization of modular-congruence claims.

The structural novelty matcher used to canonicalize ONLY the tight `P % m == r` shape; loosely
phrased RESTATEMENTS (`P % m ∈ {…}`, `or`-disjunctions, vacuous offsets, `!=`) dodged the gate and
came back false-NOVEL. `congruence_signature` now folds those shapes onto a signature keyed on the
polynomial's reduced FORM plus its COMPUTED residue set `R = { P(n) % m }` (exact over one period),
never on the residues the author asserted and NEVER on truth.

This suite has two halves:
  (i)  SHOULD-MATCH — restatement/loose pairs that denote the SAME congruence collapse to one sig;
  (ii) MUST-NOT-MATCH — the LOAD-BEARING guards: genuinely DIFFERENT modular facts get DIFFERENT
       signatures (no false-KNOWN — the unsoundness that retracted ADR 0031 L2). This half is made
       deliberately thorough: distinct polynomials, distinct moduli, distinct residue sets, unit
       multiples in the multi-residue branch, and a cross-product property check against an
       independent canonical form.

Pure stdlib; no Z3, no Lean, no corpus needed for the unit half. The gate end-to-end is exercised
at the bottom against the real corpus with a fake Lean (CI-safe).
"""
from __future__ import annotations

import ast

from leibniz.structural import (
    RESIDUE_BOUND,
    _disjunction_residues,
    _expand,
    _mod,
    _mono_degree,
    _residue_set,
    _residues_from_node,
)
from leibniz.structural import congruence_signature as sig

# ---------------------------------------------------------------------------------------------
# (i) SHOULD-MATCH — loose restatements collapse to the SAME signature as their tight form.
# ---------------------------------------------------------------------------------------------


def test_set_membership_with_singleton_actual_residue_matches_equality():
    # `P % m ∈ {0,4}` whose ACTUAL residues are {0} is the congruence `P ≡ 0 (mod m)`, so it folds
    # onto the tight `== 0` form. The asserted {0,4} is discarded; the COMPUTED {0} decides.
    assert sig("n*(n+1) % 2 in {0, 1}") == sig("n*(n+1) % 2 == 0")
    assert sig("n*(n+1)*(n+2) % 6 in {0, 3}") == sig("n*(n+1)*(n+2) % 6 == 0")
    # tuple and list literals are accepted too (same canonicalization)
    assert sig("n*(n+1) % 2 in (0, 1)") == sig("n*(n+1) % 2 == 0")
    assert sig("n*(n+1) % 2 in [0, 1]") == sig("n*(n+1) % 2 == 0")


def test_the_organic3_number_12_matches_cube_residue_mod_six():
    # organic3 #12 `n(n+1)(n+5) % 6 ∈ {0,4}` is logically the corpus's cube_residue_mod_six:
    # n(n+1)(n+5) ≡ n^3 + 5n ≡ n^3 - n (mod 6), actual residue set {0}. Same reduced poly mod 6
    # AND same computed residue set -> same signature. The loose `∈{0,4}` phrasing no longer dodges.
    twelve = sig("n*(n+1)*(n+5) % 6 in {0, 4}")
    cube = sig("n^3 % 6 == n % 6")
    assert twelve is not None and twelve == cube
    # and it equals the divisibility restatement too
    assert twelve == sig("(n^3 - n) % 6 == 0")


def test_or_disjunction_of_equalities_matches_the_membership_form():
    # `P%m==a or P%m==b` is set-membership in disguise; canonicalizes identically.
    assert sig("n*(n+1)%2==0 or n*(n+1)%2==1") == sig("n*(n+1) % 2 == 0")
    assert sig("n*(n+1)%2==0 or n*(n+1)%2==1") == sig("n*(n+1) % 2 in {0, 1}")
    # three-clause disjunction over one common P and m
    assert sig("n%6==0 or n%6==2 or n%6==4") is not None


def test_vacuous_offset_collapses_to_base():
    # `+ 6*n*(n+1)` is ≡ 0 (mod 6), so the claim is a restatement of the base. Coefficient
    # reduction mod 6 already erases the vacuous term in the tight `== 0` shape; check it holds.
    base = sig("n*(n+1)*(2*n+1) % 6 == 0")
    offset = sig("(n*(n+1)*(2*n+1) + 6*n*(n+1)) % 6 == 0")
    assert base is not None and base == offset
    # the same vacuous-offset invariance carried through the loose set shape (actual residue {0})
    assert sig("(n*(n+1)*(2*n+1) + 6*n*(n+1)) % 6 in {0, 3}") == base


def test_not_in_with_singleton_actual_residue_matches_inequality():
    # `P % m not in {c}` with computed residues {r}, r != c, is `P !≡ c`… but the residue is r, so
    # `not in {1}` for n(n+1) (actual {0}) is the congruence `P !≡ 1` ≡ `P == 0`'s negation framing.
    # Computed R={0} singleton -> folds to `!=` form with the COMPUTED residue 0.
    assert sig("n*(n+1) % 2 not in {1}") == sig("n*(n+1) % 2 != 0")


def test_existing_inequality_shape_is_recognized_and_stable():
    # `!=` was already recognized; confirm it still signs and is part of the key.
    assert sig("n^2 % 5 != 2") is not None
    assert sig("n^5 % 5 == n % 5") != sig("n^5 % 5 != n % 5")  # relation is part of the signature


# ---------------------------------------------------------------------------------------------
# (ii) MUST-NOT-MATCH — the LOAD-BEARING guards. A false-KNOWN here is the one forbidden bug.
# ---------------------------------------------------------------------------------------------


def test_different_polynomials_never_collapse_equality_shape():
    # different reduced polynomial mod m -> different signature (tight shapes)
    assert sig("n^2 % 5 == 0") != sig("n^3 % 5 == 0")
    assert sig("n*(n+1) % 6 == 0") != sig("n*(n+1)*(n+2) % 6 == 0")
    assert sig("n^2 % 7 == 0") != sig("n^4 % 7 == 0")
    for p in ("n^2 % 5 == 0", "n^3 % 5 == 0", "n*(n+1) % 6 == 0",
              "n*(n+1)*(n+2) % 6 == 0", "n^4 % 7 == 0"):
        assert sig(p) is not None


def test_different_polynomials_never_collapse_membership_shape():
    # multi-residue membership: distinct polys must give distinct signatures even when residue sets
    # happen to coincide. n^2 mod 5 and n^3 mod 5 both range over subsets — keep them apart by FORM.
    assert sig("n^2 % 5 in {0,1,4}") != sig("n^3 % 5 in {0,1,2,3,4}")
    # n^2 mod 11 and n^4 mod 11 share residue sets in some moduli; the polynomial keeps them apart
    assert sig("n^2 % 11 in {0,1,3,4,5,9}") != sig("n^4 % 11 in {0,1,3,4,5,9}")
    for p in ("n^2 % 5 in {0,1,4}", "n^3 % 5 in {0,1,2,3,4}"):
        assert sig(p) is not None


def test_unit_multiples_never_collapse_in_the_multi_residue_branch():
    # THE finding from the design self-critique: `2*n^2 % 7` and `n^2 % 7` have the SAME residue SET
    # but DIFFERENT value-maps, so in a MEMBERSHIP claim they are different facts. The multi-residue
    # branch must NOT apply monic unit-normalization (that would collapse them -> false-KNOWN).
    assert sig("2*n^2 % 7 in {0,1,2,4}") != sig("n^2 % 7 in {0,1,2,4}")
    assert sig("3*n^2 % 7 in {0,3,5,6}") != sig("n^2 % 7 in {0,1,2,4}")
    # (contrast: in the SINGLETON / equality-zero fold, `2*P ≡ 0 ⟺ P ≡ 0` for a unit — that IS the
    # same congruence and SHOULD collapse; checked in the existing structural test for `==`.)
    for p in ("2*n^2 % 7 in {0,1,2,4}", "n^2 % 7 in {0,1,2,4}", "3*n^2 % 7 in {0,3,5,6}"):
        assert sig(p) is not None


def test_different_moduli_never_collapse():
    assert sig("n^2 % 5 in {0,1,4}") != sig("n^2 % 7 in {0,1,2,4}")
    assert sig("n*(n+1) % 6 == 0") != sig("n*(n+1) % 4 == 0")
    assert sig("n^3 % 6 == n % 6") != sig("n^3 % 7 == n % 7")


def test_different_residue_sets_never_collapse():
    # SAME polynomial, but the membership claim asserts a genuinely different shape; the COMPUTED
    # residue set distinguishes a singleton congruence from a multi-residue statement.
    multi = sig("n^2 % 5 in {0,1,4}")          # computed residues {0,1,4} -> multi-residue 'in' sig
    zero = sig("n^2 % 5 == 0")                  # the congruence n^2 ≡ 0 (mod 5) -> '==' sig
    assert multi is not None and zero is not None and multi != zero
    # relop tag ('in' vs '==') also guarantees no collision across the two families
    assert multi[0] == "in" and zero[0] == "=="


def test_membership_and_equality_families_are_disjoint_by_tag():
    # a genuine multi-residue membership can never collide with ANY equality/inequality singleton,
    # because the relop tag differs ('in'/'not in' vs '=='/'!=').
    mem = sig("n^2 % 7 in {0,1,2,4}")
    assert mem is not None and mem[0] in ("in", "not in")
    eq_sigs = [sig("n^2 % 7 == 0"), sig("n^2 % 7 == 1"), sig("n^2 % 7 != 0")]
    assert all(s is not None for s in eq_sigs)
    assert all(mem != s for s in eq_sigs)


def test_asserted_set_is_irrelevant_only_computed_residues_decide():
    # two loose claims over the SAME polynomial with DIFFERENT asserted sets but the SAME computed
    # residue set MUST share a signature (phrasing-independence); and a different polynomial with the
    # SAME asserted set must NOT (form decides, not the asserted set).
    a = sig("n^2 % 5 in {0,1,4}")              # asserted exactly the true set
    b = sig("n^2 % 5 in {0,1,2,3,4}")          # asserted a superset; computed residues still {0,1,4}
    assert a is not None and a == b            # asserted set discarded -> same fact
    c = sig("n^3 % 5 in {0,1,4}")              # different poly, same asserted set
    assert c is not None and c != a            # form differs -> different fact


# ---------------------------------------------------------------------------------------------
# Soundness boundary — unrecognized / unsafe shapes fail toward NOVEL (None), never KNOWN.
# ---------------------------------------------------------------------------------------------


def test_unrecognized_loose_shapes_return_none():
    assert sig("n % 5 in {}") is None                 # {} is an empty dict literal, not a set
    assert sig("n % 5 in {0, k}") is None             # non-constant element
    assert sig("n % 5 in S") is None                  # RHS not a set/tuple/list literal
    assert sig("a*b % 6 in {0, 4}") is None           # multivariate membership not enumerated
    assert sig("n%6==0 or n^2%6==0") is None          # disjuncts over different polynomials
    assert sig("n%6==0 or n%5==0") is None            # disjuncts over different moduli
    assert sig("n%6==0 or n%6!=4") is None            # a non-`==` disjunct
    assert sig("n%6==0 and n%6==0") is None           # `and`, not `or`
    assert sig("(n%6==0 or n%6==2) or n%6==4") is None  # nested BoolOp -> conservative None
    assert sig("n % 5 in {0} or n < 3") is None       # an inequality disjunct


def test_large_modulus_membership_fails_toward_novel():
    # the residue set is exact only within one full period [0, m-1]; for m > RESIDUE_BOUND+1 the box
    # cannot cover a period, so we cannot be sure R is complete -> None (NOVEL), never a wrong KNOWN.
    big = RESIDUE_BOUND + 5
    assert sig(f"n % {big} in {{0, 4}}") is None
    # the tight `== c` shape does not need R, so it is unaffected by the residue bound
    assert sig(f"n % {big} == 0") is not None


# ---------------------------------------------------------------------------------------------
# Property check — equal signatures (membership branch) IFF equal (m, reduced poly, residue set),
# cross-checked against an INDEPENDENT canonical form. Never against truth.
# ---------------------------------------------------------------------------------------------


def _independent_canon(pred: str):
    """Recompute (m, reduced-monomials-mod-m, residue-set, negated?) for a single-variable
    membership/disjunction predicate WITHOUT going through congruence_signature. The reduced
    polynomial uses coefficient-mod-m ONLY (no monic unit step), matching the multi-residue key;
    this is the exact fact-identity two equal signatures must share."""
    t = ast.parse(pred.replace("^", "**"), mode="eval").body
    if isinstance(t, ast.BoolOp):
        dj = _disjunction_residues(t)
        if dj is None:
            return None
        pnode, m = dj
        negate = False
    elif isinstance(t, ast.Compare) and len(t.ops) == 1 and type(t.ops[0]).__name__ in ("In", "NotIn"):
        lm = _mod(t.left)
        if lm is None:
            return None
        pnode, m = lm
        comp = t.comparators[0]
        if not isinstance(comp, (ast.Set, ast.Tuple, ast.List)):
            return None
        if not _residues_from_node(comp.elts, m):
            return None
        negate = type(t.ops[0]).__name__ == "NotIn"
    else:
        return None
    state = {"vars": set()}
    poly = _expand(pnode, state)
    if len(state["vars"]) > 1:
        return None
    R = _residue_set(poly, m)
    if R is None:
        return None
    reduced = frozenset((_mono_degree(mono), c % m) for mono, c in poly.items() if c % m != 0)
    return (m, reduced, R, negate)


def test_property_membership_signature_equals_iff_same_fact():
    polys = ["n", "n+1", "n^2", "n^2+n", "n^3", "n^3+n", "n*(n+1)", "n*(n+1)*(n+2)",
             "2*n^2", "3*n^2", "n^2+2", "4*n"]
    mods = [2, 3, 4, 5, 6, 7, 8, 9]
    asserted = ["{0}", "{0,1}", "{0,4}", "{1,2,3}", "{0,1,2,3,4,5,6,7}"]
    preds = []
    for p in polys:
        for m in mods:
            for s in asserted:
                preds.append(f"({p}) % {m} in {s}")
                preds.append(f"({p}) % {m} not in {s}")

    signed = [(p, sig(p), _independent_canon(p)) for p in preds]
    signed = [(p, s, ic) for (p, s, ic) in signed if s is not None]
    assert signed, "expected some recognized membership predicates"

    # forward: equal signatures => equal independent fact identity (no false-KNOWN).
    # for a SINGLETON computed residue the signature folds to '=='/'!=' (drops R, applies monic);
    # the independent canon keeps R, so compare only on the MULTI-residue (relop in {in,not in}) sigs.
    by_sig: dict = {}
    for p, s, ic in signed:
        if s[0] in ("in", "not in"):
            by_sig.setdefault(s, []).append((p, ic))
    for s, group in by_sig.items():
        facts = {ic for _, ic in group}
        assert len(facts) == 1, (s, group)

    # converse: two DIFFERENT membership facts never share a signature.
    multi = [(p, s, ic) for (p, s, ic) in signed if s[0] in ("in", "not in")]
    for i in range(len(multi)):
        for j in range(i + 1, len(multi)):
            if multi[i][2] != multi[j][2]:
                assert multi[i][1] != multi[j][1], (multi[i][0], multi[j][0])


# ---------------------------------------------------------------------------------------------
# End-to-end through the NoveltyGate (CI-safe: fake Lean, real corpus, pure structural).
# ---------------------------------------------------------------------------------------------


class _FakeLean:
    def is_trivial(self, expr) -> bool:
        return False


def _prop(claim_property: str):
    from leibniz.propositio import Enuntiatio, Expressio, Propositio
    from leibniz.types import ClaimSignature, ClaimType
    return Propositio(
        enuntiatio=Enuntiatio(statement="c", claim_type=ClaimType.INVARIANT, falsifiable_claim="n",
                              claim_domain="n >= 0", claim_property=claim_property),
        expressio=Expressio(theorem_src="theorem t (n:Nat) : True", imports=("Mathlib.Tactic",)),
        signature=ClaimSignature(claim_type=ClaimType.INVARIANT, subject="x", relation="y",
                                 formal_hash="NOVEL_HASH_NOT_IN_CORPUS"),
    )


def test_gate_demotes_organic3_number_12_loose_phrasing_to_known():
    from leibniz.corpus import CorpusBackend
    from leibniz.gates.novelty import NoveltyGate
    from leibniz.types import FinishReason, Verdict
    out = _prop("n*(n+1)*(n+5) % 6 in {0, 4}")
    ev = NoveltyGate(CorpusBackend.from_json(), _FakeLean()).check(out)
    assert ev.verdict is Verdict.FAIL and out.finish_reason is FinishReason.KNOWN
    assert ev.detail["reason"] == "structural congruence match"
    assert ev.detail["match"] == "cube_residue_mod_six"


def test_gate_demotes_disjunction_restatement_to_known():
    from leibniz.corpus import CorpusBackend
    from leibniz.gates.novelty import NoveltyGate
    from leibniz.types import FinishReason, Verdict
    out = _prop("n*(n+1)%2==0 or n*(n+1)%2==1")
    ev = NoveltyGate(CorpusBackend.from_json(), _FakeLean()).check(out)
    assert ev.verdict is Verdict.FAIL and out.finish_reason is FinishReason.KNOWN


def test_gate_keeps_a_genuinely_novel_multi_residue_claim_novel():
    from leibniz.corpus import CorpusBackend
    from leibniz.gates.novelty import NoveltyGate
    from leibniz.types import Verdict
    # a genuine multi-residue statement not in the corpus stays NOVEL (no false-KNOWN)
    out = _prop("n^2 % 7 in {0, 1, 2, 4}")
    ev = NoveltyGate(CorpusBackend.from_json(), _FakeLean()).check(out)
    assert ev.verdict is Verdict.PASS and out.finish_reason is None
