"""R2 SMT backend — Z3 over a small, *sound* arithmetic predicate DSL.

Implements ``leibniz.verifiers.SMTBackend``. Both entry points only ever *kill* a
candidate; a model means "refuted / gamed", UNSAT means "survived" (never
"proven" — only the Lean kernel proves):

- ``find_counterexample(claim, bound)`` — search the conjecture's falsifiable
  predicate for a model (a refutation).
- ``find_gaming_witness(statement, negated_claim, bound)`` — search
  ``statement ∧ negated_claim`` for a model (the domain-narrowing gaming pattern,
  ADR 0004).
- ``decide_unsat(preds, bound)`` — TRI-STATE: True iff the conjunction is
  conclusively UNSAT, False iff SAT, None iff undecided/un-encodable. The
  faithfulness probe (ADR 0020) certifies only on a conclusive True.

Predicate DSL (ADR 0021 widening): boolean/arithmetic over **any number** of
non-negative integer variables — integer literals; ``+ - *``; **constant-exponent**
power (``^``/``**``, expanded to repeated multiplication); **constant-positive**
``/`` (floor div) and ``%``; comparisons; ``and``/``or``/``not``; parentheses.

Soundness (ADR 0021 + the 0021 soundness review):
- ``^`` is rewritten to ``**`` *before* parsing, so it gets exponentiation
  precedence (Python parses a bare ``^`` as BitXor, which binds *looser* than ``*``
  and would mis-encode ``n*2^0`` — a wrong-UNSAT / vacuous PASS).
- Every search has a timeout; ``z3`` ``unknown`` (and any exception — un-encodable,
  RecursionError, non-boolean, Z3Exception) is reported as "undecided", never as
  "no witness". The DSL is a fragment Z3 decides soundly over a bounded box, so a
  conclusive UNSAT genuinely means "no witness in the box". Un-decided/un-encodable
  contracts DEFER at the probe — never a vacuous PASS, never a gate crash.
"""
from __future__ import annotations

import ast
import math
from dataclasses import dataclass
from math import gcd
from typing import Optional

try:  # z3 ships in the `verify` extra; the module stays importable without it
    import z3
except ImportError:  # pragma: no cover
    z3 = None  # type: ignore[assignment]

VAR = "n"
MAX_POW = 8       # cap constant exponents (sound expansion to repeated multiplication)
MAX_NODES = 200   # cap predicate AST size (bounds recursion on untrusted input)
MAX_TABLE_BOUND = 128  # ADR 0066: cap the bounded-definition tables (factorial/gcd If-chains)
MAX_ORDER = 64    # ADR 0035 Stage A: cap the multiplicative-order If-chain length (and the box
#   must cover a full period, so the order must also be <= the search bound — enforced per-call)

_ORDER_CACHE: dict[tuple[int, int], Optional[int]] = {}


class PredicateError(ValueError):
    """The predicate string is outside the safe, soundly-decidable DSL."""


def _multiplicative_order(base: int, m: int) -> Optional[int]:
    """The multiplicative order ord_m(base) = smallest k>0 with base^k ≡ 1 (mod m), or None when
    it does not exist (gcd(base, m) != 1, so base^n mod m is NOT purely periodic from n=0 — it has
    a transient, e.g. 2^n mod 4 = 1,2,0,0,…). Pure trial over k in [1, m-1] (ord | φ(m) ≤ m-1);
    cached. ADR 0035 Stage A — used only to drive an exact finite encoding; never a verdict."""
    key = (base % m, m) if m else (base, m)
    if key in _ORDER_CACHE:
        return _ORDER_CACHE[key]
    out: Optional[int] = None
    if m >= 2 and gcd(base, m) == 1:
        x = 1 % m
        for k in range(1, m):
            x = (x * base) % m
            if x == 1:
                out = k
                break
    _ORDER_CACHE[key] = out
    return out


