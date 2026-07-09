"""ADR 0050 Phase 2 (11th law) — promote the kernel-attested arithmetic core of the Markoff-cage
connectedness result to a promulgated LAW with ADR 0064 figures: at the special point (1,1,1) of the
Markoff mod-p graph, for every certified prime p ≡ ±2 (mod 5) — including the Mersenne primes 127,
524287 and 2³¹−1 — the rotation's companion matrix A = [[0,1],[−1,3]] satisfies A^{p+1} = I and
A^{(p+1)/2} ≠ I, so 2^{ν₂(p+1)} divides the rotation order (Bellah–Dunn–Naidu–Wells Thm 2.10; for
Mersenne p the order is exactly p+1); and ord(A) = π(p)/2 for p ∈ {7, 127} (their Prop 3.3, tying the
order to the Fibonacci Pisano period). Labelled ``amplified`` + cited, tier ``kernel-decided``.

Whole-artifact-verbatim preamble (``docs/crt/markoff_cage.lean`` is pure core, namespace-free — its
hyperbolic negative control at p = 11 rides along and is re-decided at every check); the law theorem
restates the three positive facts. Two figures: the order-8 rotation orbit mod 7 (the actual matrix
powers) and the Mersenne 2-adic staircase.

Usage:  PYTHONPATH=. python scripts/export_markoff_law.py [--write]
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

from figures.gen_markoff_figures import mersenne_figure, orbit7_figure  # noqa: E402

_ROOT = Path(__file__).resolve().parent.parent
_ARTIFACT = _ROOT / "docs" / "crt" / "markoff_cage.lean"
_OUT = _ROOT / "site" / "src" / "content" / "laws" / "markoff_cage_core.json"

_THEOREM_SRC = ("theorem markoff_cage_core : (allPos [7, 13, 17, 23, 43, 47] = true) "
                "∧ (allPos [127, 524287, 2147483647] = true) "
                "∧ ((pisano 7 == 2 * matOrder 7 && pisano 127 == 2 * matOrder 127) = true)")

_REFERENCES = [
    {"citation": ("Bellah, E., Dunn, C., Naidu, V., & Wells, A. (2025). Connectedness of Special "
                  "Points in the Markoff mod p Graphs (arXiv:2511.23401)."),
     "url": "https://arxiv.org/abs/2511.23401"},
    {"citation": ("Bourgain, J., Gamburd, A., & Sarnak, P. (2016). Markoff triples and strong "
                  "approximation. Comptes Rendus Mathématique, 354(2), 131–135."),
     "url": "https://doi.org/10.1016/j.crma.2015.12.006"},
]


def build_preamble() -> str:
    """The ENTIRE audited artifact VERBATIM — pure core (no import line), namespace-free; the
    hyperbolic control theorem rides along and is re-decided at every honesty check."""
    return _ARTIFACT.read_text().rstrip("\n")


def build_propositio() -> Propositio:
    en = Enuntiatio(
        statement=("At the Markoff special point (1,1,1) mod p, for the certified primes "
                   "p ≡ ±2 (mod 5) — 7, 13, 17, 23, 43, 47 and the Mersenne primes 127, 524287, "
                   "2³¹−1 — the rotation's companion matrix satisfies A^{p+1} = I and "
                   "A^{(p+1)/2} ≠ I, so 2^{ν₂(p+1)} divides the rotation order (for Mersenne p, "
                   "ord = p+1 exactly); and ord(A) = π(p)/2 for p ∈ {7, 127} "
                   "(Bellah–Dunn–Naidu–Wells, Thm 2.10 / Prop 3.3)"),
        claim_type=ClaimType.INVARIANT,
        falsifiable_claim=("a certified prime p with A^{p+1} ≠ I or A^{(p+1)/2} = I over F_p, or "
                           "pisano(p) ≠ 2·ord(A) at p ∈ {7, 127}"),
        domain="arithmetic_dynamics",
    )
    ex = Expressio(theorem_src=_THEOREM_SRC, imports=(), preamble=build_preamble())
    de = Demonstratio(proof_obligation="markoff_cage_core", proof_src="by decide")
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

    print("=== ADR 0050 Phase 2 (11th) — Markoff-cage arithmetic core → amplified law ===")
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
                          references=_REFERENCES, figures=[orbit7_figure(), mersenne_figure()])
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
