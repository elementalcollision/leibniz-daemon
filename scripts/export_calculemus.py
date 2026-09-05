"""Export / verify the Codex Calculemus ledger.

The site lives in the separate private repo **`elementalcollision/codex-calculemus`**
(the renderer); this repo (Leibniz) is the producer. The bridge is the published
ledger JSON, committed in the site repo at `ledger/calculemus.json`.

Two roles:

1. **Programmatic (the forward path).** From a live `Calculemus` produced by the
   daemon's gated pipeline, write the site ledger:

       from leibniz.calculemus_site import write_ledger
       write_ledger(calc, "/path/to/codex-calculemus/ledger/calculemus.json", generated_at=stamp)

2. **`--check [ledger.json]` (honesty gate).** Every published law must carry a non-empty
   ``published_at`` (the DATE of publication — stamped when the law is appended to the ledger,
   normally the append-commit date); an undated law fails the check. Then re-verify every law
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
import re
import sys
from pathlib import Path

from leibniz.backends.lean_axioms import STD_AXIOMS, axiom_closure  # noqa: F401

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

_REPO = Path(__file__).resolve().parent.parent
_DEFAULT_LEDGER = Path(
    os.environ.get("LEIBNIZ_LEDGER")
    or (_REPO.parent / "codex-calculemus" / "ledger" / "calculemus.json")
)

# H0 axiom-closure gate: a discharged/Q.E.D. law may depend only on the standard Lean/Mathlib axioms — never on
# `sorryAx` and never on a project-admitted axiom (an F2b-style scaffold), which would mean the "proof" is not a
# proof. `#print axioms <name>` reports the footprint; we assert it is a subset of the standard set.
_STD_AXIOMS = STD_AXIOMS
_NAME_RE = re.compile(r"(?:theorem|lemma)\s+([^\s({\[:]+)")

# ADR 0089: this module used to carry its OWN copy of `axiom_closure`. `leibniz.backends.lean_axioms`
# exists precisely so the faithfulness-time and publish-time checks are "the SAME code ... not two
# drifting copies" (its own docstring) — and they had drifted: the library copy was hardened to
# require a `#print axioms` report about the theorem, while this one, which is `check_ledger`'s H0
# gate for the ADR 0033 publish act, still printed VERIFIED for a false theorem proved `by sorry`
# against a silent REPL. Re-exported rather than re-implemented so it cannot drift again.

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

    # H1 (date honesty): every PUBLISHED law must carry its publication date. The producer-side law
    # JSONs are legitimately undated (publication has not happened yet); the ledger is the record of
    # the publish act, so an empty published_at here is a provenance defect — fail regardless of
    # whether the kernel is available.
    undated = [law.get("id") or law.get("statement", "?") for law in laws
               if not str(law.get("published_at", "")).strip()]
    if undated:
        print(f"✗ {len(undated)} law(s) missing published_at — stamp the publication date at "
              f"ledger-append time:", file=sys.stderr)
        for lid in undated:
            print(f"    - {lid}", file=sys.stderr)

    if not available():
        print("Lean REPL image not available; cannot verify proofs. (skip — non-fatal)")
        return 1 if undated else 0

    backend = LeanReplBackend()
    failures = 0
    try:
        for law in claimed:
            preamble = law.get("preamble", "")   # ADR 0062: re-verify the SAME full source the kernel saw
            expr = Expressio(theorem_src=law["theorem_src"], imports=tuple(law.get("imports", [])),
                             preamble=preamble)
            ok = backend.check_proof(expr, law.get("proof_src", ""))
            # H0: a claimed Q.E.D. must also have a clean axiom footprint (no sorryAx / admitted axiom).
            ax = axiom_closure(backend, law["theorem_src"], law.get("proof_src", ""), law.get("imports", []),
                               preamble=preamble)
            clean = ok and ax["ok"]
            note = f"axioms={ax['axioms']}"
            if ax.get("has_sorry"):
                note += " ⚠SORRY"
            if ax.get("extra_axioms"):
                note += f" ⚠ADMITTED={ax['extra_axioms']}"
            print(f"  {'VERIFIED' if clean else 'FAILED  '}  {law.get('id', law['statement'])}: "
                  f"proof_ok={ok} {note}")
            if not clean:
                failures += 1
    finally:
        backend.close()

    if failures:
        print(f"✗ {failures} law(s) claim a Q.E.D. the kernel rejects or that rests on sorry/an admitted axiom.",
              file=sys.stderr)
        return 1
    if undated:
        return 1
    print("✓ every claimed Q.E.D. is kernel-confirmed with a clean axiom footprint, and every law is dated.")
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
