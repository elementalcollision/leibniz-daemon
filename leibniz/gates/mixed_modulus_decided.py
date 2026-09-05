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
- `MIN_VARS ≤ nvars ≤ MAX_VARS`, `M ** nvars ≤ MIXED_MAX_CELLS`, `≤ MIXED_MAX_ATOMS` atoms
  (ADR 0088: this fragment's own budgets, not the shared boolean/single-modulus ones).

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
from leibniz.gates.boolean_decided import MAX_ATOMS as _ENUM_ATOM_CAP
from leibniz.gates.boolean_decided import _content_free, _walk_bool
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
# ADR 0088 — this fragment's OWN budgets. They are deliberately NOT the shared `MAX_ATOMS`
# (boolean_decided) / `MAX_RESIDUE_CELLS` (lean_decided) constants: those are tested against
# `modulus ** nvars` by the single-modulus and boolean classifiers too, so raising them in place to
# admit a 1-variable claim at M=10080 would silently also admit 2-var claims at M≈142 and 3-var at
# M≈27 for procedures whose cost was never measured there. Widening is per-fragment.
#
# Every one of these bounds a `decide` over a FINITE `ZMod` — compute budget, never soundness. A
# false formula still makes the decide refuse ⇒ the kernel rejects ⇒ DEFER, at any cap.
MAX_LCM = 20160        # measured on live Lean 4.31: M=10080 closes in 16s, M=100800 in 47s, OOM
                       # before M=262080. 20160 admits arXiv 2607.19029 (10080) and Klein (15120)
                       # with an order of magnitude of headroom under the measured ceiling.
MIXED_MAX_CELLS = 20160    # this fragment's `M ** nvars` budget, ONE VARIABLE ONLY — see `_cell_budget`
MIXED_MAX_ATOMS = 72       # a covering system with lcm M and min modulus m has at most
                           # #{d : d | M, d ≥ m} congruences — 66 for (10080, 7), which arXiv
                           # 2607.19029 §7 exactly attains. 72 is that bound with margin.


def _cell_budget(nvars: int) -> int:
    """The `M ** nvars` budget. The ADR 0088 widening applies at ONE variable and nowhere else.

    Adversarial review caught this: ADR 0088 argues the SHARED `MAX_RESIDUE_CELLS` must not be
    raised because 20160 "would silently also admit 2-var claims at M≈142 and 3-var at M≈27 —
    cells nobody measured" — and then a flat `MIXED_MAX_CELLS` did exactly that INSIDE this
    fragment (2-var went M ≤ 64 → M ≤ 141, 3-var M ≤ 16 → M ≤ 27). Every row of the ADR's
    evidence table, and every covering system that motivated it, is single-variable. So the
    widened budget is scoped to where it was measured; multi-variable claims keep the shared,
    long-tested 4096. Raising THAT wants its own measurements, not a side effect of this one.
    """
    return MIXED_MAX_CELLS if nvars == 1 else MAX_RESIDUE_CELLS
# ADR 0088 — options for the `key` decide, scoped to the TACTIC (`set_option … in`), so the
# gate-owned proof stays self-contained: no file-level preamble, nothing for a caller to forget.
# All three are load-bearing and were each found by a kernel run, not by reasoning:
#   maxRecDepth              — without it `decide` dies at M≈120 with "maximum recursion depth".
#                              This, not compute, is the wall the old MAX_LCM = 64 sat behind.
#   synthInstance.maxSize    — without them a 66-atom disjunction fails to synthesize `Decidable`
#   synthInstance.maxHeartbeats  (instance synthesis, not compute — a 32-atom proxy never hits this).
# `decide +kernel` reduces in the kernel instead of the elaborator: 6.8s vs 37.5s at M=10080.
_DECIDE_OPTS = (
    "set_option maxRecDepth 1000000 in",
    "set_option synthInstance.maxSize 4000 in",
    "set_option synthInstance.maxHeartbeats 4000000 in",
)

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
    if not atoms or len(atoms) > MIXED_MAX_ATOMS:
        return None
    M = math.lcm(*moduli)
    if M > MAX_LCM:
        return None
    if _mixed_content_free(tree, atoms):                 # a propositional tautology carries no content
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


def _mixed_content_free(tree: ast.AST, atoms: list) -> bool:
    """Non-triviality for this fragment, WITHOUT `boolean_decided._content_free`'s 2**n enumeration.

    That helper decides content-freeness exactly by trying every truth assignment — 256 at the
    boolean fragment's `MAX_ATOMS = 8`, and 2**72 once ADR 0088 raises this fragment's atom cap to
    72. Raising the cap without this branch does not merely slow the classifier down, it HANGS it,
    which is strictly worse than a DEFER: the daemon's cycle stops instead of moving on.

    Two branches:
      - `<= _ENUM_ATOM_CAP` atoms → delegate, so every claim that classified before ADR 0088
        classifies identically after it;
      - more → admit ONLY a flat disjunction of modular atoms, the covering-system shape, where
        non-triviality is exact and O(n): such a formula is false when every atom is false and
        true when any single atom holds, so it is CONSTANT iff some atom occurs both as `==` and
        as `!=` (a literal `p ∨ ¬p`). Any other large shape returns True — content-free ⇒ REJECT
        ⇒ DEFER — which is the fail-closed direction: an unrecognised big formula is refused, not
        waved through on an unchecked guard.
    """
    # ADR 0089 review — the full-residue-block check is O(k) and sound at ANY size, so it runs
    # FIRST and at every atom count. Scoping it to the >8 branch (as this first landed) left the
    # ADR's own example family classifying at 3-8 atoms: `(n%2==0) ∨ (n%2==1) ∨ (n%3==0)` went
    # straight through, and `boolean_decided` refuses that same shape on one modulus — the mixed
    # gate was laxer than its sibling on the pathology it had just been hardened against.
    flat = _flat_atoms(tree)
    if flat and _padded_covering(flat):
        return True
    if len(atoms) <= _ENUM_ATOM_CAP:
        return _content_free(tree, atoms)
    if not flat:
        return True                                      # large non-flat shape → refuse
    pos: set = set()
    neg: set = set()
    for op, poly, mj, c in flat:
        (pos if op == "eq" else neg).add((ast.dump(poly), mj, c))
    return bool(pos & neg)                               # a literal `p ∨ ¬p`


def _flat_atoms(tree: ast.AST) -> list:
    """The `(op, poly, m, c)` atoms of a FLAT disjunction, or [] if the tree is not one.
    (CPython does not flatten `(A ∨ B) ∨ C`, so a parenthesis-grouped disjunction reads as
    non-flat here and takes the conservative path.)"""
    if not (isinstance(tree, ast.BoolOp) and isinstance(tree.op, ast.Or)):
        return []
    out: list = []
    for node in tree.values:
        parsed = _atom(node) if isinstance(node, ast.Compare) else None
        if parsed is None:
            return []
        out.append(parsed)
    return out


def _padded_covering(flat: list) -> bool:
    """ADR 0089 — True when a flat disjunction is content-free BY CONSTRUCTION: some modulus
    appears with ALL of its residues, i.e. the formula literally restates "every integer has some
    residue mod m". `(n%4==0) ∨ (n%4==1) ∨ (n%4==2) ∨ (n%4==3) ∨ …` is such a claim padded out
    with filler; it is TRUE, so the kernel accepts it, and it would promulgate as a law carrying
    no content. Propositionally it is not constant — the atoms are independent boolean variables —
    so neither `_content_free` nor the `pos & neg` check above sees anything wrong with it.

    THE CRITERION IS NOT REDUNDANCY. ADR 0089 first specified "reject when a proper subset already
    covers ℤ", computed by a coverage-count array. Testing that against the system it exists to
    admit refuted it: arXiv 2607.19029 §7 — the published, distinct, minimum-modulus-7, lcm-10080
    covering system this whole line of work is aimed at — contains a REDUNDANT congruence. Drop
    `233 (mod 1120)` and the remaining 65 still cover ℤ, still have distinct moduli, minimum
    modulus 7 and lcm 10080 (verified exhaustively). That is not an error in the paper: its
    theorem is that the minimal LCM is 10080, not that the witness is irredundant. But it means
    redundancy does not imply absence of content, and the redundancy criterion would have rejected
    the target.

    A full residue block cannot occur in a DISTINCT covering system at all — no modulus repeats —
    so this criterion cannot fire on one, which is exactly the property the redundancy test lacked.

    Scope, deliberately narrow: only all-`==` atoms over the SAME bare variable, the
    covering-system shape. Anything else keeps the propositional verdict; coverage is not the
    right question there and guessing at it would be a new way to be wrong. O(k), no arithmetic
    over ℤ/M at all.
    """
    # Only the `==` atoms matter, and the rest of the disjunction is irrelevant: if the eq atoms
    # alone contain a complete residue system mod m the whole formula is a tautology over ℤ no
    # matter what else is OR'd in. Requiring EVERY atom to be `==` (as this first landed) made the
    # guard evadable by appending one unrelated `!=` atom.
    eqs = [(p, mj, c) for op, p, mj, c in flat if op == "eq"]
    if not eqs:
        return False
    if len({ast.dump(p) for p, _m, _c in eqs}) != 1 or not all(isinstance(p, ast.Name) for p, _m, _c in eqs):
        return False                                     # compound polys or >1 variable → not ours
    residues: dict = {}
    for _p, mj, c in eqs:
        residues.setdefault(mj, set()).add(c % mj)
    return any(len(rs) == mj for mj, rs in residues.items())


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
    lines.append(f"  have key : ∀ ({binder} : ZMod {M}), {_zmod_prop_mixed(skel.tree, M)} := by")
    lines += [f"    {opt}" for opt in _DECIDE_OPTS]
    lines.append("    decide +kernel")
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
    if skel.M ** len(vs) > _cell_budget(len(vs)):
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
        return skel is not None and skel.M ** len(vs) <= _cell_budget(len(vs))

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
