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
        (r"\b(certificate|witness|verifiable proof)\b", 2, "explicit certificate"),
        (r"\b(strongly regular graph|Latin square|Hadamard matri(?:x|ces)|Steiner (?:system|triple)|"
         r"block design|difference set|Kochen[–-]Specker|cap ?set|association scheme|"
         r"tournament|resolvable design)\b", 1, "finite structure"),
        (r"\bsrg\s*\(\s*\d+\s*,\s*\d+\s*,\s*\d+\s*,\s*\d+\s*\)", 2, "srg parameter tuple"),
        (r"\bof order (?:at most )?\d{1,4}\b", 1, "explicit small order"),
        (r"\b(smallest|minimal|minimum) (?:number|size|order|counterexample)\b", 1, "extremal bound"),
    ])
QUEUE_THRESHOLD = 3   # queue when the summed evidence reaches this
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
                 max_results: int = 80, timeout: int = 30) -> list[dict]:
    """Recent submissions in `categories` (newest first), client-filtered to the last
    `days`. One polite request; any network/HTTP failure raises to the caller (which
    treats it as a note, not an abort)."""
    query = " OR ".join(f"cat:{c}" for c in categories)
    url = (f"{API}?search_query={urllib.parse.quote(query)}"
           f"&sortBy=submittedDate&sortOrder=descending&max_results={max_results}")
    req = urllib.request.Request(url, headers={"User-Agent": _UA})
    # macOS framework Pythons often ship without CA wiring; certifi (present via the
    # propose extra's client stack) supplies the bundle when the default store cannot.
    try:
        import certifi
        ctx = ssl.create_default_context(cafile=certifi.where())
    except ImportError:  # pragma: no cover
        ctx = ssl.create_default_context()
    with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
        entries = parse_atom(resp.read())
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    fresh = []
    for e in entries:
        try:
            when = datetime.fromisoformat(e["published"].replace("Z", "+00:00"))
        except ValueError:
            continue
        if when >= cutoff:
            fresh.append(e)
    return fresh


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


def run_feed(home: Path) -> dict:
    """One sweep: fetch → score → queue. The heartbeat's entry point."""
    return update_queue(fetch_recent(), home)
