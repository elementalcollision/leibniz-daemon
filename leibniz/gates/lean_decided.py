"""ADR 0056 Track A increment 2 — the Lean-decided faithfulness backend.

The Lean **kernel** decides the faithfulness pair over ``established_domain`` for
multivariable modular-polynomial claims — the fragment Z3 returns *unknown* on
(``probes.py`` DEFERs) and the daemon's richer conjectures die in today.

Built to the seven build obligations recorded in ADR 0056 (§"Increment-1 re-review
outcome"), which the increment-2 re-review made binding:

1. **Gate-owned reduction, never proposer-emitted.** Every Lean statement AND every
   proof the kernel checks is constructed *here*, by gate-owned templates, from the
   three DSL contract strings. No backend/proposer ``proof_src`` is ever accepted.
   The reduction is the ZMod bridge (validated against the real Lean 4.31 kernel):
   a ``decide``-closed key lemma over ``ZMod m`` lifted to the unbounded ``∀ … : ℤ``
   statement via ``ZMod.intCast_eq_intCast_iff'`` + ``push_cast``. If the claim is
   false, the key lemma's ``decide`` refuses → the kernel rejects → **DEFER** — the
   kernel, not the template, is the decider.
2. **Pinned ``cert.data`` contract:** exactly the three builtin-``str`` DSL fields
   ``{claim_domain, claim_property, established_domain}`` — never a tool-supplied
   ``theorem_src``.
3. **The re-checker re-derives everything from ``cert.data``:** re-renders the four
   pair statements (``dsl_to_lean.faithfulness_pair``), re-constructs the gate-owned
   proofs, kernel-checks **all four**, and runs the shared ``axiom_closure``
   (``leibniz/backends/lean_axioms.py``) on each — rejecting ``sorryAx`` /
   ``Lean.ofReduceBool`` (``native_decide``) at faithfulness time.
4. **All four statements bound individually** inside one canonical statement string
   whose segments the re-checker re-renders and the gate compares — no single
   un-elaborable key with unproved segments: the re-checker proves each of coverage,
   property, ``∃ claim_domain`` and ``∃ established ∧ claim`` or returns False.
5. **Statement binding to the PROP** happens in ``FaithfulnessGate.check`` via the
   ``templates`` registry (this module's ``prop_statement_template``): the gate
   renders the canonical statement from ``prop``'s own fields and refuses a PASS
   whose certificate statement differs (builtin-``str``, ``str.__ne__`` — the
   registry E7 discipline, replicated on the gate's accept path).
6. **Robustness:** every render/classify step is total-or-DEFER; a ``RenderError``
   is a DEFER, never an escaping crash.
7. **Fragment guards:** the *reduction* fragment is strictly narrower than the
   *renderer* fragment — pure polynomial congruence skeletons only. ``min``/``max``
   and division are renderable but **not residue-periodic/bridgeable** (``min(a,b)%2``
   at ``(0,1)`` vs ``(2,1)`` — same residues, different truth), so they DEFER here.
   A residue budget caps ``m ** nvars``; a missing modulus DEFERs.

**Fail-closed by default.** Nothing imports or registers this module in the assembly.
Activation is an OPERATOR action: call :func:`register` on the constructed gate with a
kernel backend, after review — until then ``recheckers.get(kind)`` is ``None`` and no
PASS of this kind is ever accepted (``faithfulness.py`` accept path).

Supported property skeletons (all validated against the real kernel; everything else
DEFERs):
- ``poly % m != c``                       (e.g. ``(a*a + b*b) % 4 != 3``)
- ``poly % m == c``                       (e.g. ``(a*b*(a*a - b*b)) % 6 == 0``)
- ``poly % m == c₁ or … or poly % m == cₖ`` (residue set, same poly and m)
where ``poly`` is a pure polynomial (``+ - *``, constant ``^``, unary minus) over the
claim's variables.
"""
from __future__ import annotations

