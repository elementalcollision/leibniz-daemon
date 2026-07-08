"""ADR 0060 — the LCM/castHom faithfulness backend for MIXED-modulus modular claims.

The fourth (and final planned) decision procedure of the ceiling-raiser: boolean combinations of modular
atoms whose moduli **differ** — e.g. `((a+b)²%4=1) ↔ ((a+b)%2=1)`, `(a²+b²)%4=2 ↔ (a%2=1 ∧ b%2=1)`.
`lean_decided`/`boolean_decided` decide a claim over `ZMod m` for a SINGLE modulus `m`; a mixed-modulus
claim has no single `m`. This backend reduces to the **least common multiple** `M = lcm(mⱼ)`: the Lean
kernel `decide`s the whole boolean formula over `ZMod M`, and a **ring homomorphism** `ZMod.castHom
(mⱼ ∣ M) (ZMod mⱼ)` expresses each sub-modulus atom over the common `ZMod M`. A **false** formula makes
the `decide` refuse ⇒ DEFER — the kernel decides (kernel-validated against Lean 4.31).

The proof (uniform; validated against the real kernel):

1. `have key : ∀ (vars : ZMod M), Q_M := by decide` — `Q_M` is the claim's boolean structure with each
   atom `poly % mⱼ ⋈ cⱼ` rendered as `castHom(mⱼ∣M) (poly(vars)) ⋈ cⱼ` (or `poly(vars) ⋈ cⱼ` when mⱼ = M).
2. Per DISTINCT `(poly, mⱼ, cⱼ)`: a bridge `(Int.emod poly mⱼ = cⱼ) ↔ ((↑poly : ZMod mⱼ) = ↑cⱼ)`, proved
   `rw [ZMod.intCast_eq_intCast_iff']; show ((poly) % mⱼ = cⱼ) ↔ ((poly) % mⱼ = cⱼ % mⱼ); omega`.
3. `rw` the bridges, `push_cast` (turns `↑(poly)` into `poly(↑vars)`), then instantiate `hk := key ↑vars`
   and `simp only [map_add, map_mul, map_pow, map_intCast, …] at hk` to DISTRIBUTE the castHoms into
   direct casts, so `hk` matches the goal — `exact hk`.

Fragment (owned at the classifier — the renderer is more permissive):
- **≥ 2 distinct moduli** (a single-modulus claim is `boolean_decided`'s job — disjoint by construction);
- every atom `poly % mⱼ == cⱼ` / `!= cⱼ` with `poly` a pure polynomial and `0 ≤ cⱼ < mⱼ` (reuses
  `lean_decided._atom`); `and`/`or`/`not`/`↔` structure only; ≥1 modular content (non-triviality guard);
- `MIN_VARS ≤ nvars ≤ MAX_VARS`, `M ** nvars ≤ MAX_RESIDUE_CELLS`, `≤ MAX_ATOMS` atoms.

**Fail-closed by default.** Nothing registers this in the assembly. Activation is an OPERATOR action
(`register`, gated in `assembly.maybe_register_mixed_modulus` behind the same `LEIBNIZ_LEAN_DECIDED` REPL
activation); until then no PASS of this kind is accepted. Producer `mixed_modular/kernel`, admitted to
`FAITHFULNESS_PRODUCERS` by the operator (ADR 0041), like the other decision-procedure producers.
"""
from __future__ import annotations

import ast
import math
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
from leibniz.gates.boolean_decided import MAX_ATOMS, _content_free, _walk_bool
from leibniz.gates.lean_decided import (
    IMPORTS,
    MAX_RESIDUE_CELLS,
    MAX_VARS,
    MIN_VARS,
    _atom,
    _thm,
    coverage_proofs,
    find_witness,
    witness_proof,
)
from leibniz.gates.sound_backends import Certificate, FaithfulnessVerdict
from leibniz.propositio import Propositio
from leibniz.types import Verdict

KIND = "mixed-modulus-faithfulness"
# Cap the LCM so the castHom `by decide` divisibility proofs and the `ZMod M` decide stay cheap; the
# `M ** nvars ≤ MAX_RESIDUE_CELLS` budget is the binding one, this is a belt-and-suspenders ceiling.
MAX_LCM = 64
# The ring-hom-distribution lemmas that push a `ZMod.castHom` through a polynomial to its int-cast leaves.
_MAP_LEMMAS = ("map_add, map_sub, map_mul, map_pow, map_intCast, map_neg, map_ofNat, map_one, map_zero")


