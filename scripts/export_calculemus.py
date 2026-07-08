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
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

_REPO = Path(__file__).resolve().parent.parent
_DEFAULT_LEDGER = Path(
    os.environ.get("LEIBNIZ_LEDGER")
    or (_REPO.parent / "codex-calculemus" / "ledger" / "calculemus.json")
)

# H0 axiom-closure gate: a discharged/Q.E.D. law may depend only on the standard Lean/Mathlib axioms — never on
# `sorryAx` and never on a project-admitted axiom (an F2b-style scaffold), which would mean the "proof" is not a
# proof. `#print axioms <name>` reports the footprint; we assert it is a subset of the standard set.
_STD_AXIOMS = frozenset({"propext", "Classical.choice", "Quot.sound"})
_NAME_RE = re.compile(r"(?:theorem|lemma)\s+([^\s({\[:]+)")
_AXIOMS_RE = re.compile(r"depends on axioms:\s*\[([^\]]*)\]")


def axiom_closure(backend, theorem_src: str, proof_src: str, imports, allowed=_STD_AXIOMS,
                  preamble: str = "") -> dict:
    """Elaborate `<preamble> <theorem_src> := <proof_src>` and run `#print axioms`. ok = it elaborates with no
    error AND its axiom footprint contains no `sorryAx` and no axiom outside `allowed` (the standard Lean/Mathlib
    set). A discharged law that secretly rests on `sorry` or an admitted lemma fails here even if the kernel
    elaborates the (open) term. ADR 0062: the operator-authored `preamble` (defs/set_options) is elaborated as
    part of the source, so a smuggled hole/axiom there is caught too. Read-only: mints nothing, edits no core file."""
    m = _NAME_RE.search(theorem_src)
    if not m:
        return {"ok": False, "reason": "no theorem name in theorem_src", "axioms": []}
    name = m.group(1)
    body = proof_src if proof_src.lstrip().startswith(":=") else f":= {proof_src}"
    decl = f"{theorem_src} {body}\n#print axioms {name}"
    src = f"{preamble.rstrip()}\n{decl}" if preamble.strip() else decl
    r = backend._run(src, tuple(imports))
    if r is None:
        return {"ok": False, "reason": "no response from REPL", "axioms": [], "name": name}
    msgs = r.get("messages", []) or []
    errors = [(mm.get("data") or "") for mm in msgs if mm.get("severity") == "error"]
    axioms: list = []
    for mm in msgs:
        am = _AXIOMS_RE.search(mm.get("data") or "")
        if am:
            axioms = [a.strip() for a in am.group(1).split(",") if a.strip()]
    has_sorry = "sorryAx" in axioms or any("sorry" in e.lower() for e in errors)
    extra = [a for a in axioms if a not in allowed]
    return {"ok": bool(not errors and not has_sorry and not extra), "axioms": axioms,
            "extra_axioms": extra, "has_sorry": has_sorry, "errors": errors[:2], "name": name}


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
    print("✓ every claimed Q.E.D. is kernel-confirmed with a clean axiom footprint.")
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
