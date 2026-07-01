<!--
Research-ingestion -> amplification pipeline: baseline scoping + the measure-before-build probe result +
the non-trust triage adapter that was built. No trust-core change; no PROTECTED file touched; audit-tier.
-->

# Research-ingestion → amplification: baseline (Track 3, 2026-06-30)

## The vision and the honest reality
The amplification spine (`scripts/amplify.py`) kernel-verifies externally-supplied finite constructions
into an audit-tier corpus. The vision: feed it automatically from the literature (the arxiv scraper at
`.../arxiv_feed`). This scopes and builds the **baseline** of that loop.

**What exists:** the scraper is real and running (weekly, ~120 Leibniz records/run) — but each record is
**title + abstract + citation only** (no PDF, no LaTeX, no enumerated witnesses). The
`seeds → amplify_seeds → amplify` chain exists but is **severed at the first joint**:
`seeds.seed_from_feed_record` only ever emits `TARGET`/`HINT` seeds (never a `CONSTRUCTION` seed with a
`witness`), so nothing from the feed can reach `amplify_seeds` today. The corpus is fed only by hand.

**The hard wall (why full auto-ingestion is not feasible now):** the spine needs an *explicit finite
witness* (the enumerated codewords/blocks). Papers publish **methods and theorems** (e.g. "a cyclic
construction over Z_n with base block B"), not the expanded witness — and the feed does not even fetch the
full text. Reconstructing a witness from a method is exactly the *producer* the D0/Track-D arc measured as
the binding wall; it is a research task, not parsing. So the automated **witness** yield from the feed is
~zero. The feed's genuine role is **surfacing, provenance, and triage** — with the sound checkers deciding.

## Measure-before-build probe (run first, as the program's discipline requires) — **RED**
Scanned the 5 weekly runs on disk (2026-06-21 … latest, **220 unique records**) for records that both
mention a supported domain (cwc / covering) **and** carry a parseable inline witness (a list-of-lists):

```
unique records: 220 | cwc-mention: 0 | covering-mention: 0 | with inline witness: 0
VERDICT: RED
```

The Leibniz feed is complexity / logic / number-theory heavy; **0 records** carry an extractable witness in
a supported domain. So per the probe's exit criterion, we **build the triage/worklist half only** and shelve
the automated *witness* on-ramp (it would require full-text pull + domain-specific reconstruction, a
separately-scoped bet, or human/stronger-producer witnesses).

## What was built (baseline — non-trust, no PROTECTED file touched)
`scripts/ingest_candidates.py` — the on-ramp adapter. It reads `leibniz.json` and:
- **classifies** each record's `domain_guess` (lexical cwc / covering / none — a router hint; a wrong guess
  is harmless: a malformed/absent witness is `skipped` by `amplify_one` or kernel-rejected);
- **extracts an explicit witness only if one is structurally present** (a `witness` field — the clean
  automatable case; it **never fabricates** a witness from free-text abstracts);
- routes: explicit-witness records → an **amplify-ready candidate feed** (the kernel decides downstream via
  the unchanged `amplify.py`); everything else with a domain mention → an **operator worklist**
  (`ingestion_worklist.md`) tagged "needs reconstruction."

On the live feed this yields **0 candidates** (RED) and a worklist noting the honest emptiness — the machinery
is proven on a fixture (`tests/test_ingest_candidates.py`: a structured Fano covering / CWC witness flows to
an amplify-ready candidate; a covering *mention* and a numbers-in-prose abstract both go to the worklist and
are never fabricated into a witness).

## Trust analysis
- **No LLM decides.** The adapter is pure lexical classification + literal-witness parsing. The Lean kernel
  + the validated oracle remain the sole deciders, via the unchanged `amplify.amplify_one` path.
- **Never promulgates.** The path terminates in the audit-tier corpus; it never calls `discharge`, sets
  `kernel_verified`, or touches `TrustPolicy`.
- **PROTECTED files are fixed seams.** `seeds.py` / `seed_intake.py` are read-only; the adapter builds
  amplify-shaped dicts directly and does not add a `SeedKind` or change validation.
- **The witness is the only untrusted surface**, and the kernel re-checks it; provenance (`proof_of_use` =
  the citation) rides along.

## Out of baseline (separate, gated slices)
- **Full-text pull + domain-specific witness reconstruction** — the real "producer"; large, separately
  scoped; only worth it if a domain with reachable headroom is found (see the novelty-frontier scout).
- **Making `seed_from_feed_record` emit CONSTRUCTION seeds** — `seeds.py` is PROTECTED (operator-gated).
- **Promulgating a verified construction** — ADR 0045, 8/8 DEFERRED pending a real record beat.
- **Adding a new amplification domain** — a new `*_check.py` + Lean renderer + oracle, gated by the Gate-B0
  4-way criterion.

## Bottom line
The baseline is a small, honest thing: a non-trust **triage + provenance adapter** that connects the
severed first joint and routes the (currently zero) explicit-witness records to the kernel and everything
else to an operator queue. Automated *discovery* from the feed is not reachable now — consistent with the
program's measured conclusions (no reachable beat; verification-amplification is the home). The value here
is surfacing + provenance + a fixture-tested on-ramp ready for the day a witness source (human, stronger
producer, or a reconstruction slice) exists.
