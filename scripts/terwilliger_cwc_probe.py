"""Constant-weight Terwilliger — D1 step 4: the discovery reach probe against Brouwer's A(n,d,w) tables.

Operator-local (cvxpy/sdpap for the solves; docker for kernel escalation). Answers ONE question: can the
validated constant-weight three-point producer DISCOVER (tighten a current best-known upper bound on
A(n,d,w)), or only reproduce? The ticket-① protocol applied to the Johnson-scheme build:

  Snapshot. `--build-snapshot <andw.html>` parses a fetched copy of Brouwer's constant-weight table
  (https://aeb.win.tue.nl/codes/Andw.html; cells are `lb` when exact or `lb-ub` with source superscripts)
  into docs/data/brouwer-cwc-snapshot-2026-07.json. The parse is VALIDATED before writing (the Probe-α
  safeguard, via cwc_table_oracle): ground-truth anchors, ub ≥ lb, lb monotone in n, and a cross-check
  against the independently-fetched-and-validated 2026-06-27 lower-bound oracle snapshot — a wrong snapshot
  would poison every targeting decision. The snapshot is TARGETING CONTEXT ONLY — never a decider;
  soundness of any bound stays with the exact-rational LP certificate and the Lean kernel.

  Sweep, cheap-first. OPEN cells (lb < ub) with d ∈ {6,8,10,12} and n ≤ 28 (the Table II range), ordered by
  free-variable count so small cells land first; each cell solved in a SUBPROCESS with a hard wall-clock cap
  (macOS has no `timeout`) on the solver ladder auto(SDPA-GMP tight, eq.58-normalized) → CLARABEL. A float
  is ACCEPTED only when its floor ≥ the snapshot lb (a valid upper bound can't be below a known lower
  bound); failures/caps are recorded honestly — they are the (w,v)-scaling measurement. `--budget` stops
  issuing new cells when the total clock is spent (remaining cells recorded as not_attempted).

  Escalate candidates only. candidate = accepted floor strictly below the snapshot ub. Escalation =
  terwilliger_cwc_cert.certify_lp (exact-rational dual certificate — the DECIDER) then kernel_verify_lp
  (attestation on top; its failure never erases a certification).

Verdict: GREEN(candidate) = ≥1 CERTIFIED exact bound strictly below the snapshot ub — stop and surface to
the operator (independent re-verification of the snapshot value required before any announcement). DRY = 0
certified tightenings — the honest-expected outcome, though this family is LESS mined than the unrestricted
one (post-2005 work concentrated on selected cells: `Po`/`S` superscripts in the table).
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import math
import re
import subprocess
import sys
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
SNAPSHOT = _ROOT / "docs" / "data" / "brouwer-cwc-snapshot-2026-07.json"
OUT = _ROOT / "docs" / "results" / "terwilliger_cwc_probe.json"

SWEEP_D = (6, 8, 10, 12)
SWEEP_N_MAX = 28


def _load(mod, rel):
    spec = importlib.util.spec_from_file_location(mod, _ROOT / rel)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


# ---- snapshot: parse + validate + write -------------------------------------------------------------------

# lb, optional optimum-dot (also seen after the source marker), optional lb source, optional `-ub` where ub
# is a number or `...` (no explicit ub given on the page)
_CELL_RE = re.compile(r"^(\d+)(\.)?(?:\^\{([^}]*)\})?(\.)?(?:-(?:(\d+)(?:\^\{([^}]*)\})?|(\.\.\.)))?$")


def _cell_text(td_html: str) -> str:
    """Normalize one <td>: keep superscripts as ^{...} (adjacent ones merged), strip all other tags,
    collapse whitespace."""
    s = re.sub(r"<sup>(.*?)</sup>", r"^{\1}", td_html, flags=re.S)
    s = re.sub(r"<[^>]+>", "", s)
    s = s.replace("&nbsp;", " ")
    s = re.sub(r"\s+", "", s.strip())
    return s.replace("}^{", " ")


def parse_andw_html(html: str):
    """Parse Brouwer's `Bounds on A(n,d,w)` HTML tables into {(n,d,w): {lb, ub, exact, lb_source,
    ub_source}} with ub=None when the page gives none. Section = heading `Bounds on A(n,d,w)` up to the next
    <h1>; every `n\\w`-headed matrix inside is parsed (other tables skipped). Conventions ON THE PAGE: in the
    d=4 section values are LOWER bounds only, a trailing dot marks an optimum (⇒ lb=ub); in d≥6 sections a
    single number is a settled cell (lb=ub) and `lb-ub` a range, `-...` = no explicit ub. Deterministic;
    unparsable non-empty cells are returned separately (inspected, never silently dropped)."""
    cells: dict = {}
    unparsed: list = []
    heads = list(re.finditer(r"<h1><a name=\"d(\d+)\">Bounds on A\(n,\s*\d+,\s*w\)</a></h1>", html))
    for hi, h in enumerate(heads):
        d = int(h.group(1))
        section = html[h.end(): heads[hi + 1].start() if hi + 1 < len(heads) else len(html)]
        for tm in re.finditer(r"<table.*?</table>", section, flags=re.S):
            rows = re.findall(r"<tr>(.*?)</tr>", tm.group(0), flags=re.S)
            if not rows or "n\\w" not in rows[0]:
                continue                                  # not an A(n,d,w) matrix (e.g. the lost-codes table)
            header_ws = [int(x) for x in re.findall(r"<th[^>]*>(\d+)</th>", rows[0])]
            for row in rows[1:]:
                # The n-label is the row's FIRST cell — Brouwer marks it <th> on most rows but <td> on some
                # (e.g. n=33..35 in the d=18 section); a <th>-only match silently drops those whole rows.
                row_cells = re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", row, flags=re.S)
                if not row_cells or not re.fullmatch(r"\d+", _cell_text(row_cells[0])):
                    continue                                  # header/footer or a row without an integer label
                n = int(_cell_text(row_cells[0]))
                tds = row_cells[1:]
                for w, td in zip(header_ws, tds):
                    txt = _cell_text(td)
                    if not txt:
                        continue
                    m = _CELL_RE.match(txt)
                    if m is None:
                        unparsed.append({"n": n, "d": d, "w": w, "text": txt})
                        continue
                    lb = int(m.group(1))
                    dotted = m.group(2) or m.group(4)
                    ub_num, no_ub = m.group(5), m.group(7)
                    if d == 4:                            # lower bounds only; dot = optimum
                        ub = lb if dotted else (int(ub_num) if ub_num else None)
                    elif ub_num:
                        ub = int(ub_num)
                    elif no_ub:
                        ub = None
                    else:
                        ub = lb                           # single number in a d>=6 matrix = settled cell
                    if (n, d, w) in cells and cells[(n, d, w)]["lb"] != lb:
                        unparsed.append({"n": n, "d": d, "w": w, "text": f"DUPLICATE {txt}"})
                        continue
                    cells[(n, d, w)] = {"lb": lb, "ub": ub, "exact": ub == lb,
                                        "lb_source": m.group(3) or "", "ub_source": m.group(6) or ""}
    return cells, unparsed


def build_snapshot(html_path: Path, fetched_at: str, sha256_page: str):
    """Parse, VALIDATE (refuse a wrong snapshot — the Probe-α safeguard), cross-check against the 2026-06-27
    validated lower-bound oracle, and write docs/data/brouwer-cwc-snapshot-2026-07.json."""
    import hashlib
    oracle = _load("cwc_table_oracle", "scripts/cwc_table_oracle.py")
    tcs_tab = _load("terwilliger_cwc_sdp", "scripts/terwilliger_cwc_sdp.py")  # TABLE_II for the ub cross-check
    raw = html_path.read_bytes()
    real_sha = hashlib.sha256(raw).hexdigest()                            # provenance from the bytes, not a flag
    if sha256_page and sha256_page != real_sha:
        raise ValueError(f"--sha256 {sha256_page[:12]}… disagrees with the file's {real_sha[:12]}…")
    html = raw.decode(errors="replace")
    cells, unparsed = parse_andw_html(html)
    problems = []
    for key, expected in oracle.GROUND_TRUTH.items():                     # anchors (exact d=4 cells)
        got = cells.get(key)
        if got is None or got["lb"] != expected:
            problems.append(f"anchor A{key}: lb={got and got['lb']} != {expected}")
    for (n, d, w), c in cells.items():
        if c["ub"] is not None and c["ub"] < c["lb"]:
            problems.append(f"ub<lb at A({n},{d},{w}): {c['ub']}<{c['lb']}")
        prev = cells.get((n - 1, d, w))
        if prev is not None and c["lb"] < prev["lb"]:
            problems.append(f"lb monotonicity A({n},{d},{w})={c['lb']} < A({n-1},{d},{w})={prev['lb']}")
    # ub cross-check (independent of lb): the current best-known ub can only be <= Schrijver 2005's Table II
    # bound, never above it — the ONLY validator that touches the ub side, which drives all targeting.
    ub_bad = [(n, d, w, cells[(n, d, w)]["ub"], tab) for (n, d, w), tab in tcs_tab.TABLE_II.items()
              if (n, d, w) in cells and cells[(n, d, w)]["ub"] is not None and cells[(n, d, w)]["ub"] > tab]
    if ub_bad:
        problems.append(f"ub > Schrijver Table II at {len(ub_bad)} cells (e.g. {ub_bad[:3]})")
    old_snap, old_prov = oracle.load_snapshot()                           # cross-check vs the June oracle
    shared = [k for k in old_snap if k in cells]
    diffs = [{"cell": list(k), "old_lb": old_snap[k], "new_lb": cells[k]["lb"]}
             for k in shared if old_snap[k] != cells[k]["lb"]]
    if not shared or len(diffs) > 0.01 * len(shared):
        problems.append(f"cross-check: {len(diffs)}/{len(shared)} lb disagreements vs the validated "
                        f"2026-06-27 oracle snapshot (>1%)")
    # omission gate: any old-oracle cell whose d-section we parsed MUST survive the new parse (a silently
    # dropped row — e.g. a <td>-labeled one — would otherwise vanish with no trace and no failing gate).
    parsed_ds = {d for (_n, d, _w) in cells}
    dropped = [k for k in old_snap if k[1] in parsed_ds and k not in cells]
    if dropped:
        problems.append(f"{len(dropped)} old-oracle cells vanished from the new parse (e.g. {dropped[:5]})")
    if len(unparsed) > 10:
        problems.append(f"{len(unparsed)} unparsable cells: {unparsed[:3]}")
    if problems:
        raise ValueError(f"refusing to write an invalid cwc snapshot: {problems[:6]}")
    meta = {"source_name": "Andries Brouwer — Bounds for binary constant weight codes A(n,d,w)",
            "source_url": "https://aeb.win.tue.nl/codes/Andw.html",
            "fetched_at": fetched_at, "sha256_page": real_sha,
            "parser": "scripts/terwilliger_cwc_probe.py --build-snapshot",
            "cells": len(cells), "unparsed_cells": unparsed,
            "cross_check": {"against": str(oracle.SNAPSHOT.relative_to(_ROOT)),
                            "fetched_at_old": old_prov.get("fetched_at"),
                            "shared_cells": len(shared), "lb_diffs": diffs},
            "trust_note": ("Targeting context ONLY — never a decider. Soundness of any bound claim stays "
                           "with the exact-rational LP certificate and the Lean kernel.")}
    out = {"_meta": meta,
           "cells": {f"{n},{d},{w}": c for (n, d, w), c in sorted(cells.items())}}
    SNAPSHOT.parent.mkdir(parents=True, exist_ok=True)
    SNAPSHOT.write_text(json.dumps(out, indent=1) + "\n")
    return meta


# ---- sweep -------------------------------------------------------------------------------------------------

def load_snapshot():
    return json.loads(SNAPSHOT.read_text())


def sweep_cells(snap_cells):
    """OPEN cells (lb < ub) in the sweep scope, ordered cheap-first by free-variable count."""
    tc = _load("terwilliger_cwc_beta", "scripts/terwilliger_cwc_beta.py")
    out = []
    for key, c in snap_cells.items():
        n, d, w = (int(x) for x in key.split(","))
        if d not in SWEEP_D or n > SWEEP_N_MAX or c["ub"] is None or c["lb"] >= c["ub"]:
            continue
        out.append((len(tc.free_keys(w, n - w, d)), n, d, w))
    out.sort()
    return [(n, d, w, nv) for (nv, n, d, w) in out]


def solve_cell(n, d, w, lb=None):
    """Single-cell float solve (inside the capped subprocess). Emits a JSON line after EVERY attempt so the
    parent keeps completed attempts when the cap fires mid-ladder. Ladder: auto (SDPA-GMP tight, normalized,
    when installed) → CLARABEL raw. Accepted only when floor ≥ lb; a valid solver optimum that floors BELOW
    lb is recorded as a soundness alarm (a wrong transcription can under-bound), not folded into a generic
    solver-failure status."""
    tcs = _load("terwilliger_cwc_sdp", "scripts/terwilliger_cwc_sdp.py")
    row = {"stage": "full", "n": n, "d": d, "w": w, "attempts": [],
           "status": "ladder_in_progress", "sdp_value": None, "sdp_value_raw": None,
           "sdp_floor": None, "below_lb_floor": None}
    for solver in (None, "CLARABEL"):
        t0 = time.time()
        try:
            r = tcs.solve_primal(n, d, w, solver=solver)
            val, status, used = r["value"], r["status"], r["solver"]
        except Exception as e:  # noqa: BLE001 -- a solver crash is a data point, not a probe failure
            # resolve the solver name so the dedup break below fires (a bare "auto" defeats it and re-runs
            # the same crashing CLARABEL when sdpap is absent).
            resolved = tcs.ts._solver_defaults(solver, None, None)[0]
            val, status, used = None, f"solver_error: {type(e).__name__}", resolved
        if val is not None and not math.isfinite(val):
            val, status = None, f"{status} (non-finite value)"
        att = {"solver": used, "status": status,
               "value": None if val is None else round(val, 4),
               "floor": None if val is None else int(val + 1e-6),
               "secs": round(time.time() - t0, 1)}
        row["attempts"].append(att)
        # a genuine (optimal) solver optimum strictly below the known lb is a formulation red flag — retain it
        if (att["floor"] is not None and lb is not None and att["floor"] < lb
                and str(status).startswith("optimal")):
            row["below_lb_floor"] = att["floor"]
        accepted = att["floor"] is not None and (lb is None or att["floor"] >= lb)
        if accepted:
            row.update({"solver": att["solver"], "status": att["status"], "sdp_value": att["value"],
                        "sdp_value_raw": val, "sdp_floor": att["floor"], "solve_secs": att["secs"]})
        print(json.dumps(row), flush=True)
        if accepted:
            break
        if solver is None and row["attempts"][-1]["solver"] == "CLARABEL":
            break                                        # auto already was CLARABEL; no second rung
    if row["sdp_floor"] is None:
        row["status"] = (f"floored_below_known_lb ({row['below_lb_floor']} < {lb}) — SOUNDNESS ALARM"
                         if row["below_lb_floor"] is not None
                         else "no_valid_float (solvers crashed or floored below the known lb)")
    row["stage"] = "cell"
    print(json.dumps(row), flush=True)


def run_cell_capped(n, d, w, cap_s, lb=None):
    """Run solve_cell in a subprocess with a hard wall-clock cap; return the best row it emitted."""
    cmd = [sys.executable, str(Path(__file__).resolve()), "--cell", str(n), str(d), str(w)]
    if lb is not None:
        cmd += ["--lb", str(lb)]
    t0 = time.time()
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=cap_s)
        out, timed_out, rc, stderr = p.stdout, False, p.returncode, p.stderr or ""
    except subprocess.TimeoutExpired as e:
        out = (e.stdout or b"").decode() if isinstance(e.stdout, bytes) else (e.stdout or "")
        err = e.stderr or ""
        timed_out, rc, stderr = True, None, (err.decode() if isinstance(err, bytes) else err)
    rows = []
    for line in out.splitlines():
        try:
            rows.append(json.loads(line))
        except ValueError:
            continue
    row = next((r for r in reversed(rows) if r.get("stage") == "cell"),
               next((r for r in reversed(rows) if r.get("stage") == "full"), None))
    if row is None:
        row = {"n": n, "d": d, "w": w,
               "status": "time_cap" if timed_out else
               f"error: no output (rc={rc}; tail: {stderr[-200:].strip()})"}
    elif timed_out and row.get("status") == "ladder_in_progress":
        row["status"] = "time_cap (mid-ladder; completed attempts retained)"
    elif not timed_out and rc != 0:
        # a child that emitted a row and THEN died (segfault/OOM, rc!=0) — surface the crash instead of
        # leaving a stale 'ladder_in_progress'/partial status that reads like a clean interrupted run.
        row["status"] = f"child_crashed (rc={rc}); prior: {row.get('status')}"
        if stderr.strip():
            row["stderr_tail"] = stderr[-200:].strip()
    row.pop("stage", None)
    row["cell_secs"] = round(time.time() - t0, 1)
    return row


def classify_row(row, snap_cells, table_ii):
    """Attach snapshot context + the candidate verdict (pure; test-covered). above_known_lb means only
    'not refuted by the known lower bound' — never a validity claim."""
    n, d, w = row["n"], row["d"], row["w"]
    cell = snap_cells.get(f"{n},{d},{w}")
    floor = row.get("sdp_floor")
    row["snapshot"] = cell and {"lb": cell["lb"], "ub": cell["ub"], "ub_source": cell["ub_source"]}
    if cell is None or floor is None:
        row["candidate"] = False
        # a solver OPTIMUM below the known lb is a formulation red flag (a wrong transcription can under-
        # bound), not mere solver weakness — mark it so the sweep's soundness tripwire can fire.
        if cell is not None and row.get("below_lb_floor") is not None:
            row["above_known_lb"] = False
        return row
    row["margin_vs_ub"] = floor - cell["ub"]
    row["above_known_lb"] = floor >= cell["lb"]
    # candidacy is targeting-only: be optimistic at the ub boundary. A true optimum a hair below an integer
    # ub floors UP under the +1e-6 acceptance bump, so also test the raw-value floor; escalation is cheap and
    # the exact leg is the decider, so a spurious candidate costs one solve while a missed one costs a record.
    raw = row.get("sdp_value_raw")
    opt_floor = math.floor(raw) if isinstance(raw, (int, float)) and not isinstance(raw, bool) else floor
    row["candidate"] = bool(row["above_known_lb"] and (floor < cell["ub"] or opt_floor < cell["ub"]))
    if (n, d, w) in table_ii:
        row["table_II"] = table_ii[(n, d, w)]
        row["reproduces_table_II"] = floor == table_ii[(n, d, w)]
    return row


def escalate(n, d, w, target, lb=None, kernel_timeout_s=900):
    """Candidates only: the exact-rational LP certificate (the DECIDER) against the discovery threshold
    `target` (= known ub − 1, the smallest strict tightening — NOT the loose float floor, which would report a
    certifiable record as DRY), then the kernel leg on THAT certificate's blocks. `lb` arms the soundness
    tripwire (a certified bound below the known lb is a transcription alarm, never a discovery). `decided`
    distinguishes a genuine exact refusal from a decider that time-capped/errored on a live candidate."""
    tcc = _load("terwilliger_cwc_cert", "scripts/terwilliger_cwc_cert.py")
    precisions = (10 ** 10, 10 ** 12, 10 ** 14)
    row = {"n": n, "d": d, "w": w, "target": target}
    cert_row = tcc.certify_lp(n, d, w, target=target, lb=lb, precisions=precisions, return_duals=True)
    row["exact_lp"] = {k: v for k, v in cert_row.items() if k != "duals"}
    row["certified"] = bool(cert_row.get("certified"))
    row["decided"] = "certified" in cert_row            # False => time-capped / no exact cert, not a refusal
    if cert_row.get("soundness_alarm"):
        row["soundness_alarm"] = cert_row["soundness_alarm"]
    if row["certified"]:
        try:                                             # attest EXACTLY the certified certificate (cert_row)
            row["kernel"] = tcc.kernel_verify_lp(n, d, w, target=target, lb=lb, cert_row=cert_row,
                                                 timeout_s=kernel_timeout_s, precisions=precisions).get("kernel")
        except Exception as e:  # noqa: BLE001 -- attestation failure is a data point
            row["kernel"] = f"error: {type(e).__name__}: {e}"
    return row


def verdict_of(candidates, escalations, no_escalate=False, soundness_alarms=None):
    if soundness_alarms:
        return "SOUNDNESS-ALARM(a solved bound floored below a known lower bound — transcription suspect)"
    if any(e.get("certified") for e in escalations):
        return "GREEN(candidate)"
    if candidates and no_escalate:
        return "UNESCALATED(candidates pending the exact-LP decider)"
    if candidates and any(not e.get("decided", True) for e in escalations):
        return "UNDECIDED(escalation incomplete — the exact-LP decider time-capped or errored on a candidate)"
    return "DRY"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--build-snapshot", type=Path, metavar="ANDW_HTML",
                    help="parse+validate+write the snapshot from a fetched copy of Brouwer's Andw.html")
    ap.add_argument("--fetched-at", default=None,
                    help="fetch date recorded in provenance (default: today — never a stale hardcoded date)")
    ap.add_argument("--sha256", default="",
                    help="optional expected sha256 of the page; build_snapshot computes the real one and "
                         "REFUSES to write if this disagrees")
    ap.add_argument("--cell", nargs=3, type=int, metavar=("N", "D", "W"), help="single-cell mode (internal)")
    ap.add_argument("--lb", type=int, default=None, help="known lower bound (acceptance gate)")
    ap.add_argument("--cap", type=float, default=120.0, help="per-cell wall-clock cap, seconds")
    ap.add_argument("--budget", type=float, default=5400.0, help="total sweep budget, seconds")
    ap.add_argument("--no-escalate", action="store_true", help="sweep only; skip exact-LP/kernel escalation")
    args = ap.parse_args(argv)

    if args.build_snapshot:
        import datetime
        fetched_at = args.fetched_at or datetime.date.today().isoformat()
        meta = build_snapshot(args.build_snapshot, fetched_at, args.sha256)
        print(f"[cwc-probe] snapshot written: {meta['cells']} cells, "
              f"{len(meta['cross_check']['lb_diffs'])} lb diffs vs June oracle "
              f"({meta['cross_check']['shared_cells']} shared) -> {SNAPSHOT}")
        return 0

    if args.cell:
        solve_cell(*args.cell, lb=args.lb)
        return 0

    tcs = _load("terwilliger_cwc_sdp", "scripts/terwilliger_cwc_sdp.py")
    snap = load_snapshot()
    snap_cells = snap["cells"]
    todo = sweep_cells(snap_cells)
    rows, escalations, skipped = [], [], []

    def not_yet_attempted():
        """Cells never run: budget-skipped OR (on an external kill) the untouched tail of `todo`."""
        return skipped or [{"n": n2, "d": d2, "w": w2, "n_vars": nv2}
                           for (n2, d2, w2, nv2) in todo[len(rows):]]

    def soundness_alarms():
        return [{"n": r["n"], "d": r["d"], "w": r["w"], "below_lb_floor": r.get("below_lb_floor"),
                 "lb": (r.get("snapshot") or {}).get("lb")}
                for r in rows if r.get("above_known_lb") is False]

    def table_ii_regressions():
        # a Table II cell whose floor exceeds Schrijver's published bound for the SAME relaxation is a
        # faithfulness signal across the un-gated Table II range (the step-2 gate covered only 3 cells). The
        # `status` disambiguates: an `optimal_inaccurate` overshoot is float non-convergence (targeting noise,
        # the exact leg decides), whereas a CLEAN-`optimal` floor above the published bound would be a real
        # transcription regression (a weaker relaxation) — `clean_optimal` flags exactly those.
        return [{"n": r["n"], "d": r["d"], "w": r["w"], "floor": r["sdp_floor"], "table_II": r["table_II"],
                 "status": r.get("status"), "clean_optimal": r.get("status") == "optimal"}
                for r in rows if r.get("reproduces_table_II") is False
                and r.get("sdp_floor") is not None and r.get("table_II") is not None
                and r["sdp_floor"] > r["table_II"]]

    def flush(verdict="RUNNING"):
        res = {"verdict": verdict, "per_cell_cap_s": args.cap, "budget_s": args.budget,
               "snapshot": {"file": str(SNAPSHOT.relative_to(_ROOT)),
                            "meta": {k: v for k, v in snap["_meta"].items() if k != "unparsed_cells"}},
               "sweep": {"scope": f"open cells, d in {SWEEP_D}, n <= {SWEEP_N_MAX}, cheap-first",
                         "n_cells": len(todo), "not_attempted": not_yet_attempted()},
               "soundness_alarms": soundness_alarms(), "table_II_regressions": table_ii_regressions(),
               "rows": rows, "escalations": escalations,
               "reading": ("D1 step 4 constant-weight reach probe. candidate = float floor (optimistically, at "
                           "the ub boundary) strictly below the Brouwer-snapshot ub and >= its lb; counts as a "
                           "discovery ONLY once the exact-rational LP certifies a bound < ub (escalations[]). "
                           "GREEN(candidate) -> surface to operator (independent snapshot re-verification "
                           "before any announcement). DRY = 0 certified tightenings. SOUNDNESS-ALARM = a solved "
                           "optimum floored below a known lower bound (transcription suspect). UNDECIDED = a "
                           "candidate whose exact-LP decider time-capped/errored. Time-caps/solver failures "
                           "are the honest scaling measurement. The snapshot is targeting context only, never "
                           "a decider.")}
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(res, indent=2) + "\n")
        return res

    t0 = time.time()
    for ci, (n, d, w, nv) in enumerate(todo):
        if time.time() - t0 > args.budget:
            skipped = [{"n": n2, "d": d2, "w": w2, "n_vars": nv2} for (n2, d2, w2, nv2) in todo[ci:]]
            print(f"  budget spent: {len(skipped)} cells not attempted", flush=True)
            break
        cell = snap_cells[f"{n},{d},{w}"]
        row = run_cell_capped(n, d, w, args.cap, lb=cell["lb"])
        row["n_vars"] = nv
        row = classify_row(row, snap_cells, tcs.TABLE_II)
        rows.append(row)
        flush()
        s = row.get("snapshot") or {}
        print(f"  A({n},{d},{w}): status={row.get('status')} floor={row.get('sdp_floor')} "
              f"lb={s.get('lb')} ub={s.get('ub')}{s.get('ub_source') and '^' + s['ub_source'] or ''} "
              f"candidate={row['candidate']} vars={nv} secs={row.get('cell_secs')}", flush=True)

    candidates = [r for r in rows if r.get("candidate")]
    if candidates and not args.no_escalate:
        for r in candidates:
            cell = snap_cells[f"{r['n']},{r['d']},{r['w']}"]
            threshold = cell["ub"] - 1                    # the smallest strict tightening below the known ub
            print(f"  escalating candidate A({r['n']},{r['d']},{r['w']}) target<={threshold} "
                  f"(ub {cell['ub']}) ...", flush=True)
            try:
                escalations.append(escalate(r["n"], r["d"], r["w"], threshold, lb=cell["lb"]))
            except Exception as e:  # noqa: BLE001 -- record, keep going
                escalations.append({"n": r["n"], "d": r["d"], "w": r["w"], "target": threshold,
                                    "certified": False, "decided": False, "error": f"{type(e).__name__}: {e}"})
            flush()

    res = flush(verdict_of(candidates, escalations, args.no_escalate, soundness_alarms()))
    certified = [e for e in escalations if e.get("certified")]
    solved = [r for r in rows if r.get("sdp_floor") is not None]
    regs = table_ii_regressions()
    clean_regs = [r for r in regs if r["clean_optimal"]]
    print(f"terwilliger cwc reach probe: {res['verdict']} — {len(solved)}/{len(rows)} attempted cells "
          f"solved ({len(todo)} in scope), {len(candidates)} candidate(s), {len(certified)} certified, "
          f"{len(soundness_alarms())} below-lb alarm(s), {len(regs)} Table II regression(s) "
          f"({len(clean_regs)} at clean 'optimal' — float non-convergence excluded)")
    print(f"  -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
