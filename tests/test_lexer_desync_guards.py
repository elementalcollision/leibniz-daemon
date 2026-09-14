"""A guard must not scan text the lexer already swallowed.

Found by adversarial review of the ADR 0099 preamble audit; the defect was NOT in that audit, it was
here, in `_strip_comments`, which five guards share -- two of them scanning PROPOSER-authored text.
The fix belongs with the guards, so it lands with ADR 0097 rather than with the audit that found it.

Lean lexes `def «z/-» := 1` as ONE identifier. The stripper treated `«` as ordinary punctuation, let
the `/-` inside the name open a block comment, and returned `def «z` -- so every guard below it
scanned text Lean would never see. Measured before the fix, on the pinned 4.34:

    statement_is_single_declaration('theorem «a/-» : True := trivial\\n'
                                    'namespace M\\ntheorem catastrophe : False := lie')  -> True
    smuggles_top_level('by «q/-»\\nrun_cmd IO.println "hi"')                             -> False

That is the ADR 0097 round-3 namespace-move shape passing the guard built to stop it. It was NOT
driven to `Q.E.D.`: the fresh probe name (round 3) and the kernel replay (ADR 0098) both still held,
which is precisely the argument for having them. A guard returning a confidently wrong answer is
still a defect -- its whole value is being right when the layers above it are not.
"""
from __future__ import annotations

from leibniz.backends.lean_axioms import (
    _strip_comments,
    closes_more_than_it_opens,
    declaration_name,
    defeats_the_kernel,
    smuggles_top_level,
    statement_is_single_declaration,
    unterminated_block_comment,
    uses_string_interpolation,
)

WHY = "a guard must not scan text the lexer already swallowed"


def test_guillemet_identifier_does_not_open_a_comment():
    """`«z/-»` is one identifier to Lean. The stripper must not read the `/-` inside it."""
    assert "notation" in _strip_comments('def «z/-» := 1\nnotation "False" => True'), WHY


def test_statement_is_single_declaration_refuses_the_desync():
    """Measured before the fix: True for a THREE-declaration smuggle."""
    evil = 'theorem «a/-» : True := trivial\nnamespace M\ntheorem catastrophe : False := lie'
    assert statement_is_single_declaration(evil) is False, WHY


def test_smuggles_top_level_refuses_the_desync():
    """Measured before the fix: False -- 'nothing smuggled' -- for a `run_cmd`."""
    assert smuggles_top_level('by «q/-»\nrun_cmd IO.println "hi"') is True, WHY


def test_unterminated_block_comment_is_the_general_symptom():
    """Chasing each construct that can hide a `/-` is the losing half of the game.

    An unterminated block comment is the symptom of ANY such desync, whatever caused it -- including
    `s!"{"/-"}"`, which no amount of guillemet handling would have caught -- and no honest
    declaration has one. That is why the guards key off this rather than off a list of constructs.
    """
    assert unterminated_block_comment('def s := s!"{"/-"}"') is True, WHY
    assert unterminated_block_comment('def a := 1 -- fine\n/- nested /- ok -/ -/ def b := 2') is False


def test_every_guard_that_shares_the_lexer_fails_closed():
    """All five, not just the two that were measured wrong -- the next desync may reach any of them."""
    # A REAL desync -- an unterminated block comment. Note `theorem «t/-» : ...` is NOT one any
    # more: `«t/-»` is genuinely the Lean name, and the guards are now right to accept it.
    desync = 'theorem t : True := trivial /- swallowed'
    assert declaration_name(desync) is None, WHY
    assert statement_is_single_declaration(desync) is False, WHY
    assert smuggles_top_level(desync) is True, WHY
    assert closes_more_than_it_opens(desync) is True, WHY
    assert defeats_the_kernel(desync) is True, WHY


def test_honest_sources_are_unaffected():
    """The round-2 string-literal behaviour and ordinary comments must be untouched.

    A fail-closed check that fires on legitimate input is a new outage, not a fix.
    """
    assert '"/-"' in _strip_comments('have s : String := "/-"\nnamespace M')
    assert 'r"/-"' in _strip_comments('have s := r"/-"')
    assert statement_is_single_declaration("theorem t : True := trivial") is True
    assert smuggles_top_level("by simp") is False
    assert closes_more_than_it_opens("by simp") is False
    assert declaration_name("theorem foo.bar : True := trivial") == "foo.bar"
    assert unterminated_block_comment("theorem t : True := by\n  simp -- done") is False


# --- round 9b: the same lexer did not know CHARACTER literals -------------------------------
#
# Found by a second adversarial round, against the round-9 fix above. `_lex` skipped strings and
# guillemets but not `'c'`, so the `"` inside `'"'` opened a phantom string. One defect, and it cut
# BOTH ways: it hid a smuggled command from the guards, and it made the new fail-closed check refuse
# an honest theorem. The second is the worse failure -- a fail-closed check that fires on legitimate
# input is a new outage introduced by a fix.

_F1_THEOREM = "theorem oops : (2:Nat)^20 = 1048576"
_F1_PROOF = '''(fun (_ : Char) => by native_decide) '"' -- "
) macro_rules | `(@$_:ident) => `(True.intro'''


def test_9b_char_literal_does_not_open_a_phantom_string():
    """`'\"'` is one token. Reading its quote as a string start desynced everything after it."""
    assert unterminated_block_comment('''def c : Char := '"' ''') is False, WHY
    assert '"/-"' in _strip_comments('''def c := '"'\ntheorem t : "/-".length = 2 := by decide''')


