"""Guard the constant-weight (Johnson-scheme) Terwilliger build — D1 of the discovery pivot
(scripts/terwilliger_cwc_{beta,dual,sdp,cert,probe}.py). The free-CPU legs (structure, real-code PSD
differential oracle, mechanical dual, snapshot parsing/classification) run in CI; solver and kernel legs
need cvxpy/sdpap/docker (operator-local) and SKIP cleanly. Trust-relevant assertions: real constant-weight
codes' blocks are exactly PSD and a corrupted β breaks that (the transcription oracle has teeth); the
mechanically-collected dual equals the Lagrangian; a solved bound never floors below a known lower bound;
gate cells reproduce Schrijver Table II; and the probe classifies candidates only above the known lb."""
from __future__ import annotations

import importlib.util
import json
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


def test_dual_check_feasibility_conjuncts_have_teeth():
    # THE DECIDER's PSD + nonnegativity conjuncts must actually gate: weakening either should be catchable.
    n, d, w = 7, 4, 3
    base = tcd._zero_duals(n, w)                          # zero duals: psd_ok & nonneg_ok hold (only residuals fail)
    chk = tcd.dual_check(n, d, w, base)
    assert chk["psd_ok"] is True and chk["nonneg_ok"] is True
    # a negative multiplier breaks nonneg_ok
    neg = tcd._zero_duals(n, w)
    neg["g"][next(iter(neg["g"]))] = Fr(-1)
    assert tcd.dual_check(n, d, w, neg)["nonneg_ok"] is False
    # a non-PSD Z block breaks psd_ok
    badz = tcd._zero_duals(n, w)
    kl = next(iter(badz["Z"]))
    m = len(badz["Z"][kl])
    badz["Z"][kl] = [[Fr(-1) if a == b else Fr(0) for b in range(m)] for a in range(m)]
    assert tcd.dual_check(n, d, w, badz)["psd_ok"] is False
    # an ASYMMETRIC Z whose symmetric part is indefinite must ALSO break psd_ok. Use [[1,4],[0,1]]: bare
    # is_psd_exact ACCEPTS it (it reads only the lower triangle, so the 4 is invisible), so this uniquely
    # exercises the _sym gate — its symmetric part [[1,2],[2,1]] has a negative eigenvalue.
    asym = tcd._zero_duals(n, w)
    kl2 = next(k for k in asym["Z"] if len(asym["Z"][k]) >= 2)
    M = asym["Z"][kl2]
    M[0][0] = M[1][1] = Fr(1)
    M[0][1] = Fr(4)                                       # M[1][0] stays 0 -> asymmetric; bare LDLᵀ says "PSD"
    assert tcd.is_psd_exact(M) is True                    # the trap: the unguarded test is fooled
    assert tcd.dual_check(n, d, w, asym)["psd_ok"] is False   # the _sym gate is not


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


def test_probe_classify_row_optimistic_boundary_and_below_lb_alarm():
    snap = {"20,6,8": {"lb": 588, "ub": 1084, "ub_source": "Po"}}
    # a raw optimum a hair below the ub floors UP to the ub under the +1e-6 acceptance bump — the optimistic
    # candidacy gate must still flag it so the exact leg gets a chance (else a true tightening is missed).
    row = tp.classify_row({"n": 20, "d": 6, "w": 8, "sdp_floor": 1084, "sdp_value_raw": 1083.9999997}, snap, {})
    assert row["candidate"] is True
    # a genuine reproduction (raw value at/above the ub) is NOT a candidate
    row = tp.classify_row({"n": 20, "d": 6, "w": 8, "sdp_floor": 1084, "sdp_value_raw": 1084.3}, snap, {})
    assert row["candidate"] is False
    # a solver OPTIMUM below the known lb (no accepted floor) is a soundness red flag, surfaced for the alarm
    row = tp.classify_row({"n": 20, "d": 6, "w": 8, "sdp_floor": None, "below_lb_floor": 500}, snap, {})
    assert row["above_known_lb"] is False and row["candidate"] is False


def test_probe_verdict_semantics():
    assert tp.verdict_of([], []) == "DRY"
    assert tp.verdict_of([{"n": 1}], [{"certified": False}]) == "DRY"
    assert tp.verdict_of([{"n": 1}], [{"certified": True}]) == "GREEN(candidate)"
    assert tp.verdict_of([{"n": 1}], [], no_escalate=True).startswith("UNESCALATED")
    # a candidate whose exact-LP decider time-capped/errored (decided False) is UNDECIDED, never DRY
    assert tp.verdict_of([{"n": 1}], [{"certified": False, "decided": False}]).startswith("UNDECIDED")
    assert tp.verdict_of([{"n": 1}], [{"certified": False, "decided": True}]) == "DRY"
    # a solved bound below a known lower bound outranks everything: SOUNDNESS-ALARM
    assert tp.verdict_of([], [], soundness_alarms=[{"n": 1}]).startswith("SOUNDNESS-ALARM")
    assert tp.verdict_of([{"n": 1}], [{"certified": True}],
                         soundness_alarms=[{"n": 1}]).startswith("SOUNDNESS-ALARM")


