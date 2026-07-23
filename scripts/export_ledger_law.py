"""Export a LEDGER-ORIGINATED law (a daemon promulgation from the runtime DB) as a publishable
site law JSON — the first exerciser of the ADR 0063 origination path.

Unlike the ``export_*_law.py`` amplification scripts (operator-authored artifacts re-deciding a
cited source), this exports the daemon's OWN conjectures: rows the pipeline promulgated. The
origination claim is earned at export time, fail-closed:

1. The proof is re-discharged against the live Lean kernel HERE (``LeanVerifier.discharge`` —
   the sole ``kernel_verified`` writer) and its axiom closure is checked (propext only).
2. ``attest_novelty`` runs the FULL mechanical novelty gate (ADR 0061 coefficient-degenerate →
   ``is_trivial`` ladder → corpus ``contains_equivalent`` → ADR 0032 ``structural_known``)
   against the curated corpus PLUS the daemon's other promulgated laws (ADR 0052) — excluding
   only the law's own hash (a law is not disqualified by being itself). No PASS → no export.
3. The payload carries ``origination: "originated"`` + the attestation with its ADR 0063 caveat
   (gate-novel ≠ literature-novel), ``tier: kernel-decided``, and ``published_at`` stamped by
   the CALLER's append into the codex ledger (H1: dates are stamped at append; this script
   leaves it empty unless ``--published-at`` is given for the site JSON twin).

Usage:
  PYTHONPATH=. python scripts/export_ledger_law.py --pid dab2022069c9 \\
      --id two_squares_mod4_obstruction --statement "…crisp faithful prose…" [--write]
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from leibniz.backends.lean_axioms import axiom_closure  # noqa: E402
from leibniz.backends.lean_repl import LeanReplBackend, available  # noqa: E402
from leibniz.calculemus_site import law_payload  # noqa: E402
from leibniz.corpus import CorpusBackend, self_ledger_entries  # noqa: E402
from leibniz.gates.novelty import NoveltyGate  # noqa: E402
from leibniz.origination import attest_novelty, claim_signature  # noqa: E402
from leibniz.propositio import Demonstratio, Enuntiatio, Expressio, Propositio  # noqa: E402
from leibniz.types import ClaimType  # noqa: E402
from leibniz.verifiers import LeanVerifier, normalize_statement  # noqa: E402


def load_row(db_path: str, pid: str) -> dict:
    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    row = con.execute(
        "SELECT * FROM memory WHERE pid = ? AND lower(finish_reason) = 'promulgated' "
        "AND kernel_verified = 1", (pid,)).fetchone()
    con.close()
    if row is None:
        raise SystemExit(f"no promulgated kernel-verified row with pid {pid!r}")
    return dict(row)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pid", required=True)
    ap.add_argument("--id", required=True, help="site law id (filename stem)")
    ap.add_argument("--statement", default="", help="crisp faithful prose (defaults to the ledger's)")
    ap.add_argument("--published-at", default="", help="leave empty; the ledger append stamps H1 dates")
    ap.add_argument("--db", default=str(Path.home() / "Claude_Primary" / "leibniz" / ".leibniz" / "memory.db"))
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()

    if not available():
        raise SystemExit("Lean REPL image unavailable — the kernel must re-verify before export")
    row = load_row(args.db, args.pid)
    statement = args.statement or (row.get("statement") or "").strip()
    en = Enuntiatio(statement=statement, claim_type=ClaimType(row["claim_type"]),
                    falsifiable_claim=row.get("falsifiable_claim") or "",
                    claim_domain="", claim_property=row.get("claim_property") or "")
    expr = Expressio(theorem_src=row["theorem_src"], imports=("Mathlib.Tactic",))
    prop = Propositio(enuntiatio=en, expressio=expr)
    prop.demonstratio = Demonstratio(proof_obligation="claim", proof_src=row["proof_src"])

    kernel = LeanReplBackend()
    lean = LeanVerifier(kernel)
    ev = lean.discharge(prop.expressio, prop.demonstratio)      # sole kernel_verified writer
    if not prop.demonstratio.kernel_verified:
        raise SystemExit(f"kernel REFUSED the ledger proof: {ev.detail}")
    ax = axiom_closure(kernel, row["theorem_src"], row["proof_src"], ("Mathlib.Tactic",))
    if not ax.get("ok"):
        raise SystemExit(f"axiom closure failed: {ax}")
    print(f"[export] kernel re-verified {args.pid}; axioms: {ax.get('axioms')}")

    # ADR 0063: the origination claim is earned NOW, against corpus + the daemon's OTHER laws.
    prop.signature = claim_signature(row["theorem_src"], en.claim_type,
                                     subject="nonnegative integers",
                                     relation=row.get("claim_property") or "")
    own_hash = normalize_statement(row["theorem_src"])
    extras = [e for e in self_ledger_entries(args.db) if e.formal_hash != own_hash]
    gate = NoveltyGate(CorpusBackend.from_json(None, extra=extras), lean)
    attestation = attest_novelty(prop, gate)
    if attestation is None:
        raise SystemExit("novelty gate REFUSED origination (trivial/known/restatement) — not exported")
    print(f"[export] novelty attested: {attestation['checks_passed']}")

    payload = law_payload(prop, published_at=args.published_at, specimen=False,
                          tier="kernel-decided", origination="originated",
                          references=[], novelty_attestation=attestation)
    payload["pid"] = args.pid
    out = _ROOT / "site" / "src" / "content" / "laws" / f"{args.id}.json"
    if args.write:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
        print(f"[export] wrote {out}")
    else:
        print(json.dumps(payload, ensure_ascii=False)[:400])
    kernel.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
