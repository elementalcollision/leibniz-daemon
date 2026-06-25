"""Novelty instrumentation (ADR 0034 Stage 0) — a READ-ONLY structural-diversity metric.

This module measures how much the daemon's promulgations spread out in the
polynomial-congruence signature space of `structural.congruence_signature`. It exists to
answer one question honestly: *are we still re-proving the same textbook shapes under new
names, or are the proven laws actually diversifying?*

WHAT IT IS — and explicitly is NOT (ADR 0034 §4, the measurement-circularity finding):

  • It is a COARSE diversity TRIPWIRE. Two signals are trustworthy in the NEGATIVE: if the
    signature-distance distribution does NOT move, we have certainly not diversified; and a
    rising fraction of `None`-signature promulgations is itself a sign of leaving the bounded
    DSL (where genuine novelty would have to live).
  • It is NOT a novelty oracle. The metric lives in the SAME polynomial-congruence DSL that
    produced the textbook clustering, so a fresh `(P, m)` populates a new signature cell —
    "a new drawer in the same cabinet" — whether or not anything mathematically novel
    happened. A distance distribution that shifts right is therefore NECESSARY-NOT-SUFFICIENT
    for genuine novelty. The real success signal is the operator's blind human read
    (ADR 0034 §5.1); this metric only supports it.

PROHIBITION 1 (ADR 0034 §6): everything here is measurement. There is NO accept/reject,
quarantine, filter, or drop. The sole novelty arbiter stays `gates/novelty.py`. This module
must never be wired into a proposal-side prefilter — that would move a novelty judgment into
untested code outside the trust boundary. It computes numbers; it decides nothing.

Pure stdlib; no Z3, no Lean, no LLM. Reuses `structural.congruence_signature` (zero new math).
"""
from __future__ import annotations

from typing import Iterable, Optional, Sequence

from leibniz.structural import congruence_signature

# The feature axes a congruence signature decomposes into, for a coarse normalized Hamming
# dissimilarity. A signature is `(relop, m, reduced_poly[, residues])`:
#   • relop    — "==" / "!=" (single-residue) or "in" / "not in" (multi-residue membership)
#   • m        — the modulus (categorical: m=2 vs m=3 are simply "a different modulus"; we do
#                NOT treat |m1-m2| as continuous, which would over-weight large moduli)
#   • shape    — the SET of monomial keys present (which powers/monomials appear) — derived
#                from reduced_poly; a shape change is a bigger structural difference than a
#                coefficient-only change, so counting shape AND coeffs gives shape extra weight
#   • coeffs   — the full reduced_poly tuple (captures coefficient VALUES, not just the shape)
#   • residues — the computed residue set R for membership claims, else None
_N_FEATURES = 5


def _features(sig: tuple) -> tuple:
    """Decompose a congruence signature into its (relop, m, shape, coeffs, residues) axes.

    `sig` must be a non-None signature as returned by `congruence_signature`. Robust to both
    the 3-tuple (`==`/`!=`) and 4-tuple (`in`/`not in`, with a residue set) shapes."""
    relop, m, reduced_poly = sig[0], sig[1], sig[2]
    residues = sig[3] if len(sig) > 3 else None
    shape = frozenset(key for key, _coeff in reduced_poly)
    return (relop, m, shape, reduced_poly, residues)


def signature_distance(a: tuple, b: tuple) -> float:
    """Normalized structural dissimilarity of two NON-None congruence signatures, in [0, 1].

    Defined as the fraction of the five feature axes (relop, modulus, shape, coefficients,
    residues) on which the two signatures differ — a normalized Hamming distance. It is 0.0
    iff the signatures are identical and symmetric by construction; it is deliberately COARSE
    and is NOT claimed to be a true metric (no triangle-inequality guarantee — `shape` is a
    derived coordinate of `coeffs`, included so shape changes outweigh coefficient-only ones).
    Per the module docstring this is a tripwire, not a novelty oracle."""
    fa, fb = _features(a), _features(b)
    differ = sum(1 for x, y in zip(fa, fb) if x != y)
    return differ / _N_FEATURES


def _nearest_distance(sig: tuple, others: Sequence[tuple]) -> Optional[float]:
    """Minimum `signature_distance` from `sig` to any signature in `others`, or None if
    `others` is empty (an isolated point — no reference to measure against)."""
    if not others:
        return None
    return min(signature_distance(sig, o) for o in others)


def signatures_of(properties: Iterable[Optional[str]]) -> list[Optional[str]]:
    """Map each canonical `claim_property` predicate to its congruence signature (or None).

    A None/empty property (a prose-only / OPEN_FORM claim, or one outside the recognized DSL
    shapes) yields None — which is itself meaningful for coverage (see `profile`)."""
    return [congruence_signature(p) if p else None for p in properties]


def profile(
    properties: Sequence[Optional[str]],
    reference: Sequence[Optional[str]] = (),
) -> dict:
    """Compute the read-only novelty profile of a set of claim properties.

    `properties` — the canonical `claim_property` predicates of the promulgations (or corpus
    entries) under study. `reference` — additional known properties (e.g. the known-results
    corpus) to measure nearest-neighbour distance against, in ADDITION to the other members of
    `properties` itself. Each item's nearest neighbour is taken over
    `(properties \\ {self}) ∪ reference`.

    Returns a JSON-friendly dict:
      • n_total            — number of properties examined
      • n_covered          — how many produced a non-None signature (the metric's denominator)
      • coverage           — n_covered / n_total (the headline honesty number; the rest of the
                             metric is BLIND to the n_total - n_covered uncovered claims, which
                             is exactly where genuine, less-DSL-expressible novelty would live)
      • distinct_clusters  — number of distinct signatures among the covered properties
      • nearest_distances  — sorted list of each covered item's nearest-neighbour distance
                             (items with no neighbour at all are reported in `isolated`)
      • distance_summary   — {min, mean, max} over nearest_distances (empty dict if none)
      • isolated           — count of covered items with no neighbour to measure against
    This dict is data only — it carries no verdict and gates nothing (Prohibition 1)."""
    sigs = [s for s in signatures_of(properties) if s is not None]
    ref_sigs = [s for s in signatures_of(reference) if s is not None]
    n_total = len(properties)
    n_covered = len(sigs)

    nearest: list[float] = []
    isolated = 0
    for i, sig in enumerate(sigs):
        others = sigs[:i] + sigs[i + 1:] + ref_sigs
        d = _nearest_distance(sig, others)
        if d is None:
            isolated += 1
        else:
            nearest.append(d)
    nearest.sort()

    summary: dict = {}
    if nearest:
        summary = {
            "min": nearest[0],
            "mean": sum(nearest) / len(nearest),
            "max": nearest[-1],
        }

    return {
        "n_total": n_total,
        "n_covered": n_covered,
        "coverage": (n_covered / n_total) if n_total else 0.0,
        "distinct_clusters": len({tuple(s) for s in sigs}),
        "nearest_distances": nearest,
        "distance_summary": summary,
        "isolated": isolated,
    }
