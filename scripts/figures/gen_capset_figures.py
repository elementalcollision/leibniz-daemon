"""ADR 0064 — deterministic SVG figures for the cap-set law, drawn FROM THE ARTIFACT DATA.

Parses ``set81`` (20 vectors in (F₃)⁴) and ``eq64`` (9 vectors in (F₂)⁶) out of the audited
``docs/crt/capset_subgroups.lean`` — the exact lists the kernel decided over — and renders them as the
classic board pictures: AG(4,3) as the 9×9 SET board (v = (a,b,c,d) ↦ row 3a+c, col 3b+d) and AG(6,2)
as an 8×8 grid (v = (a,b,c,d,e,f) ↦ row 4a+2b+c, col 4d+2e+f). Pure stdlib, no randomness, no
timestamps — regenerating is byte-identical (a figure is a RENDERING of kernel-checked data, never
evidence). Runnable: prints both SVGs.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent.parent
ARTIFACT = _ROOT / "docs" / "crt" / "capset_subgroups.lean"

_INK, _FILL, _GRID = "#1a1a1a", "#8b2500", "#b9b0a2"


def parse_vectors(name: str) -> list[list[int]]:
    """The named vector list, parsed VERBATIM from the audited artifact (Lean's list literal is a
    valid Python literal)."""
    m = re.search(rf"def {name} : List \(List Int\) := (\[.*\])", ARTIFACT.read_text())
    return ast.literal_eval(m.group(1))


def _grid_svg(cells: set[tuple[int, int]], n: int, block: int, title: str) -> str:
    """An n×n grid with the given (row, col) cells filled; heavier rules every ``block`` cells."""
    cell, pad = 36, 12
    size = n * cell + 2 * pad
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {size} {size}" '
           f'width="{size}" height="{size}" role="img" aria-label="{title}">']
    for r, c in sorted(cells):
        out.append(f'<rect x="{pad + c * cell + 2}" y="{pad + r * cell + 2}" '
                   f'width="{cell - 4}" height="{cell - 4}" rx="5" fill="{_FILL}"/>')
    for i in range(n + 1):
        w = 2 if i % block == 0 else 1
        color = _INK if i % block == 0 else _GRID
        p = pad + i * cell
        out.append(f'<line x1="{pad}" y1="{p}" x2="{size - pad}" y2="{p}" stroke="{color}" stroke-width="{w}"/>')
        out.append(f'<line x1="{p}" y1="{pad}" x2="{p}" y2="{size - pad}" stroke="{color}" stroke-width="{w}"/>')
    out.append("</svg>")
    return "".join(out)


def set81_figure() -> dict:
    vecs = parse_vectors("set81")
    cells = {(3 * v[0] + v[2], 3 * v[1] + v[3]) for v in vecs}
    assert len(cells) == len(vecs)                    # the mapping is injective on the witness
    return {
        "svg": _grid_svg(cells, 9, 3, "The 20-point SET cap in AG(4,3)"),
        "caption": ("The 20 nonzero fourth powers of GF(81) as points of AG(4,3), drawn on the 9×9 "
                    "SET board (v=(a,b,c,d) ↦ row 3a+c, col 3b+d). The kernel decided no three "
                    "distinct points sum to 0 (mod 3) — a maximal SET cap."),
        "generated_by": "scripts/figures/gen_capset_figures.py (from docs/crt/capset_subgroups.lean)",
    }


def eq64_figure() -> dict:
    vecs = parse_vectors("eq64")
    cells = {(4 * v[0] + 2 * v[1] + v[2], 4 * v[3] + 2 * v[4] + v[5]) for v in vecs}
    assert len(cells) == len(vecs)
    return {
        "svg": _grid_svg(cells, 8, 2, "The 9-point EvenQuads cap in AG(6,2)"),
        "caption": ("The 9 nonzero seventh powers of GF(64) as points of AG(6,2), drawn on an 8×8 "
                    "board (v=(a,…,f) ↦ row 4a+2b+c, col 4d+2e+f). The kernel decided no four "
                    "distinct points sum to 0 (mod 2) — a maximal EvenQuads cap."),
        "generated_by": "scripts/figures/gen_capset_figures.py (from docs/crt/capset_subgroups.lean)",
    }


if __name__ == "__main__":
    for fig in (set81_figure(), eq64_figure()):
        print(fig["caption"])
        print(fig["svg"][:120] + "…\n")
