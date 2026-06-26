"""ADR 0039 — the Observatory faithfulness lint: a BOUNDED, SOUND cross-check that a
Walnut-DECIDED-true predicate is faithful to the property the conjecturer SAYS it encodes.

These pin the lessons of the first live run (``docs/observatory-first-run-finding.md``): all
three DECIDED records were faithfulness artifacts (off-by-one / off-by-p) whose prose claim is
FALSE for Rudin-Shapiro. The lint catches that class WITHOUT trusting prose, by brute-forcing a
machine-checkable ``property_descriptor`` over a finite prefix.

Non-negotiables pinned below:
  * the sequence generators MATCH canonical definitions (the soundness root);
  * the two live counterexample artifacts are CAUGHT (quarantined, never DECIDED);
  * the contrived n-dependent artifact has no standard family => undescribable => (production)
    refused;
  * the descriptor is BOUND to the predicate: its word must be the word the predicate indexes
    (the review's high-severity word-substitution finding) + alphabet/param guards;
  * a genuine TRUE property still PASSES (the lint never over-blocks);
  * the lint can only DOWNGRADE: it never sets promulgated/Demonstratio/Q.E.D.;
  * a refuted verdict is never blocked by the lint.

Stdlib-only; Walnut never invoked (runner injected).
"""
from __future__ import annotations

from leibniz.observatory import WALNUT_DECISION_EDGE, WalnutObservatory, is_walnut_decided
from leibniz.observatory_lint import (
    _fibonacci_word,
    _rudin_shapiro,
    _thue_morse,
    _tribonacci_word,
    descriptor_binds_predicate,
    lint_descriptor,
    predicate_indexed_words,
)
from leibniz.propositio import Enuntiatio, Expressio, Propositio
from leibniz.types import ClaimType, FinishReason

_UNIVERSAL = "msd_2\n\n0 1\n0 -> 0\n1 -> 0\n"  # a universal agreement automaton (decided true)


def _pred(word: str) -> str:
    """A minimal Walnut predicate that INDEXES ``word`` (so the descriptor binds to it)."""
    return f"A i,p (p>=1) => (E t (t<p+p+p+p) & {word}[i+t] != {word}[i+t+p])"


def _lint(descriptor, *, decided_true=True, word="RS"):
    """Lint helper with a predicate that indexes ``word`` (defaults to a bound predicate)."""
    return lint_descriptor(descriptor, decided_true=decided_true, predicate=_pred(word))


# --- the soundness root: generators match canonical definitions ----------------------------

def test_generators_match_canonical_prefixes():
    assert _thue_morse(16) == [0, 1, 1, 0, 1, 0, 0, 1, 1, 0, 0, 1, 0, 1, 1, 0]
    assert _rudin_shapiro(16) == [0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0, 1, 1, 1, 0, 1]
    assert _fibonacci_word(13) == [0, 1, 0, 0, 1, 0, 1, 0, 0, 1, 0, 0, 1]
    assert _tribonacci_word(11) == [0, 1, 0, 2, 0, 1, 0, 0, 1, 0, 2]
    # RS[7..10] is the 4th power 0000 (NOT 1111) — the d4a4d22b counterexample
    assert _rudin_shapiro(11)[7:11] == [0, 0, 0, 0]
    # RS[13..16] is the alternating 1010 — the d37eb690 counterexample
    assert _rudin_shapiro(17)[13:17] == [1, 0, 1, 0]


# --- lint catches the live artifacts; passes genuine truths --------------------------------

def test_lint_catches_rs_fourth_power_artifact():  # d4a4d22b
    r = _lint({"family": "power_free", "word": "RS", "exponent": 4}, word="RS")
    assert r.is_counterexample
    cx = r.detail["counterexample"]
    assert cx["exponent"] == 4 and cx["factor"] == [0, 0, 0, 0]


def test_lint_catches_rs_alternating_artifact():  # d37eb690
    r = _lint({"family": "avoids_pattern", "word": "RS", "pattern": "alternating", "length": 4},
              word="RS")
    assert r.is_counterexample


def test_lint_undescribable_for_contrived_family():  # baff1218 (no standard family)
    assert _lint({"family": "nonconstant_window", "word": "RS"}, word="RS").status \
        == "undescribable"


