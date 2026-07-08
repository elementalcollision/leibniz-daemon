"""ADR 0050 Phase 2 (2nd law) — promote the kernel-attested complex Hadamard matrix of ORDER 94
(Szöllősi 2026) from an audit-tier cycle to a promulgated LAW, labelled ``amplified`` +
``kernel-decided`` with the source cited. Uses the ADR 0062 Expressio preamble so the ``theorem_src``
is a clean one-liner and the legible definitions ride in the preamble.

The law: Szöllősi's Example-1 circulant quadruple (A,B,C,D) of order 47 over {−1,1} satisfies the
Theorem-4 construction hypothesis — ``A A^T + B B^T + C C^T + D D^T = 188·I`` (reduced to vanishing
summed periodic autocorrelations at every nonzero shift, 188 at shift 0) with A,B symmetric — the
kernel-attested structural core establishing that a complex Hadamard matrix of order 94 exists
(previously the smallest open order). The kernel decides ``eq1 a1 b1 c1 d1 && symrow a1 && symrow b1``.

Trust boundary UNTOUCHED: ``kernel_verified`` only via ``LeanVerifier.discharge``; ``axiom_closure``
re-checks the WHOLE source (preamble ⊕ theorem ⊕ proof); plain ``decide``, no ``native_decide``, no
``sorryAx``; ``tier``/``origination``/``references`` are report-only. The preamble is read verbatim from
the audited artifact ``docs/crt/hadamard94.lean`` (byte-identical definitions).

Usage:  PYTHONPATH=. python scripts/export_hadamard94_law.py [--write]
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
_ARTIFACT = _ROOT / "docs" / "crt" / "hadamard94.lean"
_OUT = _ROOT / "site" / "src" / "content" / "laws" / "hadamard94_witness1.json"

# The Example-1 witness theorem: the FULL Theorem-4 hypothesis (autocorrelation eq (1) + symmetry of A,B).
_THEOREM_SRC = "theorem had94_witness1 : (eq1 a1 b1 c1 d1 && symrow a1 && symrow b1) = true"

_REFERENCES = [
    {"citation": ("Szöllősi, F. (2026). A complex Hadamard matrix of order 94. "
                  "arXiv:2603.09572."),
     "url": "https://arxiv.org/abs/2603.09572"},
]


def build_preamble() -> str:
    """The legible definitions — read VERBATIM from the audited artifact: `set_option`s + `rot`, `dotf`,
    `autocorr`, `eq1`, `symrow`, and the Example-1 blocks a1/b1/c1/d1 (through `def d1`, excluding the
    Example-2 / negative-control data the witness theorem does not reference)."""
    lines = _ARTIFACT.read_text().splitlines()
    start = next(i for i, ln in enumerate(lines) if ln.startswith("set_option"))
    end = next(i for i, ln in enumerate(lines) if ln.startswith("def d1"))
    return "\n".join(lines[start:end + 1])


def build_propositio() -> Propositio:
    en = Enuntiatio(
        statement=("A complex Hadamard matrix of order 94 exists (Szöllősi 2026) — kernel-attested "
                   "structural core: the Example-1 circulant quadruple (A,B,C,D, order 47, {−1,1}) "
                   "satisfies A A^T+B B^T+C C^T+D D^T = 188·I with A,B symmetric (Theorem 4)"),
        claim_type=ClaimType.EXISTENCE,
        falsifiable_claim=("a nonzero shift s∈[1,47) at which the summed periodic autocorrelations of "
                           "A,B,C,D are nonzero (or ≠188 at s=0), or an asymmetry in A or B — breaking "
                           "the Theorem-4 construction hypothesis"),
        domain="combinatorial_design_theory",
    )
    ex = Expressio(theorem_src=_THEOREM_SRC, imports=(), preamble=build_preamble())   # ADR 0062
    de = Demonstratio(proof_obligation="hadamard94_witness1", proof_src="by decide")
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
        # the artifact claims "no axioms"; allow the standard set and REPORT the actual footprint.
        ax = axiom_closure(be, ex.theorem_src, de.proof_src, ex.imports,
                           allowed=frozenset({"propext"}), preamble=ex.preamble)
    finally:
        be.close()

    print("=== ADR 0050 Phase 2 (2nd) — complex Hadamard order 94 → amplified law ===")
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
    print(f"  references      : {len(payload['references'])} cited")
    print(f"  theorem_src     : {payload['theorem_src']}")
    print(f"  preamble        : {len(payload['preamble'])} chars ({payload['preamble'].count(chr(10)) + 1} lines)")
    if write:
        _OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
        print(f"\n  WROTE {_OUT.relative_to(_ROOT)}")
    else:
        print("\n  (dry run — pass --write to emit the law JSON)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
