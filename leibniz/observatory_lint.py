"""Observatory faithfulness lint (ADR 0039) — a BOUNDED, SOUND cross-check that a
Walnut-DECIDED-true predicate is faithful to the property the conjecturer says it encodes.

The motivating failure (first live run, ``docs/observatory-first-run-finding.md``): Walnut
soundly decides the *predicate*, but the conjecturer's English→FO encoding mis-states the
bound (``t<4p`` for "4th-power-free", ``i<n+4`` for "length-4 factor"), so the predicate is a
DIFFERENT — true — statement while the prose claim is FALSE. Walnut cannot catch this: it
faithfully decides whatever predicate it is handed. The gap is *formal-statement ↔ intent*, on
the proposal side.

This module closes that gap for the common finitary property families with a CHEAP, SOUND
necessary check: the conjecturer co-emits a structured ``property_descriptor`` (a high-level
spec — ``power_free`` exponent 4 — that does NOT contain the error-prone bound arithmetic), and
we brute-force it over a finite PREFIX of the sequence. A prefix counterexample to a property
the predicate was DECIDED-true on is a genuine refutation of faithfulness ⇒ quarantine.

Soundness posture (mirrors the bounded-Z3-as-lint demotion, ADR 0037):
  * the lint can ONLY downgrade a DECIDED-true to quarantine — it never certifies, never
    upgrades, never sets any kernel/promotion state. A clean prefix is NOT a proof.
  * absence of a usable descriptor ⇒ "undescribable" ⇒ the caller may refuse to file DECIDED
    (the formal-first record has no machine-checkable anchor). DEFER is the safe default.
  * the sequence generators below MUST match Walnut's built-in word definitions exactly, or the
    cross-check compares the wrong sequence. They are pinned to canonical definitions and
    adversarially verified (popcount / morphism fixed points; see tests + the finding doc).

Stdlib-only. No Walnut, no LLM, no I/O.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable, Optional

# --- canonical built-in automatic sequences (MUST match Walnut's words) ------------------
# Each returns the first `n` terms as a list[int] over the word's natural alphabet. These are
# the soundness root of the whole lint: a wrong generator silently makes the cross-check
# meaningless. Definitions are the standard ones Walnut ships (Shallit's `Walnut` words).


def _thue_morse(n: int) -> list[int]:
    """T[k] = parity of the number of 1-bits in the binary expansion of k. T = 0110100110010110…"""
    return [bin(k).count("1") & 1 for k in range(n)]


def _rudin_shapiro(n: int) -> list[int]:
    """RS[k] = parity of the number of (possibly overlapping) '11' blocks in base-2 of k.
    RS = 0001001000011101… (RS[7..10] = 0,0,0,0 — the period-1 4th power that refutes '4th-power-free')."""
    out = []
    for k in range(n):
        b = bin(k)[2:]
        out.append(sum(1 for i in range(len(b) - 1) if b[i] == "1" and b[i + 1] == "1") & 1)
    return out


def _morphic(n: int, rules: dict[int, list[int]], start: int = 0) -> list[int]:
    """First `n` letters of the fixed point of a morphism starting at `start` (its prefix is
    extended by repeatedly substituting until long enough — the standard fixed-point limit)."""
    seq = [start]
    # Iterate the substitution; the fixed point's length-n prefix stabilises once len >= n.
    while len(seq) < n:
        nxt: list[int] = []
        for c in seq:
            nxt.extend(rules[c])
        if len(nxt) == len(seq):  # not growing (defensive — would loop forever otherwise)
            break
        seq = nxt
    return seq[:n]


def _fibonacci_word(n: int) -> list[int]:
    """Fixed point of 0->01, 1->0. F = 0100101001001…"""
    return _morphic(n, {0: [0, 1], 1: [0]})


def _tribonacci_word(n: int) -> list[int]:
    """Fixed point of 0->01, 1->02, 2->0. TR = 0102010010201…"""
    return _morphic(n, {0: [0, 1], 1: [0, 2], 2: [0]})


# Canonical word symbol -> generator. Aliases map the names the conjecturer / Walnut use.
WORD_GENERATORS: dict[str, Callable[[int], list[int]]] = {
    "T": _thue_morse, "TM": _thue_morse, "THUEMORSE": _thue_morse,
    "RS": _rudin_shapiro, "RUDINSHAPIRO": _rudin_shapiro,
    "F": _fibonacci_word, "FIB": _fibonacci_word, "FIBONACCI": _fibonacci_word,
    "TR": _tribonacci_word, "TRIB": _tribonacci_word, "TRIBONACCI": _tribonacci_word,
    # Paperfolding (P/PF/FOLD) is intentionally UNSUPPORTED in v1: its sign/definition
    # conventions are subtle, and an unsupported word safely DEFERS (no DECIDED) rather than
    # risk an unsound generator. See ADR 0039 "future work".
}


def _canon_word(word: str) -> Optional[str]:
    key = "".join(ch for ch in str(word).upper() if ch.isalpha())
    return key if key in WORD_GENERATORS else None


# Each supported word's alphabet — used to reject descriptors that ask about symbols the word
# cannot contain (a block "9999" over a binary word trivially "never occurs", a false anchor).
WORD_ALPHABET: dict[str, frozenset[int]] = {
    "T": frozenset({0, 1}), "RS": frozenset({0, 1}), "F": frozenset({0, 1}),
    "TR": frozenset({0, 1, 2}),
}


def _word_alphabet(canon: str) -> frozenset[int]:
    return WORD_ALPHABET.get(_canon_word(canon) or "", frozenset())


# Sanity caps: a descriptor parameter beyond these is degenerate (a vacuous "true" anchor and a
# likely parameter-shop). Real power-free / pattern claims use single-digit parameters.
_MAX_EXPONENT = 64
_MAX_PATTERN_LEN = 64


# --- binding the descriptor to the predicate (ADR 0039 review fix) -----------------------
# A lint pass must attest something about the predicate Walnut DECIDED, not an unrelated word.
# So the descriptor's word MUST be exactly the word(s) the predicate indexes. Without this, a
# descriptor naming a DIFFERENT sequence (Thue-Morse) than the predicate (Rudin-Shapiro) would
# brute-force the wrong sequence and pass a real artifact (the high-severity review finding).
_INDEX_RE = re.compile(r"([A-Za-z][A-Za-z0-9_]*)\s*\[")


def predicate_indexed_words(predicate: Optional[str]) -> list[str]:
    """The raw word symbols indexed (``W[...]``) in a Walnut predicate. In Walnut only *words*
    are indexed with ``[`` — variables appear only in arithmetic/comparisons — so this reliably
    recovers which sequence(s) the predicate is about."""
    return _INDEX_RE.findall(predicate or "")


def descriptor_binds_predicate(descriptor: dict, predicate: Optional[str]) -> bool:
    """True iff the descriptor's (canonical) word is EXACTLY the set of words the predicate
    indexes. Requires the predicate to index ≥1 word and every indexed word to canon-match the
    descriptor's word (a predicate over two distinct words, or over a word the descriptor does
    not name, cannot be anchored by a single-word descriptor ⇒ not bound)."""
    dw = _canon_word(descriptor.get("word", ""))
    if dw is None:
        return False
    raws = predicate_indexed_words(predicate)
    if not raws:
        return False
    # Unknown/unsupported indexed words (e.g. paperfolding ``P``) stay distinct from dw, so a
    # predicate that indexes them fails to bind to a supported-word descriptor.
    canon = {(_canon_word(w) or w.upper()) for w in raws}
    return canon == {dw}


# --- lint result ------------------------------------------------------------------------

@dataclass(frozen=True)
class LintResult:
    """Outcome of the bounded faithfulness cross-check.

    ``status``:
      * ``"pass"``         — no prefix counterexample; the DECIDED-true verdict is *consistent*
                             with the descriptor over the checked prefix (NOT a proof).
      * ``"counterexample"`` — a prefix counterexample exists ⇒ the predicate is NOT faithful to
                             the stated property ⇒ the caller MUST quarantine, never file DECIDED.
      * ``"undescribable"`` — no usable descriptor (missing / unknown family / unsupported word /
                             bad params) ⇒ no machine-checkable anchor; caller decides (the
                             production tier refuses DECIDED; see ADR 0039).
    """

    status: str
    prefix_checked: int = 0
    detail: dict = field(default_factory=dict)

    @property
    def is_counterexample(self) -> bool:
        return self.status == "counterexample"

    @property
    def is_pass(self) -> bool:
        return self.status == "pass"


def _undescribable(why: str, **extra) -> LintResult:
    return LintResult("undescribable", detail={"why": why, **extra})


# --- property families (each: brute-force over a prefix -> first counterexample or None) ---
# A returned counterexample is a GENUINE witness that the property FAILS on the finite prefix,
# hence a sound refutation of any universal claim. None means "no counterexample within the
# prefix" — necessary, not sufficient (the lint never certifies).

def _check_power_free(seq: list[int], exponent: int) -> Optional[dict]:
    """A word is e-th-power-free iff it has NO factor w^e (e>=2 consecutive equal blocks of some
    period p>=1). Returns the lexicographically-first (start, period) whose e copies all match,
    or None. O(N^2/e) — the caller bounds N for this family."""
    N = len(seq)
    for p in range(1, N // exponent + 1):
        span = exponent * p
        for i in range(0, N - span + 1):
            block = seq[i:i + p]
            if all(seq[i + j * p:i + j * p + p] == block for j in range(1, exponent)):
                return {"kind": "power", "exponent": exponent, "start": i, "period": p,
                        "factor": seq[i:i + span]}
    return None


def _check_avoids_factor(seq: list[int], block: list[int]) -> Optional[dict]:
    """The word AVOIDS ``block`` iff that exact finite block never occurs as a factor. Returns
    the first occurrence position, or None."""
    L = len(block)
    if L == 0:
        return None
    for i in range(0, len(seq) - L + 1):
        if seq[i:i + L] == block:
            return {"kind": "factor", "block": block, "start": i}
    return None


def _alternating_block(symbols: list[int], length: int) -> list[int]:
    """The length-``length`` alternating block over two symbols, e.g. [0,1,0,1] / [1,0,1,0]."""
    a, b = symbols
    return [a if k % 2 == 0 else b for k in range(length)]


def _check_avoids_pattern(seq: list[int], length: int) -> Optional[dict]:
    """The word avoids ALTERNATING factors of the given length iff neither the 0101… nor the
    1010… block of that length occurs. (Binary patterns; the common 'no strictly alternating
    length-L window' family — d37eb690's intended claim.)"""
    for sym in ([0, 1], [1, 0]):
        block = _alternating_block(sym, length)
        hit = _check_avoids_factor(seq, block)
        if hit is not None:
            return {"kind": "pattern", "pattern": "alternating", "length": length,
                    "block": block, "start": hit["start"]}
    return None


# Per-family driver: validate params, generate a correctly-sized prefix, brute-force.
# ``avoids_*`` are O(N) so they get a large prefix; ``power_free`` is O(N^2/e) so it is capped.
_FACTOR_PREFIX = 1 << 16   # 65536 — cheap linear scan
_POWER_PREFIX = 1 << 12    # 4096 — quadratic; small powers/critical exponents appear very early


def lint_descriptor(descriptor: Optional[dict], *, decided_true: bool,
                    predicate: Optional[str]) -> LintResult:
    """Cross-check a ``property_descriptor`` against a DECIDED verdict over a finite prefix.

    Only meaningful when ``decided_true`` (the artifact class is "decided TRUE but actually
    FALSE"). For a refuted verdict the lint is informational and never blocks (Walnut's
    refutation is itself sound). Returns a :class:`LintResult`; the caller maps
    ``counterexample`` -> quarantine and ``undescribable`` -> (production) refuse-to-decide.

    ``predicate`` is the ``walnut_predicate`` Walnut actually decided. The descriptor is REQUIRED
    to be bound to it (its word == the word(s) the predicate indexes); otherwise a lint pass
    would attest a property of the WRONG sequence (the review's high-severity finding). ``bool``
    parameters are rejected up front so ``True``/``False`` cannot masquerade as int params.
    """
    if not isinstance(descriptor, dict):
        return _undescribable("no_descriptor")
    family = str(descriptor.get("family", "")).strip().lower()
    word = _canon_word(descriptor.get("word", ""))
    if word is None:
        return _undescribable("unknown_word", word=str(descriptor.get("word", "")))
    if not descriptor_binds_predicate(descriptor, predicate):
        # the descriptor is not about the sequence the predicate decides => the cross-check would
        # be vacuous (wrong sequence). Refuse to anchor.
        return _undescribable("word_mismatch", word=word,
                              predicate_words=predicate_indexed_words(predicate))
    gen = WORD_GENERATORS[word]

    if family == "power_free":
        e = descriptor.get("exponent")
        if isinstance(e, bool) or not (isinstance(e, int) and 2 <= e <= _MAX_EXPONENT):
            return _undescribable("bad_exponent", exponent=e)
        seq = gen(_POWER_PREFIX)
        cx = _check_power_free(seq, e)
        return _verdict(cx, len(seq), decided_true, descriptor)

    if family == "avoids_factor":
        block = _coerce_block(descriptor.get("block"))
        if block is None:
            return _undescribable("bad_block", block=descriptor.get("block"))
        alpha = _word_alphabet(word)
        if any(d not in alpha for d in block):
            # a block over symbols the word cannot contain "never occurs" trivially — a false
            # anchor, not a real avoidance property.
            return _undescribable("block_out_of_alphabet", block=block, alphabet=sorted(alpha))
        seq = gen(_FACTOR_PREFIX)
        cx = _check_avoids_factor(seq, block)
        return _verdict(cx, len(seq), decided_true, descriptor)

    if family == "avoids_pattern":
        if str(descriptor.get("pattern", "")).strip().lower() != "alternating":
            return _undescribable("unknown_pattern", pattern=descriptor.get("pattern"))
        length = descriptor.get("length")
        if isinstance(length, bool) or not (isinstance(length, int) and 1 <= length <= _MAX_PATTERN_LEN):
            return _undescribable("bad_length", length=length)
        seq = gen(_FACTOR_PREFIX)
        cx = _check_avoids_pattern(seq, length)
        return _verdict(cx, len(seq), decided_true, descriptor)

    return _undescribable("unknown_family", family=family)


def _coerce_block(block) -> Optional[list[int]]:
    """Accept a block as a list of ints, or a compact string of digits ("00", "1010")."""
    if isinstance(block, str) and block and all(c in "0123456789" for c in block):
        return [int(c) for c in block]
    if isinstance(block, (list, tuple)) and block and all(isinstance(x, int) for x in block):
        return list(block)
    return None


def _verdict(counterexample: Optional[dict], prefix: int, decided_true: bool,
             descriptor: dict) -> LintResult:
    """Map a brute-force result to a LintResult. A counterexample only CONTRADICTS a
    decided-true verdict (the artifact class); when the verdict is already refuted, a prefix
    counterexample merely corroborates it and the lint passes (informational)."""
    if counterexample is not None and decided_true:
        return LintResult("counterexample", prefix_checked=prefix,
                          detail={"family": descriptor.get("family"),
                                  "counterexample": counterexample})
    return LintResult("pass", prefix_checked=prefix,
                      detail={"family": descriptor.get("family"),
                              "corroborated_refutation": counterexample is not None})
