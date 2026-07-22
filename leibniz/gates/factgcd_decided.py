"""ADR 0070 — the two-regime faithfulness backend for FACTORIAL/GCD claims (Phase γ leg 1).

The sixth decision procedure of the ceiling-raiser: claims about ``factorial(n) % m`` and
``gcd(c, n)`` / ``gcd(n, c)`` — the ADR 0066 fragment Z3 already decides by bounded If-tables, now
decidable by the Lean kernel too (and hence provable as promulgable LAWS). Two kernel-validated
templates (Lean 4.31, prototyped 2026-07-22 with true instances CHECKED and false controls
REJECTED):

- **factorial** (two-regime): ``bridge : Int.emod ↑(t!) m = ↑(t! % m)`` (``push_cast; rfl``);
  ``key : ∀ t, m ≤ t → t! % m = 0`` (``Nat.dvd_factorial`` + ``omega`` — no lemma-name roulette);
  then split ``toNat < m`` (``interval_cases <;> norm_num [Nat.factorial]`` — the finite initial
  segment) vs ``≥ m`` (rewrite by ``key``; the tail is identically 0).
- **gcd** (period-split): ``key : ∀ t, Nat.gcd c t = Nat.gcd c (t % c)`` (``Nat.gcd_rec`` +
  ``Nat.gcd_comm`` — gcd is periodic in its variable argument with period c), then
  ``interval_cases r <;> norm_num [Nat.gcd]`` over the c arms; a leading ``gcd_comm`` flips the
  ``gcd(n, c)`` spelling first.

A **false** claim fails at some arm ⇒ the kernel rejects ⇒ **DEFER** — the kernel, not the
template, decides.

Fragment (owned at the classifier — the renderer is more permissive):
- factorial: ONE atom family ``factorial(v) % m ⋈ c`` — bare variable argument, constant modulus
  ``2 ≤ m ≤ MAX_ORDER`` (the arm-count cap, as in ADR 0065), residues in ``[0, m)``;
- gcd: ONE atom family ``gcd(c, v) ⋈ d`` or ``gcd(v, c) ⋈ d`` — one bare variable + one constant
  ``1 ≤ c ≤ MAX_ORDER``, asserted values in ``[0, c]`` (``gcd(c, t) ∣ c``);
- ``eq`` / ``neq`` single atom, or an or-disjunction of ``==`` atoms over the SAME family
  (residue_set); the claim's ONLY free variable is the function's variable argument.

**Fail-closed by default.** Nothing registers this in the assembly. Activation is an OPERATOR
action (``register``, gated in ``assembly.maybe_register_factgcd`` behind the same
``LEIBNIZ_LEAN_DECIDED`` REPL activation); until then no PASS of this kind is accepted. Producer
``factgcd/kernel``, admitted to ``FAITHFULNESS_PRODUCERS`` by the operator (ADR 0041), like the
other decision-procedure producers.
"""
from __future__ import annotations

import ast
from dataclasses import dataclass
from typing import Callable, Optional

from leibniz.backends.lean_axioms import axiom_closure
from leibniz.backends.smt_z3 import MAX_ORDER
from leibniz.dsl_to_lean import (
    RenderError,
    _parse,
    canonical_statement,
    faithfulness_pair,
    free_vars,
)
from leibniz.gates.lean_decided import (
    IMPORTS,
    _thm,
    coverage_proofs,
    find_witness,
    witness_proof,
)
from leibniz.gates.sound_backends import Certificate, FaithfulnessVerdict
from leibniz.propositio import Propositio
from leibniz.types import Verdict

KIND = "factgcd-faithfulness"
# Single-variable fragment (the function's variable argument), on the same COST grounds as ADR 0065:
# the sound backends run only after the cheap probes DEFER, and the Z3 If-tables (ADR 0066) already
# cover this fragment on the box — this backend fires exactly where the cheap path could not.
EXACT_VARS = 1


@dataclass(frozen=True)
class FactGcdSkeleton:
    """A classified factorial/gcd claim. ``fn`` ∈ {'factorial','gcd'}; ``op`` ∈ {'eq','neq',
    'residue_set'}; ``modulus`` is the ``%`` modulus (factorial) or the constant argument (gcd);
    ``var_first`` (gcd only) records the ``gcd(v, c)`` spelling; ``residues`` the asserted values."""

    fn: str
    op: str
    var: str
    modulus: int
    var_first: bool
    residues: tuple[int, ...]


