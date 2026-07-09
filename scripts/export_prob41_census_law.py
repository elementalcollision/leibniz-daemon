"""ADR 0050 Phase 2 (7th law) — promote the kernel-certified Problem-41 NORMALITY CENSUS to a
promulgated LAW (tier ``kernel-decided``): eleven corner triples 1 ≤ a ≤ b ≤ c ≤ 9 — including
(2,3,7) and (3,4,5), both smaller than the textbook Huneke–Swanson (4,5,7) — define NON-normal
monomial ideals I = closure(x^a, y^b, z^c): for each, a kernel-decided witness x^u lies in
closure(I²) ∖ I² (Problem 41 of Cahen–Fontana–Frisch–Glaz). Labelled ``amplified`` + cited.

Honesty: the kernel decides the L-cleared weighted-degree facts (``wt``/``inI2``) as defined in the
artifact; that these encode ``x^u ∈ closure(I²) ∖ I²`` is the documented collapse in the audited
artifact's docstrings (which ride along verbatim). The ADR 0062 preamble carries the ENTIRE artifact
VERBATIM (closed namespace blocks, its 11 theorems included) minus only the ``import`` line; the law
theorem restates the 11 witness facts by QUALIFIED names. Trust boundary untouched; plain ``decide``.

Usage:  PYTHONPATH=. python scripts/export_prob41_census_law.py [--write]
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
_ARTIFACT = _ROOT / "docs" / "crt" / "prob41_census_certificate.lean"
_OUT = _ROOT / "site" / "src" / "content" / "laws" / "prob41_census_non_normal.json"

# (triple-tag, 2L threshold, witness u) — exactly the artifact's 11 certified non-normality witnesses.
_WITNESSES = [
    ("2_3_7", 84, (1, 2, 6)), ("3_4_5", 120, (2, 3, 3)), ("2_5_7", 140, (1, 4, 5)),
    ("3_5_8", 240, (1, 4, 7)), ("4_5_7", 280, (2, 4, 5)), ("3_7_8", 336, (2, 5, 5)),
    ("5_6_7", 420, (3, 5, 4)), ("5_6_8", 240, (4, 2, 7)), ("5_7_9", 630, (2, 5, 8)),
    ("5_8_9", 720, (3, 5, 7)), ("7_8_9", 1008, (4, 7, 5)),
]

_THEOREM_SRC = ("theorem prob41_census_non_normal : "
                + " ∧ ".join(f"({thr} ≤ Prob41_{t}.wt {u[0]} {u[1]} {u[2]} ∧ Prob41_{t}.inI2 = false)"
                             for t, thr, u in _WITNESSES))

_REFERENCES = [
    {"citation": ("Cahen, P.-J., Fontana, M., Frisch, S., & Glaz, S. (2014). Open problems in "
                  "commutative ring theory. In M. Fontana, S. Frisch, & S. Glaz (Eds.), Commutative "
                  "algebra (pp. 353–375). Springer."), "url": ""},
    {"citation": ("Huneke, C., & Swanson, I. (2006). Integral closure of ideals, rings, and modules "
                  "(London Mathematical Society Lecture Note Series No. 336). Cambridge University "
                  "Press."), "url": ""},
    {"citation": ("Reid, L., Roberts, L. G., & Vitulli, M. A. (2003). Some results on normal "
                  "homogeneous ideals. Communications in Algebra, 31(9), 4485–4506."), "url": ""},
    {"citation": ("Ataka, M., & Matsuoka, N. (2026). Normality of monomial ideals in three variables "
                  "(arXiv:2602.01782). arXiv."), "url": "https://arxiv.org/abs/2602.01782"},
]


def build_preamble() -> str:
    """The ENTIRE audited artifact, VERBATIM, minus only its ``import`` line(s) — see the prob16 twin."""
    return "\n".join(ln for ln in _ARTIFACT.read_text().splitlines() if not ln.startswith("import "))


def build_propositio() -> Propositio:
    en = Enuntiatio(
        statement=("Eleven corner triples 1 ≤ a ≤ b ≤ c ≤ 9 — including (2,3,7) and (3,4,5), both "
                   "smaller than the textbook (4,5,7) — define non-normal monomial ideals "
                   "I = closure(x^a, y^b, z^c): each carries a kernel-decided witness "
                   "x^u ∈ closure(I²) ∖ I² (normality census for Problem 41 of "
                   "Cahen–Fontana–Frisch–Glaz)"),
        claim_type=ClaimType.EXISTENCE,
        falsifiable_claim=("one of the 11 certified witnesses failing — wt(u) below the 2L threshold, "
                           "or the witness monomial landing in I² after all"),
        domain="commutative_algebra",
    )
    ex = Expressio(theorem_src=_THEOREM_SRC, imports=("Mathlib.Tactic",), preamble=build_preamble())
    de = Demonstratio(proof_obligation="prob41_census_non_normal", proof_src="by decide")
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

    print("=== ADR 0050 Phase 2 (7th) — Problem-41 normality census → amplified law ===")
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
    print(f"  theorem_src     : {payload['theorem_src'][:88]}…")
    print(f"  preamble        : {len(payload['preamble'])} chars ({payload['preamble'].count(chr(10)) + 1} lines, whole artifact verbatim minus import)")
    if write:
        _OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
        print(f"\n  WROTE {_OUT.relative_to(_ROOT)}")
    else:
        print("\n  (dry run — pass --write to emit the law JSON)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
