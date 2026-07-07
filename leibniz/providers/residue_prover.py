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

from typing import Optional

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
)

IMPORTS = ("Mathlib.Tactic",)   # ZMod + intCast_eq_intCast_iff' resolve here (as in lean_decided)


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
    fragment (reusing `lean_decided.classify_property`: pure-poly `% m ⋈ c`, eq/neq/residue-set,
    two or three variables, residue product within budget). Total-or-abstain; never raises.

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
