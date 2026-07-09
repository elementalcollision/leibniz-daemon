"""ADR 0064 — figures for the Markoff-cage law, drawn FROM THE ARTIFACT DATA.

Parses the certified prime lists out of the audited ``docs/crt/markoff_cage.lean`` and mirrors its
exact matrix arithmetic (``Amat``/``mmul``/``mpow``/``matOrder``/``pisano`` over Nat 4-tuples mod p).
Before drawing, each generator asserts the Python twin of the kernel-decided facts — ``posCheck``
(A^{p+1} = I and A^{(p+1)/2} ≠ I) for every certified prime, ``matOrder 7 = 8`` with
``pisano 7 = 16 = 2·8`` — so the figures can never diverge from the kernel.

  • orbit7_figure    — the rotation orbit at (1,1,1) mod 7: the eight powers A¹..A⁸ = I on a circle,
                       each node showing the actual 2×2 matrix (ord = π(7)/2 = 8 exactly, since
                       2^{ν₂(8)} = 8 divides ord divides 8).
  • mersenne_figure  — the 2-adic staircase for the Mersenne primes 127, 524287, 2³¹−1: the
                       repeated-squaring chain A^(2^k), with the certified endpoints marked
                       (A^{(p+1)/2} ≠ I open, A^{p+1} = I filled).

Pure stdlib, deterministic.
"""
from __future__ import annotations

import ast
import math
import re
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent.parent
ARTIFACT = _ROOT / "docs" / "crt" / "markoff_cage.lean"

_INK, _GRID, _FILL, _OPEN = "#1a1a1a", "#c5bbaa", "#8b2500", "#1f4e79"


def parse_primes(theorem: str) -> list[int]:
    """The prime list inside the named theorem's ``allPos [...]``, VERBATIM from the artifact."""
    m = re.search(rf"theorem {theorem} : allPos (\[[0-9, ]*\]) = true", ARTIFACT.read_text())
    return ast.literal_eval(m.group(1))


# --- the artifact's arithmetic, mirrored exactly (Nat 4-tuples mod p) -------------------------------

def amat(p: int) -> tuple:
    return (0, 1, p - 1, 3 % p)


IDEN = (1, 0, 0, 1)


def mmul(p: int, X: tuple, Y: tuple) -> tuple:
    a, b, c, d = X
    e, f, g, h = Y
    return ((a * e + b * g) % p, (a * f + b * h) % p, (c * e + d * g) % p, (c * f + d * h) % p)


def mpow(p: int, X: tuple, e: int) -> tuple:
    acc, base = IDEN, X
    while e > 0:
        if e % 2 == 1:
            acc = mmul(p, acc, base)
        base = mmul(p, base, base)
        e //= 2
    return acc


def pos_check(p: int) -> bool:
    """Twin of the kernel-decided ``posCheck``."""
    return (p % 5 in (2, 3)) and mpow(p, amat(p), p + 1) == IDEN and mpow(p, amat(p), (p + 1) // 2) != IDEN


def mat_order(p: int) -> int:
    cur, d = amat(p), 1
    while cur != IDEN:
        cur, d = mmul(p, cur, amat(p)), d + 1
    return d


def pisano(p: int) -> int:
    a, b, n = 0, 1, 0
    while True:
        a, b, n = b, (a + b) % p, n + 1
        if a == 0 and b == 1:
            return n


def orbit7_figure() -> dict:
    assert 7 in parse_primes("markoff_div_small")
    assert pos_check(7), "posCheck(7) fails in Python — diverges from the kernel"
    assert mat_order(7) == 8 and pisano(7) == 16, "matOrder/pisano twin diverges from the kernel"
    powers = [mpow(7, amat(7), k) for k in range(1, 9)]
    assert powers[-1] == IDEN
    size, r, cx = 430, 165, 215
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {size} {size}" width="{size}" '
           f'height="{size}" role="img" aria-label="The order-8 rotation orbit at (1,1,1) mod 7">']
    out.append(f'<circle cx="{cx}" cy="{cx}" r="{r}" fill="none" stroke="{_GRID}" stroke-width="1.4"/>')
    for k, M in enumerate(powers, start=1):
        th = 2 * math.pi * (k - 1) / 8 - math.pi / 2
        x, y = round(cx + r * math.cos(th), 1), round(cx + r * math.sin(th), 1)
        fill = _INK if M == IDEN else _FILL
        out.append(f'<rect x="{x - 30}" y="{y - 24}" width="60" height="48" rx="7" fill="#faf6ee" '
                   f'stroke="{fill}" stroke-width="1.6"/>')
        out.append(f'<text x="{x}" y="{y - 12}" font-size="10" font-family="monospace" fill="{_INK}" '
                   f'text-anchor="middle">A^{k}{" = I" if M == IDEN else ""}</text>')
        out.append(f'<text x="{x}" y="{y + 3}" font-size="11" font-family="monospace" fill="{fill}" '
                   f'text-anchor="middle">{M[0]} {M[1]}</text>')
        out.append(f'<text x="{x}" y="{y + 17}" font-size="11" font-family="monospace" fill="{fill}" '
                   f'text-anchor="middle">{M[2]} {M[3]}</text>')
    out.append("</svg>")
    return {
        "svg": "".join(out),
        "caption": ("The rotation at the Markoff special point (1,1,1) mod 7, as the powers of the "
                    "companion matrix A = [[0,1],[−1,3]] over F₇: the orbit closes after exactly "
                    "8 = (p+1) steps (A⁸ = I, A⁴ ≠ I — the kernel-decided certificate — and "
                    "π(7) = 16 = 2·ord, the kernel-decided Pisano identity)."),
        "generated_by": "scripts/figures/gen_markoff_figures.py (from docs/crt/markoff_cage.lean)",
    }