import ast
import hashlib
import itertools
from dataclasses import dataclass
from typing import Callable, Optional

from leibniz.backends.lean_axioms import axiom_closure
from leibniz.backends.smt_z3 import MAX_POW
from leibniz.dsl_to_lean import (
    RenderError,
    _parse,
    _term,
    canonical_statement,
    faithfulness_pair,
    free_vars,
)
from leibniz.gates.sound_backends import Certificate, FaithfulnessVerdict
from leibniz.propositio import Propositio
from leibniz.types import Verdict

KIND = "lean-decided-faithfulness"
IMPORTS = ("Mathlib.Tactic",)
# Residue budget: the ZMod key lemma's `decide` enumerates m ** nvars cells in the kernel.
MAX_RESIDUE_CELLS = 4096
# Witness search box (proposal-side; the kernel checks the concrete instance).
WITNESS_RANGE = 21
MIN_VARS, MAX_VARS = 2, 3   # 1-var claims stay on the cheap Z3 probe (invariant 5)


# --- property-skeleton classification --------------------------------------------------------


@dataclass(frozen=True)
class Skeleton:
    """A classified claim_property: `poly % m ⋈ {cs}` with op ∈ {'eq','neq','residue_set'}."""

    op: str                 # 'eq' | 'neq' | 'residue_set'
    poly_src: ast.AST       # the pure-polynomial AST (shared across disjuncts)
    modulus: int
    residues: tuple[int, ...]   # one value for eq/neq; the set for residue_set


def _is_pure_poly(node: ast.AST) -> bool:
    """Pure polynomial: vars/consts, + - *, constant ^, unary minus. NO mod/div/min/max —
    those are renderable but not ZMod-bridgeable (obligation 7)."""
    if isinstance(node, ast.Name):
        return True
    if isinstance(node, ast.Constant):
        return isinstance(node.value, int) and not isinstance(node.value, bool)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        return _is_pure_poly(node.operand)
    if isinstance(node, ast.BinOp):
        if isinstance(node.op, (ast.Add, ast.Sub, ast.Mult)):
            return _is_pure_poly(node.left) and _is_pure_poly(node.right)
        if isinstance(node.op, ast.Pow):
            # Bound the exponent by MAX_POW so `_term` (which enforces the same cap) can never raise
            # on a poly `_is_pure_poly` accepted — keeps decide_certificate total-or-DEFER even if a
            # future refactor reaches `property_proof`'s `_term` before `faithfulness_pair` renders.
            return (_is_pure_poly(node.left) and isinstance(node.right, ast.Constant)
                    and isinstance(node.right.value, int) and 0 <= node.right.value <= MAX_POW)
    return False


def _const(node: ast.AST) -> Optional[int]:
    if isinstance(node, ast.Constant) and isinstance(node.value, int) and not isinstance(node.value, bool):
        return node.value
    return None


def _atom(node: ast.AST) -> Optional[tuple[str, ast.AST, int, int]]:
    """`(poly % m) ⋈ c` with ⋈ ∈ {==, !=} → (op, poly, m, c); else None."""
    if not (isinstance(node, ast.Compare) and len(node.ops) == 1 and len(node.comparators) == 1):
        return None
    left, cmp_op, right = node.left, node.ops[0], node.comparators[0]
    if not (isinstance(left, ast.BinOp) and isinstance(left.op, ast.Mod)):
        return None
    m, c = _const(left.right), _const(right)
    if m is None or m < 2 or c is None or not _is_pure_poly(left.left):
        return None
    # STATIC residue-range guard (code-review hardening): a residue outside [0, m) is degenerate —
    # for `eq`/`residue_set` the ZMod key can be vacuously true (e.g. `poly % 2 == 2`: 2 ≡ 0 in
    # ZMod 2) while the ℤ statement `Int.emod poly m = c` is FALSE. Today the eq/residue bridge's
    # `simpa` step fails on such a `c` → DEFER, but that makes soundness depend on tactic behavior in
    # the pinned image. Rejecting `c ∉ [0, m)` here moves the guard to classification, so no skeleton
    # with an out-of-range residue is ever built. (`neq` with `c ≥ m` is trivially true, not unsound,
    # but is likewise degenerate — reject uniformly.)
    if not (0 <= c < m):
        return None
    if isinstance(cmp_op, ast.Eq):
        return ("eq", left.left, m, c)
    if isinstance(cmp_op, ast.NotEq):
        return ("neq", left.left, m, c)
    return None


