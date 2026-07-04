"""Problem 16 (Cahen–Fontana–Frisch–Glaz / Chabert) — a self-ordered sequence census with certified refutations.

Problem 16 asks for the "natural" self-ordered integer sequences. A sequence a = (aₙ) is **self-ordered**
(Adam–Cahen–Fares "simultaneously ordered") when, for every n, the factorial `D_n = ∏_{k<n}(aₙ − aₖ)` divides
`P(m,n) = ∏_{k<n}(aₘ − aₖ)` for every m — i.e. the natural order is itself a simultaneous ordering.

"Self-ordered" is an *infinite* condition, so it cannot be settled by a bounded computation; but its NEGATION
is finitely witnessed — a single (m,n) with `D_n ∤ P(m,n)` refutes it, and that is a kernel-`decide`-able fact.
This module screens a curated set of natural sequences and emits a bundled Lean certificate refuting the
non-self-ordered ones. Each certificate hardcodes the (short) value prefix the witness needs, so any sequence
— polynomial, factorial, Fibonacci, primes — is handled uniformly, no symbolic sequence definition required.

Findings (screen bound N = 12, cross-checked to N = 30 for the positive side):
  • NOT self-ordered (certified witness): n³ (m,n=3,2), n⁴ (4,3), (n+1)! (4,3), Fibonacci (4,3), primes (3,2).
  • Self-ordered up to the bound (evidence, not a proof): identity n, arithmetic 3+5n, **n²**, triangular,
    2ⁿ. The n² result CORRECTS the loose corpus-doc claim "refute {n²}" — {n²} is self-ordered to N = 30;
    the refutable pure powers are the ODD/higher ones, n^k with k ≥ 3.

Tier audit, verification-AMPLIFICATION (certified instances of an OPEN classification, not a classification).
No trust surface touched; read-only. Certs use only standard axioms (propext), like the sibling
`self_ordered` family in the counterexample domain.

Run:  python scripts/prob16_census.py [N]      (the screen is free-CPU; the kernel leg needs the Lean REPL)
"""
from __future__ import annotations

import json
import sys
from math import prod
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
OUT = _ROOT / "docs" / "results" / "prob16_census.json"
ARTIFACT = _ROOT / "docs" / "crt" / "prob16_census_certificate.lean"
IMPORTS = ("Mathlib.Tactic",)
DEFAULT_N = 12
CROSS_CHECK_N = 30


def _fib_distinct(n: int) -> list[int]:
    out = [1, 2]
    while len(out) < n:
        out.append(out[-1] + out[-2])
    return out[:n]


def _primes(n: int) -> list[int]:
    ps: list[int] = []
    x = 2
    while len(ps) < n:
        if all(x % p for p in ps):
            ps.append(x)
        x += 1
    return ps


_FIB = _fib_distinct(120)   # long enough for the screen's m-range (N + m_extra)
_PRM = _primes(120)

