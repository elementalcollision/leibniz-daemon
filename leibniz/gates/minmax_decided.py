"""ADR 0059 (min/max half) — the order-split faithfulness backend for min/max identities.

The **second** decision procedure of the ceiling-raiser, parallel to `lean_decided` (the modular
one) but for a disjoint fragment: **algebraic symmetric-function identities over `min`/`max`** — e.g.
``max(a,b)² + min(a,b)² == a² + b²``. These are polynomial identities once every `min`/`max` is
resolved by the variable ordering; the Lean **kernel** decides them by an exhaustive `le_total`
case-split, `simp`-resolving each `min`/`max`, then `ring` on the resulting polynomial goal. A
**non-identity makes `ring` fail on some ordering branch → the kernel rejects → DEFER** — the kernel,
not the template, is the decider (kernel-validated against Lean 4.31).

Built to the ADR 0059 min/max amendments (B.1–B.4) the adversarial review made binding:

- **B.2 / obligation 5 (statement binding).** `register` installs BOTH `recheckers[KIND]` AND
  `templates[KIND]` (`prop_statement_template`), so `FaithfulnessGate.check` refuses a PASS whose
  certificate statement is not byte-identical to the canonical statement rendered from the prop's own
  fields. Without the template the gate would leave the statement unbound (`faithfulness.py:144`).
- **B.3 (fragment owned at the classifier).** `dsl_to_lean._term` renders ≥3-ary / nested / compound-arg
  `min`/`max`, so this backend — not the renderer — owns the restriction: top-level `Eq` **or a
  conjunction of ≤ `MAX_MINMAX_EQS` `Eq`s** (ADR 0059 Path A), every `min`/`max` a **bare 2-arg call over
  two distinct variables**, LHS/RHS min/max-polynomials, ≥1 `min`/`max` present, ≤ `MAX_VARS` vars, branch
  count `2^#pairs ≤ MAX_MINMAX_BRANCHES` on the UNION of pairs. Anything else → DEFER.
- **B.4 (domain-free ⇒ ∃-witness legs gate non-vacuity, not truth).** An identity holds independent of
  the claim's `established_domain`, so the ∃-witness legs add no power to the identity's TRUTH; they
  remain a deliberate non-vacuity gate over the non-negative witness box (identical to the modular path
  — an empty/out-of-box `claim_domain` DEFERs). A faithful identity over a negative-only or large domain
  is a conservative out-of-scope yield choice, never an unsound outcome.
- **Order-split is a sound proof-search heuristic, not a complete decision procedure.** It proves the
  restricted fragment (2-arg min/max over bare variables); compound / nested args are DEFERred, not
  mis-proved. Soundness (the only thing that matters): `ring` closes only genuine polynomial identities
  per branch, and every appearing `min`/`max` pair is split, so a false identity leaves some branch's
  polynomial goal non-trivial → `ring` fails → DEFER.

**Fail-closed by default.** Nothing imports or registers this module in the assembly. Activation is an
OPERATOR action (`register`, gated in `assembly.maybe_register_minmax_decided` behind the same
`LEIBNIZ_LEAN_DECIDED` REPL activation as the modular backend); until then `recheckers.get(KIND)` is
`None` and no PASS of this kind is ever accepted. The producer `minmax_identity/kernel` is admitted to
`FAITHFULNESS_PRODUCERS` by the operator (ADR 0041), like `lean_decided/kernel`.
"""
from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from typing import Callable, Optional

from leibniz.backends.lean_axioms import axiom_closure
from leibniz.backends.smt_z3 import MAX_POW
from leibniz.dsl_to_lean import (
    RenderError,
    _parse,
    canonical_statement,
    faithfulness_pair,
    free_vars,
)
from leibniz.gates.lean_decided import (
    IMPORTS,
    MAX_VARS,
    MIN_VARS,
    _thm,
    coverage_proofs,
    find_witness,
    witness_proof,
)
from leibniz.gates.sound_backends import Certificate, FaithfulnessVerdict
from leibniz.propositio import Propositio
from leibniz.types import Verdict

