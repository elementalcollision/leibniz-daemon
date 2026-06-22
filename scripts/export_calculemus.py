"""Export / verify the Codex Calculemus ledger.

The site lives in the separate private repo **`elementalcollision/codex-calculemus`**
(the renderer); this repo (Leibniz) is the producer. The bridge is the published
ledger JSON, committed in the site repo at `ledger/calculemus.json`.

Two roles:

1. **Programmatic (the forward path).** From a live `Calculemus` produced by the
   daemon's gated pipeline, write the site ledger:

       from leibniz.calculemus_site import write_ledger
       write_ledger(calc, "/path/to/codex-calculemus/ledger/calculemus.json", generated_at=stamp)

2. **`--check [ledger.json]` (honesty gate).** Re-verify every law in the ledger
   against the *real* Lean kernel (via the REPL backend, which lives here, not in
   the site repo). A law claiming `kernel_verified: true` whose proof the kernel
   rejects fails the check — so the ledger can never publish a Q.E.D. the kernel
   won't confirm. Run this here (Leibniz has Lean + the package) before publishing
   the ledger to the site repo. Skips cleanly when the Lean image is absent.

Ledger location, in priority order: the `--check` path arg, then `LEIBNIZ_LEDGER`,
then a sibling checkout `../codex-calculemus/ledger/calculemus.json`.

Run:  python scripts/export_calculemus.py --check [path/to/ledger.json]
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

_REPO = Path(__file__).resolve().parent.parent
_DEFAULT_LEDGER = Path(
    os.environ.get("LEIBNIZ_LEDGER")
    or (_REPO.parent / "codex-calculemus" / "ledger" / "calculemus.json")
)


def check_ledger(path: Path) -> int:
    path = Path(path)
    if not path.exists():
        print(f"ledger not found: {path}", file=sys.stderr)
        print("  clone elementalcollision/codex-calculemus, or pass a path / set LEIBNIZ_LEDGER.")
        return 0  # non-fatal: nothing to check here

    from leibniz.backends.lean_repl import LeanReplBackend, available  # noqa: E402
    from leibniz.propositio import Expressio  # noqa: E402

    ledger = json.loads(path.read_text())
    laws = ledger.get("laws", [])
    claimed = [law for law in laws if law.get("kernel_verified")]
    print(f"ledger {path}: {len(laws)} laws, {len(claimed)} claim kernel_verified")

    if not available():
        print("Lean REPL image not available; cannot verify. (skip — non-fatal)")
        return 0

    backend = LeanReplBackend()
    failures = 0
    try:
        for law in claimed:
            expr = Expressio(theorem_src=law["theorem_src"], imports=tuple(law.get("imports", [])))
            ok = backend.check_proof(expr, law.get("proof_src", ""))
            print(f"  {'VERIFIED' if ok else 'FAILED  '}  {law.get('id', law['statement'])}: {law.get('proof_src','')}")
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
        paths = [a for a in argv if not a.startswith("-")]
        return check_ledger(Path(paths[0]) if paths else _DEFAULT_LEDGER)
    print(__doc__)
    print(f"default ledger: {_DEFAULT_LEDGER}")
    print("Use --check [path] to re-verify a ledger's proofs against the Lean kernel.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
