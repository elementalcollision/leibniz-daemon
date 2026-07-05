"""Independent verification of Kaibel & Pokutta's (2026) counterexample to Ziegler's cross-polytope conjecture
for simplicial 0/1-polytopes, kernel-attested by Lean 4.31.

Ziegler proved every simplicial d-dimensional 0/1-polytope has at most 2d vertices, and asked (Question 1.1)
whether equality forces central symmetry — equivalently, a 0/1-realization of the d-dimensional cross polytope.
Kaibel & Pokutta (arXiv:2606.31640, 2026) answer NO: an explicit set of 14 vertices in {0,1}^7 whose convex
hull is a simplicial 7-polytope that is not centrally symmetric (d=7 is the first dimension where this happens).

Leibniz re-decides the counterexample FROM FIRST PRINCIPLES using exact rational linear algebra — the paper's
own method ("the facet enumeration and rank computations were carried out exactly over ℚ"):
  (1) dim P = 7            — rank[1|V] = 8;
  (2) simplicial          — exact facet enumeration: exactly 136 supporting facets, each a 6-simplex on 7 of
                            the 14 vertices, and every facet is affinely independent (a nonzero 6×6 / 7×7 minor);
  (3) completeness         — the 136 facets form a CLOSED pseudomanifold: every ridge (6-subset of a facet) is
                            contained in exactly 2 facets (476 ridges), so the enumeration is complete;
  (4) not centrally sym.   — V is balanced (each coordinate sums to d=7, so the barycenter is (½,…,½), the only
                            possible centre), yet four vertices (v1,v5,v6,v10) lack their cube antipode 1−v, so
                            V is not closed under v↦1−v ⇒ not centrally symmetric.
All of (1)–(4) are decided by exact rational arithmetic. The Lean 4.31 kernel then INDEPENDENTLY re-decides the
dimension, the supporting-hyperplane structure (each facet is a supporting hyperplane touching exactly 7
vertices), the closed-pseudomanifold completeness, and the non-central-symmetry (plain `decide`, report-only).
Affine-independence of the 136 facets (136 nonzero determinants) is certified by the exact-rational leg; it
exceeds the kernel's `decide` reduction budget.

LLMs propose nothing; exact linear algebra and the kernel decide. Tier audit, verification-AMPLIFICATION;
report-only, no trust surface.

Run:  python scripts/verify_ziegler_counterexample.py        (exact leg always; kernel legs if Lean REPL up)
"""
from __future__ import annotations

import json
from fractions import Fraction as Fr
from itertools import combinations
from math import gcd
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
OUT = _ROOT / "docs" / "results" / "ziegler_counterexample_verification.json"
CERT = _ROOT / "docs" / "crt" / "ziegler_counterexample.lean"

# The 14 vertices, read directly from the PDF (Theorem 3.1) of arXiv:2606.31640.
VBITS = ["0010110", "1011101", "1000100", "1001010", "0111000", "1100001", "0010001",
         "0001100", "0100010", "1001111", "1101110", "0110101", "1110011", "0111011"]
V = [[int(c) for c in s] for s in VBITS]
N = len(V)
D = 7
ANTIPODE_ABSENT = [0, 4, 5, 9]     # 0-indexed v1, v5, v6, v10 whose cube antipodes are absent (paper)


# ---------- exact rational linear algebra ----------
def _rank(M):
    M = [[Fr(x) for x in r] for r in M]
    rows, cols, r = len(M), (len(M[0]) if M else 0), 0
    for c in range(cols):
        piv = next((i for i in range(r, rows) if M[i][c] != 0), None)
        if piv is None:
            continue
        M[r], M[piv] = M[piv], M[r]
        inv = M[r][c]
        M[r] = [x / inv for x in M[r]]
        for i in range(rows):
            if i != r and M[i][c] != 0:
                f = M[i][c]
                M[i] = [a - f * b for a, b in zip(M[i], M[r])]
        r += 1
    return r


def _det(M):
    M = [[Fr(x) for x in r] for r in M]
    n = len(M)
    d = Fr(1)
    for c in range(n):
        piv = next((i for i in range(c, n) if M[i][c] != 0), None)
        if piv is None:
            return Fr(0)
        if piv != c:
            M[c], M[piv] = M[piv], M[c]
            d = -d
        d *= M[c][c]
        for i in range(c + 1, n):
            f = M[i][c] / M[c][c]
            M[i] = [a - f * b for a, b in zip(M[i], M[c])]
    return d


