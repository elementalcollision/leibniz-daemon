"""R3 known-results corpus — a real KnownCorpus backend (structural, no judge).

Loads ``corpus/known_results.json`` (built by ``scripts/build_corpus.py``) and
settles novelty by *structure*, per ADR 0001 (retrieval + a decision procedure,
never an LLM judge):

- ``contains_equivalent`` — True iff the candidate's elaborator-canonical
  ``formal_hash`` (R1c) equals a known entry's: the same theorem up to alpha-
  renaming and notation. This is the mechanical signal that stops the daemon
  rediscovering a textbook result.
- ``nearest`` — known entries sharing the claim's subject / relation / type, as
  informational neighbours (not a promotion signal).

Runtime queries need no Lean: the entries' hashes are precomputed at build time,
so this is a pure hash/signature comparison (CI-safe).
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from leibniz.types import ClaimSignature

_DEFAULT_PATH = Path(__file__).resolve().parent.parent / "corpus" / "known_results.json"


@dataclass(frozen=True)
class CorpusEntry:
    name: str
    claim_type: str
    subject: str
    relation: str
    formal_hash: str
    # ADR 0031 Layer 2: the DSL contract predicate of this known result, for
    # decision-procedure equivalence (catches RESTATEMENTS the formal_hash misses).
    # Optional — entries without it participate only in exact-hash matching.
    claim_domain: Optional[str] = None
    claim_property: Optional[str] = None


@dataclass
class CorpusBackend:
    entries: list[CorpusEntry]
    _by_hash: dict[str, CorpusEntry] = field(default_factory=dict, repr=False)

    def __post_init__(self) -> None:
        self._by_hash = {e.formal_hash: e for e in self.entries if e.formal_hash}

    @classmethod
    def from_json(cls, path: Optional[Path] = None) -> "CorpusBackend":
        data = json.loads(Path(path or _DEFAULT_PATH).read_text())
        return cls([CorpusEntry(
            name=d["name"], claim_type=d["claim_type"], subject=d["subject"],
            relation=d["relation"], formal_hash=d["formal_hash"],
            claim_domain=d.get("claim_domain"), claim_property=d.get("claim_property"),
        ) for d in data])

    # --- KnownCorpus Protocol -------------------------------------------------
    def contains_equivalent(self, sig: ClaimSignature) -> bool:
        # A structural identity match. Empty/absent hash never matches (a candidate
        # we couldn't normalize is treated as novel, not silently KNOWN).
        return bool(sig.formal_hash) and sig.formal_hash in self._by_hash

    def equivalent_known(
        self, claim_domain: Optional[str], claim_property: Optional[str], backend,
        *, claim_type: Optional[str] = None, bound: int = 1024,
    ) -> Optional[str]:
        """ADR 0031 Layer 2: the name of a curated known result whose contract is
        DECISION-PROCEDURE-equivalent to (claim_domain, claim_property) over the box, or None.

        Catches RESTATEMENTS the exact formal_hash misses (e.g. `(n^5+4n)%5==0` vs Fermat's
        `n^5%5==n%5`). Two claims match iff their domains agree AND their properties agree on
        that domain — both as CONCLUSIVE box-equivalences (`backend.equivalent is True`); an
        inconclusive/un-encodable check never matches, so a genuine novelty is never wrongly
        demoted. `claim_type` is an optional pre-filter. Needs a backend with `.equivalent`;
        returns None if absent (safe degrade).

        SOUNDNESS (false-KNOWN risk): box-equivalence is exact for the natural class here —
        modular/divisibility predicates are periodic in n, so agreement over a box spanning the
        period IS true equivalence. The residual is a contrived predicate that diverges only
        BEYOND the box (e.g. `(P) or (n > K)` for some literal K); the default `bound=1024` puts
        the margin far past any constant the conjecturer emits, and Z3 finds any in-box
        divergence (-> not a match). The error is one-directional and BOUNDED: at worst a
        genuine novelty whose only divergence is past 1024 is wrongly demoted — and that is
        REVERSIBLE (KNOWN quarantines, never deletes; ADR 0031). A rigorous period-aware bound
        is a noted follow-up."""
        equiv = getattr(backend, "equivalent", None)
        if not (claim_domain and claim_property and callable(equiv)):
            return None
        for e in self.entries:
            if not (e.claim_domain and e.claim_property):
                continue
            if claim_type is not None and e.claim_type != claim_type:
                continue
            # domains agree, and on the (shared) domain the properties agree — both conclusive.
            if equiv(claim_domain, e.claim_domain, bound) is not True:
                continue
            if equiv(f"({claim_domain}) and ({claim_property})",
                     f"({e.claim_domain}) and ({e.claim_property})", bound) is True:
                return e.name
        return None

    def nearest(self, sig: ClaimSignature, k: int = 5) -> list[tuple[str, float]]:
        scored: list[tuple[str, float]] = []
        for e in self.entries:
            if e.formal_hash and e.formal_hash == sig.formal_hash:
                score = 1.0
            else:
                score = 0.0
                if e.subject == sig.subject:
                    score += 0.5
                if e.relation == sig.relation:
                    score += 0.3
                if e.claim_type == sig.claim_type.value:
                    score += 0.2
            if score > 0:
                scored.append((e.name, round(score, 2)))
        scored.sort(key=lambda x: (-x[1], x[0]))
        return scored[:k]
