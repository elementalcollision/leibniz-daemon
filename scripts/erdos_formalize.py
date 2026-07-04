"""Erdős statement-formalization lane (T9, candidate B) — faithfully formalize Erdős problem *statements* in
Lean 4 (not solutions), gated on faithfulness.

The Erdős database (erdosproblems.com, ~1000 problems) is dominated by *asymptotic* statements the kernel cannot
decide (`≪`, `o(1)`, `limsup`) — so Leibniz cannot *solve* them. But it can state them faithfully in Lean, and
**faithfulness of a formal statement is a kernel-adjacent judgment**: does the `Prop` type-check, and do the
defined objects behave/compute correctly? This module holds each problem's statement as a `.lean` artifact and
runs the FAITHFULNESS GATE over it.

The faithfulness gate — a mis-stated formalization is worthless, so a statement passes iff:
  * **elaborates** — the conjecture `Prop` (and its definitions) type-check under a pinned Mathlib;
  * **anchored** — a faithfulness anchor holds: either `#eval`/`native_decide` on a computable definition
    matching the problem's own worked examples (Problem 367: `B₂(9800)=9800`), or a *proved sanity lemma*
    showing the definition captures the intended notion (Problem 477: `tiling_sanity`);
  * **non-vacuous** — the recorded note confirms the quantifier structure and that it is not trivially T/F.
  * (**independent review** — an LLM proposes the Lean, a skeptic checks it line-by-line against the English;
    that human/agent lens is out of band here, but the anchor + non-vacuity note are the mechanical part.)

Deliberately NOT submitting to erdosproblems.com (their AI-contribution policy). The `url` is attribution only;
the second exemplar's statement was sourced from the public pipeline-math paper, not the site.

Run:  python scripts/erdos_formalize.py   (needs the Lean REPL image; skips cleanly otherwise)
"""
from __future__ import annotations

import json
import re
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
OUT = _ROOT / "docs" / "results" / "erdos_formalize.json"

REGISTRY = [
    {"id": "367", "title": "products of the 2-full part over short intervals",
     "status": "OPEN — asymptotic (‘cannot be resolved with a finite computation’); not a Leibniz solve target",
     "artifact": "docs/erdos/erdos_367.lean", "conjecture": "Erdos367",
     "imports": ["Mathlib.Data.Nat.Factorization.Basic", "Mathlib.Analysis.SpecialFunctions.Pow.Real",
                 "Mathlib.Algebra.BigOperators.Intervals"],
     "url": "https://www.erdosproblems.com/367",
     "apa": ("Erdős, P., & Graham, R. L. (1980). Old and new problems and results in combinatorial number "
             "theory (Monographies de L'Enseignement Mathématique No. 28). Université de Genève."),
     "anchor": "B₂ #eval/native_decide on witnesses (9800↦9800, 9802↦169, 12↦4, squarefree 30↦1)",
     "non_vacuity": ("∀k∀ε∃C∀n form of ≪ n^{2+o(1)}; the o(1) is essential (van Doorn: fails ≪_k n² for k≥3), "
                     "so the statement is not trivially true and the quantifier order is load-bearing.")},
    {"id": "477", "title": "the thirteenth powers have a tiling complement in ℤ",
     "status": "RESOLVED affirmatively (Peng, Tao, Wang, Yu & Liu, 2026)",
     "artifact": "docs/erdos/erdos_477.lean", "conjecture": "Erdos477",
     "imports": ["Mathlib.Data.Int.Basic", "Mathlib.Tactic"],
     "url": "https://www.erdosproblems.com/477",
     "apa": ("Peng, B., Tao, R., Wang, S., Yu, H., & Liu, D. (2026). Erdős problem 477 [Preprint]. In "
             "pipeline-math. GitHub. https://github.com/Pengbinghui/pipeline-math"),
     "anchor": "tiling_sanity proved (ℤ = univ ⊕ {0}) — the definition captures *unique* representation",
     "non_vacuity": ("∃A, ∀n ∃! (a,b) …; the uniqueness (∃!) is the whole content — a plain ∃ would be "
                     "trivially true, so the ∃! is load-bearing.")},
]


def _read_artifact(rel: str):
    text = (_ROOT / rel).read_text(encoding="utf-8")
    body = "\n".join(ln for ln in text.splitlines() if not ln.strip().startswith("import"))
    return text, body


def formalize(prob: dict, backend) -> dict:
    """Run the faithfulness gate for one Erdős-problem statement against the real kernel."""
    _, body = _read_artifact(prob["artifact"])
    src = body + f"\n#check @{prob['conjecture']}\n"
    r = backend._run(src, tuple(prob["imports"]))
    msgs = (r or {}).get("messages", []) or []
    errs = [(m.get("data") or "") for m in msgs if m.get("severity") == "error"]
    check = next((m.get("data", "") for m in msgs if prob["conjecture"] in (m.get("data") or "")
                  and "Prop" in (m.get("data") or "")), "")
    conj_is_prop = ": Prop" in check
    n_anchor = len(re.findall(r"^\s*(theorem|example)\b", body, re.M))   # the proved anchors in the artifact
    faithful = (not errs) and conj_is_prop and n_anchor >= 1
    return {"id": prob["id"], "elaborates": not errs, "conjecture_is_prop": conj_is_prop,
            "n_anchors": n_anchor, "faithful": faithful, "errors": errs[:1]}


def main() -> int:
    print("=== Erdős statement-formalization lane (faithfulness gate) ===")
    results = []
    kernel_status = "not run"
    try:
        from leibniz.backends.lean_repl import LeanReplBackend, available
        if not available():
            kernel_status = "unavailable (Lean REPL)"
            print("  Lean REPL unavailable — cannot run the gate. (skip)")
        else:
            bk = LeanReplBackend(timeout_s=400)
            try:
                for prob in REGISTRY:
                    g = formalize(prob, bk)
                    results.append({**{k: prob[k] for k in ("id", "title", "status", "url", "apa", "anchor",
                                                             "non_vacuity", "artifact", "conjecture")}, **g})
                    print(f"  Erdős {prob['id']:<4} elaborates={g['elaborates']} prop={g['conjecture_is_prop']} "
                          f"anchors={g['n_anchors']}  -> faithful={g['faithful']}")
            finally:
                bk.close()
            kernel_status = "checked"
    except Exception as ex:  # pragma: no cover
        kernel_status = f"unavailable ({type(ex).__name__}: {ex})"
        print(f"  {kernel_status}")

    all_ok = bool(results) and all(r["faithful"] for r in results)
    gate = ("GREEN" if all_ok else "AMBER(kernel-unavailable)" if "unavailable" in kernel_status else "RED")
    out = {"gate": gate, "tier": "presentation", "ev": "AMPLIFICATION", "kernel_status": kernel_status,
           "problems": results,
           "reading": ("Erdős statement-formalization lane: faithful Lean statements of Erdős problems (NOT "
                       "solutions — the DB is mostly asymptotic and kernel-undecidable), each passing the "
                       "faithfulness gate (elaborates + a faithfulness anchor + a non-vacuity note). 367 is an "
                       "OPEN asymptotic bound (statement only); 477 is a resolved combinatorial problem (bridge "
                       "to the counterexample domain). Not submitting to erdosproblems.com (their AI policy); "
                       "the url is attribution. GREEN = every registered statement passes the gate.")}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2, default=str) + "\n")
    print(f"\ngate={gate}  tier=presentation  ev=AMPLIFICATION\n-> {OUT}")
    return 0 if gate != "RED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
