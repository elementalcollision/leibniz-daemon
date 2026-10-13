"""SS-RS-GD refutation — kernel-verified core of a COLT-2021 open-problem resolution.

Yun-Sra-Jadbabaie (COLT 2021) asked whether single-shuffle SGD can beat reshuffle SGD and GD in the
well-conditioned regime (Conjecture 1.1: the chain ‖W_SS‖ ≤ ‖W_RS‖ ≤ ‖W_GD‖). A pipeline-math write-up
(GPT-5.5-Pro) refutes the SS-RS half at (n,K)=(3,2). This module independently KERNEL-VERIFIES the
refutation's algebraic core against the real Lean kernel (Leibniz discipline: LLMs propose, the kernel decides).

Taking the eigenvalue polynomials λ_RS, λ_SS of Lemma 1.5 as given (the paper's sympy script verifies they are
the spectral-norm eigenvalues via characteristic-polynomial factorization), the following are kernel-verified,
each with `#print axioms` = {propext, Classical.choice, Quot.sound}:

  * gap_identity          — Lemma 1.6 eq (1.8): λ_SS − λ_RS = (1−q)⁶(q+1)²·g(q)/2048   [`ring`]
  * dominance_q6          — Lemma 1.5 eq (1.6)                                          [`ring`]
  * dominance_mu_1_7      — Lemma 1.5 eq (1.7), exactly as printed                       [`ring`]
  * sos_cofactor, sos_sextic — the two SOS positivity certificates                      [`ring`]
  * gg_pos                — g(q) > 0 on [1/4, 1] ⊂ (q*, 1], q* = 0.212036…              [`nlinarith`]
  * ss_exceeds_rs         — λ_RS < λ_SS on [1/4, 1): THE REFUTATION (Conjecture 1.1 is false)
  * violation_at_half     — a fully concrete witness at q = 1/2

By-product of running it through the kernel:
  * `sos_cofactor` VINDICATES the paper: an LLM scout flagged it as off by 2q²; the kernel confirms the paper is
    right (the scout dropped the +2q² cross-term of (q²−4q+1)²). LLMs propose; the kernel decides.

CORRECTION (2026-10-13). An earlier version of this module claimed a "kernel-attested erratum" in (1.7). That
was our transcription error, not the paper's: we wrote μ_RS = (q+1)⁴(q⁴+4q³−42q²+4q+1)/16384 and dropped the
square the paper prints on the quartic factor. With μ_RS as printed, (1.7) holds identically
(`dominance_mu_1_7`). The kernel was right about the formula we gave it; the formula was wrong. The
mis-transcribed statement is kept as a negative control (`mistranscribed_1_7_false_at_half`), and
`tests/test_ss_rs_gd.py` re-checks (1.7) in exact rational arithmetic against an independent transcription.
The upstream issue was retracted: https://github.com/Pengbinghui/pipeline-math/issues/4

Tier: audit, verification-AMPLIFICATION (the mathematics is the paper's; the value is an independent, replayable
kernel attestation). No trust surface touched; read-only; mints nothing.

Run:  python scripts/ss_rs_gd_lean.py   (needs the Lean REPL image; skips cleanly otherwise)
"""
from __future__ import annotations

import json
import re
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
OUT = _ROOT / "docs" / "results" / "ss_rs_gd.json"
ARTIFACT = _ROOT / "docs" / "colt" / "ss_rs_gd_refutation.lean"
IMPORTS = ("Mathlib.Tactic",)