@dataclass(frozen=True)
class MixedSkeleton:
    """A classified mixed-modulus boolean combination: the common modulus `M = lcm(moduli)`, the DISTINCT
    `(poly_ast, mⱼ, cⱼ)` atoms needing a bridge, the parsed boolean `tree` (re-rendered over ZMod M with
    castHoms for the key), and `has_neq` (a `!=` atom → `simp only [ne_eq]` before the eq-bridges)."""

    M: int
    atoms: tuple[tuple[ast.AST, int, int], ...]
    tree: ast.AST
    has_neq: bool = False


def classify_mixed(claim_property: str) -> Optional[MixedSkeleton]:
    """Classify `claim_property` into a mixed-modulus skeleton, or None (→ DEFER)."""
    try:
        tree = _parse(claim_property)
    except RenderError:
        return None
    atoms: list = []
    moduli: set = set()
    if not _walk_bool(tree, atoms, moduli):
        return None
    if len(moduli) < 2:
        return None                                      # single modulus is boolean_decided's fragment
    if not atoms or len(atoms) > MAX_ATOMS:
        return None
    M = math.lcm(*moduli)
    if M > MAX_LCM:
        return None
    if _content_free(tree, atoms):                       # a propositional tautology carries no content
        return None
    # distinct (poly, mⱼ, cⱼ) for the bridges — one bridge rewrites all occurrences of its atom
    seen: dict = {}
    for _op, poly, mj, c in atoms:
        seen.setdefault((ast.dump(poly), mj, c), (poly, mj, c))
    has_neq = any(op == "neq" for op, *_ in atoms)
    return MixedSkeleton(M=M, atoms=tuple(seen.values()), tree=tree, has_neq=has_neq)


# --- gate-owned proof construction (LCM/castHom; validated against the real Lean 4.31 kernel) -------


def _castHom(mj: int, M: int) -> str:
    return f"(ZMod.castHom (show ({mj}:ℕ) ∣ {M} by decide) (ZMod {mj}))"


def _zmod_prop_mixed(node: ast.AST, M: int) -> str:
    """Render the boolean tree as a `ZMod M` proposition: each atom `poly % mⱼ ⋈ cⱼ` becomes
    `poly(vars) ⋈ cⱼ` (when mⱼ = M) or `castHom(mⱼ∣M) (poly(vars)) ⋈ cⱼ` (when mⱼ | M, mⱼ < M), keeping
    the boolean structure. Total on a classified tree."""
    if isinstance(node, ast.BoolOp):
        conn = " ∧ " if isinstance(node.op, ast.And) else " ∨ "
        return "(" + conn.join(_zmod_prop_mixed(v, M) for v in node.values) + ")"
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
        return f"(¬ {_zmod_prop_mixed(node.operand, M)})"
    if isinstance(node, ast.Compare):
        if (len(node.ops) == 1 and isinstance(node.ops[0], (ast.Eq, ast.NotEq))
                and _is_bool_node(node.left) and _is_bool_node(node.comparators[0])):
            iff = f"({_zmod_prop_mixed(node.left, M)} ↔ {_zmod_prop_mixed(node.comparators[0], M)})"
            return iff if isinstance(node.ops[0], ast.Eq) else f"(¬ {iff})"
        op, poly, mj, c = _atom(node)
        term = _term(poly)
        expr = term if mj == M else f"{_castHom(mj, M)} ({term})"
        # neq rendered `¬ (expr = c)` so it matches the goal after `simp only [ne_eq]`
        return f"({expr} = {c})" if op == "eq" else f"(¬ ({expr} = {c}))"
    raise RenderError("not a classified mixed node")     # unreachable after classify_mixed


def _hyp_base(vs: list[str]) -> str:
    base = "hm"
    while any(re.fullmatch(base + r"\d+", v) for v in vs):
        base += "m"
    return base


def _bridge(name: str, poly: str, mj: int, c: int) -> str:
    return (f"  have {name} : (Int.emod ({poly}) {mj} = {c}) ↔ ((({poly} : ℤ) : ZMod {mj}) = (({c}:ℤ):ZMod {mj})) := by\n"
            f"    rw [ZMod.intCast_eq_intCast_iff']\n"
            f"    show (({poly}) % {mj} = {c}) ↔ (({poly}) % {mj} = {c} % {mj})\n"
            f"    omega")


