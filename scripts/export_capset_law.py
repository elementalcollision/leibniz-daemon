"""ADR 0050 Phase 2 (8th law) — promote the kernel-attested cap-set result to a promulgated LAW with
the first ADR 0064 FIGURES: the 20 nonzero fourth powers of GF(81) form a maximal SET cap in AG(4,3)
(no three distinct points sum to 0 mod 3), and the 9 nonzero seventh powers of GF(64) form a maximal
EvenQuads cap in AG(6,2) (no four distinct points sum to 0 mod 2) — Kable, Mills & Wright (2026).
Labelled ``amplified`` + cited, tier ``kernel-decided``.

The ADR 0062 preamble carries the ENTIRE audited artifact VERBATIM (it has no import line and no
namespaces); the law theorem restates the two decided statements as one conjunction. Two ADR 0064
figures ride along, generated deterministically from the same ``set81``/``eq64`` lists the kernel
decided over (scripts/figures/gen_capset_figures.py).

Usage:  PYTHONPATH=. python scripts/export_capset_law.py [--write]
"""
from __future__ import annotations

import json
import re
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

from figures.gen_capset_figures import eq64_figure, set81_figure  # noqa: E402

_ROOT = Path(__file__).resolve().parent.parent
_ARTIFACT = _ROOT / "docs" / "crt" / "capset_subgroups.lean"
_OUT = _ROOT / "site" / "src" / "content" / "laws" / "capset_subgroup_caps.json"

_REFERENCES = [
    {"citation": ("Kable, A., Mills, M., & Wright, D. J. (2026). Subgroups of finite fields as cap "
                  "sets (arXiv:2604.26989). arXiv."),
     "url": "https://arxiv.org/abs/2604.26989"},
]


def _artifact_statement(name: str) -> str:
    """The named theorem's STATEMENT, extracted verbatim from the artifact and collapsed to one line."""
    m = re.search(rf"theorem {name} :\n(.*?) := by decide", _ARTIFACT.read_text(), re.S)
    return " ".join(m.group(1).split())


def build_theorem_src() -> str:
    return ("theorem capset_subgroup_caps : "
            f"({_artifact_statement('capset_set81')}) ∧ ({_artifact_statement('capset_eq64')})")


def build_preamble() -> str:
    """The ENTIRE audited artifact VERBATIM — it has no ``import`` line (pure core) and no namespaces,
    so nothing is stripped at all."""
    return _ARTIFACT.read_text().rstrip("\n")


def build_propositio() -> Propositio:
    en = Enuntiatio(
        statement=("The 20 nonzero fourth powers of GF(81) form a maximal SET cap in AG(4,3) — no "
                   "three distinct points sum to 0 (mod 3) — and the 9 nonzero seventh powers of "
                   "GF(64) form a maximal EvenQuads cap in AG(6,2) — no four distinct points sum to "
                   "0 (mod 2) (Kable–Mills–Wright: subgroups of finite fields as cap sets)"),
        claim_type=ClaimType.INVARIANT,
        falsifiable_claim=("three distinct indices i<j<k with set81[i]+set81[j]+set81[k] ≡ 0 (mod 3), "
                           "or four distinct indices with the corresponding eq64 sum ≡ 0 (mod 2)"),
        domain="finite_geometry",
    )
    ex = Expressio(theorem_src=build_theorem_src(), imports=(), preamble=build_preamble())
    de = Demonstratio(proof_obligation="capset_subgroup_caps", proof_src="by decide")
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

    print("=== ADR 0050 Phase 2 (8th) — subgroup cap sets → amplified law (with ADR 0064 figures) ===")
    print(f"  kernel_verified : {de.kernel_verified}")
    print(f"  qed             : {de.qed}")
    print(f"  proof edge      : {edge.verdict.value} (producer {edge.producer})")
    print(f"  axiom_closure   : ok={ax['ok']} axioms={ax.get('axioms')}")
    if not (de.kernel_verified and de.qed == "Q.E.D." and ax["ok"]):
        print("!! discharge or axiom check failed — NOT emitting a law.")
        return 1
    prop.promulgated = True
    figures = [set81_figure(), eq64_figure()]        # deterministic, from the artifact's own lists
    payload = law_payload(prop, published_at="", specimen=False,
                          tier="kernel-decided", origination="amplified",
                          references=_REFERENCES, figures=figures)
    payload["$schema"] = "../../../.astro/collections/laws.schema.json"
    print(f"\n  law id          : {payload['id']}")
    print(f"  figures         : {len(payload['figures'])} "
          f"({', '.join(f['generated_by'].split('/')[-1].split(' ')[0] for f in payload['figures'])})")
    print(f"  theorem_src     : {payload['theorem_src'][:80]}…")
    if write:
        _OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
        print(f"\n  WROTE {_OUT.relative_to(_ROOT)}")
    else:
        print("\n  (dry run — pass --write to emit the law JSON)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