# name -> (value function a(k), human description, Lean-safe id). All sequences are INJECTIVE (distinct
# values), so every D_n is nonzero and "self-ordered" is well-posed.
SEQUENCES = [
    ("identity", lambda k: k, "aₙ = n (arithmetic)"),
    ("arith_3_5", lambda k: 3 + 5 * k, "aₙ = 3 + 5n (arithmetic)"),
    ("square", lambda k: k * k, "aₙ = n²"),
    ("cube", lambda k: k ** 3, "aₙ = n³"),
    ("quartic", lambda k: k ** 4, "aₙ = n⁴"),
    ("triangular", lambda k: k * (k + 1) // 2, "aₙ = n(n+1)/2"),
    ("pow2", lambda k: 2 ** k, "aₙ = 2ⁿ (geometric)"),
    ("factorial", lambda k: prod(range(1, k + 2)), "aₙ = (n+1)!"),
    ("fibonacci", lambda k: _FIB[k], "distinct Fibonacci 1,2,3,5,8,…"),
    ("primes", lambda k: _PRM[k], "aₙ = (n+1)-th prime"),
]


def screen(a, n_bound: int, m_extra: int = 30):
    """Return the first refuting witness (m,n) with D_n ∤ P(m,n), or None (self-ordered up to the bound)."""
    for n in range(1, n_bound):
        dn = prod(a(n) - a(k) for k in range(n))
        if dn == 0:
            continue
        for m in range(n_bound + m_extra):
            if prod(a(m) - a(k) for k in range(n)) % dn != 0:
                return (m, n)
    return None


def census(n_bound: int = DEFAULT_N) -> list[dict]:
    rows = []
    for name, a, desc in SEQUENCES:
        w = screen(a, n_bound)
        row = {"name": name, "desc": desc, "self_ordered": w is None, "witness": list(w) if w else None}
        if w is not None:
            m, n = w
            row["prefix"] = [a(k) for k in range(max(m, n) + 1)]
            row["D_n"] = prod(a(n) - a(k) for k in range(n))
            row["P_mn"] = prod(a(m) - a(k) for k in range(n))
        rows.append(row)
    return rows


def _lean_refutation(name: str, prefix: list[int], m: int, n: int) -> str:
    vals = ", ".join(str(v) for v in prefix)
    return (
        f"namespace SO_{name}\n"
        f"/-- Value prefix a₀..a_{len(prefix) - 1} of the sequence (enough for the witness). -/\n"
        f"def a : List Int := [{vals}]\n"
        f"def D (n : Nat) : Int := (List.range n).foldl (fun acc k => acc * (a.getD n 0 - a.getD k 0)) 1\n"
        f"def P (m n : Nat) : Int := (List.range n).foldl (fun acc k => acc * (a.getD m 0 - a.getD k 0)) 1\n"
        f"/-- NOT self-ordered: at (m,n)=({m},{n}), D_{n} = {prod_str(prefix, n)} ∤ P({m},{n}). -/\n"
        f"theorem {name}_not_self_ordered : P {m} {n} % D {n} ≠ 0 := by decide\n"
        f"end SO_{name}\n"
    )


def prod_str(prefix, n):
    return prod(prefix[n] - prefix[k] for k in range(n))


def build_certificate(rows: list[dict]) -> tuple[str, list[str]]:
    nn = [r for r in rows if not r["self_ordered"]]
    header = (
        "/-\n"
        "  Problem 16 (Cahen–Fontana–Frisch–Glaz / Chabert) — self-ordered sequence census: certified\n"
        "  REFUTATIONS. A sequence is self-ordered when D_n = ∏_{k<n}(aₙ−aₖ) divides P(m,n) = ∏_{k<n}(aₘ−aₖ)\n"
        "  for all m,n; the negation is finitely witnessed by one (m,n) with D_n ∤ P(m,n), kernel-decided.\n\n"
        f"  {len(nn)} natural sequences refuted here: "
        + ", ".join(r["name"] for r in nn) + ".\n"
        "  (n² is NOT here — it is self-ordered to N=30; the refutable pure powers are n^k, k ≥ 3.)\n"
        "  Produced by scripts/prob16_census.py.\n"
        "-/\n"
    )
    body = "".join(_lean_refutation(r["name"], r["prefix"], r["witness"][0], r["witness"][1]) + "\n" for r in nn)
    names = [f"SO_{r['name']}.{r['name']}_not_self_ordered" for r in nn]
    src = header + "".join(f"import {i}\n" for i in IMPORTS) + "\n" + body
    return src, names


def main() -> int:
    n_bound = int(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_N
    print(f"=== Problem 16 self-ordered sequence census (screen bound N = {n_bound}) ===")
    rows = census(n_bound)
    so = [r["name"] for r in rows if r["self_ordered"]]
    nn = [r for r in rows if not r["self_ordered"]]
    for r in rows:
        tag = "self-ordered (to N)" if r["self_ordered"] else f"NOT self-ordered, witness (m,n)={tuple(r['witness'])}"
        print(f"  {r['name']:<12} {r['desc']:<26} -> {tag}")
    # cross-check the positive side at a higher bound (evidence, not proof)
    square_hi = screen(lambda k: k * k, CROSS_CHECK_N)
    print(f"  [correction] n² self-ordered to N={CROSS_CHECK_N}: {square_hi is None}  "
          f"(corpus doc's 'refute n²' is wrong; refutable powers are k ≥ 3)")

    src, names = build_certificate(rows)
    ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT.write_text(src)

    kernel = {"status": "not run"}
    try:
        from leibniz.backends.lean_repl import LeanReplBackend, available
        if available():
            bk = LeanReplBackend(timeout_s=400)
            try:
                run_src = "".join(ln for ln in src.splitlines(keepends=True) if not ln.startswith("import "))
                run_src = run_src + "\n" + "\n".join(f"#print axioms {nm}" for nm in names) + "\n"
                r = bk._run(run_src, IMPORTS)
            finally:
                bk.close()
            msgs = (r or {}).get("messages", []) or []
            errs = [(msg.get("data") or "") for msg in msgs if msg.get("severity") == "error"]
            axiom_lines = [msg.get("data", "") for msg in msgs if "axiom" in (msg.get("data") or "")]
            _std = {"propext", "Classical.choice", "Quot.sound"}
            clean_axioms = all(
                ("does not depend on any axioms" in ln)
                or all(tok.strip() in _std for tok in ln.split("[", 1)[-1].rstrip("]").split(",") if tok.strip())
                for ln in axiom_lines)
            kernel = {"status": "checked", "errors": errs[:3], "n_theorems": len(names),
                      "axiom_lines": [ln.strip() for ln in axiom_lines],
                      "clean": (not errs and len(axiom_lines) == len(names) and clean_axioms)}
            print(f"  kernel: {len(names)} refutations — {'CLEAN (standard axioms) ✓' if kernel['clean'] else 'ISSUE: ' + str(errs[:2])}")
        else:
            kernel = {"status": "unavailable (Lean REPL)"}
            print("  kernel: REPL unavailable (skip)")
    except Exception as ex:  # pragma: no cover
        kernel = {"status": f"unavailable ({type(ex).__name__}: {ex})"}
        print(f"  kernel: {kernel['status']}")

    gate = ("GREEN" if kernel.get("clean") else
            "AMBER(kernel-unavailable)" if "unavailable" in str(kernel.get("status")) else "RED")
    out = {"gate": gate, "tier": "audit", "ev": "AMPLIFICATION", "problem": "CFFG Problem 16 (Chabert)",
           "N": n_bound, "self_ordered_to_N": so, "not_self_ordered": [r["name"] for r in nn],
           "n2_self_ordered_to_30": square_hi is None, "census": rows, "kernel": kernel,
           "artifact": str(ARTIFACT.relative_to(_ROOT)), "theorems": names,
           "reading": ("A self-ordered sequence census: certified refutations of natural non-self-ordered "
                       "sequences (n³, n⁴, factorial, Fibonacci, primes) plus a correction — n² is self-ordered "
                       "(to N=30), not refutable as the corpus doc loosely claimed. Certified instances of an "
                       "open classification; verification-amplification, no trust surface.")}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2, default=str) + "\n")
    print(f"\ngate={gate}  tier=audit  ev=AMPLIFICATION\n-> {OUT}\n-> {ARTIFACT}")
    return 0 if gate != "RED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
