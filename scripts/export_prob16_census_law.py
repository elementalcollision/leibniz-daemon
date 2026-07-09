"""ADR 0050 Phase 2 (6th law) — promote the kernel-certified Problem-16 self-ordered-sequence census
REFUTATIONS to a promulgated LAW (tier ``kernel-decided``): five natural sequences — n³, n⁴, n!,
Fibonacci, and the primes — are each NOT self-ordered; for each, one kernel-decided witness (m,n) has
Dₙ ∤ P(m,n), where Dₙ = ∏_{k<n}(aₙ−aₖ) and P(m,n) = ∏_{k<n}(aₘ−aₖ) (Problem 16 of
Cahen–Fontana–Frisch–Glaz). Labelled ``amplified`` + cited.

The artifact keeps each sequence in its own namespace (same def names ``a``/``D``/``P``), so the
ADR 0062 preamble carries the ENTIRE audited artifact VERBATIM (closed namespace blocks, its theorems
included) minus only the ``import`` line — the strongest anti-drift property — and the law theorem
restates the five witness facts by QUALIFIED names. Trust boundary untouched; plain ``decide``.

Usage:  PYTHONPATH=. python scripts/export_prob16_census_law.py [--write]
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
_ARTIFACT = _ROOT / "docs" / "crt" / "prob16_census_certificate.lean"
_OUT = _ROOT / "site" / "src" / "content" / "laws" / "prob16_census_refutations.json"

# (namespace, witness m, witness n) — exactly the artifact's five certified refutation witnesses.
_WITNESSES = [
    ("SO_cube", 3, 2), ("SO_quartic", 4, 3), ("SO_factorial", 3, 2),
    ("SO_fibonacci", 4, 3), ("SO_primes", 3, 2),
]

_THEOREM_SRC = ("theorem prob16_census_refutations : "
                + " ∧ ".join(f"{ns}.P {m} {n} % {ns}.D {n} ≠ 0" for ns, m, n in _WITNESSES))

_REFERENCES = [
    {"citation": ("Cahen, P.-J., Fontana, M., Frisch, S., & Glaz, S. (2014). Open problems in "
                  "commutative ring theory. In M. Fontana, S. Frisch, & S. Glaz (Eds.), Commutative "
                  "algebra (pp. 353–375). Springer."), "url": ""},
    {"citation": ("Adam, D., Cahen, P.-J., & Fares, Y. (2010). Subsets of ℤ with simultaneous "
                  "ordering. Integers, 10, 437–451."), "url": ""},
]


def build_preamble() -> str:
    """The ENTIRE audited artifact, VERBATIM, minus only its ``import`` line(s) (imports ride on
    ``Expressio.imports``; an ``import`` inside a REPL command errors). Namespace blocks are complete
    (opened AND closed), so the appended law theorem elaborates after them via qualified names."""
    return "\n".join(ln for ln in _ARTIFACT.read_text().splitlines() if not ln.startswith("import "))


def build_propositio() -> Propositio:
    en = Enuntiatio(
        statement=("Five natural sequences — n³, n⁴, n!, Fibonacci, and the primes — are each NOT "
                   "self-ordered: for each, a kernel-decided witness (m,n) has Dₙ ∤ P(m,n) "
                   "(census refutations for Problem 16 of Cahen–Fontana–Frisch–Glaz)"),
        claim_type=ClaimType.EXISTENCE,
        falsifiable_claim=("one of the five certified witnesses failing — i.e. Dₙ dividing P(m,n) at "
                           "the stated (m,n) for that sequence's value prefix"),
        domain="number_theory",
    )
    ex = Expressio(theorem_src=_THEOREM_SRC, imports=("Mathlib.Tactic",), preamble=build_preamble())
    de = Demonstratio(proof_obligation="prob16_census_refutations", proof_src="by decide")
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

    print("=== ADR 0050 Phase 2 (6th) — Problem-16 census refutations → amplified law ===")
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
