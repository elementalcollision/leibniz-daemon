"""ADR 0037 Slice 2 — Walnut backend: parser, the gate-owned UNIVERSALITY re-checker, and
the backend's exact-or-DEFER verdicts. Stdlib-only: the Walnut binary is never invoked (the
runner is injected), so the parser/universality/verdict logic is fully exercised without it.

Headline guards (the laundering classes the soundness review demanded):
  * a backend fabricating a re-checked PASS on a `false`/non-universal certificate is caught;
  * a backend fabricating data="true" (a bare token, no universal automaton) is caught;
  * only a STRUCTURED, genuinely UNIVERSAL agreement automaton earns a PASS.
"""
from __future__ import annotations

import stat

from leibniz.backends import walnut
from leibniz.backends.walnut import (
    WALNUT_CERT_KIND,
    WalnutBackend,
    automaton_is_universal,
    classify_agreement,
    parse_walnut_automaton,
    recheck_walnut_certificate,
)
from leibniz.gates.faithfulness import FaithfulnessGate
from leibniz.gates.sound_backends import Certificate, FaithfulnessVerdict
from leibniz.propositio import Enuntiatio, Expressio, Propositio
from leibniz.trust import FAITHFULNESS_EDGE
from leibniz.types import ClaimType, TrustTier, Verdict

# A genuinely UNIVERSAL agreement automaton: one state (0), output 1 (accepting), every
# input self-loops -> the only reachable state is accepting -> accepts all n.
_UNIVERSAL = "msd_2\n\n0 1\n0 -> 0\n1 -> 0\n"
# A NON-universal automaton: state 0 (output 1) reaches state 1 (output 0) on input 1.
_NON_UNIVERSAL = "msd_2\n\n0 1\n0 -> 0\n1 -> 1\n\n1 0\n0 -> 1\n1 -> 1\n"
# Thue-Morse-shaped: outputs alternate -> reachable set contains an output-0 state -> not universal.
_AUT_ALTERNATING = "msd_2\n\n0 0\n0 -> 0\n1 -> 1\n\n1 1\n0 -> 1\n1 -> 0\n"


# --- parser -----------------------------------------------------------------

def test_parse_bare_tokens_are_sentences_not_structured():
    t = parse_walnut_automaton("true")
    assert t.is_sentence and t.is_true and t.parsed_ok is False
    f = parse_walnut_automaton("false")
    assert f.is_sentence and not f.is_true


def test_parse_structured_automaton():
    a = parse_walnut_automaton(_NON_UNIVERSAL)
    assert a.is_sentence is False and a.parsed_ok is True
    assert a.numeration == "msd_2"
    assert a.states == {0: 1, 1: 0}
    assert a.n_states == 2


def test_parse_garbage_is_not_parsed_ok():
    assert parse_walnut_automaton("not an automaton").parsed_ok is False
    assert parse_walnut_automaton("").parsed_ok is False


# Exact byte-format Walnut's Automaton.write()/writeAlphabet/writeState emit: numeration
# header, then per state a leading blank line, "<q> <output>", and "<digit> -> <dest>" lines
# with BARE digits (not bracketed). This pins our parser to the real serializer.
_REAL_UNIVERSAL = "msd_2\n\n0 1\n0 -> 0\n1 -> 1\n\n1 1\n0 -> 0\n1 -> 1\n"
_REAL_REFUTED = "msd_2\n\n0 1\n0 -> 0\n1 -> 1\n\n1 0\n0 -> 0\n1 -> 1\n"


def test_parses_real_walnut_serializer_format():
    a = parse_walnut_automaton(_REAL_UNIVERSAL)
    assert a.numeration == "msd_2"
    assert a.states == {0: 1, 1: 1}
    assert a.trans == {0: {"0": 0, "1": 1}, 1: {"0": 0, "1": 1}}
    assert a.parsed_ok and a.deterministic
    # multi-state universal / refuted both classify correctly in the real format
    assert classify_agreement(parse_walnut_automaton(_REAL_UNIVERSAL)) == "universal"
    assert classify_agreement(parse_walnut_automaton(_REAL_REFUTED)) == "refuted"


