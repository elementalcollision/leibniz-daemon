"""Ramsey lower-bound verifier framework (Gate B2 — SCOPED by the kernel-`decide` wall, see
docs/gate-b2-ramsey-decide-wall-finding.md).

A witness for R(s,t) > n is a graph on n vertices with no s-clique and no t-independent-set; we scope to
CIRCULANT witnesses (a symmetric connection set S ⊆ Z_n), the form cyclic Ramsey records take and the
one the vertex-transitive (VT) reduction needs. `verify_ramsey` is the UNTRUSTED, fast (pruned B&B)
checker — the reusable proposer/checker. `render_ramsey_lean` emits a core-Lean `decide` theorem but is
HARD-CAPPED to the toy regime: `decide` does naive (un-pruned) enumeration, so it is intractable at
frontier sizes (C(n,s)+C(n,t) explodes). Sound frontier verification needs a certificate architecture
(deferred). The cap keeps the audit promise honest — it never emits an intractable kernel job.
"""
from __future__ import annotations

from math import comb

# decide-render cap: total subsets the kernel would enumerate. C5 (~20) verified in ~1s; keep well within.
RENDER_SUBSET_CAP = 2000


def _circulant_adj(n: int, S):
    Sset = {x % n for x in S}
    return [[(j != i) and ((i - j) % n in Sset) for j in range(n)] for i in range(n)]


def _is_symmetric(n: int, S) -> bool:
    Sset = {x % n for x in S if x % n != 0}
    return all((n - x) % n in Sset for x in Sset)


def _max_clique(verts, adj) -> int:
    """Exact max-clique size on the induced subgraph (Tomita-style greedy-colour bound; pruned, UNTRUSTED)."""
    best = [0]

    def expand(R, cand):
        if not cand:
            best[0] = max(best[0], R)
            return
        col, rem, order = {}, set(cand), []
        while rem:
            c = max(col.values(), default=0) + 1
            avail = set(rem)
            while avail:
                v = min(avail)
                col[v] = c
                avail.discard(v)
                for u in cand:
                    if adj[v][u]:
                        avail.discard(u)
                rem.discard(v)
        order = sorted(cand, key=lambda v: col[v])
        for v in reversed(order):
            if R + col[v] <= best[0]:
                return
            expand(R + 1, [u for u in cand if adj[v][u]])
            cand = [u for u in cand if u != v]
    expand(0, list(verts))
    return best[0]


def omega_alpha(n: int, S) -> tuple[int, int]:
    """(ω, α) of the circulant graph, via the VT reduction: ω = 1 + ω(G[N(0)]),
    α = 1 + α(G[non-N(0)]) = 1 + ω(complement[non-N(0)]). UNTRUSTED (pruned search)."""
    adj = _circulant_adj(n, S)
    N0 = [j for j in range(n) if adj[0][j]]
    NN0 = [j for j in range(1, n) if not adj[0][j]]
    comp = [[(a != b) and not adj[a][b] for b in range(n)] for a in range(n)]
    omega = 1 + _max_clique(N0, adj) if n else 0
    alpha = 1 + _max_clique(NN0, comp) if n else 0
    return omega, alpha


def verify_ramsey(n: int, s: int, t: int, S) -> tuple[bool, str]:
    """True iff the circulant witness proves R(s,t) > n: symmetric S, ω < s, α < t. UNTRUSTED pre-check."""
    if not _is_symmetric(n, S):
        return False, "connection set is not symmetric (graph is not undirected/circulant)"
    omega, alpha = omega_alpha(n, S)
    if omega >= s:
        return False, f"has a clique of size {omega} >= s={s}"
    if alpha >= t:
        return False, f"has an independent set of size {alpha} >= t={t}"
    return True, "ok"


_LEAN_HELPERS = """\
-- circulant Ramsey-witness checker (core Lean 4; no Mathlib)
def combs : Nat -> List Nat -> List (List Nat)
  | 0,     _       => [[]]
  | _+1,   []      => []
  | (k+1), (x::xs) => (combs k xs).map (fun c => x :: c) ++ combs (k+1) xs
def hasEdge (n : Nat) (S : List Nat) (i j : Nat) : Bool := S.contains ((i + n - j) % n)
def isClq (n : Nat) (S c : List Nat) : Bool := c.all (fun i => c.all (fun j => (i == j) || hasEdge n S i j))
def isInd (n : Nat) (S c : List Nat) : Bool := c.all (fun i => c.all (fun j => (i == j) || ! hasEdge n S i j))
def ramseyWitness (n s t : Nat) (S : List Nat) : Bool :=
  (combs s (List.range n)).all (fun c => ! isClq n S c) &&
  (combs t (List.range n)).all (fun c => ! isInd n S c)"""


def render_ramsey_lean(n: int, s: int, t: int, S, thm_name: str | None = None) -> str:
    """Render a core-Lean `decide` theorem `R(s,t) > n`. Refuses a FALSE witness, and refuses to render
    beyond the toy regime (RENDER_SUBSET_CAP) — `decide` is intractable at frontier sizes (Gate B2)."""
    ok, reason = verify_ramsey(n, s, t, S)
    if not ok:
        raise ValueError(f"refusing to render a false Ramsey theorem: {reason}")
    n_subsets = comb(n, s) + comb(n, t)
    if n_subsets > RENDER_SUBSET_CAP:
        raise ValueError(f"refusing to render: {n_subsets} subsets exceed the decide cap "
                         f"({RENDER_SUBSET_CAP}); frontier Ramsey needs a certificate architecture, not "
                         f"`decide` (docs/gate-b2-ramsey-decide-wall-finding.md)")
    name = thm_name or f"ramsey_{s}_{t}_gt_{n}"
    lits = "[" + ", ".join(str(x % n) for x in sorted({x % n for x in S})) + "]"
    return (f"{_LEAN_HELPERS}\n\ntheorem {name} :\n"
            f"    ramseyWitness {n} {s} {t} {lits} = true := by\n  decide\n")
