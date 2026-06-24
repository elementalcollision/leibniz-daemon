"""ADR 0032: structural novelty signatures — match restatements by FORM, never truth.

CI-safe, pure stdlib (no Z3, no Lean). The trust-critical property is one-directional: two
claims share a signature IFF they assert the SAME polynomial congruence, so a genuinely
different fact can never be wrongly demoted to KNOWN (no false-KNOWN); anything out of the
recognized univariate-congruence shapes returns None and stays NOVEL.
"""
from __future__ import annotations

from leibniz.structural import congruence_signature as sig


def test_restatements_of_the_same_congruence_collapse():
    # Fermat's little theorem p=5, three surface forms -> one signature
    fermat5 = {sig("n^5 % 5 == n % 5"), sig("(n^5 + 4*n) % 5 == 0"), sig("(n^5 - n) % 5 == 0")}
    assert len(fermat5) == 1 and None not in fermat5
    # p=3 family
    fermat3 = {sig("n^3 % 3 == n % 3"), sig("(n^3 + 2*n) % 3 == 0"), sig("(n^3 - n) % 3 == 0")}
    assert len(fermat3) == 1 and None not in fermat3
    # n(n+1) even, two forms (genuinely the same congruence mod 2)
    even = {sig("(n^2 + n) % 2 == 0"), sig("n^2 % 2 == n % 2")}
    assert len(even) == 1 and None not in even


def test_unit_multiples_and_alpha_renames_collapse():
    # prime-m unit normalization: 2(n^5 - n) ≡ 0 (mod 5) is the same fact as Fermat-5
    assert sig("(2*n^5 - 2*n) % 5 == 0") == sig("n^5 % 5 == n % 5")
    # single-variable alpha-rename
    assert sig("k^5 % 5 == k % 5") == sig("n^5 % 5 == n % 5")


def test_different_congruences_get_different_signatures():
    s = sig("n^5 % 5 == n % 5")
    assert sig("n^7 % 7 == n % 7") != s            # different modulus + poly
    assert sig("n^2 % 3 == 1") != sig("n^2 % 3 == 2")   # different residue
    assert sig("n^2 % 5 == 0") != sig("n^3 % 5 == 0")   # different poly
    assert sig("n^5 % 5 == n % 5") != sig("n^5 % 5 != n % 5")  # relation is part of the signature
    # all are non-None (they ARE recognized congruences, just distinct)
    assert all(x is not None for x in (sig("n^2 % 3 == 1"), sig("n^2 % 3 == 2"), sig("n^7 % 7 == n % 7")))


def test_the_l2_traps_and_out_of_scope_return_none():
    # the exact case L2 wrongly matched: an identity is not a congruence
    assert sig("n + 0 == n") is None
    # raw (non-reduced) RHS: `n^5 % 5 == n` is NOT the congruence n^5≡n (false for n>=5)
    assert sig("n^5 % 5 == n") is None
    # two different moduli in one claim
    assert sig("n^2 % 2 == n % 3") is None
    # residue out of range (P % m == c with c >= m is unsatisfiable, not a normal congruence)
    assert sig("n^2 % 5 == 7") is None
    # non-polynomial / non-congruence terms
    assert sig("Nat.log(2, n) % 5 == 0") is None
    assert sig("(n / 2) % 3 == 0") is None      # division inside the term
    assert sig("n^2 % 5 < 3") is None           # inequality, not == / !=
    assert sig("2 ^ n % 5 == 1") is None        # variable exponent
    assert sig(None) is None and sig("") is None


def test_multivariate_lookalike_does_not_collapse_to_univariate():
    # THE prototype-era false-KNOWN bug: a*b (a multivariate monomial) and a^2 (a univariate
    # square) are DIFFERENT facts and MUST get different signatures. Both are now recognized
    # (multivariate is no longer rejected), but they must never collide.
    assert sig("a * b % 2 == 0") is not None
    assert sig("a^2 % 2 == 0") is not None
    assert sig("a * b % 2 == 0") != sig("a^2 % 2 == 0")
    # and the univariate single-var case is unchanged (n^2 IS recognized)
    assert sig("n^2 % 2 == 0") is not None
    # a multivariate monomial key (tuple) can never equal a univariate one (int exponent), so a
    # multivariate sig and ANY univariate sig are structurally disjoint
    assert sig("a * b % 2 == 0") != sig("n^2 % 2 == 0")


