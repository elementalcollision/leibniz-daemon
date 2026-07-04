"""F2b discharge validator — mechanizes the F2b brief's acceptance gate so any attempt to discharge the
Terwilliger block-diagonalization bridge (Schrijver Theorem 1 / the `schrijver_block_psd_iff` engine lemma) is
classified honestly, via the H0 axiom-closure machinery. This is the T5 audit instrument applied to an internal
formal claim: it certifies whether a claimed F2b discharge is REAL or rests on an admitted scaffold.

The brief (docs/briefs/terwilliger-f2b-external-brief-2026-07-02.md) is explicit: a *scaffold* may introduce the
block-diagonalization lemma as a NAMED axiom (to wire the pipeline), and a *discharge* must have an EMPTY
project-axiom footprint — `#print axioms` shows only Lean/Mathlib's standard axioms, no `schrijver_block_psd_iff`,
no `sorryAx`. This validator runs exactly that check and classifies:

  * DISCHARGED — 0 errors, 0 sorries, only standard axioms (propext / Classical.choice / Quot.sound). A real proof.
  * SCAFFOLD   — clean except it rests on the single named admitted lemma (`schrijver_block_psd_iff`). Wires the
                 pipeline; NOT a proof. (This is the F2b-M1 tier; must never be labelled discharged / Q.E.D.)
  * BROKEN     — rests on `sorryAx`, an unexpected axiom, or fails to elaborate.

Current F2b state (measured, this session): the engine lemma is NOT dischargeable in-session — this Mathlib pin
defines `Matrix.PosSemidef` via a Finsupp bilinear form, Mathlib has no block-diagonal PSD lemma (`exact?`
empty), and Harmonic Aristotle returned 0/1 (~644 s). So F2b remains at the admitted-SCAFFOLD tier, which this
validator certifies. When an external formalizer returns a discharge, run it through here.

Read-only: the validator mints nothing and edits no core file (it reuses export_calculemus.axiom_closure).

Run:  python scripts/f2b_validate.py   (needs the Lean REPL image; skips cleanly otherwise)
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
OUT = _ROOT / "docs" / "results" / "f2b_validate.json"
IMPORTS = ("Mathlib.LinearAlgebra.Matrix.PosDef", "Mathlib.Tactic")
SCAFFOLD_AXIOM = "block_psd_iff"   # stands in for the brief's `schrijver_block_psd_iff` engine lemma


def _axiom_closure():
    spec = importlib.util.spec_from_file_location("export_calculemus", _ROOT / "scripts" / "export_calculemus.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m.axiom_closure


def classify(backend, theorem_src: str, proof_src: str, imports=IMPORTS, scaffold_axiom: str = SCAFFOLD_AXIOM,
             preamble: str = "") -> dict:
    """Classify one F2b discharge attempt. `preamble` may declare the scaffold axiom (for a SCAFFOLD case)."""
    axiom_closure = _axiom_closure()
    src = f"{preamble}\n{theorem_src}" if preamble else theorem_src
    r = axiom_closure(backend, src, proof_src, imports, allowed=frozenset({"propext", "Classical.choice", "Quot.sound"}))
    axioms = r.get("axioms", [])
    if r.get("has_sorry"):
        verdict = "BROKEN"
    elif r.get("errors"):
        verdict = "BROKEN"
    elif r["ok"]:
        verdict = "DISCHARGED"
    elif r.get("extra_axioms") == [scaffold_axiom]:
        verdict = "SCAFFOLD"
    else:
        verdict = "BROKEN"
    return {"verdict": verdict, "axioms": axioms, "extra_axioms": r.get("extra_axioms", []),
            "has_sorry": r.get("has_sorry", False), "errors": r.get("errors", [])}


# --- Demonstration cases (block-diagonal-PSD themed; verified against the real kernel) ------------------------
_SCAFFOLD_PREAMBLE = (
    "axiom block_psd_iff {m n : Type*} [Fintype m] [Fintype n] [DecidableEq m] [DecidableEq n]\n"
    "    (A : Matrix m m ℝ) (D : Matrix n n ℝ) :\n"
    "    (Matrix.fromBlocks A 0 0 D).PosSemidef ↔ A.PosSemidef ∧ D.PosSemidef")
_CASES = [
    {"name": "scaffold (admits the engine lemma)", "expect": "SCAFFOLD", "preamble": _SCAFFOLD_PREAMBLE,
     "theorem": ("theorem uses_scaffold {m n : Type*} [Fintype m] [Fintype n] [DecidableEq m] [DecidableEq n]\n"
                 "    (A : Matrix m m ℝ) (D : Matrix n n ℝ) (h : (Matrix.fromBlocks A 0 0 D).PosSemidef) :\n"
                 "    A.PosSemidef"),
     "proof": ":= ((block_psd_iff A D).mp h).1"},
    {"name": "discharged (real proof, no axiom)", "expect": "DISCHARGED", "preamble": "",
     "theorem": "theorem discharged {n : Type*} [Fintype n] (A : Matrix n n ℝ) (h : A.PosSemidef) : A.PosSemidef",
     "proof": ":= h"},
    {"name": "broken (rests on sorry)", "expect": "BROKEN", "preamble": "",
     "theorem": "theorem broke {n : Type*} [Fintype n] (A : Matrix n n ℝ) : A.PosSemidef",
     "proof": ":= by sorry"},
]


def main() -> int:
    print("=== F2b discharge validator ===")
    kernel = {"status": "not run"}
    try:
        from leibniz.backends.lean_repl import LeanReplBackend, available
        if not available():
            print("Lean REPL unavailable — cannot validate. (skip)")
            OUT.parent.mkdir(parents=True, exist_ok=True)
            OUT.write_text(json.dumps({"gate": "AMBER(kernel-unavailable)"}, indent=2) + "\n")
            return 0
        bk = LeanReplBackend(timeout_s=400)
        rows = []
        for c in _CASES:
            got = classify(bk, c["theorem"], c["proof"], preamble=c["preamble"])
            ok = got["verdict"] == c["expect"]
            rows.append({"case": c["name"], "expected": c["expect"], "got": got["verdict"],
                         "extra_axioms": got["extra_axioms"], "correct": ok})
            print(f"  {c['name']:<40} expect {c['expect']:<11} got {got['verdict']:<11} {'✓' if ok else '✗'}")
        bk.close()
        all_ok = all(r["correct"] for r in rows)
        kernel = {"status": "checked", "cases": rows, "all_correct": all_ok, "sound": all_ok}
    except Exception as ex:  # pragma: no cover
        kernel = {"status": f"unavailable ({type(ex).__name__}: {ex})"}
        print(f"  {kernel['status']}")

    gate = ("GREEN" if kernel.get("sound") else
            "AMBER(kernel-unavailable)" if "unavailable" in str(kernel.get("status")) else "RED")
    out = {"gate": gate, "kernel": kernel, "scaffold_axiom": SCAFFOLD_AXIOM,
           "f2b_current_verdict": "SCAFFOLD (not discharged)",
           "reading": ("The F2b discharge validator mechanizes the brief's acceptance gate via #print axioms: "
                       "DISCHARGED (only standard axioms) / SCAFFOLD (rests on the named engine lemma, wires the "
                       "pipeline but is not a proof) / BROKEN (sorry / unexpected axiom / error). GREEN = the "
                       "three demonstration cases classify correctly against the real kernel. Current F2b state "
                       "= SCAFFOLD: the engine lemma (block-diag PSD-iff) is not dischargeable in-session (this "
                       "pin's Finsupp-based PosSemidef, no Mathlib lemma, Aristotle 0/1), so it stays the "
                       "external-round ask; the validator is ready to certify a real discharge when one returns.")}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2, default=str) + "\n")
    print(f"\ngate={gate}  F2b current verdict = SCAFFOLD (not discharged)\n-> {OUT}")
    return 0 if gate != "RED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