def classify_property(claim_property: str) -> Optional[Skeleton]:
    """Classify `claim_property` into a supported skeleton, or None (→ DEFER)."""
    try:
        tree = _parse(claim_property)
    except RenderError:
        return None
    a = _atom(tree)
    if a is not None:
        op, poly, m, c = a
        return Skeleton(op=op, poly_src=poly, modulus=m, residues=(c,))
    if isinstance(tree, ast.BoolOp) and isinstance(tree.op, ast.Or):
        atoms = [_atom(v) for v in tree.values]
        if any(x is None or x[0] != "eq" for x in atoms):
            return None
        polys = {ast.dump(x[1]) for x in atoms}
        moduli = {x[2] for x in atoms}
        if len(polys) != 1 or len(moduli) != 1:
            return None    # residue set must share one poly and one modulus
        return Skeleton(op="residue_set", poly_src=atoms[0][1],
                        modulus=atoms[0][2], residues=tuple(x[3] for x in atoms))
    return None


# --- gate-owned proof construction (templates validated against the real Lean 4.31 kernel) ---


def _casts(vs: list[str], m: int) -> str:
    return " ".join(f"(({v} : ℤ) : ZMod {m})" for v in vs)


def _key_lemma(skel: Skeleton, vs: list[str]) -> str:
    """The `decide`-closed ZMod key: the whole skeleton over `ZMod m`. This is where the
    KERNEL decides the mathematics — a false skeleton makes `decide` refuse → DEFER."""
    poly = _term(skel.poly_src)
    binder = " ".join(vs)
    if skel.op == "neq":
        body = f"{poly} ≠ {skel.residues[0]}"
    elif skel.op == "eq":
        body = f"{poly} = {skel.residues[0]}"
    else:
        body = " ∨ ".join(f"{poly} = {c}" for c in skel.residues)
    return f"∀ ({binder} : ZMod {skel.modulus}), {body}"


def _or_nest(i: int, k: int, inner: str) -> str:
    """The Or-constructor spine selecting disjunct i of a right-associated k-disjunction:
    `A₀ ∨ (A₁ ∨ …)` — disjunct i<k-1 is `Or.inr^i (Or.inl …)`, the last is `Or.inr^(k-1) …`."""
    if k == 1:
        return inner
    out = inner if i == k - 1 else f"Or.inl ({inner})"
    for _ in range(i):
        out = f"Or.inr ({out})"
    return out


