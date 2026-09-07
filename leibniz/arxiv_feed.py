"""ADR 0069 (Phase β) — the external frontier feed: a periodic arXiv sweep proposing
AMPLIFICATION TARGETS.

The daemon's proven best work is amplification: taking a fresh published result with a
kernel-checkable finite core (an srg non-existence, a KS set, a Hadamard census…) and
re-deciding that core in the Lean kernel. Every such target so far was found by a human
reading listings. This module makes the *finding* periodic and mechanical: sweep recent
arXiv submissions in the daemon's domains, score each abstract for finite-core signals,
and queue the hits for the operator.

Trust posture — proposal-side only, and deliberately LLM-free:
- Scoring is deterministic keyword/regex evidence, not judgment. A queued entry is a
  TARGET, not a result; nothing is verified, claimed, or published by being queued.
- The feed writes only the queue files under the heartbeat home. Amplification itself
  remains the established operator-driven act (formalize → kernel → ADR 0033 publish).
- Network failure degrades to a journal note, never an abort (the beat must not depend
  on arXiv being up at 02:30).

stdlib only (urllib + xml.etree): the core install stays dependency-free.
"""
from __future__ import annotations

import json
import re
import ssl
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path

API = "https://export.arxiv.org/api/query"
CATEGORIES = ("math.NT", "math.CO", "math.AG", "quant-ph")  # quant-ph: the KS-set precedent
_ATOM = "{http://www.w3.org/2005/Atom}"
_UA = "leibniz-daemon/0.1 (theorem amplification feed; mailto:dave@elementalcollision.com)"

# Finite-core evidence: each (pattern, weight, label) is a signal that the paper's claim
# has a bounded, certificate-shaped core the kernel could re-decide. Weights are coarse;
# QUEUE_THRESHOLD is the only decision this module makes (and it only decides *queueing*).
_SIGNALS: tuple[tuple[re.Pattern, int, str], ...] = tuple(
    (re.compile(p, re.IGNORECASE), w, label) for (p, w, label) in [
        (r"\b(exhaustive(?:ly)?|computer[- ]assisted|computer search|computational proof|"
         r"SAT solver|verified by computer|enumerat\w+)\b", 2, "exhaustive/computer search"),
        (r"\b(does not exist|do not exist|there (?:is|are) no|non[- ]?existence|no such)\b",
         2, "non-existence claim"),
        (r"\b(classif(?:y|ied|ication)|census|complete (?:list|enumeration)|catalogue)\b",
         2, "classification/census"),
        # ADR 0091: was `certificate|witness` — "certified by complete Gurobi computations", the
        # phrase in the paper this feed missed, matched none of it.
        (r"\b(certificat\w+|certif(?:y|ies|ied)|witness|verifiable proof)\b", 2, "explicit certificate"),
        (r"\b(strongly regular graph|Latin square|Hadamard matri(?:x|ces)|Steiner (?:system|triple)|"
         r"block design|difference set|Kochen[–-]Specker|cap ?set|association scheme|"
         r"tournament|resolvable design)\b", 1, "finite structure"),
        (r"\bsrg\s*\(\s*\d+\s*,\s*\d+\s*,\s*\d+\s*,\s*\d+\s*\)", 2, "srg parameter tuple"),
        (r"\bof order (?:at most )?\d{1,4}\b", 1, "explicit small order"),
        (r"\b(smallest|minimal|minimum) (?:number|size|order|counterexample)\b", 1, "extremal bound"),

        # --- ADR 0091: the daemon has THREE arithmetic kernel decision procedures (ADRs 0060,
        # 0065, 0070) and this list had no vocabulary for any of them. Every signal above names a
        # finite COMBINATORIAL structure. That is why arXiv 2607.19029 — a covering system the
        # daemon has since kernel-decided and published — scored ZERO here.
        (r"\b(covering system|exact cover(?:ing)?|congruence class|residue class|"
         r"multiplicative order|primitive root|quadratic residue)\b", 2, "arithmetic structure"),
        # a modulus or lcm stated WITH A NUMBER: the extractable-core signal, not the topic word.
        # "minimum modulus" alone matched nothing — the extremal pattern above wants
        # number|size|order|counterexample, and a modulus is none of those.
        (r"\b(?:least common multiple|lcm|modulus|moduli)\b[^.]{0,60}?\d"
         r"|\b(?:minimum|minimal|least|smallest) modulus\b", 2, "stated modulus/lcm"),
        # An explicitly stated parameter tuple. ADR 0084 already EXTRACTS these; the scorer never
        # rewarded their presence. Highest-lift general signal in the labelled sample.
        (r"\(\s*-?\d+\s*(?:,\s*-?\d+\s*){2,}\)|\[\s*\d+\s*,\s*\d+\s*,\s*\d+\s*\]",
         2, "explicit parameter tuple"),
        # A solver did the hard part — so the hard part is a BOUNDED computation, which is exactly
        # what the kernel re-decides. "complete Gurobi computations" is the motivating instance.
        (r"\b(Gurobi|CPLEX|SCIP|MiniSat|CaDiCaL|Kissat|DRAT|LRAT|MaxSAT|SMT solver"
         r"|integer program\w*|mixed[- ]integer|branch[- ]and[- ]bound|ILP)\b", 2, "solver-backed"),
    ])
