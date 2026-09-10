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
   the ledger to the site repo.

   **Exit codes are three-valued, because "did not run" is not "passed"** (ADR 0093's rule,
   applied to this gate). ``0`` means the gate RAN and everything it checks is clean; ``1``
   means at least one check FAILED (and may coexist with checks that could not run -- a real
   defect outranks "could not verify"); ``2`` means nothing failed but not everything ran --
   no ledger, an unreadable or law-less one, no Lean image without ``--dates-only``, or a REPL
   that died mid-run. Before this, both of those returned 0, so a green run proved
   nothing unless you happened to read the stderr line: a `--check` against a missing sibling
   checkout printed "ledger not found" and exited 0, which is indistinguishable from a verified
   ledger to any caller that reads the status.

   ``--dates-only`` opts INTO the kernel-less run (H1 date honesty alone, no proof re-check) and
   is the only way to get a 0 without the kernel. It exists because the date check is genuinely
   kernel-independent; it must be asked for, never inferred from the kernel being missing.

Ledger location, in priority order: the `--check` path arg, then `LEIBNIZ_LEDGER`,
then a sibling checkout `../codex-calculemus/ledger/calculemus.json`.

Run:  python scripts/export_calculemus.py --check [path/to/ledger.json]
      python scripts/export_calculemus.py --check --dates-only        # no kernel needed
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from leibniz.backends.lean_axioms import STD_AXIOMS, axiom_closure  # noqa: E402,F401

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

#: `check_ledger` could not verify: no ledger, or no kernel. Distinct from 0 (verified) and
#: 1 (a real failure) so a caller cannot read "did not run" as "passed".
EXIT_UNVERIFIED = 2


def check_ledger(path: Path, dates_only: bool = False) -> int:
    path = Path(path)
    if not path.exists():
        print(f"✗ ledger not found: {path}", file=sys.stderr)
        print("  clone elementalcollision/codex-calculemus, or pass a path / set LEIBNIZ_LEDGER.",
              file=sys.stderr)
        # NOT 0. An absent ledger means this gate verified nothing; returning 0 made that
        # indistinguishable from a clean ledger, which is the failure shape ADR 0093 exists for.
        return EXIT_UNVERIFIED

    from leibniz.backends.lean_repl import LeanReplBackend, available  # noqa: E402
    from leibniz.propositio import Expressio  # noqa: E402

    try:
        ledger = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        # A ledger we cannot READ is not a ledger we verified. `deploy/profiles/*.env.example`
        # set LEIBNIZ_LEDGER to a DIRECTORY, which lands here rather than as a traceback.
        print(f"✗ cannot read ledger {path}: {exc}", file=sys.stderr)
        return EXIT_UNVERIFIED
    if not isinstance(ledger, dict) or "laws" not in ledger:
        print(f"✗ {path} has no 'laws' key — not a ledger, or the schema moved. Nothing was checked.",
              file=sys.stderr)
        return EXIT_UNVERIFIED

    laws = ledger.get("laws") or []
    claimed = [law for law in laws if law.get("kernel_verified")]
    print(f"ledger {path}: {len(laws)} laws, {len(claimed)} claim kernel_verified")
    if not laws:
        # "0 collected must not masquerade as a pass" -- the rule ci.yml already applies to pytest.
        print(f"✗ ledger {path} contains 0 laws — nothing was verified.", file=sys.stderr)
        return EXIT_UNVERIFIED

    # H1b: a law carrying a Q.E.D. but NOT kernel_verified is skipped by the loop below, so the
    # boolean silently shrinks the gate's scope. Disagreement between the two is a defect, not a
    # reason to check less.
    mismatched = [law.get("id") or law.get("statement", "?") for law in laws
                  if str(law.get("qed", "")).strip() == "Q.E.D." and not law.get("kernel_verified")]
    if mismatched:
        print(f"✗ {len(mismatched)} law(s) stamp Q.E.D. without kernel_verified — the gate would "
              f"skip them:", file=sys.stderr)
        for lid in mismatched:
            print(f"    - {lid}", file=sys.stderr)

    # H1 (date honesty): every PUBLISHED law must carry its publication date. The producer-side law
    # JSONs are legitimately undated (publication has not happened yet); the ledger is the record of
    # the publish act, so an empty published_at here is a provenance defect — fail regardless of
    # whether the kernel is available.
    # `str(law.get(...))` let None/0/False through as "None"/"0"/"False" -- non-empty, so dated.
    undated = [law.get("id") or law.get("statement", "?") for law in laws
               if not (isinstance(law.get("published_at"), str) and law["published_at"].strip())]
    if undated:
        print(f"✗ {len(undated)} law(s) missing published_at — stamp the publication date at "
              f"ledger-append time:", file=sys.stderr)
        for lid in undated:
            print(f"    - {lid}", file=sys.stderr)

    hard_defect = bool(undated or mismatched)
    if dates_only or not available():
        if not dates_only:
            print("✗ Lean REPL image not available; proofs were NOT re-verified. Re-run where the "
                  "kernel is, or pass --dates-only to check H1 dates alone.", file=sys.stderr)
            # A defect the date check CAN see without a kernel outranks "could not verify".
            return 1 if hard_defect else EXIT_UNVERIFIED
        print("--dates-only requested; proofs were NOT re-verified.")
        return 1 if hard_defect else 0

    backend = LeanReplBackend()
    failures = 0
    unreachable = 0
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
            if clean:
                continue
            if ax.get("reason") == "no response from REPL":
                # The REPL died (ADR 0088 records an exit-134 kernel-stack overflow). That is NOT
                # the kernel rejecting the proof, and must not be reported as one.
                unreachable += 1
            else:
                failures += 1
    finally:
        backend.close()

    if failures:
        print(f"✗ {failures} law(s) claim a Q.E.D. the kernel rejects or that rests on sorry/an admitted axiom.",
              file=sys.stderr)
        return 1
    if mismatched:
        return 1
    if hard_defect:
        return 1
    if unreachable:
        print(f"✗ {unreachable} law(s) could not be checked — the REPL gave no response.", file=sys.stderr)
        return EXIT_UNVERIFIED
    print("✓ every claimed Q.E.D. is kernel-confirmed with a clean axiom footprint, and every law is dated.")
    return 0


_KNOWN_FLAGS = {"--check", "--dates-only"}


def main(argv: list[str]) -> int:
    unknown = [a for a in argv if a.startswith("-") and a not in _KNOWN_FLAGS]
    if unknown:
        # A typo'd flag used to be silently dropped -- `--chek` ran the help path and exited 0,
        # which under this contract reads as "verified".
        print(f"✗ unknown option(s): {' '.join(unknown)}", file=sys.stderr)
        return EXIT_UNVERIFIED
    if "--check" in argv:
        dates_only = "--dates-only" in argv
        paths = [a for a in argv if not a.startswith("-")]
        return check_ledger(Path(paths[0]) if paths else _DEFAULT_LEDGER, dates_only=dates_only)
    print(__doc__)
    print(f"default ledger: {_DEFAULT_LEDGER}")
    print("Use --check [path] to re-verify a ledger's proofs against the Lean kernel.")
    return 0 if not argv else EXIT_UNVERIFIED


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