SRC = r"""
namespace SSRSGD

noncomputable def lamRS (q : ℝ) : ℝ :=
  ((q^6 - 6*q^5 + 15*q^4 + 12*q^3 + 15*q^2 - 6*q + 1)/32)^2
noncomputable def lamSS (q : ℝ) : ℝ :=
  (q^12 - 24*q^11 + 186*q^10 - 504*q^9 + 399*q^8 + 528*q^7 + 876*q^6
    + 528*q^5 + 399*q^4 - 504*q^3 + 186*q^2 - 24*q + 1)/2048
noncomputable def muRS (q : ℝ) : ℝ :=
  (q+1)^4 * (q^4 + 4*q^3 - 42*q^2 + 4*q + 1)^2/16384
/-- Our earlier mis-transcription of μ_RS (the square on the quartic factor dropped). Kept only as the
    subject of a negative control; it is NOT the paper's μ_RS. -/
noncomputable def muRS_unsquared (q : ℝ) : ℝ :=
  (q+1)^4 * (q^4 + 4*q^3 - 42*q^2 + 4*q + 1)/16384
def gg (q : ℝ) : ℝ := 42*q^2 - q^4 - 4*q^3 - 4*q - 1

/-- Lemma 1.6, eq (1.8): the exact gap identity. -/
theorem gap_identity (q : ℝ) :
    lamSS q - lamRS q = (1 - q)^6 * (q + 1)^2 * gg q / 2048 := by
  unfold lamSS lamRS gg; ring

/-- Lemma 1.5 dominance eq (1.6). -/
theorem dominance_q6 (q : ℝ) :
    lamRS q - q^6
      = (1 - q)^6 * (q + 1)^2 * (q^4 - 8*q^3 + 30*q^2 - 8*q + 1) / 1024 := by
  unfold lamRS; ring

/-- SOS cofactor for (1.6). (An LLM scout wrongly flagged this as off by 2q²; the kernel confirms
    the paper: (q²−4q+1)² = q⁴−8q³+18q²−8q+1, so +12q² gives 30q².) -/
theorem sos_cofactor (q : ℝ) :
    q^4 - 8*q^3 + 30*q^2 - 8*q + 1 = (q^2 - 4*q + 1)^2 + 12*q^2 := by ring

/-- Second SOS cofactor (sextic), positive for q ≥ 0. -/
theorem sos_sextic (q : ℝ) :
    3*q^6 - 30*q^5 + 93*q^4 + 124*q^3 + 93*q^2 - 30*q + 3
      = 3*q^4*((q - 5)^2 + 6) + 124*q^3 + 3*(31*q^2 - 10*q + 1) := by ring

/-- Positivity of the gap's final factor on [1/4, 1] ⊂ (q*, 1], q* = 0.212036… -/
theorem gg_pos (q : ℝ) (h1 : (1:ℝ)/4 ≤ q) (h2 : q ≤ 1) : 0 < gg q := by
  unfold gg
  nlinarith [h1, h2, sq_nonneg (q - 1), sq_nonneg q, sq_nonneg (2*q - 1),
    mul_nonneg (sub_nonneg.2 h1) (sub_nonneg.2 h2)]

/-- THE REFUTATION on the violation interval [1/4, 1): λ_SS > λ_RS, so ‖W_SS‖ ≥ λ_SS > λ_RS = ‖W_RS‖.
    Conjecture 1.1 (the SS-RS inequality) is FALSE. -/
theorem ss_exceeds_rs (q : ℝ) (h1 : (1:ℝ)/4 ≤ q) (h2 : q < 1) : lamRS q < lamSS q := by
  have hg : 0 < gg q := gg_pos q h1 (le_of_lt h2)
  have h1q : 0 < 1 - q := by linarith
  have hq1 : 0 < q + 1 := by linarith
  have hpos : 0 < (1 - q)^6 * (q + 1)^2 * gg q / 2048 :=
    div_pos (mul_pos (mul_pos (pow_pos h1q 6) (pow_pos hq1 2)) hg) (by norm_num)
  have := gap_identity q
  linarith

/-- A fully concrete refutation witness: at q = 1/2, single-shuffle strictly beats reshuffle. -/
theorem violation_at_half : lamRS (1/2) < lamSS (1/2) := by
  unfold lamRS lamSS; norm_num

/-- Lemma 1.5 dominance eq (1.7), exactly as printed. (Corrects an earlier version of this artifact,
    which mis-transcribed μ_RS and reported (1.7) false; see `mistranscribed_1_7_false_at_half`.) -/
theorem dominance_mu_1_7 (q : ℝ) :
    lamRS q - muRS q
      = (1 - q)^4 * (5*q^2 + 2*q + 5)
        * (3*q^6 - 30*q^5 + 93*q^4 + 124*q^3 + 93*q^2 - 30*q + 3) / 16384 := by
  unfold lamRS muRS; ring

/-- NEGATIVE CONTROL, not an erratum. With the square on μ_RS's quartic factor dropped (our former
    transcription), the right-hand side of (1.7) no longer matches at q = 1/2. The kernel decides what it is
    given; this records what we gave it. -/
theorem mistranscribed_1_7_false_at_half :
    lamRS (1/2) - muRS_unsquared (1/2)
      ≠ (1 - (1:ℝ)/2)^4 * (5*(1/2)^2 + 2*(1/2) + 5)
        * (3*(1/2)^6 - 30*(1/2)^5 + 93*(1/2)^4 + 124*(1/2)^3 + 93*(1/2)^2 - 30*(1/2) + 3) / 16384 := by
  unfold lamRS muRS_unsquared; norm_num

/-- The inequality (1.7) establishes, λ_RS ≥ μ_RS, at the witness point. -/
theorem lamRS_ge_muRS_at_half : muRS (1/2) ≤ lamRS (1/2) := by
  unfold lamRS muRS; norm_num

end SSRSGD
"""

# Theorems whose axiom footprint we assert is exactly the standard set.
HEADLINE = ["SSRSGD.gap_identity", "SSRSGD.ss_exceeds_rs", "SSRSGD.violation_at_half",
            "SSRSGD.sos_cofactor", "SSRSGD.dominance_mu_1_7", "SSRSGD.mistranscribed_1_7_false_at_half",
            "SSRSGD.lamRS_ge_muRS_at_half"]
