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

LOOSE PHRASINGS (ADR 0032 follow-up — phrasing-independent by COMPUTED residues): a restatement
that dodges the tight `P % m == r` shape used to slip through (false-NOVEL). Three additional
predicate SHAPES now canonicalize onto the SAME signature space, keyed on the polynomial's FORM
plus its ACTUAL residue set — never on the asserted set, never on truth:
  • set-membership `P % m in {r1, r2, …}` / `not in {…}` (also `(…)`, `[…]`);
  • `or`-disjunctions of `P % m == c` over one common `P` and `m`;
and the already-recognized `!=` form. For these, the residues the author *asserted* are
DISCARDED; we recompute `R = { P(n) % m : n in [0, m-1] }`. That set is EXACT, not bounded-
approximate: an integer polynomial is periodic mod m with period m (`P(n+m) ≡ P(n)`), so one
period yields the complete residue set. (If `m` exceeds the enumeration bound `RESIDUE_BOUND`,
R could be incomplete → we return None → NOVEL, never a wrong canonicalization.) When R is a
SINGLETON `{r}` the claim *is* the congruence `P ≡ r (mod m)`, so it folds onto the existing
`== r` / `!= r` signature — that is why loose `P % m ∈ {0,4}` with actual residues `{0}` matches
a corpus `P % m == 0`. When R has >1 residue the claim is a genuine multi-residue statement and
gets a DISTINCT, relop-tagged signature `('in'/'not in', m, normalize(P), frozenset(R))` that can
never collide with a singleton `==` form. This is purely structural: R is a *coarser* coordinate
than the reduced polynomial (which already determines the residue function), so adding it can only
SPLIT signature classes finer — it can NEVER merge two distinct polynomials. (See ADR 0032's
soundness argument and the L2-retraction note in ADR 0031.)

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
RESIDUE_BOUND = 64  # box [0, RESIDUE_BOUND] for residue enumeration (ADR 0021's default bound).
#   A polynomial is periodic mod m with period m, so [0, m-1] already gives the COMPLETE residue
#   set; with m <= RESIDUE_BOUND+1 the computed R is EXACT. For m > RESIDUE_BOUND+1 we cannot be
#   sure R is complete -> return None (fail toward NOVEL) rather than risk a wrong canonicalization.


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


def _residue_set(poly: dict, m: int) -> Optional[frozenset]:
    """The EXACT set of residues `{ P(n) % m : n ∈ ℤ }` for the integer polynomial `poly`.

    An integer polynomial is periodic mod m with period m (`P(n+m) ≡ P(n) (mod m)`, since
    `(n+m)^k ≡ n^k (mod m)`), so enumerating one full period `[0, m-1]` yields the COMPLETE
    residue set — this is exact, not bounded-approximate. We only enumerate when `m <=
    RESIDUE_BOUND + 1`; for a larger modulus the box would not cover a full period, so we
    return None and let the caller fail toward NOVEL rather than canonicalize on an incomplete
    set. Multivariate polynomials (several variables) are also returned as None here: the
    residue *set* of a multivariate polynomial would need a product enumeration we do not do;
    the loose-shape canonicalization is single-variable only (a conservative miss, never wrong).

    Truth is never consulted — this enumerates the polynomial's FORM (its values mod m), the
    same posture as ADR 0021's bounded box, but here the box is a full period so the set is
    complete."""
    if m > RESIDUE_BOUND + 1:
        return None
    # require a single variable name so n ranges over one axis; the constant poly has no vars.
    names = {name for mono in poly for name, _ in mono}
    if len(names) > 1:
        return None
    var = next(iter(names)) if names else None

    def _eval(n: int) -> int:
        total = 0
        for mono, c in poly.items():
            term = c
            for _, e in mono:  # single var (or none): exponent on `var`
                term *= n ** e
            total += term
        return total % m

    if var is None:                       # constant polynomial -> single residue
        return frozenset({_eval(0)})
    return frozenset(_eval(n) for n in range(m))   # one full period = exact residue set


def _residues_from_node(elts, m: int) -> Optional[frozenset]:
    """Collect the constant integer residues asserted by a set/tuple/list literal, each reduced
    into `[0, m)`. Any non-constant or non-int element -> None (unrecognized -> NOVEL). NOTE: the
    asserted residues are used ONLY to recognize the shape; the SIGNATURE keys on the COMPUTED
    residue set, never on this asserted set (so phrasing is irrelevant)."""
    out = set()
    for e in elts:
        c = _const_int(e)
        if c is None:
            return None
        out.add(c % m)
    return frozenset(out)


