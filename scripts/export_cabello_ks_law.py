"""ADR 0050 Phase 2 — promote the kernel-attested Kochen–Specker uncolorability (Cabello 2025) from an
audit-tier cycle to a promulgated LAW: a real kernel discharge of a self-contained Propositio, labelled
``amplified`` + ``kernel-decided`` with the source cited. Writes ``site/src/content/laws/…``.

Trust boundary UNTOUCHED. ``kernel_verified`` is set ONLY by ``LeanVerifier.discharge`` (the sole
writer); no ``trust.py``/``verifiers.py``/``tests/test_invariants.py`` edit. ``axiom_closure``
independently confirms the footprint is ``≤ [propext]`` over the WHOLE assembled source (plain
``decide``; no ``native_decide``/``Lean.ofReduceBool``, no ``sorryAx``). ``tier``/``origination``/
``references`` are report-only (ADR 0050) and never gate promotion — a law is admitted iff it carries a
real kernel ``Q.E.D.`` (invariant #7).

ADR 0062: the legible top-level definitions (Eisenstein arithmetic, the recursive backtracking
``solve``, the 33 rays / 14 bases — identical to ``docs/crt/cabello_ks.lean``) ride in the Expressio
PREAMBLE, so the ``theorem_src`` is a clean one-liner. The preamble is operator-authored (never from a
proposer) and re-checked in full by ``axiom_closure`` and the honesty gate.

Usage:  PYTHONPATH=. python scripts/export_cabello_ks_law.py [--write]
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

from figures.gen_ks_graph import ks_graph_figure  # noqa: E402

_ROOT = Path(__file__).resolve().parent.parent
_OUT = _ROOT / "site" / "src" / "content" / "laws" / "cabello_ks_uncolorable.json"

_RAYS = "[[(0, 0), (0, 0), (1, 0)], [(0, 0), (1, 0), (0, 0)], [(1, 0), (0, 0), (0, 0)], [(1, 0), (0, 1), (-1, -1)], [(1, 0), (1, 0), (1, 0)], [(-1, -1), (0, 1), (1, 0)], [(1, 0), (0, 1), (1, 1)], [(1, 0), (1, 0), (-1, 0)], [(-1, -1), (0, 1), (-1, 0)], [(1, 0), (0, -1), (-1, -1)], [(1, 0), (-1, 0), (1, 0)], [(-1, -1), (0, -1), (1, 0)], [(-1, 0), (0, 1), (-1, -1)], [(-1, 0), (1, 0), (1, 0)], [(1, 1), (0, 1), (1, 0)], [(1, 0), (1, 0), (0, 0)], [(1, 0), (-1, 0), (0, 0)], [(1, 0), (0, 1), (0, 0)], [(1, 0), (0, -1), (0, 0)], [(0, 1), (1, 0), (0, 0)], [(0, 1), (-1, 0), (0, 0)], [(1, 0), (0, 0), (1, 0)], [(1, 0), (0, 0), (-1, 0)], [(1, 0), (0, 0), (0, 1)], [(1, 0), (0, 0), (0, -1)], [(0, 1), (0, 0), (1, 0)], [(0, 1), (0, 0), (-1, 0)], [(0, 0), (1, 0), (1, 0)], [(0, 0), (1, 0), (-1, 0)], [(0, 0), (1, 0), (0, 1)], [(0, 0), (1, 0), (0, -1)], [(0, 0), (0, 1), (1, 0)], [(0, 0), (0, 1), (-1, 0)]]"
_BASES = "[(0, 1, 2), (3, 4, 5), (6, 7, 8), (9, 10, 11), (12, 13, 14), (0, 15, 16), (0, 17, 18), (0, 19, 20), (1, 21, 22), (1, 23, 24), (1, 25, 26), (2, 27, 28), (2, 29, 30), (2, 31, 32)]"

# ADR 0062: the LEGIBLE top-level definitions go in the Expressio PREAMBLE (prepended to the kernel
# source before `theorem_src := proof`). These are the exact definitions of docs/crt/cabello_ks.lean —
# structurally-recursive `solve` (reduces under `decide`), Eisenstein-integer arithmetic, the 33 rays
# and 14 bases. Because they ride in the preamble (not through `_join_proof`, which cuts at the first
# `:=`), the `theorem_src` stays a clean one-liner.
_PREAMBLE = f"""set_option maxHeartbeats 0
set_option maxRecDepth 4000000

abbrev Eis := Int × Int
def emul (p q : Eis) : Eis := (p.1 * q.1 - p.2 * q.2, p.1 * q.2 + p.2 * q.1 - p.2 * q.2)
def econj (p : Eis) : Eis := (p.1 - p.2, - p.2)
def eadd (p q : Eis) : Eis := (p.1 + q.1, p.2 + q.2)
def herm (u v : List Eis) : Eis := (List.zipWith (fun a b => emul (econj a) b) u v).foldl eadd (0, 0)
def orth (u v : List Eis) : Bool := herm u v == (0, 0)
def ray (rays : List (List Eis)) (i : Nat) : List Eis := rays.getD i []
def orthI (rays : List (List Eis)) (i j : Nat) : Bool := orth (ray rays i) (ray rays j)
def pickable (rays : List (List Eis)) (ones zeros : List Nat) (v : Nat) : Bool :=
  !(zeros.contains v) && !(ones.any (fun o => orthI rays o v))
