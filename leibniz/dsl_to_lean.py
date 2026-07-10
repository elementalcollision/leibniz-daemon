"""ADR 0056 Track A — the audited DSL→Lean renderer (increment 1: the statement side).

The faithfulness DSL (``leibniz.backends.smt_z3``) is a small integer-predicate language the Z3
backend decides. ADR 0055/0056 move the *decision* onto the Lean kernel: the gate asks the kernel to
decide the faithfulness **pair** over ``established_domain`` (coverage + property, ``probes.py``) by
finite residue enumeration. To do that soundly, the DSL predicate must be **rendered into a Lean
proposition that denotes the same integer function** — and *that renderer is faithfulness TCB*
(ADR 0056's review: a mis-encoding renderer passes any string-identity check while both strings mean
the wrong thing; only a semantics-conformance suite catches it — see ``tests/test_dsl_to_lean_conformance.py``).

This module is the renderer. It is deliberately tiny and total-or-raise, and it commits to the two
decisions ADR 0056's review forced:

1. **ℤ-with-explicit-box, never ℕ.** The DSL admits real subtraction (``a - b``) and unary minus over
   a box that constrains only *variables* to be non-negative (``smt_z3.py:279-280``), so subexpressions
   range over ℤ. Rendering over ℕ would turn ``a - b`` into truncated ``Nat.sub`` (monus) — a *different*
   Boolean function and a false-EXACT-PASS. So every quantifier is ``∀ (v : ℤ), 0 ≤ v → …`` /
   ``∃ (v : ℤ), 0 ≤ v ∧ …``: real ℤ arithmetic with the non-negativity box explicit in the proposition.
2. **Euclidean division/modulo (``Int.ediv`` / ``Int.emod``), never Lean's ``/`` / ``%``.** Z3's integer
   ``div``/``mod`` are Euclidean (``mod`` non-negative); Lean's ``HDiv``/``HMod`` on ``Int`` are
   *truncating* (``Int.div`` rounds toward zero: ``-7 / 2 = -3`` vs the DSL's ``-4``). Emitting the
   truncating operators would silently mis-encode every negative intermediate. The conformance suite
   pins ``MOD_OP``/``DIV_OP`` against the DSL over a grid including negatives.

**Admission is in lockstep with the Z3 backend.** The walk below mirrors ``smt_z3._conv`` node-for-node
and imports the same ``MAX_POW``/``MAX_NODES`` caps, so the renderer admits *exactly* the Z3-admitted
grammar and no more. Anything outside it — a variable exponent (the ADR 0035 ``base^n % m`` order case,
out of increment-1 scope), a non-constant divisor, an unknown call — raises :class:`RenderError`, and
the caller **DEFERs** (never a guess). Variable-exponent modulus is refused here because the inner
``Pow`` with a non-constant exponent raises before the ``Mod`` node is reached.

**Fail-closed.** This module renders *statements*; it registers nothing. No faithfulness re-checker of
kind ``lean-decided-faithfulness`` is registered anywhere, so ``FaithfulnessGate.recheckers.get(kind)``
is ``None`` and a backend PASS is never accepted (``faithfulness.py:129-130``). Wiring the renderer to
the gate via the tool-registry E7 template pin (``leibniz/tools/registry.py``), and emitting the
residue-case-split *proof*, are increment 2 — gated on this increment's conformance suite and a further
adversarial re-review.
"""
from __future__ import annotations

import ast
from typing import Optional

from leibniz.backends.smt_z3 import MAX_NODES, MAX_POW

# The two load-bearing operator choices (pinned by the conformance suite). Euclidean, to match Z3.
MOD_OP = "Int.emod"   # DSL `a % d`  (d>0)  — non-negative remainder, NOT Lean's truncating `%`
DIV_OP = "Int.ediv"   # DSL `a / d`  (d>0)  — floor for positive divisor, NOT Lean's truncating `/`

_CMP_LEAN = {
    ast.Lt: "<", ast.LtE: "≤", ast.Gt: ">", ast.GtE: "≥", ast.Eq: "=", ast.NotEq: "≠",
}


class RenderError(ValueError):
    """The predicate is outside the renderable (conformance-pinned) DSL fragment → the caller DEFERs."""


def _const_int(node: ast.AST) -> Optional[int]:
    """The int value if `node` is a non-negative integer literal, else None (mirrors smt_z3._const_int)."""
    if isinstance(node, ast.Constant) and isinstance(node.value, int) and not isinstance(node.value, bool):
        return node.value
    return None


