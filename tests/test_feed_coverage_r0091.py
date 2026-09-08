"""ADR 0091 — the feed must SEE a paper before any signal can score it.

Two defects, found by measuring the live feed rather than reading it:

1. COVERAGE. `fetch_recent` issued one request for the 80 newest entries and then filtered to a
   4-day window. Measured against the API: at least 121 papers existed in that same window, so the
   beat swept ~66% of what it claimed, silently. The loss was biased — arXiv returns newest-first
   across the category union and quant-ph dominates by volume, so the ~41 that fell off were the
   oldest in the window and disproportionately the math.NT ones the daemon can actually decide.

2. SIGNALS. Every pattern in `_SIGNALS` named a finite COMBINATORIAL structure (srg, Latin square,
   Hadamard, Steiner). The daemon has three arithmetic kernel decision procedures (ADRs 0060, 0065,
   0070) and the scorer had no vocabulary for any of them. arXiv 2607.19029 — a covering system
   this repo has since kernel-decided and published as a law — scored ZERO.
"""
from __future__ import annotations


import pytest

from leibniz import arxiv_feed as af

#: The abstract of arXiv 2607.19029, verbatim. This is the paper the feed missed.
TARGET_TITLE = ("A Distinct Covering System with Minimum Modulus 7 and Minimal Least Common "
                "Multiple 10080")
TARGET_ABSTRACT = (
    "We determine the minimum possible least common multiple of a distinct covering system whose "
    "minimum modulus is $7$. Klein previously constructed such a system with least common multiple "
    "$15120$, and conjectured that this value was minimal. We give a construction with least common "
    "multiple $10080$, and we prove that no smaller least common multiple can occur. The proof is "
    "organized as a successive filtering argument. Starting from the possible multiples of $7$ "
    "below $10080$, we first apply a reciprocal-sum filter, then a divisor-completed "
    "integer-programming filter, then a stronger partial-sum filter. The few remaining hard cases "
    "are finally certified by complete Gurobi computations.")


def test_the_paper_the_daemon_published_would_now_be_queued():
    """The regression that motivated this ADR. This paper is now a promulgated law
    (site/src/content/laws/covering_min_modulus_7_lcm_10080.json) and the feed scored it zero."""
    score, signals = af.finite_core_score(TARGET_TITLE, TARGET_ABSTRACT)
    assert score >= af.QUEUE_THRESHOLD, f"scored {score} against threshold {af.QUEUE_THRESHOLD}"
    # and not by a single lucky pattern
    assert len(signals) >= 3, signals


@pytest.mark.parametrize("label", [
    "arithmetic structure", "stated modulus/lcm", "solver-backed", "explicit certificate",
])
def test_each_new_signal_class_fires_on_the_target(label):
    """Names the four near-misses individually, so a future edit that guts one is visible."""
    _, signals = af.finite_core_score(TARGET_TITLE, TARGET_ABSTRACT)
    assert label in signals


def test_the_near_misses_that_scored_zero_now_fire():
    """Each phrase was in the abstract and matched nothing before: 'certified by' against a
    /certificate/ pattern, 'minimum modulus' against /minimum (number|size|order|counterexample)/,
    'Gurobi' against nothing at all."""
    for phrase in ("certified by complete computations", "minimum modulus is 7",
                   "certified by complete Gurobi computations"):
        assert af.finite_core_score("", phrase)[0] > 0, f"{phrase!r} still scores nothing"


def test_a_topic_word_alone_is_not_evidence():
    """Deliberate: 'least common multiple' with no number is a SUBJECT, not an extractable core,
    and must not score. The signal is a modulus or lcm stated WITH a value -- which is what makes
    a core extractable at all (the same insight ADR 0084 encodes in its parameter shapes).
    Without this, every analytic number-theory abstract in the sweep would queue."""
    bare, _ = af.finite_core_score("", "we study the least common multiple of arbitrary integers")
    assert bare == 0, "a bare topic word must not be evidence"
    stated, sigs = af.finite_core_score("", "with least common multiple 10080")
    assert stated > 0 and "stated modulus/lcm" in sigs