KIND = "minmax-identity-faithfulness"
# 2^#pairs branches; MAX_VARS=3 ⇒ ≤ C(3,2)=3 pairs ⇒ ≤ 8 branches. An explicit cap keeps the
# case-split bounded even if a future MAX_VARS bump would otherwise blow it up.
MAX_MINMAX_BRANCHES = 8
# A conjunction of ≤ this many Eq-identities is admitted (ADR 0059 Path A); the union of their pairs
# still obeys MAX_MINMAX_BRANCHES.
MAX_MINMAX_EQS = 4
# The Mathlib rewrite lemmas that resolve a min/max once its arguments' order is known.
_LEMMAS = "max_eq_left, max_eq_right, min_eq_left, min_eq_right"


# --- identity-skeleton classification (B.3: the fragment gate lives HERE, not in the renderer) ----


@dataclass(frozen=True)
class MinMaxSkeleton:
    """A classified min/max identity: a single `LHS = RHS` (`n_eqs == 1`) or a conjunction of `n_eqs`
    such equalities (ADR 0059 Path A). `pairs` is the sorted UNION of the variable pairs `(x, y)`
    appearing as `min(x,y)`/`max(x,y)` across all conjuncts — the pairs the proof splits `le_total`
    on. `lhs`/`rhs` are the FIRST conjunct's sides (vestigial: the proof reads only `pairs`/`n_eqs`,
    and the statement is rendered from the DSL, not from these)."""

    lhs: ast.AST
    rhs: ast.AST
    pairs: tuple[tuple[str, str], ...]
    n_eqs: int = 1


def _mmpoly(node: ast.AST, pairs: set) -> bool:
    """A *min/max polynomial*: variables, int consts, `+ - *`, constant `^`, unary minus, and
    `min(x,y)`/`max(x,y)` where x,y are **two distinct bare variables**. Collects each such pair into
    `pairs`. Returns False on anything else — nested/≥3-ary/compound-arg min/max, division, mod, etc.
    This is where B.3's fragment restriction is enforced (the renderer is more permissive)."""
    if isinstance(node, ast.Name):
        return True
    if isinstance(node, ast.Constant):
        return isinstance(node.value, int) and not isinstance(node.value, bool)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        return _mmpoly(node.operand, pairs)
    if isinstance(node, ast.BinOp):
        if isinstance(node.op, (ast.Add, ast.Sub, ast.Mult)):
            return _mmpoly(node.left, pairs) and _mmpoly(node.right, pairs)
        if isinstance(node.op, ast.Pow):
            return (_mmpoly(node.left, pairs) and isinstance(node.right, ast.Constant)
                    and isinstance(node.right.value, int) and 0 <= node.right.value <= MAX_POW)
        return False
    if isinstance(node, ast.Call):
        if not (isinstance(node.func, ast.Name) and node.func.id in ("min", "max")
                and len(node.args) == 2 and not node.keywords):
            return False    # ≥3-ary / keyword / unknown callee → DEFER
        x, y = node.args
        if not (isinstance(x, ast.Name) and isinstance(y, ast.Name) and x.id != y.id):
            return False    # nested or compound arg, or degenerate min(a,a) → DEFER
        pairs.add(tuple(sorted((x.id, y.id))))
        return True
    return False


def _eq_sides(node: ast.AST) -> Optional[tuple[ast.AST, ast.AST]]:
    """`(lhs, rhs)` if `node` is a single top-level `==`, else None."""
    if (isinstance(node, ast.Compare) and len(node.ops) == 1
            and isinstance(node.ops[0], ast.Eq) and len(node.comparators) == 1):
        return node.left, node.comparators[0]
    return None


