"""Empirical pattern mining (ADR 0034 Stage 2) — proposal-side, pure compute, no LLM, no decisions.

Stage 1 (steering) showed the conjecturer only hops to a *wider* drawer of RECALLED textbook
facts (arm A: it imitated the residue-set exemplars it was shown). This stage changes the
generative SOURCE: it finds TRUE residue regularities of low-degree integer polynomials by
COMPUTATION over the integers, and feeds them to the conjecturer as seeds — compute, not recall.

Every mined pattern is EXACTLY TRUE: an integer polynomial is periodic mod m with period m, so the
residue set over one full period [0, m) is the COMPLETE set (the same fact `structural._residue_set`
relies on). So a mined seed is a real, verified-by-enumeration fact for the conjecturer to
formalize. But it DECIDES NOTHING (ADR 0034 §6, Prohibition 1): the seed still runs the full
novelty / triviality / faithfulness gates and the kernel's N+1 consensus. The miner proposes; the
kernel disposes.

HONEST SCOPE (ADR 0034 §4 / §7). The miner enumerates the SAME polynomial-congruence DSL the
novelty metric lives in, so corpus-novel != genuinely novel — a mined pattern can be a true-but-
arbitrary residue fact ("a new drawer in the same cabinet"). Whether compute-found patterns read
as *more* novel than Stage-1's recall is exactly what the A/B + the blind human read (§5.1) decide;
the pre-registered kill condition (§5) catches "still textbook". This module does not pretend the
metric proves novelty — it only changes where proposals come from.

PROVABILITY TARGET (§7, the four-way intersection novel ∧ in-DSL ∧ non-trivial ∧ within-reach).
The score favours a PROPER MULTI-RESIDUE restriction `2 <= |R| < m` — a real restriction that needs
case analysis on n mod m (so it survives `is_trivial`, which is gated FIRST and closes single-shot
`ring`/`decide`/`omega` claims) yet is reachable (the band arm A actually promulgated). It is NOT
tuned for "simplest" (that hits the triviality floor) nor for "hardest".
"""
from __future__ import annotations

import itertools
from dataclasses import dataclass
from typing import Iterable, Optional

from leibniz.structural import congruence_signature

# Bounded, deterministic enumeration (ADR 0034 §9: "start conservative"). ~8.4k polynomials ×
# 15 moduli, each residue set computed over one period — well under a second.
MAX_DEGREE = 4          # univariate polynomials of degree 2..MAX_DEGREE (linear is mostly uniform)
COEFF = 3               # lower coefficients range over [-COEFF, COEFF]
LEAD_MAX = 3            # leading (top-degree) coefficient ranges over [1, LEAD_MAX]
M_MIN, M_MAX = 2, 16    # modulus range (small: provable by case analysis, exact residue set)


@dataclass(frozen=True)
class MinedPattern:
    """A true residue regularity found by enumeration: for all n>=0, `poly` mod `m` lies in
    `residues`. `prop` is the canonical DSL claim_property; `signature` its congruence signature;
    `score` ranks it within the non-trivial-but-reachable band."""
    poly: str
    m: int
    residues: tuple
    prop: str
    signature: tuple
    score: float


def _residue_set(coeffs: list[int], m: int) -> frozenset:
    """The EXACT residue set {P(n) mod m : n in Z}. coeffs is constant-term-first
    ([c0, c1, ...]); a polynomial is periodic mod m with period m, so [0, m) is complete."""
    out = set()
    for n in range(m):
        val = 0
        p = 1
        for c in coeffs:        # Horner-free but bounded (degree <= 4)
            val += c * p
            p *= n
        out.add(val % m)
    return frozenset(out)