def _term(node: ast.AST) -> str:
    """Render an INTEGER-valued DSL node to a fully-parenthesised Lean ℤ term. Raises on anything the
    Z3 backend would not admit as an integer term."""
    if isinstance(node, ast.UnaryOp):
        if isinstance(node.op, ast.USub):
            return f"(-{_term(node.operand)})"
        raise RenderError(f"unary op {type(node.op).__name__} is not an integer term")
    if isinstance(node, ast.BinOp):
        op = node.op
        if isinstance(op, ast.Add):
            return f"({_term(node.left)} + {_term(node.right)})"
        if isinstance(op, ast.Sub):
            return f"({_term(node.left)} - {_term(node.right)})"
        if isinstance(op, ast.Mult):
            return f"({_term(node.left)} * {_term(node.right)})"
        if isinstance(op, ast.Pow):
            # Constant, small, non-negative exponent only (repeated multiplication). A VARIABLE
            # exponent (the ADR 0035 `base^n % m` order case) is out of increment-1 scope → refuse.
            k = _const_int(node.right)
            if k is None or k > MAX_POW:
                raise RenderError("power needs a constant exponent in [0, MAX_POW] (no variable exponents)")
            return f"({_term(node.left)} ^ ({k} : ℕ))"
        if isinstance(op, (ast.Div, ast.FloorDiv)):
            d = _const_int(node.right)
            if not d or d <= 0:
                raise RenderError("division needs a constant positive divisor")
            return f"({DIV_OP} {_term(node.left)} {d})"
        if isinstance(op, ast.Mod):
            d = _const_int(node.right)
            if not d or d <= 0:
                raise RenderError("modulo needs a constant positive divisor")
            # ADR 0065: `base^n % m` (CONSTANT base, BARE-variable exponent, constant modulus) — the
            # exact shape smt_z3's ADR 0035 order-reduction admits, so lockstep is preserved: the
            # variable exponent is renderable ONLY under a constant modulus, nowhere else. Rendered
            # `(base : ℤ) ^ (n).toNat`: faithful under the ℤ-box (0 ≤ n ⇒ ↑n.toNat = n, so the power
            # denotes the DSL's base**n and the Euclidean emod matches); outside the box the statement
            # is vacuous, exactly as note 1's ℤ-with-box convention already guarantees.
            pw = node.left
            if (isinstance(pw, ast.BinOp) and isinstance(pw.op, ast.Pow)
                    and _const_int(pw.left) is not None and isinstance(pw.right, ast.Name)):
                b = _const_int(pw.left)
                return f"({MOD_OP} (({b} : ℤ) ^ ({pw.right.id}).toNat) {d})"
            return f"({MOD_OP} {_term(node.left)} {d})"
        raise RenderError(f"bin op {type(op).__name__}")
    if isinstance(node, ast.Call):
        if (not isinstance(node.func, ast.Name) or node.keywords
                or any(isinstance(a, ast.Starred) for a in node.args)):
            raise RenderError("only bare min()/max() calls are allowed")
        name = node.func.id
        if name in ("min", "max") and len(node.args) >= 2:
            out = _term(node.args[0])
            for a in node.args[1:]:
                out = f"({name} {out} {_term(a)})"
            return out
        raise RenderError(f"unsupported call: {name}/{len(node.args)}")
    if isinstance(node, ast.Name):
        return node.id
    val = _const_int(node)
    if val is not None:
        return str(val)
    raise RenderError(f"unsupported syntax: {type(node).__name__}")


def _is_bool_node(node: ast.AST) -> bool:
    """A DSL node that renders to a Lean `Prop` (boolean), not an arithmetic term: a comparison, an
    `and`/`or`, or a `not`. Used to distinguish a biconditional `(P) == (Q)` (boolean operands) from an
    arithmetic equality `poly == c` (arithmetic operands)."""
    return (isinstance(node, ast.BoolOp)
            or (isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not))
            or isinstance(node, ast.Compare))


def _prop(node: ast.AST) -> str:
    """Render a BOOLEAN DSL node to a fully-parenthesised Lean `Prop`. Raises on a non-boolean node
    (mirrors smt_z3.compile_pred's 'predicate is not a boolean expression' check)."""
    if isinstance(node, ast.BoolOp):
        conn = " ∧ " if isinstance(node.op, ast.And) else " ∨ "
        return "(" + conn.join(_prop(v) for v in node.values) + ")"
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
        return f"(¬ {_prop(node.operand)})"
    if isinstance(node, ast.Compare):
        # Biconditional: a single `==` / `!=` whose operands are THEMSELVES boolean (comparisons,
        # and/or, not) renders to `P ↔ Q` (resp. `¬ (P ↔ Q)`) — Python has no `↔`, so the daemon
        # writes it as `(P) == (Q)`. Arithmetic equalities (`poly == c`) keep the existing rendering
        # because their operands are terms, not booleans.
        if (len(node.ops) == 1 and isinstance(node.ops[0], (ast.Eq, ast.NotEq))
                and _is_bool_node(node.left) and _is_bool_node(node.comparators[0])):
            iff = f"({_prop(node.left)} ↔ {_prop(node.comparators[0])})"
            return iff if isinstance(node.ops[0], ast.Eq) else f"(¬ {iff})"
        terms = [node.left, *node.comparators]
        clauses = []
        for i, op in enumerate(node.ops):
            sym = _CMP_LEAN.get(type(op))
            if sym is None:
                raise RenderError(f"compare op {type(op).__name__}")
            clauses.append(f"({_term(terms[i])} {sym} {_term(terms[i + 1])})")
        return "(" + " ∧ ".join(clauses) + ")" if len(clauses) > 1 else clauses[0]
    raise RenderError("predicate is not a boolean expression")


