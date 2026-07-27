"""ADR 0078 — a candidate carries every hash scheme it could be KNOWN under.

`pipeline._normalized_hash` prefers the wired backend's elaborator-canonical hash and falls back
to the textual one, so the novelty key silently changed scheme when the daemon moved from the CLI
backend to the REPL. Giving the REPL a normalizer (so alpha-renamed statements collide again)
flips the scheme back — which on its own would make every law stored under the *other* scheme
invisible to ADR 0052 self-dedup. A candidate therefore carries both keys.
"""
from __future__ import annotations

from leibniz.corpus import CorpusBackend, CorpusEntry
from leibniz.types import ClaimSignature, ClaimType


def _corpus(*hashes):
    return CorpusBackend([CorpusEntry(name=f"ledger:l{i}", claim_type="invariant",
                                      subject="daemon_ledger", relation="promulgated",
                                      formal_hash=h) for i, h in enumerate(hashes)])


def _sig(primary, *alts):
    return ClaimSignature(claim_type=ClaimType.INVARIANT, subject="s", relation="r",
                          formal_hash=primary, alt_hashes=tuple(alts))


def test_a_law_stored_under_the_other_scheme_is_still_known():
    """The regression this exists to prevent: primary misses, alternate hits."""
    assert _corpus("TEXTUAL").contains_equivalent(_sig("ELABORATOR", "TEXTUAL")) is True
    assert _corpus("ELABORATOR").contains_equivalent(_sig("ELABORATOR", "TEXTUAL")) is True


def test_a_genuinely_new_claim_is_still_novel():
    """Extra keys must not make unrelated claims collide — each is an exact identity."""
    assert _corpus("TEXTUAL", "ELABORATOR").contains_equivalent(_sig("OTHER", "ALSO_OTHER")) is False


def test_empty_hashes_never_match():
    """A candidate we could not normalize is NOVEL, not silently KNOWN."""
    assert _corpus("").contains_equivalent(_sig("", "")) is False
    assert _corpus("TEXTUAL").contains_equivalent(_sig("", "")) is False


def test_signatures_without_alt_hashes_behave_exactly_as_before():
    assert _corpus("H").contains_equivalent(_sig("H")) is True
    assert _corpus("H").contains_equivalent(_sig("X")) is False
