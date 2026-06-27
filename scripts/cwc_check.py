"""Standalone CWC witness audit CLI (Option E — the re-runnable verification asset).

Takes a constant-weight-code witness `A(n,d,w) >= |code|` and runs it end-to-end through the two
already-validated sound assets:

    code --> verify_cwc (UNTRUSTED pre-check; refuses to render a false theorem)
         --> render_cwc_lean (core-Lean, no Mathlib)
         --> Lean 4.31 kernel via LeanCliBackend.check_source  (the TRUSTED re-check)
         --> cwc_table_oracle: best_known / is_improvement       (AUTOMATED novelty, never an LLM)

and prints whether the kernel ACCEPTED the witness and how it compares to Brouwer's table-of-record.

WHAT THIS IS / IS NOT (read before trusting the output):
- It is an AUDIT / demonstration tool: a human (or a search) hands it a finite witness; it gives a
  kernel-stamped lower bound + an automated novelty verdict. This is the "human proposes / daemon
  soundly checks" (verification-amplification) mode, scoped to ONE domain (CWC lower bounds).
- It is NOT the production promulgation path. It deliberately bypasses the full faithfulness gate and
  the novelty/triviality gates. It NEVER sets Demonstratio.kernel_verified or marks anything
  promulgated — it only reports the kernel verdict and the oracle lookup. The trust boundary
  (LeanVerifier.discharge as sole kernel_verified writer; TrustPolicy.validate_path for promotion)
  is untouched by this script.
- A record-BEATING witness here would be flagged "BEATS record" by the oracle but is NOT auto-
  promulgated: the pipeline's `decide`-triviality gate would quarantine it absent the ADR 0040
  carve-out (deferred until a real beat exists). See docs/adr/0040-cwc-record-triviality-carveout.md.

Pure stdlib + the project's own modules. The kernel step needs the Lean docker image; without it the
CLI still runs verify_cwc + the oracle and reports the kernel step as UNAVAILABLE.

Exit codes (a machine-readable pass/fail signal; exit 0 NEVER means "kernel-checked" unless the kernel
actually ran):
    0  witness valid AND kernel ACCEPTED it (or the kernel was deliberately skipped via --no-kernel)
    2  witness passed the UNTRUSTED pre-check but the kernel could not run (docker absent/timeout/crash)
       -- this is NOT a kernel pass; only verify_cwc saw the witness
    1  witness invalid (failed verify_cwc) OR the kernel REJECTED it
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT / "scripts"))
sys.path.insert(0, str(_ROOT))

import cwc_table_oracle as ora  # noqa: E402
from probe_beta_cwc_pilot import render_cwc_lean, verify_cwc  # noqa: E402


def parse_code(spec: str) -> list[tuple[int, ...]]:
    """Parse 'a,b,c;d,e,f;...' into a list of integer tuples (one codeword per ';' group)."""
    out = []
    for group in spec.split(";"):
        group = group.strip()
        if not group:
            continue
        out.append(tuple(int(x) for x in group.replace(" ", "").split(",")))
    return out


def load_witness(args) -> tuple[int, int, int, list[tuple[int, ...]]]:
    """Witness from --witness JSON {n,d,w,code:[[...],...]} or from --n/--d/--w/--code flags."""
    if args.witness:
        try:
            data = json.loads(Path(args.witness).read_text())
            code = [tuple(c) for c in data["code"]]
            return int(data["n"]), int(data["d"]), int(data["w"]), code
        except (json.JSONDecodeError, KeyError, OSError, TypeError, ValueError) as e:
            raise SystemExit(f"bad witness file {args.witness}: {e}")
    if args.n is None or args.d is None or args.w is None or not args.code:
        raise SystemExit("provide --witness FILE.json, or all of --n --d --w --code 'a,b,c;d,e,f'")
    return args.n, args.d, args.w, parse_code(args.code)


def check(n: int, d: int, w: int, code, *, run_kernel: bool = True) -> dict:
    """Run the full audit pipeline; return a structured report. Never mutates any ledger state."""
    code_sets = [frozenset(c) for c in code]
    ok, reason = verify_cwc(code_sets, n, d, w)
    report: dict = {"n": n, "d": d, "w": w, "size": len(code_sets),
                    "verify_ok": ok, "verify_reason": reason}
    if not ok:
        report["kernel"] = "skipped (witness fails the untrusted pre-check)"
        report["novelty"] = "n/a"
        return report

    lean_src = render_cwc_lean(n, d, w, code)        # raises only if verify failed; we already passed
    report["lean_theorem"] = f"cwc_{n}_{d}_{w}_ge_{len(code_sets)}"

    # --- the trusted re-check: the Lean kernel. Reports only; never sets kernel_verified. ---
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

    # --- automated novelty: oracle lookup, never an LLM judgment (invariant 4) ---
    snap = ora.load_snapshot()[0]                    # load once; thread to both oracle calls
    bk = ora.best_known(n, d, w, snap)
    if bk is None:
        report["best_known"] = None
        report["novelty"] = "untabulated (no table-of-record entry; novelty not claimable)"
    else:
        report["best_known"] = bk
        if ora.is_improvement(n, d, w, len(code_sets), snap):
            report["novelty"] = (f"BEATS record ({len(code_sets)} > {bk}) — NOT auto-promulgated; "
                                 f"needs the ADR 0040 carve-out + operator review")
        elif len(code_sets) == bk:
            report["novelty"] = f"equals record ({bk})"
        else:
            report["novelty"] = f"below record ({len(code_sets)} < {bk})"
    return report


def _exit_status(report: dict) -> int:
    """Pure pass/fail signal (see module docstring). 0 = valid + kernel-accepted (or --no-kernel);
    2 = valid pre-check but the kernel could NOT run (not a kernel pass); 1 = invalid or rejected.
    Driven off the typed kernel status, not display copy, so exit 0 never silently means
    'kernel-checked' when the kernel never saw the witness."""
    if not report["verify_ok"]:
        return 1
    kernel = str(report.get("kernel", ""))
    if kernel in ("KERNEL-VERIFIED", "not run (--no-kernel)"):
        return 0
    if kernel.startswith("unavailable"):
        return 2
    return 1                                          # KERNEL-REJECTED or anything unexpected


def main() -> int:
    ap = argparse.ArgumentParser(description="Audit a constant-weight-code lower-bound witness "
                                             "(kernel re-check + automated novelty). NOT the "
                                             "production promulgation path.")
    ap.add_argument("--witness", help="JSON file: {n,d,w,code:[[...],...]}")
    ap.add_argument("--n", type=int)
    ap.add_argument("--d", type=int)
    ap.add_argument("--w", type=int)
    ap.add_argument("--code", help="'a,b,c;d,e,f;...' (one weight-w codeword per ';' group)")
    ap.add_argument("--no-kernel", action="store_true", help="skip the Lean kernel step")
    ap.add_argument("--json", action="store_true", help="emit the report as JSON")
    args = ap.parse_args()

    n, d, w, code = load_witness(args)
    report = check(n, d, w, code, run_kernel=not args.no_kernel)

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"witness: A({n},{d},{w}) >= {report['size']}")
        print(f"  pre-check (untrusted verify_cwc): {'OK' if report['verify_ok'] else 'FAIL — ' + report['verify_reason']}")
        if report["verify_ok"]:
            print(f"  Lean kernel re-check (trusted):    {report['kernel']}")
            print(f"  novelty vs Brouwer table (oracle): {report['novelty']}")
        print("  [audit tool — does not promulgate; trust boundary untouched]")
    return _exit_status(report)


if __name__ == "__main__":
    raise SystemExit(main())
