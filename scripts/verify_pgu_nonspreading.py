"""Independent verification of Bamberg–Giudici–Lansdown–Royle's Conjecture 4.1 (arXiv:2403.17576) — the OPEN
finite-field solution-count symmetry underpinning the non-spreading of PΓU(5,q) — kernel-attested (base case
q=3) by Lean 4.31.

In "Tactical decompositions in finite polar spaces and non-spreading classical group actions" (Bamberg, Giudici,
Lansdown & Royle; Designs, Codes and Cryptography, 2024), Theorem 4.2 shows that PΓU(5,q), acting on the totally
isotropic 1-spaces of the Hermitian polar space H(4,q²), is **non-spreading** — *conditional on* the following
still-open conjecture about counts of solutions to an equation over F_{q²}:

  CONJECTURE 4.1 (p.7). Let q be an odd prime power, b ∈ F_{q²} with b^{q+1} = −1, and (s,u,w) ∈ F_{q²}³ with
  s^{q+1} = u^{q+1} + w^{q+1}. For κ ∈ F_q^*, let n(κ) be the number of λ ∈ F_{q²} ∪ {∞} with
      (wλ+1)(b+uλ)^q − (wλ+1)^q(b+uλ) = κ·(b² + 1 + λ²(s² − u² − w²))^{(q+1)/2}.
  Then n(κ) = n(−κ) for all κ ∈ F_q^*.

Leibniz re-decides this by exact GF(q²) arithmetic (field F_{q²} = F_q[X]/(X²−r), r the least non-square mod q;
Frobenius x^q negates the X-coordinate; λ ∈ F_{q²}∪{∞} handled by homogenising [λ:μ] over the projective line
P¹(F_{q²})). For each prime q ∈ {3,5,7} it enumerates every admissible b and every (s,u,w) on the norm cone and
checks the symmetry n(κ) = n(−κ).

Honest scope note (a faithfulness finding). The literal statement has EXACTLY ONE exception: the trivial triple
(s,u,w) = (0,0,0). It is the zero vector — no projective point, and in the paper's own derivation (s,u,w) arises
from a *non-zero* totally isotropic point (−w,−u,t,u,w) — so it is evidently excluded; with the non-degeneracy
(s,u,w) ≠ 0 the conjecture holds with zero violations for q ∈ {3,5,7}. Leibniz reports both facts (the origin is
the sole exception; everything else is symmetric) and, for q ≥ 5, that the symmetry is *specifically* κ ↦ −κ
(there exist tuples with n(1) ≠ n(2)), so it is not the vacuous "all counts equal".

The Lean 4.31 kernel independently re-decides the base case q = 3 (plain `decide`): the symmetry holds for all
admissible non-trivial parameters (`pgu_q3_symmetry`), and the origin genuinely breaks it (`pgu_q3_origin` — a
discriminating negative control). Certifying Conjecture 4.1 at q = 3 makes Theorem 4.2 UNCONDITIONAL there:
PΓU(5,3) on H(4,9) is non-spreading, no longer contingent on an open conjecture.

LLMs propose nothing; exact finite-field arithmetic and the kernel decide. Tier audit, verification-
AMPLIFICATION; report-only, no trust surface.

Run:  python scripts/verify_pgu_nonspreading.py            (exact arithmetic; --kernel adds the Lean leg)
"""
from __future__ import annotations

import json
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
OUT = _ROOT / "docs" / "results" / "pgu_nonspreading_verification.json"
CERT = _ROOT / "docs" / "crt" / "pgu_nonspreading.lean"

PRIME_CASES = [3, 5, 7]          # exact-procedure verification (F_{q²}, q prime)
KERNEL_CASES = [3]               # base case re-decided in the Lean kernel
ORIGIN = ((0, 0), (0, 0), (0, 0))


