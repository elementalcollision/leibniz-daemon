"""Standalone covering-design witness audit CLI (ADR 0043, Track B1) — the 2nd-domain audit asset.

Takes a (v,k,t)-covering witness `C(v,k,t) <= |blocks|` and runs it end-to-end through the same sound
audit path as cwc_check.py, for the new domain:

    blocks --> verify_covering (UNTRUSTED pre-check; refuses to render a false theorem)
           --> render_covering_lean (core Lean, no Mathlib; completeness of t-subsets BY CONSTRUCTION)
           --> Lean 4.31 kernel via LeanCliBackend.check_source  (the TRUSTED re-check)
           --> covering_table_oracle: best_known / is_improvement   (AUTOMATED novelty, never an LLM)

WHAT THIS IS / IS NOT (identical posture to cwc_check.py — read before trusting the output):
- AUDIT / amplification tool: a stronger/human/research producer hands it a finite covering; it returns
  a kernel-stamped UPPER bound + an automated novelty verdict against the La Jolla table of record.
- It is NOT the production promulgation path. It NEVER sets Demonstratio.kernel_verified and NEVER marks
  anything promulgated. The trust boundary is untouched.
- A record-BEATING covering (strictly fewer blocks than the LJCR best-known) is flagged "BEATS record"
  but is NOT auto-promulgated.

Exit codes (exit 0 NEVER means "kernel-checked" unless the kernel actually ran):
    0  witness valid AND kernel ACCEPTED it (or --no-kernel)
    2  witness passed the UNTRUSTED pre-check but the kernel could not run (docker absent/timeout/crash)
    1  witness invalid (failed verify_covering) OR the kernel REJECTED it
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT / "scripts"))
sys.path.insert(0, str(_ROOT))

import covering_table_oracle as ora  # noqa: E402
from covering_verify import render_covering_lean, verify_covering  # noqa: E402


def parse_blocks(spec: str) -> list[tuple[int, ...]]:
    """Parse 'a,b,c;d,e,f;...' into a list of integer tuples (one block per ';' group)."""
    out = []
    for group in spec.split(";"):
        group = group.strip()
        if not group:
            continue
        out.append(tuple(int(x) for x in group.replace(" ", "").split(",")))
    return out


def load_witness(args):
    if args.witness:
        try:
            data = json.loads(Path(args.witness).read_text())
            blocks = [tuple(b) for b in data["blocks"]]
            return int(data["v"]), int(data["k"]), int(data["t"]), blocks
        except (json.JSONDecodeError, KeyError, OSError, TypeError, ValueError) as e:
            raise SystemExit(f"bad witness file {args.witness}: {e}")
    if args.v is None or args.k is None or args.t is None or not args.blocks:
        raise SystemExit("provide --witness FILE.json, or all of --v --k --t --blocks 'a,b,c;d,e,f'")
    return args.v, args.k, args.t, parse_blocks(args.blocks)


def check(v: int, k: int, t: int, blocks, *, run_kernel: bool = True) -> dict:
    """Run the full audit pipeline; return a structured report. Never mutates any ledger state."""
    block_sets = [frozenset(b) for b in blocks]
    ok, reason = verify_covering(block_sets, v, k, t)
    report: dict = {"v": v, "k": k, "t": t, "size": len(block_sets),
                    "verify_ok": ok, "verify_reason": reason}
    if not ok:
        report["kernel"] = "skipped (witness fails the untrusted pre-check)"
        report["novelty"] = "n/a"
        return report

    lean_src = render_covering_lean(v, k, t, blocks)
    report["lean_theorem"] = f"cov_{v}_{k}_{t}_le_{len(block_sets)}"

    if run_kernel:
        try:
            from leibniz.backends.lean_cli import LeanCliBackend, available
            if available():
                verdict = LeanCliBackend().check_source(lean_src)
                report["kernel"] = ("KERNEL-VERIFIED" if verdict is True
                                    else "KERNEL-REJECTED" if verdict is False
                                    else "unavailable")
            else:
                report["kernel"] = "unavailable (Lean docker image not present)"
        except Exception as e:  # pragma: no cover - environment dependent
            report["kernel"] = f"unavailable ({type(e).__name__})"
    else:
        report["kernel"] = "not run (--no-kernel)"

    snap = ora.load_snapshot()[0]
    bk = ora.best_known(v, k, t, snap)
    if bk is None:
        report["best_known"] = None
        report["novelty"] = "untabulated (no LJCR entry; novelty not claimable)"
    else:
        report["best_known"] = bk
        if ora.is_improvement(v, k, t, len(block_sets), snap):
            report["novelty"] = (f"BEATS record ({len(block_sets)} < {bk}) — NOT auto-promulgated; "
                                 f"needs operator review")
        elif len(block_sets) == bk:
            report["novelty"] = f"equals record ({bk})"
        else:
            report["novelty"] = f"above record ({len(block_sets)} > {bk}; not an improvement)"
    return report


def _exit_status(report: dict) -> int:
    if not report["verify_ok"]:
        return 1
    kernel = str(report.get("kernel", ""))
    if kernel in ("KERNEL-VERIFIED", "not run (--no-kernel)"):
        return 0
    if kernel.startswith("unavailable"):
        return 2
    return 1


def main() -> int:
    ap = argparse.ArgumentParser(description="Audit a covering-design upper-bound witness (kernel "
                                             "re-check + automated novelty vs the La Jolla table). "
                                             "NOT the production promulgation path.")
    ap.add_argument("--witness", help="JSON file: {v,k,t,blocks:[[...],...]}")
    ap.add_argument("--v", type=int)
    ap.add_argument("--k", type=int)
    ap.add_argument("--t", type=int)
    ap.add_argument("--blocks", help="'a,b,c;d,e,f;...' (one k-subset block per ';' group)")
    ap.add_argument("--no-kernel", action="store_true", help="skip the Lean kernel step")
    ap.add_argument("--json", action="store_true", help="emit the report as JSON")
    args = ap.parse_args()

    v, k, t, blocks = load_witness(args)
    report = check(v, k, t, blocks, run_kernel=not args.no_kernel)

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"witness: C({v},{k},{t}) <= {report['size']}")
        print(f"  pre-check (untrusted verify_covering): {'OK' if report['verify_ok'] else 'FAIL — ' + report['verify_reason']}")
        if report["verify_ok"]:
            print(f"  Lean kernel re-check (trusted):       {report['kernel']}")
            print(f"  novelty vs La Jolla table (oracle):   {report['novelty']}")
        print("  [audit tool — does not promulgate; trust boundary untouched]")
    return _exit_status(report)


if __name__ == "__main__":
    raise SystemExit(main())
