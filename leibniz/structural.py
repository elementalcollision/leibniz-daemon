"""Structural novelty signatures (ADR 0032) — canonicalize a claim's polynomial-congruence
FORM, never its truth.

ADR 0031 Layer 2 tried to catch restatements of known results by Z3 *truth*-equivalence and
was retracted as unsound: every theorem's claim is a tautology over its domain, so all true
claims were mutually equivalent and any always-true known matched everything. This module
decides on FORM instead: it reduces a univariate polynomial congruence to a canonical
signature and matches signature-to-signature. Truth is never evaluated.

`congruence_signature("(n^5 + 4*n) % 5 == 0")` and `congruence_signature("n^5 % 5 == n % 5")`
both yield `('==', 5, ((1, 4), (5, 1)))` — the same congruence `n^5 ≡ n (mod 5)` — so they
match; while `n + 0 == n` (not a congruence) and `n^2 % 3 == 1` (a different congruence) and
`a * b % 2 == 0` (multivariate) all yield `None` / a distinct signature and stay NOVEL.

SOUNDNESS: two claims share a signature IFF they assert the same polynomial congruence in
ℤ/mℤ (up to a unit multiple when m is prime). Coefficient reduction mod m is an exact
algebraic normalization in (ℤ/mℤ)[x], not a value reduction — so DIFFERENT facts get DIFFERENT
signatures (no false-KNOWN). Anything not a clean univariate congruence in the recognized
shapes returns None → not matched → NOVEL (the only error direction is a missed known, benign;
and novelty only demotes, reversibly). Pure stdlib; no Z3, no Lean.
"""
from __future__ import annotations

import ast
from typing import Optional

MAX_NODES = 200    # bound the AST against adversarial input (matches smt_z3)
MAX_DEGREE = 64    # cap expanded-polynomial degree (bounds dict size; over-degree -> NotPoly)
MAX_EXP = 8        # constant-power cap (matches the DSL's ^ cap, ADR 0021)


class _NotPoly(Exception):
    """The term is not a univariate integer polynomial in the DSL's `+ - *` / constant `^`."""


def _add(a: dict, b: dict) -> dict:
    out = dict(a)
    for e, c in b.items():
        out[e] = out.get(e, 0) + c
    return out


def _neg(a: dict) -> dict:
    return {e: -c for e, c in a.items()}


def _mul(a: dict, b: dict) -> dict:
    out: dict = {}
    for e1, c1 in a.items():
        for e2, c2 in b.items():
            e = e1 + e2
            if e > MAX_DEGREE:
                raise _NotPoly
            out[e] = out.get(e, 0) + c1 * c2
    return out


def _expand(node: ast.AST, state: dict) -> dict:
    """Expand an AST term to a univariate polynomial {exponent: int_coeff}. `state['var']`
    pins the single variable; a second distinct name => _NotPoly (multivariate is out of scope
    and must NOT be canonicalized as univariate). Any non-polynomial construct (mod/div inside
    the term, a function call, a non-constant exponent) => _NotPoly."""
    if isinstance(node, ast.Constant) and isinstance(node.value, int) and not isinstance(node.value, bool):
        return {0: node.value}
    if isinstance(node, ast.Name):
        if state["var"] is None:
            state["var"] = node.id
        elif node.id != state["var"]:
            raise _NotPoly
        return {1: 1}
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        return _neg(_expand(node.operand, state))
    if isinstance(node, ast.BinOp):
        op = node.op
        if isinstance(op, ast.Add):
            return _add(_expand(node.left, state), _expand(node.right, state))
        if isinstance(op, ast.Sub):
            return _add(_expand(node.left, state), _neg(_expand(node.right, state)))
        if isinstance(op, ast.Mult):
            return _mul(_expand(node.left, state), _expand(node.right, state))
        if isinstance(op, ast.Pow):
            k = node.right
            if not (isinstance(k, ast.Constant) and isinstance(k.value, int)
                    and not isinstance(k.value, bool) and 0 <= k.value <= MAX_EXP):
                raise _NotPoly
            base = _expand(node.left, state)
            out = {0: 1}
            for _ in range(k.value):
                out = _mul(out, base)
            return out
    raise _NotPoly  # Mod/Div/FloorDiv/Call/etc. inside the polynomial term


def _const_int(node: ast.AST) -> Optional[int]:
    if isinstance(node, ast.Constant) and isinstance(node.value, int) and not isinstance(node.value, bool):
        return node.value
    return None


def _mod(node: ast.AST):
    """If `node` is `P % m` with a constant m, return (P_ast, m); else None."""
    if (isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mod)
            and (m := _const_int(node.right)) is not None):
        return (node.left, m)
    return None


def _isprime(x: int) -> bool:
    if x < 2:
        return False
    i = 2
    while i * i <= x:
        if x % i == 0:
            return False
        i += 1
    return True


def _normalize(poly: dict, m: int) -> tuple:
    """Reduce coefficients mod m (exact in ℤ/mℤ), drop zeros, and for PRIME m put in canonical
    monic form (multiply by the leading-coefficient inverse) so unit-multiples and side-swaps
    collapse. For composite m, skip the unit step — that only misses matches, never creates a
    wrong one."""
    poly = {e: c % m for e, c in poly.items() if c % m != 0}
    if not poly:
        return ()
    if _isprime(m):
        inv = pow(poly[max(poly)], -1, m)
        poly = {e: (c * inv) % m for e, c in poly.items()}
    return tuple(sorted(poly.items()))


def congruence_signature(predicate: Optional[str]) -> Optional[tuple]:
    """Canonical signature of a univariate polynomial congruence DSL predicate, or None.

    Recognized SOUND shapes only (relop ∈ {==, !=}):
      • `P % m <relop> c`        with c an integer constant residue 0 ≤ c < m
      • `P % m <relop> Q % m`    (both sides reduced by the SAME modulus)
    Everything else — a raw (non-reduced) RHS, two different moduli, multivariate, a
    non-polynomial term, an inequality, a non-congruence — returns None (→ stays NOVEL)."""
    if not predicate:
        return None
    try:
        tree = ast.parse(predicate.replace("^", "**"), mode="eval").body
    except (SyntaxError, ValueError):
        return None
    if sum(1 for _ in ast.walk(tree)) > MAX_NODES:
        return None
    if not (isinstance(tree, ast.Compare) and len(tree.ops) == 1):
        return None
    relop = {ast.Eq: "==", ast.NotEq: "!="}.get(type(tree.ops[0]))
    if relop is None:
        return None
    left, right = tree.left, tree.comparators[0]
    lm, rm = _mod(left), _mod(right)
    state = {"var": None}
    try:
        if lm and rm:                         # P1 % m == P2 % m
            if lm[1] != rm[1]:
                return None                   # different moduli -> not one congruence
            m = lm[1]
            poly = _add(_expand(lm[0], state), _neg(_expand(rm[0], state)))
        elif lm or rm:                        # P % m == c  (the other side MUST be a constant)
            (pnode, m), other = (lm, right) if lm else (rm, left)
            c = _const_int(other)
            if c is None or not (0 <= c < m):  # raw-poly RHS or out-of-range residue -> reject
                return None
            poly = _add(_expand(pnode, state), {0: -c})
        else:
            return None
    except _NotPoly:
        return None
    if m < 2:
        return None
    return (relop, m, _normalize(poly, m))