def _const(node: ast.AST) -> Optional[int]:
    if isinstance(node, ast.Constant) and isinstance(node.value, int) and not isinstance(node.value, bool):
        return node.value
    return None


def _call(node: ast.AST, name: str, nargs: int) -> Optional[list[ast.AST]]:
    if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == name
            and not node.keywords and len(node.args) == nargs
            and not any(isinstance(a, ast.Starred) for a in node.args)):
        return list(node.args)
    return None


def _factgcd_atom(node: ast.AST) -> Optional[tuple[str, str, str, int, bool, int]]:
    """One comparison atom → ``(fn, op, var, modulus, var_first, value)``; else None.
    factorial: ``factorial(v) % m ⋈ c``; gcd: ``gcd(c, v) ⋈ d`` / ``gcd(v, c) ⋈ d``."""
    if not (isinstance(node, ast.Compare) and len(node.ops) == 1 and len(node.comparators) == 1):
        return None
    op = {ast.Eq: "eq", ast.NotEq: "neq"}.get(type(node.ops[0]))
    val = _const(node.comparators[0])
    if op is None or val is None:
        return None
    left = node.left
    # factorial(v) % m
    if isinstance(left, ast.BinOp) and isinstance(left.op, ast.Mod):
        args = _call(left.left, "factorial", 1)
        m = _const(left.right)
        if args is None or m is None or not (2 <= m <= MAX_ORDER) or not isinstance(args[0], ast.Name):
            return None
        if not (0 <= val < m):
            return None                                  # out-of-range residue → degenerate → DEFER
        return ("factorial", op, args[0].id, m, False, val)
    # gcd(c, v) / gcd(v, c)
    args = _call(left, "gcd", 2)
    if args is None:
        return None
    a, b = args
    if isinstance(a, ast.Name) and _const(b) is not None:
        var, c, var_first = a.id, _const(b), True
    elif isinstance(b, ast.Name) and _const(a) is not None:
        var, c, var_first = b.id, _const(a), False
    else:
        return None                                      # var/var or const/const → outside the fragment
    if not (1 <= c <= MAX_ORDER) or not (0 <= val <= c):
        return None
    return ("gcd", op, var, c, var_first, val)


def classify_factgcd(claim_property: str) -> Optional[FactGcdSkeleton]:
    """Classify ``claim_property`` into a factorial/gcd skeleton, or None (→ DEFER)."""
    try:
        tree = _parse(claim_property)
    except RenderError:
        return None
    atoms: list[tuple[str, str, str, int, bool, int]] = []
    if isinstance(tree, ast.BoolOp) and isinstance(tree.op, ast.Or):
        for v in tree.values:
            a = _factgcd_atom(v)
            if a is None or a[1] != "eq":                # residue_set: or-of-== only
                return None
            atoms.append(a)
    else:
        a = _factgcd_atom(tree)
        if a is None:
            return None
        atoms.append(a)
    # one atom family: same (fn, var, modulus, spelling) across all disjuncts
    if len({(fn, v, m, vf) for fn, _op, v, m, vf, _c in atoms}) != 1:
        return None
    fn, op0, var, m, vf, _ = atoms[0]
    residues = tuple(c for *_x, c in atoms)
    if len(atoms) > 1 and len(set(residues)) != len(residues):
        return None
    op = op0 if len(atoms) == 1 else "residue_set"
    return FactGcdSkeleton(fn=fn, op=op, var=var, modulus=m, var_first=vf, residues=residues)


# --- gate-owned proof construction (validated against the real Lean 4.31 kernel) -------------------