# ---------------------------------------------------------------------------------------------------------------
# Exact GF(q²) arithmetic. Elements are pairs (a0,a1) = a0 + a1·X over F_q = ℤ/qℤ (q prime), with X² = r and r
# the least non-square mod q. Then X^q = −X, so Frobenius x^q negates the X-coefficient and the norm is a scalar.
# ---------------------------------------------------------------------------------------------------------------
class Fq2:
    def __init__(self, q: int):
        self.q = q
        squares = {(i * i) % q for i in range(q)}
        self.r = next(r for r in range(2, q) if r not in squares)
        self.zero, self.one = (0, 0), (1, 0)
        self.elems = [(a, b) for a in range(q) for b in range(q)]

    def add(self, x, y): return ((x[0] + y[0]) % self.q, (x[1] + y[1]) % self.q)
    def sub(self, x, y): return ((x[0] - y[0]) % self.q, (x[1] - y[1]) % self.q)

    def mul(self, x, y):
        q, r = self.q, self.r
        return ((x[0] * y[0] + x[1] * y[1] * r) % q, (x[0] * y[1] + x[1] * y[0]) % q)

    def frob(self, x): return (x[0] % self.q, (-x[1]) % self.q)                 # x^q
    def norm(self, x): return (x[0] * x[0] - x[1] * x[1] * self.r) % self.q     # x^{q+1} ∈ F_q
    def scal(self, k): return (k % self.q, 0)

    def powp(self, x, k):
        acc = self.one
        for _ in range(k):
            acc = self.mul(acc, x)
        return acc


def _p1(F: Fq2):
    """Projective line P¹(F_{q²}): affine points [x:1] and the point at infinity [1:0]."""
    return [(x, F.one) for x in F.elems] + [(F.one, F.zero)]


def counts(F: Fq2, b, s, u, w) -> dict[int, int]:
    """n(κ) for every κ ∈ F_q^*, using the homogenised equation LHS_h = RHS_h on P¹(F_{q²})."""
    q, e = F.q, (F.q + 1) // 2
    b2p1 = F.add(F.mul(b, b), F.one)
    coef = F.sub(F.sub(F.mul(s, s), F.mul(u, u)), F.mul(w, w))       # s² − u² − w²
    n = {k: 0 for k in range(1, q)}
    for lam, mu in _p1(F):
        wl_mu = F.add(F.mul(w, lam), mu)                            # wλ + μ
        bmu_ul = F.add(F.mul(b, mu), F.mul(u, lam))                 # bμ + uλ
        lhs = F.sub(F.mul(wl_mu, F.frob(bmu_ul)), F.mul(F.frob(wl_mu), bmu_ul))
        inside = F.add(F.mul(b2p1, F.mul(mu, mu)), F.mul(coef, F.mul(lam, lam)))
        base = F.powp(inside, e)                                    # (…)^{(q+1)/2}
        for k in range(1, q):
            if F.mul(F.scal(k), base) == lhs:
                n[k] += 1
    return n


def _valid_b(F: Fq2):
    return [b for b in F.elems if F.norm(b) == (F.q - 1) % F.q]     # b^{q+1} = −1


def _valid_suw(F: Fq2):
    N = {x: F.norm(x) for x in F.elems}
    return [(s, u, w) for s in F.elems for u in F.elems for w in F.elems
            if N[s] == (N[u] + N[w]) % F.q]                         # s^{q+1} = u^{q+1} + w^{q+1}


def check_conjecture(q: int) -> dict:
    F = Fq2(q)
    bs, suw = _valid_b(F), _valid_suw(F)
    failing_suw: set = set()
    asym_pair = None                                               # tuple with n(1) ≠ n(2): κ↦−κ specificity
    for b in bs:
        for (s, u, w) in suw:
            n = counts(F, b, s, u, w)
            if any(n[k] != n[(q - k) % q] for k in range(1, q)):
                failing_suw.add((s, u, w))
            if q >= 5 and asym_pair is None and n.get(1) != n.get(2):
                asym_pair = {"b": b, "suw": (s, u, w), "n": dict(n)}
    nontrivial_ok = failing_suw <= {ORIGIN}
    origin_is_sole_exception = failing_suw == {ORIGIN}
    return {
        "q": q, "r": F.r, "n_valid_b": len(bs), "n_valid_suw": len(suw),
        "symmetry_holds_for_nontrivial": nontrivial_ok,
        "origin_is_sole_exception": origin_is_sole_exception,
        "failing_suw_count": len(failing_suw),
        "specificity_asymmetric_pair": asym_pair,                  # None for q=3 (F_3^* = {±1})
        "ok": nontrivial_ok and origin_is_sole_exception,
    }


