"""ADR 0066 — factorial/gcd in the faithfulness DSL via bounded definitional encodings.

Pure Z3 (no Docker): the encodings must be EXACT over the boxed range — pinned by comparing
`find_counterexample` against a brute-force Python oracle over the same box — and exact-or-DEFER
outside the encodable shape (compound arguments, over-cap constants, missing bound). The renderer's
lockstep is ⊆ (never MORE than Z3): factorial/gcd stay UNRENDERABLE (no kernel procedure consumes
them yet), which existing behaviour already exhibits for the ADR 0035 shape.
"""
from __future__ import annotations

import itertools
import math

import pytest

from leibniz.backends.smt_z3 import MAX_TABLE_BOUND, PredicateError, Z3Backend, available, compile_pred
from leibniz.dsl_to_lean import RenderError, render_pred

# the core install is stdlib-only; z3 is the `verify` extra — skip cleanly where absent (CI)
pytestmark = pytest.mark.skipif(not available(), reason="z3-solver (verify extra) not installed")

BE = Z3Backend()
BOUND = 24


def _oracle_cx(claim: str, bound: int):
    """Brute-force: does any assignment in the box satisfy `claim`? (The DSL semantics of
    factorial/gcd are Python's math.factorial / math.gcd on the non-negative box.)"""
    import ast
    vs = sorted({n.id for n in ast.walk(ast.parse(claim, mode="eval"))
                 if isinstance(n, ast.Name) and n.id not in ("min", "max", "factorial", "gcd")})
    for pt in itertools.product(range(bound + 1), repeat=len(vs)):
        env = dict(zip(vs, pt), min=min, max=max, factorial=math.factorial, gcd=math.gcd)
        if eval(claim, {"__builtins__": {}}, env):  # noqa: S307 — test oracle over generated claims
            return dict(zip(vs, pt))
    return None


@pytest.mark.parametrize("claim", [
    "factorial(n) == 6",
    "factorial(n) % 2 == 1 and n >= 2",            # UNSAT: n! is even for n ≥ 2
    "factorial(n) == n * factorial(n) and n >= 2",  # UNSAT: would need n == 1
    "factorial(n) > 100 and n <= 4",                # SAT? 4! = 24 → UNSAT; 5! = 120 but n ≤ 4
    "gcd(a, b) == 5 and a == 10",
    "gcd(n, 12) == 5",                              # UNSAT: gcd(n,12) divides 12
    "gcd(a, b) > a and a >= 1",                     # UNSAT: gcd(a,b) ≤ a for a ≥ 1
    "gcd(n, 0) != n",                               # UNSAT: gcd(n,0) = n
    "gcd(a, b) == gcd(b, a) and a + b >= 1 and gcd(a, b) == 0",  # UNSAT: gcd=0 needs a=b=0
    "gcd(a, 18) == 6",                              # SAT: a = 6
])
def test_encodings_agree_with_the_brute_force_oracle(claim):
    got = BE.find_counterexample(claim, BOUND)
    want = _oracle_cx(claim, BOUND)
    assert (got is None) == (want is None), f"{claim}: z3={got} oracle={want}"
    if got is not None:                              # any model must actually satisfy the claim
        env = dict(got, min=min, max=max, factorial=math.factorial, gcd=math.gcd)
        assert eval(claim, {"__builtins__": {}}, env)  # noqa: S307


@pytest.mark.parametrize("bad", [
    "factorial(n + 1) == 2",                        # compound argument
    "factorial(a * b) == 2",
    "gcd(a + 1, b) == 1",
    "gcd(factorial(n), factorial(n)) == 1",         # nested call = compound argument
    "gcd(a, b, 3) == 1",                            # arity
    "factorial(n, 2) == 2",
    f"factorial({MAX_TABLE_BOUND + 1}) == 2",       # over-cap constant
    "sqrt(n) == 2",                                 # not whitelisted
])
def test_unencodable_shapes_defer(bad):
    with pytest.raises(PredicateError):
        compile_pred(bad, {}, BOUND)
    assert BE.find_counterexample(bad, BOUND) is None   # error degrades to no-refutation, never a crash


def test_missing_bound_defers_the_table_but_constants_still_encode():
    with pytest.raises(PredicateError):
        compile_pred("factorial(n) == 6", {}, None)      # bound-less caller → DEFER
    compile_pred("factorial(5) == 120", {}, None)        # constant argument needs no box


def test_gcd_var_var_semantics_on_the_full_table():
    # every cell of the (var, var) table must match math.gcd — decided as UNSAT of the negation
    assert BE.find_counterexample("gcd(a, b) != gcd(b, a)", 16) is None            # symmetry
    assert BE.find_counterexample("gcd(a, a) != a", 16) is None                    # idempotence
    got = BE.find_counterexample("gcd(a, b) == 7 and a == 14 and b != 7 and b != 14", 21)
    assert got is not None and math.gcd(14, got["b"]) == 7


#: Admitted / refused on BOTH sides. `dsl_to_lean`'s header states the invariant this pins: the
#: renderer "admits *exactly* the Z3-admitted grammar and no more".
_LOCKSTEP_IN = ("factorial(n) == 6", "gcd(a, b) == 1", "gcd(n, 6) == 1", "factorial(6) == 720",
                "gcd(12, 18) == 6", "factorial(n) + gcd(a, b) == 7")
_LOCKSTEP_OUT = ("factorial(n + 1) == 6",          # compound argument
                 "factorial(factorial(n)) == 6",   # nested call
                 "gcd(a) == 1", "gcd(a, b, c) == 1",  # wrong arity
                 "gcd(a*a, b) == 1",               # compound argument
                 f"gcd(n, {MAX_TABLE_BOUND + 1}) == 1")   # constant over the table bound


def test_renderer_and_z3_admit_the_same_named_function_fragment():
    """ADR 0070 put the renderer in LOCKSTEP with smt_z3's ADR 0066 table fragment.

    This test previously asserted the opposite — "no kernel procedure consumes factorial/gcd yet
    → the renderer must keep REFUSING them" — and went stale the moment ADR 0070 landed the
    factgcd kernel procedure. That ADR records replacing the conformance suite's `gcd(n, 6) == 1`
    refusal pin, but this sibling pin was missed, so the suite has carried a red test asserting a
    superseded design ever since.

    Pinning lockstep is strictly stronger than the refusal it replaces: it catches the renderer
    drifting in EITHER direction, and admitting more than Z3 is the dangerous one — a claim the
    cheap Z3 refutation never saw would reach the kernel."""
    import z3        # local: this module must import on the stdlib-only core install (CI
                    # runs the BLOCKING invariants job without the verify extra), and the
                    # module-level import broke collection before pytestmark could skip.
    env_vars = ("n", "a", "b", "c")

    def z3_admits(src: str) -> bool:
        try:
            compile_pred(src, {v: z3.Int(v) for v in env_vars}, 16)
            return True
        except Exception:
            return False

    def renderer_admits(src: str) -> bool:
        try:
            render_pred(src)
            return True
        except RenderError:
            return False

    for src in _LOCKSTEP_IN:
        assert z3_admits(src) and renderer_admits(src), f"should be admitted by both: {src}"
    for src in _LOCKSTEP_OUT:
        assert not z3_admits(src) and not renderer_admits(src), f"should be refused by both: {src}"