def _order_reduction(mod_node: ast.AST, env: dict, bound: Optional[int]):
    """ADR 0035 Stage A: if `mod_node` is `base^n % m` (CONSTANT base, BARE-VARIABLE exponent,
    CONSTANT modulus), encode it EXACTLY over the multiplicative-order period as an `ord`-arm
    `If`-chain indexed by `n mod ord` — `ord` arms (typically 3–20), not the 64-arm chain that
    made ADR 0030 Tier B inert. Returns the Z3 residue expression, or None when the node is NOT
    that shape (the normal mod path then applies and DEFERs on the variable exponent).

    Exact-or-DEFER. When it IS the shape but cannot be soundly encoded, raise PredicateError
    (-> DEFER), never a wrong encoding:
      • gcd(base, m) != 1 -> not purely periodic (pre-period) -> DEFER;
      • the search box must cover a FULL PERIOD for 'UNSAT over the box' to be genuine, so
        ord must be <= the search `bound` (and <= MAX_ORDER) -> else DEFER. (A bare variable n
        ranges [0, bound]; with ord <= bound, n=0..ord-1 all lie in the box, so every residue in
        the cycle is reachable and an UNSAT is a real 'no witness anywhere'.)
    The base^k mod m sequence is purely periodic from k=0 with period ord when gcd(base,m)=1 (it
    lives in the unit group (ℤ/mℤ)*), so residues[k mod ord] == base^k mod m for ALL k>=0 —
    including the n=0 arm (residues[0] = base^0 mod m = 1)."""
    # Self-contained guard (defense-in-depth): only ever act on a real `_ % _` node. Today the
    # sole caller is the ast.Mod branch of _conv, so this is belt-and-suspenders — but a function
    # in the faithfulness encoding path must not depend on its caller for soundness.
    if not (isinstance(mod_node, ast.BinOp) and isinstance(mod_node.op, ast.Mod)):
        return None
    left = mod_node.left
    if not (isinstance(left, ast.BinOp) and isinstance(left.op, ast.Pow)):
        return None  # `ast.Pow` is the operator; the power node is a BinOp whose .op is ast.Pow
    base = _const_int(left.left)
    exp = left.right
    # Our shape iff CONSTANT base + BARE-variable exponent + CONSTANT modulus >= 2. A constant
    # exponent uses the normal Pow path; a compound exponent (2^(n+1)) or non-constant base/modulus
    # is NOT our shape -> return None -> normal mod path -> recurses into Pow -> DEFER.
    m = _const_int(mod_node.right)  # type: ignore[arg-type]
    if base is None or not isinstance(exp, ast.Name) or m is None or m < 2:
        return None
    # It IS base^n % m. From here every failure is a DEFER (raise), never a wrong encoding.
    ordv = _multiplicative_order(base, m)
    if ordv is None:
        raise PredicateError("base^n % m: needs gcd(base, m) == 1 (else a pre-period, not periodic)")
    if bound is None or ordv > bound or ordv > MAX_ORDER:
        raise PredicateError("base^n % m: order exceeds the search bound/cap (box must cover a period)")
    var = env.setdefault(exp.id, z3.Int(exp.id))
    residues = [pow(base, i, m) for i in range(ordv)]   # residues[0] = 1 (the n=0 arm), pinned
    idx = var % ordv
    out = z3.IntVal(residues[-1])
    for i in range(ordv - 2, -1, -1):
        out = z3.If(idx == i, z3.IntVal(residues[i]), out)
    return out


_CMP = {
    ast.Lt: lambda a, b: a < b,
    ast.LtE: lambda a, b: a <= b,
    ast.Gt: lambda a, b: a > b,
    ast.GtE: lambda a, b: a >= b,
    ast.Eq: lambda a, b: a == b,
    ast.NotEq: lambda a, b: a != b,
}


def _const_int(node: ast.AST) -> Optional[int]:
    """The int value if `node` is a non-negative integer literal, else None."""
    if isinstance(node, ast.Constant) and isinstance(node.value, int) and not isinstance(node.value, bool):
        return node.value
    return None


