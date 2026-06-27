"""Probe α — the zero-LLM enumeration audit (the witness round's liquidation audit).

The 7-model external round narrowed our cross-backend conclusion: the wall may be the PRODUCER's
catalogue bias (an LLM recites Thue-Morse/Motzkin), not finite-encodability itself. This probe
removes the LLM from the producer entirely: it brute-force enumerates a pre-registered space of
*un-named* k-automatic sequences (fixed points of small UNIFORM morphisms), and emits Walnut
command files that DECIDE pre-registered properties of them. Walnut decides; a human panel grades
novelty (invariant 4). If a sound, faithful, non-trivial, non-catalogued DECIDED theorem falls out
that the LLM never proposed, the slogan "finitely-encodable = textbook" is FALSIFIED and the lever
is search, not a better LLM. If none does after sweeping the bounded space, autonomous discovery in
decidable domains closes cleanly.

WHY UNIFORM ONLY (soundness): `promote` of a k-uniform morphism builds a DFAO whose numeration is
`msd_k` (Walnut `Morphism.toWordAutomaton`, NS = "msd_"+maxImageLength). For a NON-uniform morphism
that base is wrong for the true fixed point, so a decided result would not faithfully be about the
sequence. Restricting to uniform keeps the numeration exact (`?msd_k`) and the faithfulness gap ~0
(the morphism IS the definition — no English).

NO LLM anywhere here. Pure stdlib. The producer is exhaustive enumeration; the decider is Walnut
(operator-run); novelty is the human panel's. Output: a known-answer SMOKE batch (validate syntax
first), the full pre-registered batch, and a manifest.

Run:
    python3 scripts/enumerate_walnut_probe_alpha.py [out_dir] [--max-morphisms N]
"""
from __future__ import annotations

import json
import sys
from itertools import permutations, product
from pathlib import Path

# --- pre-registered space ---------------------------------------------------------------
# (k, m): k = uniform image length (= base), m = alphabet size {0..m-1}. Enumerated in this
# fixed order; --max-morphisms truncates deterministically. This IS the pre-registration.
KM_SPACE: tuple[tuple[int, int], ...] = ((2, 2), (2, 3), (3, 2))
POWER_FREE_EXPONENTS: tuple[int, ...] = (2, 3, 4)   # square-/cube-/4th-power-free
PREFIX_LEN = 4096                                    # fixed-point prefix for triage filters

# Catalogued / named morphic words to FLAG (triage only; the human literature check is
# authoritative). Keyed by canonical morphism form (filled in below once _canon is defined).
NAMED: dict[tuple, str] = {}
_NAMED_RAW = {
    "Thue-Morse": (2, {0: (0, 1), 1: (1, 0)}),
    "period-doubling": (2, {0: (0, 1), 1: (0, 0)}),
}


def _canon(h: dict[int, tuple[int, ...]], m: int) -> tuple:
    """Canonical form of a morphism under alphabet permutations fixing 0 (so the fixed point
    still starts at 0). Two morphisms equal up to relabel collapse to one representative."""
    best = None
    for perm in permutations(range(1, m)):
        sigma = {0: 0}
        for old, new in zip(range(1, m), perm):
            sigma[old] = new
        relabeled = {sigma[a]: tuple(sigma[x] for x in img) for a, img in h.items()}
        key = tuple(sorted(relabeled.items()))
        if best is None or key < best:
            best = key
    return best


def uniform_morphisms(k: int, m: int):
    """All uniform k-morphisms on {0..m-1} whose fixed point starts at 0 (h(0)[0] == 0),
    deduped up to alphabet relabeling. Yields (canon_key, h)."""
    seen = set()
    img0_choices = [img for img in product(range(m), repeat=k) if img[0] == 0]
    other = list(product(range(m), repeat=k))
    for img0 in img0_choices:
        for rest in product(other, repeat=m - 1):
            h = {0: img0}
            for letter, img in zip(range(1, m), rest):
                h[letter] = img
            key = _canon(h, m)
            if key in seen:
                continue
            seen.add(key)
            yield key, h


def fixed_point_prefix(h: dict[int, tuple[int, ...]], n: int) -> list[int]:
    """First n letters of the fixed point of h starting from 0 (uniform => grows by factor k)."""
    seq = [0]
    while len(seq) < n:
        nxt: list[int] = []
        for a in seq:
            nxt.extend(h[a])
        if len(nxt) == len(seq):    # not growing (defensive)
            break
        seq = nxt
    return seq[:n]


