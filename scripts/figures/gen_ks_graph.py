"""ADR 0064 — the Kochen–Specker orthogonality graph, drawn FROM THE ARTIFACT DATA.

Parses the 33 rays (Eisenstein-integer triples) and 14 bases out of the audited
``docs/crt/cabello_ks.lean`` and renders the orthogonality graph: 33 vertices on a circle, an edge
for every orthogonal pair under the SAME exact Hermitian form the kernel decided
(``herm(u,v) = Σ econj(uᵢ)·vᵢ`` over ℤ[ω]), with edges inside one of the 14 bases drawn dark. A
consistency check re-derives ``cabello_bases_orth`` in Python (every basis pair orthogonal) so the
figure's arithmetic can never silently diverge from the kernel's. Pure stdlib, deterministic.
"""
from __future__ import annotations

import ast
import math
import re
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent.parent
ARTIFACT = _ROOT / "docs" / "crt" / "cabello_ks.lean"

_INK, _SOFT, _NODE = "#1a1a1a", "#c5bbaa", "#8b2500"


def parse_data() -> tuple[list, list]:
    """(rays, bases) parsed VERBATIM from the audited artifact (Lean literals are Python literals)."""
    text = ARTIFACT.read_text()
    rays = ast.literal_eval(re.search(r"def rays : List \(List Eis\) := (\[.*\])", text).group(1))
    bases = ast.literal_eval(re.search(r"def bases : List \(Nat × Nat × Nat\) := (\[.*\])", text).group(1))
    return rays, bases


def _emul(p, q):                                     # (a+bω)(c+dω) with ω² = −1−ω — the artifact's emul
    return (p[0] * q[0] - p[1] * q[1], p[0] * q[1] + p[1] * q[0] - p[1] * q[1])


def _econj(p):                                       # conj(a+bω) = (a−b) − bω — the artifact's econj
    return (p[0] - p[1], -p[1])


def orthogonal(u, v) -> bool:
    h = (0, 0)
    for a, b in zip(u, v):
        m = _emul(_econj(a), b)
        h = (h[0] + m[0], h[1] + m[1])
    return h == (0, 0)


def ks_graph_figure() -> dict:
    rays, bases = parse_data()
    n = len(rays)
    basis_pairs = set()
    for (i, j, k) in bases:
        for p in ((i, j), (i, k), (j, k)):
            assert orthogonal(rays[p[0]], rays[p[1]]), \
                f"basis pair {p} not orthogonal — figure arithmetic diverges from the kernel"
            basis_pairs.add(tuple(sorted(p)))
    edges = [(i, j) for i in range(n) for j in range(i + 1, n) if orthogonal(rays[i], rays[j])]

    size, r_edge, r_label, cx = 460, 195, 215, 230
    def xy(i, radius):
        th = 2 * math.pi * i / n - math.pi / 2
        return (round(cx + radius * math.cos(th), 1), round(cx + radius * math.sin(th), 1))

    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {size} {size}" width="{size}" '
           f'height="{size}" role="img" aria-label="The Cabello 33-ray orthogonality graph">']
    for i, j in edges:                                # light non-basis edges first, dark basis edges on top
        if tuple(sorted((i, j))) not in basis_pairs:
            (x1, y1), (x2, y2) = xy(i, r_edge), xy(j, r_edge)
            out.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{_SOFT}" stroke-width="0.7"/>')
    for i, j in sorted(basis_pairs):
        (x1, y1), (x2, y2) = xy(i, r_edge), xy(j, r_edge)
        out.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{_INK}" stroke-width="1.6"/>')
    for i in range(n):
        x, y = xy(i, r_edge)
        out.append(f'<circle cx="{x}" cy="{y}" r="4.5" fill="{_NODE}"/>')
        lx, ly = xy(i, r_label)
        out.append(f'<text x="{lx}" y="{ly}" font-size="9" font-family="monospace" fill="{_INK}" '
                   f'text-anchor="middle" dominant-baseline="middle">{i}</text>')
    out.append("</svg>")
    return {
        "svg": "".join(out),
        "caption": (f"The orthogonality graph of the 33 Cabello rays ({len(edges)} orthogonal pairs "
                    f"under the exact Hermitian form over ℤ[ω]); the {len(basis_pairs)} dark edges lie "
                    "inside the 14 orthonormal bases the kernel decided admit no {0,1} coloring."),
        "generated_by": "scripts/figures/gen_ks_graph.py (from docs/crt/cabello_ks.lean)",
    }


if __name__ == "__main__":
    fig = ks_graph_figure()
    print(fig["caption"])
    print(fig["svg"][:120] + "…")