def _table_arg(node: ast.AST, env: dict, bound: Optional[int], fname: str):
    """ADR 0066: an argument a bounded-definition table can encode EXACTLY — a small non-negative
    CONSTANT, or a BARE variable (every solver query in this module boxes variables to [0, bound],
    the same assumption the ADR 0035 order-reduction rests on). Anything else — a compound argument
    like ``factorial(n+1)``, a missing bound — raises PredicateError (→ DEFER), never a wrong encoding."""
    c = _const_int(node)
    if c is not None:
        if c > MAX_TABLE_BOUND:
            raise PredicateError(f"{fname}: constant argument over MAX_TABLE_BOUND")
        return ("const", c)
    if isinstance(node, ast.Name):
        if bound is None or bound < 0 or bound > MAX_TABLE_BOUND:
            raise PredicateError(f"{fname}: no usable search bound (bounded definitional encoding)")
        return ("var", _conv(node, env, bound))
    raise PredicateError(f"{fname} needs a bare-variable or constant argument (bounded encoding)")


def _ite_table(v, values: list):
    """`values[k]` selected by ``v == k`` — exact for v ∈ [0, len(values)-1] (the boxed range)."""
    out = z3.IntVal(values[-1])
    for k in range(len(values) - 2, -1, -1):
        out = z3.If(v == k, z3.IntVal(values[k]), out)
    return out


def _conv(node: ast.AST, env: dict, bound: Optional[int] = None):
    """Compile an AST node to a Z3 expression over the integer variables in `env`
    (created on demand — multi-variable). Only soundly-encodable constructs are
    accepted; anything else raises PredicateError. `bound` is the search box bound, threaded
    through so the ADR 0035 order-reduction can require the box to cover a full period."""
    if isinstance(node, ast.BoolOp):
        vals = [_conv(v, env, bound) for v in node.values]
        return z3.And(*vals) if isinstance(node.op, ast.And) else z3.Or(*vals)
    if isinstance(node, ast.UnaryOp):
        if isinstance(node.op, ast.Not):
            return z3.Not(_conv(node.operand, env, bound))
        if isinstance(node.op, ast.USub):
            return -_conv(node.operand, env, bound)
        raise PredicateError(f"unary op {type(node.op).__name__}")
    if isinstance(node, ast.BinOp):
        op = node.op
        if isinstance(op, ast.Add):
            return _conv(node.left, env, bound) + _conv(node.right, env, bound)
        if isinstance(op, ast.Sub):
            return _conv(node.left, env, bound) - _conv(node.right, env, bound)
        if isinstance(op, ast.Mult):
            return _conv(node.left, env, bound) * _conv(node.right, env, bound)
        # `^` is rewritten to `**` before parsing, so only ast.Pow reaches here. Sound
        # only for a constant, small, non-negative exponent -> repeated multiplication.
        # (A VARIABLE exponent reaches here only OUTSIDE a `% m` context — unbounded, so DEFER;
        # the periodic `base^n % m` case is intercepted at the Mod node below, never here.)
        if isinstance(op, ast.Pow):
            k = _const_int(node.right)
            if k is None or k > MAX_POW:
                raise PredicateError("power needs a constant exponent in [0, MAX_POW]")
            base = _conv(node.left, env, bound)
            out = z3.IntVal(1)
            for _ in range(k):
                out = out * base
            return out
        # Floor division / modulo: only by a constant positive divisor.
        if isinstance(op, (ast.Div, ast.FloorDiv)):
            d = _const_int(node.right)
            if not d or d <= 0:
                raise PredicateError("division needs a constant positive divisor")
            return _conv(node.left, env, bound) / d
        if isinstance(op, ast.Mod):
            # ADR 0035 Stage A: `base^n % m` is encoded over its multiplicative-order period
            # (exact-or-DEFER); any other shape falls through to the normal constant-divisor mod.
            reduced = _order_reduction(node, env, bound)
            if reduced is not None:
                return reduced
            d = _const_int(node.right)
            if not d or d <= 0:
                raise PredicateError("modulo needs a constant positive divisor")
            return _conv(node.left, env, bound) % d
        raise PredicateError(f"bin op {type(op).__name__}")
    if isinstance(node, ast.Compare):
        terms = [_conv(node.left, env, bound), *[_conv(c, env, bound) for c in node.comparators]]
        clauses = []
        for i, op in enumerate(node.ops):
            fn = _CMP.get(type(op))
            if fn is None:
                raise PredicateError(f"compare op {type(op).__name__}")
            clauses.append(fn(terms[i], terms[i + 1]))
        return z3.And(*clauses) if len(clauses) > 1 else clauses[0]
    if isinstance(node, ast.Call):
        # ADR 0030 Tier A: a FIXED whitelist of pure, total, integer functions — only
        # min/max, which encode EXACTLY as nested z3.If (no bound interaction, sound for all
        # integers). Reject attribute calls (`Nat.min`), keyword/star args, and any other
        # name, so the `ast.Call` allowance opens no eval/import surface.
        if (not isinstance(node.func, ast.Name) or node.keywords
                or any(isinstance(a, ast.Starred) for a in node.args)):
            raise PredicateError("only whitelisted bare calls are allowed (min/max/factorial/gcd)")
        name = node.func.id
        # ADR 0066: factorial / gcd via bounded definitional encodings — EXACT over the box for
        # bare-variable/constant arguments (see _table_arg), else DEFER. DSL semantics are Python's
        # math.factorial / math.gcd on the boxed non-negative range.
        if name == "factorial" and len(node.args) == 1:
            kind, val = _table_arg(node.args[0], env, bound, "factorial")
            if kind == "const":
                return z3.IntVal(math.factorial(val))
            return _ite_table(val, [math.factorial(k) for k in range(bound + 1)])
        if name == "gcd" and len(node.args) == 2:
            (k0, v0), (k1, v1) = (_table_arg(a, env, bound, "gcd") for a in node.args)
            if k0 == "const" and k1 == "const":
                return z3.IntVal(math.gcd(v0, v1))
            if k0 == "const" or k1 == "const":
                c, var = (v0, v1) if k0 == "const" else (v1, v0)
                return _ite_table(var, [math.gcd(k, c) for k in range(bound + 1)])
            out = _ite_table(v1, [math.gcd(bound, k) for k in range(bound + 1)])
            for j in range(bound - 1, -1, -1):
                out = z3.If(v0 == j, _ite_table(v1, [math.gcd(j, k) for k in range(bound + 1)]), out)
            return out
        if name in ("min", "max") and len(node.args) >= 2:
            args = [_conv(a, env, bound) for a in node.args]
            pick = ((lambda x, y: z3.If(x < y, x, y)) if name == "min"
                    else (lambda x, y: z3.If(x > y, x, y)))
            out = args[0]
            for a in args[1:]:
                out = pick(out, a)
            return out
        raise PredicateError(f"unsupported call: {name}/{len(node.args)}")
    if isinstance(node, ast.Name):
        return env.setdefault(node.id, z3.Int(node.id))  # integer var, on demand
    val = _const_int(node)
    if val is not None:
        return val
    raise PredicateError(f"unsupported syntax: {type(node).__name__}")