def test_lint_passes_genuine_truths():
    # Thue-Morse is cube-free; RS is 5th-power-free (within prefix); TM avoids 000 (cube-free).
    assert _lint({"family": "power_free", "word": "T", "exponent": 3}, word="T").is_pass
    assert _lint({"family": "power_free", "word": "RS", "exponent": 5}, word="RS").is_pass
    assert _lint({"family": "avoids_factor", "word": "T", "block": "000"}, word="T").is_pass


def test_lint_catches_genuine_falsehoods():
    # TM is NOT square-free (it has 11), and does NOT avoid 00.
    assert _lint({"family": "power_free", "word": "T", "exponent": 2}, word="T").is_counterexample
    assert _lint({"family": "avoids_factor", "word": "T", "block": "00"}, word="T").is_counterexample


def test_refuted_verdict_is_never_blocked():
    # decided_true=False (Walnut REFUTED): even with a prefix counterexample the lint passes.
    r = _lint({"family": "power_free", "word": "RS", "exponent": 4}, decided_true=False, word="RS")
    assert r.is_pass and r.detail["corroborated_refutation"] is True


def test_unsupported_word_and_bad_params_are_undescribable():
    assert _lint({"family": "power_free", "word": "P", "exponent": 3}, word="RS").status \
        == "undescribable"                                     # paperfolding word unsupported
    assert lint_descriptor(None, decided_true=True, predicate=_pred("RS")).status \
        == "undescribable"                                     # missing descriptor
    assert _lint({"family": "power_free", "word": "T", "exponent": 1}, word="T").status \
        == "undescribable"                                     # e<2


# --- descriptor<->predicate binding (the review's high-severity fix) ------------------------

def test_word_indexing_extraction():
    assert predicate_indexed_words("A n (RS[n]=@0 & RS[n+1]=@1)") == ["RS", "RS"]
    assert predicate_indexed_words("A n (T[n] != T[n+p])") == ["T", "T"]
    assert predicate_indexed_words("n>=1 & p<n") == []          # indexes nothing


def test_descriptor_binds_only_matching_word():
    assert descriptor_binds_predicate({"word": "RS"}, _pred("RS")) is True
    assert descriptor_binds_predicate({"word": "T"}, _pred("RS")) is False   # word substitution
    assert descriptor_binds_predicate({"word": "RS"}, "n>=1 & p<n") is False  # indexes nothing
    # two distinct indexed words cannot be anchored by a single-word descriptor
    assert descriptor_binds_predicate({"word": "RS"}, "RS[n]=T[n]") is False


def test_word_substitution_artifact_is_caught():
    # THE review witness: false "RS 4th-power-free" claim, but descriptor names Thue-Morse
    # (which IS 4th-power-free). Without binding this PASSED; now it is refused as a mismatch.
    r = lint_descriptor({"family": "power_free", "word": "T", "exponent": 4},
                        decided_true=True, predicate=_pred("RS"))
    assert r.status == "undescribable" and r.detail["why"] == "word_mismatch"


def test_out_of_alphabet_block_is_refused():
    # a block over symbols a binary word cannot contain "never occurs" trivially — a false anchor.
    r = _lint({"family": "avoids_factor", "word": "RS", "block": "9999"}, word="RS")
    assert r.status == "undescribable" and r.detail["why"] == "block_out_of_alphabet"
    # '2' is in the Tribonacci alphabet, so it is allowed there
    assert _lint({"family": "avoids_factor", "word": "TR", "block": "2"}, word="TR").status \
        in {"pass", "counterexample"}


def test_degenerate_parameters_are_refused():
    assert _lint({"family": "power_free", "word": "RS", "exponent": 100}, word="RS").status \
        == "undescribable"                                     # absurd exponent (param-shop)
    assert _lint({"family": "avoids_pattern", "word": "RS", "pattern": "alternating",
                  "length": 999}, word="RS").status == "undescribable"
    # bools must not masquerade as int params
    assert _lint({"family": "power_free", "word": "RS", "exponent": True}, word="RS").status \
        == "undescribable"


# --- Observatory integration ---------------------------------------------------------------

