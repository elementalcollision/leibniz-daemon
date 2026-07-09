"""ADR 0050 Phase 2 (9th law) — promote the kernel-attested Steiner systems S(2,8,225) and
S(2,9,289) to a promulgated LAW with ADR 0064 figures: each printed difference family's within-block
differences are exactly the nonzero group elements, once each — so each develops to its Steiner
system, resolving two of the 129 undecided cases in the Handbook of Combinatorial Designs
(Hetman 2026). Labelled ``amplified`` + cited, tier ``kernel-decided``.

Whole-artifact-verbatim preamble (``docs/crt/steiner_designs.lean`` is pure core, namespace-free);
the law theorem restates both decided statements. Two figures draw the base blocks on the group
grids, generated from the same ``blocks8``/``blocks9`` lists the kernel decided over.

Usage:  PYTHONPATH=. python scripts/export_steiner_law.py [--write]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from leibniz.backends.lean_axioms import axiom_closure  # noqa: E402
from leibniz.backends.lean_repl import LeanReplBackend, available  # noqa: E402
from leibniz.calculemus_site import law_payload  # noqa: E402
from leibniz.propositio import Demonstratio, Enuntiatio, Expressio, Propositio  # noqa: E402
from leibniz.types import ClaimType  # noqa: E402
from leibniz.verifiers import LeanVerifier  # noqa: E402

from figures.gen_steiner_figures import s8_225_figure, s9_289_figure  # noqa: E402

_ROOT = Path(__file__).resolve().parent.parent
_ARTIFACT = _ROOT / "docs" / "crt" / "steiner_designs.lean"
_OUT = _ROOT / "site" / "src" / "content" / "laws" / "steiner_s8_225_s9_289.json"

_THEOREM_SRC = ("theorem steiner_s8_225_s9_289 : "
                "(isDiffFamily mods8 blocks8 224 = true) ∧ (isDiffFamily mods9 blocks9 288 = true)")

_REFERENCES = [
    {"citation": ("Hetman, I. (2026). There exist Steiner systems S(2,8,225) and S(2,9,289) "
                  "(arXiv:2509.10673). arXiv / Journal of Combinatorial Designs."),
     "url": "https://arxiv.org/abs/2509.10673"},
    {"citation": ("Colbourn, C. J., & Dinitz, J. H. (Eds.). (2007). Handbook of Combinatorial "
                  "Designs (2nd ed.). CRC Press."),
     "url": "https://www.routledge.com/9781584885061"},
]


def build_preamble() -> str:
    """The ENTIRE audited artifact VERBATIM — pure core (no import line), namespace-free."""
    return _ARTIFACT.read_text().rstrip("\n")


def build_propositio() -> Propositio:
    en = Enuntiatio(
        statement=("Steiner systems S(2,8,225) and S(2,9,289) exist: the printed difference families "
                   "in ℤ₃×ℤ₃×ℤ₅×ℤ₅ and ℤ₁₇×ℤ₁₇ each hit every nonzero group element exactly once "
                   "among their within-block differences, so each develops to its Steiner system — "
                   "resolving two of the 129 undecided Handbook cases (Hetman 2026)"),
        claim_type=ClaimType.EXISTENCE,
        falsifiable_claim=("a repeated, zero, or missing within-block difference — i.e. the 224 (resp. "
                           "288) differences of blocks8 (resp. blocks9) failing to be exactly the "
                           "nonzero elements of the group, once each"),
        domain="combinatorial_design_theory",
    )
    ex = Expressio(theorem_src=_THEOREM_SRC, imports=(), preamble=build_preamble())
    de = Demonstratio(proof_obligation="steiner_s8_225_s9_289", proof_src="by decide")
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

    print("=== ADR 0050 Phase 2 (9th) — Steiner systems S(2,8,225) + S(2,9,289) → amplified law ===")
    print(f"  kernel_verified : {de.kernel_verified}")
    print(f"  qed             : {de.qed}")
    print(f"  proof edge      : {edge.verdict.value} (producer {edge.producer})")
    print(f"  axiom_closure   : ok={ax['ok']} axioms={ax.get('axioms')}")
    if not (de.kernel_verified and de.qed == "Q.E.D." and ax["ok"]):
        print("!! discharge or axiom check failed — NOT emitting a law.")
        return 1
    prop.promulgated = True
    payload = law_payload(prop, published_at="", specimen=False,
                          tier="kernel-decided", origination="amplified",
                          references=_REFERENCES, figures=[s8_225_figure(), s9_289_figure()])
    payload["$schema"] = "../../../.astro/collections/laws.schema.json"
    print(f"\n  law id          : {payload['id']}  |  figures: {len(payload['figures'])}")
    if write:
        _OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
        print(f"  WROTE {_OUT.relative_to(_ROOT)}")
    else:
        print("  (dry run — pass --write to emit the law JSON)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
