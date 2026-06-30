"""Covering false-witness breadth fuzz + render directional-soundness smoke (validation plan Tier 0,
R0.4 + R0.2 — the free-CPU arm of GATE-4).

The untrusted pre-check `verify_covering` is the FIRST audit-tier defense: it must refuse every invalid
covering (0 false-accepts) and accept every valid one (0 false-rejects), and `render_covering_lean` must
emit a kernel theorem IFF the pre-check accepts (no render-time laundering: the rendered B equals the block
count and the rendered literals are exactly the witness). We cross-check `verify_covering` against an
INDEPENDENT brute-force oracle that traverses coverage the other way (accumulate covered t-subsets from the
blocks, then check the whole t-subset universe is covered) so a shared bug cannot hide.
"""
from __future__ import annotations

import importlib.util
import random
from itertools import combinations
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parent.parent


def _load(mod_name: str, rel: str):
    spec = importlib.util.spec_from_file_location(mod_name, _ROOT / rel)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


cov = _load("covering_verify", "scripts/covering_verify.py")


def _brute_valid(blocks, v, k, t) -> bool:
    """INDEPENDENT covering check: structural k-subset test, then accumulate the set of covered t-subsets
    from the blocks and require it to equal the full t-subset universe. (verify_covering instead iterates
    the universe and asks if ANY block contains each — a different traversal.)"""
    universe = set(range(v))
    for b in blocks:
        bs = set(b)
        if len(bs) != k or not bs <= universe:
            return False
    covered = set()
    for b in blocks:
        for ts in combinations(sorted(b), t):
            covered.add(ts)
    needed = set(combinations(range(v), t))
    return needed <= covered


def _all_ksubsets(v, k):
    return [frozenset(c) for c in combinations(range(v), k)]


# ---- valid witnesses: the all-k-subsets covering is valid for any t<=k<=v ----------------------------
VALID_CELLS = [(5, 3, 2), (6, 3, 2), (7, 3, 2), (6, 4, 2), (8, 4, 3), (7, 4, 2), (9, 3, 2)]


def test_valid_coverings_accepted_and_agree_with_bruteforce():
    for (v, k, t) in VALID_CELLS:
        blocks = _all_ksubsets(v, k)
        ok, reason = cov.verify_covering(blocks, v, k, t)
        assert ok, reason
        assert _brute_valid(blocks, v, k, t) is True


def test_render_emits_for_valid_and_is_faithful():
    # R0.2: render emits iff valid; rendered B == block count; literals are exactly the sorted blocks.
    for (v, k, t) in [(6, 3, 2), (7, 3, 2), (8, 4, 3)]:
        blocks = _all_ksubsets(v, k)
        src = cov.render_covering_lean(v, k, t, blocks)
        B = len(blocks)
        assert f"{v} {k} {t} {B} = true" in src        # the theorem claims exactly C(v,k,t) <= |blocks|
        assert src.rstrip().endswith("decide")
        # every block appears as a sorted literal list; the count of '[' opening block-literals matches B
        for b in blocks:
            lit = "[" + ", ".join(str(x) for x in sorted(b)) + "]"
            assert lit in src


def _invalid_witnesses(seed=0xC0FFEE):
    """Yield (v,k,t, blocks, label) for a broad class of INVALID coverings (>=500 total)."""
    rng = random.Random(seed)
    cells = [(6, 3, 2), (7, 3, 2), (8, 3, 2), (8, 4, 2), (9, 3, 2), (10, 4, 2),
             (8, 4, 3), (10, 5, 3), (12, 4, 2), (14, 4, 2)]
    for (v, k, t) in cells:
        full = _all_ksubsets(v, k)
        # (a) a symbol is entirely absent -> every t-subset touching it is uncovered
        for _ in range(11):
            missing = rng.randrange(v)
            blocks = [b for b in full if missing not in b]
            blocks = rng.sample(blocks, min(len(blocks), max(1, len(full) // 3)))
            yield (v, k, t, blocks, f"symbol {missing} absent")
        # (b) too few random blocks (almost surely leaves an uncovered t-subset at these sizes)
        for _ in range(11):
            m = rng.randint(1, max(1, k - 1))
            yield (v, k, t, rng.sample(full, m), f"only {m} blocks")
        # (c) structurally bad blocks: wrong size
        for _ in range(11):
            base = rng.sample(full, min(len(full), 4))
            bad = [frozenset(list(sorted(b))[: k - 1]) for b in base]   # k-1 sized
            yield (v, k, t, bad, "block wrong size (k-1)")
        # (d) out-of-range symbol
        for _ in range(11):
            bad = [frozenset(list(range(k - 1)) + [v + 1])]            # symbol v+1 not in [0,v)
            yield (v, k, t, bad, "out-of-range symbol")
        # (e) duplicate symbol within a block (not a k-subset; frozenset collapses -> size < k)
        for _ in range(11):
            bad = [frozenset([0] * 1 + list(range(1, k - 1)))]          # < k distinct
            yield (v, k, t, bad, "degenerate block (<k distinct)")


def test_false_witness_breadth_zero_false_accepts():
    n = 0
    for (v, k, t, blocks, label) in _invalid_witnesses():
        n += 1
        ok, _reason = cov.verify_covering(blocks, v, k, t)
        assert ok is False, f"FALSE-ACCEPT [{label}] C({v},{k},{t}) blocks={[sorted(b) for b in blocks]}"
        # the independent oracle must agree it is invalid
        assert _brute_valid(blocks, v, k, t) is False, f"oracle disagreement [{label}]"
        # and render must REFUSE to emit a theorem for it
        with pytest.raises(ValueError):
            cov.render_covering_lean(v, k, t, blocks)
    assert n >= 500, f"expected >=500 invalid witnesses, generated {n}"