QUEUE_THRESHOLD = 4   # ADR 0091: 3 -> 4. Measured on 108 labelled papers, threshold 4 gives the
                      # same recall as 3 while queueing fewer; at 5 recall collapses (held-out
                      # 0.60 -> 0.20). Queue when the summed evidence reaches this.
_SUMMARY_CAP = 1500   # ADR 0084: retain enough abstract for parameter extraction, bounded
_SEEN_CAP = 4000      # bound seen_arxiv.json


def finite_core_score(title: str, summary: str) -> tuple[int, list[str]]:
    """(score, matched signal labels) for one paper — deterministic evidence, no judgment."""
    text = f"{title}\n{summary}"
    score, labels = 0, []
    for pat, weight, label in _SIGNALS:
        if pat.search(text):
            score += weight
            labels.append(label)
    return score, labels


def parse_atom(xml_bytes: bytes) -> list[dict]:
    """arXiv Atom → [{id, title, summary, published, categories, link}] (malformed → [])."""
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError:
        return []
    out = []
    for e in root.findall(f"{_ATOM}entry"):
        def _txt(tag: str, e=e) -> str:
            n = e.find(f"{_ATOM}{tag}")
            return " ".join((n.text or "").split()) if n is not None else ""
        raw_id = _txt("id")                      # http://arxiv.org/abs/2507.01234v1
        aid = raw_id.rsplit("/abs/", 1)[-1].split("v")[0] if "/abs/" in raw_id else raw_id
        cats = [c.get("term", "") for c in e.findall(f"{_ATOM}category")]
        out.append({"id": aid, "title": _txt("title"), "summary": _txt("summary"),
                    "published": _txt("published"), "categories": cats,
                    "link": f"https://arxiv.org/abs/{aid}" if aid else raw_id})
    return out


def fetch_recent(categories: tuple[str, ...] = CATEGORIES, days: int = 4,
                 max_results: int = 80, timeout: int = 30, *,
                 page_size: int = 200, max_pages: int = 8) -> list[dict]:
    """Recent submissions in `categories` (newest first), client-filtered to the last `days`.

    ADR 0091 — this PAGINATES. It used to issue one request for `max_results` newest entries and
    then filter to the window, which silently truncated: measured on a live sweep, 80 fetched
    against **at least 121** actually submitted in the same 4 days, i.e. ~66% coverage, with no
    log line and nothing in the journal. The loss was also biased. arXiv returns newest-first
    across the whole category union and quant-ph dominates by volume (27 of 80 leading
    categories on that sweep, against 11 for math.NT), so the ~41 papers falling off the end were
    the OLDEST in the window and disproportionately the arithmetic ones the daemon can decide.
    No signal set can rescue a paper that was never fetched.

    Pages until the results run older than the cutoff (which is the real stopping condition), or
    until `max_pages`. `truncated` is recorded on the returned list's last element only via
    `fetch_recent_detail`; callers that need the flag should use that. Polite: one request per
    page with a delay between, `sortBy=submittedDate` so paging is stable.
    """
    return fetch_recent_detail(categories, days, max_results, timeout,
                               page_size=page_size, max_pages=max_pages)["entries"]