def compile_pred(src: str, env=None, bound: Optional[int] = None):
    """Compile a DSL predicate into a Z3 BOOLEAN over the integer vars in `env`. The
    result must be boolean (a bare term like ``n + 1`` is rejected). `env=None` starts
    fresh; a bare Z3 var is accepted for the legacy single-`n` call shape. `bound` is the
    search box bound (threaded to the ADR 0035 order-reduction, which needs the box to cover a
    full period; when None, that reduction DEFERs, so behaviour is unchanged for bound-less callers)."""
    if env is None:
        env = {}
    elif not isinstance(env, dict):
        env = {VAR: env}  # legacy: compile_pred(src, z3.Int("n"))
    src = src.replace("^", "**")  # `^` means power here; give it exponentiation precedence
    try:
        tree = ast.parse(src, mode="eval")
    except (SyntaxError, ValueError) as e:
        raise PredicateError(str(e)) from e
    if sum(1 for _ in ast.walk(tree)) > MAX_NODES:
        raise PredicateError("predicate too large")
    result = _conv(tree.body, env, bound)
    if not isinstance(result, z3.BoolRef):
        raise PredicateError("predicate is not a boolean expression")
    return result


@dataclass
class Z3Backend:
    """Z3-backed SMTBackend. Only kills; never promotes."""

    default_bound: int = 64
    timeout_ms: int = 3000

    def _decide(self, preds: list[str], bound: int) -> tuple[str, Optional[dict]]:
        """Decide the conjunction of `preds` over the bounded box. Returns a status —
        'sat' (with model), 'unsat', 'unknown', or 'error' — so callers can tell a
        conclusive result from an undecided/un-encodable one. Any failure (un-encodable
        predicate, RecursionError on a deep parse, non-boolean, Z3 error) degrades to
        'error', never a crash and never a silent 'no witness'."""
        if z3 is None:
            return ("error", None)
        env: dict = {}
        try:
            # thread the search bound so the ADR 0035 order-reduction only fires when the box
            # covers a full period (ord <= bound) — else it DEFERs (exact-or-DEFER).
            exprs = [compile_pred(p, env, bound) for p in preds]
        except (PredicateError, RecursionError, z3.Z3Exception):
            # z3 raises a Z3Exception at CONSTRUCTION time for a non-boolean term fed to
            # And/Or/Not (e.g. "not n", "n and n>0"); treat it as un-encodable, never a
            # crash (matches this module's docstring contract).
            return ("error", None)
        try:
            solver = z3.Solver()
            solver.set("timeout", self.timeout_ms)
            for v in env.values():
                solver.add(v >= 0, v <= bound)
            for e in exprs:
                solver.add(e)
            res = solver.check()
        except (z3.Z3Exception, RecursionError):  # pragma: no cover
            return ("error", None)
        if res == z3.sat:
            m = solver.model()
            return ("sat", {name: (m[v].as_long() if m[v] is not None else 0) for name, v in env.items()})
        if res == z3.unsat:
            return ("unsat", None)
        return ("unknown", None)

    def encodable(self, pred: str) -> bool:
        """True iff `pred` compiles to a boolean in the sound DSL — so a None search
        result can be read as 'checked, no witness' rather than 'could not encode'."""
        if z3 is None:
            return False
        try:
            compile_pred(pred, bound=self.default_bound)  # match what _decide will search
            return True
        except (PredicateError, RecursionError, z3.Z3Exception):
            return False  # incl. a non-boolean term z3 rejects at construction time

    def decide_unsat(self, preds: list[str], bound: int = 0) -> Optional[bool]:
        """Tri-state: True iff the conjunction is conclusively UNSAT (no witness in
        the box), False iff SAT, None iff undecided/un-encodable. The faithfulness
        probe certifies only on a conclusive True — sat *or* None DEFERs."""
        status, _ = self._decide(preds, bound or self.default_bound)
        if status == "unsat":
            return True
        if status == "sat":
            return False
        return None

    def equivalent(self, p: str, q: str, bound: int = 0) -> Optional[bool]:
        """Tri-state predicate equivalence over the box (ADR 0031 Layer 2): True iff p and q
        agree at EVERY point (no witness where they differ), False iff they differ somewhere,
        None iff undecided/un-encodable. Used by the novelty gate to demote a restatement of a
        known result to KNOWN — but ONLY on a conclusive True (None/False stay NOVEL, so an
        un-encodable or undecided search never wrongly suppresses a genuine discovery). For
        bounded-modulus arithmetic the box spans a full period, so True is genuine equivalence.
        Variable names must match for two predicates to compare as the same n; a mismatch
        reads as SAT -> not equivalent -> conservatively NOVEL."""
        return self.decide_unsat([f"({p}) != ({q})"], bound or self.default_bound)

    # --- SMTBackend Protocol --------------------------------------------------
    def find_counterexample(self, claim: str, bound: int = 0) -> Optional[dict]:
        # Only a *conclusive* model kills (undecided/un-encodable -> no refutation).
        return self._decide([claim], bound or self.default_bound)[1]

    def find_gaming_witness(
        self, statement: str, negated_claim: str, bound: int = 0
    ) -> Optional[dict]:
        return self._decide([statement, negated_claim], bound or self.default_bound)[1]


def available() -> bool:
    """True iff z3 is importable (used to skip z3 tests where the extra is absent)."""
    return z3 is not None
