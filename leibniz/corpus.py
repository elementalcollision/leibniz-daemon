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

from leibniz.structural import congruence_signature
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
    _by_sig: dict[tuple, str] = field(default_factory=dict, repr=False)  # ADR 0032

    def __post_init__(self) -> None:
        self._by_hash = {e.formal_hash: e for e in self.entries if e.formal_hash}
        # ADR 0032: precompute structural congruence signatures for entries with a DSL predicate
        self._by_sig = {}
        for e in self.entries:
            if e.claim_property:
                s = congruence_signature(e.claim_property)
                if s is not None:
                    self._by_sig.setdefault(s, e.name)

    @classmethod
    def from_json(cls, path: Optional[Path] = None,
                  extra: Optional[list["CorpusEntry"]] = None) -> "CorpusBackend":
        """Load the curated known-results corpus, optionally augmented with `extra` entries
        (ADR 0052: the daemon's own promulgated laws, so it stops rediscovering itself)."""
        data = json.loads(Path(path or _DEFAULT_PATH).read_text())
        entries = [CorpusEntry(
            name=d["name"], claim_type=d["claim_type"], subject=d["subject"],
            relation=d["relation"], formal_hash=d["formal_hash"],
            claim_domain=d.get("claim_domain"), claim_property=d.get("claim_property"),
        ) for d in data]
        if extra:
            entries = entries + list(extra)
        return cls(entries)

    # --- KnownCorpus Protocol -------------------------------------------------
    def contains_equivalent(self, sig: ClaimSignature) -> bool:
        # A structural identity match. Empty/absent hash never matches (a candidate
        # we couldn't normalize is treated as novel, not silently KNOWN).
        return bool(sig.formal_hash) and sig.formal_hash in self._by_hash

    def structural_known(self, claim_property: Optional[str]) -> Optional[str]:
        """ADR 0032: the name of a curated known whose polynomial congruence is structurally
        IDENTICAL to `claim_property`'s (same signature), or None. Catches RESTATEMENTS the
        exact elaborator-hash misses (e.g. `(n^5+4n)%5==0` vs Fermat `n^5%5==n%5`) by FORM, not
        truth — so it cannot false-KNOWN (a different congruence has a different signature), the
        unsoundness that retracted ADR 0031 L2. Unrecognized shapes -> None -> stays NOVEL."""
        s = congruence_signature(claim_property)
        return self._by_sig.get(s) if s is not None else None

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


def self_ledger_entries(db_path: Optional[str]) -> list[CorpusEntry]:
    """ADR 0052 — the daemon's OWN promulgated laws, as corpus entries, so a re-conjecture of a
    law it already promulgated is caught as KNOWN (novelty against the ledger, not only the external
    corpus — closing the HANDOFF §6 gap the daemon demonstrated by re-deriving n^4 % 5).

    Soundness: the novelty gate is KILL-ONLY (it can quarantine, never promote), so seeding it with
    more knowns can never cause an unsound promulgation — only prevent a rediscovery. Matching is by
    the elaborator-canonical ``formal_hash`` (the same signal ``contains_equivalent`` uses), so a
    genuinely distinct statement has a distinct hash and is never false-KNOWN. Read-only and
    fail-safe: an absent/unreadable DB yields no entries, degrading to external-corpus-only behaviour.
    Only PROMULGATED, kernel-verified laws seed the ledger — an unproven prior attempt must remain
    re-attemptable."""
    import sqlite3
    if not db_path:
        return []
    try:
        con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    except Exception:
        return []
    try:
        rows = con.execute(
            "SELECT theorem_src, normalized_hash, claim_type, claim_property FROM memory "
            "WHERE lower(finish_reason) = 'promulgated' AND kernel_verified = 1 "
            "AND normalized_hash IS NOT NULL AND normalized_hash != ''"
        ).fetchall()
    except Exception:
        return []
    finally:
        con.close()
    out: list[CorpusEntry] = []
    for theorem_src, formal_hash, claim_type, claim_property in rows:
        parts = (theorem_src or "").split()
        name = parts[1] if len(parts) > 1 else (theorem_src or "law")
        out.append(CorpusEntry(
            name=f"ledger:{name}", claim_type=claim_type or "invariant",
            subject="daemon_ledger", relation="promulgated",
            formal_hash=formal_hash, claim_property=claim_property,
        ))
    return out