def fetch_recent_detail(categories: tuple[str, ...] = CATEGORIES, days: int = 4,
                        max_results: int = 80, timeout: int = 30, *,
                        page_size: int = 200, max_pages: int = 8) -> dict:
    """`fetch_recent` plus the coverage facts: {"entries", "seen", "pages", "truncated"}.

    `truncated` is True when paging stopped while the oldest entry seen was STILL inside the
    window — i.e. more papers exist that we did not fetch. The heartbeat journals it, so a beat
    that under-sweeps says so instead of looking like a quiet night.
    """
    query = " OR ".join(f"cat:{c}" for c in categories)
    # macOS framework Pythons often ship without CA wiring; certifi (present via the propose
    # extra's client stack) supplies the bundle when the default store cannot.
    try:
        import certifi
        ctx = ssl.create_default_context(cafile=certifi.where())
    except ImportError:  # pragma: no cover
        ctx = ssl.create_default_context()

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    step = max(1, min(page_size, max(max_results, page_size)))
    fresh: list[dict] = []
    seen = 0
    pages = 0
    truncated = False
    oldest_in_window = True
    for pageno in range(max_pages):
        url = (f"{API}?search_query={urllib.parse.quote(query)}"
               f"&sortBy=submittedDate&sortOrder=descending"
               f"&start={pageno * step}&max_results={step}")
        req = urllib.request.Request(url, headers={"User-Agent": _UA})
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            entries = parse_atom(resp.read())
        pages += 1
        seen += len(entries)
        if not entries:
            oldest_in_window = False        # the feed is exhausted, not truncated
            break
        page_had_stale = False
        for e in entries:
            try:
                when = datetime.fromisoformat(e["published"].replace("Z", "+00:00"))
            except ValueError:
                continue
            if when >= cutoff:
                fresh.append(e)
            else:
                page_had_stale = True
        if page_had_stale or len(entries) < step:
            oldest_in_window = False        # we ran off the end of the window: full coverage
            break
        time.sleep(3)                       # arXiv asks for ~3s between requests
    else:
        truncated = oldest_in_window        # hit max_pages with everything still in-window
    if oldest_in_window and not truncated and pages >= max_pages:
        truncated = True
    return {"entries": fresh, "seen": seen, "pages": pages, "truncated": bool(truncated)}


def update_queue(entries: list[dict], home: Path) -> dict:
    """Score `entries`, append NEW hits to amplification_queue.jsonl, regenerate the
    operator-readable amplification_queue.md, and persist the seen-id set. Returns
    {"fetched": N, "queued": M} for the beat journal."""
    home.mkdir(parents=True, exist_ok=True)
    seen_path, jsonl_path = home / "seen_arxiv.json", home / "amplification_queue.jsonl"
    try:
        seen = set(json.loads(seen_path.read_text()))
    except (OSError, ValueError, TypeError):
        seen = set()
    queued = []
    for e in entries:
        if not e.get("id") or e["id"] in seen:
            continue
        seen.add(e["id"])
        score, labels = finite_core_score(e.get("title", ""), e.get("summary", ""))
        if score >= QUEUE_THRESHOLD:
            queued.append({"id": e["id"], "title": e.get("title", ""), "link": e.get("link", ""),
                           "summary": (e.get("summary") or "")[:_SUMMARY_CAP],
                           "published": e.get("published", ""), "categories": e.get("categories", []),
                           "score": score, "signals": labels,
                           "queued_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")})
    if queued:
        with jsonl_path.open("a") as f:
            for q in queued:
                f.write(json.dumps(q, ensure_ascii=False) + "\n")
    seen_path.write_text(json.dumps(sorted(seen)[-_SEEN_CAP:]))
    _render_md(jsonl_path, home / "amplification_queue.md")
    return {"fetched": len(entries), "queued": len(queued)}


def _render_md(jsonl_path: Path, md_path: Path, top: int = 30) -> None:
    rows: list[dict] = []
    try:
        for line in jsonl_path.read_text().splitlines():
            try:
                rows.append(json.loads(line))
            except ValueError:
                continue
    except OSError:
        pass
    rows.sort(key=lambda r: (-int(r.get("score", 0)), r.get("queued_at", "")))
    lines = ["# Amplification queue — arXiv targets (ADR 0069)", "",
             "_Candidates whose abstracts show finite-core signals. These are TARGETS, not_",
             "_results: nothing here is verified, endorsed, or claimed. Amplifying one is the_",
             "_established operator act: formalize the finite core → kernel → ADR 0033 publish._",
             ""]
    if not rows:
        lines.append("(queue empty)")
    for r in rows[:top]:
        sig = ", ".join(r.get("signals", []))
        lines.append(f"- **{r.get('score')}** · [{r.get('id')}]({r.get('link')}) · "
                     f"{r.get('title')}  \n  _{sig}_")
    if len(rows) > top:
        lines.append(f"\n({len(rows) - top} more in amplification_queue.jsonl)")
    md_path.write_text("\n".join(lines) + "\n")


