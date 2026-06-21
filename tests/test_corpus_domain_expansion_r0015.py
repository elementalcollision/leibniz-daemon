"""ADR 0015: corpus (D4) + domain (D9) expansion (CI-safe; no Lean, no network).

The corpus hashes are precomputed by scripts/build_corpus.py, so these query the
committed corpus/known_results.json and never invoke Lean.
"""
from __future__ import annotations

from leibniz.corpus import CorpusBackend
from leibniz.daemon import Leibniz
from leibniz.gates.verification import VerificationGate
from leibniz.leonardo import LeonardoForgeAdapter
from leibniz.selection import KFM, Archive
from leibniz.trust import TrustPolicy
from leibniz.types import ClaimSignature, ClaimType


# --- D4: the known-results corpus actually grew and matches structurally ------

def test_corpus_substantially_expanded():
    cb = CorpusBackend.from_json()
    assert len(cb.entries) >= 30  # was 3 before D4


def test_corpus_hashes_are_present_and_distinct():
    cb = CorpusBackend.from_json()
    hashes = [e.formal_hash for e in cb.entries]
    assert all(hashes), "every curated entry must carry a structural hash"
    assert len(set(hashes)) == len(hashes), "distinct theorems must not collide"


def test_known_result_is_recognized_by_structural_hash():
    cb = CorpusBackend.from_json()
    known = cb.entries[0]
    sig = ClaimSignature(
        claim_type=ClaimType.STRUCTURAL, subject="anything", relation="anything",
        formal_hash=known.formal_hash,
    )
    assert cb.contains_equivalent(sig) is True


def test_unknown_and_empty_hashes_are_treated_as_novel():
    cb = CorpusBackend.from_json()
    base = dict(claim_type=ClaimType.STRUCTURAL, subject="s", relation="r")
    assert cb.contains_equivalent(ClaimSignature(formal_hash="deadbeefdeadbeef", **base)) is False
    assert cb.contains_equivalent(ClaimSignature(formal_hash="", **base)) is False


# --- D9: the frontier carries multiple domains, and runs rotate over them -----

def test_frontier_exposes_multiple_domains():
    domains = LeonardoForgeAdapter().domains()
    assert "analysis_of_algorithms" in domains
    assert len(domains) >= 3


def test_active_domains_falls_back_to_single_domain():
    d = _daemon(domains=())
    assert d._active_domains() == ("analysis_of_algorithms",)
    d2 = _daemon(domains=("x", "y"))
    assert d2._active_domains() == ("x", "y")


def test_run_cycles_rotates_across_domains():
    surveyed: list[str] = []

    class _Survey:
        def run(self, domain):
            surveyed.append(domain)
            return []  # no seeds -> cycle does no proposal work

    d = _daemon(domains=("d0", "d1"), survey=_Survey())
    d.run_cycles(4)
    # collapse consecutive duplicates (a cycle may survey its domain more than once)
    collapsed = [x for i, x in enumerate(surveyed) if i == 0 or x != surveyed[i - 1]]
    assert collapsed == ["d0", "d1", "d0", "d1"]


# --- helpers -----------------------------------------------------------------

class _Stage:
    def run(self, *a, **k):
        return a[0] if a else None


class _Runtime:
    def remember(self, p):
        pass


class _DefaultSurvey:
    def run(self, domain):
        return []


def _daemon(*, domains=(), survey=None) -> Leibniz:
    return Leibniz(
        runtime=_Runtime(), survey=survey or _DefaultSurvey(), conjecture=_Stage(),
        formalize=_Stage(), derive=_Stage(), demonstrate=_Stage(), promulgate=_Stage(),
        verification=VerificationGate(TrustPolicy()), kfm=KFM(Archive()), domains=domains,
    )
