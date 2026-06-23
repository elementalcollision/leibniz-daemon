"""Try Harmonic Aristotle on a hard goal — and RE-VERIFY its proof with our own kernel.

Aristotle PROPOSES a proof; Leibniz's Lean kernel (LeanVerifier.discharge) DECIDES — so
this both exercises the live aristotlelib flow (confirming the submit→poll→get_files
assumptions in AristotleProver) and proves the trust boundary holds end-to-end: a hosted
agent's output is worthless to us unless OUR kernel re-checks it.

Usage (needs ARISTOTLE_API_KEY in .env; BILLABLE — Aristotle runs minutes→hours):
    python scripts/try_aristotle.py "theorem t (n : Nat) : 6 ∣ n*(n+1)*(n+2)"
    python scripts/try_aristotle.py --from-memory 3     # N LEAN near-misses the kernel couldn't close
    python scripts/try_aristotle.py --from-notebook 3   # N human-prose near-misses (NL; needs formalize)
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
_REPO = Path(__file__).resolve().parent.parent


def _verify(theorem_src: str, proof: str) -> bool:
    """Re-check Aristotle's proof against OUR kernel (REPL if available, else CLI)."""
    from leibniz.backends import lean_repl
    from leibniz.backends.lean_cli import LeanCliBackend
    from leibniz.propositio import Demonstratio, Expressio
    from leibniz.verifiers import LeanVerifier
    backend = lean_repl.LeanReplBackend() if lean_repl.available() else LeanCliBackend()
    lean = LeanVerifier(backend)
    # Re-verify with `Mathlib.Tactic`, not the root `Mathlib`: our Lean image ships the
    # component oleans but not the root aggregate, and Aristotle's tactic-style proofs
    # (norm_num/interval_cases/Nat lemmas) resolve under Mathlib.Tactic. (Building the root
    # Mathlib.olean into the image is the durable fix for full-import coverage.)
    expr = Expressio(theorem_src=theorem_src, imports=("Mathlib.Tactic",))
    demo = Demonstratio(proof_obligation="aristotle", proof_src=proof)
    ev = lean.discharge(expr, demo)   # sole kernel_verified writer
    return demo.kernel_verified and ev.verdict.name == "PASS"


def _goals(argv: list[str]) -> list[str]:
    if len(argv) >= 2 and argv[0] == "--from-memory":
        # The daemon's LEAN near-misses: recent candidates that reached formalization but
        # the kernel never closed. This is what Aristotle needs (valid Lean theorem_src),
        # unlike --from-notebook (human prose). Most-recent-first, deduped.
        from leibniz.runtime import PersistentRuntime
        n = int(argv[1])
        seen: set[str] = set()
        out: list[str] = []
        for p in PersistentRuntime().recall_recent(200):
            ts = p.expressio.theorem_src if p.expressio else None
            if not ts or ts in seen or (p.demonstratio and p.demonstratio.kernel_verified):
                continue
            seen.add(ts)
            out.append(ts)
            if len(out) >= n:
                break
        return out
    if len(argv) >= 2 and argv[0] == "--from-notebook":
        import json  # NB: notebook holds HUMAN statements (NL) — only usable if Aristotle formalizes
        n = int(argv[1])
        nb = json.loads((_REPO / ".leibniz" / "notebook.json").read_text())
        return [f"theorem t : {s}" if not s.strip().startswith(("theorem", "lemma")) else s
                for s in (nb.get("too_hard") or [])[:n]]
    return [argv[0]] if argv else []


def main() -> int:
    from leibniz.env import load_env
    load_env(_REPO / ".env")
    from leibniz.providers.aristotle_provider import AristotleProver
    from leibniz.types import Role

    goals = _goals(sys.argv[1:])
    if not goals:
        print(__doc__)
        return 2
    prover = AristotleProver()
    if not prover.available():
        print("[try_aristotle] ARISTOTLE_API_KEY not set or aristotlelib missing.")
        return 2

    closed = 0
    for i, goal in enumerate(goals):
        print(f"\n[try_aristotle] goal {i}: {goal[:120]}")
        t0 = time.time()
        try:
            proof = prover.propose(Role.PROOF_DRAFT, goal)
        except Exception as e:  # surface live-API shape issues for iteration
            print(f"  ! aristotle error: {type(e).__name__}: {e}")
            continue
        dt = time.time() - t0
        if not proof:
            print(f"  → no proof returned ({dt:.0f}s)")
            continue
        print(f"  → Aristotle returned a proof ({dt:.0f}s):\n      {proof[:200]}")
        ok = _verify(goal, proof)
        print(f"  → OUR kernel re-verification: {'Q.E.D.' if ok else 'REJECTED'}")
        closed += int(ok)
    print(f"\n[try_aristotle] {closed}/{len(goals)} closed AND re-verified by our kernel.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