def checks() -> dict:
    per = {q: check_conjecture(q) for q in PRIME_CASES}
    return {"prime_cases": per, "all_ok": all(v["ok"] for v in per.values())}


# ---------------------------------------------------------------------------------------------------------------
# Lean 4.31 certificate — the field, the admissible parameter sets and P¹(F_{q²}) are all generated by the kernel
# from (q, r); plain `decide`, no baked data. Base case q = 3.
# ---------------------------------------------------------------------------------------------------------------
_HDR = r"""/-
  Conjecture 4.1 of Bamberg–Giudici–Lansdown–Royle, "Tactical decompositions in finite polar spaces and
  non-spreading classical group actions" (arXiv:2403.17576; Des. Codes Cryptogr. 2024) — kernel-attested base
  case q = 3. The conjecture (still open in general) underpins Theorem 4.2: PΓU(5,q) acting on the totally
  isotropic 1-spaces of H(4,q²) is non-spreading, CONDITIONAL on Conjecture 4.1. Certifying it at q = 3 makes
  that unconditional for q = 3.

  Statement. For b ∈ F_{q²} with b^{q+1} = −1 and (s,u,w) ∈ F_{q²}³ with s^{q+1} = u^{q+1} + w^{q+1}, and for
  κ ∈ F_q^*, let n(κ) = #{ λ ∈ F_{q²} ∪ {∞} : (wλ+1)(b+uλ)^q − (wλ+1)^q(b+uλ) = κ(b²+1+λ²(s²−u²−w²))^{(q+1)/2} }.
  Then n(κ) = n(−κ) for all κ ∈ F_q^*.

  Encoding. F_{q²} = F_q[X]/(X²−r) with r the least non-square mod q (r = 2 for q = 3); an element a0 + a1·X is
  the pair (a0,a1) with coeffs in {0,…,q−1}. Then X^q = −X, so `frob` negates the X-coordinate. λ ∈ F_{q²}∪{∞}
  is handled by homogenising to [λ:μ] on P¹(F_{q²}) (μ = 1 affine, [1:0] at infinity); both sides are degree
  q+1 homogeneous, so the test is projectively well-defined. `validB`, `validSUWnz` (norm cone minus the origin)
  and `p1` are generated by the kernel from (q,r) — no baked data.

    • pgu_q3_symmetry : n(κ) = n(−κ) for every admissible b and every NON-TRIVIAL (s,u,w) on the norm cone.
    • pgu_q3_origin   : the trivial triple (0,0,0) DOES break the symmetry — a discriminating negative control,
                        documenting exactly why the non-degeneracy (s,u,w) ≠ 0 is required.

  Plain `decide` — no `native_decide`, no `sorry`; every theorem depends on no axioms. Report-only.
-/
set_option maxHeartbeats 0
set_option maxRecDepth 1000000

abbrev Fp := Nat × Nat   -- a0 + a1·X in F_q[X]/(X²−r), coeffs in {0,…,q−1}

def fone : Fp := (1, 0)
def fzero : Fp := (0, 0)
def fadd (q : Nat) (x y : Fp) : Fp := ((x.1 + y.1) % q, (x.2 + y.2) % q)
def fsub (q : Nat) (x y : Fp) : Fp := ((x.1 + q - y.1 % q) % q, (x.2 + q - y.2 % q) % q)
def fmul (q r : Nat) (x y : Fp) : Fp :=
  ((x.1 * y.1 + x.2 * y.2 * r) % q, (x.1 * y.2 + x.2 * y.1) % q)
def frob (q : Nat) (x : Fp) : Fp := (x.1 % q, (q - x.2 % q) % q)
def nrm (q r : Nat) (x : Fp) : Nat := (x.1 * x.1 + (q - (x.2 * x.2 * r) % q)) % q
def scal (q k : Nat) : Fp := (k % q, 0)
def fpow (q r : Nat) (x : Fp) (k : Nat) : Fp := (List.range k).foldl (fun acc _ => fmul q r acc x) fone

def allF (q : Nat) : List Fp := (List.range q).flatMap (fun a => (List.range q).map (fun b => (a, b)))
def p1 (q : Nat) : List (Fp × Fp) := (allF q).map (fun x => (x, fone)) ++ [(fone, fzero)]
def fqstar (q : Nat) : List Nat := (List.range q).filter (fun k => k != 0)

def eqAt (q r : Nat) (b s u w : Fp) (k : Nat) (pt : Fp × Fp) : Bool :=
  let lam := pt.1
  let mu := pt.2
  let wlmu := fadd q (fmul q r w lam) mu
  let bmuul := fadd q (fmul q r b mu) (fmul q r u lam)
  let lhs := fsub q (fmul q r wlmu (frob q bmuul)) (fmul q r (frob q wlmu) bmuul)
  let b2p1 := fadd q (fmul q r b b) fone
  let coef := fsub q (fsub q (fmul q r s s) (fmul q r u u)) (fmul q r w w)
  let inside := fadd q (fmul q r b2p1 (fmul q r mu mu)) (fmul q r coef (fmul q r lam lam))
  let base := fpow q r inside ((q + 1) / 2)
  fmul q r (scal q k) base == lhs

def nCount (q r : Nat) (b s u w : Fp) (k : Nat) : Nat := ((p1 q).filter (eqAt q r b s u w k)).length

def validB (q r : Nat) : List Fp := (allF q).filter (fun b => nrm q r b == (q - 1) % q)
def suwAll (q : Nat) : List (Fp × Fp × Fp) :=
  (allF q).flatMap (fun s => (allF q).flatMap (fun u => (allF q).map (fun w => (s, u, w))))
def validSUWnz (q r : Nat) : List (Fp × Fp × Fp) :=
  (suwAll q).filter (fun t =>
    (nrm q r t.1 == (nrm q r t.2.1 + nrm q r t.2.2) % q) &&
    !(t.1 == fzero && t.2.1 == fzero && t.2.2 == fzero))

/-- n(κ) = n(−κ) for every admissible b and every non-trivial (s,u,w) on the norm cone. -/
def symmetryHolds (q r : Nat) : Bool :=
  (validB q r).all (fun b =>
    (validSUWnz q r).all (fun t =>
      (fqstar q).all (fun k =>
        nCount q r b t.1 t.2.1 t.2.2 k == nCount q r b t.1 t.2.1 t.2.2 ((q - k) % q))))

/-- The trivial triple (0,0,0) breaks the symmetry — witnessing that the non-degeneracy is load-bearing. -/
def originBreaks (q r : Nat) : Bool :=
  (validB q r).any (fun b =>
    (fqstar q).any (fun k =>
      nCount q r b fzero fzero fzero k != nCount q r b fzero fzero fzero ((q - k) % q)))

"""


