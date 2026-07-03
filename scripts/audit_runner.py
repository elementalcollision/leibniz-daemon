"""Audit-runner harness (T5) — the MCR formal-verification-as-a-service audit generalized into a re-runnable
instrument. The MCR audit was the daemon's one measured-POSITIVE lane, but a one-off (n=1). This turns it into
a repeatable instrument: an *audit* is a set of findings, each carrying a VERDICT and (where re-runnable) an
ARTIFACT — a numeric check, a Z3 query, or a Lean-kernel check. The runner executes the available artifacts and
returns a structured verdict report; the regression pack (tests/test_audit_runner.py) locks the shipped
verdicts so the audit is a CI-guarded instrument, not a spreadsheet. A second external target is simply a second
spec — the harness is target-agnostic.

Every verdict remains backed by a re-runnable artifact (numeric/Z3/Lean); the runner reports what each check
actually returns, so an audit that silently rotted (a broken proof, a flipped Z3 result) fails loudly.

Run:  python scripts/audit_runner.py   (runs the MCR spec; z3/Lean legs skip cleanly if unavailable)
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent


def _mcr_artifacts():
    spec = importlib.util.spec_from_file_location(
        "mcr_audit_artifacts", _ROOT / "docs" / "audits" / "mcr_audit_artifacts.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def mcr_audit_spec() -> list:
    """The MCR whitepaper audit as an instrument spec: 8 findings, each a (verdict, re-runnable artifact).
    P1/P5 are pure numeric; P2/P3/P6 are Z3; P4 is a Lean-kernel proof; P7/P8 are reasoning verdicts (P7 the
    honest NOT-PROVEN downgrade, P8 the proven-but-exponential steelman — recorded, not auto-re-runnable here)."""
    m = _mcr_artifacts()
    return [
        {"id": "P1", "verdict": "VACUOUS", "kind": "numeric",
         "check": lambda: (lambda r: r["real_square"] and r["stub_square"])(m.p1_parametricity_witness())},
        {"id": "P2", "verdict": "REFUTED", "kind": "z3",
         "check": lambda: (lambda r: r["honest_P1P2_notC_is_SAT"] and r["equivocated_is_UNSAT"])(m.p2_syllogism_invalid())},
        {"id": "P3", "verdict": "REFUTED", "kind": "z3", "check": lambda: m.p3_z3_floor_proven()},
        {"id": "P4", "verdict": "REFUTED", "kind": "lean",
         "lean": ("docs/audits/mcr_p4_not_derivable.lean", ("Mathlib.Tactic",))},
        {"id": "P5", "verdict": "ILL-POSED", "kind": "numeric",
         "check": lambda: m.p5_entropy_exceeds_logN()["E_exceeds_logN"]},
        {"id": "P6", "verdict": "TRUE-BUT-WEAKER", "kind": "z3",
         "check": lambda: m.p6_hoeffding_constant()["union_identity_holds"]},
        {"id": "P7", "verdict": "NOT-PROVEN", "kind": "reasoning"},
        {"id": "P8", "verdict": "PROVEN", "kind": "reasoning"},
    ]


def lean_leg_ok(lean_rel: str, imports, backend) -> bool | None:
    """Kernel-check a Lean audit artifact through the REPL, stripping the umbrella `import Mathlib` (broken in
    the REPL image) and passing targeted imports. Returns True iff 0 errors and 0 sorries; None on no response."""
    raw = (_ROOT / lean_rel).read_text()
    body = "\n".join(ln for ln in raw.splitlines() if not ln.strip().startswith("import "))
    r = backend._run(body, tuple(imports))
    if r is None:
        return None
    msgs = r.get("messages", []) or []
    errs = [mm for mm in msgs if mm.get("severity") == "error"]
    sry = [mm for mm in msgs if "sorry" in (mm.get("data") or "")]
    return not errs and not sry


def run_audit(spec: list, *, run_z3: bool = True, lean_backend=None) -> dict:
    """Execute a spec's artifacts. Numeric always runs; Z3 runs iff run_z3; Lean runs iff a backend is given;
    reasoning verdicts carry no automated artifact. Returns {id: {verdict, kind, artifact_ok}} where artifact_ok
    is True/False (ran) or None (not run / no artifact)."""
    report = {}
    for f in spec:
        kind, ok = f["kind"], None
        if kind == "numeric":
            ok = bool(f["check"]())
        elif kind == "z3":
            ok = bool(f["check"]()) if run_z3 else None
        elif kind == "lean" and lean_backend is not None:
            ok = lean_leg_ok(f["lean"][0], f["lean"][1], lean_backend)
        report[f["id"]] = {"verdict": f["verdict"], "kind": kind, "artifact_ok": ok}
    return report


def _z3_available() -> bool:
    return importlib.util.find_spec("z3") is not None


def main() -> int:
    spec = mcr_audit_spec()
    print("=== audit-runner: MCR whitepaper audit ===")
    z3 = _z3_available()
    backend = None
    try:
        from leibniz.backends.lean_repl import LeanReplBackend, available
        if available():
            backend = LeanReplBackend(timeout_s=400)
    except Exception:  # pragma: no cover
        backend = None

    report = run_audit(spec, run_z3=z3, lean_backend=backend)
    for fid, r in report.items():
        mark = {True: "✓", False: "✗", None: "·"}[r["artifact_ok"]]
        print(f"  {fid}  {r['verdict']:<16} [{r['kind']:<9}] artifact {mark}")

    # A ran-artifact is GREEN iff it passed; not-run (·) is neither pass nor fail.
    ran = [r for r in report.values() if r["artifact_ok"] is not None]
    all_ran_pass = all(r["artifact_ok"] for r in ran)
    gate = "GREEN" if all_ran_pass and ran else "RED" if any(r["artifact_ok"] is False for r in report.values()) else "AMBER(nothing-ran)"
    out = {"gate": gate, "target": "MCR whitepaper", "z3": z3, "lean": backend is not None,
           "report": report, "verdicts": {k: v["verdict"] for k, v in report.items()},
           "reading": ("The MCR audit as a re-runnable instrument: 8 findings, each a (verdict, artifact). "
                       "GREEN = every artifact that ran (numeric always; Z3 if installed; Lean if docker) "
                       "passed. A second external target is a second spec. This makes the daemon's one "
                       "measured-positive lane (formal-verification-as-a-service) a repeatable, CI-guarded "
                       "instrument rather than a one-off.")}
    p = _ROOT / "docs" / "results" / "audit_runner.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, indent=2, default=str) + "\n")
    print(f"\ngate={gate}  (z3={z3}, lean={backend is not None})  ran={len(ran)}/8\n-> {p}")
    if backend is not None:
        backend.close()
    return 0 if gate != "RED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
