"""Verification-amplification spine (ADR 0042 Track A, slice A1) — batch intake → kernel-verify → corpus.

This is the first-class, repeatable form of what Gate D0 did by hand for 5 cells: take a *collection* of
externally-supplied constructions (from research, the scraper's CONSTRUCTION seeds, or a stronger
producer) and run each through the already-validated sound audit path, accumulating a durable,
provenance'd **kernel-checked corpus**:

    feed entry --> cwc_check.check  (verify_cwc --> render_cwc_lean --> Lean kernel --> automated oracle)
               --> augment with provenance (source, stamp, cell, witness)
               --> merge into the kernel-checked-corpus JSON  (dedup by domain/cell/size/source/witness)
               --> render a reading-room markdown

WHAT THIS IS / IS NOT (the same posture as scripts/cwc_check.py — read before trusting the output):
- It is the **verification-amplification** mode: a stronger/human/research producer PROPOSES a finite
  construction; the daemon's existing sound checker DECIDES (the Lean kernel re-checks). This is the
  capability Gate D0 measured GREEN.
- It is **audit-tier**. It NEVER sets `Demonstratio.kernel_verified` and NEVER promulgates — it only
  calls `cwc_check.check` (which is itself audit-only) and writes JSON/markdown artifacts. The trust
  boundary (`LeanVerifier.discharge` as the sole `kernel_verified` writer; `TrustPolicy.validate_path`
  for promotion) is untouched. The corpus is a *ledger of audits*, not the Codex and not the published
  Calculemus. Promoting an audited construction into the Codex is a separate, fuller step (ADR 0042
  Track C / the publish gate), deliberately out of scope here.
- The kernel step needs the Lean docker image; without it each entry still runs verify_cwc + the oracle
  and the kernel field reads "unavailable" (NOT a pass).

Pure stdlib + the project's own modules.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT / "scripts"))
sys.path.insert(0, str(_ROOT))

import covering_check  # noqa: E402  (ADR 0043 Track B1: 2nd domain — covering designs)
import cwc_check  # noqa: E402  (audit path: verify -> render -> kernel -> oracle)

DEFAULT_CORPUS = _ROOT / "docs" / "results" / "amplification_corpus.json"

# Finite-witness domains whose witnesses the spine can audit through the sound kernel path.
SUPPORTED_DOMAINS = ("cwc", "covering")


def _norm_code(code) -> list[list[int]]:
    """Canonical list-of-lists form (sorted within each codeword) for JSON + stable hashing."""
    return [sorted(int(x) for x in cw) for cw in code]


def _witness_hash(code) -> str:
    """Order-insensitive content hash of a witness, so the same construction dedups regardless of order."""
    canon = sorted(tuple(cw) for cw in _norm_code(code))
    return hashlib.sha1(repr(canon).encode()).hexdigest()[:12]


def corpus_key(report: dict) -> str:
    """Stable, domain-agnostic dedup key: a re-run that newly kernel-verifies an entry REPLACES the
    older record. `cell` encodes the domain's parameters (e.g. 'A(13,6,5)' or 'C(9,3,2)')."""
    return (f"{report['domain']}:{report['cell']}:{report['size']}:"
            f"{report.get('source', 'unknown')}:{report['witness_sha']}")


def amplify_one(entry: dict, *, run_kernel: bool = True, stamp: str | None = None) -> dict:
    """Audit one construction entry through the sound kernel path. Returns an augmented report (never
    mutates any ledger). An unsupported domain / malformed entry is recorded as skipped rather than
    raising, so a mixed feed still processes its valid entries."""
    domain = (entry.get("domain") or "cwc").strip().lower()
    source = entry.get("source", "unknown")
    if domain not in SUPPORTED_DOMAINS:
        return {"domain": domain, "source": source, "skipped":
                f"unsupported domain {domain!r} (supported: {SUPPORTED_DOMAINS})"}
    try:
        if domain == "cwc":
            n, d, w = int(entry["n"]), int(entry["d"]), int(entry["w"])
            witness = _norm_code(entry["code"])
            report = cwc_check.check(n, d, w, witness, run_kernel=run_kernel)
            cell = f"A({n},{d},{w})"
        else:  # covering
            v, k, t = int(entry["v"]), int(entry["k"]), int(entry["t"])
            witness = _norm_code(entry["blocks"])
            report = covering_check.check(v, k, t, witness, run_kernel=run_kernel)
            cell = f"C({v},{k},{t})"
    except (KeyError, TypeError, ValueError) as e:
        return {"domain": domain, "source": source, "skipped": f"malformed {domain} entry: {e}"}

    report.update({  # audit-only; never promulgates
        "domain": domain,
        "cell": cell,
        "source": source,
        "note": entry.get("note"),
        "witness_sha": _witness_hash(witness),
        "witness": witness,
        "stamped": stamp,
    })
    return report


def merge_corpus(existing: list[dict], new: list[dict]) -> list[dict]:
    """Merge new audits into the corpus, deduped by `corpus_key` (new wins), sorted by cell then size."""
    by_key: dict[str, dict] = {}
    for r in existing:
        try:
            by_key[corpus_key(r)] = r
        except KeyError:
            continue  # tolerate hand-edited / older-shape rows
    for r in new:
        by_key[corpus_key(r)] = r
    return sorted(by_key.values(),
                  key=lambda r: (r["domain"], r.get("cell", ""), r["size"]))


def _verified(report: dict) -> bool:
    return str(report.get("kernel", "")) == "KERNEL-VERIFIED"


