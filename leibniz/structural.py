"""Structural novelty signatures (ADR 0032) — canonicalize a claim's polynomial-congruence
FORM, never its truth.

ADR 0031 Layer 2 tried to catch restatements of known results by Z3 *truth*-equivalence and
was retracted as unsound: every theorem's claim is a tautology over its domain, so all true
claims were mutually equivalent and any always-true known matched everything. This module
decides on FORM instead: it reduces a polynomial congruence to a canonical signature and
matches signature-to-signature. Truth is never evaluated.

`congruence_signature("(n^5 + 4*n) % 5 == 0")` and `congruence_signature("n^5 % 5 == n % 5")`
both yield `('==', 5, ((1, 4), (5, 1)))` — the same congruence `n^5 ≡ n (mod 5)` — so they
match; while `n + 0 == n` (not a congruence) and `n^2 % 3 == 1` (a different congruence) all
yield `None` / a distinct signature and stay NOVEL.

MULTIVARIATE (ADR 0032, conservative extension): a 2nd distinct variable no longer forces
`None`. A multivariate monomial is the sorted tuple of `(variable_name, exponent)` and the
signature is `(relop, m, sorted((monomial, coeff_mod_m)))`. The match keys on the LITERAL
variable names: `a*b % 2 == 0` matches a corpus `a*b % 2 == 0` but NOT `x*y % 2 == 0` (a
rename). This is deliberate. Variable-RENAMING canonicalization (mapping a,b -> x,y) is a
permutation-canonical-form problem; getting it wrong would collapse two genuinely different
congruences to one signature — a false-KNOWN that wrongly suppresses a real discovery. We
therefore do NOT rename. The cost is a missed match (false-NOVEL), which is safe.

SOUNDNESS: two claims share a signature IFF they assert the same polynomial congruence in
ℤ/mℤ over the SAME literally-named variables (up to a unit multiple when m is prime AND the
claim is single-variable). Coefficient reduction mod m is an exact algebraic normalization in
(ℤ/mℤ)[vars], not a value reduction — so DIFFERENT facts get DIFFERENT signatures (no
false-KNOWN). A different monomial set (different variable names, different exponents, or a
different number of variables) yields a different signature by construction. Anything not a
clean polynomial congruence in the recognized shapes returns None → not matched → NOVEL (the
only error direction is a missed known, benign; and novelty only demotes, reversibly). Pure
stdlib; no Z3, no Lean.
"""
from __future__ import annotations

import ast
from typing import Optional

MAX_NODES = 200    # bound the AST against adversarial input (matches smt_z3)
MAX_DEGREE = 64    # cap expanded-polynomial total degree (bounds dict size; over-degree -> NotPoly)
MAX_EXP = 8        # constant-power cap (matches the DSL's ^ cap, ADR 0021)


class _NotPoly(Exception):
    """The term is not an integer polynomial in the DSL's `+ - *` / constant `^`."""


# --- Monomial representation -------------------------------------------------
# A monomial is a canonical key: a tuple of (variable_name, exponent) pairs sorted by name,
# every exponent > 0; the constant monomial is the empty tuple (). A polynomial is a dict
# {monomial_key: int_coeff}. The univariate case is the special case where every non-constant
# monomial mentions exactly one (the same) variable; its public signature is rendered in the
# legacy `(exponent, coeff)` form so existing univariate behavior is byte-identical.


def _mono_degree(mono: tuple) -> int:
    return sum(e for _, e in mono)


def _mono_mul(a: tuple, b: tuple) -> tuple:
    """Multiply two monomials: add exponents per variable (all exps stay > 0)."""
    exps: dict = {}
    for name, e in a:
        exps[name] = exps.get(name, 0) + e
    for name, e in b:
        exps[name] = exps.get(name, 0) + e
    return tuple(sorted(exps.items()))


def _add(a: dict, b: dict) -> dict:
    out = dict(a)
    for mono, c in b.items():
        out[mono] = out.get(mono, 0) + c
    return out


def _neg(a: dict) -> dict:
    return {mono: -c for mono, c in a.items()}


def _mul(a: dict, b: dict) -> dict:
    out: dict = {}
    for m1, c1 in a.items():
        for m2, c2 in b.items():
            mono = _mono_mul(m1, m2)
            if _mono_degree(mono) > MAX_DEGREE:
                raise _NotPoly
            out[mono] = out.get(mono, 0) + c1 * c2
    return out


def _expand(node: ast.AST, state: dict) -> dict:
    """Expand an AST term to a polynomial {monomial_key: int_coeff}. Every variable name seen is
    recorded in `state['vars']`; a literal name is keyed on itself (no renaming — that would risk
    a false-KNOWN). Any non-polynomial construct (mod/div inside the term, a function call, a
    non-constant exponent) => _NotPoly."""
    if isinstance(node, ast.Constant) and isinstance(node.value, int) and not isinstance(node.value, bool):
        return {(): node.value}
    if isinstance(node, ast.Name):
        state["vars"].add(node.id)
        return {((node.id, 1),): 1}
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
            out = {(): 1}
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


def _normalize(poly: dict, m: int, single_var: bool) -> tuple:
    """Reduce coefficients mod m (exact in ℤ/mℤ) and drop zeros. Nothing is renamed.

    For a SINGLE-variable claim render the legacy univariate signature — `tuple(sorted((exp,
    coeff)))` — and, if m is PRIME, put it in canonical monic form (multiply by the
    leading-coefficient inverse) so unit-multiples and side-swaps collapse. This path is
    byte-identical to the pre-ADR-0032 behavior.

    For a MULTIVARIATE claim render `tuple(sorted((monomial_key, coeff)))` and SKIP the unit step:
    unit-normalization across multiple variables is ambiguous (which leading term?) and a wrong
    choice could collapse distinct congruences — so we skip it, costing only recall, never
    soundness. The two render shapes are disjoint (int exponent keys vs tuple monomial keys), so
    a univariate and a multivariate signature can never coincide."""
    poly = {mono: c % m for mono, c in poly.items() if c % m != 0}
    if not poly:
        return ()
    if single_var:
        # collapse each surviving monomial to its single total exponent (constant -> 0)
        uni = {_mono_degree(mono): c for mono, c in poly.items()}
        if _isprime(m):
            inv = pow(uni[max(uni)], -1, m)
            uni = {e: (c * inv) % m for e, c in uni.items()}
        return tuple(sorted(uni.items()))
    return tuple(sorted(poly.items()))


def congruence_signature(predicate: Optional[str]) -> Optional[tuple]:
    """Canonical signature of a polynomial congruence DSL predicate, or None.

    Recognized SOUND shapes only (relop ∈ {==, !=}):
      • `P % m <relop> c`        with c an integer constant residue 0 ≤ c < m
      • `P % m <relop> Q % m`    (both sides reduced by the SAME modulus)
    where P, P1, P2 are integer polynomials in the DSL's `+ - *` / constant `^` over one or
    more LITERAL variable names. Everything else — a raw (non-reduced) RHS, two different moduli,
    a non-polynomial term, an inequality, a non-congruence — returns None (→ stays NOVEL).

    Single-variable claims produce the legacy univariate signature (with prime-m unit
    normalization); multivariate claims produce a monomial-keyed signature with NO renaming and
    NO unit normalization (conservative: never a false-KNOWN, only missed matches)."""
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
    state = {"vars": set()}
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
            poly = _add(_expand(pnode, state), {(): -c})
        else:
            return None
    except _NotPoly:
        return None
    if m < 2:
        return None
    single_var = len(state["vars"]) <= 1
    return (relop, m, _normalize(poly, m, single_var))