# --- ADR 0032 multivariate extension: SOUND, conservative, no false-KNOWN -------------------
# Priority: the false-KNOWN guards. Truth is never consulted; matching is by FORM only. The one
# forbidden bug is two GENUINELY DIFFERENT congruences sharing a signature. A missed match
# (different signature / None) is benign. Multivariate keys on the LITERAL variable names — NO
# rename canonicalization — so a different monomial set always yields a different signature.

def test_multivariate_is_now_recognized_not_none():
    # the pre-ADR-0032 behavior returned None for any 2nd distinct variable; now recognized
    assert sig("a * b % 2 == 0") is not None
    assert sig("(a + b) % 3 == 0") is not None
    assert sig("(a*b + a + b) % 5 == 0") is not None


def test_multivariate_distinct_monomial_sets_get_distinct_signatures():
    # the prototype-era bug, stated head-on: product-of-two-vars vs a single-var square
    assert sig("a * b % 2 == 0") != sig("a^2 % 2 == 0")
    # different variable PAIRS are different facts (different literal names)
    assert sig("a * b % 2 == 0") != sig("a * c % 2 == 0")
    # different exponents on the same vars
    assert sig("a^2 * b % 3 == 0") != sig("a * b^2 % 3 == 0")
    # adding a term changes the monomial set
    assert sig("a * b % 3 == 0") != sig("(a * b + a) % 3 == 0")
    # different modulus
    assert sig("a * b % 2 == 0") != sig("a * b % 3 == 0")
    # different relation
    assert sig("a * b % 2 == 0") != sig("a * b % 2 != 0")
    # different coefficient (multivariate unit-normalization is SKIPPED, so 2ab != ab) — safe
    assert sig("a * b % 5 == 0") != sig("2 * a * b % 5 == 0")
    # all of the above are genuinely recognized congruences (non-None), just distinct
    for p in ("a * b % 2 == 0", "a * c % 2 == 0", "a^2 * b % 3 == 0",
              "a * b^2 % 3 == 0", "2 * a * b % 5 == 0"):
        assert sig(p) is not None


def test_multivariate_restatements_of_the_same_congruence_collapse():
    # the SAME congruence written different ways -> ONE signature
    # a*b == 0 (mod 2) restated as (a*b - 0)
    same = {sig("a * b % 2 == 0"), sig("(a * b - 0) % 2 == 0"), sig("(a * b) % 2 == 0")}
    assert len(same) == 1 and None not in same
    # commutativity is a true algebraic identity (NOT a rename): a*b and b*a are the SAME monomial
    assert sig("a * b % 2 == 0") == sig("b * a % 2 == 0")
    # P1 % m == P2 % m form: a*b ≡ 0  <=>  a*b ≡ a*b - a*b  (the difference is the same poly)
    assert sig("(a*b + c) % 7 == c % 7") == sig("a * b % 7 == 0")


def test_multivariate_variable_rename_does_NOT_collapse():
    # CONSERVATIVE MISS (documents the safe false-NOVEL): a rename is a different literal form.
    # We do NOT do permutation-canonical-form (that risks a false-KNOWN); we key on names.
    assert sig("a * b % 2 == 0") != sig("x * y % 2 == 0")
    assert sig("(a + b) % 3 == 0") != sig("(x + y) % 3 == 0")
    # even a partial rename / reorder of names is a distinct signature (safe)
    assert sig("a * b % 2 == 0") != sig("a * x % 2 == 0")
    # all are recognized (non-None) — the point is they DON'T collide, not that they're rejected
    assert all(sig(p) is not None for p in
               ("a * b % 2 == 0", "x * y % 2 == 0", "a * x % 2 == 0"))


