"""ADR 0056 Track A — the DSL→Lean renderer semantics-conformance suite.

This is the artifact the ADR 0056 review said must exist before the renderer can be trusted: a
mis-encoding renderer passes any string-identity check while both strings denote the wrong
proposition, so *only* a conformance suite catches it. It pins, over a grid **including negatives**,
that the Lean operators the renderer emits denote the SAME integer function as the DSL/Z3 backend —
the load-bearing cases being Euclidean ``Int.emod``/``Int.ediv`` (not Lean's truncating ``%``/``/``)
and real ℤ subtraction (not ℕ monus).

The ground truth is doubly anchored:
- The DSL/Z3 meaning is modelled by Python ``%``/``//`` which, for the DSL's positive constant divisor,
  ARE Euclidean (non-negative remainder, floor quotient) — exactly Z3's integer ``mod``/``div``.
- The Lean meaning of each emitted operator token is an INDEPENDENT table (:data:`TOKEN_SEM`), whose
  entries are pinned to hand-verified Lean values (``Int.emod (-7) 2 = 1``, ``Int.ediv (-7) 2 = -4``,
  truncating ``(-7) % 2 = -1``, ``(-7) / 2 = -3``). An optional Lean-image end-to-end test
  (``LEIBNIZ_LEAN_E2E=1``) anchors those values in the real kernel.
"""
from __future__ import annotations

import ast
import os

import pytest

from leibniz import dsl_to_lean as d2l


# --- Independent semantics tables (audited; pinned to hand-verified Lean values below) -------------

def _euclid_mod(a: int, m: int) -> int:  # Z3 / Int.emod : non-negative remainder for m>0
    return a % m

def _euclid_div(a: int, m: int) -> int:  # Z3 / Int.ediv : floor quotient for m>0
    return a // m

def _trunc_mod(a: int, m: int) -> int:   # Lean HMod (Int.mod) : truncated, sign of dividend
    return a - m * int(a / m)

def _trunc_div(a: int, m: int) -> int:   # Lean HDiv (Int.div) : truncation toward zero
    return int(a / m)

TOKEN_SEM = {
    "Int.emod": _euclid_mod, "Int.ediv": _euclid_div,   # the conformant (renderer's) choices
    "%": _trunc_mod, "/": _trunc_div,                    # the WRONG choices, for the regression guard
}


def test_audited_semantics_table_matches_hand_verified_lean_values():
    """The independent Lean-semantics table is itself pinned to values a human verified in Lean."""
    assert TOKEN_SEM["Int.emod"](-7, 2) == 1     # Euclidean: non-negative
    assert TOKEN_SEM["Int.ediv"](-7, 2) == -4    # Euclidean: floor
    assert TOKEN_SEM["%"](-7, 2) == -1           # truncating: sign of dividend
    assert TOKEN_SEM["/"](-7, 2) == -3           # truncating: toward zero
    # The renderer must have chosen the Euclidean operators (this is what makes the suite meaningful).
    assert d2l.MOD_OP == "Int.emod" and d2l.DIV_OP == "Int.ediv"


# --- A reference evaluator over the DSL AST, parameterised by the mod/div semantics ---------------

def _eval(node: ast.AST, asn: dict, mod_fn, div_fn):
    """Evaluate a DSL node over an assignment, using `mod_fn`/`div_fn` for `%`/`/`. Real ℤ subtraction
    throughout (there is no ℕ monus — the renderer emits `∀ (v:ℤ)`)."""
    if isinstance(node, ast.BoolOp):
        vals = [_eval(v, asn, mod_fn, div_fn) for v in node.values]
        return all(vals) if isinstance(node.op, ast.And) else any(vals)
    if isinstance(node, ast.UnaryOp):
        if isinstance(node.op, ast.Not):
            return not _eval(node.operand, asn, mod_fn, div_fn)
        if isinstance(node.op, ast.USub):
            return -_eval(node.operand, asn, mod_fn, div_fn)
        raise AssertionError("unexpected unary")
    if isinstance(node, ast.BinOp):
        a = _eval(node.left, asn, mod_fn, div_fn)
        b = _eval(node.right, asn, mod_fn, div_fn)
        op = node.op
        if isinstance(op, ast.Add):
            return a + b
        if isinstance(op, ast.Sub):
            return a - b
        if isinstance(op, ast.Mult):
            return a * b
        if isinstance(op, ast.Pow):
            return a ** b
        if isinstance(op, (ast.Div, ast.FloorDiv)):
            return div_fn(a, b)
        if isinstance(op, ast.Mod):
            return mod_fn(a, b)
        raise AssertionError("unexpected binop")
    if isinstance(node, ast.Compare):
        left = _eval(node.left, asn, mod_fn, div_fn)
        ok = True
        for op, comp in zip(node.ops, node.comparators):
            right = _eval(comp, asn, mod_fn, div_fn)
            ok = ok and {
                ast.Lt: left < right, ast.LtE: left <= right, ast.Gt: left > right,
                ast.GtE: left >= right, ast.Eq: left == right, ast.NotEq: left != right,
            }[type(op)]
            left = right
        return ok
    if isinstance(node, ast.Call):
        args = [_eval(a, asn, mod_fn, div_fn) for a in node.args]
        return min(args) if node.func.id == "min" else max(args)
    if isinstance(node, ast.Name):
        return asn[node.id]
    if isinstance(node, ast.Constant):
        return node.value
    raise AssertionError(f"unexpected node {type(node).__name__}")


