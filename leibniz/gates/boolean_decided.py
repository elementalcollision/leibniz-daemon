"""ADR 0059 (biconditional path) — the ZMod-decide faithfulness backend for same-modulus boolean
combinations of modular atoms.

The third decision procedure of the ceiling-raiser, generalising `lean_decided` (which handles a single
atom / residue-set / conjunction) to an **arbitrary boolean combination** — `∧`, `∨`, `¬`, and
**biconditionals `↔`** — of eq/neq modular atoms **sharing one modulus `m`**, over nonlinear
polynomials. E.g. `(a²%5=1) ↔ (a%5=1 ∨ a%5=4)`, `(a·b)%3=0 ↔ (a%3=0 ∨ b%3=0)`. The Lean **kernel**
decides the whole boolean formula over `ZMod m` by `decide` (finite), and a uniform per-atom bridge
lifts it to the ℤ statement; a **false** formula makes the `decide` refuse ⇒ DEFER — the kernel decides.

How the proof works (validated against the real Lean 4.31 kernel):

1. `have key : ∀ (vars : ZMod m), Q_zmod := by decide` — `Q_zmod` is the claim's boolean structure with
   each atom `poly % m ⋈ c` replaced by `poly(vars) ⋈ c` over `ZMod m` (`decide` is the decider).
2. Per DISTINCT atom `(poly, c)`: `have hbᵢ : (Int.emod poly m = c) ↔ ((↑poly : ZMod m) = ↑c)`, proved
   `rw [ZMod.intCast_eq_intCast_iff']; show (poly % m = c) ↔ (poly % m = c % m); omega`. The `Int.emod`
   LHS matches the DSL-rendered goal; the `show` converts to `%` (defeq) so `omega` — which groks `%`,
   not raw `Int.emod` — can finish.
3. `rw [hb₀, …]` rewrites every atom (eq AND neq — `rw` rewrites the eq subterm inside `¬`), `push_cast`
   turns `↑(poly)` into `poly(↑vars)`, and `exact key vars` discharges the (now ZMod) goal.

Fragment restriction (owned at the classifier — the renderer is more permissive):
- single shared modulus `m` (mixed moduli ⇒ DEFER; that needs the LCM/castHom machinery, a later increment);
- every atom `poly % m == c` / `!= c` with `poly` a pure polynomial and `0 ≤ c < m` (reuses `lean_decided._atom`);
- boolean structure of `and`/`or`/`not`/biconditional only; comparisons other than `==`/`!=` ⇒ DEFER;
- `MIN_VARS ≤ nvars ≤ MAX_VARS`, `m ** nvars ≤ MAX_RESIDUE_CELLS`, `≤ MAX_ATOMS` atoms.

Disjoint-by-construction from `lean_decided`: `classify_boolean` declines anything `lean_decided`'s
`classify_property` already owns (bare atom / single-poly residue-set / plain conjunction), so this
backend fires ONLY for the richer boolean shapes (biconditionals, `∨` of different polys, `¬`, nested
mixes). A **non-triviality** guard additionally DEFERs propositional tautologies/contradictions (`P↔P`,
`P∨¬P`) — content-free non-results the modular `decide` would otherwise certify.

**Fail-closed by default.** Nothing registers this module in the assembly. Activation is an OPERATOR
action (`register`, gated in `assembly.maybe_register_boolean_decided` behind the same
`LEIBNIZ_LEAN_DECIDED` REPL activation); until then `recheckers.get(KIND)` is `None` and no PASS of this
kind is accepted. The producer `boolean_modular/kernel` is admitted to `FAITHFULNESS_PRODUCERS` by the
operator (ADR 0041), like the other decision-procedure producers.
"""
from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from typing import Callable, Optional

from leibniz.backends.lean_axioms import axiom_closure
from leibniz.dsl_to_lean import (
    RenderError,
    _is_bool_node,
    _parse,
    _term,
    canonical_statement,
    faithfulness_pair,
    free_vars,
)
from leibniz.gates.lean_decided import (
    IMPORTS,
    MAX_RESIDUE_CELLS,
    MAX_VARS,
    MIN_VARS,
    _atom,
    _thm,
    classify_property,
    coverage_proofs,
    find_witness,
    witness_proof,
)
from leibniz.gates.sound_backends import Certificate, FaithfulnessVerdict
from leibniz.propositio import Propositio
from leibniz.types import Verdict

KIND = "boolean-modular-faithfulness"
MAX_ATOMS = 8   # distinct atoms → distinct bridges; keeps the proof and the ZMod decide bounded