def test_probe_parse_d4_optimum_noub_and_duplicate():
    # d=4 section: lower-bounds-only, a trailing dot marks an optimum (lb=ub); `-...` = no explicit ub.
    html = ('<h1><a name="d4">Bounds on A(n,4,w)</a></h1>\n'
            '<table><tr><th>n\\w</th><th>3</th><th>4</th></tr>\n'
            '<tr><th>7</th><td>7.</td><td>2<sup>x</sup>-...</td></tr></table>')
    cells, unparsed = tp.parse_andw_html(html)
    assert unparsed == []
    assert cells[(7, 4, 3)] == {"lb": 7, "ub": 7, "exact": True, "lb_source": "", "ub_source": ""}
    assert cells[(7, 4, 4)]["lb"] == 2 and cells[(7, 4, 4)]["ub"] is None
    # duplicate (n,d,w) with a DIFFERENT lb across two matrices: first wins, the clash is recorded (not dropped)
    dup = ('<h1><a name="d6">Bounds on A(n,6,w)</a></h1>'
           '<table><tr><th>n\\w</th><th>4</th></tr><tr><th>10</th><td>5</td></tr></table>'
           '<table><tr><th>n\\w</th><th>4</th></tr><tr><th>10</th><td>9</td></tr></table>')
    cells2, unparsed2 = tp.parse_andw_html(dup)
    assert cells2[(10, 6, 4)]["lb"] == 5
    assert any("DUPLICATE" in u.get("text", "") for u in unparsed2)


def test_probe_parse_td_labeled_row():
    # Brouwer marks some rows' n-label as <td> (e.g. n=33..35 in d=18); a <th>-only match dropped them whole.
    html = ('<h1><a name="d6">Bounds on A(n,6,w)</a></h1>'
            '<table><tr><th>n\\w</th><th>4</th><th>5</th></tr>'
            '<tr><td>33</td><td>5</td><td>6<sup>s</sup>-9</td></tr></table>')
    cells, unparsed = tp.parse_andw_html(html)
    assert unparsed == []
    assert cells[(33, 6, 4)]["lb"] == 5 and cells[(33, 6, 5)]["ub"] == 9


def test_snapshot_checked_in_and_validated_shape():
    # The committed snapshot must load, contain the gate cells, and honor ub >= lb.
    snap = tp.load_snapshot()
    cells = snap["cells"]
    assert cells["17,6,7"]["lb"] == 166 and cells["17,6,7"]["ub"] == 206
    assert cells["18,6,6"]["lb"] == 133
    assert all(c["ub"] is None or c["ub"] >= c["lb"] for c in cells.values())
    assert snap["_meta"]["cross_check"]["lb_diffs"] == []
    # a <td>-labeled row the old <th>-only parser dropped is now present (n=33, d=18)
    assert "33,18,10" in cells
    # provenance is real, not a defaulted empty hash
    assert len(snap["_meta"]["sha256_page"]) == 64


def test_cert_artifact_flagship_kernel_consistency():
    # The shipped headline — A(17,6,7)<=228 at P=1e14, kernel-attested — is pinned to its actual parameter
    # path, and the kernel must attest the SAME certificate whose bound the artifact records (not a re-solve).
    cert = json.loads((_ROOT / "docs" / "results" / "terwilliger_cwc_cert.json").read_text())
    assert cert["verdict"] == "GREEN"
    assert cert["kernel_attests_recorded_cert"] is True
    k = cert["a17_6_7_kernel"]
    assert isinstance(k, dict) and k.get("sound") is True
    row = next(r for r in cert["rows"] if (r["n"], r["d"], r["w"]) == (17, 6, 7))
    assert row["certified"] is True and row["P"] == 10 ** 14 and row["floor"] == 228
    assert "duals" not in row                             # duals must never leak into the artifact


def test_kernel_verify_lp_incomplete_census_and_uncertified(monkeypatch):
    tcc = _load("terwilliger_cwc_cert", "scripts/terwilliger_cwc_cert.py")
    n, d, w = 7, 4, 3
    expected = 2 * len(tcc.tc.block_pairs(w, n - w))
    assert expected > 1
    # a certified cert whose rendered block census is SHORT (a singular block dropped) is a render failure,
    # never sound: kernel_verify_lp must refuse before ever calling the kernel.
    fake = {"certified": True, "duals": {"stub": True}, "target": 7, "exact_bound": "7", "floor": 7}
    monkeypatch.setattr(tcc.cert, "cert_psd_blocks",
                        lambda duals: [{"M": [[1]], "L": [[1]], "d": [1], "scale": 1}])
    out = tcc.kernel_verify_lp(n, d, w, target=7, cert_row=fake)
    assert isinstance(out["kernel"], str) and "render_incomplete" in out["kernel"]
    assert out["expected_blocks"] == expected and out["n_blocks"] == 1
    # an uncertified cert_row is never rendered
    out2 = tcc.kernel_verify_lp(n, d, w, target=7, cert_row={"certified": False})
    assert out2["certified"] is False and "no exact LP cert" in out2["note"]


# ---- solver legs (operator-local; CI-skip) ----------------------------------------------------------------

@_needs
def test_small_cells_reproduce_known_A():
    tcs = _load("terwilliger_cwc_sdp", "scripts/terwilliger_cwc_sdp.py")
    for (n, d, w), expected in (((7, 4, 3), 7), ((6, 4, 3), 4), ((5, 2, 2), 10)):
        assert (n, d, w) in tcs.LOWER                     # the soundness key must exist (no silent no-op)
        r = tcs.run_numerical(n, d, w)
        assert r["sdp_floor"] == expected
        assert r["valid_bound"] is True                  # KeyError = coverage loss, made loud (not defaulted)


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
