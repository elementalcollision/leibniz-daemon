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
    # multivariate must NOT be canonicalized as univariate (a*b is not n^2)
    assert sig("a * b % 2 == 0") is None
    assert sig("(a + b) % 3 == 0") is None
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
    # guard the multivariate gap directly: a*b and n^2 must not share a signature
    assert sig("a * b % 2 == 0") is None
    assert sig("n^2 % 2 == 0") is not None       # the univariate one IS recognized


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