# --- universality (the real structural check) -------------------------------

def test_universality():
    assert automaton_is_universal(parse_walnut_automaton(_UNIVERSAL)) is True
    assert automaton_is_universal(parse_walnut_automaton(_NON_UNIVERSAL)) is False
    assert automaton_is_universal(parse_walnut_automaton(_AUT_ALTERNATING)) is False
    # bare tokens carry no structure -> never universal (cannot be re-checked)
    assert automaton_is_universal(parse_walnut_automaton("true")) is False
    assert automaton_is_universal(parse_walnut_automaton("false")) is False


def test_universality_requires_initial_state_zero():
    # an automaton with no state 0 cannot be evaluated -> conservatively not universal
    assert automaton_is_universal(parse_walnut_automaton("msd_2\n\n5 1\n0 -> 5\n1 -> 5\n")) is False


# --- gate-owned re-checker --------------------------------------------------

def _cert(data, rechecked=True, kind=WALNUT_CERT_KIND):
    return Certificate(kind=kind, rechecked=rechecked, data=data)


def test_recheck_accepts_only_universal_structured_automaton():
    assert recheck_walnut_certificate(_cert(_UNIVERSAL)) is True
    assert recheck_walnut_certificate(_cert(_NON_UNIVERSAL)) is False


def test_recheck_rejects_bare_true_token_fabrication():
    # THE laundering class the review flagged: a fabricated data="true" has no universal
    # automaton -> the gate's universality re-check rejects it.
    assert recheck_walnut_certificate(_cert("true")) is False
    assert recheck_walnut_certificate(_cert("false")) is False


def test_recheck_ignores_self_reported_flag_and_uses_data():
    assert recheck_walnut_certificate(_cert(_NON_UNIVERSAL, rechecked=True)) is False


def test_recheck_rejects_wrong_kind_or_bad_data():
    assert recheck_walnut_certificate(_cert(_UNIVERSAL, kind="sos")) is False
    assert recheck_walnut_certificate(_cert(123)) is False
    assert recheck_walnut_certificate(None) is False


# --- backend verdicts (injected runner) -------------------------------------

def _walnut_prop():
    en = Enuntiatio(statement="s", claim_type=ClaimType.INVARIANT,
                    falsifiable_claim="exists counterexample")
    ex = Expressio(theorem_src="theorem t : P",
                   walnut_predicate="claim(n) <=> stmt(n)", walnut_numeration="msd_2")
    return Propositio(enuntiatio=en, expressio=ex)


def _plain_prop():
    en = Enuntiatio(statement="s", claim_type=ClaimType.INVARIANT,
                    falsifiable_claim="exists counterexample")
    return Propositio(enuntiatio=en, expressio=Expressio(theorem_src="theorem t : P"))


def test_backend_applies_only_to_walnut_claims():
    b = WalnutBackend(runner=lambda *a, **k: _UNIVERSAL)
    assert b.applies(_walnut_prop()) is True
    assert b.applies(_plain_prop()) is False


def test_backend_universal_is_pass_with_rechecked_certificate():
    b = WalnutBackend(runner=lambda *a, **k: _UNIVERSAL)
    v = b.check(_walnut_prop())
    assert v.verdict is Verdict.PASS
    assert v.certificate.kind == WALNUT_CERT_KIND
    assert recheck_walnut_certificate(v.certificate) is True


def test_backend_non_universal_is_fail():
    b = WalnutBackend(runner=lambda *a, **k: _NON_UNIVERSAL)
    assert b.check(_walnut_prop()).verdict is Verdict.FAIL


def test_backend_defers_on_bare_token_result():
    # A closed-sentence token can't be independently universality-checked -> DEFER.
    assert WalnutBackend(runner=lambda *a, **k: "true").check(_walnut_prop()).verdict is Verdict.DEFER
    assert WalnutBackend(runner=lambda *a, **k: "false").check(_walnut_prop()).verdict is Verdict.DEFER