def mixed_proof(skel: MixedSkeleton, vs: list[str], n_domain: int) -> str:
    """Gate-owned proof of `∀ vars, box → …dom… → Q` for a mixed-modulus Q: the ZMod-M decide key (with
    castHom-expressed sub-modulus atoms), one bridge per distinct atom, then `rw` + `push_cast` +
    `simp [map_*] at hk` (distribute the castHoms) + `exact hk`. `n_domain` = 2 for the faithfulness
    pair's property leg, 1 for the prover LAW."""
    M = skel.M
    binder = " ".join(vs)
    intro_all = (" ".join(vs) + " " + " ".join("_" for _ in vs)
                 + (" " + " ".join("_" for _ in range(n_domain)) if n_domain else ""))
    base = _hyp_base(vs)
    lines = ["by", f"  intro {intro_all}"]
    if skel.has_neq:
        lines.append("  simp only [ne_eq]")             # `≠` → `¬ =` so the eq-bridges reach the `=`
    lines.append(f"  have key : ∀ ({binder} : ZMod {M}), {_zmod_prop_mixed(skel.tree, M)} := by decide")
    for i, (poly, mj, c) in enumerate(skel.atoms):
        lines.append(_bridge(f"{base}{i}", _term(poly), mj, c))
    lines.append("  rw [" + ", ".join(f"{base}{i}" for i in range(len(skel.atoms))) + "]")
    lines.append("  push_cast")
    lines.append("  have hk := key " + " ".join(f"({v} : ZMod {M})" for v in vs))
    lines.append(f"  simp only [{_MAP_LEMMAS}] at hk")
    lines.append("  exact hk")
    return "\n".join(lines)


# --- the gate-owned decision (used identically by the backend AND the re-checker) ------------------


def decide_certificate(data: object, kernel) -> tuple[bool, dict]:
    """Decide the faithfulness pair for a mixed-modulus claim by constructing all four statements +
    gate-owned proofs and requiring the KERNEL to accept each with a clean axiom footprint. Exact-or-
    DEFER; total. Mirrors `boolean_decided.decide_certificate`, swapping the classifier + the LCM/castHom
    property proof and the `M`-based residue budget."""
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
    skel = classify_mixed(cp)
    if skel is None:
        return False, {"reason": "claim_property outside the mixed-modulus fragment"}
    if skel.M ** len(vs) > MAX_RESIDUE_CELLS:
        return False, {"reason": "residue budget exceeded"}

    w_claim = find_witness([cd], vs)
    w_ec = find_witness([ed, cd], vs)
    if w_claim is None or w_ec is None:
        return False, {"reason": "no ∃-witness found (empty or out-of-box domain)"}

    checks: list[tuple[str, str, list[str]]] = [
        ("coverage", pair["coverage"], coverage_proofs(len(vs))),
        ("property", pair["property"], [mixed_proof(skel, vs, n_domain=2)]),
        ("exists_claim", pair["exists_claim"], witness_proof(w_claim)),
        ("exists_ec", pair["exists_ec"], witness_proof(w_ec)),
    ]
    from leibniz.propositio import Expressio
    detail: dict = {"witness_claim": w_claim, "witness_ec": w_ec, "lcm": skel.M, "n_atoms": len(skel.atoms)}
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
    en, ex = prop.enuntiatio, prop.expressio
    if en is None or ex is None or not (en.claim_domain and en.claim_property and ex.established_domain):
        return None
    try:
        return canonical_statement(en.claim_domain, en.claim_property, ex.established_domain)
    except RenderError:
        return None


@dataclass
class MixedModulusFaithfulness:
    """SoundFaithfulnessBackend: mixed-modulus boolean combinations, kernel-decided over ZMod(lcm)."""

    kernel: object
    name: str = "mixed-modulus-decided"
    cost_rank: int = 94        # after lean_decided (90) / minmax (91) / boolean (93); disjoint fragment

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
        skel = classify_mixed(en.claim_property)
        return skel is not None and skel.M ** len(vs) <= MAX_RESIDUE_CELLS

    def check(self, prop: Propositio) -> FaithfulnessVerdict:
        en, ex = prop.enuntiatio, prop.expressio
        data = {"claim_domain": en.claim_domain, "claim_property": en.claim_property,
                "established_domain": ex.established_domain}
        ok, detail = decide_certificate(data, self.kernel)
        if not ok:
            return FaithfulnessVerdict(verdict=Verdict.DEFER, producer="mixed_modular/defer", detail=detail)
        statement = canonical_statement(**data)
        cert = Certificate(kind=KIND, rechecked=True, data=data, detail={"statement": statement})
        return FaithfulnessVerdict(verdict=Verdict.PASS, producer="mixed_modular/kernel",
                                   certificate=cert, detail=detail)


def make_rechecker(kernel) -> Callable[[Certificate], bool]:
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
    FaithfulnessGate. Installs BOTH the re-checker AND the statement template. Fail-closed until called."""
    gate.sound_backends = tuple(gate.sound_backends) + (MixedModulusFaithfulness(kernel=kernel),)
    gate.recheckers[KIND] = make_rechecker(kernel)
    gate.templates[KIND] = prop_statement_template
