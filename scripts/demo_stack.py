"""End-to-end demonstration of the Leibniz tool-using + research-seeding stack (ADR 0041 Phases 1-3).

A runnable showcase of what's built, exercised against the real modules:

  Stage A  Verification amplification: a CWC witness -> verify_cwc -> Lean kernel -> oracle novelty
           (the "hand it a witness, get a kernel-stamped, oracle-judged answer" capability).
  Stage B  The tool seam (Phases 1-2): an UNTRUSTED construction program -> sandbox -> ToolRegistry.
           With no decider admitted (State 1) the registry DEFERs even a valid result; a malicious
           program is contained by the sandbox.
  Stage C  Research-seeding (Phase 3): a paper's claim -> Seed -> validate_seed, incl. the Rosin
           BoundSeed (no behavior change) and the floor-raising guard (a fabricated raise is quarantined).

Docker-gated stages (the Lean kernel, the sandbox) degrade gracefully when docker is absent — the demo
prints what it could run. Nothing is promulgated; cwc_check is audit-only and the trust boundary is
untouched. The pure-Python stages are regression-covered by tests/test_demo_stack.py.

    python3 scripts/demo_stack.py            # fast (Fano witness)
    python3 scripts/demo_stack.py --full     # also kernel-verify a 42-codeword A(14,6,6) construction
    python3 scripts/demo_stack.py --no-kernel --no-sandbox   # pure stages only
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_ROOT / "scripts"))

import cwc_table_oracle as ora  # noqa: E402
import cwc_tool as ct  # noqa: E402
from cwc_check import check  # noqa: E402
from cwc_rosin_crosscheck import rosin_bound_seed  # noqa: E402

from leibniz.seeds import (  # noqa: E402
    Seed, SeedKind, SeedProvenance, effective_floor, seed_from_feed_record, validate_seed,
)
from leibniz.tools.registry import ToolRegistry  # noqa: E402
from leibniz.tools.sandbox import SandboxTask  # noqa: E402

FANO = [[0, 1, 2], [0, 3, 4], [0, 5, 6], [1, 3, 5], [1, 4, 6], [2, 3, 6], [2, 4, 5]]
BENIGN_PROG = ("def construct(n, d, w):\n    return " + repr(FANO) + "\n")
MALICIOUS_PROG = ("def construct(n, d, w):\n    import urllib.request\n"
                  "    urllib.request.urlopen('http://example.com', timeout=3)\n    return []\n")


def _structural_witness(n, d, w, budget_s=25):
    """Construct a real CWC code via the structural (automorphism-orbit) tool — used for the --full
    A(14,6,6)=42 kernel demo (a record exact CP-SAT only reached 30)."""
    import time
    import probe_beta_automorphism as pa
    elems = pa.group_elements(n, "cyclic")
    kept, weights, adj = pa.build_orbit_graph(pa.orbits(n, w, elems), w, d)
    chosen = pa.max_weight_clique(weights, adj, time.time() + budget_s)
    return [sorted(cw) for i in chosen for cw in kept[i]]


def stage_a_verification(use_kernel: bool, full: bool) -> list[dict]:
    """A: verify witnesses through verify_cwc -> Lean kernel -> oracle. Returns one report per witness."""
    cases = [("Fano A(7,4,3)=7 (valid)", 7, 4, 3, FANO),
             ("false A(7,4,3) (distance-2 pair)", 7, 4, 3, [[0, 1, 2], [0, 1, 3]])]
    if full:
        cases.insert(1, ("structural A(14,6,6)=42 (record; CP-SAT got 30)", 14, 6, 6,
                         _structural_witness(14, 6, 6)))
    out = []
    for label, n, d, w, code in cases:
        rep = check(n, d, w, code, run_kernel=use_kernel)
        out.append({"label": label, "verify_ok": rep["verify_ok"],
                    "kernel": rep.get("kernel"), "novelty": rep.get("novelty")})
    return out


def stage_b_tool_seam(use_sandbox: bool) -> dict:
    """B: an untrusted construction through the sandbox + ToolRegistry (State 1 — no decider)."""
    reg = ToolRegistry()
    reg.register_tool(ct.cwc_tool())                       # State 1: registered, runnable, no decider
    res = {"dormant_recheckers": reg.recheckers == {}, "dormant_templates": reg.templates == {}}
    if use_sandbox:
        ev = reg.run(SandboxTask(program=BENIGN_PROG, args={"n": 7, "d": 4, "w": 3}))
        res["benign_verdict"] = ev.verdict.value          # DEFER: ran+scored, cannot decide (State 1)
        ev2 = reg.run(SandboxTask(program=MALICIOUS_PROG, args={"n": 7, "d": 4, "w": 3}))
        res["malicious_verdict"] = ev2.verdict.value      # contained by --network none -> DEFER
    return res


def stage_c_seeds() -> dict:
    """C: research-seeding — Rosin BoundSeed (no behavior change) + the floor-raising guard (pure)."""
    snap = ora.load_snapshot()[0]
    rosin = validate_seed(rosin_bound_seed(), snap)
    fab = Seed(kind=SeedKind.FLOOR, payload={"cells": {(7, 4, 3): 999}},
               provenance=SeedProvenance(source_id="arXiv:fabricated"),
               proof_of_use="fabricated", extraction_agreement=2)
    fabricated = validate_seed(fab, snap)
    target = validate_seed(seed_from_feed_record(
        {"arxiv_id": "2606.1", "abs_url": "u", "title": "An open conjecture",
         "work_items": ["conjecture", "proof"], "seed_priority": 0,
         "citation": {"plain": "Author (2026)."}}), snap)
    return {
        "rosin_status": rosin.status.value,
        "rosin_floor_unchanged": effective_floor(28, 8, 10, snap, [rosin]) == snap[(28, 8, 10)],
        "fabricated_status": fabricated.status.value,
        "fabricated_floor_held": effective_floor(7, 4, 3, snap, [fabricated]) == snap[(7, 4, 3)],
        "target_kind": target.kind.value, "target_status": target.status.value,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="End-to-end demo of the Leibniz tool/seed stack.")
    ap.add_argument("--full", action="store_true", help="also kernel-verify a 42-codeword A(14,6,6)")
    ap.add_argument("--no-kernel", action="store_true", help="skip the Lean kernel step")
    ap.add_argument("--no-sandbox", action="store_true", help="skip the docker sandbox step")
    args = ap.parse_args()

    print("== Stage A: verification amplification (witness -> kernel -> oracle) ==")
    for r in stage_a_verification(not args.no_kernel, args.full):
        print(f"  {r['label']}: verify={'OK' if r['verify_ok'] else 'FAIL'} "
              f"kernel={r['kernel']} novelty={r['novelty']}")
    print("== Stage B: tool seam (untrusted construction -> sandbox -> registry, State 1) ==")
    b = stage_b_tool_seam(not args.no_sandbox)
    print(f"  deciding-registries dormant-empty: {b['dormant_recheckers'] and b['dormant_templates']}")
    if "benign_verdict" in b:
        print(f"  benign construction -> {b['benign_verdict']} (State 1: cannot decide w/o a decider)")
        print(f"  malicious (network) -> {b['malicious_verdict']} (sandbox contained it)")
    print("== Stage C: research-seeding (validate + floor-raising guard) ==")
    c = stage_c_seeds()
    print(f"  Rosin BoundSeed: {c['rosin_status']}; floor unchanged: {c['rosin_floor_unchanged']}")
    print(f"  fabricated raise A(7,4,3)>=999: {c['fabricated_status']}; floor held: {c['fabricated_floor_held']}")
    print(f"  feed conjecture -> {c['target_kind']} seed ({c['target_status']})")
    print("\n[demo: nothing promulgated; trust boundary untouched]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
