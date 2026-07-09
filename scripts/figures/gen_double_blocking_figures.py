"""ADR 0064 — figures for the double-blocking-sets law, drawn FROM THE ARTIFACT DATA.

Parses ``B13``/``lines13`` and ``B19``/``lines19`` out of the audited ``docs/crt/double_blocking.lean``
and draws each 3q−1 double blocking set in PG(2,q): the affine q×q grid ((1:a:b) ↦ col a, row b) with
a strip above it for the line at infinity ((0:1:c) ↦ position c, and (0:0:1) at its end). A
consistency check re-derives ``doubleBlocking`` in Python (every one of the q²+q+1 lines meets B in
≥ 2 points — the twin of the kernel-decided theorems) before drawing. Pure stdlib, deterministic.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent.parent
ARTIFACT = _ROOT / "docs" / "crt" / "double_blocking.lean"

_INK, _GRID, _FILL, _INF = "#1a1a1a", "#c5bbaa", "#8b2500", "#1f4e79"


def parse(name: str):
    """The named point list, VERBATIM from the audited artifact."""
    m = re.search(rf"def {name} : List Pt := (\[.*\])", ARTIFACT.read_text())
    return ast.literal_eval(m.group(1))


def assert_double_blocking(q: int, B, lines) -> None:
    """Python twin of the kernel-decided ``doubleBlocking``: every line meets B in ≥ 2 points."""
    assert len(lines) == q * q + q + 1
    for L in lines:
        hits = sum(1 for P in B if (L[0] * P[0] + L[1] * P[1] + L[2] * P[2]) % q == 0)
        assert hits >= 2, f"line {L} meets B in {hits} < 2 points — diverges from the kernel"


def _pg2_svg(q: int, B, title: str) -> str:
    cell = 24 if q <= 13 else 18
    pad, gap = 12, 10
    w = q * cell + 2 * pad + cell            # +cell for the (0:0:1) box at the strip's end
    h = q * cell + 2 * pad + cell + gap      # strip row + gap + affine grid
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" '
           f'role="img" aria-label="{title}">']
    Bset = set(B)
    # line at infinity: (0:1:c) at position c, then (0:0:1)
    for c in range(q):
        if (0, 1, c) in Bset:
            out.append(f'<rect x="{pad + c * cell + 2}" y="{pad + 2}" width="{cell - 4}" '
                       f'height="{cell - 4}" rx="4" fill="{_INF}"/>')
        out.append(f'<rect x="{pad + c * cell}" y="{pad}" width="{cell}" height="{cell}" '
                   f'fill="none" stroke="{_GRID}" stroke-width="1"/>')
    if (0, 0, 1) in Bset:
        out.append(f'<rect x="{pad + q * cell + 2}" y="{pad + 2}" width="{cell - 4}" '
                   f'height="{cell - 4}" rx="4" fill="{_INF}"/>')
    out.append(f'<rect x="{pad + q * cell}" y="{pad}" width="{cell}" height="{cell}" '
               f'fill="none" stroke="{_INK}" stroke-width="1.5"/>')
    # affine grid: (1:a:b) ↦ col a, row b
    top = pad + cell + gap
    for (x, a, b) in sorted(Bset):
        if x == 1:
            out.append(f'<rect x="{pad + a * cell + 2}" y="{top + b * cell + 2}" width="{cell - 4}" '
                       f'height="{cell - 4}" rx="4" fill="{_FILL}"/>')
    for i in range(q + 1):
        y = top + i * cell
        out.append(f'<line x1="{pad}" y1="{y}" x2="{pad + q * cell}" y2="{y}" stroke="{_GRID}" stroke-width="1"/>')
        x = pad + i * cell
        out.append(f'<line x1="{x}" y1="{top}" x2="{x}" y2="{top + q * cell}" stroke="{_GRID}" stroke-width="1"/>')
    out.append("</svg>")
    return "".join(out)


def _figure(q: int) -> dict:
    B, lines = parse(f"B{q}"), parse(f"lines{q}")
    assert_double_blocking(q, B, lines)
    assert len(B) == 3 * q - 1
    return {
        "svg": _pg2_svg(q, B, f"The 3q−1 = {3 * q - 1}-point double blocking set in PG(2,{q})"),
        "caption": (f"The minimal double blocking set of size 3q−1 = {3 * q - 1} in PG(2,{q}): affine "
                    f"points (1:a:b) on the {q}×{q} grid (rust), points of the line at infinity "
                    "(0:1:c) and (0:0:1) on the strip above (blue). The kernel decided every one of "
                    f"the {q * q + q + 1} lines meets it at least twice, and that it is minimal."),
        "generated_by": "scripts/figures/gen_double_blocking_figures.py (from docs/crt/double_blocking.lean)",
    }


def db13_figure() -> dict:
    return _figure(13)


def db19_figure() -> dict:
    return _figure(19)


if __name__ == "__main__":
    for fig in (db13_figure(), db19_figure()):
        print(fig["caption"][:80], "…")
        print(fig["svg"][:100], "…\n")
