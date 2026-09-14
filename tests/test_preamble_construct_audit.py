"""ADR 0099 -- the preamble audit must go RED on the attacks it exists to catch.

A green audit is worth nothing on its own. These tests are the evidence that it is non-vacuous, and
in particular they pin the SEVEN working bypasses an adversarial review found in the audit's first
version. Every one of them reported CLEAN and let `theorem oops : False := trivial` elaborate on
`leanprover/lean4:v4.34.0-rc2` with an empty axiom closure.

What these tests do NOT claim: that the lint is sound. It is an authoring aid. The enforcement is
the hash pin -- see `test_pin_*` below -- and `tests/test_native_eval_redteam.py` keeps its strict
xfail for the statement-meaning class, which remains open.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import pathlib
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "audit_preamble_constructs.py"
PINS = ROOT / "docs" / "audits" / "preamble-pins.json"


def _fresh():
    """A FRESH module per case, so findings never leak between tests."""
    spec = importlib.util.spec_from_file_location("_preamble_audit", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _audit(preamble: str) -> list[str]:
    mod = _fresh()
    mod.audit("<case>", preamble)
    return [why for _, why in mod.findings]


# --- the seven bypasses of the FIRST version of this audit, each confirmed against real Lean -----
#
# Root causes: (A) the comment stripper desynced from Lean's lexer, (B) namespace balance was a
# line-anchored count, (C) the core-name check could not see guillemet names, (D) the command scan
# skipped indented lines, (E) CORE_NAMES omitted Nat.
BYPASSED = [
    pytest.param('def «z/-» := 1\nnotation "False" => True', id="A1-guillemet-hides-block-comment"),
    pytest.param('def s := s!"{"/-"}"\nnotation "False" => True', id="A2-interpolation-hides-block-comment"),
    pytest.param('namespace Foo\n  section\ndef «False» := True\nend', id="B1-indented-section-eats-the-end"),
    pytest.param('def a := 1 namespace Foo\ndef «False» := True', id="B2-mid-line-namespace"),
    pytest.param('namespace Foo\ndef note : String := "\nend\n"\ndef «False» := True', id="B3-string-supplies-the-end"),
    pytest.param('namespace Foo\ndef «False» := True\nend Foo', id="C-guillemet-core-name"),
    pytest.param("  axiom bad : False", id="D-one-leading-space-defeats-the-scan"),
    pytest.param("def a := 1 namespace Foo\ndef Nat := Unit", id="E-shadow-Nat-no-guillemets-needed"),
]


@pytest.mark.parametrize("preamble", BYPASSED)
def test_known_bypass_is_now_refused(preamble: str) -> None:
    assert _audit(preamble), f"REGRESSION -- this bypass is clean again: {preamble!r}"


REFUSED = [
    pytest.param('notation "False" => True', "notation", id="round8-notation-redefinition"),
    pytest.param('  notation "True" => False', "notation", id="notation-indented"),
    pytest.param("namespace Foo\ndef False := True", "scope", id="unclosed-namespace"),
    pytest.param("open Classical", "open", id="open"),
    pytest.param("attribute [simp] foo", "attribute", id="attribute"),
    pytest.param("macro_rules | `(x) => `(y)", "macro_rules", id="macro-rules"),
    pytest.param('infixl:65 " +++ " => Nat.add', "infixl", id="infix"),
    pytest.param("set_option pp.all true", "resource allowlist", id="elaborator-set-option"),
    pytest.param("axiom smuggled : False", "axiom", id="axiom"),
    pytest.param("variable (h : False)", "variable", id="variable"),
    pytest.param("unsafe def loop : False := loop", "unsafe", id="unsafe"),
]


@pytest.mark.parametrize("preamble,expect", REFUSED)
def test_meaning_changing_preamble_is_a_finding(preamble: str, expect: str) -> None:
    findings = _audit(preamble)
    assert findings, f"audit passed a preamble it must refuse: {preamble!r}"
    assert any(expect in f for f in findings), f"wrong reason for {preamble!r}: {findings}"


ALLOWED = [
    pytest.param("set_option maxRecDepth 8000\ndef f (n : Nat) := n", id="resource-option-and-def"),
    pytest.param("namespace SO_cube\ndef g := 1\nend SO_cube", id="balanced-namespace"),
    pytest.param("abbrev Eis := Int\ntheorem t : True := trivial", id="abbrev-and-theorem"),
    pytest.param('-- notation "False" => True\ndef a := 1', id="line-comment-is-not-a-command"),
    pytest.param('/- notation "False" => True -/\ndef a := 1', id="block-comment-is-not-a-command"),
    # The corpus really does wrap declarations; a positional scan flagged these as commands.
    pytest.param("def h (v : List Nat) : Bool :=\n  !(v.contains 3) && true", id="continuation-lines"),
]


@pytest.mark.parametrize("preamble", ALLOWED)
def test_legitimate_preamble_is_clean(preamble: str) -> None:
    assert _audit(preamble) == []


def test_string_literals_are_not_stripped_for_the_keyword_scan() -> None:
    """Documented false positive: erring loud beats trusting a string-scanner (see the docstring)."""
    assert _audit('def m : String := "open sesame"'), "the lint is documented to err loud here"


# --- the pin is the enforcement ------------------------------------------------------------------

def test_pin_manifest_covers_every_live_preamble() -> None:
    mod = _fresh()
    corpus = mod.collect()
    assert corpus, "VACUOUS -- no preambles found at all"
    pins = json.loads(PINS.read_text(encoding="utf-8"))["pins"]
    assert set(corpus) == set(pins), "pin manifest and corpus disagree"
    for where, pre in corpus.items():
        assert pins[where] == hashlib.sha256(pre.encode("utf-8")).hexdigest(), f"stale pin: {where}"


def test_pin_catches_a_silent_edit_the_lint_would_miss() -> None:
    """The pin's whole purpose: it holds even where the lint is fooled.

    A one-character edit inside an existing definition changes what the law proves while using only
    allowlisted constructs, so no keyword scan can object. The hash does.
    """
    mod = _fresh()
    where, pre = sorted(mod.collect().items())[0]
    pins = json.loads(PINS.read_text(encoding="utf-8"))["pins"]
    tampered = pre + "\n"                      # the smallest possible silent change
    assert _audit(tampered) == [], "expected the LINT to be blind to this edit"
    assert pins[where] != hashlib.sha256(tampered.encode("utf-8")).hexdigest(), "pin must differ"


def test_live_corpus_is_clean_and_the_audit_is_not_vacuous() -> None:
    r = subprocess.run([sys.executable, str(SCRIPT)], capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0, f"live corpus has findings:\n{r.stdout}\n{r.stderr}"
    assert "preambles checked: 0" not in r.stdout, "audit is VACUOUS -- it found no preambles"
    assert "pinned: 0" not in r.stdout, "pin manifest is empty -- the enforcement is not running"


# --- the pin's collection must not lose preambles (second adversarial round) ---------------------
#
# `collect()` first keyed by FILE, so it kept only the last preamble it walked into. Either shape
# below let a hostile preamble reach the kernel while never being linted and never being pinned --
# defeating both mechanisms at once. Keyed by JSON path now.

def _collect_in(tmp_path, monkeypatch, name: str, payload: dict) -> dict:
    (tmp_path / name).write_text(json.dumps(payload), encoding="utf-8")
    mod = _fresh()
    monkeypatch.setattr(mod, "ROOT", tmp_path)
    monkeypatch.setattr(mod, "PINS", tmp_path / "pins.json")
    return mod.collect()


HOSTILE = 'notation "False" => True'
BENIGN = "def helper : Nat := 0"


def test_collect_sees_every_preamble_in_a_multi_law_file(tmp_path, monkeypatch):
    """Ledger shape. Measured before the fix: only the LAST preamble survived."""
    got = _collect_in(tmp_path, monkeypatch, "ledger.json",
                      {"laws": [{"id": "evil", "preamble": HOSTILE},
                                {"id": "last", "preamble": BENIGN}]})
    assert len(got) == 2, f"a preamble was dropped: {got}"
    assert HOSTILE in got.values(), "the hostile preamble was never collected"


def test_collect_does_not_let_a_nested_key_overwrite_the_law(tmp_path, monkeypatch):
    """`law_payload` emits sub-objects; a `preamble` inside one silently repointed the pin."""
    got = _collect_in(tmp_path, monkeypatch, "law.json",
                      {"preamble": HOSTILE, "novelty_attestation": {"preamble": BENIGN}})
    assert len(got) == 2, f"a preamble was dropped: {got}"
    assert HOSTILE in got.values(), "the top-level preamble was overwritten by a nested one"


def test_every_collected_preamble_is_linted(tmp_path, monkeypatch):
    """Collection and linting must agree: whatever reaches the kernel must reach the lint."""
    got = _collect_in(tmp_path, monkeypatch, "ledger.json",
                      {"laws": [{"preamble": HOSTILE}, {"preamble": BENIGN}]})
    refused = [k for k, v in got.items() if _audit(v)]
    assert len(refused) == 1, f"expected exactly the hostile preamble refused, got {refused}"


def test_pin_keys_are_stable_across_an_edit(tmp_path, monkeypatch):
    """Keyed by path, not by content -- otherwise an edit reads as a new pin plus a stale one,
    and a PIN MISMATCH (the thing that catches a silent edit) could never be reported."""
    before = _collect_in(tmp_path, monkeypatch, "law.json", {"preamble": BENIGN})
    after = _collect_in(tmp_path, monkeypatch, "law.json", {"preamble": BENIGN + "\ndef b := 1"})
    assert set(before) == set(after), "editing a preamble changed its pin key"
