"""Guard the constant-weight (Johnson-scheme) Terwilliger build — D1 of the discovery pivot
(scripts/terwilliger_cwc_{beta,dual,sdp,cert,probe}.py). The free-CPU legs (structure, real-code PSD
differential oracle, mechanical dual, snapshot parsing/classification) run in CI; solver and kernel legs
need cvxpy/sdpap/docker (operator-local) and SKIP cleanly. Trust-relevant assertions: real constant-weight
codes' blocks are exactly PSD and a corrupted β breaks that (the transcription oracle has teeth); the
mechanically-collected dual equals the Lagrangian; a solved bound never floors below a known lower bound;
gate cells reproduce Schrijver Table II; and the probe classifies candidates only above the known lb."""
from __future__ import annotations

import importlib.util
from fractions import Fraction as Fr
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parent.parent
_HAS = importlib.util.find_spec("cvxpy") is not None and importlib.util.find_spec("numpy") is not None
_needs = pytest.mark.skipif(not _HAS, reason="cvxpy/numpy are operator-local; SDP legs skipped in CI")


def _load(mod, rel):
    spec = importlib.util.spec_from_file_location(mod, _ROOT / rel)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


tc = _load("terwilliger_cwc_beta", "scripts/terwilliger_cwc_beta.py")
tcd = _load("terwilliger_cwc_dual", "scripts/terwilliger_cwc_dual.py")
tp = _load("terwilliger_cwc_probe", "scripts/terwilliger_cwc_probe.py")


# ---- structure (free-CPU) ---------------------------------------------------------------------------------

def test_possible_matches_multinomials():
    # possible() ⟺ both Venn-cell multinomials are nonzero — the impossible-configuration trap (eq. 10).
    for w, v in ((3, 4), (4, 4), (5, 3)):
        for i in range(min(w, v) + 1):
            for j in range(min(w, v) + 1):
                for t in range(min(i, j) + 1):
                    for s in range(min(i, j) + 1):
                        expect = (tc._multinom(w, i - t, j - t, t) != 0
                                  and tc._multinom(v, i - s, j - s, s) != 0)
                        assert tc.possible(w, v, i, j, t, s) is expect


def test_canon_is_orbit_invariant_and_possible_is_orbit_constant():
    # The (65)(iii) orbit key: all six orderings of a realizable configuration share the key, and every
    # realized orbit has a possible representative (rep_quad round-trip).
    w, v = 4, 5
    for q in tc.valid_quads(w, v):
        key = tc.canon(*q)
        rep = tc.rep_quad(w, v, key)
        assert rep is not None
        assert tc.canon(*rep) == key


def test_classify_forbidden_band():
    # (65)(iv): distance 2h forbidden iff 1 <= 2h <= d-1; half-distances are what the key stores.
    assert tc.classify(((0, 2, 2), 0), 6) == "zero"       # distance 4 < 6
    assert tc.classify(((0, 3, 3), 0), 6) == "free"       # distance 6
    assert tc.classify(((0, 0, 0), 0), 6) == "free"       # the pinned y^{0,0}_{0,0}
    assert tc.classify(((3, 3, 4), 0), 8) == "zero"       # distance 6 < 8


def test_objective_is_johnson_inner_distribution():
    # Objective coeff C(w,i)C(v,i) exactly on the ((0,i,i),0) keys.
    w, v = 3, 4
    assert tc.obj_coeff(((0, 0, 0), 0), w, v) == 1
    assert tc.obj_coeff(((0, 2, 2), 0), w, v) == tc.C(3, 2) * tc.C(4, 2)
    assert tc.obj_coeff(((0, 2, 2), 1), w, v) == 0        # delta != 0 is not an inner-distribution key
    assert tc.obj_coeff(((1, 2, 2), 0), w, v) == 0


def test_real_codes_give_psd_blocks_and_identities():
    # The differential oracle: every real constant-weight code satisfies (64) — both families PSD, all
    # (k,l) — and the eq.(66) counting identity + (65)(iii) orbit merge hold exactly.
    for (n, w), code in (((7, 3), tc.FANO), ((9, 3), tc.STS9), ((6, 3), tc.johnson_space(6, 3))):
        assert tc.validate_code(n, w, code) is True
        assert tc.objective_identity_holds(n, w, code) is True
        assert tc.orbit_merge_holds(n, w, code) is True


def test_corrupt_beta_breaks_psd():
    # Teeth: the transposed-binomial corruption of the w-side factor must break PSD on a real code.
    broke = any(not tc.validate_code(n, w, code, beta_w=tc.tb.beta_corrupt)
                for (n, w), code in (((7, 3), tc.FANO), ((6, 3), tc.johnson_space(6, 3)),
                                     ((8, 4), tc.johnson_space(8, 4))))
    assert broke is True


def test_johnson_space_normalization_matches_eq66():
    # For the full Johnson space y^{0,0}_{i,0} = 1 and eq.(66) sums to C(n,w) (Vandermonde).
    n, w = 7, 3
    _y, y0 = tc.code_y(n, w, tc.johnson_space(n, w))
    assert all(y0[r] == 1 for r in range(min(w, n - w) + 1))
    assert sum(tc.C(w, i) * tc.C(n - w, i) * y0[i] for i in y0) == tc.C(n, w)


# ---- mechanical dual (free-CPU) ---------------------------------------------------------------------------

def test_dual_identity_and_teeth():
    for (n, d, w) in ((6, 4, 3), (7, 4, 3), (8, 4, 4)):
        assert tcd.identity_holds(n, d, w) is True
        assert tcd.identity_holds(n, d, w, corrupt=True) is False


