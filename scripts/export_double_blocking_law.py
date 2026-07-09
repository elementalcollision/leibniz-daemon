"""ADR 0050 Phase 2 (10th law) — promote the kernel-attested minimal double blocking sets of size
3q−1 in PG(2,13) and PG(2,19) to a promulgated LAW with ADR 0064 figures: each printed 3q−1-point
set meets every line of PG(2,q) at least twice AND is minimal (every point lies on a 2-secant) —
the constructive half of Csajbók–Héger, refuting Hill's 1984 conjecture; for prime q > 13 the first
double blocking sets of size < 3q. Labelled ``amplified`` + cited, tier ``kernel-decided``.

Whole-artifact-verbatim preamble (``docs/crt/double_blocking.lean`` is pure core, namespace-free —
its negative-control theorems ride along and are re-decided at every check); the law theorem
restates the four positive facts. Two figures draw each blocking set in PG(2,q), generated from the
same ``B13``/``B19`` lists the kernel decided over.

Usage:  PYTHONPATH=. python scripts/export_double_blocking_law.py [--write]
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

from figures.gen_double_blocking_figures import db13_figure, db19_figure  # noqa: E402

_ROOT = Path(__file__).resolve().parent.parent
_ARTIFACT = _ROOT / "docs" / "crt" / "double_blocking.lean"
_OUT = _ROOT / "site" / "src" / "content" / "laws" / "double_blocking_3qm1.json"

_THEOREM_SRC = ("theorem double_blocking_3qm1 : "
                "(doubleBlocking 13 B13 lines13 = true) ∧ (minimalDBS 13 B13 lines13 = true) "
                "∧ (doubleBlocking 19 B19 lines19 = true) ∧ (minimalDBS 19 B19 lines19 = true)")

_REFERENCES = [
    {"citation": ("Csajbók, B., & Héger, T. (2019). Double blocking sets of size 3q−1 in PG(2,q). "
                  "European Journal of Combinatorics, 78, 655–678 (arXiv:1805.01267)."),
     "url": "https://arxiv.org/abs/1805.01267"},
    {"citation": ("Ball, S., & Blokhuis, A. (1996). On the size of a double blocking set in PG(2,q). "
                  "Finite Fields and Their Applications, 2(2), 125–137."),
     "url": "https://doi.org/10.1006/ffta.1996.0009"},
    {"citation": ("Hill, R. (1984). Some problems concerning (k,n)-arcs in finite projective planes. "
                  "Rendiconti del Seminario Matematico di Brescia, 7, 367–383."),
     "url": ""},
]


def build_preamble() -> str:
    """The ENTIRE audited artifact VERBATIM — pure core (no import line), namespace-free."""
    return _ARTIFACT.read_text().rstrip("\n")


def build_propositio() -> Propositio:
    en = Enuntiatio(
        statement=("Minimal double blocking sets of size 3q−1 exist in PG(2,13) and PG(2,19): each "
                   "printed set meets every line at least twice and every point of it lies on a "
                   "2-secant — the constructive half of Csajbók–Héger, refuting Hill's 1984 "
                   "conjecture; for prime q > 13 the first double blocking sets of size < 3q"),
        claim_type=ClaimType.EXISTENCE,
        falsifiable_claim=("a line of PG(2,13) meeting B13 (resp. PG(2,19) meeting B19) in fewer than "
                           "2 points, or a point of either set lying on no 2-secant"),
        domain="finite_geometry",
    )
    ex = Expressio(theorem_src=_THEOREM_SRC, imports=(), preamble=build_preamble())
    de = Demonstratio(proof_obligation="double_blocking_3qm1", proof_src="by decide")
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

    print("=== ADR 0050 Phase 2 (10th) — 3q−1 double blocking sets → amplified law ===")
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
                          references=_REFERENCES, figures=[db13_figure(), db19_figure()])
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