def _membership_signature(pnode: ast.AST, m: int, negate: bool) -> Optional[tuple]:
    """Canonicalize a set-membership / disjunction claim `P % m ∈ R` (or its negation) to a
    signature keyed on the polynomial FORM and the COMPUTED residue set R. Single-variable only.

    • If the COMPUTED R is a singleton `{r}` the claim is exactly `P ≡ r (mod m)` (or `!≡` when
      negated), so we fold onto the EXISTING `== r` / `!= r` signature `(relop, m, normalize(P-r))`
      — making a loose `∈{…}` restatement match a tight `== r` corpus entry. The fold reuses the
      full `_normalize` (incl. prime-m monic step): `c·P ≡ 0` ⟺ `P ≡ 0` for a unit `c`, so
      unit-multiples of the SAME congruence collapse — exactly the tested `==`-shape behavior.
    • Otherwise the claim is a genuine multi-residue statement; we emit a DISTINCT, relop-tagged
      signature `('in'/'not in', m, coeffs-mod-m of P, frozenset(R))`. Here we DELIBERATELY do NOT
      apply the monic unit step: for a membership claim the residue at each point matters, so `2·P`
      and `P` are NOT interchangeable (they have different value-maps, even though their zero sets
      agree). Monic-normalizing here would collapse `2*n^2 % 7 ∈ {…}` onto `n^2 % 7 ∈ {…}` — two
      polynomials whose residue SETS coincide but whose facts differ — a false-KNOWN. So the
      multi-residue key reduces coefficients mod m ONLY (exact in ℤ/mℤ), keeping distinct
      polynomials distinct. The `'in'/'not in'` tag also never collides with the `'=='/'!='`
      singleton form."""
    state = {"vars": set()}
    try:
        poly = _expand(pnode, state)
    except _NotPoly:
        return None
    if len(state["vars"]) > 1:            # multivariate residue set not enumerated -> NOVEL
        return None
    R = _residue_set(poly, m)
    if R is None:                         # modulus too large for an exact period -> NOVEL
        return None
    if len(R) == 1:
        r = next(iter(R))
        relop = "!=" if negate else "=="
        diff = _add(poly, {(): -r})
        return (relop, m, _normalize(diff, m, single_var=True))
    relop = "not in" if negate else "in"
    # coefficient reduction mod m ONLY (NO monic unit step — see docstring): exact in ℤ/mℤ, and
    # keeps 2*P distinct from P, so distinct polynomials never collide in the multi-residue key.
    reduced = tuple(sorted((_mono_degree(mono), c % m) for mono, c in poly.items() if c % m != 0))
    return (relop, m, reduced, R)


def _disjunction_residues(node: ast.BoolOp):
    """If `node` is `(P % m == c1) or (P % m == c2) or …` over ONE common polynomial `P` and
    modulus `m` (each disjunct a `P % m == const`, same `P` source text, same `m`), return
    `(P_ast, m, negate=False)` for membership canonicalization; else None. A heterogeneous or
    non-`==` disjunct -> None (unrecognized -> NOVEL)."""
    if not isinstance(node.op, ast.Or):
        return None
    p_src = None
    mod = None
    pnode = None
    for v in node.values:
        if not (isinstance(v, ast.Compare) and len(v.ops) == 1 and isinstance(v.ops[0], ast.Eq)):
            return None
        lm = _mod(v.left)
        if lm is None:
            return None
        c = _const_int(v.comparators[0])
        if c is None:
            return None
        src = ast.dump(lm[0])             # structural identity of the polynomial term across disjuncts
        if p_src is None:
            p_src, mod, pnode = src, lm[1], lm[0]
        elif src != p_src or lm[1] != mod:
            return None                   # different P or different m across disjuncts -> reject
    if pnode is None or mod is None:
        return None
    return (pnode, mod)


def congruence_signature(predicate: Optional[str]) -> Optional[tuple]:
    """Canonical signature of a polynomial congruence DSL predicate, or None.

    Recognized SOUND shapes only:
      • `P % m <relop> c`        (relop ∈ {==, !=}) with c an integer residue 0 ≤ c < m
      • `P % m <relop> Q % m`    (both sides reduced by the SAME modulus)
      • `P % m in {r1, …}` / `not in {…}`   (also `(…)` / `[…]`) — single-variable P
      • `(P % m == c1) or (P % m == c2) or …` over ONE common P and m — single-variable P
    where P, P1, P2 are integer polynomials in the DSL's `+ - *` / constant `^` over one or
    more LITERAL variable names. Everything else — a raw (non-reduced) RHS, two different moduli,
    a non-polynomial term, an inequality `<`/`>`, a non-congruence — returns None (→ stays NOVEL).

    The set-membership and disjunction shapes are PHRASING-INDEPENDENT: they key on the
    polynomial's reduced FORM plus its COMPUTED residue set (`{P(n) % m}`, exact over one period),
    NOT on the residues the author asserted. A singleton computed residue folds onto the existing
    `== r` / `!= r` signature (so `P % m ∈ {0,4}` with actual residues `{0}` matches a corpus
    `P % m == 0`); a multi-residue set yields a distinct `'in'/'not in'`-tagged signature. See the
    module docstring and ADR 0032 for the soundness argument (no false-KNOWN).

    Single-variable claims produce the legacy univariate signature (with prime-m unit
    normalization); multivariate `==`/`!=` claims produce a monomial-keyed signature with NO
    renaming and NO unit normalization (conservative: never a false-KNOWN, only missed matches)."""
    if not predicate:
        return None
    try:
        tree = ast.parse(predicate.replace("^", "**"), mode="eval").body
    except (SyntaxError, ValueError):
        return None
    if sum(1 for _ in ast.walk(tree)) > MAX_NODES:
        return None
    # `or`-disjunction of `P % m == c` clauses -> membership canonicalization (computed residues).
    if isinstance(tree, ast.BoolOp):
        dj = _disjunction_residues(tree)
        if dj is None:
            return None
        pnode, m = dj
        if m < 2:
            return None
        return _membership_signature(pnode, m, negate=False)
    if not (isinstance(tree, ast.Compare) and len(tree.ops) == 1):
        return None
    # set-membership `P % m in {…}` / `not in {…}` -> membership canonicalization.
    memop = {ast.In: False, ast.NotIn: True}.get(type(tree.ops[0]))
    if memop is not None:
        lm = _mod(tree.left)
        if lm is None:
            return None
        pnode, m = lm
        if m < 2:
            return None
        comp = tree.comparators[0]
        if not isinstance(comp, (ast.Set, ast.Tuple, ast.List)):
            return None
        asserted = _residues_from_node(comp.elts, m)
        if asserted is None or not asserted:   # non-constant element or empty literal -> NOVEL
            return None
        return _membership_signature(pnode, m, negate=memop)
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
