"""Export / verify the codexcalculemus.com source ledger.

Two roles:

1. **Programmatic (the forward path).** From a live `Calculemus` produced by the
   daemon's gated pipeline, write `site/ledger/calculemus.json`:

       from leibniz.calculemus_site import write_ledger
       write_ledger(calc, "site/ledger/calculemus.json", generated_at=stamp)

2. **`--check` (honesty gate).** Re-verify every law in the committed ledger
   against the *real* Lean kernel (via the REPL backend). A law claiming
   `kernel_verified: true` whose proof the kernel rejects fails the check — so the
   ledger can never publish a Q.E.D. the kernel won't confirm. Skips cleanly when
   the Lean image is absent (e.g. CI without Docker).

Run:  python scripts/export_calculemus.py --check
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

_REPO = Path(__file__).resolve().parent.parent
_LEDGER = _REPO / "site" / "ledger" / "calculemus.json"


def check_ledger(path: Path = _LEDGER) -> int:
    from leibniz.backends.lean_repl import LeanReplBackend, available  # noqa: E402
    from leibniz.propositio import Expressio  # noqa: E402

    ledger = json.loads(path.read_text())
    laws = ledger.get("laws", [])
    claimed = [law for law in laws if law.get("kernel_verified")]
    print(f"ledger: {len(laws)} laws, {len(claimed)} claim kernel_verified")

    if not available():
        print("Lean REPL image not available; cannot verify. (skip — non-fatal)")
        return 0

    backend = LeanReplBackend()
    failures = 0
    try:
        for law in claimed:
            expr = Expressio(theorem_src=law["theorem_src"], imports=tuple(law.get("imports", [])))
            ok = backend.check_proof(expr, law.get("proof_src", ""))
            mark = "VERIFIED" if ok else "FAILED  "
            print(f"  {mark}  {law.get('id', law['statement'])}: {law.get('proof_src','')}")
            if not ok:
                failures += 1
    finally:
        backend.close()

    if failures:
        print(f"✗ {failures} law(s) claim a Q.E.D. the kernel rejects.", file=sys.stderr)
        return 1
    print("✓ every claimed Q.E.D. is confirmed by the kernel.")
    return 0


def main(argv: list[str]) -> int:
    if "--check" in argv:
        return check_ledger()
    print(__doc__)
    print(f"committed ledger: {_LEDGER}")
    print("Use --check to re-verify specimen proofs against the Lean kernel.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