def _canonical_poly(predicate: str):
    """Independently recompute the normalized (m, {monomial: coeff_mod_m}) form for a `P % m == 0`
    predicate, WITHOUT going through congruence_signature, plus the set of distinct variable names.
    Cross-checks that equal MULTIVARIATE signatures really mean equal normalized polynomials over
    the same literal names (the soundness invariant — no false-KNOWN). Literal-name keying means
    no alpha-collapse happens for >=2 vars, so this map is the exact thing the signature encodes."""
    import ast as _ast

    from leibniz.structural import _expand, _mod
    tree = _ast.parse(predicate.replace("^", "**"), mode="eval").body
    pnode, m = _mod(tree.left)
    state = {"vars": set()}
    poly = _expand(pnode, state)
    canon = frozenset((mono, c % m) for mono, c in poly.items() if c % m != 0)
    return m, canon, frozenset(state["vars"])


def test_property_distinct_monomial_coeff_sets_never_collide():
    # property-ish: build many small congruences and confirm that two GENUINELY MULTIVARIATE
    # predicates (>=2 distinct literal variable names) share a signature IFF they denote the same
    # normalized polynomial congruence (mod m) over the same names. This is the false-KNOWN
    # invariant checked DIRECTLY against an independent canonical form — never against truth.
    names = ["a", "b", "c"]
    preds = []
    for v in names:
        for w in names:
            for m in (2, 3, 5, 6):
                for coeff in (1, 2):
                    preds.append(f"{coeff} * {v} * {w} % {m} == 0")
                    preds.append(f"({coeff} * {v} * {w} + {v}) % {m} == 0")
    # keep only the genuinely multivariate ones (>=2 distinct names); single-var ones go through
    # the legacy univariate path (alpha-invariant by exponent) which is tested elsewhere.
    mv = [p for p in preds if len(_canonical_poly(p)[2]) >= 2]
    assert mv, "expected some multivariate predicates"
    by_sig: dict = {}
    for p in mv:
        s = sig(p)
        assert s is not None, p
        by_sig.setdefault(s, []).append(p)
    # every group sharing one signature must share one normalized polynomial (same m + monomials)
    for s, group in by_sig.items():
        canon = {_canonical_poly(p)[:2] for p in group}
        assert len(canon) == 1, (s, group, canon)
    # and conversely: two predicates with DIFFERENT normalized polynomials never share a signature
    for i in range(len(mv)):
        for j in range(i + 1, len(mv)):
            if _canonical_poly(mv[i])[:2] != _canonical_poly(mv[j])[:2]:
                assert sig(mv[i]) != sig(mv[j]), (mv[i], mv[j])


def test_caps_degrade_to_none_without_crashing():
    huge = "(" + " + ".join(["n"] * 500) + ") % 7 == 0"     # exceeds MAX_NODES
    assert sig(huge) is None
    deep = "n" + "^8" * 20 + " % 5 == 0"                     # would blow up degree -> None
    assert sig(deep) is None


# --- end-to-end through the NoveltyGate (CI-safe: fake Lean, real corpus, pure structural) ---

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
                                 formal_hash="NOVEL_HASH_NOT_IN_CORPUS"),  # forces past the hash check
    )


def test_novelty_gate_demotes_a_structural_restatement_to_known():
    from leibniz.corpus import CorpusBackend
    from leibniz.gates.novelty import NoveltyGate
    from leibniz.types import FinishReason, Verdict
    out = _prop("(n^5 + 4*n) % 5 == 0")
    ev = NoveltyGate(CorpusBackend.from_json(), _FakeLean()).check(out)
    assert ev.verdict is Verdict.FAIL and out.finish_reason is FinishReason.KNOWN
    assert ev.detail["reason"] == "structural congruence match" and ev.detail["match"] == "fermat_little_5"


def test_novelty_gate_passes_a_genuinely_novel_congruence():
    from leibniz.corpus import CorpusBackend
    from leibniz.gates.novelty import NoveltyGate
    from leibniz.types import Verdict
    out = _prop("(n^2 + n + 41) % 41 == 0")     # Euler's polynomial — not in the corpus
    ev = NoveltyGate(CorpusBackend.from_json(), _FakeLean()).check(out)
    assert ev.verdict is Verdict.PASS and out.finish_reason is None