def test_backend_defers_when_binary_absent():
    assert WalnutBackend(runner=lambda *a, **k: None).check(_walnut_prop()).verdict is Verdict.DEFER


def test_backend_defers_on_malformed_result():
    assert WalnutBackend(runner=lambda *a, **k: "garbage").check(_walnut_prop()).verdict is Verdict.DEFER


# --- end-to-end through the gate (registry + dispatch) -----------------------

class _NoWitnessSMT:
    class backend:
        @staticmethod
        def find_gaming_witness(statement, negated_claim, bound):
            return None


def _gate(backend, register_recheck=True):
    recheckers = {WALNUT_CERT_KIND: recheck_walnut_certificate} if register_recheck else {}
    return FaithfulnessGate(smt=_NoWitnessSMT(), probes={}, judge=None,
                            sound_backends=(backend,), recheckers=recheckers)


def test_gate_accepts_universal_as_mechanical_faithfulness_pass():
    ev = _gate(WalnutBackend(runner=lambda *a, **k: _UNIVERSAL)).check(_walnut_prop())
    assert ev.verdict is Verdict.PASS
    assert ev.tier is TrustTier.MECHANICAL          # never JUDGED
    assert ev.edge == FAITHFULNESS_EDGE             # never the proof edge
    assert ev.detail["certificate_kind"] == WALNUT_CERT_KIND
    assert ev.detail["rechecked_by_gate"] is True


def test_gate_without_registered_rechecker_cannot_pass():
    ev = _gate(WalnutBackend(runner=lambda *a, **k: _UNIVERSAL),
               register_recheck=False).check(_walnut_prop())
    assert ev.verdict is Verdict.DEFER


class _LyingBackend:
    """Self-reports a re-checked PASS on a certificate that is NOT a universal automaton.
    The gate's own universality re-check must defeat it -- for both a non-universal
    automaton and the bare data="true" fabrication."""

    name = "liar"
    cost_rank = 1

    def __init__(self, data):
        self._data = data

    def applies(self, prop):
        return True

    def check(self, prop):
        return FaithfulnessVerdict(
            verdict=Verdict.PASS, producer="liar",
            certificate=Certificate(kind=WALNUT_CERT_KIND, rechecked=True, data=self._data),
        )


def test_lying_backend_non_universal_certificate_is_caught():
    assert _gate(_LyingBackend(_NON_UNIVERSAL)).check(_walnut_prop()).verdict is Verdict.DEFER


def test_lying_backend_bare_true_fabrication_is_caught():
    # The exact laundering class the adjudicator reproduced: fabricated data="true".
    assert _gate(_LyingBackend("true")).check(_walnut_prop()).verdict is Verdict.DEFER


# --- completeness: the partial/dangling/non-deterministic laundering classes ------------
# (the second review reproduced these as false-PASS paths; they must all DEFER, never pass)

_PARTIAL = "msd_2\n\n0 1\n0 -> 0\n"                       # accepting, but no transition on digit 1
_DANGLING = "msd_2\n\n0 1\n0 -> 7\n1 -> 7\n"             # transitions to an undeclared state 7
_NONDET = "msd_2\n\n0 1\n0 -> 0\n0 -> 1\n1 -> 0\n\n1 1\n0 -> 0\n1 -> 0\n"  # dup label on state 0
_UNKNOWN_NUM = "pell_x\n\n0 1\n0 -> 0\n1 -> 0\n"          # numeration alphabet we don't model


def test_partial_automaton_is_not_universal():
    # one accepting state with only the digit-0 branch: under msd_2 it rejects every n with
    # a '1' -> the agreement automaton of a FALSE claim. Must NOT be judged universal.
    assert recheck_walnut_certificate(_cert(_PARTIAL)) is False
    assert _gate(_LyingBackend(_PARTIAL)).check(_walnut_prop()).verdict is Verdict.DEFER


def test_dangling_edge_is_not_universal():
    assert recheck_walnut_certificate(_cert(_DANGLING)) is False
    assert _gate(_LyingBackend(_DANGLING)).check(_walnut_prop()).verdict is Verdict.DEFER


