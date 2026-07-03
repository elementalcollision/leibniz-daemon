"""Process-complexity certificate domain (T8 → first-class) — a reusable interface for certifying a stochastic
process's beyond-Markov complexity, a sibling of the code-bound and covering-design certificate domains. It
unifies the per-process beyond-Markov machinery behind one `certify(process)` call that produces the exact-
rational certificate bundle and names the kernel-verified Lean lemma that attests each part:

  * VALIDITY     — a valid rational HMM (pi>=0, sum pi=1, T_a>=0, sum_a T_a row-stochastic): P(w) is a genuine
                   stochastic process, not a signed formal series (the external panel's #1 mandate).
  * HANKEL RANK  — the exact rank of the word-Hankel block (the prediction-state dimension) + a nonsingular
                   r-minor (the kernel-checkable rank>=r lower bound; kernel lemma: hankel_block_rank_le).
  * MARKOV ORDER — a conditional-separation certificate (order > K), and for synchronizing processes the
                   infinite-order recurrence (kernel lemma: even_infinite_order via two_step_recurrence_nonzero).
  * POSITIVE REALIZATION — where a fooling set exists, the minimal-positive-HMM-states lower bound
                   (kernel lemma: fooling_le_of_nonneg_factor + hankel_nonneg_factor).

Honest disposition: audit tier, verification-AMPLIFICATION (the mathematics is textbook; the discovery case is
provably out of reach of the exact-rational machinery — see docs/results/beyond-markov-witness-review-*). The
domain's value is a reusable, kernel-attestable certificate family, not new theorems. No trust surface touched.

Run:  python scripts/process_complexity_domain.py   (free-CPU; the kernel attestation is the per-process scripts)
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent


def _load(mod, rel):
    sys.path.insert(0, str(_ROOT))
    sys.path.insert(0, str(_ROOT / "scripts"))
    spec = importlib.util.spec_from_file_location(mod, _ROOT / rel)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _words(alph, L):
    out, cur = [], [()]
    for _ in range(L):
        cur = [c + (a,) for c in cur for a in alph]
        out += cur
    return out


def _exact_rank(rows) -> int:
    R = [r[:] for r in rows]
    m, n = len(R), (len(R[0]) if R else 0)
    prow = rank = 0
    for col in range(n):
        piv = next((i for i in range(prow, m) if R[i][col] != 0), None)
        if piv is None:
            continue
        R[prow], R[piv] = R[piv], R[prow]
        pv = R[prow][col]
        R[prow] = [x / pv for x in R[prow]]
        for i in range(m):
            if i != prow and R[i][col] != 0:
                f = R[i][col]
                R[i] = [x - f * y for x, y in zip(R[i], R[prow])]
        prow += 1
        rank += 1
        if prow == m:
            break
    return rank


def certify(process: dict, *, L: int = 2, K: int = 8) -> dict:
    """The process-complexity certificate bundle for one process (given as an HMM/OOM in beyond_markov_cert
    form: {name, alphabet, pi, T, [order], [expect]}). Free-CPU, exact-rational."""
    bmc = _load("beyond_markov_cert", "scripts/beyond_markov_cert.py")
    hmm = {"name": process["name"], "params": process.get("params", {}),
           "pi": process["pi"], "T": process["T"]}
    val = bmc.hmm_valid(hmm)
    alph = sorted(hmm["T"].keys())

    # Hankel rank over words of length 1..L (the exact prediction-state dimension) + a rank-lower minor.
    W = _words(alph, L)
    H = [[bmc.prob(hmm, u + v) for v in W] for u in W]
    hankel_rank = _exact_rank(H)
    rank_cert = bmc.hankel_minor_cert(hmm, [(), (alph[0],)], [(alph[0],), (alph[-1],)])

    # Markov order: conditional-separation certs order > K (per-process history config).
    oc = process.get("order")
    order = None
    if oc:
        certs = [bmc.order_separation_cert(hmm, k, a=oc["a"], pre1=oc["pre1"], pre2=oc["pre2"], suffix=oc["suffix"])
                 for k in range(K + 1)]
        order = {"order_gt": K, "all_hold": all(c["ok"] for c in certs)}

    return {
        "name": process["name"], "dim": len(hmm["pi"]), "alphabet": len(alph),
        "validity": {"valid_hmm": val["valid"]},
        "hankel": {"rank": hankel_rank, "rank_ge_minor_det": rank_cert["det_int"],
                   "rank_lower_ok": rank_cert["ok"]},
        "markov_order": order,
        "kernel_lemmas": process.get("kernel_lemmas", []),
        "certified": bool(val["valid"] and rank_cert["ok"] and (order is None or order["all_hold"])),
    }


def registry() -> list:
    """The initial process corpus — the beyond-Markov witnesses, each with the kernel lemma that attests it."""
    bmc = _load("beyond_markov_cert", "scripts/beyond_markov_cert.py")
    bm1 = bmc.bm1_two_mode()
    ev = bmc.even_process()
    return [
        {**bm1, "params": bm1.get("params", {}),
         "kernel_lemmas": ["hankel_block_rank_le", "two_step_recurrence_nonzero (geometric-decay gap)"],
         "note": "symmetric 2-mode HMM: rank 2, order>K (gap decays but never vanishes)"},
        {**ev, "params": {},
         "kernel_lemmas": ["hankel_block_rank_le → eB_rank_eq_two", "even_infinite_order"],
         "note": "even process: rank 2 AND infinite Markov order, both kernel-derived from its OOM"},
    ]


def necklace_positive_realization() -> dict:
    """The necklace chain's positive-realization certificate (rank 3, minimal positive realization 4) — the
    fooling-set family, attested by necklace_positive_realization_needs_4."""
    mprp = _load("beyond_markov_mprp", "scripts/beyond_markov_mprp.py")
    A, pi = mprp.necklace()
    H2 = [[pi[a] * A[a][b] for b in range(4)] for a in range(4)]
    fooling = mprp.fooling_ok([[1 if H2[a][b] > 0 else 0 for b in range(4)] for a in range(4)],
                              mprp.FS_ROWS, mprp.FS_COLS)
    pa = mprp.process_audit()
    return {"name": "necklace 4-cycle chain", "hankel_rank": 3, "minimal_positive_realization": 4,
            "gap": "4 > 3 = rank", "fooling_size4_valid": fooling,
            "hankel_rank_stable_3": pa["hankel_rank_stable_3"],
            "kernel_lemmas": ["fooling_le_of_nonneg_factor", "hankel_nonneg_factor",
                              "necklace_positive_realization_needs_4"],
            "certified": bool(fooling and pa["hankel_rank_stable_3"])}


def main() -> int:
    print("=== process-complexity certificate domain ===")
    results = [certify(p) for p in registry()]
    neck = necklace_positive_realization()
    for r in results:
        o = r["markov_order"]
        print(f"  {r['name']:<28} dim={r['dim']} rank={r['hankel']['rank']} "
              f"(minor {r['hankel']['rank_ge_minor_det']}!=0) "
              f"order>{o['order_gt'] if o else '—'}={o['all_hold'] if o else '—'}  certified={r['certified']}")
    print(f"  {neck['name']:<28} rank={neck['hankel_rank']} minimal-positive-realization="
          f"{neck['minimal_positive_realization']} (gap {neck['gap']})  certified={neck['certified']}")

    all_ok = all(r["certified"] for r in results) and neck["certified"]
    out = {"gate": "GREEN" if all_ok else "RED", "tier": "audit", "ev": "AMPLIFICATION",
           "processes": results, "positive_realization": neck,
           "reading": ("Process-complexity certificate domain: a reusable interface certifying a process's "
                       "beyond-Markov complexity (validity, Hankel rank + a rank-lower minor, Markov order, "
                       "positive-realization gap), each part naming the kernel-verified Lean lemma that attests "
                       "it. A sibling of the code-bound and covering domains, but VERIFICATION-AMPLIFICATION "
                       "(textbook math; the discovery case is out of reach of the exact-rational machinery). "
                       "GREEN = every registered process certifies exact-rationally and maps to its kernel lemma.")}
    p = _ROOT / "docs" / "results" / "process_complexity_domain.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, indent=2, default=str) + "\n")
    print(f"\ngate={out['gate']}  tier=audit  ev=AMPLIFICATION\n-> {p}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
