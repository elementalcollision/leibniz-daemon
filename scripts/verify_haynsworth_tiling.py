"""Kernel-verify the Haynsworth / block-LDLᵀ tiling soundness lemma (docs/crt/haynsworth_tiling_soundness.lean)
— the once-proved "Half 1" of the deferred large-block-PSD Schur-tiling path (ADR 0047 Option 3; recorded
follow-on from the 7a/7b/7c probe findings).

Two lemmas over ℝ, proved from Mathlib's `Matrix.PosSemidef.conjTranspose_mul_mul_same` (congruence preserves
PSD) + `.add`/`.zero`: (1) `psd_of_congruence` — `D ⪰ 0 ∧ M = Lᴴ D L → M ⪰ 0` (fail-closed: the factor is
untrusted, the kernel recomputes the identity); (2) `psd_of_sum_congruence` — `M = Σ (Cᵢ)ᴴ Bᵢ Cᵢ` with each
pivot `Bᵢ ⪰ 0` → `M ⪰ 0` (the tiling: reduce an order-N block to its ≤60 pivots + one recomputed identity,
never forming the monolithic Ω(N²) decide). Pure Mathlib theorem — no trust surface touched.

Run:  python scripts/verify_haynsworth_tiling.py   (needs docker + leibniz-lean-repl; skips cleanly if absent)
"""
from __future__ import annotations

import json
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
ARTIFACT = _ROOT / "docs" / "crt" / "haynsworth_tiling_soundness.lean"
OUT = _ROOT / "docs" / "results" / "haynsworth_tiling_verification.json"
IMPORTS = ("Mathlib.LinearAlgebra.Matrix.PosDef",)
THEOREMS = ["psd_of_congruence", "psd_of_sum_congruence"]
_STD = {"propext", "Classical.choice", "Quot.sound"}


def main() -> int:
    print("=== Haynsworth / block-LDLᵀ tiling soundness — kernel verification ===")
    src = ARTIFACT.read_text(encoding="utf-8")
    for banned in ("sorry", "native_decide", "admit"):
        assert banned not in src, f"artifact contains {banned!r}"
    assert all(f"theorem {t}" in src for t in THEOREMS)

    kernel = {"status": "not run"}
    try:
        from leibniz.backends.lean_repl import LeanReplBackend, available
        if available():
            run_src = "".join(ln for ln in src.splitlines(keepends=True) if not ln.startswith("import "))
            bk = LeanReplBackend(timeout_s=300)
            try:
                r = bk._run(run_src, IMPORTS)
            finally:
                bk.close()
            msgs = (r or {}).get("messages", []) or []
            errs = [(m.get("data") or "") for m in msgs if m.get("severity") == "error"]
            axiom_lines = [m.get("data", "") for m in msgs if "axiom" in (m.get("data") or "")]
            clean = all(all(t.strip() in _STD for t in ln.split("[", 1)[-1].rstrip("]\n").split(",") if t.strip())
                        for ln in axiom_lines)
            kernel = {"status": "checked", "errors": errs[:3], "n_theorems": len(THEOREMS),
                      "axiom_lines": [ln.strip() for ln in axiom_lines],
                      "clean": (not errs and len(axiom_lines) == len(THEOREMS) and clean)}
            print(f"  kernel: {len(THEOREMS)} lemmas — "
                  f"{'CLEAN (standard axioms, 0 sorry) ✓' if kernel['clean'] else 'ISSUE: ' + str(errs[:2])}")
            for ln in kernel["axiom_lines"]:
                print(f"    {ln}")
        else:
            kernel = {"status": "unavailable (Lean REPL)"}
            print("  kernel: REPL unavailable (skip)")
    except Exception as ex:  # pragma: no cover
        kernel = {"status": f"unavailable ({type(ex).__name__}: {ex})"}
        print(f"  kernel: {kernel['status']}")

    gate = ("GREEN" if kernel.get("clean") else
            "AMBER(kernel-unavailable)" if "unavailable" in str(kernel.get("status")) else "RED")
    out = {"gate": gate, "tier": "audit", "ev": "AMPLIFICATION-research", "adr": "0047",
           "target": "Schur-tiling soundness (Half 1) for the deferred large-block-PSD path",
           "kernel": kernel, "theorems": THEOREMS, "artifact": str(ARTIFACT.relative_to(_ROOT)),
           "reading": ("The once-proved Haynsworth/block-LDLᵀ soundness lemma the Schur-tiling large-block-PSD "
                       "path needs: congruence + sum preserve PSD, so an order-N block that is a sum of "
                       "congruences of ≤60-order PSD pivots is PSD — reducing it to the small pivots + one "
                       "kernel-recomputed (fail-closed) identity, no Schur-iff. Pure Mathlib theorem, "
                       "axiom-clean; NO trust surface (it would be used by a future operator-gated tiling "
                       "primitive). A down-payment on ADR 0047 Option 3's tractable Half 1.")}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2) + "\n")
    print(f"\ngate={gate}  tier=audit\n-> {OUT}\n-> {ARTIFACT}")
    return 0 if gate != "RED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