def _poly_str(coeffs: list[int]) -> str:
    """Render coeffs (constant-first) as a DSL polynomial in `n`, e.g. [1,0,3,0,1] -> 'n^4 + 3*n^2 + 1'.
    Empty (all-zero) -> '0'. Uses `^` (the DSL/structural form)."""
    terms: list[str] = []
    for power in range(len(coeffs) - 1, -1, -1):
        c = coeffs[power]
        if c == 0:
            continue
        mag = abs(c)
        if power == 0:
            body = str(mag)
        elif power == 1:
            body = "n" if mag == 1 else f"{mag}*n"
        else:
            body = f"n^{power}" if mag == 1 else f"{mag}*n^{power}"
        sign = "-" if c < 0 else "+"
        terms.append((sign, body))
    if not terms:
        return "0"
    first_sign, first_body = terms[0]
    head = (f"-{first_body}" if first_sign == "-" else first_body)
    return head + "".join(f" {s} {b}" for s, b in terms[1:])


def _property(poly: str, m: int, R: frozenset) -> Optional[str]:
    """Canonical DSL claim_property for the residue fact, or None if vacuous (|R| == m: P hits
    every residue, an empty restriction). Singleton -> `== r`; all-but-one -> `!= missing`;
    otherwise the residue-set membership `in {..}`."""
    if len(R) >= m:
        return None
    rs = sorted(R)
    body = f"({poly}) % {m}"
    if len(R) == 1:
        return f"{body} == {rs[0]}"
    if len(R) == m - 1:
        missing = next(r for r in range(m) if r not in R)
        return f"{body} != {missing}"
    return f"{body} in {{{', '.join(str(r) for r in rs)}}}"


def _score(degree: int, m: int, R: frozenset, monic: bool) -> float:
    """Rank within the non-trivial-but-reachable band (§7). Higher = a tighter, multi-residue
    restriction at a small modulus / moderate degree, with a MONIC leading coefficient. NOT tuned
    for 'simplest'. The monic bonus surfaces the clean canonical representative (`n^2 mod m`) over
    its scaled siblings (`2*n^2`, `3*n^2`), which read as arbitrary restatements — a principled
    preference, not result-tuning."""
    exclusion = 1.0 - len(R) / m           # fraction of residues the polynomial never hits
    multi = 0.30 if 1 < len(R) < m else 0.0  # a proper multi-residue restriction needs case analysis
    # gentle provability priors: smaller modulus + lower degree are easier to close
    return exclusion + multi + (0.15 if monic else 0.0) - 0.03 * m - 0.05 * max(0, degree - 2)


def _enumerate_coeffs() -> Iterable[list[int]]:
    """Bounded, deterministic polynomial enumeration (degree 2..MAX_DEGREE; leading coeff in
    [1, LEAD_MAX]; lower coeffs in [-COEFF, COEFF])."""
    lowers = range(-COEFF, COEFF + 1)
    for degree in range(2, MAX_DEGREE + 1):
        for lead in range(1, LEAD_MAX + 1):
            for low in itertools.product(lowers, repeat=degree):
                yield [*low, lead]   # constant-first: low[0]=c0 ... low[d-1]=c_{d-1}, then lead=c_d


def _degree(p: MinedPattern) -> int:
    """The polynomial's degree, read off the signature's reduced-poly monomial keys (sig[2])."""
    return max((k for k, _c in p.signature[2]), default=0)


def _diversified(ranked: list[MinedPattern]) -> list[MinedPattern]:
    """Reorder the score-ranked patterns for genuine spread: the raw ranking floods with one
    monotone region (degree-2, two-residue, modulus-8 variants), so naive cursoring would cluster
    B on a single mined family — recreating arm A's problem. Group by (modulus, degree) and
    round-robin DEGREE-major / modulus-spread, so the first batch dispensed spans moduli 2..16
    (then climbs in degree), and within a group score order is kept."""
    groups: dict[tuple, list[MinedPattern]] = {}
    for p in ranked:                                # ranked is score-sorted -> groups stay ordered
        groups.setdefault((p.m, _degree(p)), []).append(p)
    keys = sorted(groups, key=lambda k: (k[1], k[0]))  # (degree, modulus): degree-2 across all m first
    out: list[MinedPattern] = []
    while len(out) < len(ranked):
        progressed = False
        for k in keys:
            if groups[k]:
                out.append(groups[k].pop(0))
                progressed = True
        if not progressed:
            break
    return out