def _prop(descriptor=None, pred=None, num="msd_2"):
    word = (descriptor or {}).get("word", "RS")
    en = Enuntiatio(statement="advisory prose", claim_type=ClaimType.INVARIANT,
                    falsifiable_claim="exists n")
    ex = Expressio(theorem_src="theorem t : P", walnut_predicate=pred or _pred(word),
                   walnut_numeration=num, property_descriptor=descriptor)
    return Propositio(enuntiatio=en, expressio=ex)


def _decide(descriptor, automaton=_UNIVERSAL, require_descriptor=False, pred=None):
    obs = WalnutObservatory(runner=lambda *a, **k: automaton, require_descriptor=require_descriptor)
    return obs.decide(_prop(descriptor, pred=pred))


def test_decided_true_with_counterexample_descriptor_is_quarantined():
    prop = _decide({"family": "power_free", "word": "RS", "exponent": 4})
    assert prop.finish_reason is FinishReason.UNPROVEN
    assert is_walnut_decided(prop) is False
    edge = next(e for e in prop.edges if e.edge == WALNUT_DECISION_EDGE)
    assert edge.detail["reason"] == "lint_counterexample"
    assert edge.detail["faithfulness"]["lint"] == "counterexample"
    assert prop.promulgated is False and prop.demonstratio is None


def test_decided_true_with_passing_descriptor_is_decided_and_formal_first():
    prop = _decide({"family": "power_free", "word": "T", "exponent": 3})
    assert prop.finish_reason is FinishReason.WALNUT_DECIDED
    assert is_walnut_decided(prop) is True
    edge = next(e for e in prop.edges if e.edge == WALNUT_DECISION_EDGE)
    assert edge.detail["faithfulness"]["mode"] == "formal_first"
    assert edge.detail["faithfulness"]["lint"] == "pass"
    assert prop.promulgated is False and prop.demonstratio is None


def test_word_mismatch_descriptor_is_quarantined_under_require():
    # descriptor names T but the predicate indexes RS => unbound => refused in the live tier.
    prop = _decide({"family": "power_free", "word": "T", "exponent": 4},
                   require_descriptor=True, pred=_pred("RS"))
    assert prop.finish_reason is FinishReason.UNPROVEN
    edge = next(e for e in prop.edges if e.edge == WALNUT_DECISION_EDGE)
    assert edge.detail["reason"] == "lint_no_descriptor"
    assert edge.detail["faithfulness"]["lint"] == "undescribable"


def test_require_descriptor_quarantines_descriptor_less_decision():
    prop = _decide(None, require_descriptor=True)
    assert prop.finish_reason is FinishReason.UNPROVEN
    edge = next(e for e in prop.edges if e.edge == WALNUT_DECISION_EDGE)
    assert edge.detail["reason"] == "lint_no_descriptor"


def test_without_require_descriptor_descriptor_less_decision_is_advisory_decided():
    # backward-compat: the pure decision-semantics path still decides, lint marked advisory.
    prop = _decide(None, require_descriptor=False)
    assert prop.finish_reason is FinishReason.WALNUT_DECIDED
    edge = next(e for e in prop.edges if e.edge == WALNUT_DECISION_EDGE)
    assert edge.detail["faithfulness"]["lint"] == "undescribable"


def test_closed_sentence_true_is_also_linted():
    # the bare-`true` sentence path (decided_sentence) runs the same lint; a counterexample
    # descriptor quarantines it just like the universal path.
    prop = _decide({"family": "power_free", "word": "RS", "exponent": 4}, automaton="true")
    assert prop.finish_reason is FinishReason.UNPROVEN
    edge = next(e for e in prop.edges if e.edge == WALNUT_DECISION_EDGE)
    assert edge.detail["reason"] == "lint_counterexample"


def test_lint_never_blocks_a_refutation():
    # a non-universal automaton => REFUTED, regardless of descriptor (lint guards only DECIDED).
    non_universal = "msd_2\n\n0 1\n0 -> 0\n1 -> 1\n\n1 0\n0 -> 1\n1 -> 1\n"
    prop = _decide({"family": "power_free", "word": "RS", "exponent": 4}, automaton=non_universal)
    assert prop.finish_reason is FinishReason.REFUTED
