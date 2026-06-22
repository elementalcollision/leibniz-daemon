"""R2 SMT backend — Z3 over a small, safe arithmetic predicate DSL.

Implements ``leibniz.verifiers.SMTBackend``. Both entry points only ever *kill* a
candidate; a model means "refuted / gamed", UNSAT means "survived" (never
"proven" — only the Lean kernel proves):

- ``find_counterexample(claim, bound)`` — search the conjecture's falsifiable
  predicate for a model (a refutation).
- ``find_gaming_witness(statement, negated_claim, bound)`` — search
  ``statement ∧ negated_claim`` for a model: an object the formal statement admits
  while the human claim is false. For the canonical *domain-narrowing / vacuous
  specialization* gaming pattern the gate (R2b) passes ``statement`` = the region
  the formal statement leaves unconstrained (``¬established_domain``) and
  ``negated_claim`` = ``claim_domain ∧ ¬claim_property`` (see ADR 0004).

Predicate DSL: boolean/arithmetic expressions over the single integer variable
``n`` — integer literals, ``n``, ``+ - *``, comparisons (``< <= > >= == !=``),
``and`` / ``or`` / ``not``, parentheses. Parsed via a whitelisted ``ast`` walk
(no ``eval``); anything else raises ``PredicateError`` and the search degrades to
"no witness" rather than crashing the gate.
"""
from __future__ import annotations

import ast
from dataclasses import dataclass
from typing import Optional

try:  # z3 ships in the `verify` extra; the module stays importable without it
    import z3
except ImportError:  # pragma: no cover
    z3 = None  # type: ignore[assignment]

VAR = "n"


class PredicateError(ValueError):
    """The predicate string is outside the safe DSL."""


_CMP = {
    ast.Lt: lambda a, b: a < b,
    ast.LtE: lambda a, b: a <= b,
    ast.Gt: lambda a, b: a > b,
    ast.GtE: lambda a, b: a >= b,
    ast.Eq: lambda a, b: a == b,
    ast.NotEq: lambda a, b: a != b,
}


def _conv(node: ast.AST, n: z3.ArithRef):
    if isinstance(node, ast.BoolOp):
        vals = [_conv(v, n) for v in node.values]
        return z3.And(*vals) if isinstance(node.op, ast.And) else z3.Or(*vals)
    if isinstance(node, ast.UnaryOp):
        if isinstance(node.op, ast.Not):
            return z3.Not(_conv(node.operand, n))
        if isinstance(node.op, ast.USub):
            return -_conv(node.operand, n)
        raise PredicateError(f"unary op {type(node.op).__name__}")
    if isinstance(node, ast.BinOp):
        a, b = _conv(node.left, n), _conv(node.right, n)
        if isinstance(node.op, ast.Add):
            return a + b
        if isinstance(node.op, ast.Sub):
            return a - b
        if isinstance(node.op, ast.Mult):
            return a * b
        raise PredicateError(f"bin op {type(node.op).__name__}")
    if isinstance(node, ast.Compare):
        terms = [_conv(node.left, n), *[_conv(c, n) for c in node.comparators]]
        clauses = []
        for i, op in enumerate(node.ops):
            fn = _CMP.get(type(op))
            if fn is None:
                raise PredicateError(f"compare op {type(op).__name__}")
            clauses.append(fn(terms[i], terms[i + 1]))
        return z3.And(*clauses) if len(clauses) > 1 else clauses[0]
    if isinstance(node, ast.Name):
        if node.id != VAR:
            raise PredicateError(f"unknown name {node.id!r} (only {VAR!r} allowed)")
        return n
    if isinstance(node, ast.Constant) and isinstance(node.value, int) and not isinstance(node.value, bool):
        return node.value
    raise PredicateError(f"unsupported syntax: {type(node).__name__}")


def compile_pred(src: str, n: z3.ArithRef):
    """Compile a DSL predicate string into a Z3 boolean expression over `n`."""
    try:
        tree = ast.parse(src, mode="eval")
    except SyntaxError as e:
        raise PredicateError(str(e)) from e
    return _conv(tree.body, n)


@dataclass
class Z3Backend:
    """Z3-backed SMTBackend. Only kills; never promotes."""

    default_bound: int = 64

    def _search(self, preds: list[str], bound: int) -> Optional[dict]:
        n = z3.Int(VAR)
        solver = z3.Solver()
        solver.add(n >= 0, n <= bound)
        try:
            for p in preds:
                solver.add(compile_pred(p, n))
        except PredicateError:
            return None  # un-encodable -> no witness (do not crash the gate)
        if solver.check() == z3.sat:
            return {"n": solver.model()[n].as_long()}
        return None

    def encodable(self, pred: str) -> bool:
        """True iff `pred` compiles in the safe DSL — so a None search result can be
        read as 'checked, no witness' rather than 'could not encode'. The faithfulness
        probe uses this to DEFER (not vacuously PASS) on contracts it cannot search."""
        if z3 is None:
            return False
        try:
            compile_pred(pred, z3.Int(VAR))
            return True
        except PredicateError:
            return False

    # --- SMTBackend Protocol --------------------------------------------------
    def find_counterexample(self, claim: str, bound: int = 0) -> Optional[dict]:
        return self._search([claim], bound or self.default_bound)

    def find_gaming_witness(
        self, statement: str, negated_claim: str, bound: int = 0
    ) -> Optional[dict]:
        return self._search([statement, negated_claim], bound or self.default_bound)


def available() -> bool:
    """True iff z3 is importable (used to skip z3 tests where the extra is absent)."""
    return z3 is not None