def classify_identity(claim_property: str) -> Optional[MinMaxSkeleton]:
    """Classify `claim_property` into a supported min/max identity skeleton, or None (→ DEFER). Accepts
    a single `LHS == RHS` or a top-level conjunction of such equalities (ADR 0059 Path A); every
    conjunct's sides must be min/max-polynomials, and the UNION of min/max pairs must be non-empty and
    within the branch budget."""
    try:
        tree = _parse(claim_property)
    except RenderError:
        return None
    if isinstance(tree, ast.BoolOp) and isinstance(tree.op, ast.And):
        eqs = [_eq_sides(v) for v in tree.values]        # every conjunct a bare `==` (rejects nested And / ↔ / non-Eq)
        if any(e is None for e in eqs) or not (2 <= len(eqs) <= MAX_MINMAX_EQS):
            return None
    else:
        e = _eq_sides(tree)
        if e is None:
            return None                                  # top-level must be `==` or a conjunction of `==`
        eqs = [e]
    pairs: set = set()
    for lhs, rhs in eqs:
        if not (_mmpoly(lhs, pairs) and _mmpoly(rhs, pairs)):
            return None
    if not pairs:
        return None    # no min/max anywhere → a pure-poly identity is not this backend's job
    if 2 ** len(pairs) > MAX_MINMAX_BRANCHES:
        return None    # branch budget on the UNION of pairs
    return MinMaxSkeleton(lhs=eqs[0][0], rhs=eqs[0][1], pairs=tuple(sorted(pairs)), n_eqs=len(eqs))


# --- gate-owned proof construction (order-split; validated against the real Lean 4.31 kernel) ------


def _hyp_base(vs: list[str]) -> str:
    """A hypothesis-name base no claim variable shadows: `h`, else `hh`, `hhh`, … until no variable
    matches `<base><digits>`. Keeps the order-split's ordering hyps (`{base}0,{base}1,…`) disjoint from
    the claim's own identifiers, so a variable literally named `h0` yields a valid proof rather than a
    spurious DEFER. Robustness only — a name clash never risked unsoundness (`ring` still requires the
    genuine polynomial identity in the real fvar), only yield."""
    base = "h"
    while any(re.fullmatch(base + r"\d+", v) for v in vs):
        base += "h"
    return base


def _order_split(pairs: tuple[tuple[str, str], ...], base: str) -> str:
    """The order-split tail: `rcases le_total` on every variable pair (hyps `{base}0,{base}1,…`), then
    across all branches `simp only` the min/max-resolving lemmas + those exact hyps, then `ring`.
    Referencing ONLY the hyps that exist is essential — a stray hyp would be an unknown identifier →
    elaboration failure → DEFER for the wrong reason. `base` is chosen (`_hyp_base`) to never collide
    with a claim variable."""
    hyps = ", ".join(f"{base}{i}" for i in range(len(pairs)))
    rc = " <;>\n    ".join(f"rcases le_total {x} {y} with {base}{i} | {base}{i}"
                           for i, (x, y) in enumerate(pairs))
    return f"  {rc} <;>\n    simp only [{_LEMMAS}, {hyps}] <;>\n    ring"


def identity_proof(skel: MinMaxSkeleton, vs: list[str], n_domain: int) -> str:
    """Gate-owned proof of `∀ vars, box → …dom… → (LHS = RHS)` — or of a conjunction of such
    equalities: intro the vars + box + `n_domain` domain antecedents (all unused by the algebra), then
    the order-split over the UNION of pairs. For a conjunction (`n_eqs > 1`) the goal is first split by
    `refine ⟨…⟩` and the order-split is applied to every resulting equality via `<;>` — each equality is
    a polynomial identity once the (shared) orderings are fixed, so a false conjunct fails `ring` on
    some branch ⇒ DEFER. `n_domain` is 2 for the faithfulness pair's property leg, 1 for the prover LAW."""
    intro_all = (" ".join(vs) + " " + " ".join("_" for _ in vs)
                 + (" " + " ".join("_" for _ in range(n_domain)) if n_domain else ""))
    split = _order_split(skel.pairs, _hyp_base(vs))
    if skel.n_eqs > 1:
        holes = ", ".join("?_" for _ in range(skel.n_eqs))
        split = f"  refine ⟨{holes}⟩ <;>\n  ({split.strip()})"
    return f"by\n  intro {intro_all}\n{split}"


# --- the gate-owned decision (used identically by the backend AND the re-checker) ------------------