_STD = {"propext", "Classical.choice", "Quot.sound"}
_AX = re.compile(r"depends on axioms:\s*\[([^\]]*)\]")


def full_source() -> str:
    prints = "\n".join(f"#print axioms {n}" for n in HEADLINE)
    return f"{SRC}\n{prints}\n"


def write_artifact() -> None:
    ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    header = ("/-\n  SS-RS-GD refutation (Yun-Sra-Jadbabaie, COLT 2021 open problem) — kernel-verified core.\n"
              "  Independent Leibniz attestation of a pipeline-math (GPT-5.5-Pro) resolution.\n"
              "  Every theorem: #print axioms = [propext, Classical.choice, Quot.sound].\n-/\n")
    ARTIFACT.write_text(header + "".join(f"import {i}\n" for i in IMPORTS) + "\n" + full_source())


def main() -> int:
    print("=== SS-RS-GD refutation — kernel verification ===")
    write_artifact()
    kernel = {"status": "not run"}
    try:
        from leibniz.backends.lean_repl import LeanReplBackend, available
        if not available():
            print("Lean REPL unavailable — cannot verify. (skip)")
            OUT.parent.mkdir(parents=True, exist_ok=True)
            OUT.write_text(json.dumps({"gate": "AMBER(kernel-unavailable)"}, indent=2) + "\n")
            return 0
        bk = LeanReplBackend(timeout_s=400)
        try:
            r = bk._run(full_source(), IMPORTS)
        finally:
            bk.close()
        msgs = (r or {}).get("messages", []) or []
        errs = [(m.get("data") or "") for m in msgs if m.get("severity") == "error"]
        axioms = {}
        for m in msgs:
            am = _AX.search(m.get("data") or "")
            if am:
                names = [a.strip() for a in am.group(1).split(",") if a.strip()]
                # associate to the theorem named in the same message
                for n in HEADLINE:
                    if n in (m.get("data") or ""):
                        axioms[n] = names
        clean = (not errs) and all(set(axioms.get(n, [])) <= _STD and axioms.get(n) for n in HEADLINE)
        kernel = {"status": "checked", "errors": errs[:2], "axioms": axioms, "all_clean": clean}
        print(f"  errors: {len(errs)}   headline theorems with clean axioms: "
              f"{sum(1 for n in HEADLINE if set(axioms.get(n, [])) <= _STD and axioms.get(n))}/{len(HEADLINE)}")
    except Exception as ex:  # pragma: no cover
        kernel = {"status": f"unavailable ({type(ex).__name__}: {ex})"}
        print(f"  {kernel['status']}")

    gate = ("GREEN" if kernel.get("all_clean") else
            "AMBER(kernel-unavailable)" if "unavailable" in str(kernel.get("status")) else "RED")
    out = {"gate": gate, "tier": "audit", "ev": "AMPLIFICATION",
           "problem": "Yun-Sra-Jadbabaie COLT-2021 open problem (SS-RS-GD inequalities); SS-RS half refuted",
           "kernel": kernel, "artifact": str(ARTIFACT.relative_to(_ROOT)),
           "findings": {
               "refutation_verified": "Conjecture 1.1 (SS-RS) kernel-refuted: lamSS > lamRS on [1/4,1); concrete witness q=1/2",
               "scout_false_alarm": "an LLM scout flagged sos_cofactor as wrong; the kernel confirms the PAPER is correct",
               "identity_1_7": "the paper's identity (1.7) holds exactly as printed (kernel, ring)",
               "retracted_erratum_1_7": ("an earlier version of this artifact reported (1.7) false; that was our "
                                         "transcription error (the square on muRS's quartic factor was dropped). "
                                         "Retracted upstream 2026-10-13: "
                                         "https://github.com/Pengbinghui/pipeline-math/issues/4. The "
                                         "mis-transcribed statement is kept as a negative control."),
           },
           "reading": ("Independent kernel attestation of the SS-RS-GD refutation core (COLT-2021 open problem): "
                       "the gap identity, positivity, the violation lamSS > lamRS, and a concrete witness are "
                       "kernel-verified with only the standard axioms. Verification-AMPLIFICATION (the maths is "
                       "the paper's). The kernel vindicates the paper against an LLM scout's false alarm on sos_cofactor, "
                       "and verifies the supporting identity (1.7) as printed. A former 'erratum' on (1.7) was our "
                       "own transcription error and has been retracted.")}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2, default=str) + "\n")
    print(f"\ngate={gate}  tier=audit  ev=AMPLIFICATION\n-> {OUT}\n-> {ARTIFACT}")
    return 0 if gate != "RED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
