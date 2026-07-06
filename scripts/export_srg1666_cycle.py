"""Emit the kernel-attested AUDIT of the Belousova-Makhnev-Tokbaeva (2026) srg(1666,105,0,7)
non-existence proof as a Codex Calculemus cycle (ADR 0017). New domain: spectral / algebraic
graph theory (strongly regular graphs). Producer only.

Run:  python scripts/export_srg1666_cycle.py [-o FILE]
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from leibniz.calculemus_site import cycle_payload, downloadable_artifact  # noqa: E402

_ROOT = Path(__file__).resolve().parent.parent
_CERT = _ROOT / "docs" / "crt" / "srg1666_audit.lean"

_SUMMARY = (
    "An audit, in a domain new to the ledger -- spectral / algebraic graph theory (strongly regular graphs) -- "
    "of a 2026 non-existence proof, independently re-decided from first principles and kernel-attested. "
    "Belousova, Makhnev & Tokbaeva (Vestnik Perm. Univ. 1(72), 2026, 29-34) prove that srg(1666,105,0,7) does "
    "not exist by ruling out its bipartite double, the distance-regular graph with intersection array "
    "{105,104,98,7,1;1,7,98,104,105} (3332 vertices), via triple intersection numbers. srg(1666,105,0,7) is the "
    "smallest feasible triangle-free srg with mu=7 (Biggs' k=49s^2+49s+7 family, s=1) -- a long-standing "
    "feasible-but-open parameter set, beyond every published table. Leibniz reconstructs the whole argument in "
    "exact rational arithmetic from the array alone: Lemmas 1-3 reproduce exactly (the intersection numbers, the "
    "dual eigenmatrix, the Krein parameters, the unique Lemma-2 triple solution and the one-parameter Lemma-3 "
    "family r1 in {0..7}), catching one typo (Lemma 1 prints p^2_33=543; it is forced to 1461 by duality and a "
    "row sum). But the proof of Theorem 1 does NOT establish non-existence: its contradiction compares two "
    "computations of the mean lambda of the auxiliary graph Lambda (the distance-2 graph on Gamma_2(u), "
    "p^2_22=1461-regular on 1560 vertices), and with correct arithmetic BOTH equal 1999388/1461. The printed gap "
    "(1362.905 vs 1368.09) is an artifact of two compensating errors -- using 104 for the true non-neighbour "
    "count 1560-1-1461=98, and dividing by 1560 instead of the degree 1461 -- with the structural identity "
    "[222]+[224]=1364+97=1461=p^2_22 forcing S1=S2. The triple-intersection method leaves the array feasible: "
    "every metric base triple (with all 81 zero-Krein equations) has a non-negative integer solution, and the "
    "all-distance-2 config has exactly 8. This is corroborated by the canonical tool the authors cite, sage-drg "
    "(check_feasible clean; all deeper checks pass; tripleSolution_generator(2,2,2) -> 8 solutions; no "
    "zero-solution config; it too reports p^2_33=1461), and by three further independent from-scratch "
    "reconstructions. The Lean 4.31 kernel re-decides the finite core (plain decide): the two mean-lambda sums "
    "are equal, the structural identity, the paper's 104 manufactures the gap, all 8 Lemma-3 witnesses satisfy "
    "every marginal + zero-Krein equation + non-negativity, the Lemma-2 witness is valid, and r1=8 is rejected "
    "(a negative control). #print axioms at most [propext]; no native_decide, no sorry. Report-only, audit tier. "
    "CONCLUSION: the given proof does not decide the parameter set; srg(1666,105,0,7) should be treated as OPEN. "
    "This is an audit of a proof's validity, NOT a claim that the graph exists or does not exist. LLMs propose "
    "nothing; exact arithmetic and the kernel decide."
)

_FINDINGS = [
    {"id": "lemmas-reproduced", "claim": "Lemmas 1-3 reproduce exactly from the intersection array (one typo caught)",
     "verdict": "CERTIFIED",
     "note": "Intersection numbers, dual eigenmatrix Q, Krein parameters, the unique Lemma-2 triple solution and "
             "the one-parameter Lemma-3 family (r1 in {0..7}) all match. Lemma 1 prints p^2_33=543; the correct "
             "value is 1461, forced by the duality k_2 p^2_33=k_3 p^3_23 and the row sum p^2_31+p^2_33+p^2_35=1560."},
    {"id": "contradiction-vacuous", "claim": "The proof of Theorem 1 does not establish non-existence: its contradiction is arithmetically vacuous",
     "verdict": "CERTIFIED",
     "note": "The two computations of the mean lambda of Lambda are identically 1999388/1461 "
             "(1461*1460-98*1364 = 98*97+1461*1362). The printed gap (1362.905 vs 1368.09) comes from using 104 "
             "for the true non-neighbour count 98 and dividing by 1560 instead of the degree 1461; the identity "
             "[222]+[224]=1364+97=1461=p^2_22 forces S1=S2. Kernel-decided."},
    {"id": "method-feasible", "claim": "The triple-intersection method leaves the array feasible",
     "verdict": "CERTIFIED",
     "note": "Every metrically-valid base triple (with all 81 zero-Krein equations) has a non-negative integer "
             "solution; the all-distance-2 config has exactly 8. The kernel verifies all 8 Lemma-3 witnesses "
             "(marginals + zero-Krein + non-negativity) and the unique Lemma-2 witness, and rejects r1=8. "
             "Corroborated by canonical sage-drg (8 solutions; no zero-solution config; check_feasible clean)."},
    {"id": "open-case", "claim": "srg(1666,105,0,7) is not decided by the given proof and should be treated as OPEN",
     "verdict": "REPORTED",
     "note": "This is an audit of the proof's validity, report-only. It does NOT claim the graph exists or does "
             "not exist. The group's method (triple intersection numbers + Krein equality) is the correct tool "
             "for this class; a corrected argument may recover the theorem. Nothing here sets kernel_verified."},
]

_ARTIFACTS = [
    downloadable_artifact(_CERT, cycle_id="cycle_000035", kind="lean-proof",
                          checker="Lean 4.31 kernel (plain decide, 6 theorems) + exact rational reconstruction",
                          result="srg1666_contradiction_vacuous + srg1666_row_identity + srg1666_paper_gap_from_104 "
                                 "(the two mean-lambda routes are equal; the paper's 104 manufactures the gap) + "
                                 "srg1666_lemma3_feasible + srg1666_lemma2_feasible (triple witnesses satisfy all "
                                 "marginals + zero-Krein + non-negativity) + srg1666_control_r1_8 (r1=8 rejected); "
                                 "#print axioms at most [propext]"),
]

_REFERENCES = [
    {"citation": ("Belousova, V. I., Makhnev, A. A., & Tokbaeva, A. A. (2026). A strongly regular graph with "
                  "parameters (1666, 105, 0, 7) does not exist. Bulletin of Perm University. Mathematics. "
                  "Mechanics. Computer Science, 1(72), 29-34."),
     "url": "https://doi.org/10.17072/1993-0550-2026-1-29-34"},
    {"citation": ("Biggs, N. (2009). Families of parameters for SRNT graphs (arXiv:0911.2455)."),
     "url": "https://arxiv.org/abs/0911.2455"},
    {"citation": ("Coolsaet, K., & Jurisic, A. (2008). Using equality in the Krein conditions to prove "
                  "nonexistence of certain distance-regular graphs. Journal of Combinatorial Theory, Series A, "
                  "115(6), 1086-1095."),
     "url": "https://doi.org/10.1016/j.jcta.2007.12.001"},
    {"citation": ("Vidali, J. (2018). Using triple intersection numbers to prove non-existence of distance-regular "
                  "graphs. Electronic Journal of Combinatorics, 25(4), P4.21."),
     "url": "https://doi.org/10.37236/7763"},
]

_REPOSITORIES = [
    {"name": "elementalcollision/leibniz-daemon (srg(1666,105,0,7) audit)",
     "url": "https://github.com/elementalcollision/leibniz-daemon",
     "role": "produced",
     "note": "docs/crt/srg1666_audit.lean + scripts/verify_srg1666.py (exact reconstruction of Lemmas 1-3, the "
             "vacuity of the contradiction, and the triple-intersection feasibility witnesses; Lean 4.31 decide)"},
    {"name": "jaanos/sage-drg",
     "url": "https://github.com/jaanos/sage-drg",
     "role": "audited",
     "note": "the canonical triple-intersection tool cited by the paper; run on this array it reports the graph "
             "feasible (check_feasible clean; tripleSolution_generator(2,2,2) -> 8 solutions)."},
]

_TARGET = "elementalcollision/codex-calculemus : ledger/calculemus.json -> cycles[]"


def build_cycle() -> dict:
    return cycle_payload(
        cycle=35, date="2026-07-06",
        domain="Spectral / algebraic graph theory (strongly regular graphs)", kind="audit",
        title="Kernel-attested audit: the srg(1666,105,0,7) non-existence proof does not decide the case (Belousova-Makhnev-Tokbaeva 2026)",
        summary=_SUMMARY, findings=_FINDINGS, artifacts=_ARTIFACTS, references=_REFERENCES,
        repositories=_REPOSITORIES)


def build_fragment(*, generated_at: str = "") -> dict:
    return {"meta": {"generated_at": generated_at, "producer": "scripts/export_srg1666_cycle.py",
                     "target": _TARGET,
                     "merge": "append to cycles[]; copy docs/crt/srg1666_audit.lean to public/artifacts/cycle_000035/."},
            "cycles": [build_cycle()]}


def main(argv: list[str]) -> int:
    stamp = (argv[argv.index("--generated-at") + 1] if "--generated-at" in argv
             else datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
    text = json.dumps(build_fragment(generated_at=stamp), indent=2, ensure_ascii=False) + "\n"
    if "-o" in argv:
        Path(argv[argv.index("-o") + 1]).write_text(text)
        print(f"wrote (target: {_TARGET})")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