def property_proof(skel: Skeleton, vs: list[str]) -> str:
    """A gate-owned proof of the pair's PROPERTY statement
    (`∀ vars, box → established → claim_domain → claim_property`), via the ZMod bridge.
    Introduces the two domain antecedents as `_` and proves the property outright (the
    stronger claim) — sound: if the property is not universally true over the box, the
    key lemma's `decide` refuses → the kernel rejects → DEFER (yield loss, never
    unsoundness)."""
    poly = _term(skel.poly_src)
    m = skel.modulus
    intro_all = " ".join(vs) + " " + " ".join(f"_h{v}" for v in vs) + " _ _"
    key = _key_lemma(skel, vs)
    casts = _casts(vs, m)
    if skel.op == "neq":
        c = skel.residues[0]
        return f"""by
  have key : {key} := by decide
  intro {intro_all} h
  have h' : {poly} % {m} = {c} := h
  apply key {casts}
  have hz : (({poly} : ℤ) : ZMod {m}) = (({c} : ℤ) : ZMod {m}) := by
    rw [ZMod.intCast_eq_intCast_iff']
    simpa using h'
  push_cast at hz
  exact hz"""
    if skel.op == "eq":
        c = skel.residues[0]
        return f"""by
  have key : {key} := by decide
  intro {intro_all}
  have hk := key {casts}
  have hz : (({poly} : ℤ) : ZMod {m}) = (({c} : ℤ) : ZMod {m}) := by
    push_cast
    exact hk
  rw [ZMod.intCast_eq_intCast_iff'] at hz
  have h' : {poly} % {m} = {c} := by simpa using hz
  exact h'"""
    # residue_set: rcases the ZMod key instance, bridge each branch back to a `% m = c` fact,
    # then select its disjunct in the goal.
    k = len(skel.residues)
    rcases_pat = " | ".join(["h"] * k)
    blocks = []
    for i, c in enumerate(skel.residues):
        select = _or_nest(i, k, "h'")
        blocks.append(
            f"  · have hz : (({poly} : ℤ) : ZMod {m}) = (({c} : ℤ) : ZMod {m}) := by\n"
            f"      push_cast\n"
            f"      exact h\n"
            f"    rw [ZMod.intCast_eq_intCast_iff'] at hz\n"
            f"    have h' : {poly} % {m} = {c} := by simpa using hz\n"
            f"    exact {select}"
        )
    return (f"by\n  have key : {key} := by decide\n  intro {intro_all}\n"
            f"  have hk := key {casts}\n  rcases hk with {rcases_pat}\n" + "\n".join(blocks))


def coverage_proofs(nvars: int) -> list[str]:
    """The gate-owned tactic ladder for the COVERAGE statement
    (`∀ vars, box → claim_domain → established_domain`). Tried in order; none accepted
    by the kernel → DEFER. `omega` handles the linear/modular-by-literal domain logic."""
    intro = " ".join(f"v{i}" for i in range(nvars)) + " " + " ".join(f"b{i}" for i in range(nvars)) + " h"
    return [f"by intro {intro}; exact h", f"by intro {intro}; omega"]


def _eval_pred(node: ast.AST, asn: dict) -> object:
    """Proposal-side DSL evaluator for the ∃-witness search (Euclidean % and // — matches
    Z3/Lean). Untrusted by construction: the kernel checks the concrete witness instance."""
    if isinstance(node, ast.BoolOp):
        vals = [_eval_pred(v, asn) for v in node.values]
        return all(vals) if isinstance(node.op, ast.And) else any(vals)
    if isinstance(node, ast.UnaryOp):
        if isinstance(node.op, ast.Not):
            return not _eval_pred(node.operand, asn)
        return -_eval_pred(node.operand, asn)
    if isinstance(node, ast.BinOp):
        a, b = _eval_pred(node.left, asn), _eval_pred(node.right, asn)
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
            return a // b
        if isinstance(op, ast.Mod):
            return a % b
        raise RenderError("op")
    if isinstance(node, ast.Compare):
        left, ok = _eval_pred(node.left, asn), True
        for op, comp in zip(node.ops, node.comparators):
            right = _eval_pred(comp, asn)
            ok = ok and {ast.Lt: left < right, ast.LtE: left <= right, ast.Gt: left > right,
                         ast.GtE: left >= right, ast.Eq: left == right,
                         ast.NotEq: left != right}[type(op)]
            left = right
        return ok
    if isinstance(node, ast.Call):
        args = [_eval_pred(a, asn) for a in node.args]
        return min(args) if node.func.id == "min" else max(args)
    if isinstance(node, ast.Name):
        return asn[node.id]
    if isinstance(node, ast.Constant):
        return node.value
    raise RenderError("node")