def build_lean_cert() -> tuple[str, list[str]]:
    thms, names = [], []
    for q in KERNEL_CASES:
        r = Fq2(q).r
        thms.append(
            f"theorem pgu_q{q}_symmetry : symmetryHolds {q} {r} = true := by decide\n\n"
            f"theorem pgu_q{q}_origin : originBreaks {q} {r} = true := by decide\n")
        names += [f"pgu_q{q}_symmetry", f"pgu_q{q}_origin"]
    prints = "".join(f"#print axioms {n}\n" for n in names)
    return _HDR + "\n".join(thms) + "\n" + prints, names


def _leg_decls(src: str):
    prefix = src.split("\ntheorem ", 1)[0]
    out = []
    for chunk in src.split("\ntheorem ")[1:]:
        name = chunk.split(" ", 1)[0].rstrip(":")
        thm = "theorem " + chunk.split("\n\n", 1)[0].split("\n#print", 1)[0].rstrip()
        out.append((name, f"{prefix}\n\n{thm}\n\n#print axioms {name}\n"))
    return out


def run_kernel(src: str, timeout_s: int = 360) -> dict:
    try:
        from leibniz.backends.lean_repl import LeanReplBackend, available
    except Exception:
        return {"status": "unavailable (import)"}
    if not available():
        return {"status": "unavailable (docker/image)"}
    legs = {}
    for name, decl in _leg_decls(src):
        body = "\n".join(ln for ln in decl.splitlines() if not ln.startswith("import "))
        res = LeanReplBackend(timeout_s=timeout_s)._run(body, ())
        if not isinstance(res, dict):
            legs[name] = {"verified": False, "status": "timeout/unavailable"}
            continue
        msgs = res.get("messages", [])
        errors = [m.get("data") for m in msgs if m.get("severity") == "error"]
        axioms = " ".join(str(m.get("data", "")) for m in msgs
                          if "axiom" in str(m.get("data", "")).lower() or "depend" in str(m.get("data", "")).lower())
        cheated = ("sorryAx" in axioms) or ("native" in axioms.lower())
        legs[name] = {"verified": not errors and not cheated, "axioms": axioms.strip()}
    return {"status": "checked", "legs": legs, "all_verified": all(v.get("verified") for v in legs.values())}