def test_9b_honest_law_about_quote_characters_is_not_refused():
    """The regression the fix introduced: this elaborates fine on the pinned 4.34 and was REFUSED.

    Any honest statement with an odd number of `"`-bearing char literals ahead of a string
    containing `/-` tripped the new fail-closed check.
    """
    honest = '''theorem honest (c : Char := '"') : "/-".length = 2 := by decide'''
    assert unterminated_block_comment(honest) is False, "honest law refused -- outage, not a fix"
    assert declaration_name(honest) == "honest"
    assert statement_is_single_declaration(honest) is True
    # `smuggles_top_level` guards proof_src, so give it the PROOF -- handing it a whole
    # theorem would (correctly) report a top-level declaration.
    assert smuggles_top_level('by decide') is False


def test_9b_confinement_escape_behind_a_char_literal_is_refused():
    """The round-4 hijack shape, reached by hiding the wrapper-closing `)` behind `'\"'`.

    Measured before the fix: every guard passed and `check_proof` returned True for a
    `native_decide` proof. The mint still refused it (ADR 0098's reporter reads every constant),
    but the confinement layer contributed nothing.

    Asserts the GATE the backends actually evaluate, not one guard: `smuggles_top_level` is still
    blind here -- the smuggled `macro_rules` sits mid-line after `)`, and a keyword scan cannot find
    command position without parsing. `closes_more_than_it_opens` is what refuses it, which is the
    point of having more than one.
    """
    assert closes_more_than_it_opens(_F1_PROOF) is True, WHY
    refused = (not declaration_name(_F1_THEOREM)
               or smuggles_top_level(_F1_PROOF)
               or closes_more_than_it_opens(_F1_PROOF)
               or defeats_the_kernel(_F1_PROOF)
               or defeats_the_kernel(_F1_THEOREM))
    assert refused is True, "the backend gate admitted a confinement escape"


def test_9b_unmatched_guillemet_does_not_swallow_the_rest():
    """A stray `«` consumed to EOF, hiding a genuinely open `/-` so the depth check never fired."""
    assert unterminated_block_comment("def x := '«'\n/- never closed") is True, WHY
    assert unterminated_block_comment("def x := «\n/- never closed") is True, WHY


def test_9b_primes_are_not_char_literals():
    """`'` ends identifiers too. Treating `h'` as a literal opener would desync in the other
    direction -- this is why the skipper refuses a quote preceded by an identifier character."""
    assert declaration_name("theorem foo' : True := trivial") == "foo'"
    assert smuggles_top_level("by simpa using h'.mp h''") is False
    assert unterminated_block_comment("theorem t (h' : True) : True := h'") is False


# --- round 9c: string interpolation, the third construct in three rounds ---------------------
#
# `_skip_string` reads `s!"{f "a--b"}"` as the string `"{f "` followed by live code, because an
# interpolation's `{...}` may contain its own string literals and this lexer does not recurse. The
# `--` inside the nested string then opened a line comment that swallowed a wrapper-closing `)` AND
# a smuggled `macro_rules` on the same line.
#
# Measured on the pin: the assembled declaration elaborates, `macro_rules` becomes a top-level
# command, and `#print axioms oops` reports `oops._native.native_decide.ax_1_1`. The MINT still
# refused it (kernel_verified=False, Q.E.I.; the ADR 0097 reporter named the native axiom), so the
# trust boundary held -- but the confinement layer contributed nothing, for the third round running.

_9C_THEOREM = "theorem oops : (2:Nat)^20 = 1048576"
_9C_PROOF = ('(fun (_ : String) => by native_decide) s!"{id "x--"}" ) '
             'macro_rules | `(@$_:ident) => `(True.intro')


def test_9c_interpolation_is_refused_rather_than_parsed():
    """Recursing into Lean's term grammar is the losing half of this game. Refuse instead."""
    assert uses_string_interpolation('def m := s!"{f "a--b"}"') is True
    assert uses_string_interpolation('theorem t : True := trivial') is False
    assert uses_string_interpolation('have s : String := "plain"') is False, "a plain string is not one"


def test_9c_confinement_escape_behind_an_interpolation_is_refused():
    """Asserts the GATE the backends evaluate, which is what actually decides."""
    refused = (not declaration_name(_9C_THEOREM)
               or smuggles_top_level(_9C_PROOF)
               or closes_more_than_it_opens(_9C_PROOF)
               or defeats_the_kernel(_9C_PROOF)
               or defeats_the_kernel(_9C_THEOREM)
               or not statement_is_single_declaration(_9C_THEOREM))
    assert refused is True, "the backend gate admitted the round-9c confinement escape"


def test_9c_every_guard_fails_closed_on_interpolation():
    src = 'by exact (s!"{f "x--y"}" ▸ rfl)'
    assert smuggles_top_level(src) is True
    assert closes_more_than_it_opens(src) is True
    assert defeats_the_kernel(src) is True
    assert declaration_name('theorem t : s!"{x}" = "" := rfl') is None
    assert statement_is_single_declaration('theorem t : s!"{x}" = "" := rfl') is False


def test_9c_no_published_law_uses_interpolation():
    """The refusal is only free because nothing honest needs it. If this ever fails, the decision
    to refuse rather than parse has to be revisited -- do not just widen the regex."""
    import glob
    import json
    for p in sorted(glob.glob("site/src/content/laws/*.json")):
        d = json.load(open(p))
        for k in ("theorem_src", "proof_src", "preamble"):
            assert not uses_string_interpolation(d.get(k) or ""), f"{p} {k} uses interpolation"
