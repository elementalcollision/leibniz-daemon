"""ADR 0056 Track A — the DSL→Lean renderer semantics-conformance suite.

This is the artifact the ADR 0056 review said must exist before the renderer can be trusted: a
mis-encoding renderer passes any string-identity check while both strings denote the wrong
proposition, so *only* a conformance suite catches it.

The load-bearing test **actually parses and evaluates the Lean string ``render_pred`` emits** (via an
independent evaluator :func:`eval_lean`) and compares its value to the DSL/Z3 meaning over a grid
**including negatives**. This is the fix for the increment-1 re-review's critical finding: the first
version re-evaluated the DSL AST with the *same* Euclidean functions on both sides and never looked at
the emitted string, so a garbage renderer would have passed. Now the emitted operators, operands,
structure, and parenthesisation are all exercised: a truncating ``%``/``/`` (or ``Nat.sub`` monus, a
swapped operand, a dropped term) diverges from the DSL meaning on the grid — or fails to parse — and
the test fails.

Two independent anchors keep the evaluator honest:
- the DSL/Z3 meaning is modelled by Python ``%``/``//`` which, for the DSL's positive constant divisor,
  ARE Euclidean (non-negative remainder, floor quotient) — exactly Z3's integer ``mod``/``div``;
- ``eval_lean`` interprets ``Int.emod``/``Int.ediv`` as Euclidean — an audited fact pinned to
  hand-verified kernel values (``Int.emod (-7) 2 = 1``, ``Int.ediv (-7) 2 = -4``) and, with
  ``LEIBNIZ_LEAN_E2E=1``, to the real Lean 4 kernel.
"""
from __future__ import annotations

import ast
import os
import re

import pytest

from leibniz import dsl_to_lean as d2l


# --- An INDEPENDENT evaluator of the emitted Lean string ------------------------------------------
# The renderer emits a small, fully-parenthesised Lean subset. This evaluator parses that exact subset
# and computes its value under an independent Lean-semantics reading of each operator — so it genuinely
# tests render_pred's OUTPUT, not the DSL AST. Its integer-op semantics (Int.emod/Int.ediv Euclidean,
# real subtraction) are the audited meaning of the Lean operators, pinned below to kernel values.

_TOKEN_RE = re.compile(r"Int\.emod|Int\.ediv|[A-Za-z_][A-Za-z0-9_]*|\d+|≤|≥|≠|∧|∨|¬|↔|ℕ|ℤ|[()+\-*^<>=:]")


class LeanParseError(AssertionError):
    """The emitted string is not in the renderer's expected Lean subset (a renderer defect)."""