def decide_certificate(data: object, kernel) -> tuple[bool, dict]:
    """Decide the faithfulness pair for `data` = {claim_domain, claim_property, established_domain} of a
    min/max identity by constructing all four statements AND their gate-owned proofs and requiring the
    KERNEL to accept each with a clean axiom footprint (no sorryAx / Lean.ofReduceBool). Exact-or-DEFER;
    total (never raises). Mirrors `lean_decided.decide_certificate`, swapping the classifier + the
    property proof (order-split) and the residue budget for the branch budget."""
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
    skel = classify_identity(cp)
    if skel is None:
        return False, {"reason": "claim_property outside the min/max identity fragment"}

    # ∃-witness legs (B.4). An identity is true independent of its domain, so these legs add no
    # discriminating power to the identity's TRUTH; they remain a deliberate NON-VACUITY gate over the
    # non-negative witness box (identical to the modular path): a claim whose claim_domain has no
    # witness in [0, WITNESS_RANGE) DEFERs before any kernel call. A faithful identity over a
    # negative-only or ≥WITNESS_RANGE domain is therefore intentionally out of scope this increment
    # (a conservative yield choice consistent with lean_decided, never an unsound outcome).
    w_claim = find_witness([cd], vs)
    w_ec = find_witness([ed, cd], vs)
    if w_claim is None or w_ec is None:
        return False, {"reason": "no ∃-witness found (empty or out-of-box domain)"}

    checks: list[tuple[str, str, list[str]]] = [
        ("coverage", pair["coverage"], coverage_proofs(len(vs))),
        ("property", pair["property"], [identity_proof(skel, vs, n_domain=2)]),
        ("exists_claim", pair["exists_claim"], witness_proof(w_claim)),
        ("exists_ec", pair["exists_ec"], witness_proof(w_ec)),
    ]
    from leibniz.propositio import Expressio  # local: avoid cycles at import time
    detail: dict = {"witness_claim": w_claim, "witness_ec": w_ec, "pairs": skel.pairs}
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
    """The canonical statement rendered from PROP'S OWN fields (never from the certificate) — the
    gate compares this to the certificate's claimed statement before any re-check (obligation 5 / B.2).
    Identical rendering to the modular backend; None → unbindable → no PASS."""
    en, ex = prop.enuntiatio, prop.expressio
    if en is None or ex is None or not (en.claim_domain and en.claim_property and ex.established_domain):
        return None
    try:
        return canonical_statement(en.claim_domain, en.claim_property, ex.established_domain)
    except RenderError:
        return None


@dataclass
class MinMaxDecidedFaithfulness:
    """SoundFaithfulnessBackend: min/max symmetric-function identities, kernel-decided by order-split."""

    kernel: object
    name: str = "minmax-decided"
    cost_rank: int = 91        # after the modular lean_decided backend; both run after cheap probes

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
        return classify_identity(en.claim_property) is not None

    def check(self, prop: Propositio) -> FaithfulnessVerdict:
        en, ex = prop.enuntiatio, prop.expressio
        data = {"claim_domain": en.claim_domain, "claim_property": en.claim_property,
                "established_domain": ex.established_domain}
        ok, detail = decide_certificate(data, self.kernel)
        if not ok:
            return FaithfulnessVerdict(verdict=Verdict.DEFER, producer="minmax_identity/defer",
                                       detail=detail)
        statement = canonical_statement(**data)
        cert = Certificate(kind=KIND, rechecked=True, data=data, detail={"statement": statement})
        return FaithfulnessVerdict(verdict=Verdict.PASS, producer="minmax_identity/kernel",
                                   certificate=cert, detail=detail)


def make_rechecker(kernel) -> Callable[[Certificate], bool]:
    """The gate's independent re-checker for this kind: re-derives EVERYTHING from cert.data with
    gate-owned code and replicates the E7 statement pin (template(cert.data) == claimed, builtin-str,
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
    """OPERATOR ACTION (not called anywhere in the assembly): activate this kind on a constructed
    FaithfulnessGate. Installs BOTH the re-checker AND the statement template (B.2). Until called, the
    fail-closed default holds — no PASS of this kind is ever accepted."""
    gate.sound_backends = tuple(gate.sound_backends) + (MinMaxDecidedFaithfulness(kernel=kernel),)
    gate.recheckers[KIND] = make_rechecker(kernel)
    gate.templates[KIND] = prop_statement_template