# --- classification (the fragment gate lives HERE, not in the renderer) ----------------------------


@dataclass(frozen=True)
class BooleanSkeleton:
    """A classified same-modulus boolean combination: the shared modulus `m`, the DISTINCT eq-atoms
    `(poly_ast, c)` needing a bridge, the parsed boolean `tree` (re-rendered over ZMod for the key), and
    `has_neq` (a `!=` atom is present, so the proof must `simp only [ne_eq]` before the eq-bridges — a
    `≠`/`Ne` hides its `=` from `rw`)."""

    modulus: int
    atoms: tuple[tuple[ast.AST, int], ...]
    tree: ast.AST
    has_neq: bool = False


def _walk_bool(node: ast.AST, atoms: list, moduli: set) -> bool:
    """Walk a boolean DSL node, collecting `(op, poly, m, c)` atoms and their moduli. Returns False on
    anything outside the fragment (a non-eq/neq comparison, a bare arithmetic term, unsupported node)."""
    if isinstance(node, ast.BoolOp):                     # and / or
        return all(_walk_bool(v, atoms, moduli) for v in node.values)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
        return _walk_bool(node.operand, atoms, moduli)
    if isinstance(node, ast.Compare):
        # biconditional: `(P) == (Q)` / `(P) != (Q)` between boolean operands → recurse on both sides
        if (len(node.ops) == 1 and isinstance(node.ops[0], (ast.Eq, ast.NotEq))
                and _is_bool_node(node.left) and _is_bool_node(node.comparators[0])):
            return (_walk_bool(node.left, atoms, moduli)
                    and _walk_bool(node.comparators[0], atoms, moduli))
        a = _atom(node)                                  # a modular atom `poly % m ⋈ c` (eq/neq), or None
        if a is None:
            return False
        op, poly, m, c = a
        atoms.append((op, poly, m, c))
        moduli.add(m)
        return True
    return False


def _content_free(tree: ast.AST, atoms: list) -> bool:
    """True if the boolean formula is a propositional TAUTOLOGY or CONTRADICTION — the same truth value
    for every assignment of its distinct atoms (an eq atom is a boolean var, its `!=` the negation of the
    same var). Such a claim carries no modular content (`P↔P`, `P∨¬P`, `A∧¬A`) — reject it as a
    non-result. Genuine modular content (e.g. `A ↔ (B ∨ C)`) is non-constant and passes. ≤ 2**MAX_ATOMS
    assignments (bounded)."""
    import itertools
    keys = sorted({(ast.dump(poly), c) for _op, poly, _m, c in atoms})
    index = {k: i for i, k in enumerate(keys)}

    def ev(node: ast.AST, asn: tuple) -> bool:
        if isinstance(node, ast.BoolOp):
            vals = [ev(v, asn) for v in node.values]
            return all(vals) if isinstance(node.op, ast.And) else any(vals)
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            return not ev(node.operand, asn)
        # Compare: biconditional between booleans, or a modular atom
        if (len(node.ops) == 1 and isinstance(node.ops[0], (ast.Eq, ast.NotEq))
                and _is_bool_node(node.left) and _is_bool_node(node.comparators[0])):
            same = ev(node.left, asn) == ev(node.comparators[0], asn)
            return same if isinstance(node.ops[0], ast.Eq) else not same
        op, poly, _m, c = _atom(node)
        v = asn[index[(ast.dump(poly), c)]]
        return v if op == "eq" else not v

    truths = {ev(tree, asn) for asn in itertools.product((False, True), repeat=len(keys))}
    return len(truths) == 1