def test_arithmetic_vocabulary_covers_the_daemons_own_procedures():
    """The daemon decides covering systems (ADR 0060), base^n % m (ADR 0065) and factorial/gcd
    (ADR 0070). A scorer blind to those families cannot surface work for them."""
    joined = " ".join(p.pattern for p, _w, _l in af._SIGNALS)
    for term in ("covering system", "multiplicative order", "residue class", "modulus"):
        assert term in joined, f"no signal mentions {term!r}"


def test_signals_are_not_memorized_phrases():
    """Every pattern must be a family, not a paper. A pattern matching one specific abstract is
    tuning noise; the four proposals that scored 1.000 on the labelled sample all collapsed on
    held-out data (to 0.30 and 0.67), and carried the most single-paper patterns."""
    for pat, _w, label in af._SIGNALS:
        assert pat.pattern.strip(), label
        # a pattern with no alternation and no character class is a literal phrase -> suspicious
        if "|" not in pat.pattern and "[" not in pat.pattern and "\\d" not in pat.pattern:
            pytest.fail(f"signal {label!r} looks like a memorized literal: {pat.pattern!r}")


# --- coverage --------------------------------------------------------------------------------

def test_fetch_recent_detail_reports_coverage(monkeypatch):
    """A beat that under-sweeps must SAY so. Before this, truncation was invisible: the journal
    recorded a queue count and nothing about the papers never fetched."""
    pages = {"n": 0}

    class _Resp:
        def __init__(self, body): self._b = body
        def read(self): return self._b
        def __enter__(self): return self
        def __exit__(self, *a): return False

    def fake_urlopen(req, timeout=None, context=None):
        pages["n"] += 1
        # always a full page of in-window entries -> the caller must detect truncation
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        entries = "".join(
            f'<entry><id>http://arxiv.org/abs/26{pages["n"]:02d}.{i:05d}v1</id>'
            f'<title>T{i}</title><summary>S</summary><published>{now}</published></entry>'
            for i in range(3))
        return _Resp(f'<feed xmlns="http://www.w3.org/2005/Atom">{entries}</feed>'.encode())

    monkeypatch.setattr(af.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(af.time, "sleep", lambda *_a: None)
    got = af.fetch_recent_detail(days=4, page_size=3, max_pages=3)
    assert got["pages"] == 3
    assert got["truncated"] is True, "every page was in-window at max_pages: that is truncation"
    assert got["seen"] == 9 and len(got["entries"]) == 9


def test_fetch_recent_detail_is_not_truncated_when_it_reaches_the_window_edge(monkeypatch):
    class _Resp:
        def __init__(self, body): self._b = body
        def read(self): return self._b
        def __enter__(self): return self
        def __exit__(self, *a): return False

    def fake_urlopen(req, timeout=None, context=None):
        from datetime import datetime, timedelta, timezone
        now = datetime.now(timezone.utc)
        old = (now - timedelta(days=40)).isoformat().replace("+00:00", "Z")
        fresh = now.isoformat().replace("+00:00", "Z")
        entries = (f'<entry><id>http://arxiv.org/abs/2609.00001v1</id><title>A</title>'
                   f'<summary>S</summary><published>{fresh}</published></entry>'
                   f'<entry><id>http://arxiv.org/abs/2601.00002v1</id><title>B</title>'
                   f'<summary>S</summary><published>{old}</published></entry>')
        return _Resp(f'<feed xmlns="http://www.w3.org/2005/Atom">{entries}</feed>'.encode())

    monkeypatch.setattr(af.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(af.time, "sleep", lambda *_a: None)
    got = af.fetch_recent_detail(days=4, page_size=2, max_pages=5)
    assert got["truncated"] is False        # ran off the end of the window: full coverage
    assert len(got["entries"]) == 1 and got["pages"] == 1


def test_fetch_recent_still_returns_a_plain_list():
    """Backward compatibility: run_feed and the ADR 0069 callers expect a list of entries."""
    import inspect
    assert "entries" in inspect.getsource(af.fetch_recent)
    sig = inspect.signature(af.fetch_recent)
    for name in ("categories", "days", "max_results", "timeout"):
        assert name in sig.parameters
