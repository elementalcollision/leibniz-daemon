"""ADR 0031 Layer 2: the novelty gate catches RESTATEMENTS of known results by
decision-procedure equivalence, not just exact structural-hash identity.

The first organic run promulgated Fermat's little theorem restated (`(n^5+4n)%5==0`)
because its hash differs from `n^5%5==n%5`. With a curated known predicate, the gate
now demotes such restatements to KNOWN via Z3 box-equivalence — mechanically, no judge,
conclusive-only (an inconclusive/un-encodable check never wrongly demotes a novelty).

z3-gated (the equivalence search needs the `verify` extra); Lean is faked so this
exercises the equivalence path without a container.
"""
from __future__ import annotations

import pytest

from leibniz.backends.smt_z3 import available
from leibniz.corpus import CorpusBackend, CorpusEntry
from leibniz.gates.novelty import NoveltyGate
from leibniz.propositio import Enuntiatio, Expressio, Propositio
from leibniz.types import ClaimSignature, ClaimType, FinishReason, Verdict

pytestmark = [
    pytest.mark.z3,
    pytest.mark.skipif(not available(), reason="z3-solver (verify extra) not installed"),
]


class _FakeLean:
    """is_trivial=False so the gate proceeds past non-triviality to the corpus checks."""

    def is_trivial(self, expr) -> bool:
        return False


def _smt():
    from leibniz.backends.smt_z3 import Z3Backend
    from leibniz.verifiers import SMTVerifier
    return SMTVerifier(Z3Backend())


def _corpus() -> CorpusBackend:
    # curated knowns WITH DSL predicates (as build_corpus emits for ADR 0031 L2)
    return CorpusBackend([
        CorpusEntry("fermat_little_5", "invariant", "number_theory", "fermat_little",
                    "HASH_F5", claim_domain="n >= 0", claim_property="n^5 % 5 == n % 5"),
        CorpusEntry("cube_residue_mod_six", "invariant", "number_theory", "power_residue",
                    "HASH_C6", claim_domain="n >= 0", claim_property="n^3 % 6 == n % 6"),
        CorpusEntry("mul_comm_nat", "structural", "nat_mul", "commutativity", "HASH_MC"),  # no predicate
    ])


def _prop(claim_property: str, claim_type=ClaimType.INVARIANT, fhash="NOVEL_HASH") -> Propositio:
    return Propositio(
        enuntiatio=Enuntiatio(
            statement="c", claim_type=claim_type, falsifiable_claim="n",
            claim_domain="n >= 0", claim_property=claim_property,
        ),
        expressio=Expressio(theorem_src="theorem t (n:Nat) : True", imports=("Mathlib.Tactic",)),
        signature=ClaimSignature(claim_type=claim_type, subject="number_theory",
                                 relation="fermat_little", formal_hash=fhash),  # not in corpus
    )


def test_restatement_of_fermat_is_caught_known_by_equivalence():
    # the exact cycle-5 escape: Fermat restated. Its hash is novel, but it is box-equivalent
    # to the curated Fermat predicate -> KNOWN.
    gate = NoveltyGate(_corpus(), _FakeLean(), smt=_smt())
    prop = _prop("(n^5 + 4*n) % 5 == 0")
    ev = gate.check(prop)
    assert ev.verdict is Verdict.FAIL and prop.finish_reason is FinishReason.KNOWN
    assert ev.detail["reason"] == "decision-procedure equivalence to known"
    assert ev.detail["match"] == "fermat_little_5"


def test_minus_form_matches_residue_entry():
    gate = NoveltyGate(_corpus(), _FakeLean(), smt=_smt())
    prop = _prop("(n^3 - n) % 6 == 0")          # <-> n^3 % 6 == n % 6
    ev = gate.check(prop)
    assert prop.finish_reason is FinishReason.KNOWN and ev.detail["match"] == "cube_residue_mod_six"


def test_genuinely_novel_claim_passes():
    # not equivalent to any curated known -> stays NOVEL (PASS).
    gate = NoveltyGate(_corpus(), _FakeLean(), smt=_smt())
    prop = _prop("(n^2 + n + 41) % 41 == 0")    # not a corpus fact
    ev = gate.check(prop)
    assert ev.verdict is Verdict.PASS and prop.finish_reason is None


def test_unencodable_predicate_stays_novel_never_wrongly_known():
    # an inconclusive/un-encodable equivalence search must NEVER demote -> PASS.
    gate = NoveltyGate(_corpus(), _FakeLean(), smt=_smt())
    prop = _prop("Nat.log(2, n) == n % 5")
    ev = gate.check(prop)
    assert ev.verdict is Verdict.PASS and prop.finish_reason is None


def test_magic_constant_attack_is_rejected_at_default_bound():
    # adversarial false-KNOWN attempt: a claim that agrees with a known only on a prefix and
    # diverges past a literal (`or n > 128`). The default bound (1024) is far past 128, so Z3
    # finds the in-box divergence -> NOT demoted (stays NOVEL). Guards the false-KNOWN risk.
    corpus = CorpusBackend([
        CorpusEntry("parity_even", "invariant", "number_theory", "parity",
                    "H_PAR", claim_domain="n >= 0", claim_property="n % 2 == 0"),
    ])
    gate = NoveltyGate(corpus, _FakeLean(), smt=_smt())
    prop = _prop("(n % 2 == 0) or (n > 128)")
    ev = gate.check(prop)
    assert ev.verdict is Verdict.PASS and prop.finish_reason is None


def test_layer2_is_noop_without_smt():
    # no smt backend -> equivalence pass is skipped; a restatement stays NOVEL (v1 behaviour).
    gate = NoveltyGate(_corpus(), _FakeLean())  # smt=None
    ev = gate.check(_prop("(n^5 + 4*n) % 5 == 0"))
    assert ev.verdict is Verdict.PASS