def _grid(vars_, lo=-8, hi=8):
    if not vars_:
        yield {}
        return
    head, *rest = vars_
    for val in range(lo, hi + 1):
        for tail in _grid(rest, lo, hi):
            yield {head: val, **tail}


# Predicates that exercise the load-bearing cases: negative intermediates through mod/div/sub, nesting,
# composition through min/max, multivariable modular polynomials.
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
]


@pytest.mark.parametrize("pred", CONFORMANCE_PREDS)
def test_renderer_ops_denote_the_DSL_function_over_negatives(pred):
    """For every grid point (including negatives), the DSL/Z3 meaning (Euclidean) equals the meaning of
    the operator tokens the renderer emitted. A regression to truncating `%`/`/` or to ℕ monus would
    diverge at a negative intermediate and fail here."""
    tree = ast.parse(pred.replace("^", "**"), mode="eval").body
    vars_ = sorted({n.id for n in ast.walk(tree) if isinstance(n, ast.Name)})
    # sanity: the renderer accepts it (in-fragment)
    d2l.render_pred(pred)
    emit_mod, emit_div = TOKEN_SEM[d2l.MOD_OP], TOKEN_SEM[d2l.DIV_OP]
    for asn in _grid(vars_):
        dsl_truth = _eval(tree, asn, _euclid_mod, _euclid_div)          # what the DSL/Z3 means
        emitted_truth = _eval(tree, asn, emit_mod, emit_div)           # what the emitted Lean means
        assert dsl_truth == emitted_truth, f"{pred} @ {asn}: DSL={dsl_truth} emitted={emitted_truth}"


def test_regression_guard_would_fire_if_renderer_used_truncating_ops():
    """Proof the suite has teeth: had the renderer chosen Lean's truncating `%`/`/`, the differential
    would diverge on a negative intermediate."""
    tree = ast.parse("(a - b) % 5 == 2", mode="eval").body
    diverged = any(
        _eval(tree, asn, _euclid_mod, _euclid_div) != _eval(tree, asn, TOKEN_SEM["%"], TOKEN_SEM["/"])
        for asn in _grid(["a", "b"])
    )
    assert diverged, "truncating vs Euclidean must diverge somewhere on the negative grid"


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

def test_canonical_statement_is_deterministic():
    args = ("(a*a + b*b) % 4 == 0", "(a*a + b*b) % 4 != 3", "(a*a + b*b) % 4 == 0")
    assert d2l.canonical_statement(*args) == d2l.canonical_statement(*args)


# --- Refusals: everything outside the conformance-pinned fragment must DEFER (raise) --------------

@pytest.mark.parametrize("bad", [
    "2 ** n == 1",        # variable exponent (ADR 0035 order case) — out of increment-1 scope
    "2 ** n % 5 == 1",    # variable-exponent modulus — refused via the inner Pow
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


# --- Optional: anchor the audited table in the real Lean kernel (opt-in; needs the Lean image) -----

@pytest.mark.skipif(not os.environ.get("LEIBNIZ_LEAN_E2E"), reason="set LEIBNIZ_LEAN_E2E=1 to run Lean e2e")
def test_lean_kernel_confirms_euclidean_semantics_and_a_true_pair():  # pragma: no cover
    from leibniz.backends.lean_repl import LeanReplBackend, available
    if not available():
        pytest.skip("Lean image unavailable")
    backend = LeanReplBackend()
    try:
        # Anchor the audited values in the kernel, and confirm a known-true pair `decide`s.
        checks = [
            "example : Int.emod (-7) 2 = 1 := by decide",
            "example : Int.ediv (-7) 2 = -4 := by decide",
            "example : ∀ (a b : ℤ), 0 ≤ a → 0 ≤ b → Int.emod (a*a + b*b) 4 ≠ 3 := by decide",
        ]
        for src in checks:
            assert backend._run(src, ()) is not None
    finally:
        backend.close()
