"""ADR 0050 Phase 2 (4th law) — promote the kernel-attested Guo–Krattenthaler binomial divisibilities
to a promulgated LAW at tier ``cross-kernel``: (6n−1) ∣ C(12n,3n) and (6n−1) ∣ C(12n,4n) for every
certified n = 1..8, and (66n−1) ∣ C(330n,88n) at n = 1 — kernel-attested instances of the all-n
theorems of Guo & Krattenthaler (2014). The SAME 17 facts are independently re-decided by the Rocq 9.0
kernel (``docs/crt/gk_coq_crosscheck.v``), which is what backs the tier (ADR 0048; report-only).

The theorem is ONE bounded-∀ conjunction, mathematically identical to the audited artifact's 17
per-instance theorems (``docs/crt/guo_krattenthaler_certificate.lean``) — the kernel decides it by the
same enumeration. Scope note: the artifact's §(B) Sun-conjecture non-divisibility witnesses are NOT
promoted here — they are a different claim and are not covered by the Rocq crosscheck.

Trust boundary UNTOUCHED: ``kernel_verified`` only via ``LeanVerifier.discharge``; ``axiom_closure``
re-checks the WHOLE source; plain ``decide``; ``tier``/``origination``/``references`` report-only.
No custom defs are needed (the statement uses Mathlib's ``Nat.choose``), so the ADR 0062 preamble is
just the artifact's ``set_option`` line (verbatim).

Usage:  PYTHONPATH=. python scripts/export_guo_krattenthaler_law.py [--write]
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
_ARTIFACT = _ROOT / "docs" / "crt" / "guo_krattenthaler_certificate.lean"
_OUT = _ROOT / "site" / "src" / "content" / "laws" / "gk_divisibilities.json"

# Both certified families over n = 1..8 (as ∀ n < 8 at n+1) + the (66n−1) family at n = 1.
_THEOREM_SRC = ("theorem gk_divisibilities : (∀ n < 8, (6*(n+1) - 1) ∣ Nat.choose (12*(n+1)) (3*(n+1)) "
                "∧ (6*(n+1) - 1) ∣ Nat.choose (12*(n+1)) (4*(n+1))) ∧ (65 : ℕ) ∣ Nat.choose 330 88")

_REFERENCES = [
    {"citation": ("Guo, V. J. W., & Krattenthaler, C. (2014). Some divisibility properties of binomial "
                  "and q-binomial coefficients. Journal of Number Theory, 135, 167–184."),
     "url": "https://arxiv.org/abs/1301.7651"},
]


def build_preamble() -> str:
    """The artifact's ``set_option`` line, VERBATIM (no custom defs are needed — the statement uses
    Mathlib's ``Nat.choose``). The ``namespace`` wrapper is dropped as usual (it could never be closed
    after ``_join_proof`` appends the theorem)."""
    lines = _ARTIFACT.read_text().splitlines()
    return next(ln for ln in lines if ln.startswith("set_option"))


def build_propositio() -> Propositio:
    en = Enuntiatio(
        statement=("The Guo–Krattenthaler divisibilities (6n−1) ∣ C(12n,3n) and (6n−1) ∣ C(12n,4n) "
                   "hold for every n = 1..8, and (66n−1) ∣ C(330n,88n) at n = 1 — kernel-attested "
                   "instances of the all-n theorems of Guo & Krattenthaler (2014)"),
        claim_type=ClaimType.INVARIANT,
        falsifiable_claim=("an n between 1 and 8 with (6n−1) ∤ C(12n,3n) or (6n−1) ∤ C(12n,4n), "
                           "or 65 ∤ C(330,88)"),
        domain="number_theory",
    )
    ex = Expressio(theorem_src=_THEOREM_SRC, imports=("Mathlib.Tactic",), preamble=build_preamble())
    de = Demonstratio(proof_obligation="gk_divisibilities", proof_src="by decide")
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

    print("=== ADR 0050 Phase 2 (4th) — Guo–Krattenthaler divisibilities → amplified law (cross-kernel) ===")
    print(f"  kernel_verified : {de.kernel_verified}")
    print(f"  qed             : {de.qed}")
    print(f"  proof edge      : {edge.verdict.value} (producer {edge.producer})")
    print(f"  axiom_closure   : ok={ax['ok']} axioms={ax.get('axioms')}")
    if not (de.kernel_verified and de.qed == "Q.E.D." and ax["ok"]):
        print("!! discharge or axiom check failed — NOT emitting a law.")
        return 1
    prop.promulgated = True
    # tier=cross-kernel (ADR 0048): the same 17 facts (div_12_3_n1..n8, div_12_4_n1..n8,
    # div_330_88_n1) are independently re-decided by Rocq 9.0 in docs/crt/gk_coq_crosscheck.v.
    payload = law_payload(prop, published_at="", specimen=False,
                          tier="cross-kernel", origination="amplified", references=_REFERENCES)
    payload["$schema"] = "../../../.astro/collections/laws.schema.json"
    print(f"\n  law id          : {payload['id']}")
    print(f"  tier/origination: {payload['tier']} / {payload['origination']}")
    print(f"  theorem_src     : {payload['theorem_src'][:88]}…")
    print(f"  preamble        : {payload['preamble']!r}")
    if write:
        _OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
        print(f"\n  WROTE {_OUT.relative_to(_ROOT)}")
    else:
        print("\n  (dry run — pass --write to emit the law JSON)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
