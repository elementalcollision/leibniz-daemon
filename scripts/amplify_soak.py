"""Amplify batch soak + idempotency (validation plan Tier 0, R0.7).

Drives the amplification spine over a large SYNTHETIC mixed feed (valid CWC + covering, exact duplicates,
reordered duplicates, malformed entries, unsupported domains, and false witnesses) into a THROWAWAY corpus
(never the committed docs/results/amplification_corpus.json), with the kernel step OFF (pre-check only), and
checks the durability properties the banked Track-A product needs:

  - no exception on the full feed; audited + skipped == feed length
  - merge is idempotent: merge(C, audited) twice == once (re-running the spine does not grow the corpus)
  - merge is order-independent: shuffling the audited rows yields the same corpus
  - witness_sha is order-insensitive (reordered duplicates dedup to one row)
  - false/adversarial witnesses are audited but NEVER counted verified (the display gate holds)
  - witness_sha collisions at scale are 0 on the synthetic corpus

Pure stdlib + the project's own modules. No kernel, no trust touch.
"""
from __future__ import annotations

import importlib.util
import json
import random
import sys
import time
from itertools import combinations
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
OUT = _ROOT / "docs" / "results" / "amplify_soak.json"


def _load(mod_name: str, rel: str):
    spec = importlib.util.spec_from_file_location(mod_name, _ROOT / rel)
    m = importlib.util.module_from_spec(spec)
    sys.modules.setdefault(mod_name, m)
    spec.loader.exec_module(m)
    return m


amp = _load("amplify", "scripts/amplify.py")


def _valid_covering_entry(v, k, t, source):
    blocks = [list(c) for c in combinations(range(v), k)]   # all-k-subsets: a valid covering
    return {"domain": "covering", "v": v, "k": k, "t": t, "blocks": blocks, "source": source}


def _valid_cwc_entry(n, d, w, m, source):
    # a content-trivial but well-formed CWC witness; verify may reject (distance) but it must not crash
    code = [sorted(random.sample(range(n), w)) for _ in range(m)]
    return {"domain": "cwc", "n": n, "d": d, "w": w, "code": code, "source": source}


def build_feed(target: int = 800, seed: int = 0xA11CE) -> list[dict]:
    rng = random.Random(seed)
    feed: list[dict] = []
    cov_cells = [(5, 3, 2), (6, 3, 2), (7, 3, 2), (6, 4, 2), (8, 4, 3)]
    while len(feed) < target:
        roll = rng.random()
        if roll < 0.45:
            v, k, t = rng.choice(cov_cells)
            feed.append(_valid_covering_entry(v, k, t, f"soak-cov-{len(feed)}"))
        elif roll < 0.60:
            feed.append(_valid_cwc_entry(rng.choice([10, 12, 13]), 6, 5, rng.randint(3, 8),
                                         f"soak-cwc-{len(feed)}"))
        elif roll < 0.72:  # exact duplicate of the previous entry
            if feed:
                feed.append(json.loads(json.dumps(feed[-1])))
        elif roll < 0.84:  # reordered-blocks duplicate (same witness, different order)
            if feed and feed[-1]["domain"] == "covering" and "blocks" in feed[-1]:
                dup = json.loads(json.dumps(feed[-1]))
                rng.shuffle(dup["blocks"])
                for b in dup["blocks"]:
                    rng.shuffle(b)
                feed.append(dup)
        elif roll < 0.90:  # false covering: drop a symbol entirely
            v, k, t = rng.choice(cov_cells)
            blocks = [list(c) for c in combinations(range(v - 1), k)]   # symbol v-1 absent -> uncovered
            feed.append({"domain": "covering", "v": v, "k": k, "t": t, "blocks": blocks,
                         "source": f"soak-false-{len(feed)}"})
        elif roll < 0.96:  # unsupported domain
            feed.append({"domain": "ramsey", "foo": 1, "source": f"soak-unsup-{len(feed)}"})
        else:              # malformed entry (missing required keys)
            feed.append({"domain": "covering", "source": f"soak-malformed-{len(feed)}"})
    return feed


def run_soak(feed: list[dict]) -> dict:
    t0 = time.perf_counter()
    reports = [amp.amplify_one(e, run_kernel=False) for e in feed]
    audited = [r for r in reports if "skipped" not in r]
    skipped = [r for r in reports if "skipped" in r]

    merged1 = amp.merge_corpus([], audited)
    merged2 = amp.merge_corpus(merged1, audited)           # idempotence: re-merge same audits
    shuffled = list(audited)
    random.Random(7).shuffle(shuffled)
    merged_shuf = amp.merge_corpus([], shuffled)           # order independence

    idempotent = json.dumps(merged1) == json.dumps(merged2)
    order_independent = json.dumps(merged1) == json.dumps(merged_shuf)
    n_verified = sum(1 for r in merged1 if amp._verified(r))
    n_false_audited = sum(1 for r in audited if not r.get("verify_ok", False))
    false_verified = sum(1 for r in merged1 if not r.get("verify_ok", False) and amp._verified(r))

    keys = [amp.corpus_key(r) for r in merged1]
    shas = [r["witness_sha"] for r in merged1]
    # collisions: distinct (domain,cell,size,source) sharing a witness_sha but a different witness
    collisions = 0
    seen: dict[str, str] = {}
    for r in merged1:
        sig = json.dumps(r["witness"], sort_keys=True)
        prev = seen.get(r["witness_sha"])
        if prev is not None and prev != sig:
            collisions += 1
        seen[r["witness_sha"]] = sig

    return {
        "feed": len(feed), "audited": len(audited), "skipped": len(skipped),
        "covers_feed_length": len(audited) + len(skipped) == len(feed),
        "corpus_unique": len(merged1), "unique_keys": len(set(keys)) == len(merged1),
        "idempotent": idempotent, "order_independent": order_independent,
        "verified_in_corpus": n_verified, "false_witnesses_audited": n_false_audited,
        "false_witnesses_verified": false_verified,   # MUST be 0
        "witness_sha_collisions": collisions,          # MUST be 0
        "distinct_witness_sha": len(set(shas)),
        "wall_secs": round(time.perf_counter() - t0, 2),
    }


def main() -> int:
    feed = build_feed()
    res = run_soak(feed)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(res, indent=2) + "\n")
    ok = (res["covers_feed_length"] and res["unique_keys"] and res["idempotent"]
          and res["order_independent"] and res["false_witnesses_verified"] == 0
          and res["witness_sha_collisions"] == 0)
    print("amplify batch soak (throwaway corpus, no kernel):")
    for k, v in res.items():
        print(f"  {k}: {v}")
    print(f"  VERDICT: {'PASS' if ok else 'FAIL'}")
    print(f"  -> {OUT}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
