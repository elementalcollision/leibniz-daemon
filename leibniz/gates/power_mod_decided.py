"""ADR 0065 — the order-split faithfulness backend for SYMBOLIC-EXPONENT modular claims.

The fifth decision procedure of the ceiling-raiser: claims about `base^n % m` with a **variable
exponent** — the ADR 0035 fragment Z3 already decides by order-reduction, now decidable by the Lean
kernel too (and hence provable as promulgable LAWS). For `gcd(base, m) = 1` the sequence
`base^k mod m` is purely periodic with period `ord` (the multiplicative order), so a claim about
`base^n % m` reduces to its `ord` residue arms. The kernel decides that reduction (validated against
Lean 4.31):

1. `key : ∀ k : ℕ, base^k % m = base^(k % ord) % m` — proved `conv_lhs => rw [← Nat.div_add_mod k ord,
   pow_add, pow_mul]; rw [Nat.mul_mod, Nat.pow_mod]; norm_num`. **The kernel checks the period here**:
   a wrong `ord` leaves `(base^ord % m) ≠ 1` and `norm_num` cannot close ⇒ DEFER (kernel-validated
   negative control).
2. `bridge : ∀ t : ℕ, Int.emod ((base : ℤ)^t) m = ((base^t % m : ℕ) : ℤ)` — `push_cast; rfl` (the
   ℤ-box statement's power is computed in ℕ and cast back).
3. `rw [bridge]`, instantiate `key` at `(n).toNat`, `set r := (n).toNat % ord`, `interval_cases r <;>
   norm_num` — each of the `ord` arms is a closed arithmetic fact the kernel evaluates.

A **false** claim fails at some arm's `norm_num` ⇒ the kernel rejects ⇒ **DEFER** — the kernel, not
the template, decides.

Fragment (owned at the classifier — the renderer is more permissive):
- ONE atom family `base**n % m ⋈ c`: CONSTANT base ≥ 2, BARE variable exponent, CONSTANT modulus
  m ≥ 2, `gcd(base, m) = 1` (else not purely periodic → DEFER — mirror of smt_z3's ADR 0035 guard);
- `eq` / `neq` single atom, or an or-disjunction of `==` atoms over the SAME `base**n % m`
  (residue_set), every residue in `[0, m)`;
- the claim's ONLY free variable is the exponent; `ord ≤ MAX_ORDER` (the smt_z3 cap, mirrored).

**Fail-closed by default.** Nothing registers this in the assembly. Activation is an OPERATOR action
(`register`, gated in `assembly.maybe_register_power_mod` behind the same `LEIBNIZ_LEAN_DECIDED` REPL
activation); until then no PASS of this kind is accepted. Producer `power_mod/kernel`, admitted to
`FAITHFULNESS_PRODUCERS` by the operator (ADR 0041), like the other decision-procedure producers.
"""
from __future__ import annotations

import ast
import math
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

KIND = "power-mod-faithfulness"
# The power-mod fragment is inherently single-variable (a bare exponent). Invariant 5 is respected on
# COST grounds: the FaithfulnessGate consults sound backends only after the cheap probes DEFER, and the
# Z3 order-reduction (ADR 0035) already covers this fragment when its box covers a period — so this
# backend fires exactly where the cheap path could not.
EXACT_VARS = 1


def _multiplicative_order(base: int, m: int) -> Optional[int]:
    """ord(base) in (ℤ/mℤ)* — None if gcd(base, m) ≠ 1 (mirrors smt_z3's ADR 0035 guard)."""
    if math.gcd(base, m) != 1:
        return None
    r, k = base % m, 1
    while r != 1:
        r, k = (r * base) % m, k + 1
        if k > m:                                        # cannot happen for gcd=1; belt-and-suspenders
            return None
    return k


