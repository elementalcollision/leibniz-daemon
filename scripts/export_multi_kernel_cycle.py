"""Emit the ADR 0048 multi-kernel capability (Coq + Isabelle proof-edge deciders) as a Codex Calculemus
cycle (ADR 0017). A CAPABILITY cycle: it records a new faculty the daemon gained — independent re-decision in
a second and third kernel for verification-amplification — plus the live demo and the adversarial-hardening
finding. Carries no `kernel_verified`, mints no edge, promulgates nothing. Producer only.

Run:  python scripts/export_multi_kernel_cycle.py [-o FILE]
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from leibniz.calculemus_site import cycle_payload, downloadable_artifact  # noqa: E402

_ROOT = Path(__file__).resolve().parent.parent
_COQ = _ROOT / "docs" / "crt" / "coq_demo.v"
_ISA = _ROOT / "docs" / "crt" / "isabelle_demo.thy"

_SUMMARY = (
    "A new faculty for the daemon: independent re-decision of a proof in a SECOND and THIRD kernel. Leibniz's "
    "proof edge had one arbiter, the Lean 4.31 kernel. This cycle adds report-only backends for the Rocq 9.0 "
    "(Coq) and Isabelle2025 kernels, so a published result can be re-decided in a different trusted core — "
    "strictly stronger evidence than re-running the same one, because an independent kernel catches "
    "translation and kernel-specific errors a single-checker pipeline cannot. Both are LIVE for "
    "verification-amplification (audit tier) and DORMANT for promulgation: they never write kernel_verified, "
    "mint no proof edge, and — until an operator admits their producer strings under the ADR 0041/0045 "
    "allowlist ritual — the trust policy rejects any Coq/Isabelle proof edge structurally, so the trust "
    "boundary is unchanged (all four structural guards stay byte-identical). The backends genuinely GATE, not "
    "rubber-stamp: on the demo certificates each kernel accepts real theorems (Coq's add_comm / app_assoc / "
    "rev_involutive; Isabelle's add_comm / rev_rev / Gauss's summation) and REJECTS both self-laundered "
    "proofs (Coq `Admitted`; Isabelle `sorry`) and broken proofs. A three-round adversarial review (six "
    "false-PASS holes found and closed, each pinned as a regression test) drew a hard, honest line between "
    "the two kernels' trust. For Coq the axiom audit is KERNEL-DRIVEN AND SOUND: after compiling, the backend "
    "runs Rocq's own library checker `rocqchk`, which reports the whole development's axioms and unsafe "
    "constructs name-agnostically, with the authentic verdict fenced off by an unforgeable random nonce the "
    "compiled source cannot read; a final 25-attack validation could not certify a single proof of False. For "
    "Isabelle, which exposes no such report reachable without ML, the check is a comprehensive source "
    "blocklist that is NOT adversarially sound (each review round found a fresh route: a cheat tactic, then a "
    "setup-ML axiom injection, then a code_printing + eval); it is therefore scoped to trusted-provenance "
    "amplification only, with a kernel proof-term audit recorded as the blocking prerequisite for any Isabelle "
    "promotion. LLMs propose nothing here; the kernels decide, and the daemon reports what they said."
)

_FINDINGS = [
    {"id": "capability", "claim": "Independent Coq (Rocq 9.0) + Isabelle2025 re-decision, report-only",
     "verdict": "DELIVERED",
     "note": "leibniz/backends/coq_docker.py + isabelle_docker.py, built to the lean_cli contract; they only "
             "REPORT the kernel verdict. Coq amd64-under-Rosetta; Isabelle native arm64. No trust surface: "
             "trust.py / verifiers.py / test_invariants.py / the two write-guard tests are byte-identical."},
    {"id": "gate", "claim": "Both kernels gate on the demo certificates (accept real, reject laundered/broken)",
     "verdict": "CERTIFIED",
     "note": "Coq: add_comm, app_assoc, rev_involutive verified (rocqchk: axioms <none>); `Admitted` and a "
             "false goal rejected. Isabelle: add_comm, rev_rev, Gauss's summation built; `sorry` (hard error "
             "at quick_and_dirty=false) and a false goal rejected. scripts/verify_multi_kernel.py — gate GREEN."},
    {"id": "coq-sound", "claim": "The Coq axiom/unsafe audit is kernel-driven and sound", "verdict": "CERTIFIED",
     "note": "`rocqchk -o` re-validates the compiled .vo and reports the whole development's axioms + "
             "type-in-type / unsafe-(co)fixpoint / assumed-positivity name-agnostically; an unforgeable nonce "
             "authenticates the verdict against source output-injection. A 25-attack adversarial validation "
             "found no false PASS (no proof of False, no hidden axiom, no forged summary)."},
    {"id": "isabelle-scope", "claim": "The Isabelle check is best-effort, NOT adversarially sound", "verdict": "NOTED",
     "note": "No rocqchk-equivalent is reachable without ML, so the backend is a comprehensive source "
             "blocklist; three review rounds each found a fresh laundering route. Scoped to trusted-provenance "
             "amplification only; a kernel proof-term audit (Thm_Deps.thm_oracles + axiom deps from a wrapper "
             "theory) is the blocking prerequisite for Isabelle promotion (ADR 0048 §2/§4.2, HANDOFF ticket)."},
    {"id": "promotion", "claim": "Promotion to a proof-edge decider is deferred and operator-gated",
     "verdict": "NOTED",
     "note": "The CoqVerifier/IsabelleVerifier + registry that would write kernel_verified are NOT landed — "
             "prototyping them tripped the structural trust guards. The KERNEL_PRODUCER→KERNEL_PRODUCERS edit "
             "+ guard-whitelist edits are an operator keystone, gated per the ADR 0045 8/8 proof-edge deferral."},
]

_ARTIFACTS = [
    downloadable_artifact(_COQ, cycle_id="cycle_000016", kind="coq-proof",
                          checker="Rocq 9.0 kernel (rocq compile + rocqchk audit)",
                          result="3 theorems verified; rocqchk CONTEXT SUMMARY: axioms <none>, no unsafe constructs"),
    downloadable_artifact(_ISA, cycle_id="cycle_000016", kind="isabelle-proof",
                          checker="Isabelle2025 kernel (isabelle build, quick_and_dirty=false)",
                          result="3 lemmas built; sorry hard-errors, no ML/oracle/code-gen escape hatch"),
]

_REFERENCES = [
    {"citation": ("The Rocq Development Team. (2025). The Rocq Prover (Version 9.0) [Computer software]. Inria, "
                  "CNRS, and contributors."), "url": "https://rocq-prover.org/"},
    {"citation": ("Nipkow, T., Paulson, L. C., & Wenzel, M. (2025). Isabelle/HOL: A proof assistant for "
                  "higher-order logic (Isabelle2025) [Computer software]. Technische Universität München & "
                  "University of Cambridge."), "url": "https://isabelle.in.tum.de/"},
    {"citation": ("de Moura, L., & Ullrich, S. (2021). The Lean 4 theorem prover and programming language. In "
                  "Automated Deduction – CADE 28 (pp. 625–635). Springer."), "url": "https://lean-lang.org/"},
]

_REPOSITORIES = [
    {"name": "elementalcollision/leibniz-daemon #297",
     "url": "https://github.com/elementalcollision/leibniz-daemon/pull/297",
     "role": "produced",
     "note": "ADR 0048: leibniz/backends/{coq_docker,isabelle_docker}.py + scripts/verify_multi_kernel.py + "
             "docs/crt/{coq_demo.v,isabelle_demo.thy}; report-only, trust boundary unchanged."},
]

_TARGET = "elementalcollision/codex-calculemus : ledger/calculemus.json -> cycles[]"


def build_cycle() -> dict:
    return cycle_payload(
        cycle=16, date="2026-07-05", domain="Formal verification", kind="capability",
        title="Independent Coq (Rocq 9.0) + Isabelle2025 re-decision for verification-amplification (ADR 0048)",
        summary=_SUMMARY, findings=_FINDINGS, artifacts=_ARTIFACTS, references=_REFERENCES,
        repositories=_REPOSITORIES)


def build_fragment(*, generated_at: str = "") -> dict:
    return {"meta": {"generated_at": generated_at, "producer": "scripts/export_multi_kernel_cycle.py",
                     "target": _TARGET,
                     "merge": "append to cycles[]; copy docs/crt/coq_demo.v and docs/crt/isabelle_demo.thy to "
                              "public/artifacts/cycle_000016/."},
            "cycles": [build_cycle()]}


def main(argv: list[str]) -> int:
    stamp = (argv[argv.index("--generated-at") + 1] if "--generated-at" in argv
             else datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
    text = json.dumps(build_fragment(generated_at=stamp), indent=2, ensure_ascii=False) + "\n"
    if "-o" in argv:
        Path(argv[argv.index("-o") + 1]).write_text(text)
        print(f"wrote (target: {_TARGET})")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
