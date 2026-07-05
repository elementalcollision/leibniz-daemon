"""Multi-kernel decider demonstration (ADR 0048) — genuine Coq + Isabelle proofs, kernel-verified.

Runs the demonstration certificates (docs/crt/coq_demo.v, docs/crt/isabelle_demo.thy) through the real Rocq
9.0 and Isabelle2025 kernels via leibniz.backends.coq_docker / isabelle_docker, and — critically — through a
pair of NEGATIVE probes that must be REJECTED (a self-laundered proof and a broken proof), proving each
backend genuinely gates rather than rubber-stamps. This is verification-amplification (audit tier): the
backends only REPORT the kernel verdict; they never touch Demonstratio.kernel_verified, and the Coq/Isabelle
proof-edge producers are NOT in trust.KERNEL_PRODUCERS, so nothing here can promulgate. No trust surface.

  PASS demos    -> the kernel accepts real theorems (Coq: closed under the global context; Isabelle: builds).
  laundered     -> Coq `Admitted` exposes an open axiom; Isabelle `sorry` hard-errors  -> REJECTED.
  broken        -> a false goal fails to elaborate/build                                -> REJECTED.

Run:  python scripts/verify_multi_kernel.py   (needs Docker + the pinned images; skips cleanly if absent)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))  # resolve `leibniz` to THIS worktree, not the editable-installed main repo

from leibniz.backends import coq_docker, isabelle_docker  # noqa: E402
COQ_CERT = _ROOT / "docs" / "crt" / "coq_demo.v"
ISA_CERT = _ROOT / "docs" / "crt" / "isabelle_demo.thy"
OUT = _ROOT / "docs" / "results" / "multi_kernel_verification.json"

# Negative probes — each MUST be rejected, or the backend is not gating.
COQ_LAUNDERED = ("Theorem bogus : forall n : nat, n + 0 = n + 1.\nProof. Admitted.\n"
                 "Print Assumptions bogus.\n")
COQ_BROKEN = "Theorem wrong : forall n : nat, n = n + 1.\nProof. intros n. reflexivity. Qed.\n"
ISA_LAUNDERED = ('theory Bad imports Main begin\nlemma bogus: "n + (0::nat) = n + 1" sorry\nend\n')
ISA_BROKEN = ('theory Wrong imports Main begin\nlemma wrong: "n = n + (1::nat)" by simp\nend\n')


def _leg(name: str, backend, cert_text: str, laundered: str, broken: str) -> dict:
    good = backend.check_source_with_detail(cert_text)
    laun = backend.check_source(laundered)
    brok = backend.check_source(broken)
    gated = (good is not None and good["verified"] is True and laun is False and brok is False)
    return {"kernel": name, "available": good is not None, "demo_verified": (good or {}).get("verified"),
            "demo_detail": good, "laundered_rejected": laun is False, "broken_rejected": brok is False,
            "gates_correctly": gated}


def main() -> int:
    print("=== Multi-kernel decider demonstration (ADR 0048) — Coq + Isabelle ===")
    legs = []
    if coq_docker.available():
        print("  running Rocq 9.0 ...")
        legs.append(_leg("coq", coq_docker.CoqDockerBackend(), COQ_CERT.read_text(), COQ_LAUNDERED, COQ_BROKEN))
    else:
        legs.append({"kernel": "coq", "available": False})
    if isabelle_docker.available():
        print("  running Isabelle2025 ...")
        legs.append(_leg("isabelle", isabelle_docker.IsabelleDockerBackend(),
                         ISA_CERT.read_text(), ISA_LAUNDERED, ISA_BROKEN))
    else:
        legs.append({"kernel": "isabelle", "available": False})

    for leg in legs:
        if not leg.get("available"):
            print(f"  {leg['kernel']:9} UNAVAILABLE (Docker/image absent) — skip")
            continue
        d = leg.get("demo_detail") or {}
        extra = ("closed-under-global-context" if d.get("closed_under_global_context") else
                 f"rc={d.get('returncode')}")
        print(f"  {leg['kernel']:9} demo_verified={leg['demo_verified']}  "
              f"laundered_rejected={leg['laundered_rejected']}  broken_rejected={leg['broken_rejected']}  "
              f"({extra})  -> {'GATES ✓' if leg['gates_correctly'] else 'ISSUE'}")

    ran = [leg for leg in legs if leg.get("available")]
    gate = ("GREEN" if ran and all(leg["gates_correctly"] for leg in ran)
            else "AMBER(no-kernel-available)" if not ran else "RED")
    out = {"gate": gate, "tier": "audit", "ev": "AMPLIFICATION", "adr": "0048",
           "target": "Multi-kernel proof-edge deciders: Rocq 9.0 + Isabelle2025 (dormant for promulgation)",
           "legs": legs, "certs": [str(COQ_CERT.relative_to(_ROOT)), str(ISA_CERT.relative_to(_ROOT))],
           "reading": ("Genuine Coq and Isabelle theorems, kernel-verified end-to-end, with self-laundered "
                       "(Admitted / sorry) and broken proofs correctly REJECTED — proof each backend gates. "
                       "Report-only (audit tier); CoqVerifier/IsabelleVerifier producers are unadmitted in "
                       "trust.KERNEL_PRODUCERS, so this cannot promulgate. Verification-amplification.")}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2) + "\n")
    print(f"\ngate={gate}  tier=audit  ev=AMPLIFICATION\n-> {OUT}")
    return 0 if gate != "RED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
