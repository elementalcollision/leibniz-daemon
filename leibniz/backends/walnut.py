"""Walnut sound-faithfulness backend (ADR 0037 backend #1 — the crawl rung).

Walnut decides first-order formulas over **k-automatic sequences** (Büchi–Bruyère) —
SOUNDLY over **unbounded n**, the class the bounded-box DSL cannot reach (ADR 0036 M2:
0/24; the Walnut probe: 12/12). A claim carries the **free-variable agreement predicate**
``claim(n) <-> statement(n)`` (`Expressio.walnut_predicate` + `.walnut_numeration`); Walnut
emits its *agreement automaton*, and the claim is faithful iff that automaton is UNIVERSAL
(accepts all n). Universal => PASS; non-universal => a sound unfaithfulness refutation (some
n disagrees); a bare token / malformed / unavailable => DEFER.

TRUST (read before wiring this on):
  * A Walnut PASS trusts **Walnut's automaton construction** — Walnut joins the
    **faithfulness** TCB alongside Z3 (already trusted there for the gaming search). The
    **proof-edge** TCB (the Lean kernel) is untouched.
  * It also trusts the **rendering** `walnut_predicate` faithfully expresses
    claim<->statement (the renderer-TCB point, ADR 0036 §10.2). The backend decides and
    re-checks the automaton; it does not certify the rendering.
  * The gate's re-checker (`recheck_walnut_certificate`) independently runs a REAL
    structural check — `automaton_is_universal` over the certificate's agreement automaton
    (every state reachable from the initial state is accepting). This defeats a backend
    that merely *reports* a pass (a fabricated `data="true"` token has no universal
    automaton and fails). It does NOT re-verify that the automaton is the agreement
    automaton for this claim — that binding is Walnut's TCB role (like trusting Z3's
    decision), NOT a kernel-style re-derivation of everything.

OFF BY DEFAULT: nothing here is wired into the assembled gate (`assembly.py`). The
operator opts in by constructing the gate with this backend AND registering
`recheck_walnut_certificate` for `WALNUT_CERT_KIND` (no re-checker registered => the gate
cannot accept a PASS of this kind — the dormant default is safe). The real subprocess
runner DEFERs whenever Walnut is absent or errors, so an unconfigured environment is sound.

FORMAT VALIDATED against the Walnut serializer source (`Automata/Automaton.java::write` /
`writeAlphabet` / `writeState`, Walnut commit pinned in the probe): a TRUE/FALSE result is
the literal token; otherwise the header is the numeration name (``msd_2``) for a numeration
track (or ``{0, 1}`` for a set alphabet), each state is ``<q> <output>``, and each
transition is ``<digit(s)> -> <dest>`` with **bare space-separated digits** — NOT bracketed
``[0]`` labels (the brackets in Walnut are a separate display path, not the `.txt` writer).
`parse_walnut_automaton` matches this for the single-track numeration case (our agreement
automaton over one free variable n under ``?msd_k``); multi-track headers, set-alphabet
headers, and NFA multi-dest lines fall to the malformed/unknown-alphabet path => DEFER
(sound). `test_walnut_backend_r0037.py::test_parses_real_walnut_serializer_format` pins the
exact byte-format. (Reading the serializer covers every case, so it is a stronger check than
one live sample; a live eval can still triple-confirm but is not required.)

STILL MUST-DO BEFORE ENABLING (sound off-by-default; each errs toward DEFER, never a false
PASS):
  1. **Prop-binding (partial seam present):** the gate's re-checker verifies the certificate
     automaton is *universal* and `check` already DEFERs on a numeration mismatch, but the
     deeper automaton<->claim binding remains the documented Walnut+renderer TCB.
  2. **Runner home derivation:** `$LEIBNIZ_WALNUT_JAR` is assumed to live in `build/libs/`;
     accept `$LEIBNIZ_WALNUT_HOME` or assert the ancestry and DEFER otherwise.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

from leibniz.gates.sound_backends import Certificate, FaithfulnessVerdict
from leibniz.propositio import Propositio
from leibniz.types import Verdict

WALNUT_CERT_KIND = "walnut-automaton"


_STATE_DECL = re.compile(r"(\d+)\s+(-?\d+)")        # "<state> <output>"
_EDGE_DECL = re.compile(r"(.+?)\s*->\s*(\d+)")      # "<input label> -> <dest>"
_NUMERATION = re.compile(r"(?:msd|lsd)_([A-Za-z0-9]+)")


def _alphabet(numeration: Optional[str]) -> Optional[frozenset]:
    """The single-track input alphabet (digit labels) for a numeration, or None when we
    cannot determine it (=> completeness is unverifiable => the classifier DEFERs).

    Conservative: we only model the cases we are sure of -- ``msd_k``/``lsd_k`` => {0..k-1},
    and the Pisot numerations whose digit alphabet is binary (Fibonacci/Zeckendorf,
    Tribonacci). Everything else (pell, ostrowski, multi-track, unknown) => None.
    """
    if not numeration:
        return None
    m = _NUMERATION.fullmatch(numeration)
    if not m:
        return None
    base = m.group(1).lower()
    if base.isdigit():
        k = int(base)
        return frozenset(str(d) for d in range(k)) if k >= 2 else None
    if base in ("fib", "fibonacci", "trib", "tribonacci"):
        return frozenset({"0", "1"})
    return None


@dataclass(frozen=True)
class WalnutAutomaton:
    """A parsed Walnut result automaton (the certificate payload).

    Faithfulness is rendered as a FREE-VARIABLE *agreement* predicate
    ``claim(n) <-> statement(n)``, so Walnut emits a structured DFAO (state outputs +
    LABELLED transitions), not a bare ``true``/``false`` token. A faithful claim => a
    *universal* agreement automaton, which ``classify_agreement`` verifies by checking the
    automaton is **complete** (total + deterministic over the numeration's alphabet) and
    every reachable state accepts. A bare token (``is_sentence``) carries no structure to
    re-check and is NOT accepted.
    """

    is_sentence: bool                  # bare true/false token (a closed sentence), not an automaton
    is_true: bool                      # iff is_sentence: the TRUE token
    numeration: Optional[str]          # e.g. "msd_2"
    states: dict                       # state-id -> output (1 = accepting/true at that state)
    trans: dict                        # state-id -> {input-label: dest state-id}
    deterministic: bool                # False if any state had a duplicate input label
    parsed_ok: bool                    # a structured automaton parsed cleanly
    raw: str

    @property
    def n_states(self) -> int:
        return len(self.states)


def parse_walnut_automaton(text: str) -> WalnutAutomaton:
    """Parse Walnut's `.txt` automaton format into a structured DFAO, KEEPING the input
    label of each transition (completeness cannot be verified without it).

    A *closed sentence* result is literally ``true``/``false``. A predicate over a free
    variable is ``<numeration>\\n\\n<state blocks>`` where each block is a
    ``<state> <output>`` line followed by ``<input label> -> <dest>`` transition lines.
    """
    s = (text or "").strip()
    low = s.lower()
    if low == "true":
        return WalnutAutomaton(True, True, None, {}, {}, True, False, text)
    if low == "false":
        return WalnutAutomaton(True, False, None, {}, {}, True, False, text)

    numeration = None
    states: dict[int, int] = {}
    trans: dict[int, dict] = {}
    deterministic = True
    cur: Optional[int] = None
    for raw in text.splitlines():
        ln = raw.strip()
        if not ln:
            continue
        if numeration is None:               # first non-empty line is the numeration
            numeration = ln
            continue
        m_state = _STATE_DECL.fullmatch(ln)
        if m_state:
            cur = int(m_state.group(1))
            states[cur] = int(m_state.group(2))
            trans.setdefault(cur, {})
            continue
        m_edge = _EDGE_DECL.fullmatch(ln)
        if m_edge and cur is not None:
            label = m_edge.group(1).strip()
            if label in trans[cur]:          # duplicate label on a state => non-deterministic
                deterministic = False
            trans[cur][label] = int(m_edge.group(2))
            continue
        # an unparseable line -> malformed; refuse (conservative)
        return WalnutAutomaton(False, False, numeration, {}, {}, True, False, text)
    return WalnutAutomaton(False, False, numeration, states, trans, deterministic,
                           len(states) > 0, text)


def classify_agreement(aut: WalnutAutomaton) -> str:
    """Independently classify the agreement automaton as ``"universal"`` (the predicate
    holds for ALL n -> faithful), ``"refuted"`` (some n disagrees -> unfaithful), or
    ``"indeterminate"`` (cannot be soundly decided -> DEFER).

    A verdict of "universal"/"refuted" is returned ONLY for a **complete** DFAO: every
    state reachable from the initial state 0 has a deterministic transition for EVERY
    alphabet symbol (total, no dangling dest), over a numeration alphabet we can model.
    For a complete DFAO, 'all reachable states accept' <=> universal; 'some reachable state
    rejects' <=> refuted. Anything we cannot verify complete (bare token, malformed,
    non-deterministic, unknown numeration, missing/extra/dangling transitions, no initial
    state) is "indeterminate" -- never a wrong "universal".
    """
    if aut.is_sentence or not aut.parsed_ok or not aut.deterministic:
        return "indeterminate"
    if not aut.states or 0 not in aut.states:
        return "indeterminate"
    alphabet = _alphabet(aut.numeration)
    if alphabet is None:
        return "indeterminate"
    seen: set[int] = set()
    stack = [0]
    while stack:
        st = stack.pop()
        if st in seen:
            continue
        seen.add(st)
        edges = aut.trans.get(st, {})
        if set(edges.keys()) != alphabet:        # incomplete or extra labels => cannot decide
            return "indeterminate"
        for dest in edges.values():
            if dest not in aut.states:           # dangling transition => cannot decide
                return "indeterminate"
            if dest not in seen:
                stack.append(dest)
    return "universal" if all(aut.states[st] == 1 for st in seen) else "refuted"


def automaton_is_universal(aut: WalnutAutomaton) -> bool:
    """True iff ``classify_agreement`` positively verifies the automaton is universal."""
    return classify_agreement(aut) == "universal"


def recheck_walnut_certificate(cert: Certificate) -> bool:
    """The GATE-OWNED independent re-checker for ``WALNUT_CERT_KIND``.

    Parses the certificate's agreement automaton and INDEPENDENTLY verifies it is
    *universal* (accepts all n). True iff the structured automaton is universal; a bare
    ``true``/``false`` token, a non-universal automaton, a wrong kind, or malformed data
    is NOT a pass. It re-derives the verdict FROM the certificate structure, defeating a
    backend that merely *reports* a pass (e.g. a fabricated ``data="true"``).

    TRUST boundary (honest): this verifies the certificate automaton is universal; it does
    NOT re-verify that the automaton is the agreement automaton for THIS claim -- Walnut is
    trusted to have constructed it (Walnut joins the *faithfulness* TCB alongside Z3), and
    the rendering ``walnut_predicate`` is a trusted artifact (renderer-TCB, ADR 0036 §10.2).
    """
    if cert is None or cert.kind != WALNUT_CERT_KIND or not isinstance(cert.data, str):
        return False
    return automaton_is_universal(parse_walnut_automaton(cert.data))


# Walnut command-language metacharacters that could break out of the quoted `eval "..."`
# and inject a second command. The predicate/numeration are LLM/operator-authored (untrusted
# renderer artifacts), so they are validated before interpolation: any of these => DEFER.
_INJECTION_CHARS = frozenset('";\n\r\\')
_SAFE_NUMERATION = re.compile(r"(?:msd|lsd)_[A-Za-z0-9_]+")


def _safe_walnut_inputs(predicate: str, numeration: str) -> bool:
    """Reject predicate/numeration that could inject a second Walnut command (the eval is
    interpolated into Walnut's stdin). Conservative allow-list on the numeration; reject
    quote/semicolon/newline/backslash anywhere. On failure the runner DEFERs."""
    if not predicate or not numeration:
        return False
    if any(c in predicate for c in _INJECTION_CHARS):
        return False
    if any(c in numeration for c in _INJECTION_CHARS):
        return False
    return bool(_SAFE_NUMERATION.fullmatch(numeration))


def _default_runner(predicate: str, numeration: str, *, timeout: float = 120.0) -> Optional[str]:
    """Run Walnut on ``eval <name> "?<numeration> <predicate>";`` and return the result
    automaton text, or None (=> DEFER) if Walnut is unavailable, the inputs are unsafe, or
    it errors.

    Walnut location is taken from ``$LEIBNIZ_WALNUT_JAR`` (the path to ``Walnut-all.jar``);
    Walnut reads/writes relative to its home (the jar's ``build/libs/`` => repo root), so
    the result lands in ``<home>/Result/<name>.txt``.
    """
    if not _safe_walnut_inputs(predicate, numeration):
        return None  # untrusted input could inject a Walnut command -> DEFER
    jar = os.environ.get("LEIBNIZ_WALNUT_JAR")
    java = shutil.which("java")
    if not jar or java is None:
        return None
    jar_path = Path(jar)
    if not jar_path.exists():
        return None
    home = jar_path.resolve().parent.parent.parent  # build/libs/Walnut-all.jar -> repo root
    name = "leibniz_faith"
    program = f'eval {name} "?{numeration} {predicate}";\nexit;\n'
    result = home / "Result" / f"{name}.txt"
    try:
        # FRESHNESS: the result name is a fixed constant, so a stale file from a PRIOR
        # eval (which could be the literal "true") would be read back if THIS run fails to
        # overwrite it — e.g. a DSL parse error on a malformed predicate/numeration that
        # leaves Walnut's exit nonzero but the old file intact. Delete it up front so only
        # this run's output can ever be returned; if Walnut writes nothing, we DEFER.
        result.unlink(missing_ok=True)
        proc = subprocess.run(
            [java, "-jar", str(jar_path)],
            input=program, text=True, capture_output=True,
            timeout=timeout, cwd=str(home),
        )
        # Trust the result ONLY on a clean exit. A nonzero return code (parse error, crash)
        # => DEFER, never a stale or partial read.
        if proc.returncode != 0:
            return None
        return result.read_text() if result.exists() else None
    except (subprocess.SubprocessError, OSError):
        return None


@dataclass
class WalnutBackend:
    """A SoundFaithfulnessBackend over automatic sequences. ``runner`` is injectable so
    the parser/verdict logic is unit-testable without the Walnut binary; the default
    runner shells out to Walnut and DEFERs on absence/error."""

    name: str = "walnut"
    cost_rank: int = 50
    runner: Callable[..., Optional[str]] = field(default=_default_runner)

    def applies(self, prop: Propositio) -> bool:
        ex = prop.expressio
        return bool(ex is not None and ex.walnut_predicate and ex.walnut_numeration)

    def check(self, prop: Propositio) -> FaithfulnessVerdict:
        ex = prop.expressio
        # `walnut_predicate` is the FREE-VARIABLE agreement predicate claim(n)<->statement(n);
        # Walnut emits its agreement automaton.
        result_text = self.runner(ex.walnut_predicate, ex.walnut_numeration)
        if result_text is None:
            return FaithfulnessVerdict(
                verdict=Verdict.DEFER, producer="walnut/recheck",
                detail={"reason": "walnut unavailable or no result"},
            )
        aut = parse_walnut_automaton(result_text)
        # Partial prop-bind: the result automaton must be over the numeration we asked for
        # (closes the "universal automaton for the wrong numeration" sub-case; the deeper
        # automaton<->claim binding is the documented Walnut+renderer TCB).
        if not aut.is_sentence and aut.numeration != ex.walnut_numeration:
            return FaithfulnessVerdict(
                verdict=Verdict.DEFER, producer="walnut/recheck",
                detail={"reason": "result numeration does not match the requested one"},
            )
        verdict = classify_agreement(aut)
        if verdict == "indeterminate":
            # bare token / malformed / non-deterministic / incomplete / unknown numeration:
            # cannot be soundly decided. Refuse rather than guess.
            return FaithfulnessVerdict(
                verdict=Verdict.DEFER, producer="walnut/recheck",
                detail={"reason": "agreement automaton not soundly decidable"},
            )
        cert = Certificate(
            kind=WALNUT_CERT_KIND, rechecked=(verdict == "universal"), data=result_text,
            detail={"numeration": ex.walnut_numeration},
        )
        if verdict == "universal":
            # the agreement holds for ALL n -> faithful (re-checked by the gate too).
            return FaithfulnessVerdict(verdict=Verdict.PASS, producer="walnut/recheck",
                                       certificate=cert)
        # "refuted": a complete automaton with a reachable rejecting state -> some n has
        # claim(n) != statement(n) -> a SOUND unfaithfulness refutation.
        return FaithfulnessVerdict(verdict=Verdict.FAIL, producer="walnut/recheck",
                                   certificate=cert, detail={"reason": "agreement automaton refuted"})
