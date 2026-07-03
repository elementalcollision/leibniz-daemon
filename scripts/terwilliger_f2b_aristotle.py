"""F2b external formalization round via Harmonic Aristotle (task #101 follow-through, ADR 0028 path).

F2b's full Theorem 1 is a multi-week definitional build (Rmatrix/Mblock/U are not in Mathlib), so it is NOT
a single Aristotle goal. What IS a well-posed, self-contained, Mathlib-only MILESTONE — and a genuine gap
(Mathlib has no such lemma; only PosSemidef.submatrix) — is the ENGINE of Theorem 1's block decomposition:

    M0: a block-diagonal matrix is PSD iff each diagonal block is PSD.

Aristotle PROPOSES; our Lean kernel (LeanVerifier.discharge, the sole kernel_verified writer) DECIDES — so a
returned proof is worthless unless OUR kernel re-checks it. BILLABLE (minutes→hours). The human brief for the
Mathlib-community / panel channel stays at docs/briefs/terwilliger-f2b-external-brief-2026-07-02.md; this is
the automated-prover leg of the same round.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

_HERE = Path(__file__).resolve()
_WORKTREE = _HERE.parent.parent
sys.path.insert(0, str(_WORKTREE))
# The API key lives in the MAIN checkout's .env (gitignored → not copied into worktrees).
_MAIN_ENV = Path("/Users/dave/Claude_Primary/leibniz/.env")
OUT = _WORKTREE / "docs" / "results" / "terwilliger_f2b_aristotle.json"

IMPORTS = ("Mathlib.LinearAlgebra.Matrix.PosDef", "Mathlib.Tactic")

# M0 — block-diagonal PSD iff both blocks PSD (elaborates clean-with-sorry; verified before submission).
MILESTONES = {
    "M0_fromBlocks_zero_psd_iff": (
        "theorem psd_fromBlocks_zero_iff {m n : Type*} [Fintype m] [Fintype n] "
        "[DecidableEq m] [DecidableEq n] (A : Matrix m m ℝ) (D : Matrix n n ℝ) : "
        "(Matrix.fromBlocks A 0 0 D).PosSemidef ↔ A.PosSemidef ∧ D.PosSemidef"
    ),
}


def _verify(theorem_src: str, proof: str) -> bool:
    """Re-check Aristotle's proof against OUR kernel, with the imports M0 actually needs (the try_aristotle
    helper hardcodes Mathlib.Tactic, which lacks Matrix.PosSemidef — so this milestone needs its own leg)."""
    from leibniz.backends import lean_repl
    from leibniz.backends.lean_cli import LeanCliBackend
    from leibniz.propositio import Demonstratio, Expressio
    from leibniz.verifiers import LeanVerifier
    backend = lean_repl.LeanReplBackend() if lean_repl.available() else LeanCliBackend()
    lean = LeanVerifier(backend)
    expr = Expressio(theorem_src=theorem_src, imports=IMPORTS)
    demo = Demonstratio(proof_obligation="aristotle-f2b", proof_src=proof)
    ev = lean.discharge(expr, demo)
    return demo.kernel_verified and ev.verdict.name == "PASS"


def main() -> int:
    from leibniz.env import load_env
    load_env(_MAIN_ENV)
    from leibniz.providers.aristotle_provider import AristotleProver
    from leibniz.types import Role

    prover = AristotleProver()
    if not prover.available():
        print("[f2b] ARISTOTLE_API_KEY not set or aristotlelib missing.")
        return 2

    rows = []
    for name, stmt in MILESTONES.items():
        print(f"[f2b] submitting {name} …\n      {stmt[:120]}", flush=True)
        t0 = time.time()
        row = {"milestone": name, "statement": stmt}
        try:
            proof = prover.propose(Role.PROOF_DRAFT, stmt)
        except Exception as e:  # noqa: BLE001 -- surface live-API shape issues
            row.update(error=f"{type(e).__name__}: {e}", secs=round(time.time() - t0, 1))
            rows.append(row)
            print(f"  ! aristotle error: {row['error']}", flush=True)
            continue
        row["secs"] = round(time.time() - t0, 1)
        if not proof:
            row["result"] = "no_proof_returned"
            print(f"  → no proof ({row['secs']}s)", flush=True)
        else:
            row["proof_head"] = proof[:400]
            row["kernel_verified"] = _verify(stmt, proof)
            row["result"] = "QED" if row["kernel_verified"] else "REJECTED_by_our_kernel"
            print(f"  → {row['result']} ({row['secs']}s)", flush=True)
        rows.append(row)
        OUT.write_text(json.dumps({"rows": rows, "reading": (
            "F2b automated-prover leg (Aristotle proposes, our kernel decides). QED = Aristotle closed the "
            "milestone AND our Lean 4.31 kernel re-verified it — a real F2b sub-lemma banked. Anything else "
            "is honest negative signal on Aristotle's reach for this shape. Trust boundary intact: no bound "
            "or theorem is trusted without our kernel.")}, indent=2) + "\n")
    qed = [r for r in rows if r.get("kernel_verified")]
    print(f"[f2b] {len(qed)}/{len(rows)} milestones kernel-verified → {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