def mine(corpus_signatures: Iterable[tuple] = (), *, limit: Optional[int] = None) -> list[MinedPattern]:
    """Enumerate true residue patterns, drop the vacuous / unrecognized / already-KNOWN, dedup by
    signature, and return them DIVERSIFIED (round-robin across coarse families, best-in-family
    first) so a multi-cycle run gets varied computed patterns rather than a run of near-clones.
    `corpus_signatures` are signatures already in the known-results corpus (dropped here so the
    miner does not re-seed textbook facts the gate would quarantine anyway). Pure: no LLM, no I/O,
    no decisions."""
    known = set(corpus_signatures)
    best: dict[tuple, MinedPattern] = {}
    for coeffs in _enumerate_coeffs():
        degree = len(coeffs) - 1
        for m in range(M_MIN, M_MAX + 1):
            R = _residue_set(coeffs, m)
            prop = _property(_poly_str(coeffs), m, R)
            if prop is None:
                continue
            sig = congruence_signature(prop)
            if sig is None or sig in known:        # unrecognized shape, or already textbook -> skip
                continue
            score = _score(degree, m, R, monic=coeffs[-1] == 1)
            prev = best.get(sig)
            if prev is None or score > prev.score:  # dedup by signature, keep the best-scoring form
                best[sig] = MinedPattern(
                    poly=_poly_str(coeffs), m=m, residues=tuple(sorted(R)),
                    prop=prop, signature=sig, score=round(score, 4))
    ranked = sorted(best.values(), key=lambda p: (-p.score, p.m, p.poly))
    diversified = _diversified(ranked)
    return diversified[:limit] if limit is not None else diversified


# The marker every mined seed begins with — used to attribute a candidate's origin post-hoc
# (ADR 0034 §5) without trusting the LLM to echo it. Keep `seed_text` starting with this.
MINED_SEED_PREFIX = "COMPUTED PATTERN"


def seed_text(p: MinedPattern) -> str:
    """The conjecturer-facing seed for a mined pattern. Frames it as DATA to formalize (ADR 0034
    §3.D), not a topic to free-associate from."""
    rs = ", ".join(str(r) for r in p.residues)
    return (
        f"{MINED_SEED_PREFIX} (verified true by enumerating one full period — not a guess): "
        f"for every non-negative integer n, ({p.poly}) mod {p.m} always lies in {{{rs}}}. "
        "Formalize and prove THIS EXACT fact — it needs case analysis on n mod "
        f"{p.m}, so no single decision procedure closes it. Do not free-associate to a different claim."
    )


class PatternMiner:
    """A stateful dispenser over the ranked mined patterns: each cycle draws the NEXT k fresh
    seeds (a cursor), so a multi-cycle run keeps getting new computed patterns instead of the same
    top-k repeated. Proposal-side; dispenses seed text and decides nothing."""

    # A run draws only k-per-cycle (~tens); keep a diversified pool, not all ~80k patterns.
    POOL = 256

    def __init__(self, corpus_signatures: Iterable[tuple] = ()) -> None:
        self._patterns = mine(corpus_signatures, limit=self.POOL)
        self._cursor = 0

    def __len__(self) -> int:
        return len(self._patterns)

    def seeds(self, k: int) -> list[str]:
        """The next `k` mined seed strings (advancing the cursor). Empty when k<=0 or exhausted."""
        if k <= 0 or self._cursor >= len(self._patterns):
            return []
        batch = self._patterns[self._cursor:self._cursor + k]
        self._cursor += len(batch)
        return [seed_text(p) for p in batch]
