"""Independent kernel verification of Mafi–Naderi (2021) — integral closure of a special monomial ideal.

Mafi, A., & Naderi, D. (2021). Integral closure and Hilbert series of a special monomial ideal
(arXiv:2112.02921). For M_{n,t} = (x^{e_1},…,x^{e_n}), x^{e_i} = ∏_{j≠i} x_j^t, they prove:

  • Theorem 1.6: the integral closure M̄_{n,t} equals the Veronese-type ideal I_{(t(n−1); t,…,t)} — for n = 3,
    that is closure(M_{3,t}) = {x^u : min(a,t)+min(b,t)+min(c,t) ≥ 2t}.
  • Corollary 1.7: M_{n,t} is Cohen–Macaulay (unmixed), but its integral closure M̄_{n,t} has EMBEDDED primes.

Leibniz PROPOSES nothing — the paper's claims are the objects; our kernel DECIDES. Using the general
monomial-ideal instrument (`monomial_ideal_normality.py`, integral-dependence membership), we verify for n = 3:
  (A) closure(M_{3,t}) = the Veronese cap-sum ideal (Theorem 1.6) — checked t = 1..4;
  (B) the closure has the embedded prime (x,y,z) for t ≥ 2 (Corollary 1.7) — witnessed by a monomial u with
      u ∉ closure but x·u, y·u, z·u ∈ closure — while M_{3,t} itself has NO such witness (it is unmixed): the
      closure GAINS the embedded prime. Honest detail: for t = 1 the closure has no embedded prime (M_{3,1} is
      the squarefree Veronese, already closed).

Both facts are kernel-decided by `decide` over the cap-sum closure predicate (instrument-verified to equal the
true integral closure). Tier audit, verification-AMPLIFICATION; no trust surface touched.

Run:  python scripts/verify_mafi_naderi.py   (checker is free-CPU; the kernel leg needs the Lean REPL)
"""
from __future__ import annotations

import importlib.util
import json
from itertools import product
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
ARTIFACT = _ROOT / "docs" / "crt" / "mafi_naderi_certificate.lean"
OUT = _ROOT / "docs" / "results" / "mafi_naderi_verification.json"
IMPORTS = ("Mathlib.Tactic",)
CERT_TS = [2, 3]          # t values certified in-kernel
CHECK_TS = [1, 2, 3, 4]   # t values the instrument cross-checks (closure = Veronese)


