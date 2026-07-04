"""Smoke-test the two ADR 0028 lever-3 proving paths the operator asked us to actually USE.

  (1) Goedel-Prover-V2 via Featherless — a STANDING ensemble member (flat-rate; no marginal
      cost). We run the FULL loop: Goedel PROPOSES a proof of a non-trivial lemma and OUR Lean
      kernel DECIDES (LeanVerifier.discharge, the sole kernel_verified writer). That proves the
      Featherless routing works end-to-end AND re-affirms the trust boundary.
  (2) Harmonic Aristotle — ON-DEMAND escalation only (per-run billable, minutes→hours). We check
      AVAILABILITY here (key + aristotlelib importable); a real proof run is left to
      `scripts/try_aristotle.py` on a hard goal.

Usage (needs FEATHERLESS_API_KEY / ARISTOTLE_API_KEY in .env; the Featherless leg is flat-rate,
no Aristotle billing incurred):
    python scripts/smoke_provers.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO))

from leibniz.env import load_env  # noqa: E402

# Worktrees share the parent checkout's gitignored .env; fall back to the main repo root.
_ENV = _REPO / ".env"
if not _ENV.exists():
    for up in _REPO.parents:
        if (up / ".env").exists():
            _ENV = up / ".env"
            break
print(f"[env] loading {_ENV} -> {load_env(_ENV)} vars")

from leibniz.types import Role  # noqa: E402


def _kernel_verify(theorem_src: str, proof: str) -> bool:
    from leibniz.backends import lean_repl
    from leibniz.backends.lean_cli import LeanCliBackend
    from leibniz.propositio import Demonstratio, Expressio
    from leibniz.verifiers import LeanVerifier
    backend = lean_repl.LeanReplBackend(timeout_s=180) if lean_repl.available() else LeanCliBackend()
    lean = LeanVerifier(backend)
    expr = Expressio(theorem_src=theorem_src, imports=("Mathlib.Tactic",))
    demo = Demonstratio(proof_obligation="goedel", proof_src=proof)
    ev = lean.discharge(expr, demo)   # sole kernel_verified writer
    try:
        backend.close()
    except Exception:
        pass
    return demo.kernel_verified and ev.verdict.name == "PASS"


def _extract_proof(text: str) -> str:
    """Goedel returns reasoning then a fenced `theorem ... := by ...`; keep the `by ...` body."""
    t = text.strip()
    if "```" in t:
        t = max(t.split("```"), key=len).strip()
        if t.startswith("lean"):
            t = t[4:].strip()
    cut = t.find(":= by")
    if cut != -1:
        return t[cut + 3:].strip()
    cut = t.find(":=")
    return t[cut + 2:].strip() if cut != -1 else t


def _propose_with_retry(prov, prompt, tries=4):
    """Featherless 503s are transient cold-start/capacity; retry with backoff."""
    import urllib.error
    for k in range(tries):
        try:
            return prov.propose(Role.PROOF_DRAFT, prompt)
        except urllib.error.HTTPError as e:
            if e.code == 503 and k < tries - 1:
                print(f"    (503, retry {k + 1}/{tries - 1})")
                time.sleep(6 * (k + 1))
                continue
            raise


def smoke_featherless() -> bool:
    from leibniz.providers.openrouter_provider import OpenRouterProvider
    theorem_src = "theorem t (n : Nat) : 6 ∣ n * (n + 1) * (n + 2)"
    prompt = f"Complete the following Lean 4 code:\n\n```lean\nimport Mathlib\n\n{theorem_src} := by\n```\n"
    for model in ("Goedel-LM/Goedel-Prover-V2-8B", "Goedel-LM/Goedel-Prover-V2-32B"):
        prov = OpenRouterProvider(
            model=model, api_key_env="FEATHERLESS_API_KEY",
            url="https://api.featherless.ai/v1/chat/completions", max_tokens=4096, timeout_s=300,
        )
        print(f"\n[featherless] model={model}  available={prov.available()}")
        if not prov.available():
            print("  ! FEATHERLESS_API_KEY not set — skipping.")
            continue
        t0 = time.time()
        try:
            raw = _propose_with_retry(prov, prompt)
        except Exception as e:
            print(f"  ! API error: {type(e).__name__}: {str(e)[:300]}")
            continue
        proof = _extract_proof(raw)
        print(f"  → returned in {time.time() - t0:.0f}s; proof head: {proof[:200]!r}")
        ok = _kernel_verify(theorem_src, proof)
        print(f"  → OUR kernel: {'Q.E.D.' if ok else 'REJECTED'}")
        if ok:
            return True
    return False


def smoke_aristotle() -> bool:
    from leibniz.providers.aristotle_provider import AristotleProver
    ok = AristotleProver().available()
    print(f"\n[aristotle] available={ok}  (on-demand escalation: a full proof run is "
          f"minutes→hours + billable — use scripts/try_aristotle.py on a hard goal)")
    return ok


def main() -> int:
    print("=" * 70)
    fx = smoke_featherless()
    ar = smoke_aristotle()
    print("\n" + "=" * 70)
    print(f"Featherless→kernel round-trip (standing prover): {'PASS' if fx else 'FAIL'}")
    print(f"Aristotle available (on-demand escalation):      {'YES' if ar else 'NO'}")
    return 0 if fx else 1


if __name__ == "__main__":
    raise SystemExit(main())
