"""ADR 0058 increment 1 — the deterministic modular-polynomial proof GENERATOR.

The prover-reach half of the ceiling-raiser: after `lean_decided` (ADR 0056) lets a
two-variable modular-polynomial claim pass faithfulness, the LLM ensemble still cannot
prove it. The **same ZMod-bridge math that certifies faithfulness proves the theorem** —
kernel-validated for the exact live claim `((a·b)²+a·b) % 6 ∈ {0,2}`.

This module is the pure, deterministic **generator** — no I/O, no RNG, no kernel: given a
modular claim (domain + property in the faithfulness DSL), it renders the **canonical
ℤ-with-box LAW theorem** and a **ZMod-bridge proof** that discharges it. The canonical form
is the *same* one `lean_decided` renders and vets (`dsl_to_lean`), so the statement proved is
the statement certified faithful (ADR 0058 amendment A2). It reuses `lean_decided`'s
classifier and validated proof templates; the LAW proof is `property_proof` with a single
domain antecedent (`∀ vars, box → claim_domain → claim_property`) rather than the
faithfulness pair's two.

**This module decides nothing and is not yet wired to any prover/consensus seam.** The
`ResiduePolyProver` (the prover-interface adapter) and the class-identity allowlist +
promote-on-one counting (ADR 0058 A1/A3/A4) are increment 2 — where the kernel re-verifies
every generated proof via `LeanVerifier.discharge` and a generator bug is a DEFER, never an
unsound law. Here the generator is exercised only against a real kernel in tests.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, replace
from typing import Optional

from leibniz.backends.lean_axioms import axiom_closure
from leibniz.dsl_to_lean import RenderError, _binder, _nonneg, free_vars, render_pred
from leibniz.gates.lean_decided import (
    MAX_RESIDUE_CELLS,
    MAX_VARS,
    MIN_VARS,
    Skeleton,
    _casts,
    _key_lemma,
    _or_nest,
    _term,
    classify_property,
    conjunction_proof,
)
from leibniz.propositio import Demonstratio
from leibniz.trust import FAITHFULNESS_EDGE
from leibniz.types import EdgeEvidence, Verdict
from leibniz.verifiers import normalize_statement

IMPORTS = ("Mathlib.Tactic",)   # ZMod + intCast_eq_intCast_iff' resolve here (as in lean_decided)
# The producer stamped by the STATEMENT-BINDING faithfulness backend (lean_decided). The fast-path
# promotes on one kernel verification ONLY for a claim this backend certified, because it alone
# byte-binds the canonical ℤ-box statement to the claim (ADR 0056 obligation 5 / ADR 0058 A2).
LEAN_DECIDED_PRODUCER = "lean_decided/kernel"


def law_statement(claim_domain: str, claim_property: str, vs: list[str]) -> str:
    """The canonical ℤ-with-box LAW proposition: `∀ (vars : ℤ), 0≤vars → claim_domain →
    claim_property`. Raises :class:`RenderError` if either predicate is outside the DSL."""
    cd, cp = render_pred(claim_domain), render_pred(claim_property)
    box = _nonneg(vs, "→")
    return f"{_binder('∀', vs)} {box}{cd} → {cp}"


def _law_proof(skel: Skeleton, vs: list[str]) -> str:
    """The ZMod-bridge proof of the LAW (`… → claim_domain → claim_property`). Identical to
    `lean_decided.property_proof` except it introduces **one** domain antecedent (claim_domain),
    not the pair's two. A false claim makes the ZMod key's `decide` refuse → kernel rejects →
    the draft is not kernel-verified → it simply does not count (increment 2)."""
    if skel.op == "conjunction":
        return conjunction_proof(skel, vs, n_domain=1)   # claim_domain only (ADR 0059)
    poly = _term(skel.poly_src)
    m = skel.modulus
    intro_all = " ".join(vs) + " " + " ".join(f"_h{v}" for v in vs) + " _"   # box hyps + claim_domain
    key = _key_lemma(skel, vs)
    casts = _casts(vs, m)
    if skel.op == "neq":
        c = skel.residues[0]
        return (f"by\n  have key : {key} := by decide\n  intro {intro_all} h\n"
                f"  have h' : {poly} % {m} = {c} := h\n  apply key {casts}\n"
                f"  have hz : (({poly} : ℤ) : ZMod {m}) = (({c} : ℤ) : ZMod {m}) := by\n"
                f"    rw [ZMod.intCast_eq_intCast_iff']\n    simpa using h'\n"
                f"  push_cast at hz\n  exact hz")
    if skel.op == "eq":
        c = skel.residues[0]
        return (f"by\n  have key : {key} := by decide\n  intro {intro_all}\n"
                f"  have hk := key {casts}\n"
                f"  have hz : (({poly} : ℤ) : ZMod {m}) = (({c} : ℤ) : ZMod {m}) := by\n"
                f"    push_cast\n    exact hk\n"
                f"  rw [ZMod.intCast_eq_intCast_iff'] at hz\n"
                f"  have h' : {poly} % {m} = {c} := by simpa using hz\n  exact h'")
    # residue_set
    k = len(skel.residues)
    rcases_pat = " | ".join(["h"] * k)
    blocks = []
    for i, c in enumerate(skel.residues):
        select = _or_nest(i, k, "h'")
        blocks.append(
            f"  · have hz : (({poly} : ℤ) : ZMod {m}) = (({c} : ℤ) : ZMod {m}) := by\n"
            f"      push_cast\n      exact h\n"
            f"    rw [ZMod.intCast_eq_intCast_iff'] at hz\n"
            f"    have h' : {poly} % {m} = {c} := by simpa using hz\n    exact {select}"
        )
    return (f"by\n  have key : {key} := by decide\n  intro {intro_all}\n"
            f"  have hk := key {casts}\n  rcases hk with {rcases_pat}\n" + "\n".join(blocks))


def residue_law(name: str, claim_domain: str, claim_property: str) -> Optional[tuple[str, str]]:
    """The deterministic generator: `(theorem_src, proof_src)` for the canonical ℤ-box law of a
    modular-polynomial claim, or **None** (abstain) when the claim is outside the reducible
    fragment (reusing `lean_decided.classify_property`: pure-poly `% m ⋈ c`, eq/neq/residue-set, or
    an ADR 0059 single-modulus **conjunction** of such atoms, two or three variables, residue product
    within budget). Total-or-abstain; never raises.

    Soundness is not this function's responsibility: whatever it emits, the Lean kernel
    re-verifies against the *actual* `theorem_src` (increment 2). A wrong or malformed proof
    fails to elaborate → not kernel-verified → discarded. This is a PROPOSER, not a decider."""
    try:
        if not (claim_domain and claim_property):
            return None
        skel = classify_property(claim_property)
        if skel is None:
            return None
        vs = free_vars(claim_domain, claim_property)
        if not (MIN_VARS <= len(vs) <= MAX_VARS) or skel.modulus ** len(vs) > MAX_RESIDUE_CELLS:
            return None
        theorem_src = f"theorem {name} : {law_statement(claim_domain, claim_property, vs)}"
        return theorem_src, _law_proof(skel, vs)
    except RenderError:
        return None


def _law_name(claim_domain: str, claim_property: str) -> str:
    """A stable, valid Lean identifier for the law, derived from its contract."""
    h = hashlib.sha256(f"{claim_domain}␟{claim_property}".encode()).hexdigest()[:12]
    return f"residue_law_{h}"


# --- ADR 0058 increment 2: the DEMONSTRATE fast-path (decision procedure, promote-on-one) ---------


@dataclass
class ResidueDemonstrate:
    """DEMONSTRATE fast-path realising ADR 0058's *decision-procedure promotability* — the more
    conservative form of the reviewed design (there is **no pluggable prover to masquerade as**; the
    decision procedure is this single, fixed, operator-activated code path).

    For a modular-polynomial claim it proves the **gate-rendered canonical ℤ-box LAW**
    (`residue_law`, kernel-validated) and, on the **single** kernel verification, records the proof
    edge — **promote-on-one**. Everything else (non-modular claims, or a claim whose generated proof
    the kernel rejects) **falls through to `inner`** (the unchanged N+1 consensus ensemble).

    How the review's obligations are met **without touching `consensus.py`/`trust.py`/`validate_path`/
    `test_invariants`** (all byte-identical):

    - **A1 (masquerade):** none possible — the decision procedure is not a registrable prover; it is
      this hardcoded path, reached only when the operator activates it and only for claims `residue_law`
      accepts. There is no identity string or class to forge.
    - **A2 (statement binding):** the promulgated `theorem_src` is **re-rendered here** from the DSL
      contract the faithfulness gate vetted, so the proven statement *is* the certified one — not the
      autoformalizer's free-text `theorem_src`. Enforced two ways: the fast-path promotes **only** a
      claim that carries a **`lean_decided/kernel` faithfulness PASS edge** (the sole statement-binding
      backend, which byte-binds the canonical statement and DEFERs vacuous domains), and it refreshes
      `normalized_hash`/`established_domain` so the ledger + self-dedup key the published statement.
    - **A4 (axiom footprint):** a promotion-time `axiom_closure` rejects `sorryAx`/`Lean.ofReduceBool`
      (`native_decide`); the generated proofs use only kernel `decide`.
    - **Kernel-gated (the crux):** `LeanVerifier.discharge` remains the sole `kernel_verified` writer;
      the recorded edge is its own `MECHANICAL/PASS/KERNEL_PRODUCER` edge. A generator bug ⇒ the kernel
      rejects ⇒ fall-through, never an unsound law. Promotion is still gated by `TrustPolicy.validate_path`
      (unchanged) — this path merely does not *add* the N+1 requirement (a consensus-layer policy, never a
      trust-core one) to a deterministic, kernel-verified proof.

    Fail-closed: nothing constructs this unless the operator opts in (see `assembly.maybe_wrap_residue`)."""

    inner: object                 # the wrapped DEMONSTRATE stage (Consensus/Repairing/Decomposing)
    lean: object                  # the LeanVerifier (discharge = sole kernel_verified writer)
    obligation: str = "claim"

    def run(self, prop):
        if self._fastpath(prop):
            return prop
        return self.inner.run(prop)

    def _fastpath(self, prop) -> bool:
        try:
            return self._promote(prop)
        except Exception:
            return False   # any non-kernel surprise → fall through to the ensemble, never crash DEMONSTRATE

    def _promote(self, prop) -> bool:
        en, expr = prop.enuntiatio, getattr(prop, "expressio", None)
        if expr is None or not (en.claim_domain and en.claim_property):
            return False
        # A2 (statement binding): promote-on-one ONLY for a claim the STATEMENT-BINDING faithfulness
        # backend (lean_decided) certified — it alone byte-binds the canonical ℤ-box statement to this
        # claim (and DEFERs empty/vacuous domains via its ∃-witness controls). If faithfulness passed
        # some OTHER way (the Z3 probe, the gaming spine, or the OPEN_FORM judge), the canonical LAW was
        # never vetted *as a statement*, so fall through — no promote-on-one. This makes the fast-path
        # robust regardless of which faithfulness path or deployment config is live.
        if not any(e.edge == FAITHFULNESS_EDGE and e.verdict is Verdict.PASS
                   and e.producer == LEAN_DECIDED_PRODUCER for e in prop.edges):
            return False
        gen = residue_law(_law_name(en.claim_domain, en.claim_property), en.claim_domain, en.claim_property)
        if gen is None:
            return False
        theorem_src, proof = gen
        # A2: prove and promulgate the gate-rendered canonical statement. Refresh normalized_hash and
        # established_domain so the ledger + ADR-0052 self-dedup key the PUBLISHED statement, not the
        # autoformalizer's stale one (Mathlib.Tactic pins ZMod / Euclidean %).
        law_expr = replace(expr, theorem_src=theorem_src, imports=IMPORTS,
                           established_domain=en.claim_domain,
                           normalized_hash=normalize_statement(theorem_src))
        demo = Demonstratio(proof_obligation=self.obligation, proof_src=proof)
        ev = self.lean.discharge(law_expr, demo)              # sole kernel_verified writer
        if not (demo.kernel_verified and ev.verdict is Verdict.PASS):
            return False                                      # kernel rejected → fall to the ensemble
        # A4: clean axiom footprint (no native_decide / sorry). backend needed for `#print axioms`.
        backend = getattr(self.lean, "backend", None)
        if backend is None or not axiom_closure(backend, theorem_src, proof, IMPORTS).get("ok"):
            return False
        if getattr(prop, "signature", None) is not None:      # keep novelty/dedup identity in sync
            prop.signature = replace(prop.signature, formal_hash=law_expr.normalized_hash)
        prop.expressio = law_expr                             # promulgate the canonical statement
        prop.demonstratio = demo
        prop.record(EdgeEvidence(
            edge=ev.edge, tier=ev.tier, verdict=ev.verdict,   # the kernel's own verdict, never hardcoded
            detail={**ev.detail, "decision_procedure": "residue-poly-zmod", "consensus": 1},
            cost_units=ev.cost_units, producer=ev.producer,   # KERNEL_PRODUCER, preserved from discharge
        ))
        return True