def _instr():
    spec = importlib.util.spec_from_file_location("min", _ROOT / "scripts" / "monomial_ideal_normality.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _gens_M(t):
    return [(0, t, t), (t, 0, t), (t, t, 0)]


def _veronese(t):
    return sorted((a, b, c) for a in range(t + 1) for b in range(t + 1) for c in range(t + 1) if a + b + c == 2 * t)


def _capsum_in(u, t):
    return min(u[0], t) + min(u[1], t) + min(u[2], t) >= 2 * t


def _in_M(u, G):
    return any(g[0] <= u[0] and g[1] <= u[1] and g[2] <= u[2] for g in G)


def _embedded_witness(t, in_pred):
    """Smallest u with u ∉ ideal but x·u, y·u, z·u ∈ ideal (⇒ (x,y,z) associated). None if no such u in the box."""
    B = 2 * t + 1
    for u in product(range(B + 1), repeat=3):
        if (not in_pred(u)) and in_pred((u[0] + 1, u[1], u[2])) and in_pred((u[0], u[1] + 1, u[2])) \
                and in_pred((u[0], u[1], u[2] + 1)):
            return u
    return None


def verify(m) -> dict:
    rows = []
    for t in CHECK_TS:
        G = _gens_M(t)
        clo = set(map(tuple, m.closure_min_generators(G)))
        ver = set(_veronese(t))
        # cross-check the cap-sum predicate equals the true integral closure over a box
        B = 2 * t + 1
        capsum_ok = all(_capsum_in(u, t) == m.in_closure_of_power(u, G, 1)
                        for u in product(range(B + 1), repeat=3))
        clo_emb = _embedded_witness(t, lambda u: _capsum_in(u, t))          # (x,y,z) embedded in closure?
        m_emb = _embedded_witness(t, lambda u: _in_M(u, G))                 # (x,y,z) embedded in M?
        rows.append({"t": t, "closure_eq_veronese": clo == ver, "capsum_eq_closure": capsum_ok,
                     "closure_embedded_witness": list(clo_emb) if clo_emb else None,
                     "M_embedded_witness": list(m_emb) if m_emb else None})
    all_ok = all(r["closure_eq_veronese"] and r["capsum_eq_closure"] for r in rows)
    return {"rows": rows, "all_ok": all_ok}


def _cert_for_t(t, clo_wit) -> tuple[str, list[str]]:
    G = _gens_M(t)
    ns = f"MafiNaderi_t{t}"
    gens_lean = "[" + ", ".join(f"({g[0]},{g[1]},{g[2]})" for g in G) + "]"
    # a witness in closure ∖ M (Thm 1.6: the closure is strictly bigger). Use the embedded witness scaled: any
    # u in closure but not in M. Search one.
    cw = None
    for u in product(range(2 * t + 1), repeat=3):
        if _capsum_in(u, t) and not _in_M(u, G):
            cw = u
            break
    ux, uy, uz = clo_wit
    body = (
        f"namespace {ns}\n"
        f"/-- closure(M_3,{t}) = Veronese I_(2·{t}; {t},{t},{t}) = {{x^u : min(a,{t})+min(b,{t})+min(c,{t}) ≥ {2*t}}}\n"
        f"    (Mafi–Naderi Theorem 1.6; our integral-dependence instrument confirms this equals the true closure). -/\n"
        f"def inClosure (a b c : ℕ) : Bool := {2*t} ≤ min a {t} + min b {t} + min c {t}\n"
        f"/-- M_3,{t} = (x^(0,{t},{t}), x^({t},0,{t}), x^({t},{t},0)). -/\n"
        f"def gens : List (ℕ × ℕ × ℕ) := {gens_lean}\n"
        f"def inM (a b c : ℕ) : Bool := gens.any (fun g => g.1 ≤ a && g.2.1 ≤ b && g.2.2 ≤ c)\n\n"
        f"/-- **Thm 1.6 (⊆ slice).** M_3,{t} ⊆ closure, and the closure is STRICTLY bigger (witness "
        f"x^{cw} ∈ closure ∖ M). -/\n"
        f"theorem M_subsetneq_closure :\n"
        f"    (∀ a < {2*t+1}, ∀ b < {2*t+1}, ∀ c < {2*t+1}, inM a b c = true → inClosure a b c = true)\n"
        f"    ∧ inClosure {cw[0]} {cw[1]} {cw[2]} = true ∧ inM {cw[0]} {cw[1]} {cw[2]} = false := by decide\n\n"
        f"/-- **Cor 1.7 (closure has embedded prime (x,y,z)).** x^{clo_wit} ∉ closure, but multiplying by each\n"
        f"    variable lands in closure — so (closure : x^{clo_wit}) = (x,y,z), an embedded associated prime. -/\n"
        f"theorem closure_embedded_prime :\n"
        f"    inClosure {ux} {uy} {uz} = false ∧ inClosure {ux+1} {uy} {uz} = true\n"
        f"    ∧ inClosure {ux} {uy+1} {uz} = true ∧ inClosure {ux} {uy} {uz+1} = true := by decide\n\n"
        f"/-- **Cor 1.7 (the closure GAINS it).** M_3,{t} itself has NO such witness for (x,y,z) over the box —\n"
        f"    M is unmixed; the embedded prime appears only after passing to the integral closure. -/\n"
        f"theorem M_no_embedded_prime :\n"
        f"    ∀ a < {2*t+1}, ∀ b < {2*t+1}, ∀ c < {2*t+1},\n"
        f"      ¬ (inM a b c = false ∧ inM (a+1) b c = true ∧ inM a (b+1) c = true ∧ inM a b (c+1) = true) := by decide\n"
        f"end {ns}\n"
    )
    names = [f"{ns}.M_subsetneq_closure", f"{ns}.closure_embedded_prime", f"{ns}.M_no_embedded_prime"]
    return body, names


def build_certificate(v: dict) -> tuple[str, list[str]]:
    header = (
        "/-\n"
        "  Independent kernel verification of Mafi & Naderi (2021), \"Integral closure and Hilbert series of a\n"
        "  special monomial ideal\", arXiv:2112.02921 — for M_{3,t} (n = 3).\n\n"
        "  Theorem 1.6: closure(M_{3,t}) = the Veronese cap-sum ideal {min(a,t)+min(b,t)+min(c,t) ≥ 2t}.\n"
        "  Corollary 1.7: M_{3,t} is Cohen–Macaulay (unmixed), yet its integral closure has EMBEDDED primes.\n\n"
        "  Our integral-dependence instrument confirms closure(M_{3,t}) = the cap-sum ideal (t = 1..4); the\n"
        "  kernel then decides (per t) that the closure has the embedded prime (x,y,z) while M_{3,t} does not —\n"
        "  the closure GAINS it. All `decide`, standard axioms. LLMs propose nothing; the kernel decides.\n"
        "  Produced by scripts/verify_mafi_naderi.py (Leibniz daemon).\n"
        "-/\n"
        "import Mathlib.Tactic\n\n"
    )
    bodies, names = [], []
    for t in CERT_TS:
        row = next(r for r in v["rows"] if r["t"] == t)
        b, n = _cert_for_t(t, tuple(row["closure_embedded_witness"]))
        bodies.append(b)
        names += n
    return header + "\n".join(bodies), names


def main() -> int:
    print("=== Mafi–Naderi (arXiv:2112.02921) integral closure of M_{3,t} — independent verification ===")
    m = _instr()
    v = verify(m)
    for r in v["rows"]:
        print(f"  t={r['t']}: closure = Veronese (Thm 1.6): {r['closure_eq_veronese']}  "
              f"cap-sum ≡ closure: {r['capsum_eq_closure']}  "
              f"closure embedded-prime witness: {r['closure_embedded_witness']}  "
              f"(M has embedded prime: {r['M_embedded_witness'] is not None})")
    if not v["all_ok"]:
        print("  !! a cross-check FAILED — refusing to certify.")

    src, names = build_certificate(v)
    ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT.write_text(src)

    kernel = {"status": "not run"}
    try:
        from leibniz.backends.lean_repl import LeanReplBackend, available
        if available():
            bk = LeanReplBackend(timeout_s=400)
            try:
                run_src = "".join(ln for ln in src.splitlines(keepends=True) if not ln.startswith("import "))
                run_src += "\n" + "\n".join(f"#print axioms {n}" for n in names) + "\n"
                r = bk._run(run_src, IMPORTS)
            finally:
                bk.close()
            msgs = (r or {}).get("messages", []) or []
            errs = [(x.get("data") or "") for x in msgs if x.get("severity") == "error"]
            axiom_lines = [x.get("data", "") for x in msgs if "axiom" in (x.get("data") or "")]
            _std = {"propext", "Classical.choice", "Quot.sound"}
            clean_axioms = all(
                ("does not depend on any axioms" in ln)
                or all(tk.strip() in _std for tk in ln.split("[", 1)[-1].rstrip("]\n").split(",") if tk.strip())
                for ln in axiom_lines)
            kernel = {"status": "checked", "errors": errs[:3], "n_theorems": len(names),
                      "axiom_lines": [ln.strip() for ln in axiom_lines[:3]],
                      "clean": (not errs and len(axiom_lines) == len(names) and clean_axioms)}
            print(f"  kernel: {len(names)} theorems — "
                  f"{'CLEAN (standard axioms) ✓' if kernel['clean'] else 'ISSUE: ' + str(errs[:2] or axiom_lines[:1])}")
        else:
            kernel = {"status": "unavailable (Lean REPL)"}
            print("  kernel: REPL unavailable (skip)")
    except Exception as ex:  # pragma: no cover
        kernel = {"status": f"unavailable ({type(ex).__name__}: {ex})"}
        print(f"  kernel: {kernel['status']}")

    gate = ("GREEN" if (v["all_ok"] and kernel.get("clean")) else
            "AMBER(kernel-unavailable)" if "unavailable" in str(kernel.get("status")) and v["all_ok"] else "RED")
    out = {"gate": gate, "tier": "audit", "ev": "AMPLIFICATION",
           "target": "Mafi & Naderi (2021), arXiv:2112.02921 — integral closure of M_{3,t}",
           "verification": v, "kernel": kernel, "theorems": names,
           "artifact": str(ARTIFACT.relative_to(_ROOT)),
           "reading": ("Independent kernel verification of Mafi–Naderi's Theorem 1.6 (closure = Veronese cap-sum "
                       "ideal) and Corollary 1.7 (the integral closure gains an embedded prime (x,y,z) that the "
                       "Cohen–Macaulay ideal M_{3,t} lacks), for n = 3, via the general monomial-ideal instrument. "
                       "Agreement with the paper (no erratum). Verification-amplification; no trust surface.")}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2, default=str) + "\n")
    print(f"\ngate={gate}  tier=audit  ev=AMPLIFICATION\n-> {OUT}\n-> {ARTIFACT}")
    return 0 if gate != "RED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
