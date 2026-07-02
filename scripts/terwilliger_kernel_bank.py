"""Terwilliger kernel bank: kernel-attest the two new D6 exact certificates.

PR #231 (solve-leg fix) produced two new exact-rational certificates through certify_lp — A(23,6) <= 13766
and the first d>=10 certificate A(25,10) <= 503 (both dual_check-validated at P=1e14) — but their kernel
legs never ran. This script runs them: for each cell, re-derive the exact certificate and hand its PSD
blocks to the real Lean 4.31 kernel via kernel_verify_lp (per-block theorems; the corrupted-block control
must be rejected). GREEN = both cells sound (valid True, corrupted False), which puts them at the same
kernel-attested tier as A(19,6).

Needs cvxpy + sdpap (solve) + docker (Lean); operator-local, CI skips (find_spec-gated import in the test).
"""
from __future__ import annotations

import importlib.util
import json
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
OUT = _ROOT / "docs" / "results" / "terwilliger_kernel_bank.json"

# (n, d, target, precisions): the D6-measured settings — these cells certify only at P=1e14.
CELLS = [(23, 6, 13766, (10 ** 14,)), (25, 10, 503, (10 ** 14,))]


def _load(mod, rel):
    spec = importlib.util.spec_from_file_location(mod, _ROOT / rel)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def main() -> int:
    tel = _load("terwilliger_exact_lp", "scripts/terwilliger_exact_lp.py")
    rows = []
    for (n, d, target, precs) in CELLS:
        t0 = time.time()
        try:
            r = tel.kernel_verify_lp(n, d, target=target, timeout_s=1800, precisions=precs, time_cap_s=2400)
        except Exception as e:  # noqa: BLE001 -- record, keep going
            r = {"n": n, "d": d, "target": target, "error": f"{type(e).__name__}: {e}"}
        r["total_secs"] = round(time.time() - t0, 1)
        rows.append(r)
    sound = [r for r in rows if isinstance(r.get("kernel"), dict) and r["kernel"].get("sound")]
    verdict = "GREEN" if len(sound) == len(rows) else "AMBER"
    res = {"verdict": verdict, "sound": f"{len(sound)}/{len(rows)}", "rows": rows,
           "reading": ("Kernel attestation of the two new D6 exact certificates (PR #231): the real Lean 4.31 "
                       "kernel verifies every PSD block of each certificate and rejects the corrupted-block "
                       "control. GREEN = A(23,6) <= 13766 and A(25,10) <= 503 (the FIRST d>=10 certificate) "
                       "are kernel-attested at the same audit tier as A(19,6) <= 1280. Soundness stays with "
                       "certify_lp (exact rational) + the kernel; floats were only ever targeting data.")}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(res, indent=2) + "\n")
    print(f"terwilliger kernel bank: {verdict} ({len(sound)}/{len(rows)} sound)")
    for r in rows:
        print(f"  A({r['n']},{r['d']}): target={r.get('target')} bound={r.get('exact_bound')} "
              f"kernel={r.get('kernel')} secs={r.get('total_secs')}")
    print(f"  -> {OUT}")
    return 0 if verdict == "GREEN" else 1


if __name__ == "__main__":
    raise SystemExit(main())