def find_witness(pred_srcs: list[str], vs: list[str]) -> Optional[tuple[int, ...]]:
    """A non-negative grid point satisfying ALL `pred_srcs`, or None. Proposal-side."""
    try:
        trees = [_parse(p) for p in pred_srcs]
    except RenderError:
        return None
    for point in itertools.product(range(WITNESS_RANGE), repeat=len(vs)):
        asn = dict(zip(vs, point))
        try:
            if all(_eval_pred(t, asn) for t in trees):
                return point
        except (RenderError, KeyError, ZeroDivisionError):
            continue   # a per-point evaluation surprise skips that point, never aborts the search
    return None


def witness_proof(point: tuple[int, ...]) -> list[str]:
    """Proof ladder for an ∃-statement at a concrete witness (kernel checks the instance)."""
    ws = ", ".join(str(w) for w in point)
    return [f"⟨{ws}, by decide⟩", f"⟨{ws}, by norm_num⟩"]


# --- the gate-owned decision (used identically by the backend AND the re-checker) -------------


def _thm(name_seed: str, idx: str, statement: str) -> str:
    h = hashlib.sha256(name_seed.encode()).hexdigest()[:12]
    return f"theorem ld_{idx}_{h} : {statement}"


def decide_certificate(data: object, kernel) -> tuple[bool, dict]:
    """Decide the faithfulness pair for `data` = {claim_domain, claim_property,
    established_domain} by constructing all four statements AND their proofs (gate-owned)
    and requiring the KERNEL to accept each, plus a clean axiom footprint on each
    (no sorryAx / Lean.ofReduceBool). Exact-or-DEFER; total (never raises)."""
    if not (isinstance(data, dict) and set(data) == {"claim_domain", "claim_property", "established_domain"}
            and all(type(data[k]) is str for k in data)):
        return False, {"reason": "cert.data is not the pinned three-string contract"}
    cd, cp, ed = data["claim_domain"], data["claim_property"], data["established_domain"]
    try:
        pair = faithfulness_pair(cd, cp, ed)
        vs = free_vars(cd, cp, ed)
        seed = canonical_statement(cd, cp, ed)
    except RenderError as e:
        return False, {"reason": f"render: {e}"}
    if not (MIN_VARS <= len(vs) <= MAX_VARS):
        return False, {"reason": f"nvars {len(vs)} outside [{MIN_VARS},{MAX_VARS}]"}
    skel = classify_property(cp)
    if skel is None:
        return False, {"reason": "claim_property outside the reducible skeleton fragment"}
    if skel.modulus ** len(vs) > MAX_RESIDUE_CELLS:
        return False, {"reason": "residue budget exceeded"}

    # ∃-witness legs (vacuity control): no witness → no positive content → DEFER.
    w_claim = find_witness([cd], vs)
    w_ec = find_witness([ed, cd], vs)
    if w_claim is None or w_ec is None:
        return False, {"reason": "no ∃-witness found (empty or out-of-box domain)"}

    checks: list[tuple[str, str, list[str]]] = [
        ("coverage", pair["coverage"], coverage_proofs(len(vs))),
        ("property", pair["property"], [property_proof(skel, vs)]),
        ("exists_claim", pair["exists_claim"], witness_proof(w_claim)),
        ("exists_ec", pair["exists_ec"], witness_proof(w_ec)),
    ]
    from leibniz.propositio import Expressio  # local: avoid cycles at import time
    detail: dict = {"witness_claim": w_claim, "witness_ec": w_ec}
    for name, statement, ladder in checks:
        thm = _thm(seed, name, statement)
        ok_proof = None
        for proof in ladder:
            if kernel.check_proof(Expressio(theorem_src=thm, imports=IMPORTS), proof):
                ok_proof = proof
                break
        if ok_proof is None:
            return False, {"reason": f"kernel did not accept {name}", **detail}
        ax = axiom_closure(kernel, thm, ok_proof, IMPORTS)
        if not ax.get("ok"):
            return False, {"reason": f"axiom footprint on {name}: {ax}", **detail}
        detail[name] = {"axioms": ax.get("axioms", [])}
    return True, detail