def eval_lean(src: str, asn: dict):
    """Evaluate a rendered Lean predicate/term string over an assignment. Euclidean Int.emod/Int.ediv,
    real ℤ subtraction. Raises :class:`LeanParseError` on anything outside the emitted subset — so a
    renderer that emits truncating ``%``/``/``, ``Nat.sub``, or malformed output cannot silently pass."""
    toks = _TOKEN_RE.findall(src)
    pos = [0]

    def peek():
        return toks[pos[0]] if pos[0] < len(toks) else None

    def take(expect=None):
        if pos[0] >= len(toks):
            raise LeanParseError(f"unexpected end of input in {src!r}")
        tok = toks[pos[0]]
        if expect is not None and tok != expect:
            raise LeanParseError(f"expected {expect!r} got {tok!r} in {src!r}")
        pos[0] += 1
        return tok

    def node():
        tok = peek()
        if tok == "(":
            take("(")
            v = paren_body()
            take(")")
            return v
        if tok is not None and tok.isdigit():
            return int(take())
        # a bare integer VARIABLE (a callee like `min` never appears un-parenthesised)
        name = take()
        if name in asn:
            return asn[name]
        raise LeanParseError(f"unbound/unexpected token {name!r} in {src!r}")

    def paren_body():
        tok = peek()
        if tok in ("Int.emod", "Int.ediv"):
            take()
            a, b = node(), node()
            return (a % b) if tok == "Int.emod" else (a // b)   # Euclidean for the positive divisor
        if tok in ("min", "max"):
            take()
            a, b = node(), node()
            return min(a, b) if tok == "min" else max(a, b)
        if tok == "¬":
            take()
            return not node()
        if tok == "-":                                          # unary minus: (-x)
            take()
            return -node()
        left = node()
        op = peek()
        if op in ("+", "-", "*"):
            take()
            right = node()
            return left + right if op == "+" else left - right if op == "-" else left * right
        if op == "^":
            take()
            take("(")
            k = int(take())
            take(":")
            take("ℕ")
            take(")")
            return left ** k
        if op in ("<", "≤", ">", "≥", "=", "≠"):
            take()
            right = node()
            return {"<": left < right, "≤": left <= right, ">": left > right,
                    "≥": left >= right, "=": left == right, "≠": left != right}[op]
        if op in ("∧", "∨"):
            vals = [left]
            while peek() == op:
                take()
                vals.append(node())
            return all(vals) if op == "∧" else any(vals)
        if op == "↔":                                          # biconditional = boolean equality
            take()
            return left == node()
        return left                                            # a redundantly-parenthesised value

    v = node()
    if pos[0] != len(toks):
        raise LeanParseError(f"trailing tokens {toks[pos[0]:]} in {src!r}")
    return v


def test_eval_lean_is_pinned_to_hand_verified_lean_values():
    """The evaluator's integer-op semantics equal what the Lean kernel computes (Euclidean)."""
    assert eval_lean("(Int.emod a 2)", {"a": -7}) == 1             # Int.emod: non-negative
    assert eval_lean("(Int.ediv a 2)", {"a": -7}) == -4            # Int.ediv: floor
    assert eval_lean("((a - b) * a)", {"a": 2, "b": 5}) == -6      # real ℤ subtraction, not monus
    assert eval_lean("(a ^ (3 : ℕ))", {"a": -2}) == -8
    assert eval_lean("((a < b) ∧ (b < a))", {"a": 1, "b": 2}) is False
    assert d2l.MOD_OP == "Int.emod" and d2l.DIV_OP == "Int.ediv"


# --- The DSL/Z3 ground truth (Python %/// are Euclidean for the positive constant divisor) ---------

def _dsl_truth(pred: str, asn: dict):
    tree = ast.parse(pred.replace("^", "**"), mode="eval").body
    return _eval_dsl(tree, asn)


def _eval_dsl(node: ast.AST, asn: dict):
    if isinstance(node, ast.BoolOp):
        vals = [_eval_dsl(v, asn) for v in node.values]
        return all(vals) if isinstance(node.op, ast.And) else any(vals)
    if isinstance(node, ast.UnaryOp):
        return (not _eval_dsl(node.operand, asn)) if isinstance(node.op, ast.Not) else -_eval_dsl(node.operand, asn)
    if isinstance(node, ast.BinOp):
        a, b, op = _eval_dsl(node.left, asn), _eval_dsl(node.right, asn), node.op
        if isinstance(op, ast.Add):
            return a + b
        if isinstance(op, ast.Sub):
            return a - b
        if isinstance(op, ast.Mult):
            return a * b
        if isinstance(op, ast.Pow):
            return a ** b
        if isinstance(op, (ast.Div, ast.FloorDiv)):
            return a // b       # floor == Euclidean for b>0 (matches Z3)
        if isinstance(op, ast.Mod):
            return a % b        # non-negative == Euclidean for b>0 (matches Z3)
    if isinstance(node, ast.Compare):
        left, ok = _eval_dsl(node.left, asn), True
        for op, comp in zip(node.ops, node.comparators):
            right = _eval_dsl(comp, asn)
            ok = ok and {ast.Lt: left < right, ast.LtE: left <= right, ast.Gt: left > right,
                         ast.GtE: left >= right, ast.Eq: left == right, ast.NotEq: left != right}[type(op)]
            left = right
        return ok
    if isinstance(node, ast.Call):
        args = [_eval_dsl(a, asn) for a in node.args]
        return min(args) if node.func.id == "min" else max(args)
    if isinstance(node, ast.Name):
        return asn[node.id]
    if isinstance(node, ast.Constant):
        return node.value
    raise AssertionError(f"unexpected DSL node {type(node).__name__}")


def _grid(vars_, lo=-8, hi=8):
    if not vars_:
        yield {}
        return
    head, *rest = vars_
    for val in range(lo, hi + 1):
        for tail in _grid(rest, lo, hi):
            yield {head: val, **tail}


CONFORMANCE_PREDS = [
    "(a*a + b*b) % 4 == 3",
    "(a*a + a*b + b*b) % 3 != 2",
    "(a - b) % 5 == 2",                 # negative intermediate → Euclidean mod vs truncating
    "(a - b) % 5 == 0 or (a - b) % 5 == 4",
    "(-a) % 7 == 3",                     # unary minus
    "(a - b) / 4 == 1",                  # negative intermediate → Euclidean div vs truncating
    "min(a - b, b) % 3 == 0",            # composition: sub under min under mod
    "max(a*a - b, 0) % 6 != 5",
    "(a*a*a - a) % 6 == 0",              # a^3 - a  (cubic, negative-capable)
    "((a - b) % 6) % 4 == 1",            # nested mod
    "n*n % 4 == 0 or n*n % 4 == 1",      # single-var
    "0 <= a - b and (a - b) % 3 == 1",   # comparison chaining + subtraction
    "(a - b)^2 % 4 == 0 or (a - b)^2 % 4 == 1",   # power of a negative-capable base
    "(a % 2 == 0) == (b % 2 == 0)",      # biconditional (`(P) == (Q)` between booleans) → ↔
    "(a*a % 5 == 1) == ((a % 5 == 1) or (a % 5 == 4))",   # bicond with a disjunction on one side
    "(a % 2 == 0) != (b % 2 == 0)",      # xor: `(P) != (Q)` → ¬ (P ↔ Q)
    "((a - b) % 3 == 0) == (a % 3 == b % 3)",   # bicond over negative-capable subtraction
    # the renderer's ↔ branch is reachable (via claim_domain/established_domain, which are NOT
    # classifier-gated) for non-modular-atom operands — pin those render shapes too (review #4):
    "(a < b) == (a + b < 5)",            # ↔ of INEQUALITIES
    "((a % 2 == 0) and (b % 2 == 0)) == (c % 2 == 0)",   # ↔ of an and-tree
    "((a % 2 == 0) == (b % 2 == 0)) == (c % 2 == 0)",    # NESTED ↔
    "(0 <= a - b) != (b < a)",           # ¬↔ over inequalities + subtraction
]


@pytest.mark.parametrize("pred", CONFORMANCE_PREDS)
def test_EMITTED_lean_denotes_the_dsl_function_over_negatives(pred):
    """The load-bearing conformance test: parse and evaluate render_pred's EMITTED string, and require
    it to equal the DSL/Z3 meaning at every grid point (including negatives). A truncating op, a monus,
    a swapped operand, or malformed output diverges or fails to parse → this fails."""
    lean = d2l.render_pred(pred)
    tree = ast.parse(pred.replace("^", "**"), mode="eval").body
    vars_ = sorted({n.id for n in ast.walk(tree)
                    if isinstance(n, ast.Name) and not _is_callee(n, tree)})
    for asn in _grid(vars_):
        got = eval_lean(lean, asn)
        want = _dsl_truth(pred, asn)
        assert got == want, f"{pred} @ {asn}: emitted-lean={got} dsl={want}  ({lean})"


def _is_callee(name_node, tree):
    return any(isinstance(c, ast.Call) and c.func is name_node for c in ast.walk(tree))


def test_the_conformance_test_has_teeth():
    """Prove the differential is not tautological: a WRONG emission (truncating mod, or a swapped
    operand) is caught by eval_lean vs the DSL truth on the negative grid."""
    # 1. Had the renderer emitted truncating `%` semantics, eval_lean would refuse to parse it.
    with pytest.raises(LeanParseError):
        eval_lean("((a - b) % 5)", {"a": 1, "b": 4})            # bare `%` is not in the emitted subset
    # 2. A parseable-but-wrong emission (a+b where the DSL means a-b) diverges from the DSL truth.
    wrong = eval_lean("((Int.emod (a + b) 5) = 2)", {"a": 1, "b": 4})   # (1+5)%5? no: (1+4)%5=0 ≠ 2
    right = _dsl_truth("(a - b) % 5 == 2", {"a": 1, "b": 4})            # (1-4)%5 = 2 → True
    assert wrong != right


# --- Golden structural pins ----------------------------------------------------------------------

def test_emits_euclidean_operators_and_integer_binder():
    out = d2l.render_pred("(a - b) % 5 == 2")
    assert "Int.emod" in out and " % " not in out         # Euclidean mod, never truncating `%`
    assert "(a - b)" in out                                # real subtraction, not monus
    div = d2l.render_pred("n / 4 == 1")
    assert "Int.ediv n 4" in div and " / " not in div      # Euclidean div, never truncating `/`


def test_pair_is_over_integer_box_and_requires_established_domain():
    p = d2l.faithfulness_pair("(a*a + b*b) % 4 == 0", "(a*a + b*b) % 4 != 3", "(a*a + b*b) % 4 == 0")
    assert p["coverage"].startswith("∀ (a b : ℤ),") and "0 ≤ a" in p["coverage"]
    assert p["property"].count("→") >= 3                   # box → established → claim_domain → property
    assert p["exists_claim"].startswith("∃ (a b : ℤ),") and "∧" in p["exists_claim"]
    assert "ℕ" not in p["property"] and "Nat.sub" not in p["property"]
    with pytest.raises(d2l.RenderError):
        d2l.faithfulness_pair("n % 2 == 0", "n % 2 == 0", None)   # missing established_domain → DEFER


def test_min_max_predicates_do_not_capture_the_callee_as_a_bound_variable():
    """Regression for the free_vars capture bug: `min`/`max` are call targets, not ℤ variables, so the
    binder must be ∀ (a b : ℤ) — never ∀ (a b min : ℤ) with `(min a b)` applying a bound variable."""
    assert d2l.free_vars("min(a, b) % 3 == 0") == ["a", "b"]      # not ['a','b','min']
    p = d2l.faithfulness_pair("min(a, b) % 3 == 0", "max(a, b) % 2 != 1", "min(a, b) % 3 == 0")
    assert p["coverage"].startswith("∀ (a b : ℤ),")              # no `min`/`max` in the binder
    for stmt in p.values():
        assert "min : ℤ" not in stmt and "max : ℤ" not in stmt and "0 ≤ min" not in stmt
        assert "(min a b)" in stmt or "(max a b)" in stmt        # used as a function, correctly


def test_canonical_statement_is_deterministic():
    args = ("(a*a + b*b) % 4 == 0", "(a*a + b*b) % 4 != 3", "(a*a + b*b) % 4 == 0")
    assert d2l.canonical_statement(*args) == d2l.canonical_statement(*args)


# --- Refusals: everything outside the conformance-pinned fragment must DEFER (raise) --------------

@pytest.mark.parametrize("bad", [
    "2 ** n == 1",        # variable exponent (ADR 0035 order case) — out of increment-1 scope
    "2 ** (n+1) % 5 == 1",  # COMPOUND exponent under mod — outside the ADR 0065 shape
    "n ** k % 5 == 1",      # variable BASE — outside the ADR 0065 shape
    "n % k == 0",         # variable divisor
    "n / k == 0",         # variable divisor
    "gcd(n, 6) == 1",     # gcd has no DSL referent (dropped from scope)
    "foo(n) == 0",        # unknown call
    "Nat.min(a, b) == 0", # attribute call
    "n + 1",              # bare term, not a boolean predicate
    "n & 1 == 0",         # bitwise — outside the DSL
])
def test_out_of_fragment_predicates_are_refused(bad):
    with pytest.raises(d2l.RenderError):
        d2l.render_pred(bad)


# --- Optional: anchor the audited Euclidean values in the real Lean kernel (opt-in) ----------------
# NB: the unbounded ∀-over-ℤ pair is NOT `decide`-able (no `Decidable (∀ a:ℤ, …)` instance); its proof
# needs the residue reduction that is Track A increment 2, so it is deliberately NOT asserted here.

@pytest.mark.skipif(not os.environ.get("LEIBNIZ_LEAN_E2E"), reason="set LEIBNIZ_LEAN_E2E=1 to run Lean e2e")
def test_lean_kernel_confirms_euclidean_semantics():  # pragma: no cover
    from leibniz.backends.lean_repl import LeanReplBackend, available
    if not available():
        pytest.skip("Lean image unavailable")
    backend = LeanReplBackend()
    try:
        for src in ("example : Int.emod (-7) 2 = 1 := by decide",
                    "example : Int.ediv (-7) 2 = -4 := by decide"):
            assert backend._run(src, ()) is not None
    finally:
        backend.close()