def test_nondeterministic_is_not_universal():
    assert recheck_walnut_certificate(_cert(_NONDET)) is False


def test_unknown_numeration_defers():
    # we cannot model the alphabet -> completeness unverifiable -> never universal.
    assert recheck_walnut_certificate(_cert(_UNKNOWN_NUM)) is False


def test_backend_partial_result_defers_not_fails():
    # an incomplete automaton is "indeterminate", not "refuted": DEFER, never FAIL/PASS.
    assert WalnutBackend(runner=lambda *a, **k: _PARTIAL).check(_walnut_prop()).verdict is Verdict.DEFER


# A universal automaton over a DIFFERENT numeration than the prop requested (msd_2).
_UNIVERSAL_MSD3 = "msd_3\n\n0 1\n0 -> 0\n1 -> 0\n2 -> 0\n"


def test_backend_defers_on_numeration_mismatch():
    # partial prop-bind: a genuinely-universal automaton over the WRONG numeration must not
    # pass for an msd_2 claim.
    b = WalnutBackend(runner=lambda *a, **k: _UNIVERSAL_MSD3)
    assert b.check(_walnut_prop()).verdict is Verdict.DEFER


# --- injection: untrusted predicate/numeration cannot break out of the eval -------------

def test_unsafe_inputs_are_rejected():
    from leibniz.backends.walnut import _safe_walnut_inputs
    assert _safe_walnut_inputs("Ai i=i", "msd_2") is True
    # quote/semicolon/newline let a predicate close the eval and inject a second command
    assert _safe_walnut_inputs('x"; eval leibniz_faith "?msd_2 i=i', "msd_2") is False
    assert _safe_walnut_inputs("Ai i=i; reg foo", "msd_2") is False
    assert _safe_walnut_inputs("Ai i=i", 'msd_2"; eval x "?msd_2 i=i') is False
    assert _safe_walnut_inputs("Ai i=i", "not a numeration") is False


def test_default_runner_defers_on_injection_attempt(tmp_path, monkeypatch):
    # Even with a live (fake) Walnut, an injecting predicate must DEFER before invocation.
    jar, java, _ = _fake_walnut_home(tmp_path, "echo true > Result/leibniz_faith.txt\nexit 0\n")
    monkeypatch.setenv("LEIBNIZ_WALNUT_JAR", str(jar))
    monkeypatch.setattr(walnut.shutil, "which", lambda _name: str(java))
    assert walnut._default_runner('x"; eval leibniz_faith "?msd_2 i=i', "msd_2") is None


# --- default runner: freshness + exit-code guard (real subprocess, fake java/home) ----
#
# The real _default_runner is the one piece the injected-runner tests above don't cover,
# because the binary is injected everywhere else. Here we stand up a fake Walnut home
# (so home == jar.parent.parent.parent) and a fake `java` executable, and assert the
# runner DEFERs (returns None) rather than reading a STALE fixed-name result file. This
# only tightens the runner toward DEFER; it never loosens it.

