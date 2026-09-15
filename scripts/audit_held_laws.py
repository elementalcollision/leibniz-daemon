#!/usr/bin/env python3
"""Re-discharge every HELD law through the CURRENT mint, and report what no longer passes.

A `kernel_verified` verdict is only as good as the build that minted it. The guards have moved
repeatedly -- ADR 0097 (the axiom check is enforced by the sole kernel writer), ADR 0098 (a
lean4checker kernel replay), ADR 0100 (the mint reads what the statement DENOTES) -- and the review
queue holds laws minted under every generation of them. ADR 0101 made that concrete: on 2026-09-15
the beat ran pinned four trust-boundary ADRs behind `origin/main` and promulgated a law. Nothing
was published, but the verdict came from a build with a known hole.

This replaces each stored verdict with a MEASURED one. It asks `independent_axiom_footprint`, which
compiles the law, replays it through a bare kernel, and reads the axiom closure and the denotation
out of `ConstantInfo` data -- so nothing here trusts the stored `kernel_verified` column, the
`qed` column, or the source text.

Read-only with respect to the runtime DB and the review queue: it writes nothing back, because
re-verification is evidence, not a promotion. Publication remains the operator's ADR 0033 act.

Results stream to a JSONL one line per law, so a kill loses at most the law in flight and a re-run
resumes where it stopped. Exits non-zero if ANY held law fails, so it can gate.

Caveats it does not hide:
  * the runtime DB stores neither `imports` nor `preamble`, so every law is re-discharged against
    `Mathlib` (a superset of what these need) with an empty preamble. That is correct for the
    proposer path -- nothing in `leibniz/` writes a preamble (measured, ADR 0099) -- but it means
    this does not reproduce each law's exact import set, and ADR 0100's preamble surface is not
    exercised here.
  * it checks that a law's PROOF is mechanically sound. Whether the formal statement says what the
    natural-language claim says is the ADR 0002 faithfulness gate, not this.

Usage:  python scripts/audit_held_laws.py [--out PATH] [--limit N] [--fresh]
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))   # run as `python scripts/...`, like the sibling audits

from leibniz.backends.lean_cli import LeanCliBackend, available   # noqa: E402
from leibniz.propositio import Expressio                          # noqa: E402

# A superset of what any proposer-path law needs. See the caveat above.
IMPORTS = ("Mathlib",)


def db_path() -> Path:
    return Path(os.environ.get("LEIBNIZ_RUNTIME_DB") or (ROOT / ".leibniz" / "memory.db"))


def already_swept(out: Path) -> set[str]:
    """Resume support: a pid with a recorded line is not re-run."""
    if not out.exists():
        return set()
    seen: set[str] = set()
    for line in out.read_text(encoding="utf-8").splitlines():
        try:
            seen.add(json.loads(line)["pid"])
        except Exception:
            continue          # a truncated final line from a kill -- re-run that law
    return seen


def held_laws(db: sqlite3.Connection) -> list[sqlite3.Row]:
    return db.execute(
        "select * from memory where finish_reason='promulgated' order by ts"
    ).fetchall()


def verdict(backend, row: sqlite3.Row) -> dict:
    """The measured verdict for one law. Every failure mode is a REFUSAL, never a skip."""
    expr = Expressio(theorem_src=row["theorem_src"], imports=IMPORTS, preamble="")
    try:
        rep = backend.independent_axiom_footprint(expr, row["proof_src"] or "")
    except Exception as e:                       # a crash is a failure, not a pass
        return {"ok": False, "reason": f"exception: {type(e).__name__}: {e}"}
    if rep is None:
        # ADR 0097: the caller treats None as FAIL, never as a pass. Preserve that rather than
        # silently skipping the law, which would read as "swept and clean".
        return {"ok": False, "reason": "backend unavailable (None) -- treated as FAIL"}
    return rep


def main() -> int:
    ap = argparse.ArgumentParser(description="Re-discharge held laws through the current mint.")
    ap.add_argument("--out", default=str(ROOT / ".leibniz" / "held-law-sweep.jsonl"))
    ap.add_argument("--limit", type=int, default=0, help="stop after N laws (0 = all)")
    ap.add_argument("--fresh", action="store_true", help="ignore prior results and re-run all")
    args = ap.parse_args()

    if not available():
        print("FAIL: docker + the Lean verify image are required; this audit cannot run.",
              file=sys.stderr)
        return 2                                  # ADR 0093 -- a lane that cannot run must say so

    p = db_path()
    if not p.exists():
        print(f"FAIL: no runtime DB at {p}", file=sys.stderr)
        return 2

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    if args.fresh and out.exists():
        out.unlink()

    db = sqlite3.connect(p)
    db.row_factory = sqlite3.Row
    held = held_laws(db)
    done = already_swept(out)
    todo = [r for r in held if r["pid"] not in done]
    if args.limit:
        todo = todo[: args.limit]

    print(f"held: {len(held)}   already swept: {len(done)}   to do: {len(todo)}", flush=True)
    backend = LeanCliBackend(timeout_s=900)
    failures: list[dict] = []

    with out.open("a", encoding="utf-8") as f:
        for i, row in enumerate(todo, 1):
            t0 = time.time()
            rep = verdict(backend, row)
            ok = bool(rep.get("ok"))
            rec = {
                "pid": row["pid"], "ts": row["ts"], "ok": ok, "reason": rep.get("reason"),
                "axioms": rep.get("axioms"), "extra_axioms": rep.get("extra_axioms"),
                "has_sorry": rep.get("has_sorry"), "root_ok": rep.get("root_ok"),
                "nested": rep.get("nested"), "shadowed": rep.get("shadowed"),
                "vacuous": rep.get("vacuous"),
                "denotation": (rep.get("denotation") or "")[:200],
                "secs": round(time.time() - t0, 1),
                "theorem_head": (row["theorem_src"] or "")[:110].replace("\n", " "),
            }
            f.write(json.dumps(rec) + "\n")
            f.flush()
            if not ok:
                failures.append(rec)
            print(f"[{i:>3}/{len(todo)}] {'ok  ' if ok else 'FAIL'} {row['pid']} "
                  f"{rec['secs']:>6}s  {'' if ok else (rec['reason'] or '')[:70]}", flush=True)

    print(f"\nswept {len(todo)}   failures {len(failures)}   results: {out}")
    for r in failures:
        print(f"  !! {r['pid']}: {r['reason']}\n     {r['theorem_head']}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