def _parse(src: str) -> ast.AST:
    src = src.replace("^", "**")  # `^` means power here (match smt_z3.compile_pred exactly)
    try:
        tree = ast.parse(src, mode="eval")
    except (SyntaxError, ValueError) as e:
        raise RenderError(str(e)) from e
    if sum(1 for _ in ast.walk(tree)) > MAX_NODES:
        raise RenderError("predicate too large")
    return tree.body


def render_pred(src: str) -> str:
    """Render a DSL predicate string to a Lean `Prop`. Raises :class:`RenderError` if it is outside the
    conformance-pinned fragment (→ the caller DEFERs)."""
    return _prop(_parse(src))


def free_vars(*srcs: str) -> list[str]:
    """The sorted distinct integer VARIABLE names across the given DSL predicate strings (the ∀/∃
    binder). A call target (``min``/``max``) is a function name, not a variable, so it is excluded —
    exactly as ``smt_z3._conv`` treats it (it never creates a Z3 var for the callee). Walking every
    ``ast.Name`` naively would bind ``min`` as a ℤ variable and then emit ``(min a b)`` applying that
    bound variable, capturing the callee — an ill-typed statement (kernel-rejected → DEFER) for every
    ``min``/``max`` predicate."""
    names: set[str] = set()

    def visit(node: ast.AST) -> None:
        if isinstance(node, ast.Call):
            for a in node.args:          # descend into the arguments only, never node.func
                visit(a)
            return
        if isinstance(node, ast.Name):
            names.add(node.id)
        for child in ast.iter_child_nodes(node):
            visit(child)

    for src in srcs:
        if src is None:
            continue
        visit(_parse(src))
    return sorted(names)


def _binder(kind: str, vars_: list[str]) -> str:
    return f"{kind} ({' '.join(vars_)} : ℤ)," if vars_ else f"{kind} (_u : ℤ),"


def _nonneg(vars_: list[str], conn: str) -> str:
    """The non-negativity box, as antecedents (`conn='→'`) or conjuncts (`conn='∧'`)."""
    parts = [f"0 ≤ {v}" for v in vars_] or ["True"]
    return "".join(f"({p}) {conn} " for p in parts) if conn == "→" else " ∧ ".join(f"({p})" for p in parts)


def faithfulness_pair(claim_domain: str, claim_property: str, established_domain: str) -> dict[str, str]:
    """The four Lean propositions the kernel must decide for a faithful EXACT-PASS, over ℤ-with-box.

    - ``coverage``      : ∀ vars, 0≤vars → claim_domain → established_domain
    - ``property``      : ∀ vars, 0≤vars → established_domain → claim_domain → claim_property
    - ``exists_claim``  : ∃ vars, 0≤vars ∧ claim_domain                       (positive-content control)
    - ``exists_ec``     : ∃ vars, 0≤vars ∧ established_domain ∧ claim_domain   (non-empty intersection)

    All three DSL fields are required (a None `established_domain` is not renderable → DEFER upstream).
    Raises :class:`RenderError` if any field is outside the fragment."""
    if not (claim_domain and claim_property and established_domain):
        raise RenderError("faithfulness pair needs claim_domain, claim_property and established_domain")
    cd, cp, ed = render_pred(claim_domain), render_pred(claim_property), render_pred(established_domain)
    vs = free_vars(claim_domain, claim_property, established_domain)
    fa, ex = _binder("∀", vs), _binder("∃", vs)
    box_imp, box_and = _nonneg(vs, "→"), _nonneg(vs, "∧")
    return {
        "coverage": f"{fa} {box_imp}{cd} → {ed}",
        "property": f"{fa} {box_imp}{ed} → {cd} → {cp}",
        "exists_claim": f"{ex} {box_and} ∧ {cd}",
        "exists_ec": f"{ex} {box_and} ∧ {ed} ∧ {cd}",
    }


def canonical_statement(claim_domain: str, claim_property: str, established_domain: str) -> str:
    """The single deterministic string that binds a certificate to this exact claim (the future E7
    template, ``leibniz/tools/registry.py``: the certificate's claimed statement must equal
    ``template(cert.data)`` byte-for-byte). Pure and deterministic: the four pair statements joined in
    a fixed order. Increment 2 wires this as the registered template; increment 1 only defines it so the
    conformance suite can pin its determinism and the E7 str-identity semantics."""
    p = faithfulness_pair(claim_domain, claim_property, established_domain)
    return " ⋀ ".join(p[k] for k in ("coverage", "property", "exists_claim", "exists_ec"))
