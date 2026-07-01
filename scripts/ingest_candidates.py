"""Research-ingestion triage adapter (baseline, Track 3) — the non-trust on-ramp from the arxiv feed to
the amplification spine.

The scraper at `.../arxiv_feed/feeds/latest/leibniz.json` surfaces ~120 records/week (title + abstract +
citation only — no PDF, no enumerated witnesses). The measure-before-build probe over 5 on-disk runs found
**0** records carrying an extractable finite witness in a supported domain (cwc / covering) — so the
automated *witness* yield is zero, and this baseline is the **triage + provenance** half:

    leibniz.json --> classify domain_guess (lexical) --> parse an EXPLICIT witness if present (rare)
        - explicit witness in a supported domain -> an amplify-ready feed entry (kernel decides later)
        - everything else -> an operator worklist (record + why-not: unsupported / needs-reconstruction)

It DECIDES nothing: it only routes. The Lean kernel + the validated table oracle remain the sole deciders,
via the unchanged amplify.amplify_one path. No LLM. No PROTECTED file touched (seeds.py / seed_intake.py
are read-only seams; this adapter builds amplify-shaped dicts directly). Never promulgates.

RUNS WHERE: free-CPU, anywhere (pure lexical + literal parsing). The DOWNSTREAM amplify step (if a candidate
appears) needs docker for the kernel; run `scripts/amplify.py --feed <candidates.json>` then.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_FEED = Path("/Users/dave/Agent_Data/Agents (Chimera, Newton, Leibniz)/arxiv_feed/"
                    "feeds/latest/leibniz.json")

_CWC_RE = re.compile(r"A\(\s*\d+\s*,|constant[- ]weight code", re.I)
_COV_RE = re.compile(r"covering design|covering number|C\(\s*\d+\s*,\s*\d+\s*,", re.I)
_LISTOFLISTS_RE = re.compile(r"\[\s*\[\s*\d+")


def classify_domain(text: str) -> str:
    """Lexical domain guess. Purely a router hint — a wrong guess is harmless (a malformed/absent witness is
    skipped by amplify_one, or kernel-rejected)."""
    if _CWC_RE.search(text):
        return "cwc"
    if _COV_RE.search(text):
        return "covering"
    return "none"


def parse_explicit_witness(record: dict, domain: str) -> dict | None:
    """Return an amplify-shaped witness ONLY if the record carries an explicit, machine-usable one:
    (a) a structured `witness` field (the clean automatable case — a producer or a structured feed), or
    (b) — conservatively — nothing from free text (abstracts do not enumerate witnesses; we do not
    fabricate). Returns {domain, ...params, blocks|code} or None."""
    w = record.get("witness")
    if isinstance(w, dict):
        d = (w.get("domain") or domain or "").lower()
        if d == "covering" and all(k in w for k in ("v", "k", "t", "blocks")):
            return {"domain": "covering", "v": int(w["v"]), "k": int(w["k"]), "t": int(w["t"]),
                    "blocks": [list(map(int, b)) for b in w["blocks"]]}
        if d == "cwc" and all(k in w for k in ("n", "d", "w", "code")):
            return {"domain": "cwc", "n": int(w["n"]), "d": int(w["d"]), "w": int(w["w"]),
                    "code": [list(map(int, c)) for c in w["code"]]}
    return None  # free-text abstracts carry methods/theorems, not enumerated witnesses — never fabricate


def _record_id(r: dict) -> str:
    return str(r.get("id") or r.get("url") or r.get("title", "?"))[:120]


def _proof_of_use(r: dict) -> str:
    cit = r.get("citation") or {}
    return (cit.get("plain") if isinstance(cit, dict) else None) or r.get("url") or _record_id(r)


def triage(records: list[dict]) -> dict:
    candidates, worklist = [], []
    dom_counts = {"cwc": 0, "covering": 0, "none": 0}
    for r in records:
        text = f"{r.get('title', '')} {r.get('abstract', '')}"
        dom = classify_domain(text)
        dom_counts[dom] += 1
        wit = parse_explicit_witness(r, dom) if dom != "none" else None
        if wit is not None:
            candidates.append({**wit, "source": _record_id(r),
                               "note": f"arxiv-ingest: {r.get('title', '')[:80]}",
                               "proof_of_use": _proof_of_use(r)})
        elif dom != "none":
            worklist.append({"id": _record_id(r), "title": r.get("title", "")[:120],
                             "domain_guess": dom, "reason": "supported-domain mention but NO explicit "
                             "witness (needs reconstruction / full text) — operator or stronger producer"})
    return {"n_records": len(records), "domain_counts": dom_counts,
            "candidates": candidates, "worklist": worklist}


def render_worklist(res: dict, run_label: str) -> str:
    out = [f"# Research-ingestion worklist — {run_label}", "",
           "*Non-trust triage of the arxiv feed. Candidates with an explicit witness route to the "
           "amplification spine (the kernel decides); the rest are an operator/stronger-producer queue. "
           "Nothing here is decided or promulgated.*", "",
           f"- records triaged: **{res['n_records']}**",
           f"- domain guesses: cwc={res['domain_counts']['cwc']}, "
           f"covering={res['domain_counts']['covering']}, none={res['domain_counts']['none']}",
           f"- **amplify-ready candidates (explicit witness): {len(res['candidates'])}**",
           f"- worklist (domain mention, no witness): {len(res['worklist'])}", ""]
    if res["candidates"]:
        out += ["## Amplify-ready candidates", "", "| domain | source | note |", "|---|---|---|"]
        for c in res["candidates"]:
            out.append(f"| {c['domain']} | {c['source']} | {c['note']} |")
        out.append("")
    out += ["## Operator worklist (needs a witness)", ""]
    if res["worklist"]:
        out += ["| id | domain | title | why |", "|---|---|---|---|"]
        for w in res["worklist"]:
            out.append(f"| {w['id']} | {w['domain_guess']} | {w['title']} | {w['reason']} |")
    else:
        out.append("*No supported-domain records this run (the feed is complexity/logic/NT-heavy; the "
                   "automated witness yield is 0 — see docs/ingestion-pipeline-baseline.md).*")
    return "\n".join(out) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description="Triage the arxiv feed into amplify candidates + an operator "
                                             "worklist (non-trust; the kernel decides downstream).")
    ap.add_argument("--feed", default=str(DEFAULT_FEED), help=f"leibniz.json path (default {DEFAULT_FEED})")
    ap.add_argument("--candidates-out", default=str(_ROOT / "docs" / "results" / "ingestion_candidates.json"))
    ap.add_argument("--worklist-out", default=str(_ROOT / "docs" / "results" / "ingestion_worklist.md"))
    args = ap.parse_args()

    feed = Path(args.feed)
    if not feed.exists():
        raise SystemExit(f"feed not found: {feed} (run the scraper, or pass --feed)")
    data = json.loads(feed.read_text())
    records = data if isinstance(data, list) else (data.get("records") or data.get("items") or [])
    res = triage(records)
    Path(args.candidates_out).write_text(json.dumps(res["candidates"], indent=2) + "\n")
    Path(args.worklist_out).write_text(render_worklist(res, feed.parent.name))
    print(f"ingest triage: {res['n_records']} records -> {len(res['candidates'])} amplify-ready "
          f"candidate(s), {len(res['worklist'])} worklist item(s)  (domains {res['domain_counts']})")
    print(f"  candidates -> {args.candidates_out}")
    print(f"  worklist   -> {args.worklist_out}")
    if res["candidates"]:
        print(f"  next: python3 scripts/amplify.py --feed {args.candidates_out}  (needs docker for kernel)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