def classify_boolean(claim_property: str) -> Optional[BooleanSkeleton]:
    """Classify `claim_property` into a same-modulus boolean-combination skeleton, or None (→ DEFER)."""
    try:
        tree = _parse(claim_property)
    except RenderError:
        return None
    atoms: list = []
    moduli: set = set()
    if not _walk_bool(tree, atoms, moduli):
        return None
    if len(moduli) != 1:
        return None                                      # single shared modulus only (mixed → DEFER)
    if not atoms or len(atoms) > MAX_ATOMS:
        return None
    # Disjoint-by-construction from lean_decided (review #5): decline the shapes it already owns — a bare
    # atom, a single-poly residue-set (∨ of same-poly eq), a plain conjunction. This backend fires ONLY
    # for the richer boolean structure lean_decided cannot classify (biconditionals, ∨ of different polys,
    # ¬, nested mixes) — no longer relying on cost order.
    if classify_property(claim_property) is not None:
        return None
    # Non-triviality (review #1): a propositional tautology/contradiction (P↔P, P∨¬P) carries no modular
    # content — DEFER it rather than promulgate a non-result. (The novelty gate is not a reliable backstop
    # here: it runs on the autoformalized statement, and structural dedup is blind to boolean laws.)
    if _content_free(tree, atoms):
        return None
    m = next(iter(moduli))
    # distinct (poly, c) for the bridges — one bridge rewrites all occurrences of its atom
    seen: dict = {}
    for _op, poly, _m, c in atoms:
        seen.setdefault((ast.dump(poly), c), (poly, c))
    has_neq = any(op == "neq" for op, *_ in atoms)
    return BooleanSkeleton(modulus=m, atoms=tuple(seen.values()), tree=tree, has_neq=has_neq)


# --- gate-owned proof construction (ZMod bridge; validated against the real Lean 4.31 kernel) -------


def _zmod_prop(node: ast.AST) -> str:
    """Render a classified boolean tree as a `ZMod m` proposition: the SAME boolean structure, each
    atom `poly % m ⋈ c` rendered as `poly(vars) ⋈ c` (no `% m` — the vars are ZMod elements). Mirrors
    `dsl_to_lean._prop` but strips the modulus. Total on a classified tree (classify_boolean vetted it)."""
    if isinstance(node, ast.BoolOp):
        conn = " ∧ " if isinstance(node.op, ast.And) else " ∨ "
        return "(" + conn.join(_zmod_prop(v) for v in node.values) + ")"
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
        return f"(¬ {_zmod_prop(node.operand)})"
    if isinstance(node, ast.Compare):
        if (len(node.ops) == 1 and isinstance(node.ops[0], (ast.Eq, ast.NotEq))
                and _is_bool_node(node.left) and _is_bool_node(node.comparators[0])):
            iff = f"({_zmod_prop(node.left)} ↔ {_zmod_prop(node.comparators[0])})"
            return iff if isinstance(node.ops[0], ast.Eq) else f"(¬ {iff})"
        op, poly, _m, c = _atom(node)
        # neq rendered as `¬ (poly = c)` (not `poly ≠ c`) so it matches the goal after `simp only [ne_eq]`
        # AND so the shared eq-bridge (`poly = c ↔ …`) rewrites the `=` inside it.
        return f"({_term(poly)} = {c})" if op == "eq" else f"(¬ ({_term(poly)} = {c}))"
    raise RenderError("not a classified boolean node")   # unreachable after classify_boolean


def _hyp_base(vs: list[str], stem: str) -> str:
    """A hypothesis-name base (`{stem}`, else `{stem}{stem}`, …) that no claim variable shadows — keeps
    the bridge hyps disjoint from the claim's identifiers (robustness only; a clash risked a spurious
    DEFER, never unsoundness)."""
    base = stem
    while any(re.fullmatch(base + r"\d+", v) for v in vs):
        base += stem
    return base


def boolean_proof(skel: BooleanSkeleton, vs: list[str], n_domain: int) -> str:
    """Gate-owned proof of `∀ vars, box → …dom… → Q`: the ZMod-decide key, one bridge per distinct atom,
    then `rw` the atoms, `push_cast`, and discharge with the key. `n_domain` is 2 for the faithfulness
    pair's property leg, 1 for the prover LAW."""
    m = skel.modulus
    binder = " ".join(vs)
    intro_all = (" ".join(vs) + " " + " ".join("_" for _ in vs)
                 + (" " + " ".join("_" for _ in range(n_domain)) if n_domain else ""))
    base = _hyp_base(vs, "hb")
    lines = ["by", f"  intro {intro_all}"]
    if skel.has_neq:
        lines.append("  simp only [ne_eq]")   # `≠` → `¬ =` so the eq-bridges reach the `=` inside a Ne
    lines.append(f"  have key : ∀ ({binder} : ZMod {m}), {_zmod_prop(skel.tree)} := by decide")
    for i, (poly, c) in enumerate(skel.atoms):
        pt = _term(poly)
        lines.append(
            f"  have {base}{i} : (Int.emod ({pt}) {m} = {c}) ↔ ((({pt} : ℤ) : ZMod {m}) = (({c}:ℤ):ZMod {m})) := by\n"
            f"    rw [ZMod.intCast_eq_intCast_iff']\n"
            f"    show ({pt} % {m} = {c}) ↔ ({pt} % {m} = {c} % {m})\n"
            f"    omega")
    lines.append("  rw [" + ", ".join(f"{base}{i}" for i in range(len(skel.atoms))) + "]")
    lines.append("  push_cast")
    lines.append(f"  exact key {binder}")
    return "\n".join(lines)