def factgcd_proof(skel: FactGcdSkeleton, n_domain: int) -> str:
    """Gate-owned proof of ``∀ v, box → …dom… → P(...)``. ``n_domain`` = 2 for the faithfulness
    pair's property leg (established + claim_domain), 1 for the prover LAW (claim_domain only)."""
    m, v = skel.modulus, skel.var
    intro_all = f"{v} _ " + " ".join("_" for _ in range(n_domain))
    if skel.fn == "factorial":
        return f"""by
  have bridge : ∀ t : Nat, Int.emod ((Nat.factorial t : ℕ) : ℤ) {m} = ((Nat.factorial t % {m} : Nat) : ℤ) := by
    intro t
    push_cast
    rfl
  have key : ∀ t : Nat, {m} ≤ t → Nat.factorial t % {m} = 0 := by
    intro t ht
    have hd : {m} ∣ Nat.factorial t := Nat.dvd_factorial (by norm_num) ht
    omega
  intro {intro_all}
  rw [bridge]
  rcases Nat.lt_or_ge (({v}).toNat) {m} with h | h
  · set t := ({v}).toNat with ht
    interval_cases t <;> norm_num [Nat.factorial]
  · rw [key _ h]
    norm_num"""
    flip = "rw [Nat.gcd_comm]\n  " if skel.var_first else ""
    return f"""by
  intro {intro_all}
  have key : ∀ t : Nat, Nat.gcd {m} t = Nat.gcd {m} (t % {m}) := by
    intro t
    conv_lhs => rw [Nat.gcd_rec]
    rw [Nat.gcd_comm]
  {flip}rw [key (({v}).toNat)]
  have hlt : (({v}).toNat) % {m} < {m} := Nat.mod_lt _ (by norm_num)
  set r := (({v}).toNat) % {m} with hr
  interval_cases r <;> norm_num [Nat.gcd]"""


# --- the gate-owned decision (used identically by the backend AND the re-checker) ------------------


def decide_certificate(data: object, kernel) -> tuple[bool, dict]:
    """Decide the faithfulness pair for a factorial/gcd claim by constructing all four statements +
    gate-owned proofs and requiring the KERNEL to accept each with a clean axiom footprint.
    Exact-or-DEFER; total. Mirrors ``power_mod_decided.decide_certificate``, swapping the classifier
    and the two-regime/period-split property proof."""
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
    skel = classify_factgcd(cp)
    if skel is None:
        return False, {"reason": "claim_property outside the factorial/gcd fragment"}
    if len(vs) != EXACT_VARS or vs != [skel.var]:
        return False, {"reason": f"fragment is single-variable (the function argument); got {vs}"}

    w_claim = find_witness([cd], vs)
    w_ec = find_witness([ed, cd], vs)
    if w_claim is None or w_ec is None:
        return False, {"reason": "no ∃-witness found (empty or out-of-box domain)"}

    checks: list[tuple[str, str, list[str]]] = [
        ("coverage", pair["coverage"], coverage_proofs(len(vs))),
        ("property", pair["property"], [factgcd_proof(skel, n_domain=2)]),
        ("exists_claim", pair["exists_claim"], witness_proof(w_claim)),
        ("exists_ec", pair["exists_ec"], witness_proof(w_ec)),
    ]
    from leibniz.propositio import Expressio
    detail: dict = {"witness_claim": w_claim, "witness_ec": w_ec,
                    "fn": skel.fn, "modulus": skel.modulus}
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
class FactGcdFaithfulness:
    """SoundFaithfulnessBackend: factorial/gcd claims, kernel-decided two-regime/period-split."""

    kernel: object
    name: str = "factgcd-decided"
    cost_rank: int = 96        # after lean_decided (90) … power_mod (95)

    def applies(self, prop: Propositio) -> bool:
        en, ex = prop.enuntiatio, prop.expressio
        if en is None or ex is None or not (en.claim_domain and en.claim_property and ex.established_domain):
            return False
        try:
            vs = free_vars(en.claim_domain, en.claim_property, ex.established_domain)
            faithfulness_pair(en.claim_domain, en.claim_property, ex.established_domain)
        except RenderError:
            return False
        skel = classify_factgcd(en.claim_property)
        return skel is not None and len(vs) == EXACT_VARS and vs == [skel.var]

    def check(self, prop: Propositio) -> FaithfulnessVerdict:
        en, ex = prop.enuntiatio, prop.expressio
        data = {"claim_domain": en.claim_domain, "claim_property": en.claim_property,
                "established_domain": ex.established_domain}
        ok, detail = decide_certificate(data, self.kernel)
        if not ok:
            return FaithfulnessVerdict(verdict=Verdict.DEFER, producer="factgcd/defer", detail=detail)
        statement = canonical_statement(**data)
        cert = Certificate(kind=KIND, rechecked=True, data=data, detail={"statement": statement})
        return FaithfulnessVerdict(verdict=Verdict.PASS, producer="factgcd/kernel",
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
    gate.sound_backends = tuple(gate.sound_backends) + (FactGcdFaithfulness(kernel=kernel),)
    gate.recheckers[KIND] = make_rechecker(kernel)
    gate.templates[KIND] = prop_statement_template