def solve (rays : List (List Eis)) (bs : List (Nat × Nat × Nat)) (ones zeros : List Nat) (fuel : Nat) : Bool :=
  match fuel with
  | 0 => false
  | Nat.succ fuel => match bs with
    | [] => true
    | (a, b, c) :: rest =>
      let cnt := (if ones.contains a then 1 else 0) + (if ones.contains b then 1 else 0) + (if ones.contains c then 1 else 0)
      if cnt > 1 then false
      else if cnt == 1 then solve rays rest ones (([a,b,c].filter (fun v => !ones.contains v)) ++ zeros) fuel
      else [a,b,c].any (fun v => pickable rays ones zeros v &&
             solve rays rest (v :: ones) (([a,b,c].filter (fun w => w != v)) ++ zeros) fuel)
def rays : List (List Eis) := {_RAYS}
def bases : List (Nat × Nat × Nat) := {_BASES}"""

# Clean, legible statement — references the preamble's `solve`, `rays`, `bases`. `= false` ⇒ the
# backtracking search finds NO KS {0,1}-assignment. No `:=` (so `_join_proof` appends the proof intact).
_THEOREM_SRC = "theorem cabello_uncolorable : solve rays bases [] [] 30 = false"

_REFERENCES = [
    {"citation": ("Cabello, A. (2025). Simplest Kochen–Specker set. Physical Review Letters, 135, "
                  "190203 (arXiv:2508.07335)."),
     "url": "https://arxiv.org/abs/2508.07335"},
    {"citation": ("Yu, S., & Oh, C. H. (2012). State-independent proof of Kochen–Specker theorem with "
                  "13 rays. Physical Review Letters, 108, 030402."),
     "url": "https://doi.org/10.1103/PhysRevLett.108.030402"},
]


def build_theorem_src() -> str:
    return _THEOREM_SRC


def build_propositio() -> Propositio:
    en = Enuntiatio(
        statement=("The 33-vector, 14-basis Cabello set is a Kochen–Specker set (admits no {0,1} "
                   "coloring) — refuting the ≥16-basis conjecture (Cabello, PRL 135, 190203, 2025)"),
        claim_type=ClaimType.INVARIANT,
        falsifiable_claim=("a {0,1}-assignment f of the 33 rays with f(u)+f(v) ≤ 1 for orthogonal u,v "
                           "and exactly one 1 per orthonormal basis (a valid KS coloring)"),
        domain="quantum_contextuality",
    )
    ex = Expressio(theorem_src=_THEOREM_SRC, imports=(), preamble=_PREAMBLE)   # ADR 0062 legible preamble
    de = Demonstratio(proof_obligation="cabello_ks_uncolorable", proof_src="by decide")
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
        verifier = LeanVerifier(be)
        edge = verifier.discharge(ex, de)                       # THE ONLY kernel_verified writer
        ax = axiom_closure(be, ex.theorem_src, de.proof_src, ex.imports, allowed=frozenset({"propext"}),
                           preamble=ex.preamble)
    finally:
        be.close()

    print("=== ADR 0050 Phase 2 — Kochen–Specker uncolorability → amplified law ===")
    print(f"  kernel_verified : {de.kernel_verified}")
    print(f"  qed             : {de.qed}")
    print(f"  proof edge      : {edge.verdict.value} (producer {edge.producer})")
    print(f"  axiom_closure   : ok={ax['ok']} axioms={ax.get('axioms')}")
    if not (de.kernel_verified and de.qed == "Q.E.D." and ax["ok"]):
        print("!! discharge or axiom check failed — NOT emitting a law.")
        return 1
    prop.promulgated = True                                     # amplification promotion (report-only labels below)
    payload = law_payload(prop, published_at="", specimen=False,
                          tier="kernel-decided", origination="amplified", references=_REFERENCES,
                          figures=[ks_graph_figure()])   # ADR 0064: the orthogonality graph
    payload["$schema"] = "../../../.astro/collections/laws.schema.json"
    print(f"\n  law id          : {payload['id']}")
    print(f"  tier/origination: {payload['tier']} / {payload['origination']}")
    print(f"  references      : {len(payload['references'])} cited")
    print(f"  theorem_src     : {payload['theorem_src']}")
    print(f"  preamble        : {len(payload['preamble'])} chars ({payload['preamble'].count(chr(10)) + 1} lines, ADR 0062)")
    if write:
        _OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
        print(f"\n  WROTE {_OUT.relative_to(_ROOT)}")
    else:
        print("\n  (dry run — pass --write to emit the law JSON)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
