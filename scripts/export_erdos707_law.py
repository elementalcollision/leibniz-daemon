"""ADR 0050 Phase 2 (3rd law) — promote the kernel-attested finite core of the DISPROOF of Erdős
Problem 707 (the $1000 Sidon-extension conjecture; Alexeev–Mixon 2025) from an audit-tier cycle to a
promulgated LAW — the FIRST law at tier ``cross-kernel`` (ADR 0048/0050): the same finite facts were
independently re-decided by the Rocq 9.0 kernel (``docs/crt/erdos_707_crosscheck.v``, ``vm_compute``).

The law: the Alexeev–Mixon witness {1, 2, 4, 8, 13} is a Sidon set (all pairwise differences over ℤ
distinct) that extends to NO perfect difference set of order 5 or 6 — ``isPDS`` fails for the set
itself mod 21 and for every one-element extension mod 31. This is the kernel-attested finite core of
the disproof; the paper's unconditional exhaustion covers the remaining orders. Labelled ``amplified``
and cited (never presented as the daemon's own discovery).

Trust boundary UNTOUCHED: ``kernel_verified`` only via ``LeanVerifier.discharge``; ``axiom_closure``
re-checks the WHOLE source (preamble ⊕ theorem ⊕ proof); plain ``decide``, no ``native_decide``, no
``sorryAx``; ``tier``/``origination``/``references`` are report-only. The preamble defs are VERBATIM
from the audited ``docs/crt/erdos_707_certificate.lean`` — minus its ``namespace Erdos707`` wrapper,
which cannot ride along: ``_join_proof`` appends ``theorem … := proof`` AFTER the preamble, so a
namespace opened there could never be closed. The defs are name-collision-free at top level.

Usage:  PYTHONPATH=. python scripts/export_erdos707_law.py [--write]
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
_ARTIFACT = _ROOT / "docs" / "crt" / "erdos_707_certificate.lean"
_OUT = _ROOT / "site" / "src" / "content" / "laws" / "erdos707_am_witness.json"

# The Alexeev–Mixon witness, as ONE conjunction: Sidon ∧ not a PDS at order 5 ∧ no order-6 extension.
_THEOREM_SRC = ("theorem erdos707_am_witness : (diffsZ [1, 2, 4, 8, 13]).Nodup ∧ "
                "isPDS [1, 2, 4, 8, 13] 21 = false ∧ "
                "(∀ x0 < 31, isPDS ([1, 2, 4, 8, 13] ++ [x0]) 31 = false)")

_REFERENCES = [
    {"citation": ("Alexeev, B., & Mixon, D. G. (2025). Forbidden Sidon subsets of perfect difference "
                  "sets, featuring a human-assisted proof (arXiv:2510.19804). arXiv."),
     "url": "https://arxiv.org/abs/2510.19804"},
    {"citation": ("Hall, M. (1947). Cyclic projective planes. Duke Mathematical Journal, 14(4), "
                  "1079–1090."),
     "url": ""},
]


def build_preamble() -> str:
    """``set_option`` + the three defs (``diffsZ``, ``diffsMod``, ``isPDS``) — the def block is a
    VERBATIM contiguous slice of the audited artifact (docstrings included); only the enclosing
    ``namespace Erdos707`` wrapper is dropped (see module docstring)."""
    lines = _ARTIFACT.read_text().splitlines()
    set_opt = next(ln for ln in lines if ln.startswith("set_option"))
    start = next(i for i, ln in enumerate(lines) if ln.startswith("/-- pairwise differences (over"))
    end = next(i for i, ln in enumerate(lines) if ln.startswith("def isPDS"))
    return set_opt + "\n\n" + "\n".join(lines[start:end + 1])


def build_propositio() -> Propositio:
    en = Enuntiatio(
        statement=("The Alexeev–Mixon set {1, 2, 4, 8, 13} is a Sidon set extending to no perfect "
                   "difference set of order 5 or 6 — the kernel-attested finite core of the disproof "
                   "of Erdős Problem 707 (the $1000 Sidon-extension conjecture)"),
        claim_type=ClaimType.INVARIANT,
        falsifiable_claim=("a repeated pairwise difference in {1,2,4,8,13} (not Sidon), or the set "
                           "itself a perfect difference set mod 21, or an x0 < 31 making "
                           "{1,2,4,8,13,x0} a perfect difference set mod 31"),
        domain="additive_combinatorics",
    )
    ex = Expressio(theorem_src=_THEOREM_SRC, imports=("Mathlib.Tactic",), preamble=build_preamble())
    de = Demonstratio(proof_obligation="erdos707_am_witness", proof_src="by decide")
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

    print("=== ADR 0050 Phase 2 (3rd) — Erdős 707 finite core → amplified law (cross-kernel tier) ===")
    print(f"  kernel_verified : {de.kernel_verified}")
    print(f"  qed             : {de.qed}")
    print(f"  proof edge      : {edge.verdict.value} (producer {edge.producer})")
    print(f"  axiom_closure   : ok={ax['ok']} axioms={ax.get('axioms')}")
    if not (de.kernel_verified and de.qed == "Q.E.D." and ax["ok"]):
        print("!! discharge or axiom check failed — NOT emitting a law.")
        return 1
    prop.promulgated = True
    # tier=cross-kernel (ADR 0048): the same witness facts (AM5_sidon / AM5_no_order5 / AM5_no_order6)
    # are independently re-decided by the Rocq 9.0 kernel in docs/crt/erdos_707_crosscheck.v.
    payload = law_payload(prop, published_at="", specimen=False,
                          tier="cross-kernel", origination="amplified", references=_REFERENCES)
    payload["$schema"] = "../../../.astro/collections/laws.schema.json"
    print(f"\n  law id          : {payload['id']}")
    print(f"  tier/origination: {payload['tier']} / {payload['origination']}")
    print(f"  references      : {len(payload['references'])} cited")
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
