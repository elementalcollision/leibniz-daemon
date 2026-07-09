"""ADR 0064 — figures for the Steiner-systems law, drawn FROM THE ARTIFACT DATA.

Parses ``mods8``/``blocks8`` (ℤ₃×ℤ₃×ℤ₅×ℤ₅, 4 base blocks of 8) and ``mods9``/``blocks9`` (ℤ₁₇×ℤ₁₇,
4 base blocks of 9) out of the audited ``docs/crt/steiner_designs.lean`` and draws each difference
family on its group grid — one color per base block; cells shared by several blocks (the common
origin) in ink. A consistency check re-derives ``isDiffFamily`` in Python (all within-block
differences nonzero, pairwise distinct, and exactly v−1 of them — the twin of the kernel-decided
theorems) before drawing. Pure stdlib, deterministic.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent.parent
ARTIFACT = _ROOT / "docs" / "crt" / "steiner_designs.lean"

_INK, _GRID = "#1a1a1a", "#c5bbaa"
_BLOCK_COLORS = ["#8b2500", "#1f4e79", "#3d6b21", "#6b3fa0"]


def parse(name: str):
    """The named definition's list literal, VERBATIM from the audited artifact."""
    m = re.search(rf"def {name} : [^=]+ := (\[.*\])", ARTIFACT.read_text())
    return ast.literal_eval(m.group(1))


def assert_diff_family(mods: list[int], blocks: list[list[list[int]]]) -> int:
    """Python twin of the kernel-decided ``isDiffFamily``: the within-block differences are all
    nonzero, pairwise distinct, and number exactly v−1. Returns v−1."""
    diffs = []
    for blk in blocks:
        for a in blk:
            for b in blk:
                if a != b:
                    diffs.append(tuple((x - y) % m for m, x, y in zip(mods, a, b)))
    v = 1
    for m in mods:
        v *= m
    assert all(any(x != 0 for x in d) for d in diffs), "a zero difference — diverges from the kernel"
    assert len(diffs) == len(set(diffs)) == v - 1, "differences not distinct/complete — diverges from the kernel"
    return v - 1


def _family_svg(blocks, rowcol, n_rows: int, n_cols: int, title: str) -> str:
    cell, pad = 24, 12
    w, h = n_cols * cell + 2 * pad, n_rows * cell + 2 * pad
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" '
           f'role="img" aria-label="{title}">']
    owners: dict[tuple[int, int], list[int]] = {}
    for bi, blk in enumerate(blocks):
        for pt in blk:
            owners.setdefault(rowcol(pt), []).append(bi)
    for (r, c), bs in sorted(owners.items()):
        fill = _INK if len(bs) > 1 else _BLOCK_COLORS[bs[0]]
        out.append(f'<rect x="{pad + c * cell + 2}" y="{pad + r * cell + 2}" '
                   f'width="{cell - 4}" height="{cell - 4}" rx="4" fill="{fill}"/>')
    for i in range(n_rows + 1):
        y = pad + i * cell
        out.append(f'<line x1="{pad}" y1="{y}" x2="{w - pad}" y2="{y}" stroke="{_GRID}" stroke-width="1"/>')
    for i in range(n_cols + 1):
        x = pad + i * cell
        out.append(f'<line x1="{x}" y1="{pad}" x2="{x}" y2="{h - pad}" stroke="{_GRID}" stroke-width="1"/>')
    out.append("</svg>")
    return "".join(out)


def s8_225_figure() -> dict:
    mods, blocks = parse("mods8"), parse("blocks8")
    assert_diff_family(mods, blocks)
    fig = _family_svg(blocks, lambda p: (5 * p[0] + p[2], 5 * p[1] + p[3]), 15, 15,
                      "The S(2,8,225) difference family in Z3×Z3×Z5×Z5")
    return {
        "svg": fig,
        "caption": ("The four base blocks of the S(2,8,225) difference family in ℤ₃×ℤ₃×ℤ₅×ℤ₅, one "
                    "color per block on a 15×15 grid ((a,b,c,d) ↦ row 5a+c, col 5b+d); the shared "
                    "origin in ink. The kernel decided their 224 within-block differences are exactly "
                    "the nonzero group elements, once each — so the family develops to a Steiner "
                    "system S(2,8,225)."),
        "generated_by": "scripts/figures/gen_steiner_figures.py (from docs/crt/steiner_designs.lean)",
    }


def s9_289_figure() -> dict:
    mods, blocks = parse("mods9"), parse("blocks9")
    assert_diff_family(mods, blocks)
    fig = _family_svg(blocks, lambda p: (p[0], p[1]), 17, 17,
                      "The S(2,9,289) difference family in Z17×Z17")
    return {
        "svg": fig,
        "caption": ("The four base blocks of the S(2,9,289) difference family in ℤ₁₇×ℤ₁₇, one color "
                    "per block on the 17×17 grid; the shared origin in ink. The kernel decided their "
                    "288 within-block differences are exactly the nonzero group elements, once each — "
                    "so the family develops to a Steiner system S(2,9,289)."),
        "generated_by": "scripts/figures/gen_steiner_figures.py (from docs/crt/steiner_designs.lean)",
    }


if __name__ == "__main__":
    for fig in (s8_225_figure(), s9_289_figure()):
        print(fig["caption"][:80], "…")
        print(fig["svg"][:100], "…\n")