@dataclass(frozen=True)
class PowerSkeleton:
    """A classified `base**n % m` claim: op ∈ {'eq','neq','residue_set'}, the constant base and
    modulus, the exponent variable name, the multiplicative order, and the asserted residues."""

    op: str
    base: int
    modulus: int
    var: str
    ord: int
    residues: tuple[int, ...]


def _power_atom(node: ast.AST) -> Optional[tuple[str, int, str, int, int]]:
    """`(base**var % m) ⋈ c` with ⋈ ∈ {==, !=} → (op, base, var, m, c); else None."""
    if not (isinstance(node, ast.Compare) and len(node.ops) == 1 and len(node.comparators) == 1):
        return None
    op = {ast.Eq: "eq", ast.NotEq: "neq"}.get(type(node.ops[0]))
    if op is None:
        return None
    left, right = node.left, node.comparators[0]
    c = right.value if isinstance(right, ast.Constant) and isinstance(right.value, int) \
        and not isinstance(right.value, bool) else None
    if c is None or not (isinstance(left, ast.BinOp) and isinstance(left.op, ast.Mod)):
        return None
    m = left.right.value if isinstance(left.right, ast.Constant) and isinstance(left.right.value, int) \
        and not isinstance(left.right.value, bool) else None
    pw = left.left
    if (m is None or m < 2 or not (isinstance(pw, ast.BinOp) and isinstance(pw.op, ast.Pow))
            or not isinstance(pw.right, ast.Name)):
        return None
    b = pw.left.value if isinstance(pw.left, ast.Constant) and isinstance(pw.left.value, int) \
        and not isinstance(pw.left.value, bool) else None
    if b is None or b < 2:
        return None
    return op, b, pw.right.id, m, c


def classify_power(claim_property: str) -> Optional[PowerSkeleton]:
    """Classify `claim_property` into a power-mod skeleton, or None (→ DEFER)."""
    try:
        tree = _parse(claim_property)
    except RenderError:
        return None
    atoms: list[tuple[str, int, str, int, int]] = []
    if isinstance(tree, ast.BoolOp) and isinstance(tree.op, ast.Or):
        for v in tree.values:
            a = _power_atom(v)
            if a is None or a[0] != "eq":                # residue_set: or-of-== only
                return None
            atoms.append(a)
    else:
        a = _power_atom(tree)
        if a is None:
            return None
        atoms.append(a)
    # one atom family: same (base, var, modulus) across all disjuncts
    if len({(b, v, m) for _op, b, v, m, _c in atoms}) != 1:
        return None
    op0, base, var, m, _ = atoms[0]
    residues = tuple(c for *_x, c in atoms)
    if any(not (0 <= c < m) for c in residues):          # out-of-range residue → degenerate → DEFER
        return None
    if len(atoms) > 1 and len(set(residues)) != len(residues):
        return None
    ordv = _multiplicative_order(base, m)
    if ordv is None or ordv > MAX_ORDER:                 # not purely periodic / over the cap → DEFER
        return None
    op = op0 if len(atoms) == 1 else "residue_set"
    return PowerSkeleton(op=op, base=base, modulus=m, var=var, ord=ordv, residues=residues)


# --- gate-owned proof construction (order-split; validated against the real Lean 4.31 kernel) -------


def power_proof(skel: PowerSkeleton, n_domain: int) -> str:
    """Gate-owned proof of `∀ n, box → …dom… → P(base^n % m)`: the ℕ period key + the ℤ cast bridge +
    `interval_cases` over the `ord` arms. `n_domain` = 2 for the faithfulness pair's property leg
    (established + claim_domain), 1 for the prover LAW (claim_domain only)."""
    b, m, o, v = skel.base, skel.modulus, skel.ord, skel.var
    intro_all = f"{v} _ " + " ".join("_" for _ in range(n_domain))
    return f"""by
  have key : ∀ k : Nat, {b}^k % {m} = {b}^(k % {o}) % {m} := by
    intro k
    conv_lhs => rw [← Nat.div_add_mod k {o}, pow_add, pow_mul]
    rw [Nat.mul_mod, Nat.pow_mod]
    norm_num
  have bridge : ∀ t : Nat, Int.emod (({b} : ℤ)^t) {m} = (({b}^t % {m} : Nat) : ℤ) := by
    intro t
    push_cast
    rfl
  intro {intro_all}
  rw [bridge]
  have h := key ({v}).toNat
  have hlt : ({v}).toNat % {o} < {o} := Nat.mod_lt _ (by norm_num)
  set r := ({v}).toNat % {o} with hr
  rw [h]
  interval_cases r <;> norm_num"""


