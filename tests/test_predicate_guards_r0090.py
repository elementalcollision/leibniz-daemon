"""ADR 0090 — the predicate guard bounds what it admits, not just how big it is.

`MAX_NODES` counts AST nodes. It never bounded the COST of what it admits: `_conv` expands `a**k`
into a literal product of k copies of `a`, and validates `k <= MAX_POW` on each `Pow` node
INDIVIDUALLY, so nesting composes multiplicatively. `((n**8)**8)**8...` costs 3 AST nodes and 5
characters per level and reaches degree 8**L; the shipped cap of 200 admitted ~65 levels.

Measured on the real code path before the fix: L=6 (24 nodes, 35 chars) 0.06 s / 76 MB, L=7
0.49 s / 262 MB, L=8 3.90 s / 1766 MB, and past that the process died on a SIGNAL — uncatchable by
any `except Exception`, and the nightly launchd beat has no KeepAlive. It reached
`SMTVerifier.cheap_refute` (the first gate) and the ADR 0004 gaming spine.

Separately, `ast.parse` raises `MemoryError` on deeply nested source BEFORE any node count exists,
and MemoryError is neither SyntaxError nor ValueError, so it escaped every guard.
"""
from __future__ import annotations

import ast

import pytest

from leibniz import structural
from leibniz.backends.smt_z3 import (
    MAX_EXPANDED,
    MAX_NODES,
    MAX_SRC_CHARS,
    Z3Backend,
    expanded_size,
    guard_source,
)
from leibniz.dsl_to_lean import RenderError, render_pred


def _nest(L: int) -> str:
    return "(" * L + "n" + ")**8" * L + " > 0"


def _guard_ok(src: str) -> bool:
    try:
        guard_source(src)
        return True
    except ValueError:
        return False


def _render_ok(src: str) -> bool:
    try:
        render_pred(src)
        return True
    except RenderError:
        return False


# --- the composed-exponent blowup ---------------------------------------------------------------

def test_nested_powers_are_refused_while_staying_inside_the_node_cap():
    """The point: every one of these is INSIDE `MAX_NODES`. The node cap never saw them."""
    for L in (4, 6, 8, 10, 20):
        src = _nest(L)
        nodes = sum(1 for _ in ast.walk(ast.parse(src, mode="eval")))
        assert nodes <= MAX_NODES, f"L={L} must be inside the node cap for this test to mean anything"
        assert not _guard_ok(src), f"L={L} ({nodes} nodes) must be refused"


def test_shallow_nesting_still_admitted():
    assert _guard_ok(_nest(3))          # expanded size ~1096, costs nothing


def test_real_predicates_are_unaffected():
    """Measured over 545 predicates harvested from this repo: median expanded size 9, max 51.
    MAX_EXPANDED is ~80x that maximum, so the bound cannot bite legitimate work."""
    for src in ("max(a,b)**4 + min(a,b)**4 == a**4 + b**4",              # the repo's largest, esize 51
                "max(a,b)**3 - min(a,b)**3 == (max(a,b) - min(a,b))*(a**2 + a*b + b**2)",
                "((a + b)**5 - a**5 - b**5) % 30 == 0",
                "(a+b)**2 % 4 == 1",
                " or ".join(f"(n % {m} == 0)" for m in range(2, 26))):
        assert _guard_ok(src), src
    assert MAX_EXPANDED >= 4096


def test_expanded_size_saturates_rather_than_computing_the_blowup():
    """The CHECK must not be the DoS. 8**65 must never be evaluated exactly."""
    big = ast.parse(_nest(65), mode="eval").body
    assert expanded_size(big) == MAX_EXPANDED + 1        # saturated, not astronomical


def test_the_two_gates_it_reached_no_longer_explode():
    """`cheap_refute` is the FIRST gate (pipeline.py) and `find_gaming_witness` is the ADR 0004
    faithfulness spine. Both took the hostile predicate straight to Z3."""
    be = Z3Backend()
    for L in (8, 10, 20, 65):
        src = _nest(L)
        assert be.find_counterexample(src, 64) is None
        assert be.find_gaming_witness(statement="not (n >= 0)", negated_claim=src, bound=64) is None


# --- the parse-time guard ------------------------------------------------------------------------

def test_deeply_nested_source_fails_closed_instead_of_raising_memoryerror():
    """Bisected exactly before the fix: 5975 unary minuses parsed and were refused by the node cap;
    5976 raised `MemoryError: Parser stack overflowed` out of BOTH entry points, uncaught.

    The LENGTH cap is what closes this, not the `except MemoryError` clause — mutation-checked:
    removing the clause changes nothing, because no shape within 4000 chars reaches ast.parse's
    limits (3950 unary minuses parse; nested parens raise SyntaxError at 250). The clause stays as
    defence in depth for shapes not enumerated, and this docstring records that it is not
    load-bearing so nobody later mistakes it for the fix."""
    src = "-" * 5976 + "n == 0"
    assert not _guard_ok(src)
    assert Z3Backend().encodable(src) is False
    assert not _render_ok(src)
    assert structural.congruence_signature(src) is None
    assert structural.is_coefficient_degenerate(src) is False


def test_source_length_is_capped_before_parsing():
    assert MAX_SRC_CHARS > 0
    assert not _guard_ok("n == 0 or " * (MAX_SRC_CHARS // 10 + 1) + "n == 1")


# --- lockstep, which is the reason the guard is shared --------------------------------------------

@pytest.mark.parametrize("src", [
    "max(a,b)**4 + min(a,b)**4 == a**4 + b**4",
    _nest(3), _nest(4), _nest(8), _nest(65),
    "-" * 5976 + "n == 0",
    "(a+b)**2 % 4 == 1",
])
def test_z3_and_renderer_admit_exactly_the_same_inputs(src):
    """`dsl_to_lean` and `structural` route through `smt_z3.guard_source` rather than restating the
    caps. `structural` previously carried its own `MAX_NODES = 200  # (matches smt_z3)` — a comment
    asserting a coupling that did not exist. That mattered because both of its consumers fail OPEN
    above the cap (`is_coefficient_degenerate` -> keep content, `congruence_signature` -> stays
    NOVEL), so a silently-lagging copy would quietly disable the ADR 0061 vacuity kill."""
    assert Z3Backend().encodable(src) is _guard_ok(src) is _render_ok(src)


def test_structural_has_no_private_cap():
    """Assert the BINDING, not the text — the module comment quotes the old line on purpose, and a
    grep-based check would pass again the moment someone re-added the constant below the comment."""
    assert not hasattr(structural, "MAX_NODES"), "structural must not define its own cap"
    assert structural.guard_source is guard_source, "must be the same guard object, not a copy"