def mersenne_figure() -> dict:
    primes = parse_primes("markoff_div_mersenne")
    assert primes == [127, 524287, 2147483647]
    for p in primes:
        assert pos_check(p), f"posCheck({p}) fails in Python — diverges from the kernel"
    pad, row_h, cell = 14, 64, 11
    n_max = max((p + 1).bit_length() - 1 for p in primes)
    w = pad * 2 + 150 + (n_max + 1) * cell + 40
    h = pad * 2 + row_h * len(primes)
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" '
           f'role="img" aria-label="The Mersenne 2-adic staircase of rotation orders">']
    for i, p in enumerate(primes):
        n = (p + 1).bit_length() - 1                     # p + 1 = 2^n
        y = pad + row_h * i + row_h // 2
        x0 = pad + 150
        out.append(f'<text x="{pad}" y="{y - 8}" font-size="11" font-family="monospace" fill="{_INK}">'
                   f'p = 2^{n} − 1 = {p}</text>')
        out.append(f'<text x="{pad}" y="{y + 10}" font-size="10" font-family="monospace" fill="{_FILL}">'
                   f'ord = 2^{n} = {p + 1}</text>')
        out.append(f'<line x1="{x0}" y1="{y}" x2="{x0 + n * cell}" y2="{y}" stroke="{_GRID}" '
                   f'stroke-width="1.2"/>')
        for k in range(n + 1):                           # node k = A^(2^k), the squaring chain
            x = x0 + k * cell
            if k == n:                                   # A^{p+1} = I — kernel-decided
                out.append(f'<circle cx="{x}" cy="{y}" r="5" fill="{_INK}"/>')
            elif k == n - 1:                             # A^{(p+1)/2} ≠ I — kernel-decided
                out.append(f'<circle cx="{x}" cy="{y}" r="5" fill="none" stroke="{_OPEN}" stroke-width="2"/>')
            else:
                out.append(f'<circle cx="{x}" cy="{y}" r="3" fill="{_GRID}"/>')
        out.append(f'<text x="{x0 + n * cell + 10}" y="{y + 4}" font-size="10" font-family="monospace" '
                   f'fill="{_INK}">= I</text>')
    out.append("</svg>")
    return {
        "svg": "".join(out),
        "caption": ("The 2-adic staircase for the Mersenne primes 127, 524287 and 2³¹−1: each row is "
                    "the repeated-squaring chain A^(2^k) mod p. The kernel decided A^{p+1} = I (filled "
                    "node) and A^{(p+1)/2} ≠ I (open node), so with p+1 = 2ⁿ the rotation order at "
                    "(1,1,1) is exactly 2ⁿ = p+1."),
        "generated_by": "scripts/figures/gen_markoff_figures.py (from docs/crt/markoff_cage.lean)",
    }


if __name__ == "__main__":
    for fig in (orbit7_figure(), mersenne_figure()):
        print(fig["caption"][:80], "…")
        print(fig["svg"][:100], "…\n")
