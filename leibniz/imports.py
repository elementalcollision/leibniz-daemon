"""Mechanical Mathlib import-resolver (ADR 0012).

Autoformalizers often emit *stale* Mathlib module paths (modules move between
Mathlib versions). This validates requested imports against the real module index
(`corpus/mathlib_modules.json`, regenerated per toolchain) and repairs cheaply:
keep valid imports, fuzzy-match a stale path by its final segment(s) to the current
module, drop the unresolvable, and ensure `Mathlib.Tactic` when any Mathlib import
is present. It runs *before* the (costlier) R4.2 LLM repair, which still handles
genuine symbol relocations the index can't fix mechanically.

Pure, stdlib-only, CI-safe. If the index is missing, it passes imports through
unchanged (never makes things worse).
"""
from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path

_DEFAULT_INDEX = Path(__file__).resolve().parent.parent / "corpus" / "mathlib_modules.json"


@lru_cache(maxsize=4)
def _load(path_str: str) -> frozenset[str]:
    try:
        return frozenset(json.loads(Path(path_str).read_text()))
    except (OSError, json.JSONDecodeError):
        return frozenset()


def module_index(path: Path | None = None) -> frozenset[str]:
    return _load(str(path or os.environ.get("LEIBNIZ_MATHLIB_INDEX") or _DEFAULT_INDEX))


def _fuzzy(requested: str, index: frozenset[str], limit: int = 2) -> list[str]:
    """Candidate current modules for a stale path: exact final-segment match first,
    then a last-two-segment suffix match."""
    parts = requested.split(".")
    leaf = parts[-1].lower()
    if not leaf:
        return []
    exact = sorted(m for m in index if m.split(".")[-1].lower() == leaf)
    if exact:
        return exact[:limit]
    if len(parts) >= 2:
        tail = ".".join(parts[-2:]).lower()
        return sorted(m for m in index if m.lower().endswith(tail))[:limit]
    return []


def resolve_imports(requested: list[str], index: frozenset[str] | None = None) -> list[str]:
    """Return a repaired import list (see module docstring)."""
    idx = index if index is not None else module_index()
    if not idx:
        return list(requested)  # no index available -> do no harm
    out: list[str] = []
    seen: set[str] = set()
    any_mathlib = any(r.strip() == "Mathlib" or r.strip().startswith("Mathlib.") for r in requested)
    for raw in requested:
        r = raw.strip()
        if not r:
            continue
        if r in idx:
            candidates = [r]
        else:
            candidates = _fuzzy(r, idx)  # stale/invalid -> fuzzy repair (or drop)
        for c in candidates:
            if c not in seen:
                out.append(c)
                seen.add(c)
    if any_mathlib and "Mathlib.Tactic" in idx and "Mathlib.Tactic" not in seen:
        out.append("Mathlib.Tactic")
    return out