# --- the gate-owned decision (used identically by the backend AND the re-checker) ------------------


def decide_certificate(data: object, kernel) -> tuple[bool, dict]:
    """Decide the faithfulness pair for a power-mod claim by constructing all four statements +
    gate-owned proofs and requiring the KERNEL to accept each with a clean axiom footprint.
    Exact-or-DEFER; total. Mirrors `mixed_modulus_decided.decide_certificate`, swapping the classifier
    and the order-split property proof."""
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
    skel = classify_power(cp)
    if skel is None:
        return False, {"reason": "claim_property outside the power-mod fragment"}
    if len(vs) != EXACT_VARS or vs != [skel.var]:
        return False, {"reason": f"fragment is single-variable (the exponent); got {vs}"}

    w_claim = find_witness([cd], vs)
    w_ec = find_witness([ed, cd], vs)
    if w_claim is None or w_ec is None:
        return False, {"reason": "no ∃-witness found (empty or out-of-box domain)"}

    checks: list[tuple[str, str, list[str]]] = [
        ("coverage", pair["coverage"], coverage_proofs(len(vs))),
        ("property", pair["property"], [power_proof(skel, n_domain=2)]),
        ("exists_claim", pair["exists_claim"], witness_proof(w_claim)),
        ("exists_ec", pair["exists_ec"], witness_proof(w_ec)),
    ]
    from leibniz.propositio import Expressio
    detail: dict = {"witness_claim": w_claim, "witness_ec": w_ec,
                    "base": skel.base, "modulus": skel.modulus, "ord": skel.ord}
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
class PowerModFaithfulness:
    """SoundFaithfulnessBackend: symbolic-exponent modular claims, kernel-decided by order-split."""

    kernel: object
    name: str = "power-mod-decided"
    cost_rank: int = 95        # after lean_decided (90) / minmax (91) / boolean (93) / mixed (94)

    def applies(self, prop: Propositio) -> bool:
        en, ex = prop.enuntiatio, prop.expressio
        if en is None or ex is None or not (en.claim_domain and en.claim_property and ex.established_domain):
            return False
        try:
            vs = free_vars(en.claim_domain, en.claim_property, ex.established_domain)
            faithfulness_pair(en.claim_domain, en.claim_property, ex.established_domain)
        except RenderError:
            return False
        skel = classify_power(en.claim_property)
        return skel is not None and len(vs) == EXACT_VARS and vs == [skel.var]

    def check(self, prop: Propositio) -> FaithfulnessVerdict:
        en, ex = prop.enuntiatio, prop.expressio
        data = {"claim_domain": en.claim_domain, "claim_property": en.claim_property,
                "established_domain": ex.established_domain}
        ok, detail = decide_certificate(data, self.kernel)
        if not ok:
            return FaithfulnessVerdict(verdict=Verdict.DEFER, producer="power_mod/defer", detail=detail)
        statement = canonical_statement(**data)
        cert = Certificate(kind=KIND, rechecked=True, data=data, detail={"statement": statement})
        return FaithfulnessVerdict(verdict=Verdict.PASS, producer="power_mod/kernel",
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
    gate.sound_backends = tuple(gate.sound_backends) + (PowerModFaithfulness(kernel=kernel),)
    gate.recheckers[KIND] = make_rechecker(kernel)
    gate.templates[KIND] = prop_statement_template