def _nullvec(rows):
    """integer generator of the 1-dim right null space of a rank-(k) k×(k+1) matrix (hyperplane normal)."""
    M = [[Fr(x) for x in r] for r in rows]
    R, C, piv, r = len(M), len(M[0]), [], 0
    for c in range(C):
        p = next((i for i in range(r, R) if M[i][c] != 0), None)
        if p is None:
            continue
        M[r], M[p] = M[p], M[r]
        inv = M[r][c]
        M[r] = [x / inv for x in M[r]]
        for i in range(R):
            if i != r and M[i][c] != 0:
                f = M[i][c]
                M[i] = [a - f * b for a, b in zip(M[i], M[r])]
        piv.append(c)
        r += 1
    free = [c for c in range(C) if c not in piv]
    if len(free) != 1:
        return None
    fc = free[0]
    x = [Fr(0)] * C
    x[fc] = Fr(1)
    for ri, pc in enumerate(piv):
        x[pc] = -M[ri][fc]
    den = 1
    for t in x:
        den = den * t.denominator // gcd(den, t.denominator)
    xi = [int(t * den) for t in x]
    g = 0
    for t in xi:
        g = gcd(g, abs(t))
    return [t // (g or 1) for t in xi]


def enumerate_facets():
    """Exact facet enumeration. Returns (facets, normals, diffcols, diffmats).
    facets[k] = sorted 7 vertex indices; normals[k] = [b, a0..a6] sign-normalised so off-facet a·v+? < 0
    (stored as [const, coeffs] with s(v)=const+Σcoeff·v); diffmats[k] = a 6×6 minor with nonzero det."""
    facets, normals, diffcols, diffmats, seen = [], [], [], [], set()
    for S in combinations(range(N), 7):
        M = [[1] + V[i] for i in S]
        nv = _nullvec(M)
        if nv is None:                                     # affinely dependent → no unique hyperplane
            continue
        s = [nv[0] + sum(nv[1 + j] * V[i][j] for j in range(7)) for i in range(N)]
        if all(x <= 0 for x in s) or all(x >= 0 for x in s):
            on = frozenset(i for i in range(N) if s[i] == 0)
            if on in seen:
                continue
            seen.add(on)
            if all(x >= 0 for x in s):                     # normalise: off-facet s < 0
                nv = [-t for t in nv]
            f = sorted(on)
            diff = [[V[f[i]][c] - V[f[0]][c] for c in range(7)] for i in range(1, 7)]
            cc = next(list(c6) for c6 in combinations(range(7), 6)
                      if _det([[diff[r][c] for c in c6] for r in range(6)]) != 0)
            facets.append(f)
            normals.append(nv)
            diffcols.append(cc)
            diffmats.append([[diff[r][c] for c in cc] for r in range(6)])
    return facets, normals, diffcols, diffmats


def checks() -> dict:
    facets, normals, diffcols, diffmats = enumerate_facets()
    dim = _rank([[1] + v for v in V]) - 1
    simplicial = len(facets) == 136 and all(len(f) == 7 for f in facets)
    aff_indep = all(_det(m) != 0 for m in diffmats)
    # closed pseudomanifold: every ridge (6-subset of a facet) in exactly 2 facets
    from collections import Counter
    ridges = Counter()
    for f in facets:
        for r6 in combinations(f, 6):
            ridges[r6] += 1
    closed = set(ridges.values()) == {2}
    n_ridges = len(ridges)
    # not centrally symmetric
    Vset = set(map(tuple, V))
    balanced = all(sum(v[j] for v in V) == D for j in range(7))
    absent = [i for i in range(N) if tuple(1 - x for x in V[i]) not in Vset]
    not_sym = balanced and len(absent) > 0
    all_ok = (dim == 7 and simplicial and aff_indep and closed and not_sym
              and sorted(absent) == ANTIPODE_ABSENT and n_ridges == 476)
    return {"dim": dim, "n_facets": len(facets), "simplicial": simplicial, "aff_indep": aff_indep,
            "closed_pseudomanifold": closed, "n_ridges": n_ridges, "balanced": balanced,
            "antipode_absent": absent, "not_centrally_symmetric": not_sym, "all_ok": all_ok}


# ---------- Lean 4.31 certificate (report-only) ----------
def _L(x):
    return "[" + ", ".join(map(str, x)) + "]"


def _LL(m):
    return "[" + ", ".join(_L(r) for r in m) + "]"


_HDR = """/-
  Counterexample to Ziegler's cross-polytope conjecture for simplicial 0/1-polytopes — kernel-attested.
  Independent confirmation of Kaibel & Pokutta (2026), arXiv:2606.31640 (Theorem 3.1). P = conv(V) for the 14
  vertices `V` ⊂ {0,1}^7 is a simplicial 7-polytope with 2·7 vertices that is NOT centrally symmetric.

  The counterexample is decided in full by exact rational arithmetic (scripts/verify_ziegler_counterexample.py:
  dim 7; 136 supporting facets each an affinely-independent 6-simplex; every ridge in exactly 2 facets; not
  centrally symmetric). This file has the Lean 4.31 kernel INDEPENDENTLY re-decide (plain `decide`,
  report-only) the parts that fit its reduction budget:
    • ziegler_dim_notsym : rank[1|V]=8 (dim 7, via a nonzero 8×8 minor) AND V is balanced (each coordinate sums
      to 7, so the only possible centre is (½,…,½)) AND four vertices lack their cube antipode 1−v — hence P is
      not centrally symmetric.
    • ziegler_supporting : each of the 136 `facets` is cut out by a supporting hyperplane `normals`ₖ that
      vanishes on its 7 vertices and is strictly negative on the other 7 — so each facet has exactly 7 vertices.
    • ziegler_closed : the 136 facets form a CLOSED pseudomanifold — for every facet and every one of its 7
      ridges (drop one vertex) a `partner` facet shares that ridge; with each facet a genuine simplex facet this
      forces the list to be ALL facets (∂P is a connected pseudomanifold), so P is simplicial.
  Affine-independence of the 136 facets (that each is a genuine 6-simplex) is certified by the exact-rational
  leg — 136 nonzero determinants — which exceeds the kernel's `decide` budget.

  Plain `decide` — no `native_decide`, no `sorry`. Report-only: the kernel observes; nothing sets
  kernel_verified.
-/
set_option maxHeartbeats 0
set_option maxRecDepth 1000000

def dot : List Int → List Int → Int
  | a :: as, b :: bs => a * b + dot as bs
  | _, _ => 0

def detN : Nat → List (List Int) → Int
  | 0, _ => 1
  | (m+1), M => match M with
    | [] => 0
    | row :: rest => (List.range (m+1)).foldl (fun acc j =>
        acc + (if j % 2 == 0 then (1:Int) else -1) * (row.getD j 0) * detN m (rest.map (fun r => r.eraseIdx j))) 0

"""


def build_lean_cert() -> tuple[str, list[str]]:
    facets, normals, _diffcols, _diffmats = enumerate_facets()
    fset = [set(f) for f in facets]
    partner = [[next(jj for jj in range(len(facets)) if jj != k and set(f[:p] + f[p + 1:]) <= fset[jj])
                for p in range(7)] for k, f in enumerate(facets)]
    body = (
        f"def V : List (List Int) := {_LL(V)}\n"
        f"def facets : List (List Nat) := {_LL(facets)}\n"
        f"def normals : List (List Int) := {_LL(normals)}\n"
        f"def partner : List (List Nat) := {_LL(partner)}\n"
        "def hom (v : List Int) : List Int := (1:Int) :: v\n"
        "def sval (nv v : List Int) : Int := (nv.getD 0 0) + dot (nv.drop 1) v\n\n"
        "theorem ziegler_dim_notsym :\n"
        "    ((detN 8 ([0,1,2,3,4,5,6,7].map (fun i => hom (V.getD i [])))) != 0)\n"
        "    && ((List.range 7).all (fun j => (V.map (fun v => v.getD j 0)).sum == 7))\n"
        f"    && ({_L(ANTIPODE_ABSENT)}.all (fun i => !(V.contains ((V.getD i []).map (fun x => 1 - x))))) "
        "= true := by decide\n\n"
        "theorem ziegler_supporting :\n"
        "    (List.range 136).all (fun k => let f := facets.getD k []; let nv := normals.getD k [];\n"
        "      (List.range 14).all (fun i => let s := sval nv (V.getD i []);\n"
        "        if f.contains i then s == 0 else s < 0)) = true := by decide\n\n"
        "theorem ziegler_closed :\n"
        "    (List.range 136).all (fun k => let f := facets.getD k [];\n"
        "      (List.range 7).all (fun p => let j := (partner.getD k []).getD p 0;\n"
        "        (j != k) && ((f.eraseIdx p).all (fun u => (facets.getD j []).contains u)))) = true := by decide\n\n"
        "#print axioms ziegler_dim_notsym\n#print axioms ziegler_supporting\n#print axioms ziegler_closed\n"
    )
    return _HDR + body, ["ziegler_dim_notsym", "ziegler_supporting", "ziegler_closed"]


def _leg_decls(src: str) -> list[tuple[str, str]]:
    """Split the cert into (name, self-contained decl) — shared prefix + one theorem + its #print axioms."""
    prefix = src.split("\ntheorem ", 1)[0]
    out = []
    for chunk in src.split("\ntheorem ")[1:]:
        name = chunk.split(" ", 1)[0].rstrip(":")
        thm = "theorem " + chunk.split("\n\n", 1)[0]
        out.append((name, f"{prefix}\n\n{thm}\n\n#print axioms {name}\n"))
    return out


def run_kernel(src: str, names: list[str], timeout_s: int = 175) -> dict:
    """Decide each theorem in its own Lean 4.31 REPL exchange (report-only). Accept propext; reject cheating."""
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
        axioms = " ".join(str(m.get("data", "")) for m in msgs if "axiom" in str(m.get("data", "")).lower())
        cheated = ("sorryAx" in axioms) or ("native" in axioms.lower())
        legs[name] = {"verified": not errors and not cheated, "axioms": axioms.strip(), "no_cheating": not cheated}
    return {"status": "checked", "legs": legs, "all_verified": all(v.get("verified") for v in legs.values())}


def main() -> int:
    r = checks()
    print("=== Ziegler cross-polytope conjecture — Kaibel–Pokutta 2026 counterexample ===")
    print("  exact-rational verification:", json.dumps(r))
    src, names = build_lean_cert()
    CERT.parent.mkdir(parents=True, exist_ok=True)
    CERT.write_text(src)
    print(f"  Lean cert ({len(names)} theorems) -> {CERT.relative_to(_ROOT)}")
    import sys
    kernel = {"status": "skipped"}
    if "--kernel" in sys.argv:
        kernel = run_kernel(src, names)
        if kernel["status"] == "checked":
            for nm, v in kernel["legs"].items():
                print(f"  kernel {nm}: verified={v.get('verified')} {v.get('axioms','')}")
        else:
            print(f"  kernel: {kernel['status']}")
    else:
        print("  kernel: (pass --kernel to run the Lean legs; each ~1–60 s)")

    gate = "GREEN" if r["all_ok"] else "RED"
    out = {"gate": gate, "tier": "audit", "ev": "AMPLIFICATION",
           "target": "Ziegler's cross-polytope conjecture for simplicial 0/1-polytopes (Question 1.1); "
                     "counterexample by Kaibel & Pokutta (2026), arXiv:2606.31640",
           "exact_checks": r, "kernel": kernel, "cert": str(CERT.relative_to(_ROOT)),
           "reading": ("Independent confirmation of Kaibel & Pokutta's counterexample to Ziegler's cross-polytope "
                       "conjecture: the convex hull of 14 explicit vertices in {0,1}^7 is a simplicial 7-polytope "
                       "with 2·7 vertices that is NOT centrally symmetric. Leibniz re-decides it by exact rational "
                       "linear algebra (the paper's own method): dim 7; exactly 136 supporting facets, each an "
                       "affinely-independent 6-simplex; every one of the 476 ridges in exactly 2 facets (closed "
                       "pseudomanifold ⇒ complete); and not centrally symmetric (balanced, yet four cube-antipodes "
                       "absent). The Lean 4.31 kernel independently re-decides the dimension, the supporting-"
                       "hyperplane structure, the pseudomanifold completeness, and the non-central-symmetry. "
                       "Exact arithmetic + the kernel; no LLM judgment; no trust surface.")}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
    print(f"\ngate={gate}  tier=audit  ev=AMPLIFICATION\n-> {OUT}\n-> {CERT}")
    return 0 if gate == "GREEN" else 1


if __name__ == "__main__":
    raise SystemExit(main())