# --- the gate-owned decision (used identically by the backend AND the re-checker) ------------------


def decide_certificate(data: object, kernel) -> tuple[bool, dict]:
    """Decide the faithfulness pair for a same-modulus boolean-combination `data` = {claim_domain,
    claim_property, established_domain}: construct all four statements + gate-owned proofs, require the
    KERNEL to accept each with a clean axiom footprint. Exact-or-DEFER; total. Mirrors
    `lean_decided.decide_certificate`, swapping the classifier + the property proof (ZMod-bridge)."""
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
    skel = classify_boolean(cp)
    if skel is None:
        return False, {"reason": "claim_property outside the same-modulus boolean fragment"}
    if skel.modulus ** len(vs) > MAX_RESIDUE_CELLS:
        return False, {"reason": "residue budget exceeded"}

    w_claim = find_witness([cd], vs)
    w_ec = find_witness([ed, cd], vs)
    if w_claim is None or w_ec is None:
        return False, {"reason": "no ∃-witness found (empty or out-of-box domain)"}

    checks: list[tuple[str, str, list[str]]] = [
        ("coverage", pair["coverage"], coverage_proofs(len(vs))),
        ("property", pair["property"], [boolean_proof(skel, vs, n_domain=2)]),
        ("exists_claim", pair["exists_claim"], witness_proof(w_claim)),
        ("exists_ec", pair["exists_ec"], witness_proof(w_ec)),
    ]
    from leibniz.propositio import Expressio
    detail: dict = {"witness_claim": w_claim, "witness_ec": w_ec, "n_atoms": len(skel.atoms)}
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


# --- the SoundFaithfulnessBackend + gate-side re-checker / template --------------------------------


def prop_statement_template(prop: Propositio) -> Optional[str]:
    """The canonical statement rendered from PROP'S OWN fields (obligation 5) — identical rendering to
    the other backends; None → unbindable → no PASS."""
    en, ex = prop.enuntiatio, prop.expressio
    if en is None or ex is None or not (en.claim_domain and en.claim_property and ex.established_domain):
        return None
    try:
        return canonical_statement(en.claim_domain, en.claim_property, ex.established_domain)
    except RenderError:
        return None


@dataclass
class BooleanDecidedFaithfulness:
    """SoundFaithfulnessBackend: same-modulus boolean combinations (incl. biconditionals), kernel-decided."""

    kernel: object
    name: str = "boolean-decided"
    cost_rank: int = 93        # after lean_decided (90) / minmax (91); reached only for richer boolean shapes

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
            return False
        skel = classify_boolean(en.claim_property)
        return skel is not None and skel.modulus ** len(vs) <= MAX_RESIDUE_CELLS

    def check(self, prop: Propositio) -> FaithfulnessVerdict:
        en, ex = prop.enuntiatio, prop.expressio
        data = {"claim_domain": en.claim_domain, "claim_property": en.claim_property,
                "established_domain": ex.established_domain}
        ok, detail = decide_certificate(data, self.kernel)
        if not ok:
            return FaithfulnessVerdict(verdict=Verdict.DEFER, producer="boolean_modular/defer", detail=detail)
        statement = canonical_statement(**data)
        cert = Certificate(kind=KIND, rechecked=True, data=data, detail={"statement": statement})
        return FaithfulnessVerdict(verdict=Verdict.PASS, producer="boolean_modular/kernel",
                                   certificate=cert, detail=detail)


def make_rechecker(kernel) -> Callable[[Certificate], bool]:
    """The gate's independent re-checker: re-derives EVERYTHING from cert.data and replicates the E7
    statement pin (template(cert.data) == claimed, builtin-str, str.__ne__). Total: any surprise → False."""

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
    """OPERATOR ACTION (not called anywhere in the assembly): activate this kind on a constructed
    FaithfulnessGate. Installs BOTH the re-checker AND the statement template. Until called, the
    fail-closed default holds — no PASS of this kind is ever accepted."""
    gate.sound_backends = tuple(gate.sound_backends) + (BooleanDecidedFaithfulness(kernel=kernel),)
    gate.recheckers[KIND] = make_rechecker(kernel)
    gate.templates[KIND] = prop_statement_template
