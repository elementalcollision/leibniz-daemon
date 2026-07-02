"""Terwilliger three-point — task #99: the beyond-Table-I discovery reach probe.

Operator-local: cvxpy for the solve legs; docker for the kernel leg of any escalation. Answers ONE question:
can the validated three-point producer DISCOVER (tighten a current best-known upper bound), or only
reproduce? Sweeps n = 20..30, d ∈ {6, 8, 10, 12} (even d only — the machinery is validated for even d)
against a checked-in snapshot of Brouwer's table (docs/data/brouwer-snapshot-2026-07.json). The snapshot is
TARGETING CONTEXT ONLY — never a decider; soundness of any bound stays with the exact-rational LP certificate
and the Lean kernel. Brouwer's table ends at n=28, so n=29,30 cells have no snapshot target and contribute
n-scaling data only; their acceptance gate uses the monotonicity-derived lower bound A(n,d) >= A(28,d) so
under-converged floats can't masquerade as measurements there.

Cheap-first design:
  1. Float solve per cell (full SDP + the k=0 Delsarte-LP diagnostic), each cell in a SUBPROCESS with a hard
     wall-clock cap (macOS has no `timeout`; the cap is subprocess.run(timeout=)). Solver ladder CLARABEL ->
     SCS; an attempt is accepted only when its floor >= the known lower bound. Solver failures/time-caps are
     recorded honestly (per-attempt, emitted after every attempt so a mid-ladder cap keeps completed
     attempts) — they ARE the n-scaling measurement.
  2. candidate = sdp_floor strictly below the snapshot ub AND >= the snapshot lb. A floor below the lb is a
     solver artifact (INVALID), never a discovery.
  3. Escalation (candidates only): certify_lp(n, d, target=floor) exact-rational certificate, then
     kernel_verify_lp. A candidate COUNTS only with a certified exact bound; the kernel leg is attestation
     on top and its failure never erases the exact-LP decision.

Verdict: GREEN(candidate) = >=1 CERTIFIED exact bound strictly below the snapshot ub — stop and surface to the
operator (needs independent re-verification of the snapshot value before any announcement). DRY = 0 certified
tightenings (any float candidates were escalated and not certified) — the expected outcome (post-2005
literature applied stronger SDPs to these cells). UNESCALATED = candidates found under --no-escalate.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import math
import subprocess
import sys
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
SNAPSHOT = _ROOT / "docs" / "data" / "brouwer-snapshot-2026-07.json"
OUT = _ROOT / "docs" / "results" / "terwilliger_reach_probe.json"

SWEEP_N = range(20, 31)
SWEEP_D = (6, 8, 10, 12)
SOLVERS = ("CLARABEL", "SCS")


def _load(mod, rel):
    spec = importlib.util.spec_from_file_location(mod, _ROOT / rel)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def load_snapshot():
    return json.loads(SNAPSHOT.read_text())


def lb_for_cell(n, d, snap_cells):
    """(lb, note) acceptance gate for a cell: the snapshot lb; beyond the table (n>28) the monotonicity
    bound A(n,d) >= A(28,d) — without it, under-converged floats would masquerade as measurements there."""
    cell = snap_cells.get(f"{n},{d}")
    if cell is not None:
        return cell["lb"], None
    base = snap_cells.get(f"28,{d}")
    if base is None:
        return None, None
    return base["lb"], f"monotonicity: A({n},{d}) >= A(28,{d}) >= {base['lb']}"


def classify_row(row, snap_cells, table_i):
    """Attach snapshot context + the candidate verdict to a solved cell row (pure; test-covered).
    above_known_lb means only 'not refuted by the known lower bound' — it is never a validity claim."""
    n, d = row["n"], row["d"]
    cell = snap_cells.get(f"{n},{d}")
    floor = row.get("sdp_floor")
    if cell is None:
        row["snapshot"] = None                     # beyond Brouwer's table (n>28): scaling data only
        row["candidate"] = False
        return row
    row["snapshot"] = {"lb": cell["lb"], "ub": cell["ub"], "ub_source": cell["ub_source"]}
    if floor is None:
        row["candidate"] = False
        return row
    row["margin_vs_ub"] = floor - cell["ub"]
    # SOUNDNESS: a valid upper bound never floors below a known lower bound on A(n,d).
    row["above_known_lb"] = floor >= cell["lb"]
    row["candidate"] = bool(row["above_known_lb"] and floor < cell["ub"])
    if (n, d) in table_i:
        row["table_I"] = table_i[(n, d)]
        row["reproduces_table_I"] = floor == table_i[(n, d)]
    return row


def solve_cell(n, d, lb=None):
    """Single-cell float solve (runs inside the capped subprocess). Emits a JSON line after EVERY solver
    attempt so the parent keeps completed attempts even when the cap fires mid-ladder. Solver ladder:
    CLARABEL, then SCS — a fallback fires when a solver crashes, returns a non-finite value (cvxpy reports
    infeasible/unbounded as +/-inf, not None), OR its floor lands below the known lower bound lb (a valid
    upper bound can't; at d>=10 both solvers routinely return 'optimal' values far below lb — the
    conditioning wall, measured, not hidden). A cell is ACCEPTED only with floor >= lb; otherwise sdp_floor
    stays None and the attempts stand as the honest record."""
    ts = _load("terwilliger_sdp", "scripts/terwilliger_sdp.py")
    row = {"stage": "full", "n": n, "d": d, "attempts": [],
           "status": "ladder_in_progress", "sdp_value": None, "sdp_floor": None}
    accepted = None
    for solver in SOLVERS:
        t0 = time.time()
        try:
            r = ts.solve_primal(n, d, solver=solver)
            val, status = r["value"], r["status"]
        except Exception as e:  # noqa: BLE001 -- a solver crash is a data point, not a probe failure
            val, status = None, f"solver_error: {type(e).__name__}"
        if val is not None and not math.isfinite(val):
            val, status = None, f"{status} (non-finite value)"
        att = {"solver": solver, "status": status,
               "value": None if val is None else round(val, 4),
               "floor": None if val is None else int(val + 1e-6),
               "secs": round(time.time() - t0, 1)}
        row["attempts"].append(att)
        if att["floor"] is not None and (lb is None or att["floor"] >= lb):
            accepted = att
            row.update({"solver": accepted["solver"], "status": accepted["status"],
                        "sdp_value": accepted["value"], "sdp_floor": accepted["floor"],
                        "solve_secs": accepted["secs"]})
        print(json.dumps(row), flush=True)
        if accepted:
            break
    if not accepted:
        row["status"] = "no_valid_float (all solvers crashed or floored below the known lb)"
        print(json.dumps(row), flush=True)
    else:
        try:
            t1 = time.time()
            lp = ts.solve_primal(n, d, k_max=0, solver=accepted["solver"])
            lpv = lp["value"]
            row["delsarte_lp_value"] = None if lpv is None or not math.isfinite(lpv) else round(lpv, 4)
            row["lp_secs"] = round(time.time() - t1, 1)
        except Exception as e:  # noqa: BLE001 -- the diagnostic leg must not sink the cell
            row["delsarte_lp_value"] = f"error: {type(e).__name__}"
    row["stage"] = "cell"
    print(json.dumps(row), flush=True)


def run_cell_capped(n, d, cap_s, lb=None):
    """Run solve_cell in a subprocess with a hard wall-clock cap; return the best row it managed to emit."""
    cmd = [sys.executable, str(Path(__file__).resolve()), "--cell", str(n), str(d)]
    if lb is not None:
        cmd += ["--lb", str(lb)]
    t0 = time.time()
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=cap_s)
        out, timed_out = p.stdout, False
    except subprocess.TimeoutExpired as e:
        out = (e.stdout or b"").decode() if isinstance(e.stdout, bytes) else (e.stdout or "")
        timed_out = True
    rows = []
    for line in out.splitlines():
        try:
            rows.append(json.loads(line))
        except ValueError:
            continue
    row = next((r for r in reversed(rows) if r.get("stage") == "cell"),
               next((r for r in reversed(rows) if r.get("stage") == "full"), None))
    if row is None:
        if timed_out:
            row = {"n": n, "d": d, "status": "time_cap"}
        else:
            tail = " | ".join(t for t in ((out[-200:].strip() if out else ""),
                                          (p.stderr[-300:].strip() if p.stderr else "")) if t)
            row = {"n": n, "d": d, "status": f"error: no output (rc={p.returncode}; output tail: {tail})"}
    elif timed_out:
        if row.get("status") == "ladder_in_progress":
            row["status"] = "time_cap (mid-solver-ladder; completed attempts retained)"
        elif row.get("stage") == "full":
            row["status"] = f"{row['status']} (k=0 diagnostic hit the cell time cap)"
    row.pop("stage", None)
    row["cell_secs"] = round(time.time() - t0, 1)
    return row


def escalate(n, d, target, kernel_timeout_s=900):
    """Candidates only: exact-rational LP certificate at the float floor, then the kernel leg. The exact LP
    is the DECIDER and its verdict is recorded first; kernel attestation is on top, and a kernel-leg failure
    is recorded but never erases a certification (it must not flip a GREEN run to DRY)."""
    lp = _load("terwilliger_exact_lp", "scripts/terwilliger_exact_lp.py")
    row = {"n": n, "d": d, "target": target}
    cert_row = lp.certify_lp(n, d, target=target)
    row["exact_lp"] = {k: v for k, v in cert_row.items() if k != "duals"}
    row["certified"] = bool(cert_row.get("certified"))
    if row["certified"]:
        try:
            row["kernel"] = lp.kernel_verify_lp(n, d, target=target, timeout_s=kernel_timeout_s).get("kernel")
        except Exception as e:  # noqa: BLE001 -- attestation failure is a data point, not a de-certification
            row["kernel"] = f"error: {type(e).__name__}: {e}"
    return row


def verdict_of(candidates, escalations, no_escalate=False):
    """GREEN(candidate) = >=1 certified tightening. UNESCALATED = candidates exist but the exact-LP decider
    was skipped (--no-escalate) — NOT dry, undecided. DRY = 0 certified (any candidates were refused)."""
    if any(e.get("certified") for e in escalations):
        return "GREEN(candidate)"
    if candidates and no_escalate:
        return "UNESCALATED(candidates pending the exact-LP decider)"
    return "DRY"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--cell", nargs=2, type=int, metavar=("N", "D"), help="single-cell mode (internal)")
    ap.add_argument("--lb", type=int, default=None, help="known lower bound for the cell (acceptance gate)")
    ap.add_argument("--cap", type=float, default=120.0, help="per-cell wall-clock cap, seconds")
    ap.add_argument("--no-escalate", action="store_true", help="sweep only; skip exact-LP/kernel escalation")
    args = ap.parse_args(argv)

    if args.cell:
        solve_cell(*args.cell, lb=args.lb)
        return 0

    ts = _load("terwilliger_sdp", "scripts/terwilliger_sdp.py")
    snap = load_snapshot()
    snap_cells = snap["cells"]
    rows, escalations = [], []

    def flush(verdict="RUNNING"):
        res = {"verdict": verdict, "per_cell_cap_s": args.cap,
               "snapshot": {"file": str(SNAPSHOT.relative_to(_ROOT)), "meta": snap["_meta"]},
               "rows": rows, "escalations": escalations,
               "reading": ("Task #99 discovery reach probe. candidate = float floor strictly below the Brouwer-"
                           "snapshot ub and >= its lb; counts ONLY once the exact-rational LP certifies it "
                           "(escalations[]). above_known_lb means 'not refuted by the known lower bound', "
                           "never a validity claim — floats are targeting data. GREEN(candidate) = >=1 "
                           "certified strictly-below-ub bound -> surface to operator (independent snapshot "
                           "re-verification required before any announcement). DRY = 0 certified tightenings "
                           "(any float candidates were escalated and not certified) — the expected outcome: "
                           "post-2005 quadruple/stronger SDPs already tightened most cells. UNESCALATED = "
                           "candidates found under --no-escalate. Time-caps/solver failures are the honest "
                           "n-scaling measurement, not noise. The snapshot is targeting context only, never "
                           "a decider.")}
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(res, indent=2) + "\n")
        return res

    for n in SWEEP_N:
        for d in SWEEP_D:
            lb, lb_note = lb_for_cell(n, d, snap_cells)
            row = run_cell_capped(n, d, args.cap, lb=lb)
            row = classify_row(row, snap_cells, ts.TABLE_I)
            if lb_note is not None:
                row["derived_lb"] = {"lb": lb, "source": lb_note}
            rows.append(row)
            flush()
            s = row.get("snapshot") or {}
            print(f"  A({n},{d}): status={row.get('status')} solver={row.get('solver')} "
                  f"floor={row.get('sdp_floor')} ub={s.get('ub')} lb={s.get('lb')} "
                  f"candidate={row['candidate']} secs={row.get('cell_secs')}", flush=True)

    candidates = [r for r in rows if r.get("candidate")]
    if candidates and not args.no_escalate:
        for r in candidates:
            print(f"  escalating candidate A({r['n']},{r['d']}) target={r['sdp_floor']} ...", flush=True)
            try:
                escalations.append(escalate(r["n"], r["d"], r["sdp_floor"]))
            except Exception as e:  # noqa: BLE001 -- record, keep going
                escalations.append({"n": r["n"], "d": r["d"], "target": r["sdp_floor"],
                                    "certified": False, "error": f"{type(e).__name__}: {e}"})
            flush()

    res = flush(verdict_of(candidates, escalations, args.no_escalate))
    certified = [e for e in escalations if e.get("certified")]
    solved = [r for r in rows if r.get("sdp_floor") is not None]
    invalid = [r for r in rows if r.get("above_known_lb") is False]
    print(f"terwilliger reach probe: {res['verdict']} — {len(solved)}/{len(rows)} cells solved, "
          f"{len(candidates)} candidate(s), {len(certified)} certified, {len(invalid)} invalid floor(s)")
    print(f"  -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
