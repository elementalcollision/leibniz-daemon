"""Guard the verification-amplification spine (ADR 0042 Track A, scripts/amplify.py).

The spine must: (1) audit a valid construction end-to-end through the sound path; (2) record provenance
(source, witness hash, cell); (3) flag a false witness without crashing the batch; (4) skip unsupported
domains / malformed entries rather than raising; (5) merge into a corpus with stable dedup; and
(6) render an audit-tier reading-room that NEVER claims promulgation. Kernel-free (no docker) so it runs
in CI — the kernel re-check itself is exercised by test_cwc_check / the live D0 run.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent


def _load(mod_name: str, rel: str):
    spec = importlib.util.spec_from_file_location(mod_name, _ROOT / rel)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


amp = _load("amplify", "scripts/amplify.py")

VALID = {"domain": "cwc", "n": 7, "d": 4, "w": 3, "code": [[0, 1, 2], [3, 4, 5]], "source": "test:valid"}
FALSE = {"domain": "cwc", "n": 7, "d": 4, "w": 3, "code": [[0, 1, 2], [0, 1, 3]], "source": "test:false"}


def test_amplify_one_valid_records_provenance_no_kernel():
    r = amp.amplify_one(VALID, run_kernel=False, stamp="2026-06-29")
    assert r["verify_ok"] is True
    assert r["domain"] == "cwc" and r["cell"] == "A(7,4,3)" and r["size"] == 2
    assert r["source"] == "test:valid" and r["stamped"] == "2026-06-29"
    assert r["witness_sha"] and r["code"] == [[0, 1, 2], [3, 4, 5]]
    assert r["kernel"] == "not run (--no-kernel)"          # audit-tier; no claim of verification


def test_amplify_one_false_witness_flagged_not_crashed():
    r = amp.amplify_one(FALSE, run_kernel=False)
    assert r["verify_ok"] is False and "skipped" not in r   # audited, just failed the pre-check


def test_unsupported_domain_is_skipped():
    r = amp.amplify_one({"domain": "graph", "source": "test:x"}, run_kernel=False)
    assert "skipped" in r and "unsupported domain" in r["skipped"]


def test_malformed_cwc_entry_is_skipped():
    r = amp.amplify_one({"domain": "cwc", "n": 7, "source": "test:x"}, run_kernel=False)  # no d/w/code
    assert "skipped" in r and "malformed" in r["skipped"]


def test_witness_hash_is_order_insensitive():
    a = amp._witness_hash([[0, 1, 2], [3, 4, 5]])
    b = amp._witness_hash([[5, 4, 3], [2, 1, 0]])           # same set, reordered
    assert a == b


def test_merge_corpus_dedups_and_new_wins():
    old = amp.amplify_one(VALID, run_kernel=False)
    old["kernel"] = "unavailable (Lean docker image not present)"
    new = amp.amplify_one(VALID, run_kernel=False)
    new["kernel"] = "KERNEL-VERIFIED"
    merged = amp.merge_corpus([old], [new])
    assert len(merged) == 1                                  # same witness+source dedups
    assert merged[0]["kernel"] == "KERNEL-VERIFIED"         # the newer (verified) record wins


def test_render_corpus_is_audit_tier_and_counts_verified():
    r = amp.amplify_one(VALID, run_kernel=False)
    r["kernel"] = "KERNEL-VERIFIED"
    md = amp.render_corpus([r])
    assert "A(7,4,3)" in md and "test:valid" in md
    assert "1/1 entries kernel-verified" in md
    # the banner must NOT let a reader mistake the corpus for promulgated law
    assert "not promulgated laws" in md.lower()
    assert "nothing here is in the codex" in md.lower()


def test_load_feed_accepts_list_and_wrapped(tmp_path):
    import json
    p1 = tmp_path / "list.json"
    p1.write_text(json.dumps([VALID]))
    p2 = tmp_path / "wrapped.json"
    p2.write_text(json.dumps({"constructions": [VALID]}))
    assert amp.load_feed(p1) == [VALID]
    assert amp.load_feed(p2) == [VALID]
