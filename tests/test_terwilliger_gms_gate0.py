"""Guard the GATE 0 GMS-quadruple block-size probe (scripts/terwilliger_gms_gate0.py). Pure Python, CI-safe.
The finding under test: the GMS *Hamming* quadruple reduced blocks are indexed by pairs (i,i') with
i+i'∈[d,n] → O(n²) → past the ~30 native-kernel LDLT ceiling on every in-range target cell (RED). This is
the kill-gate result and must not silently regress to a GREEN if the block formula is edited."""
from __future__ import annotations

import importlib.util
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent


def _load():
    spec = importlib.util.spec_from_file_location("terwilliger_gms_gate0",
                                                  _ROOT / "scripts" / "terwilliger_gms_gate0.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


g = _load()


def test_block_dim_is_pair_indexed_On2():
    # the (0,0) block at n=28,d=6 is the number of (i,i') pairs with 6≤i+i'≤28 → ~414 (O(n²), not O(n))
    assert g.block_dim(28, 6, 0, 0) == 414
    # quadratic growth signature: doubling-ish n roughly quadruples the largest block
    assert g.profile(28, 6)["largest_block"] > 3 * g.profile(14, 6)["largest_block"]


def test_largest_block_exceeds_kernel_ceiling_on_all_targets():
    for d in (6, 8, 10, 12):
        for n in range(19, 29):
            p = g.profile(n, d)
            assert p["largest_block_s2_halved"] > g.KERNEL_CEILING   # RED on every in-range cell


def test_verdict_is_red():
    # regression lock: this gate is RED. A GREEN/AMBER here means the block formula was changed — re-review.
    rows = [g.profile(n, d) for d in g.SWEEP_D for n in range(19, 29)]
    over = [r for r in rows if r["largest_block_s2_halved"] > g.KERNEL_CEILING]
    assert len(over) == len(rows)


def test_three_point_stays_On_for_contrast():
    # the three-point (Schrijver) largest block is n+1 (O(n)) — the contrast that makes GATE 0 decisive
    assert g.profile(28, 6)["three_point_largest"] == 29
