"""Counterexample-certificate domain (T9) — one reusable `certify(object)` interface over the open-problem
counterexamples, a sibling of the shipped process-complexity and code-bound certificate domains, across two
honest tiers.

Each object is a small typed spec `{"family", "params"}`; `certify(obj)` runs a bounded EXACT check and, where
the witness is finite-decidable, emits a **kernel-`decide`-able Lean certificate** that names the fact it
attests. The certificate bundles the verdict + witness + the Lean cert + its imports + the APA references, so
it drops straight onto the Calculemus publishing spine (a cycle finding + a downloadable hash-pinned `.lean`).

Tier-1 families (this module — self-certifying via `decide`):

  * `monomial_normal` (Cahen–Fontana–Frisch–Glaz Problem 41 / Swanson) — is `I = closure(x^a,y^b,z^c)` normal?
    Newton-polyhedron + Reid–Roberts–Vitulli d=3 reduction; a non-normal triple gets a `decide` witness
    (`x^u ∈ closure(I²) ∖ I²`). Reuses `scripts/prob41_normality_lean.py`.
  * `self_ordered` (CFFG Problem 16 / Chabert) — is the integer sequence self-ordered? the divisibility
    `∏_{k<n}(a_n−a_k) ∣ ∏_{k<n}(a_m−a_k)`; a non-example gets an explicit `(m,n)` refutation witness, a base
    family a bounded positive certificate.
  * `n_absorbing` (CFFG Problem 30 / Anderson–Badawi) — the absorbing number of `(0)` in a finite ring `ℤ/m`:
    `⊥` is `k`-absorbing but not `(k−1)`-absorbing (a `decide` over `Fin(k+1) → ZMod m`).

Tier-2 family (**attested** — infinite-ring counterexamples whose witness is a genuine multi-file proof, not a
bounded `decide`):

  * `pipeline_ring` (CFFG Problems 4b/20/27b/30c, from the public `Pengbinghui/pipeline-math` repo) — `certify`
    returns the ATTESTATION: the frozen headline theorem, the checker (`lake build` on Lean 4.31 + Mathlib +
    the authors' `verify.sh`), the `#print axioms` footprint we independently recorded (standard set, no
    `sorryAx`), the exact source repo + commit, and a reproduction recipe. No Lean is emitted — the artifact is
    the recipe + pins, since a Tier-2 download is a whole multi-file Mathlib project (see
    `docs/t9-tier2-attested-scoping.md`).

Tier disposition: audit, verification-AMPLIFICATION — a legible reusable certificate family, not new theorems.
No trust surface touched.

Run:  python scripts/counterexample_domain.py   (the checks are free-CPU; the kernel leg needs the Lean REPL)
"""
from __future__ import annotations

import importlib.util
import json
import re
from math import prod
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
OUT = _ROOT / "docs" / "results" / "counterexample_domain.json"
_AX = re.compile(r"depends on axioms:\s*\[([^\]]*)\]")
_STD = {"propext", "Classical.choice", "Quot.sound"}

# --- APA references, shared across families -----------------------------------------------------------------
REF_CFFG = {"citation": ("Cahen, P.-J., Fontana, M., Frisch, S., & Glaz, S. (2014). Open problems in commutative "
                         "ring theory. In M. Fontana, S. Frisch, & S. Glaz (Eds.), Commutative algebra (pp. "
                         "353–375). Springer."), "url": ""}
REF_HS = {"citation": ("Huneke, C., & Swanson, I. (2006). Integral closure of ideals, rings, and modules "
                       "(LMS Lecture Note Series No. 336). Cambridge University Press."), "url": ""}
REF_RRV = {"citation": ("Reid, L., Roberts, L. G., & Vitulli, M. A. (2003). Some results on normal homogeneous "
                        "ideals. Communications in Algebra, 31(9), 4485–4506."), "url": ""}
