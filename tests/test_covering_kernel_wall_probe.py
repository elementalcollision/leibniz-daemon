"""Free-CPU guard for the GATE-2 covering decide-wall probe (validation plan Tier 2). The kernel timing
itself is docker-gated and run by hand via scripts/covering_kernel_wall_probe.py; here we only assert the
probe's witness construction and ladder are sound (so the kernel run measures a real, valid covering at each
rung). No docker, no kernel."""
from __future__ import annotations

import importlib.util
from math import comb
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent


def _load(mod_name, rel):
    import sys
    sys.path.insert(0, str(_ROOT))
    sys.path.insert(0, str(_ROOT / "scripts"))
    spec = importlib.util.spec_from_file_location(mod_name, _ROOT / rel)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


wall = _load("covering_kernel_wall_probe", "scripts/covering_kernel_wall_probe.py")
cov = _load("covering_verify", "scripts/covering_verify.py")


def test_ladder_is_increasing_in_t_subsets():
    sizes = [comb(v, t) for (v, k, t) in wall.LADDER]
    assert sizes == sorted(sizes), "ladder should be ordered by increasing C(v,t) so the wall is bracketed"
    assert all(1 <= t <= k <= v for (v, k, t) in wall.LADDER)


def test_witness_for_returns_a_valid_covering():
    # the rung witness must be a VALID covering, else the kernel run would measure a refused render
    for (v, k, t) in [(7, 3, 2), (9, 3, 2)]:
        blocks = wall.witness_for(v, k, t)
        ok, reason = cov.verify_covering([frozenset(b) for b in blocks], v, k, t)
        assert ok, f"witness_for({v},{k},{t}) is not a valid covering: {reason}"
        # and it must render without the false-theorem refusal firing
        src = cov.render_covering_lean(v, k, t, blocks)
        assert "validCovering" in src and src.rstrip().endswith("decide")
