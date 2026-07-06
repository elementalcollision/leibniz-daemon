#!/usr/bin/env python3
"""
Proof-of-Concept: Leanstral 1.5 as a kernel-checked prover in the Leibniz theorem daemon.

Leibniz's one invariant: LLMs PROPOSE; only mechanical checkers — the Lean 4.31 kernel, Z3,
and exact decision procedures — DECIDE. Leanstral drafts a Lean 4 proof; the Lean kernel
re-verifies it against `theorem := proof`. A wrong draft is simply rejected: the model never
gets to claim correctness, so a plausible-but-wrong proof cannot slip through.

Integration cost: ZERO code changes. Leanstral speaks the OpenAI chat-completions API, so
Leibniz's existing per-model gateway routing reaches it by config alone:

    MISTRAL_API_KEY=<your key>
    LEIBNIZ_GATEWAY_MISTRAL_URL=https://api.mistral.ai/v1/chat/completions
    LEIBNIZ_PROVER_MODELS=labs-leanstral-1-5@mistral

Prereqs:
    git clone https://github.com/elementalcollision/leibniz-daemon && cd leibniz-daemon
    pip install -e ".[verify,propose]"
    # Docker running (the pinned Lean 4.31 kernel REPL image), and MISTRAL_API_KEY exported.

Run:  python leanstral_leibniz_poc.py
"""
import os

# --- the entire integration: three env lines, then use Leibniz's normal prover API ------------
os.environ.setdefault("LEIBNIZ_GATEWAY_MISTRAL_URL", "https://api.mistral.ai/v1/chat/completions")
os.environ.setdefault("LEIBNIZ_PROVER_MODELS", "labs-leanstral-1-5@mistral")
os.environ.setdefault("LEIBNIZ_DECOMPOSE", "0")  # keep this demo to a single prover

# `prover_ensemble` reads the env config at call time, so the three lines above ARE the whole
# integration. (Imports follow them only for narrative clarity — hence the E402 waivers.)
from leibniz.assembly import prover_ensemble  # noqa: E402
from leibniz.backends.lean_repl import LeanReplBackend, available  # noqa: E402
from leibniz.consensus import normalize_proof  # noqa: E402
from leibniz.types import Role  # noqa: E402

THEOREMS = [
    "theorem t1 (n : Nat) : n + 0 = n",
    "theorem t2 (l : List Nat) : l.reverse.reverse = l",
    "theorem t3 (n : Nat) : n ≤ 2 * n",
    "theorem t4 : (2 : Nat) + 2 = 4",             # Leanstral often reaches for `native_decide` — Leibniz forbids it
    "theorem t5 (a b : Nat) : a + b = b + a",     # a known Leanstral blind spot — its draft fails to check
]

# Leibniz's real acceptance bar: the Lean kernel elaborates `theorem := proof` AND the proof's
# axiom footprint is clean — only Lean's canonical axioms, never `sorryAx` and never
# `native_decide` (which trusts the compiler, adding `Lean.ofReduceBool`). Nothing else is trusted.
_STD_AXIOMS = {"propext", "Classical.choice", "Quot.sound"}


def kernel_accepts(kernel, theorem_src, proof):
    name = theorem_src.split()[1]
    resp = kernel._run(f"{theorem_src} := {proof}\n#print axioms {name}", ("Mathlib",))
    if resp is None:
        return False, "kernel unavailable"
    msgs = resp.get("messages", [])
    if any(m.get("severity") == "error" for m in msgs):      # ignore linter warnings/info; only errors fail
        return False, "kernel rejected the proof (does not elaborate)"
    # read the `#print axioms` result specifically (not a linter warning that happens to have a bracket)
    axmsg = next((str(m.get("data", "")) for m in msgs
                  if "does not depend on any axioms" in str(m.get("data", ""))
                  or "depends on axioms" in str(m.get("data", ""))), "")
    if "sorryAx" in axmsg:
        return False, "proof depends on `sorry`"
    if "ofReduceBool" in axmsg or "native" in axmsg.lower():
        return False, "proof uses `native_decide` (trusts the compiler, not the kernel — forbidden)"
    if "does not depend on any axioms" in axmsg:
        return True, "kernel-verified, axiom-clean (depends on no axioms)"
    if "depends on axioms" in axmsg:
        listed = axmsg.split("[", 1)[1].rsplit("]", 1)[0].split(",")
        extra = [a.strip() for a in listed if a.strip() and a.strip() not in _STD_AXIOMS]
        if extra:
            return False, f"proof depends on non-standard axioms: {extra}"
        return True, f"kernel-verified, axiom-clean ({axmsg.split('[', 1)[1].rsplit(']', 1)[0].strip()})"
    return False, "no axiom footprint reported"


def main() -> None:
    if not available():
        raise SystemExit("Lean 4.31 kernel REPL image unavailable — is Docker running?")
    leanstral = prover_ensemble()[0]                 # labs-leanstral-1-5, via the Mistral gateway
    kernel = LeanReplBackend(timeout_s=180)
    print(f"proposer : {leanstral.model}")
    print("decider  : Lean 4.31 kernel + Leibniz axiom-clean bar (no native_decide, no sorry)\n")

    accepted = 0
    for src in THEOREMS:
        draft = normalize_proof(leanstral.propose(Role.PROOF_DRAFT, src))     # Leanstral PROPOSES
        ok, why = kernel_accepts(kernel, src, draft)                          # the kernel DECIDES
        accepted += ok
        print(f"{'✓ ACCEPT' if ok else '✗ REJECT'}  {src}")
        print(f"         {why}")
        print(f"         Leanstral proposed: {draft!r}\n")

    print(f"{accepted}/{len(THEOREMS)} drafts accepted. Only kernel-verified, axiom-clean proofs are "
          "trusted — LLMs propose, the kernel decides; a wrong or compiler-trusting draft is simply refused.")


if __name__ == "__main__":
    main()
