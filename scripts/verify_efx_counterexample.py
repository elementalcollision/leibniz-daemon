"""Independent verification of the first counterexample to EFX existence (Akrami, Mayorov, Mehlhorn, Srinivas &
Weidenbach, arXiv:2604.18216, 2026).

A central open problem in discrete fair division: does an EFX (envy-free up to any good) allocation always
exist? The paper resolves it NEGATIVELY, exhibiting an explicit instance — 3 agents, 8 goods, monotone
valuations — with NO EFX allocation. Each agent i's valuation vᵢ is an ORDINAL: vᵢ(A) is the rank (0..255) of
the subset A in agent i's linear order over the 2⁸ = 256 subsets of the goods.

Leibniz re-decides the counterexample by EXACT exhaustive census over the paper's own valuation tables
(vendored verbatim from the companion artifact into docs/crt/efx/Val{0,1,2}ByCard.txt):
  (1) each valuation is a valid ORDINAL: a bijection onto {0,…,255} that is MONOTONE (A ⊂ B ⟹ vᵢ(A) < vᵢ(B))
      — so it is a legitimate monotone valuation, exactly the class the EFX-existence question is posed for;
  (2) NO EFX allocation exists: for every one of the 3⁸ = 6561 allocations of the 8 goods to the 3 agents, some
      agent EFX-envies another (removing any single good from the envied bundle does not remove the envy);
  (3) FAITHFULNESS cross-check: exactly 272 of the 5796 allocations with all-nonempty bundles violate EXACTLY
      ONE of the 2m = 16 EFX-conditions — reproducing the paper's own reported statistic bit-for-bit, which
      certifies the vendored valuation tables were ingested correctly.

This is an audit of a SAT-found instance (the valuations are arbitrary monotone rankings, not reconstructible),
decided by an exact-integer exhaustive procedure — no floating point, no LLM judgment. The paper separately
formalized the SAT-encoding's correctness in Lean; this is the complementary instance-level check. Tier audit,
verification-AMPLIFICATION; report-only, no trust surface.

Run:  python scripts/verify_efx_counterexample.py
"""
from __future__ import annotations

import json
from itertools import product
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
DATA = _ROOT / "docs" / "crt" / "efx"
OUT = _ROOT / "docs" / "results" / "efx_counterexample_verification.json"

N_GOODS = 8
FULL = (1 << N_GOODS) - 1


def load_valuations() -> list[dict[int, int]]:
    """vᵢ[mask] = rank of the subset `mask` for agent i (full set → 255 implicit)."""
    vals = []
    for i in range(3):
        v = {}
        for line in (DATA / f"Val{i}ByCard.txt").read_text().splitlines():
            line = line.strip()
            if len(line.split()) != 2 or len(line.split()[0]) != 8:
                continue
            bits, rank = line.split()
            v[int(bits, 2)] = int(rank)
        if FULL not in v:
            v[FULL] = 255
        vals.append(v)
    return vals


def _efx_violations(alloc: tuple[int, ...], V) -> tuple[int, list[int]]:
    """Number of EFX-conditions violated by the allocation, and the bundle masks.
    2m = 16 conditions: for each good g and each non-owner agent i, require vᵢ(Xᵢ) ≥ vᵢ(X_owner(g) ∖ g)."""
    X = [0, 0, 0]
    for g, o in enumerate(alloc):
        X[o] |= (1 << g)
    viol = 0
    for g in range(N_GOODS):
        o = alloc[g]
        owner_minus_g = X[o] & ~(1 << g)
        for i in range(3):
            if i == o:
                continue
            if V[i][X[i]] < V[i][owner_minus_g]:        # agent i EFX-envies the owner of g
                viol += 1
    return viol, X


def checks() -> dict:
    V = load_valuations()
    # (1) valid monotone ordinals
    perms = [sorted(v.values()) == list(range(256)) for v in V]

    def monotone(v):
        return all(v[A] < v[B] for B in range(256) for A in range(256) if A != B and (A & B) == A)

    monos = [monotone(v) for v in V]

    # (2)+(3) census
    n_efx_all = 0
    nonempty_total = 0
    nonempty_by_violations: dict[int, int] = {}
    for alloc in product(range(3), repeat=N_GOODS):
        viol, X = _efx_violations(alloc, V)
        if viol == 0:
            n_efx_all += 1
        if all(x != 0 for x in X):
            nonempty_total += 1
            nonempty_by_violations[viol] = nonempty_by_violations.get(viol, 0) + 1

    return {"valuations_are_permutations": perms, "valuations_monotone": monos,
            "n_allocations": 3 ** N_GOODS, "n_efx_allocations": n_efx_all,
            "nonempty_allocations": nonempty_total,
            "nonempty_exactly_one_violation": nonempty_by_violations.get(1, 0),
            "nonempty_efx": nonempty_by_violations.get(0, 0),
            "all_ok": (all(perms) and all(monos) and n_efx_all == 0
                       and nonempty_total == 5796 and nonempty_by_violations.get(1, 0) == 272)}


def main() -> int:
    r = checks()
    print("=== EFX non-existence counterexample — arXiv:2604.18216 ===")
    print("  exact census:", json.dumps(r))
    gate = "GREEN" if r["all_ok"] else "RED"
    out = {"gate": gate, "tier": "audit", "ev": "AMPLIFICATION",
           "target": "Existence of EFX allocations (open problem in fair division); counterexample by Akrami, "
                     "Mayorov, Mehlhorn, Srinivas & Weidenbach (2026), arXiv:2604.18216",
           "checks": r, "data": "docs/crt/efx/Val{0,1,2}ByCard.txt",
           "reading": ("Independent confirmation of the first counterexample to EFX existence. Over the paper's "
                       "own valuation tables (3 agents, 8 goods, monotone ordinal valuations), Leibniz decides "
                       "by exact exhaustive census that each valuation is a monotone bijection onto {0..255} and "
                       "that NONE of the 3^8 = 6561 allocations is EFX. The count of all-nonempty allocations "
                       "(5796) and of those violating exactly one of the 16 EFX-conditions (272) reproduce the "
                       "paper's reported statistics bit-for-bit, certifying faithful ingestion. Exact-integer "
                       "census; no floating point, no LLM judgment; no trust surface.")}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
    print(f"\ngate={gate}  tier=audit  ev=AMPLIFICATION\n-> {OUT}")
    return 0 if gate == "GREEN" else 1


if __name__ == "__main__":
    raise SystemExit(main())