def eventually_periodic(seq: list[int]) -> bool:
    """Heuristic degeneracy filter: the prefix's second half has a small exact period =>
    the sequence is (ultimately) periodic => DEGENERATE (drop). Triage only."""
    tail = seq[len(seq) // 2:]
    L = len(tail)
    for p in range(1, L // 2 + 1):
        if all(tail[i] == tail[i + p] for i in range(L - p)):
            return True
    return False


def uses_all_letters(seq: list[int], m: int) -> bool:
    return len(set(seq)) == m


def _init_named() -> None:
    for name, (m, h) in _NAMED_RAW.items():
        NAMED[_canon(h, m)] = name


def named_match(canon: tuple) -> str | None:
    """Flag if the morphism is a catalogued one (by canonical form). Triage only — the human
    literature check decides whether a *survivor* is genuinely uncatalogued."""
    return NAMED.get(canon)


def _morphism_str(h: dict[int, tuple[int, ...]]) -> str:
    return " ".join(f"{a}->{''.join(str(x) for x in h[a])}" for a in sorted(h))


def _power_free_bound(e: int) -> str:
    # no e-th power at (i,p): exists t < (e-1)*p with a mismatch at distance p
    return "p" if e == 2 else f"{e - 1}*p"


def commands_for(idx: int, h: dict[int, tuple[int, ...]], k: int) -> tuple[list[str], list[dict]]:
    """Walnut commands (morphism + promote + one eval per exponent) and their manifest rows."""
    hid, wid = f"ha{idx}", f"WA{idx}"
    lines = [f'morphism {hid} "{_morphism_str(h)}";', f"promote {wid} {hid};"]
    rows = []
    for e in POWER_FREE_EXPONENTS:
        ev = f"ra{idx}e{e}"
        pred = (f"?msd_{k} A i,p (p>=1) => (E t (t<{_power_free_bound(e)}) & "
                f"{wid}[i+t] != {wid}[i+t+p])")
        lines.append(f'eval {ev} "{pred}";')
        rows.append({"eval_name": ev, "property": "power_free", "exponent": e,
                     "numeration": f"msd_{k}",
                     "meaning": f"fixed point of this uniform {k}-morphism is {e}-power-free"})
    return lines, rows


# --- smoke batch: KNOWN answers, to validate emitted syntax/numeration before the full run ----
# Thue-Morse (0->01,1->10): cube-free (e=3) TRUE; square-free (e=2) FALSE; 4-power-free TRUE.
def smoke_batch() -> tuple[list[str], list[dict]]:
    tm = {0: (0, 1), 1: (1, 0)}
    lines, rows = commands_for(0, tm, 2)
    for r in rows:
        r["expected"] = {2: "FALSE", 3: "TRUE", 4: "TRUE"}[r["exponent"]]
        r["word"] = "Thue-Morse (known-answer)"
    return lines, rows


def build(out_dir: Path, max_morphisms: int) -> dict:
    _init_named()
    out_dir.mkdir(parents=True, exist_ok=True)
    # smoke
    s_lines, s_rows = smoke_batch()
    (out_dir / "probe_alpha_smoke.txt").write_text("\n".join(s_lines) + "\n")

    # full pre-registered batch
    manifest: list[dict] = []
    batch_lines: list[str] = []
    kept = 0
    stats = {"enumerated": 0, "dropped_periodic": 0, "dropped_not_all_letters": 0,
             "named_flagged": 0, "kept": 0}
    idx = 1
    for (k, m) in KM_SPACE:
        for canon, h in uniform_morphisms(k, m):
            stats["enumerated"] += 1
            seq = fixed_point_prefix(h, PREFIX_LEN)
            if eventually_periodic(seq):
                stats["dropped_periodic"] += 1
                continue
            if not uses_all_letters(seq, m):
                stats["dropped_not_all_letters"] += 1
                continue
            if kept >= max_morphisms:
                continue
            name = named_match(canon)
            if name:
                stats["named_flagged"] += 1
            lines, rows = commands_for(idx, h, k)
            batch_lines.extend(lines)
            for r in rows:
                manifest.append({"claim_id": f"a{idx}", "k": k, "m": m,
                                 "morphism": _morphism_str(h),
                                 "fixed_point_prefix32": "".join(str(x) for x in seq[:32]),
                                 "named_match": name, **r})
            kept += 1
            idx += 1
    stats["kept"] = kept
    (out_dir / "probe_alpha_batch.txt").write_text("\n".join(batch_lines) + "\n")
    (out_dir / "probe_alpha_manifest.json").write_text(json.dumps(
        {"space": [list(km) for km in KM_SPACE], "exponents": list(POWER_FREE_EXPONENTS),
         "prefix_len": PREFIX_LEN, "max_morphisms": max_morphisms, "stats": stats,
         "claims": manifest}, indent=2))
    return stats


def main() -> int:
    args = [a for a in sys.argv[1:] if a != "--max-morphisms"]
    out = Path(args[0]) if args and not args[0].isdigit() else Path("probe_alpha_out")
    max_m = 120
    if "--max-morphisms" in sys.argv:
        i = sys.argv.index("--max-morphisms")
        if i + 1 < len(sys.argv):
            max_m = int(sys.argv[i + 1])
    stats = build(out, max_m)
    print(f"[probe-alpha] zero-LLM enumeration audit — wrote to {out}/")
    print(f"  enumerated (deduped uniform morphisms): {stats['enumerated']}")
    print(f"  dropped eventually-periodic:            {stats['dropped_periodic']}")
    print(f"  dropped (collapses to fewer letters):   {stats['dropped_not_all_letters']}")
    print(f"  named/catalogued flagged:               {stats['named_flagged']}")
    print(f"  KEPT (aperiodic, non-degenerate):       {stats['kept']}  x {len(POWER_FREE_EXPONENTS)} evals")
    print(f"  smoke (run FIRST, known answers): {out}/probe_alpha_smoke.txt")
    print(f"  full batch:                      {out}/probe_alpha_batch.txt")
    print(f"  manifest:                        {out}/probe_alpha_manifest.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