#: ADR 0084 — the finite-core PARAMETER shapes, drawn from the daemon's own eleven amplifications:
#: an srg tuple (Belousova-Makhnev-Tokbaeva), an explicit order (complex Hadamard 94), a basis
#: count (Cabello KS 14), a projective-plane parameter (double blocking 3q-1), a small bound.
#: Deterministic and LLM-free, exactly like `finite_core_score`.
_PARAM_PATTERNS: tuple = tuple((re.compile(p, re.IGNORECASE), kind) for p, kind in [
    (r"\bsrg\s*\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)", "srg_parameters"),
    (r"\bstrongly regular graph[^.]{0,40}?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)", "srg_parameters"),
    (r"\border\s+(?:at most\s+)?(\d{1,5})\b", "order"),
    (r"\b(\d{1,4})\s+bases\b", "basis_count"),
    (r"\bPG\s*\(\s*(\d+)\s*,\s*(\d+)\s*\)", "projective_space"),
    (r"\bGF\s*\(\s*(\d+)\s*\)", "finite_field"),
    (r"\b(\d{1,4})\s*[x×]\s*(\d{1,4})\b", "matrix_shape"),
    (r"\b(?:smallest|minimal|minimum)[^.]{0,30}?\b(\d{1,6})\b", "extremal_value"),
])


def extract_core_parameters(title: str, summary: str = "") -> list[dict]:
    """ADR 0084 — the STATED finite-core parameters of a paper, with the span each came from.

    Deterministic regex over the paper's own words; no LLM, no inference, no arithmetic. Every
    extraction carries the verbatim `span` it was read from, so a parameter that is not literally
    present cannot appear — the anti-fabrication discipline `seeds.py` already applies to FLOOR
    values (`proof_of_use`: "a reference tying the value to the source span"), applied here.

    This reports what the paper SAYS. It verifies nothing, and it is not evidence of anything: a
    parameter tuple is a hint about where a finite core might be, for a proposer to aim at. The
    gates and the kernel still decide every conjecture that results.
    """
    text = f"{title}\n{summary}"
    out: list[dict] = []
    seen: set = set()
    for pat, kind in _PARAM_PATTERNS:
        for m in pat.finditer(text):
            values = [int(g) for g in m.groups() if g and g.isdigit()]
            key = (kind, tuple(values))
            if not values or key in seen:
                continue
            seen.add(key)
            span = " ".join(m.group(0).split())
            # Anti-fabrication: the span must be literally present in the source text.
            if span and span in " ".join(text.split()):
                out.append({"kind": kind, "values": values, "span": span})
    return out


def queued_targets(home: Path, cap: int = 6) -> list:
    """ADR 0083 — the highest-scoring queued papers as VALIDATED **TARGET** seeds.

    A TARGET seed only ever steers a PROPOSER (`seed_intake.seed_steering`); it gates nothing and
    decides nothing, and the block it produces tells the conjecturer so in as many words. That is
    what makes VALIDATED defensible for an untrusted abstract: validation here is about
    PROVENANCE — the record carries a real arXiv id, a link, and the finite-core signals that
    queued it — not about the paper's claim being true. Nothing downstream trusts it: the
    faithfulness, novelty and proof gates decide every conjecture it may inspire, exactly as if
    the daemon had thought of it unaided.

    Newest-and-highest-scoring first, capped, so a growing queue cannot flood the prompt.
    """
    from leibniz.seeds import Seed, SeedKind, SeedProvenance, SeedStatus
    rows: list[dict] = []
    try:
        for line in (Path(home) / "amplification_queue.jsonl").read_text().splitlines():
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if isinstance(r, dict) and r.get("id") and r.get("title"):
                rows.append(r)
    except OSError:
        return []
    rows.sort(key=lambda r: (-int(r.get("score", 0)), r.get("queued_at", "")), reverse=False)
    out = []
    for r in rows[:max(0, cap)]:
        params = extract_core_parameters(r["title"], r.get("summary", ""))
        out.append(Seed(
            kind=SeedKind.TARGET,
            payload={"title": r["title"], "link": r.get("link", ""),
                     "signals": r.get("signals", []),
                     "core_parameters": params},
            provenance=SeedProvenance(source_id=r["id"], url=r.get("link", ""),
                                      fetched_at=r.get("queued_at", ""),
                                      extraction_method="arxiv_feed/finite_core_score"),
            proof_of_use=r.get("link") or r["id"],   # traceable back to the source span
            status=SeedStatus.VALIDATED,
        ))
    return out


def run_feed(home: Path) -> dict:
    """One sweep: fetch → score → queue. The heartbeat's entry point.

    ADR 0091: reports `swept` and `truncated` alongside the queue counts, so an under-swept beat
    is visible in the journal instead of reading as a quiet night."""
    got = fetch_recent_detail()
    out = update_queue(got["entries"], home)
    out["swept"] = got["seen"]
    out["pages"] = got["pages"]
    out["truncated"] = got["truncated"]
    return out