def test_weak_duality_and_teeth():
    for (n, d, w) in ((7, 4, 3), (9, 4, 3)):
        assert tcd.weak_duality_holds(n, d, w) is True
        assert tcd.corruption_detected_wd(n, d, w) is True


def test_dual_check_zero_duals_infeasible():
    # Zero duals leave the OBJECTIVE coefficients as stationarity residuals: dual_check must refuse them
    # (a checker that accepted an all-zero "certificate" would be vacuous).
    duals = tcd._zero_duals(7, 3)
    chk = tcd.dual_check(7, 4, 3, duals)
    assert chk["feasible"] is False and chk["n_residuals_nonzero"] > 0 and chk["bound"] == 0


# ---- probe pure functions (free-CPU) ----------------------------------------------------------------------

def test_probe_cell_grammar():
    cases = {
        "22^{H}": (22, 22, "H", ""),
        "109^{G}-122": (109, 122, "G", ""),
        "320^{g}-424^{KKT}": (320, 424, "g", "KKT"),
        "33^{s Ö}": (33, 33, "s Ö", ""),
        "2": (2, 2, "", ""),
    }
    for txt, (lb, ub, lbs, ubs) in cases.items():
        m = tp._CELL_RE.match(txt)
        assert m, txt
        assert int(m.group(1)) == lb
        got_ub = int(m.group(5)) if m.group(5) else (None if m.group(7) else int(m.group(1)))
        assert got_ub == ub
        assert (m.group(3) or "") == lbs
        assert (m.group(6) or "") == ubs
    # `-...` = no explicit ub on the page
    m = tp._CELL_RE.match("7137^{g}-...")
    assert m and m.group(7) == "..."
    # d=4 optimum dot, both orders
    assert tp._CELL_RE.match("140.").group(2) == "."
    assert tp._CELL_RE.match("17^{R}.").group(4) == "."


def test_probe_parse_minimal_html():
    html = ('<h1><a name="d6">Bounds on A(n,6,w)</a></h1>\nprose\n<p>\n'
            "<table border=\"1\">\n<tr>\n<th>n\\w</th> <th>4</th> <th>5</th>\n</tr>\n"
            "<tr>\n<th>10</th><td>5<sup>s</sup></td><td class=\"be\">6<sup>s</sup>-9</td>\n</tr>\n</table>")
    cells, unparsed = tp.parse_andw_html(html)
    assert unparsed == []
    assert cells[(10, 6, 4)] == {"lb": 5, "ub": 5, "exact": True, "lb_source": "s", "ub_source": ""}
    assert cells[(10, 6, 5)] == {"lb": 6, "ub": 9, "exact": False, "lb_source": "s", "ub_source": ""}


def test_probe_classify_row_candidate_gate():
    snap = {"20,6,8": {"lb": 588, "ub": 1084, "ub_source": "Po"}}
    # a floor below the known lb is an artifact, never a candidate
    row = tp.classify_row({"n": 20, "d": 6, "w": 8, "sdp_floor": 500}, snap, {})
    assert row["above_known_lb"] is False and row["candidate"] is False
    # a floor in [lb, ub) is a candidate
    row = tp.classify_row({"n": 20, "d": 6, "w": 8, "sdp_floor": 900}, snap, {})
    assert row["above_known_lb"] is True and row["candidate"] is True
    # at/above the ub: reproduction or worse, not a candidate
    row = tp.classify_row({"n": 20, "d": 6, "w": 8, "sdp_floor": 1084}, snap, {})
    assert row["candidate"] is False


def test_probe_verdict_semantics():
    assert tp.verdict_of([], []) == "DRY"
    assert tp.verdict_of([{"n": 1}], [{"certified": False}]) == "DRY"
    assert tp.verdict_of([{"n": 1}], [{"certified": True}]) == "GREEN(candidate)"
    assert tp.verdict_of([{"n": 1}], [], no_escalate=True).startswith("UNESCALATED")


def test_snapshot_checked_in_and_validated_shape():
    # The committed snapshot must load, contain the gate cells, and honor ub >= lb.
    snap = tp.load_snapshot()
    cells = snap["cells"]
    assert cells["17,6,7"]["lb"] == 166 and cells["17,6,7"]["ub"] == 206
    assert cells["18,6,6"]["lb"] == 133
    assert all(c["ub"] is None or c["ub"] >= c["lb"] for c in cells.values())
    assert snap["_meta"]["cross_check"]["lb_diffs"] == []


# ---- solver legs (operator-local; CI-skip) ----------------------------------------------------------------

@_needs
def test_small_cells_reproduce_known_A():
    tcs = _load("terwilliger_cwc_sdp", "scripts/terwilliger_cwc_sdp.py")
    for (n, d, w), expected in (((7, 4, 3), 7), ((6, 4, 3), 4), ((5, 2, 2), 10)):
        r = tcs.run_numerical(n, d, w)
        assert r["sdp_floor"] == expected
        assert r.get("valid_bound", True) is True


@_needs
def test_gate_cell_reproduces_table_II():
    # ONE Table II gate cell in-test (the full gate is the results JSON): A(18,6,6) -> 199 (Delsarte 204).
    tcs = _load("terwilliger_cwc_sdp", "scripts/terwilliger_cwc_sdp.py")
    r = tcs.run_numerical(18, 6, 6)
    assert r["reproduces_table_II"] is True
    assert r["valid_bound"] is True


@_needs
def test_exact_lp_certifies_fano_cell():
    tcc = _load("terwilliger_cwc_cert", "scripts/terwilliger_cwc_cert.py")
    row = tcc.certify_lp(7, 4, 3, target=7)
    assert row.get("certified") is True
    assert row["floor"] == 7
    assert Fr(row["exact_bound"]) >= 7                    # never below the known optimum (soundness)
