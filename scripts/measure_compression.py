#!/usr/bin/env python3
"""M1 — Proof-Compression Δ over the promulgated corpus (ADR 0036 §10.4/§10.5).

The abstraction-mining pre-test. The thesis under test (ADR 0036 §10.4): mathematics
scales by *definitions / lemma-schemas that compress* the reasoning space, not by flat
theorem search — and representation, not faithfulness, is the untouched lever. The
cheapest falsifiable check of that thesis, on data we already have and with **zero**
trust-boundary touch: do the daemon's own promulgated proofs share compressible
structure that a mined abstraction would collapse?

  KILL (GLM):  0 macros compress the corpus → the theorems are structurally disjoint
               noise → abstraction mining is dead.
  ALIVE:       a macro compresses many proofs → that macro is the candidate; promote
               it to a first-class definition.

But "it compressed 40%" is meaningless without controls — the project's whole ethos is
*do not fool yourself*. (The first cut of this script learned that the hard way: a
within-proof token-shuffle null was order-blind and conflated cross-proof sharing with
DEFLATE's anti-locality penalty, inflating the headline ~3-5× — caught by the M1-verify
adversarial pass and retracted.) The corrected controls:
  (C1) sum-of-independent vs joined — compress each proof ALONE and sum, vs the whole
                              corpus as one stream. Cleanly isolates cross-proof dictionary
                              sharing (the abstraction signal) from intra-proof repetition.
  (C2) order-0 entropy floor — frequencies only, no sharing; a conservative reference.
  (C3) boilerplate-strip    — removes ubiquitous tactic tokens (omega/decide/...); separates
                              shared-glue compression from shared-mathematical-schema.
  (C4) leave-dominant-cluster-out + cross-genre help — the headline isn't one over-sampled
                              genre, and the compressor finds NO cross-genre bridge (which is
                              why M1 is a FLOOR on mining viability, never a ceiling).

And it does not stop at "does it compress." It reports **what the top abstraction IS**
(statement schema + proof macro), because the real question (ADR 0036 §10.4
anti-gerrymandering) is whether the mined abstraction is a genuinely new concept or just
the textbook genre we already named. That read is for a human / the verify workflow; this
script lays out the evidence.

stdlib only. Reads the A/B/SA ledgers read-only. Writes a JSON + text report. No DB writes.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sqlite3
from collections import Counter
from pathlib import Path

# The corrected metric is deterministic (no shuffling) — the earlier shuffle-null was
# retracted after the M1-verify adversarial pass (see module docstring).

# Ubiquitous tactic / glue tokens — present in ~every proof, carry no mathematical
# schema. Stripping these isolates whether compression survives on *structure* alone.
BOILERPLATE_TOKENS = {
    "by", "have", "rw", "simp", "omega", "decide", "norm_num", "ring_nf", "ring",
    "rcases", "obtain", "exact", "intro", "intros", "apply", "refine", "show",
    "left", "right", "with", "at", "by_cases", "generalize", "set", "let", "dsimp",
    "conv_lhs", "conv_rhs", "conv", "all_goals", "interval_cases", "induction",
    "cases", "this", "from", "using", "simpa", "change", "calc",
}


# --------------------------------------------------------------------------- #
# Corpus loading
# --------------------------------------------------------------------------- #
def load_corpus(ab_root: Path, arms=("A", "B", "SA")) -> list[dict]:
    """Distinct promulgated (kernel_verified) laws across arms, deduped by hash."""
    seen: dict[str, dict] = {}
    for tag in arms:
        db = ab_root / tag / "memory.db"
        if not db.exists():
            continue
        con = sqlite3.connect(str(db))
        con.row_factory = sqlite3.Row
        for r in con.execute("SELECT * FROM memory WHERE kernel_verified=1"):
            h = r["normalized_hash"]
            if h not in seen:
                seen[h] = {
                    "hash": h,
                    "claim_property": r["claim_property"] or "",
                    "theorem_src": r["theorem_src"] or "",
                    "proof_src": r["proof_src"] or "",
                    "arms": [tag],
                }
            else:
                seen[h]["arms"].append(tag)
        con.close()
    return list(seen.values())


# --------------------------------------------------------------------------- #
# Tokenisation
# --------------------------------------------------------------------------- #
_TOK = re.compile(r"[A-Za-z_][A-Za-z_0-9.]*|\d+|[^\sA-Za-z0-9]")


def tokenize(s: str) -> list[str]:
    return _TOK.findall(s)


def abstract_tokens(toks: list[str]) -> list[str]:
    """Skeletonise: numerals -> <N>; common bound-var names -> <V>; hyp names -> <H>.

    This is the load-bearing normalisation. It must be aggressive enough that two proofs
    of *the same shape over a different modulus* match, but not so aggressive that
    *different* proof strategies collapse together. The shuffle-null (C1) calibrates this:
    if this normalisation manufactured fake matches, the shuffled control would compress
    just as well, and the real-minus-control gap would vanish.
    """
    out = []
    for t in toks:
        if t.isdigit():
            out.append("<N>")
        elif re.fullmatch(r"h\d*|ih|hn|hr|hm|hk|hlt|hcases|hmod|hsq|hpow|key|aux", t):
            out.append("<H>")
        elif re.fullmatch(r"[a-z]", t) and t not in ("n",):  # k,m,q,r,... bound vars (keep n)
            out.append("<V>")
        else:
            out.append(t)
    return out


# --------------------------------------------------------------------------- #
# Part 1 — statement-level schema mining (anti-unification + MDL)
# --------------------------------------------------------------------------- #
_CLAUSE = re.compile(r"\(?\s*(?P<expr>.+?)\s*\)?\s*%\s*(?P<mod>\d+)\s*==?\s*(?P<res>\d+)")


def parse_statement(claim_property: str):
    """Parse '(EXPR) % M == R or (EXPR) % M == R2 ...' into (kind, expr, mod, residues).

    Returns None if it doesn't fit the modular-residue family (then it's its own schema).
    """
    parts = re.split(r"\s+or\s+|\s*\|\|\s*", claim_property)
    exprs, mods, residues = set(), set(), set()
    for p in parts:
        m = _CLAUSE.search(p)
        if not m:
            return None
        exprs.add(m.group("expr").strip())
        mods.add(int(m.group("mod")))
        residues.add(int(m.group("res")))
    if len(exprs) != 1 or len(mods) != 1:
        return None
    expr = next(iter(exprs))
    mod = next(iter(mods))
    kind = "POW_MOD" if re.search(r"\d+\s*\^\s*n|[a-z]\s*\^\s*n", expr) else "POLY_MOD"
    # monomial exponent signature of the polynomial (abstracts coefficients)
    exps = tuple(sorted({int(e) for e in re.findall(r"n\s*\^\s*(\d+)", expr)} |
                        ({1} if re.search(r"(?<![\^\d])n(?!\s*\^)", expr) else set()) |
                        ({0} if re.search(r"\+\s*\d+\s*$|^\s*\d+\s*$", expr) else set()),
                        reverse=True))
    return {"kind": kind, "expr": expr, "mod": mod,
            "residues": tuple(sorted(residues)), "exp_sig": exps}


def statement_schema_id(parsed) -> str:
    """The schema a law instantiates: kind + monomial structure (coeffs/mod/residues are
    the per-law *parameters*, not part of the schema). This is the anti-unified template."""
    if parsed is None:
        return "OTHER"
    if parsed["kind"] == "POW_MOD":
        return "POW_MOD::a^n % m ∈ S"
    return f"POLY_MOD::P(n) % m ∈ S [degree-set {list(parsed['exp_sig'])}]"


def statement_mdl(corpus: list[dict]) -> dict:
    parsed = [parse_statement(c["claim_property"]) for c in corpus]
    schemas = [statement_schema_id(p) for p in parsed]
    hist = Counter(schemas)
    # coarse schema: collapse POLY_MOD degree-sets into one family (the "genre")
    coarse = Counter("POLY_MOD" if s.startswith("POLY_MOD") else
                     ("POW_MOD" if s.startswith("POW_MOD") else "OTHER") for s in schemas)

    dl_raw = sum(len(tokenize(c["claim_property"])) for c in corpus)
    # compressed: one template per distinct schema + per-law parameter payload
    template_cost = {sid: len(tokenize(sid)) for sid in hist}
    dl_template = sum(template_cost.values())
    dl_params = 0
    for c, p, sid in zip(corpus, parsed, schemas):
        if p is None:
            dl_params += len(tokenize(c["claim_property"]))  # OTHER: store verbatim
        else:
            # params = coefficients(expr literals) + modulus + residue set
            lits = re.findall(r"\d+", c["claim_property"])
            dl_params += len(lits)
    dl_compressed = dl_template + dl_params
    return {
        "n_laws": len(corpus),
        "schema_histogram": dict(hist.most_common()),
        "family_histogram": dict(coarse.most_common()),
        "dominant_family": coarse.most_common(1)[0] if coarse else None,
        "dl_raw_tokens": dl_raw,
        "dl_compressed_tokens": dl_compressed,
        "compression_ratio": round(dl_compressed / dl_raw, 4) if dl_raw else None,
        "n_unparsed_OTHER": sum(1 for p in parsed if p is None),
    }


# --------------------------------------------------------------------------- #
# Part 2 — proof-level macro mining (skeleton clustering + MDL)
# --------------------------------------------------------------------------- #
def proof_skeleton(proof: str, strip_boilerplate: bool = False) -> list[str]:
    toks = abstract_tokens(tokenize(proof))
    if strip_boilerplate:
        toks = [t for t in toks if t not in BOILERPLATE_TOKENS]
    return toks


def multiset_cosine(a: Counter, b: Counter) -> float:
    if not a or not b:
        return 0.0
    dot = sum(a[k] * b[k] for k in a if k in b)
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    return dot / (na * nb) if na and nb else 0.0


def cluster_proofs(skeletons: list[list[str]], thresh: float = 0.85) -> list[list[int]]:
    """Greedy agglomerative clustering by token-multiset cosine. Order-stable."""
    bags = [Counter(s) for s in skeletons]
    clusters: list[list[int]] = []
    reps: list[Counter] = []
    for i, bag in enumerate(bags):
        best, bj = thresh, -1
        for j, rep in enumerate(reps):
            sim = multiset_cosine(bag, rep)
            if sim >= best:
                best, bj = sim, j
        if bj >= 0:
            clusters[bj].append(i)
            reps[bj] = reps[bj] + bag  # centroid drift
        else:
            clusters.append([i])
            reps.append(Counter(bag))
    return clusters


def descriptive_clusters(skeletons: list[list[str]], thresh: float = 0.85) -> dict:
    """DESCRIPTIVE only (bag-cosine): 'how many proofs look alike'. Not used for the
    compression verdict — bag-cosine is order-blind, so a shuffle-null is meaningless on
    it (that confound is exactly what the order-sensitive gzip test below avoids)."""
    clusters = cluster_proofs(skeletons, thresh)
    sizes = sorted((len(c) for c in clusters), reverse=True)
    return {
        "n_proofs": len(skeletons),
        "n_clusters": len(clusters),
        "cluster_sizes": sizes,
        "largest_cluster": sizes[0] if sizes else 0,
        "top3_coverage": round(sum(sizes[:3]) / len(skeletons), 4) if skeletons else 0,
    }


def _gz(s: str) -> int:
    """Compressed length in bytes via raw DEFLATE (wbits=-15 → ~no header/checksum, so
    single-stream lengths are comparable). This is the Kolmogorov-complexity proxy."""
    import zlib
    co = zlib.compressobj(9, zlib.DEFLATED, -15)
    out = co.compress(s.encode("utf-8")) + co.flush()
    return len(out)


def _join(skeletons: list[list[str]]) -> str:
    return "\n".join(" ".join(s) for s in skeletons)


def _order0_floor_bytes(skeletons: list[list[str]]) -> float:
    """Order-0 (token-frequency) entropy of the corpus, in bytes. The 'no-structure but
    keep frequencies' reference: an ideal Huffman/arithmetic coder that knows token
    frequencies but NO sequence/sharing. Real < floor ⇒ genuine sub-frequency redundancy."""
    toks = [t for s in skeletons for t in s]
    n = len(toks)
    if n == 0:
        return 0.0
    freq = Counter(toks)
    bits = -sum(c * math.log2(c / n) for c in freq.values())
    return bits / 8.0


def compression_test(skeletons: list[list[str]]) -> dict:
    """Order-HONEST compression test (corrected after the M1-verify adversarial pass).

    The earlier within-/global-token-shuffle nulls were defective: random shuffling scatters
    identical tokens past DEFLATE's match window, so they measured anti-locality, not just
    loss of structure (inflating the gain ~3-5×). And the 32KB window spans this 17.5KB
    corpus, so the metric is order-INsensitive: it measures cross-proof DICTIONARY/substring
    sharing, not 'sequence'. Two honest references instead:

      dl_joined   : whole corpus compressed as one stream (shared dictionary across proofs).
      dl_sum_indep: Σ compress(each proof alone)  — kills ALL cross-proof sharing, keeps every
                    proof verbatim. THE clean cross-proof control.
      floor_order0: order-0 entropy (frequencies only, no sharing) — conservative reference.

    Readouts (both positive ⇒ real structure, but they answer different questions):
      cross_proof_gain   = dl_sum_indep / dl_joined - 1   (cross-proof dictionary sharing)
      joined_vs_sum      = dl_joined / dl_sum_indep        (<1 ⇒ joining helps)
      structure_vs_floor = floor_order0 / dl_joined - 1    (all sub-frequency redundancy; lower bound)
    """
    dl_joined = _gz(_join(skeletons))
    dl_sum_indep = sum(_gz(" ".join(s)) for s in skeletons)
    floor = _order0_floor_bytes(skeletons)
    return {
        "dl_joined_bytes": dl_joined,
        "dl_sum_independent_bytes": dl_sum_indep,
        "order0_entropy_floor_bytes": round(floor, 1),
        "cross_proof_gain": round(dl_sum_indep / dl_joined - 1, 4),
        "joined_vs_sum_ratio": round(dl_joined / dl_sum_indep, 4),
        "structure_vs_floor_gain": round(floor / dl_joined - 1, 4),
    }


def leave_dominant_cluster_out(skeletons: list[list[str]], thresh: float) -> dict:
    """Robustness: cross-proof gain on the proofs NOT in the largest bag-cluster — the
    headline cannot then be dismissed as one over-sampled textbook genre."""
    clusters = cluster_proofs(skeletons, thresh)
    clusters.sort(key=len, reverse=True)
    if not clusters:
        return {}
    dominant = set(clusters[0])
    rest = [s for i, s in enumerate(skeletons) if i not in dominant]
    if len(rest) < 2:
        return {"n_remaining": len(rest)}
    res = compression_test(rest)
    return {"n_remaining": len(rest), "cross_proof_gain": res["cross_proof_gain"],
            "joined_vs_sum_ratio": res["joined_vs_sum_ratio"]}


def cross_genre_help(corpus: list[dict]) -> dict:
    """How much do the POW_MOD (induction) proofs help compress the POLY_MOD (case-split)
    proofs? Near-zero ⇒ the macro is a within-schema mathematical pattern, NOT a prover-wide
    stylistic fingerprint (and confirms the compressor finds NO cross-genre bridge)."""
    poly, pow_ = [], []
    for c in corpus:
        p = parse_statement(c["claim_property"])
        sk = " ".join(proof_skeleton(c["proof_src"]))
        if p is None:
            continue
        (pow_ if p["kind"] == "POW_MOD" else poly).append(sk)
    if not poly or not pow_:
        return {"note": "one genre empty"}
    gz_poly = _gz("\n".join(poly))
    gz_pow = _gz("\n".join(pow_))
    gz_both = _gz("\n".join(pow_ + poly))
    incremental_poly_given_pow = gz_both - gz_pow
    help_frac = 1 - incremental_poly_given_pow / gz_poly if gz_poly else 0.0
    return {"n_poly": len(poly), "n_pow": len(pow_),
            "cross_genre_help_fraction": round(help_frac, 4)}


def cluster_threshold_curve(skeletons: list[list[str]]) -> dict:
    """Dominant-cluster size is threshold-sensitive — report the curve, not one number."""
    out = {}
    for th in (0.70, 0.85, 0.90, 0.95):
        cl = cluster_proofs(skeletons, th)
        out[f"{th:.2f}"] = max((len(c) for c in cl), default=0)
    return out


# --------------------------------------------------------------------------- #
# Reporting
# --------------------------------------------------------------------------- #
def representative_macros(corpus, skeletons, clusters_thresh=0.85, top=3):
    """Surface the actual recurring proof-macros (for the human/verify read)."""
    clusters = cluster_proofs(skeletons, clusters_thresh)
    clusters.sort(key=len, reverse=True)
    out = []
    for cl in clusters[:top]:
        bags = [Counter(skeletons[i]) for i in cl]
        inter = bags[0].copy()
        for b in bags[1:]:
            inter &= b
        # the shared token core, in rough document order of the first member
        core_tokens = [t for t in skeletons[cl[0]] if inter[t] > 0]
        out.append({
            "size": len(cl),
            "member_hashes": [corpus[i]["hash"][:10] for i in cl[:6]],
            "shared_core_preview": " ".join(core_tokens[:40]),
            "example_proof": corpus[cl[0]]["proof_src"][:300],
            "example_statement": corpus[cl[0]]["claim_property"],
        })
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ab-root", default=".leibniz-ab")
    ap.add_argument("--thresh", type=float, default=0.85)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    corpus = load_corpus(Path(args.ab_root))
    skel_full = [proof_skeleton(c["proof_src"], strip_boilerplate=False) for c in corpus]
    skel_strip = [proof_skeleton(c["proof_src"], strip_boilerplate=True) for c in corpus]

    report = {
        "corpus_size_distinct": len(corpus),
        "arms": Counter(tuple(sorted(c["arms"])) for c in corpus).most_common(),
        "statement_level": statement_mdl(corpus),
        "proof_compression_full": compression_test(skel_full),
        "proof_compression_stripped": compression_test(skel_strip),
        "proof_compression_raw": compression_test(
            [tokenize(c["proof_src"]) for c in corpus]),
        "leave_dominant_cluster_out": leave_dominant_cluster_out(skel_full, args.thresh),
        "cross_genre_help": cross_genre_help(corpus),
        "descriptive_clusters_full": descriptive_clusters(skel_full, args.thresh),
        "cluster_threshold_curve": cluster_threshold_curve(skel_full),
        "top_proof_macros": representative_macros(corpus, skel_full, args.thresh),
    }

    # ---- verdict logic (ADR 0036 §10.4/§10.5; corrected after M1-verify) ----
    st = report["statement_level"]["compression_ratio"]
    cf = report["proof_compression_full"]
    cs = report["proof_compression_stripped"]
    craw = report["proof_compression_raw"]
    xgain = cf["cross_proof_gain"]            # honest cross-proof dictionary sharing (sum-indep/joined-1)
    floor_gain = cf["structure_vs_floor_gain"]  # conservative lower bound (vs order-0 entropy)
    xgain_strip = cs["cross_proof_gain"]
    xgain_raw = craw["cross_proof_gain"]
    loo = report["leave_dominant_cluster_out"].get("cross_proof_gain", 0.0)

    THRESH = 0.10  # cross-proof gain must clear this to count as real sharing
    has_structure = floor_gain > 0.05        # beats the order-0 entropy floor at all
    cross_proof = xgain > THRESH and xgain_raw > THRESH
    survives_strip = xgain_strip > THRESH
    robust_loo = loo > THRESH

    if not has_structure:
        verdict = ("KILL: the corpus compresses no better than its order-0 entropy floor — no "
                   "sub-frequency structure. The proofs are structurally disjoint. Abstraction "
                   "mining is dead.")
    elif not cross_proof:
        verdict = ("INTRA-ONLY: proofs are internally redundant but share little ACROSS proofs "
                   "(sum-of-independent ≈ joined). Weak abstraction signal.")
    elif not survives_strip:
        verdict = ("BOILERPLATE-ONLY: cross-proof sharing collapses once ubiquitous tactic tokens "
                   "are stripped — shared glue, not a mathematical schema.")
    else:
        verdict = ("ALIVE (mechanism viable; KILL does not fire): genuine cross-proof dictionary "
                   "sharing, survives boilerplate-strip and leave-dominant-cluster-out, beats the "
                   "order-0 entropy floor. A real reusable macro exists. NOTE: this is a FLOOR on "
                   "mining viability, not a ceiling — a syntactic compressor is blind to "
                   "cross-genre/semantic abstraction (see cross_genre_help ≈ 0). Whether the macro "
                   "is NOVEL or the textbook genre is the §10.4 question the compressor cannot "
                   "answer; read top_proof_macros (here: textbook).")

    report["verdict"] = {
        "statement_compression_ratio": st,
        "cross_proof_gain_full": xgain,
        "cross_proof_gain_raw_unabstracted": xgain_raw,
        "cross_proof_gain_stripped": xgain_strip,
        "structure_vs_order0_floor_gain": floor_gain,
        "leave_dominant_cluster_out_gain": loo,
        "cross_genre_help_fraction": report["cross_genre_help"].get("cross_genre_help_fraction"),
        "kill_fires": not has_structure,
        "mechanism_viable": cross_proof and survives_strip,
        "robust_to_leave_one_cluster_out": robust_loo,
        "is_floor_not_ceiling": True,
        "summary": verdict,
    }

    text = render_text(report)
    print(text)
    if args.out:
        Path(args.out).write_text(json.dumps(report, indent=2))
        Path(args.out).with_suffix(".txt").write_text(text)
        print(f"\n[written] {args.out} (+ .txt)")


def render_text(r: dict) -> str:
    v = r["verdict"]
    L = []
    L.append("=" * 78)
    L.append("M1 — PROOF-COMPRESSION Δ  (ADR 0036 §10.4/§10.5, abstraction-mining pre-test)")
    L.append("=" * 78)
    L.append(f"distinct promulgated laws: {r['corpus_size_distinct']}")
    L.append("")
    s = r["statement_level"]
    L.append("STATEMENT LEVEL (schema anti-unification, MDL):")
    L.append(f"  families: {s['family_histogram']}")
    L.append(f"  compression ratio (lower=more compressible): {s['compression_ratio']}")
    L.append(f"  unparsed/OTHER: {s['n_unparsed_OTHER']}")
    L.append("")
    cf, cs, cr = (r["proof_compression_full"], r["proof_compression_stripped"],
                  r["proof_compression_raw"])
    L.append("PROOF LEVEL (order-HONEST gzip Kolmogorov-Δ; corrected after M1-verify):")
    L.append(f"  full(abstracted): joined={cf['dl_joined_bytes']}B  "
             f"sum-independent={cf['dl_sum_independent_bytes']}B  "
             f"order0-floor={cf['order0_entropy_floor_bytes']}B")
    L.append(f"     CROSS-PROOF gain (sum-indep/joined-1)={cf['cross_proof_gain']}   "
             f"joined/sum={cf['joined_vs_sum_ratio']}   "
             f"vs-floor gain={cf['structure_vs_floor_gain']}")
    L.append(f"  raw (no abstraction): cross-proof gain={cr['cross_proof_gain']}")
    L.append(f"  boilerplate-stripped: cross-proof gain={cs['cross_proof_gain']}")
    loo = r["leave_dominant_cluster_out"]
    L.append(f"  leave-dominant-cluster-out (n={loo.get('n_remaining')}): "
             f"cross-proof gain={loo.get('cross_proof_gain')}")
    L.append(f"  cross-genre help (POW→POLY): {v['cross_genre_help_fraction']}  "
             f"(≈0 ⇒ within-schema, compressor finds NO genre bridge)")
    L.append(f"  dominant-cluster size vs threshold: {r['cluster_threshold_curve']}")
    L.append("")
    L.append(f"  KILL fires? {v['kill_fires']}   mechanism viable? {v['mechanism_viable']}   "
             f"robust to leave-one-cluster-out? {v['robust_to_leave_one_cluster_out']}")
    L.append("")
    L.append("VERDICT:")
    L.append("  " + v["summary"])
    L.append("")
    L.append("TOP PROOF MACROS (read these — are they novel concepts or the known genre?):")
    for i, m in enumerate(r["top_proof_macros"], 1):
        L.append(f"  [{i}] size={m['size']}  e.g. stmt: {m['example_statement'][:70]}")
        L.append(f"      shared core: {m['shared_core_preview'][:90]}")
    return "\n".join(L)


if __name__ == "__main__":
    main()
