#!/usr/bin/env python3
"""Audit every RECORDED Lean axiom footprint in the repo against the allowlist.

Allowlist, not denylist: since Lean 4.29 native computation emits one auto-generated axiom name
per computation (leanprover/lean4#12216) -- on the pinned 4.31 it is spelled
`<theorem>._native.native_decide.ax_1`, not `Lean.ofReduceBool`. A denylist naming
`ofReduceBool` / `trustCompiler` is therefore blind to native computation on our own toolchain,
and stays blind as the naming changes again. Anything outside the canonical three is a finding.

Read-only. Exits non-zero on any finding, so CI can gate on it. See ADR 0097.
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
ALLOWED = {"propext", "Classical.choice", "Quot.sound"}
REPORT = re.compile(r"'([^']+)'\s+depends on axioms:\s*\[([^\]]*)\]")
SUFFIXES = {".json", ".md", ".lean", ".txt"}

findings: list[tuple[str, str, list[str]]] = []
clean = 0
artifacts: set[str] = set()


def check(where: str, text: str) -> None:
    global clean
    for m in REPORT.finditer(text):
        name, lst = m.group(1), m.group(2)
        extra = {a.strip() for a in lst.split(",") if a.strip()} - ALLOWED
        artifacts.add(where)
        if extra:
            findings.append((where, name, sorted(extra)))
        else:
            clean += 1


def walk(where: str, obj) -> None:
    """Recorded footprints hide inside nested JSON values, not only in flat text."""
    if isinstance(obj, str):
        check(where, obj)
    elif isinstance(obj, dict):
        for v in obj.values():
            walk(where, v)
    elif isinstance(obj, list):
        for v in obj:
            walk(where, v)


def main() -> int:
    for p in ROOT.rglob("*"):
        if ".git" in p.parts or not p.is_file() or p.suffix not in SUFFIXES:
            continue
        raw = p.read_text(encoding="utf-8", errors="replace")
        rel = str(p.relative_to(ROOT))
        if p.suffix == ".json":
            try:
                walk(rel, json.loads(raw))
                continue
            except Exception:
                pass          # not valid JSON -- fall through to the flat-text scan
        check(rel, raw)

    total = clean + len(findings)
    print(f"footprints checked: {total}  clean: {clean}  findings: {len(findings)}"
          f"  artifacts: {len(artifacts)}")
    for where, name, extra in findings:
        print(f"  !! {where}: '{name}' -> {extra}")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