def _fake_walnut_home(tmp_path, java_script):
    """Build a fake Walnut home + an executable fake `java` running ``java_script``.

    Returns ``(jar, java, result)`` where ``result`` is the fixed-name result file the
    runner reads (``home/Result/leibniz_faith.txt``), computed via the SAME
    ``jar.resolve().parent.parent.parent`` formula the runner uses so paths match on
    macOS (where ``/var`` -> ``/private/var``)."""
    libs = tmp_path / "build" / "libs"
    libs.mkdir(parents=True)
    jar = libs / "Walnut-all.jar"
    jar.write_text("")  # must merely exist; the fake java ignores its contents
    home = jar.resolve().parent.parent.parent
    result = home / "Result" / "leibniz_faith.txt"
    result.parent.mkdir(parents=True, exist_ok=True)
    java = tmp_path / "fakejava"
    java.write_text("#!/bin/sh\n" + java_script)
    java.chmod(java.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return jar, java, result


def test_default_runner_defers_on_nonzero_exit_not_stale_text(tmp_path, monkeypatch):
    # A prior eval left a stale 'true' in the fixed-name result file. Walnut now FAILS
    # (nonzero exit) — and even re-writes 'true' into that file. A clean exit is REQUIRED
    # to trust the file, so the runner must DEFER, never read the 'true' back.
    jar, java, result = _fake_walnut_home(
        tmp_path, "echo true > Result/leibniz_faith.txt\nexit 3\n"
    )
    result.write_text("true")  # stale result from a PRIOR run
    monkeypatch.setenv("LEIBNIZ_WALNUT_JAR", str(jar))
    monkeypatch.setattr(walnut.shutil, "which", lambda _name: str(java))

    out = walnut._default_runner("Ai i=i", "msd_2", timeout=30.0)

    assert out is None  # nonzero exit => DEFER, not the 'true' sitting on disk


def test_default_runner_deletes_stale_result_before_run(tmp_path, monkeypatch):
    # Walnut exits 0 but writes NOTHING (it silently produced no result). The pre-existing
    # stale 'true' must have been removed up front, so there is nothing to mis-read => DEFER.
    jar, java, result = _fake_walnut_home(tmp_path, "exit 0\n")
    result.write_text("true")  # stale result from a PRIOR run
    monkeypatch.setenv("LEIBNIZ_WALNUT_JAR", str(jar))
    monkeypatch.setattr(walnut.shutil, "which", lambda _name: str(java))

    out = walnut._default_runner("Ai i=i", "msd_2", timeout=30.0)

    assert out is None             # no fresh output => DEFER
    assert not result.exists()     # the stale file was deleted, never left to be re-read


def test_default_runner_defers_when_jar_not_in_build_libs(tmp_path, monkeypatch):
    # ADR 0037 §7 hardening: a jar NOT in <home>/build/libs/ has no reliable home -> DEFER,
    # never a wrong cwd / stale read.
    jar = tmp_path / "Walnut-all.jar"      # directly in tmp, not build/libs/
    jar.write_text("")
    java = tmp_path / "fakejava"
    java.write_text("#!/bin/sh\necho true > Result/leibniz_faith.txt\nexit 0\n")
    java.chmod(java.stat().st_mode | stat.S_IXUSR)
    monkeypatch.setenv("LEIBNIZ_WALNUT_JAR", str(jar))
    monkeypatch.delenv("LEIBNIZ_WALNUT_HOME", raising=False)
    monkeypatch.setattr(walnut.shutil, "which", lambda _name: str(java))
    assert walnut._default_runner("Ai i=i", "msd_2", timeout=30.0) is None


def test_walnut_home_override(tmp_path, monkeypatch):
    # $LEIBNIZ_WALNUT_HOME explicitly locates the home regardless of jar layout.
    jar = tmp_path / "anywhere" / "Walnut-all.jar"
    jar.parent.mkdir(parents=True)
    jar.write_text("")
    monkeypatch.setenv("LEIBNIZ_WALNUT_HOME", str(tmp_path))
    assert walnut._walnut_home(jar) == tmp_path
    monkeypatch.delenv("LEIBNIZ_WALNUT_HOME", raising=False)
    assert walnut._walnut_home(jar) is None  # not in build/libs, no override -> None


def test_default_runner_returns_fresh_result_on_clean_exit(tmp_path, monkeypatch):
    # Sanity floor: a clean exit that DOES write the result returns that fresh text — the
    # guard rejects stale/failed runs without blocking legitimate ones.
    jar, java, result = _fake_walnut_home(
        tmp_path, "echo true > Result/leibniz_faith.txt\nexit 0\n"
    )
    monkeypatch.setenv("LEIBNIZ_WALNUT_JAR", str(jar))
    monkeypatch.setattr(walnut.shutil, "which", lambda _name: str(java))

    out = walnut._default_runner("Ai i=i", "msd_2", timeout=30.0)

    assert out is not None and out.strip() == "true"