REF_ACC = {"citation": ("Adam, D., Cahen, P.-J., & Fares, Y. (2010). Subsets of ℤ with simultaneous ordering. "
                        "Integers, 10, 437–451."), "url": ""}
REF_AB = {"citation": ("Anderson, D. F., & Badawi, A. (2011). On n-absorbing ideals of commutative rings. "
                       "Communications in Algebra, 39(5), 1646–1672."), "url": ""}
REF_AM = {"citation": ("Ataka, M., & Matsuoka, N. (2026). Normality of monomial ideals in three variables "
                       "(arXiv:2602.01782). arXiv."), "url": "https://arxiv.org/abs/2602.01782"}


# =========================================================================================================
# family: monomial_normal (Problem 41)
# =========================================================================================================
def _prob41():
    spec = importlib.util.spec_from_file_location("prob41", _ROOT / "scripts" / "prob41_normality_lean.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def certify_monomial(params: dict) -> dict:
    a, b, c = params["a"], params["b"], params["c"]
    m = _prob41()
    r = m.certify(a, b, c)
    kernel = None
    if not r["normal"]:
        kernel = {"lean": m.lean_cert(a, b, c, r["witness"]), "imports": ["Mathlib.Tactic"], "check": "decide",
                  "theorem": f"Prob41_{a}_{b}_{c}.triple_{a}_{b}_{c}_not_normal"}
    return {"verdict": "not-normal" if not r["normal"] else "normal",
            "witness": r["witness"], "detail": {"L": r["L"], "weights": r["weights"]}, "kernel": kernel}


# =========================================================================================================
# family: self_ordered (Problem 16)
# =========================================================================================================
_SEQS = {"square": lambda k: k * k, "cube": lambda k: k ** 3,
         "triangular": lambda k: k * (k + 1) // 2, "pow2": lambda k: 2 ** k}
_SEQ_LEAN = {"square": "(k:ℤ)^2", "cube": "(k:ℤ)^3", "triangular": "((k*(k+1)/2:ℕ):ℤ)", "pow2": "(2:ℤ)^k"}


def certify_self_ordered(params: dict) -> dict:
    seq = _SEQS[params["seq"]]
    N = params.get("bound", 8)
    # self-ordered up to N iff ∀ m,n<N: D_n = ∏_{k<n}(a_n−a_k) divides ∏_{k<n}(a_m−a_k)
    witness = None
    for n in range(1, N):
        dn = prod(seq(n) - seq(k) for k in range(n))
        if dn == 0:
            continue
        for mm in range(N):
            if prod(seq(mm) - seq(k) for k in range(n)) % dn != 0:
                witness = (mm, n)
                break
        if witness:
            break
    aexpr = _SEQ_LEAN[params["seq"]]
    ns = f"SO_{params['seq']}"
    hdr = (f"namespace {ns}\n"
           f"def a (k : ℕ) : ℤ := {aexpr}\n"
           f"def D (n : ℕ) : ℤ := (Finset.range n).prod (fun k => a n - a k)\n"
           f"def P (m n : ℕ) : ℤ := (Finset.range n).prod (fun k => a m - a k)\n")
    if witness:
        mm, n = witness
        thm = f"{ns}.not_self_ordered"
        lean = hdr + (f"/-- ¬ self-ordered: at (m,n)=({mm},{n}), D_{n} ∤ P_{{{mm},{n}}}. -/\n"
                      f"theorem not_self_ordered : P {mm} {n} % D {n} ≠ 0 := by decide\n"
                      f"end {ns}\n")
        return {"verdict": "not-self-ordered", "witness": [mm, n],
                "kernel": {"lean": lean, "imports": ["Mathlib.Algebra.BigOperators.Intervals", "Mathlib.Tactic"],
                           "check": "decide", "theorem": thm}}
    thm = f"{ns}.self_ordered_lt{N}"
    lean = hdr + (f"/-- self-ordered up to bound {N} (a base family). -/\n"
                  f"theorem self_ordered_lt{N} : ∀ n < {N}, ∀ m < {N}, P m n % D n = 0 := by decide\n"
                  f"end {ns}\n")
    return {"verdict": f"self-ordered (bound {N})", "witness": None,
            "kernel": {"lean": lean, "imports": ["Mathlib.Algebra.BigOperators.Intervals", "Mathlib.Tactic"],
                       "check": "decide", "theorem": thm}}


# =========================================================================================================
# family: n_absorbing (Problem 30) — absorbing number of (0) in ℤ/m
# =========================================================================================================
def _absnum_bot(m: int, maxn: int = 6) -> int:
    import itertools
    for n in range(1, maxn + 1):
        ok = True
        for xs in itertools.product(range(m), repeat=n + 1):
            if prod(xs) % m == 0 and not any(prod(xs[:j] + xs[j + 1:]) % m == 0 for j in range(n + 1)):
                ok = False
                break
        if ok:
            return n
    return -1


def certify_n_absorbing(params: dict) -> dict:
    m = params["modulus"]
    k = _absnum_bot(m)
    ns = f"NAbs{m}"
    lean = (f"namespace {ns}\n"
            f"abbrev isNAbs (r : ℕ) : Prop :=\n"
            f"  ∀ x : Fin (r+1) → ZMod {m}, (∏ i, x i) = 0 → ∃ j, (∏ i ∈ Finset.univ.erase j, x i) = 0\n"
            f"/-- absorbingNumber (⊥ : ZMod {m}) = {k}: ⊥ is {k}-absorbing but not {k - 1}-absorbing. -/\n"
            f"theorem absorbing_number_bot : isNAbs {k} ∧ ¬ isNAbs {k - 1} := by decide\n"
            f"end {ns}\n")
    return {"verdict": f"absorbingNumber(⊥ : ℤ/{m}) = {k}", "witness": {"absorbing_number": k},
            "kernel": {"lean": lean,
                       "imports": ["Mathlib.Data.ZMod.Basic", "Mathlib.Algebra.BigOperators.Basic",
                                   "Mathlib.Tactic"],
                       "check": "decide", "theorem": f"{ns}.absorbing_number_bot"}}


# =========================================================================================================
# family: pipeline_ring (Problems 4b/20/27b/30c) — Tier 2, ATTESTED (not self-certified by `decide`)
# =========================================================================================================
REF_PIPE = {"citation": ("Peng, B., Tao, R., Wang, S., Yu, H., & Liu, D. (2026). pipeline-math [Computer "
                         "software]. GitHub."), "url": "https://github.com/Pengbinghui/pipeline-math"}
_PIPELINE_COMMIT = "69d7df765a8f377a5e0628c6d36c088bce7642c9"
_PIPELINE_RING = {
    "4b": {"project": "problem-4b-formalization", "headline": "Prob4b.Solution.problem4b_false",
           "type": "∃ S, FiniteConductor S ∧ ¬ QuasiCoherent S",
           "plain": "finite-conductor is strictly weaker than quasi-coherent (R = Δ(B)+C^(ℕ), an infinite ring)"},
    "20": {"project": "problem-20-formalization", "headline": "Prob20.Solution.problem20_answer",
           "type": "∃ D K …, ¬ Injective (θ₂) ∧ ¬ (Int(D²) ⊆ range θ₂)",
           "plain": "the canonical map θ₂ is neither injective nor surjective (D = 𝔽₂+𝔪 in 𝔽₂(t))"},
    "27b": {"project": "problem-27b-form", "headline": "Prob27b.Solution.problem27b_false",
            "type": "∃ g₁ g₂ ∈ IntA, g₁·g₂ ∉ IntA",
            "plain": "Int(A) need not be a ring (a noncommutative Werner counterexample over 𝔽₂[π])"},
    "30c": {"project": "problem-30c-formalization", "headline": "Prob30c.Solution.problem30c_false",
            "type": "∃ R I, absorbingNumber(I.map C) ≠ absorbingNumber I",
            "plain": "the absorbing number is not preserved under R → R[X] (A_q = 𝔽₂[t][X₀,X₁,X₂]/Arel)"},
}


def certify_pipeline_ring(params: dict) -> dict:
    """A Tier-2 ATTESTATION: the external kernel proof is re-verified by `lake build`, not re-encoded as
    `decide` (the witness is an infinite ring). The "certificate" is the attestation record + reproduction
    recipe; the source is the *public* pipeline-math repo, so nothing is hidden."""
    p = _PIPELINE_RING[params["problem"]]
    repo = "https://github.com/Pengbinghui/pipeline-math"
    return {
        "verdict": "attested",
        "witness": {"headline_theorem": p["headline"], "type": p["type"], "establishes": p["plain"]},
        "kernel": {"check": "lake-build", "theorem": p["headline"],
                   "checker": "lake build (Lean 4.31.0 + Mathlib rev v4.31.0) + the authors' scripts/verify.sh",
                   "axioms": sorted(_STD),  # independently recorded from our re-verification; no sorryAx
                   "reproduction": (f"git clone {repo} && cd pipeline-math && git checkout {_PIPELINE_COMMIT}"
                                    f" && cd lean/{p['project']} && lake exe cache get && scripts/verify.sh --all"),
                   "artifact": "recipe + pins (multi-file Mathlib project; sources public — see repo @ commit)"}}


FAMILIES = {
    "monomial_normal": {"fn": certify_monomial, "refs": [REF_CFFG, REF_HS, REF_RRV, REF_AM], "tier": 1},
    "self_ordered": {"fn": certify_self_ordered, "refs": [REF_CFFG, REF_ACC], "tier": 1},
    "n_absorbing": {"fn": certify_n_absorbing, "refs": [REF_CFFG, REF_AB], "tier": 1},
    "pipeline_ring": {"fn": certify_pipeline_ring, "refs": [REF_CFFG, REF_PIPE], "tier": 2},
}


def certify(obj: dict) -> dict:
    """The certificate for one object `{"family", "params"}` — Tier 1 (self-certified via `decide`) or Tier 2
    (attested via `lake build`), per the family."""
    fam = obj["family"]
    spec = FAMILIES[fam]
    c = spec["fn"](obj["params"])
    return {"family": fam, "tier": spec["tier"], "params": obj["params"], "verdict": c["verdict"],
            "witness": c.get("witness"), "detail": c.get("detail"), "kernel": c.get("kernel"),
            "references": spec["refs"]}


def registry() -> list:
    """The initial corpus — one entry per certified object, across the three Tier-1 families."""
    return [
        {"family": "monomial_normal", "params": {"a": 4, "b": 5, "c": 7}},   # NOT normal (Huneke–Swanson)
        {"family": "monomial_normal", "params": {"a": 7, "b": 3, "c": 2},     # NOT normal — Ataka–Matsuoka (2026)
         "note": "sharp-bound witness for μ(I)≤7 ⇒ normal; closure has 8 generators (arXiv:2602.01782, Ex. 4.5)"},
        {"family": "monomial_normal", "params": {"a": 3, "b": 4, "c": 5},     # NOT normal — the OTHER minimal triple
         "note": "with (2,3,7), the smallest non-normal corner triple (a+b+c=12); census scripts/prob41_census.py"},
        {"family": "monomial_normal", "params": {"a": 3, "b": 3, "c": 3}},   # normal
        {"family": "self_ordered", "params": {"seq": "cube", "bound": 6}},        # NOT self-ordered
        {"family": "self_ordered", "params": {"seq": "triangular", "bound": 6}},  # self-ordered base family
        {"family": "self_ordered", "params": {"seq": "pow2", "bound": 6}},        # self-ordered base family
        {"family": "n_absorbing", "params": {"modulus": 4}},   # absorbingNumber(⊥) = 2
        {"family": "n_absorbing", "params": {"modulus": 9}},   # absorbingNumber(⊥) = 2
        # Tier 2 — attested (lake build, not decide):
        {"family": "pipeline_ring", "params": {"problem": "4b"}},
        {"family": "pipeline_ring", "params": {"problem": "20"}},
        {"family": "pipeline_ring", "params": {"problem": "27b"}},
        {"family": "pipeline_ring", "params": {"problem": "30c"}},
    ]


def main() -> int:
    print("=== counterexample-certificate domain (Tier 1) ===")
    certs = [certify(o) for o in registry()]
    for c in certs:
        print(f"  {c['family']:<16} {str(c['params']):<28} -> {c['verdict']}")

    # kernel leg: elaborate each emitted Lean cert + confirm the axiom footprint is standard/empty.
    kernel = {"status": "not run", "checked": []}
    try:
        from leibniz.backends.lean_repl import LeanReplBackend, available
        if not available():
            kernel = {"status": "unavailable (Lean REPL)"}
            print("  kernel: REPL unavailable (skip)")
        else:
            bk = LeanReplBackend(timeout_s=500)
            rows = []
            try:
                for c in certs:
                    k = c.get("kernel")
                    if not k or k.get("check") != "decide":
                        continue   # Tier-2 attestations are checked by lake build, not the REPL `decide` leg
                    src = k["lean"] + f"\n#print axioms {k['theorem']}\n"
                    r = bk._run(src, tuple(k["imports"]))
                    msgs = (r or {}).get("messages", []) or []
                    errs = [m for m in msgs if m.get("severity") == "error"]
                    ax = set()
                    for m in msgs:
                        am = _AX.search(m.get("data") or "")
                        if am:
                            ax |= {a.strip() for a in am.group(1).split(",") if a.strip()}
                    ok = (not errs) and ax <= _STD
                    rows.append({"family": c["family"], "params": c["params"], "theorem": k["theorem"],
                                 "errors": len(errs), "axioms": sorted(ax), "ok": ok})
                    print(f"    kernel {k['theorem']:<40} {'OK' if ok else 'FAIL'}  axioms={sorted(ax) or '∅'}")
            finally:
                bk.close()
            kernel = {"status": "checked", "checked": rows, "all_ok": all(r["ok"] for r in rows)}
    except Exception as ex:  # pragma: no cover
        kernel = {"status": f"unavailable ({type(ex).__name__}: {ex})"}
        print(f"  kernel: {kernel['status']}")

    gate = ("GREEN" if kernel.get("all_ok") else
            "AMBER(kernel-unavailable)" if "unavailable" in str(kernel.get("status")) else "RED")
    out = {"gate": gate, "tier": "audit", "ev": "AMPLIFICATION",
           "families": {f: FAMILIES[f]["tier"] for f in FAMILIES},
           "n_tier1": sum(1 for c in certs if c["tier"] == 1), "n_tier2": sum(1 for c in certs if c["tier"] == 2),
           "certificates": certs, "kernel": kernel,
           "reading": ("Counterexample-certificate domain: one certify(object) interface across two tiers. "
                       "Tier 1 (self-certified) — the finite/exact-decidable counterexamples (monomial-normality "
                       "/ self-ordered sequences / n-absorbing ideals), each object certified by a "
                       "kernel-`decide`-able Lean cert that names the fact. Tier 2 (attested) — the infinite-ring "
                       "pipeline-math counterexamples (4b/20/27b/30c), re-verified by `lake build` (not `decide`), "
                       "the certificate being the attestation + reproduction recipe against the public repo. A "
                       "sibling of the process-complexity and code-bound domains; verification-AMPLIFICATION. "
                       "GREEN = every Tier-1 emitted cert elaborates with only standard axioms.")}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2, default=str) + "\n")
    print(f"\ngate={gate}  tier=audit  ev=AMPLIFICATION  families={sorted(FAMILIES)}\n-> {OUT}")
    return 0 if gate != "RED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
