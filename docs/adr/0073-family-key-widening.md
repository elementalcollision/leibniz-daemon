# ADR 0073 — Family-key widening: the non-modular genres steer too

- Status: accepted
- Date: 2026-07-24
- Depends on: ADR 0034 (genre-kill + the coarseness tension), ADR 0069 (dry-ground retirement),
  ADR 0070 (the factorial/gcd fragment whose claims this now keys)

## Context

`DiscoveryNotebook` retires exhausted genres two ways: `genre_kill` (ADR 0034 — a family the
daemon keeps *proving*) and `dry_kill` (ADR 0069 — a family that keeps coming back KNOWN/TRIVIAL
and never proves). Both key on `_family()`, which derived its key solely from
`congruence_signature()` — a **novelty-gate** component that recognizes polynomial congruences and
nothing else.

Two defects fell out of that, both measured against the live 85-row ledger:

1. **27 rows (32%) got no family at all** — 12 min/max, 1 factorial, 14 modular *inequalities*.
   The daemon has promulgated **three min/max laws**, and the nightly notebook shows
   `family_counts: {}` against `proven: 1`: the min/max genre was invisible to genre-kill and
   could be mined forever. Two of the three published min/max laws are in fact the same identity
   (one strictly subsumes the other) — precisely the redundancy genre-kill exists to prevent.
2. **9 rows (11%) got a *garbage* key.** For a boolean combination of congruences,
   `congruence_signature` returns `(connective, (atom, atom, …))` — so `sig[1]` is the nested atom
   tuple, not a modulus, and the old `f"{relop}|{m}"` interpolated the **whole polynomial** into
   the key: `and|(('atom','!=',5,((0,1),(1,1),(2,1))),…)`. Such a key can never group across
   polynomials (genre-kill inert) and pollutes the `_FAMILY_CAP`-bounded histogram with singletons.
   One of the nine is a kernel-verified law.

## Decision

`_family()` becomes three layers. `congruence_signature` is **not touched** — it is a novelty-gate
soundness component, and this is proposal-side steering; widening it would change what the gate
calls KNOWN.

1. **Plain congruence atom** — the original key, byte-identical (`==|3`, `in|8`, …), now guarded by
   `isinstance(sig[1], int)`. Persisted `family_counts`/`dry_counts` keep working across the
   upgrade.
2. **Boolean combination of congruences** — key on connective + the **modulus set**, polynomial
   dropped: `and|5` → "and-combinations of modular claims modulo 5". This is the bug fix.
3. **Named-function genres** (`_shape_family`) — min/max, factorial, gcd keyed as
   (genre × top-level relation × modulus set): `minmax|==`, `factorial|ineq`, `factorial%5|!=`,
   `gcd|or`. A claim with **no** named function and no congruence still yields **no family**:
   "polynomial inequality" is far too broad a genre to retire on three proofs — the ADR 0034
   coarseness tension, resolved conservatively.

Also fixed here (same failure mode, different state): the heartbeat pinned
`LEIBNIZ_RUNTIME_DB` and `LEIBNIZ_FRONTIER_STATE` canonically but never `LEIBNIZ_NOTEBOOK_PATH`,
so `discovery.py`'s package-relative default put the nightly notebook **inside the throwaway sync
worktree** — disjoint from the band and ledger, and one `git clean -xfd` from gone. `beat()` now
`setdefault`s it under `LEIBNIZ_HEARTBEAT_HOME`. Pinned in Python rather than the launchd
bootstrap so it takes effect on the next `origin/main` sync with no LaunchAgent reinstall.

## Consequences

Measured on the live ledger: **0 regressions** (every claim holding a clean key keeps the
identical key), 13 rows newly keyed, 9 garbage keys repaired, 14 deliberately left keyless.
`minmax|==` already holds **4** members against `genre_threshold = 3` — the genre would have
retired before the subsumed law was proposed.

One existing ADR 0034 assertion was deliberately inverted: `_family("gcd(n, n+1) == 1")` was
pinned as `None` ("outside the DSL"); it is now `gcd|==`. The invariant that line protected — an
*unrecognized* shape must never mint a family — is preserved in place with a bare polynomial
inequality. No trust surface is involved: `_family` steers the conjecturer's prompt and decides
nothing; the gates and the kernel are untouched.