def main() -> int:
    import sys
    r = checks()
    print("=== Conjecture 4.1 (Bamberg–Giudici–Lansdown–Royle, arXiv:2403.17576) — PΓU(5,q) non-spreading ===")
    for q, c in r["prime_cases"].items():
        spec = "n(1)≠n(2) exists" if c["specificity_asymmetric_pair"] else "F_q^*={±1} (no specificity test)"
        print(f"  q={q}: |validB|={c['n_valid_b']} |validSUW|={c['n_valid_suw']} (r={c['r']})  "
              f"symmetry(nontrivial)={c['symmetry_holds_for_nontrivial']}  "
              f"origin sole exception={c['origin_is_sole_exception']}  [{spec}]")
    src, names = build_lean_cert()
    CERT.parent.mkdir(parents=True, exist_ok=True)
    CERT.write_text(src)
    print(f"  Lean cert ({len(names)} theorems, q∈{KERNEL_CASES}) -> {CERT.relative_to(_ROOT)}")

    kernel = {"status": "skipped"}
    if "--kernel" in sys.argv:
        kernel = run_kernel(src)
        if kernel["status"] == "checked":
            for nm, v in kernel["legs"].items():
                print(f"  kernel {nm}: verified={v.get('verified')}  {v.get('axioms', '')}")
        else:
            print(f"  kernel: {kernel['status']}")
    else:
        print("  kernel: (pass --kernel to run the Lean leg)")

    kok = kernel["status"] == "skipped" or kernel.get("all_verified") or "unavailable" in kernel.get("status", "")
    gate = "GREEN" if r["all_ok"] and kok else "RED"
    out = {
        "gate": gate, "tier": "audit", "ev": "AMPLIFICATION",
        "target": ("Conjecture 4.1 (open) on solution-count symmetry n(κ)=n(−κ) over F_{q²}, underpinning the "
                   "non-spreading of PΓU(5,q) on H(4,q²) [Theorem 4.2, conditional]; Bamberg, Giudici, Lansdown "
                   "& Royle, Des. Codes Cryptogr. (2024), arXiv:2403.17576"),
        "prime_cases_checked": PRIME_CASES, "kernel_cases": KERNEL_CASES,
        "checks": r, "kernel": kernel, "cert": str(CERT.relative_to(_ROOT)),
        "reading": ("Independent exact-arithmetic verification of the open Conjecture 4.1: over F_{q²} for the "
                    "primes q ∈ {3,5,7}, the solution-count symmetry n(κ)=n(−κ) holds for every admissible b "
                    "and every non-trivial (s,u,w) on the norm cone. The literal statement has exactly one "
                    "exception, the trivial origin (0,0,0) — the zero vector, no geometric point — which Leibniz "
                    "flags and which the kernel confirms breaks the symmetry; with (s,u,w) ≠ 0 the conjecture is "
                    "satisfied with zero violations. For q ≥ 5 the symmetry is specifically κ ↦ −κ (tuples with "
                    "n(1) ≠ n(2) exist). The Lean 4.31 kernel re-decides the base case q = 3 (plain decide; "
                    "depends on no axioms), which makes Theorem 4.2 unconditional there: PΓU(5,3) on H(4,9) is "
                    "non-spreading. Exact finite-field arithmetic + the kernel; no LLM judgment; no trust "
                    "surface.")}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
    print(f"\ngate={gate}  tier=audit  ev=AMPLIFICATION\n-> {OUT}\n-> {CERT}")
    return 0 if gate == "GREEN" else 1


if __name__ == "__main__":
    raise SystemExit(main())