def render_corpus(corpus: list[dict], *, title: str = "Kernel-checked construction corpus") -> str:
    """Render the corpus as a reading-room markdown table. Audit-tier banner is explicit."""
    n_verified = sum(1 for r in corpus if _verified(r))
    head = [
        f"# {title}",
        "",
        "*Verification-amplification ledger (ADR 0042 Track A). A stronger/human/research producer "
        "proposes a finite construction; the Lean kernel re-checks it. **Audit-tier — these are kernel "
        "re-checks, not promulgated laws**: nothing here is in the Codex or the published Calculemus.*",
        "",
        f"**{n_verified}/{len(corpus)} entries kernel-verified.**",
        "",
        "| cell | size | kernel | novelty | source |",
        "|---|---|---|---|---|",
    ]
    for r in corpus:
        head.append(f"| {r['cell']} | {r['size']} | {r.get('kernel','?')} | "
                    f"{r.get('novelty','?')} | {r.get('source','unknown')} |")
    return "\n".join(head) + "\n"


_DOMAIN_LABEL = {"cwc": "Constant-weight codes — A(n,d,w) lower bounds",
                 "covering": "Covering designs — C(v,k,t) upper bounds"}


def render_reading_room(corpus: list[dict],
                        *, title: str = "Calculemus — Audit Annex (kernel-checked constructions)") -> str:
    """Render the corpus as the Calculemus AUDIT ANNEX (ADR 0042 Track A3): grouped by domain, with
    provenance. Explicitly NOT the Codex / published Calculemus — these are kernel re-checks, not laws."""
    n_ver = sum(1 for r in corpus if _verified(r))
    domains = sorted({r.get("domain", "?") for r in corpus})
    out = [
        f"# {title}",
        "",
        "*Kernel re-checks of externally-supplied / producer constructions (the verification-amplification "
        "spine). This is an **AUDIT ANNEX**: NOT the Codex, NOT the published Calculemus — nothing here is "
        "a promulgated law. Each row is a finite witness the Lean kernel independently re-checked; novelty "
        "is an automated table-of-record lookup (never an LLM).*",
        "",
        f"**{n_ver}/{len(corpus)} kernel-verified, across {len(domains)} domain(s).**",
        "",
    ]
    by_dom: dict[str, list[dict]] = {}
    for r in corpus:
        by_dom.setdefault(r.get("domain", "?"), []).append(r)
    for dom in sorted(by_dom):
        out += [f"## {_DOMAIN_LABEL.get(dom, dom)}", "",
                "| cell | size | kernel | novelty | source |", "|---|---|---|---|---|"]
        for r in sorted(by_dom[dom], key=lambda r: (r.get("cell", ""), r.get("size", 0))):
            out.append(f"| {r.get('cell','?')} | {r.get('size','?')} | {r.get('kernel','?')} | "
                       f"{r.get('novelty','?')} | {r.get('source','?')} |")
        out.append("")
    return "\n".join(out)


def load_feed(path: Path) -> list[dict]:
    """A feed is a JSON list of entries, or {'constructions': [...]}."""
    data = json.loads(Path(path).read_text())
    if isinstance(data, dict):
        data = data.get("constructions", [])
    if not isinstance(data, list):
        raise SystemExit(f"feed {path} must be a JSON list (or {{'constructions': [...]}})")
    return data


def main() -> int:
    ap = argparse.ArgumentParser(description="Batch verification-amplification: audit external "
                                             "constructions through the sound kernel path into a "
                                             "kernel-checked corpus. NOT a promulgation path.")
    ap.add_argument("--feed", required=True, help="JSON feed: [{domain,n,d,w,code,source,note}, ...]")
    ap.add_argument("--corpus", default=str(DEFAULT_CORPUS),
                    help=f"kernel-checked corpus JSON (read + merge + write); default {DEFAULT_CORPUS}")
    ap.add_argument("--render", help="also write a plain reading-room markdown table to this path")
    ap.add_argument("--reading-room", help="also write the Calculemus audit-annex markdown to this path")
    ap.add_argument("--no-kernel", action="store_true", help="skip the Lean kernel step (pre-check only)")
    ap.add_argument("--stamp", help="provenance timestamp to record on new entries (ISO string)")
    ap.add_argument("--json", action="store_true", help="print the per-entry reports as JSON")
    args = ap.parse_args()

    feed = load_feed(Path(args.feed))
    reports = [amplify_one(e, run_kernel=not args.no_kernel, stamp=args.stamp) for e in feed]
    audited = [r for r in reports if "skipped" not in r]
    skipped = [r for r in reports if "skipped" in r]

    corpus_path = Path(args.corpus)
    existing = json.loads(corpus_path.read_text()) if corpus_path.exists() else []
    merged = merge_corpus(existing, audited)
    corpus_path.parent.mkdir(parents=True, exist_ok=True)
    corpus_path.write_text(json.dumps(merged, indent=2) + "\n")

    if args.render:
        Path(args.render).write_text(render_corpus(merged))
    if args.reading_room:
        Path(args.reading_room).write_text(render_reading_room(merged))

    if args.json:
        print(json.dumps(reports, indent=2))
    else:
        n_ver = sum(1 for r in audited if _verified(r))
        n_ok = sum(1 for r in audited if r.get("verify_ok"))
        print(f"amplify: {len(feed)} feed entries -> {len(audited)} audited "
              f"({n_ok} valid, {n_ver} KERNEL-VERIFIED), {len(skipped)} skipped")
        for r in skipped:
            print(f"  skipped [{r.get('source','?')}]: {r['skipped']}")
        print(f"  corpus: {len(merged)} entries -> {corpus_path}  [audit-tier; not promulgated]")

    # exit non-zero if any audited entry FAILED its untrusted pre-check (a malformed witness in the feed)
    return 0 if all(r.get("verify_ok", False) for r in audited) or not audited else 1


if __name__ == "__main__":
    raise SystemExit(main())
