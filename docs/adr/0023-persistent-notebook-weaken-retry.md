# ADR 0023 — Persistent discovery notebook + weaken-and-retry throughput (lever 1)

Status: **Accepted** (2026-06-22)
Extends: ADR 0018 (discovery frontier), ADR 0019 (persist the band).

## Context

The ADR 0022 calibration moved the binding blocker downstream to the **prover**:
`reached_proof` rose 0 → 31/39, but 0 promulgated — conjectures reach the kernel and
the HF ensemble cannot close them under N+1 consensus. The cheapest lever to a *first*
promulgation is **weaken-and-retry**: turn those UNPROVEN near-misses into strictly-
weaker, still-novel variants and try again, leaning on the difficulty thermostat that
already eases the band off when nothing proves.

The machinery exists (`weakening_seeds`, the `too_hard` bucket, the controller) but two
things blunt it:

1. **The `DiscoveryNotebook` is recreated fresh every run** (`build_daemon` →
   `DiscoveryNotebook()`). The frontier *band* persists (ADR 0019), but the actual
   *near-misses to weaken* do not — so the 31 just discovered evaporate at process
   exit. There is nothing to "retry" on the next run.
2. **Low throughput**: `weaken_k = 2` and `capacity = 6` mean only the 2 oldest of the
   6 most-recent near-misses are mined per cycle.

## Decision

Pure proposal-side, no trust edge (mirrors the ADR 0019 band-persistence exactly):

1. **Persist the notebook.** `DiscoveryNotebook` gains `to_dict`/`from_dict`/`save`/
   `load` (a missing/corrupt file → a fresh notebook, so cold start / CI is unchanged),
   persisting to `.leibniz/notebook.json` (gitignored, per-machine). `build_daemon`
   resumes it; `run_cycles` and the calibration harness save it each cycle. Near-misses
   now **accumulate across runs**, so weaken-and-retry keeps working the same frontier.

2. **Raise throughput, configurably.** `weaken_k` (env `LEIBNIZ_WEAKEN_K`, default
   `2 → 3`) and notebook `capacity` (env `LEIBNIZ_NOTEBOOK_CAP`, default `6 → 12`) are
   wired through `build_daemon`. More near-misses accumulate and more weaker variants
   are proposed per cycle.

3. **Weaken the freshest near-misses.** `weakening_seeds` now targets the most recent
   `k` (`statements[-k:]`) — the candidates just seen to reach proof yet not close are
   the best retry targets — instead of the oldest `k`.

The depth-1 *echo guard* (never weaken a statement that already carries the weakening
instruction) is **kept**: it stops a verbatim-echoing provider's compounding loop. For
an honest provider a weakened *claim* carries no marker, so legitimate progressive
weakening across cycles already happens and is unaffected — the guard is a safety net,
not a limiter.

## Why this is trust-safe

- **Entirely proposal-side.** No edit to `trust.py`, `verifiers.py`, the gates, or
  `tests/test_invariants.py` (byte-identical). Every weakened variant still runs the
  full cheap gates + the kernel's N+1 consensus; the kernel and Z3 still decide.
- The notebook holds only **claim/outcome strings** for steering — never a verdict,
  never a trust edge. A corrupt/forged `notebook.json` can at worst feed bad *seeds*;
  it cannot promulgate anything (the gates and kernel are unchanged), and load() falls
  back to a fresh notebook on any parse error.
- Persistence is capacity-bounded (no unbounded growth) and dedup'd.

## Consequences

- Near-misses accumulate; a stubborn conjecture is weakened again on subsequent runs
  until it either proves (a modest but real first promulgation + a stepping stone) or
  is abandoned as the window rolls.
- The path to a first promulgation now runs through grinding the weakened frontier —
  complementary to lemma decomposition (ADR 0024), which attacks the hard ones by
  splitting them rather than weakening them.

## Adversarial review hardening (2026-06-22)

A two-lens review (trust-safety / robustness), every finding verified against running
code, **confirmed the trust boundary is intact** (a forged `notebook.json` can at most
inject *seed strings* into the conjecturer; the resulting claims still face novelty +
faithfulness + the kernel's N+1 consensus — nothing reaches a verdict). It also found
robustness footguns on the new knobs, all fixed:

- **(HIGH) `weaken_k = 0` weakened *everything*.** `fresh[-0:]` is the whole list, not
  none — so `LEIBNIZ_WEAKEN_K=0` would fire a billable prover pass per accumulated
  near-miss. `weakening_seeds` now guards `k <= 0 → []`.
- **(HIGH) `capacity = 0` grew without bound.** `del bucket[:-0]` is a no-op; `_push`
  now treats `cap < 1` as "disabled" (keeps nothing).
- **(MEDIUM) a non-dict `notebook.json` crashed startup** (uncaught `AttributeError`,
  contradicting the "corrupt → fresh" claim). `from_dict` now guards `isinstance(d,
  dict)` and per-bucket `isinstance(list)` — in **both** `DiscoveryNotebook` and
  `FrontierController` (the latter had the identical latent crash).
- **(LOW) a non-numeric env knob crashed assembly** → a tolerant `_env_int` helper
  falls back to the default on garbage/blank.

Regression tests cover every case (`k<=0`, `cap=0`, non-dict/wrong-typed payloads on
both loaders, `_env_int`).

## Validation

- Unit: notebook round-trips through `save`/`load`; missing/corrupt/non-dict → fresh;
  `load` respects a new capacity; the daemon writes the notebook each cycle;
  `weakening_seeds` targets the most recent `k` and refuses `k<=0`; `cap<=0` keeps
  nothing; the echo guard still stops marked instructions.
- Live (billable): a weaken-heavy calibration that resumes the accumulated notebook,
  measuring whether any weakened near-miss closes at the kernel (the first promulgation).