# --- the SoundFaithfulnessBackend + gate-side re-checker/template ------------------------------


def prop_statement_template(prop: Propositio) -> Optional[str]:
    """The canonical statement rendered from PROP'S OWN fields (never from the certificate).
    The gate compares this to the certificate's claimed statement before any re-check —
    binding the certificate to this claim (obligation 5). None → unbindable → no PASS."""
    en, ex = prop.enuntiatio, prop.expressio
    if en is None or ex is None or not (en.claim_domain and en.claim_property and ex.established_domain):
        return None
    try:
        return canonical_statement(en.claim_domain, en.claim_property, ex.established_domain)
    except RenderError:
        return None


@dataclass
class LeanDecidedFaithfulness:
    """SoundFaithfulnessBackend: multivariable modular-polynomial claims, kernel-decided."""

    kernel: object
    name: str = "lean-decided"
    cost_rank: int = 90        # most expensive backend: runs after every cheaper one

    def applies(self, prop: Propositio) -> bool:
        en, ex = prop.enuntiatio, prop.expressio
        if en is None or ex is None or not (en.claim_domain and en.claim_property and ex.established_domain):
            return False
        try:
            vs = free_vars(en.claim_domain, en.claim_property, ex.established_domain)
            faithfulness_pair(en.claim_domain, en.claim_property, ex.established_domain)
        except RenderError:
            return False
        if not (MIN_VARS <= len(vs) <= MAX_VARS):
            return False        # 1-var stays on the cheap Z3 probe (invariant 5)
        skel = classify_property(en.claim_property)
        return skel is not None and skel.modulus ** len(vs) <= MAX_RESIDUE_CELLS

    def check(self, prop: Propositio) -> FaithfulnessVerdict:
        en, ex = prop.enuntiatio, prop.expressio
        data = {"claim_domain": en.claim_domain, "claim_property": en.claim_property,
                "established_domain": ex.established_domain}
        ok, detail = decide_certificate(data, self.kernel)
        if not ok:
            return FaithfulnessVerdict(verdict=Verdict.DEFER, producer="lean_decided/defer",
                                       detail=detail)
        statement = canonical_statement(**data)
        cert = Certificate(kind=KIND, rechecked=True, data=data, detail={"statement": statement})
        return FaithfulnessVerdict(verdict=Verdict.PASS, producer="lean_decided/kernel",
                                   certificate=cert, detail=detail)


def make_rechecker(kernel) -> Callable[[Certificate], bool]:
    """The gate's independent re-checker for this kind: re-derives EVERYTHING from
    cert.data with gate-owned code (statements, proofs, kernel checks, axiom closure) and
    replicates the E7 statement pin (template(cert.data) == claimed, builtin-str,
    str.__ne__). Total: any surprise is False, never an exception."""

    def recheck(cert: Certificate) -> bool:
        try:
            data = cert.data
            if not (isinstance(data, dict)
                    and set(data) == {"claim_domain", "claim_property", "established_domain"}
                    and all(type(data[k]) is str for k in data)):
                return False
            claimed = (cert.detail or {}).get("statement")
            if type(claimed) is not str:
                return False
            rendered = canonical_statement(**data)
            if type(rendered) is not str or str.__ne__(rendered, claimed):
                return False
            ok, _ = decide_certificate(data, kernel)
            return ok
        except Exception:
            return False

    return recheck


def register(gate, kernel) -> None:
    """OPERATOR ACTION (not called anywhere in the assembly): activate this kind on a
    constructed FaithfulnessGate. Until called, the fail-closed default holds — no PASS of
    this kind is ever accepted."""
    gate.sound_backends = tuple(gate.sound_backends) + (LeanDecidedFaithfulness(kernel=kernel),)
    gate.recheckers[KIND] = make_rechecker(kernel)
    gate.templates[KIND] = prop_statement_template
