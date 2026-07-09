"""ADR 0050 Phase 2 (5th law) — promote the kernel-attested Mafi–Naderi embedded-prime phenomenon to a
promulgated LAW (tier ``kernel-decided``): for the monomial ideal M_{3,2} = (y²z², x²z², x²y²), the
Veronese cap-sum ideal {min(a,2)+min(b,2)+min(c,2) ≥ 4} — which is the integral closure of M_{3,2}
(Mafi–Naderi 2021, Thm 1.6) — strictly contains M_{3,2} and GAINS the embedded associated prime
(x,y,z) at the witness x·y·z (Cor 1.7), while M_{3,2} itself admits no such witness over the box.
Kernel-attested finite core at t = 2; the audited artifact also certifies t = 3 (its namespace reuses
the same def names, so only one instance can ride in a single preamble).

Honesty: the kernel decides facts about the CAP-SUM ideal as defined in the preamble; that this ideal
equals the true integral closure is the cited Mafi–Naderi Theorem 1.6 (confirmed by the daemon's
integral-dependence instrument in the audit cycle). Labelled ``amplified`` + cited accordingly.

Trust boundary UNTOUCHED: ``kernel_verified`` only via ``LeanVerifier.discharge``; ``axiom_closure``
re-checks the WHOLE source; plain ``decide``. The ADR 0062 preamble is a VERBATIM contiguous slice of
``docs/crt/mafi_naderi_certificate.lean`` (the t=2 defs, docstrings included), minus the namespace
wrapper as usual.

Usage:  PYTHONPATH=. python scripts/export_mafi_naderi_law.py [--write]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from leibniz.backends.lean_axioms import axiom_closure  # noqa: E402
from leibniz.backends.lean_repl import LeanReplBackend, available  # noqa: E402
from leibniz.calculemus_site import law_payload  # noqa: E402
from leibniz.propositio import Demonstratio, Enuntiatio, Expressio, Propositio  # noqa: E402
from leibniz.types import ClaimType  # noqa: E402
from leibniz.verifiers import LeanVerifier  # noqa: E402

_ROOT = Path(__file__).resolve().parent.parent
_ARTIFACT = _ROOT / "docs" / "crt" / "mafi_naderi_certificate.lean"
_OUT = _ROOT / "site" / "src" / "content" / "laws" / "mafi_naderi_t2.json"

# The three audited t=2 facts as ONE conjunction: M ⊊ closure (with witness), the (x,y,z)
# embedded-prime witness at x^(1,1,1) for the closure, and no such witness for M over the box.
_THEOREM_SRC = (
    "theorem mafi_naderi_t2_embedded_prime : "
    "((∀ a < 5, ∀ b < 5, ∀ c < 5, inM a b c = true → inClosure a b c = true) "
    "∧ inClosure 1 1 2 = true ∧ inM 1 1 2 = false) "
    "∧ (inClosure 1 1 1 = false ∧ inClosure 2 1 1 = true "
    "∧ inClosure 1 2 1 = true ∧ inClosure 1 1 2 = true) "
    "∧ (∀ a < 5, ∀ b < 5, ∀ c < 5, "
    "¬ (inM a b c = false ∧ inM (a+1) b c = true ∧ inM a (b+1) c = true ∧ inM a b (c+1) = true))"
)

_REFERENCES = [
    {"citation": ("Mafi, A., & Naderi, D. (2021). Integral closure and Hilbert series of a special "
                  "monomial ideal (arXiv:2112.02921). arXiv."),
     "url": "https://arxiv.org/abs/2112.02921"},
    {"citation": ("Huneke, C., & Swanson, I. (2006). Integral closure of ideals, rings, and modules "
                  "(London Mathematical Society Lecture Note Series No. 336). Cambridge University "
                  "Press."),
     "url": ""},
]


def build_preamble() -> str:
    """The t=2 defs (``inClosure``, ``gens``, ``inM``) as a VERBATIM contiguous slice of the audited
    artifact (docstrings included) — from the closure docstring through ``def inM``, inside the
    ``MafiNaderi_t2`` namespace, whose wrapper is dropped as usual (it could never be closed after
    ``_join_proof`` appends the theorem)."""
    lines = _ARTIFACT.read_text().splitlines()
    start = next(i for i, ln in enumerate(lines) if ln.startswith("/-- closure(M_3,2)"))
    end = next(i for i, ln in enumerate(lines) if ln.startswith("def inM"))
    return "\n".join(lines[start:end + 1])


def build_propositio() -> Propositio:
    en = Enuntiatio(
        statement=("The integral closure of the monomial ideal M_{3,2} = (y²z², x²z², x²y²) — the "
                   "Veronese cap-sum ideal of Mafi–Naderi Thm 1.6 — strictly contains M_{3,2} and "
                   "gains the embedded associated prime (x,y,z) at the witness xyz, while the unmixed "
                   "M_{3,2} admits no such witness (Cor 1.7; kernel-attested finite core, t = 2)"),
        claim_type=ClaimType.INVARIANT,
        falsifiable_claim=("a monomial x^(a,b,c), a,b,c < 5, in M_{3,2} but outside the cap-sum ideal; "
                           "or failure of the (x,y,z) colon-witness at x^(1,1,1) for the closure; or "
                           "an (a,b,c) < 5 exhibiting the same embedded-prime behaviour for M_{3,2} "
                           "itself"),
        domain="commutative_algebra",
    )
    ex = Expressio(theorem_src=_THEOREM_SRC, imports=("Mathlib.Tactic",), preamble=build_preamble())
    de = Demonstratio(proof_obligation="mafi_naderi_t2_embedded_prime", proof_src="by decide")
    return Propositio(enuntiatio=en, expressio=ex, demonstratio=de)


def main() -> int:
    write = "--write" in sys.argv
    if not available():
        print("Lean kernel unavailable (docker/image) — cannot discharge. Aborting.")
        return 2
    prop = build_propositio()
    ex, de = prop.expressio, prop.demonstratio
    be = LeanReplBackend(timeout_s=300)
    try:
        edge = LeanVerifier(be).discharge(ex, de)                # THE ONLY kernel_verified writer
        ax = axiom_closure(be, ex.theorem_src, de.proof_src, ex.imports,
                           allowed=frozenset({"propext"}), preamble=ex.preamble)
    finally:
        be.close()

    print("=== ADR 0050 Phase 2 (5th) — Mafi–Naderi embedded prime → amplified law ===")
    print(f"  kernel_verified : {de.kernel_verified}")
    print(f"  qed             : {de.qed}")
    print(f"  proof edge      : {edge.verdict.value} (producer {edge.producer})")
    print(f"  axiom_closure   : ok={ax['ok']} axioms={ax.get('axioms')}")
    if not (de.kernel_verified and de.qed == "Q.E.D." and ax["ok"]):
        print("!! discharge or axiom check failed — NOT emitting a law.")
        return 1
    prop.promulgated = True
    payload = law_payload(prop, published_at="", specimen=False,
                          tier="kernel-decided", origination="amplified", references=_REFERENCES)
    payload["$schema"] = "../../../.astro/collections/laws.schema.json"
    print(f"\n  law id          : {payload['id']}")
    print(f"  tier/origination: {payload['tier']} / {payload['origination']}")
    print(f"  theorem_src     : {payload['theorem_src'][:88]}…")
    print(f"  preamble        : {len(payload['preamble'])} chars ({payload['preamble'].count(chr(10)) + 1} lines)")
    if write:
        _OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
        print(f"\n  WROTE {_OUT.relative_to(_ROOT)}")
    else:
        print("\n  (dry run — pass --write to emit the law JSON)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
