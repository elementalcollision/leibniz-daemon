# ADR 0095 — A toolchain bump moves the keys, not the proofs

- Status: **accepted — landed 2026-09-10. Full suite 1875 passed / 0 failed, kernel lane 35 passed /
  0 skipped, the ADR 0017/0033 publish gate green on all 27 published laws, adversarially reviewed**
- Date: 2026-09-10
- Amends: ADR 0003 (the `leibniz-lean:v4.31.0` pin), ADR 0011 (the repl pin and its rebuild order)
- Depends on: ADR 0012 (module index toolchain-versioned), ADR 0015 (the corpus hash is
  toolchain-specific — first time that sentence has been cashed), ADR 0033 (per-run provenance),
  ADR 0048 (Lean stays the sole proof-edge decider), ADR 0052/0078 (the self-dedup keys that also
  move), ADR 0089 (the `#print axioms` parse contract, measured on 4.31), ADR 0093 (a lane that
  cannot run must say so), ADR 0096 (the `native_decide` fail-open this work found)

## Context

`lean4` [#14684](https://github.com/leanprover/lean4/issues/14684): `String.Pos.Raw.extract`
disagrees between its Lean definition and its C++ runtime at enormous slice bounds. Its reproducer
proves `False` and reads it out as Fermat's Last Theorem. Run unmodified:

| toolchain | `#reduce` | `#eval` | the false theorem `flt` |
|---|---|---|---|
| v4.31.0 (**current pin**) | `""` | `"a truly marvelous proof"` | **accepted** — `[…, flt._native.native_decide.ax_1_1]` |
| v4.33.1 | `""` | `"a truly marvelous proof"` | **accepted** — same footprint |
| v4.34.0-rc2 | `""` | `""` | **rejected** — falls back to `sorryAx` |

It reproduces through the project's own images too. But **the fix that matters most is not #14684**.
Alongside it (#14717) and a use-after-free at gigantic slice limits reachable from safe Lean
(#14687), v4.34.0 carries **#14838** — *"memory corruption when an object's 32-bit reference count
overflows… could be used to trigger use-after-free in the official kernel, which could be extended
into a proof of `False`."* #14684 leaves a trace in the axiom footprint, which is why an axiom check
can see it; #14838 is an unsoundness *inside* the trusted kernel, so the footprint is clean and no
axiom-level guard can see it. Taking the fixed kernel is the whole defence.

Separately, this work found `axiom_closure` is absent from the path that mints `kernel_verified`, so
invariant 8 is unenforced on the LLM-authored proof path. Older than this bump, survives it, decided
in **ADR 0096**.

## The measurement — what did not churn

The predicted cost was Mathlib churn in `docs/crt`, `docs/erdos` and the `*_decided` renderings. It
did not materialise. All 39 checked-in `.lean` artifacts, elaborated in both images:

```
v4.31.0   37 passed, 2 failed      v4.34.0-rc2   37 passed, 2 failed
per-file verdict diff              IDENTICAL on all 39
```

Both failures pre-exist on 4.31 and would have been easy to misattribute without the baseline
(`maximum recursion depth`; an olean absent from both images). Every import path used is unchanged,
the repo has zero uses of the 4.32–4.34 breaking renames, and the kernel lane reports **34 passed,
0 skipped**.

**One fragment's gate was re-run, not the trust surface.** `verify_lean_decided.py` covers the
`lean_decided` residue backend *only*; it clears (9/9 attacks DEFER, 2/2 controls PASS, 3/3 Euclidean
canaries). Of the repo's 30 `verify_*.py` gates — including `verify_ceiling_raiser_soundness.py`,
which covers the other five fragments — **29 were not run**.

## The measurement — what did churn

`pytest -q` gives **4 failed, 1871 passed, 47 skipped**; the same four pass 13/13 on 4.31. Two causes.
The first is one Mathlib rewrite in three files: `rw [Matrix.mul_apply, …]` in
`scripts/beyond_markov_{necklace,positive_realization,process}_lean.py` no longer matches.

The second is that **the identity keys moved**. Re-elaborating `corpus/known_results.json`:
**36 unchanged, 15 changed, 0 failed**. The 15 are *exactly* the entries whose `theorem_src` contains
`^`, measured both directions. Not a Lean-core change — Mathlib split `Monoid.toPow` into
`Monoid.toNPow ∘ NPow.toPow`, so the canonical fold gains two constant names and two `.app` nodes
where the `HPow` instance sat; it rides in via `lakefile.toml`'s Mathlib `rev`.

`formal_hash` is the novelty gate's identity key (`corpus.py:51`). A stale key **misses**, and the
gate is kill-only, so every miss lands on the **false-NOVEL** side — a known result promulgated as a
discovery. Confirmed by simulation against the real `NoveltyGate`. Backstops cover part and no more:
structural congruence catches **8 of 15** (`fermat_little_11/13` exceed `MAX_EXP = 8`; five carry no
`claim_property`), ADR 0086 subsumption **0**, ADR 0078 textual `alt_hashes` **0 of the corpus**.

**The ledger re-hashes too.** Of 63 promulgated kernel-verified rows, 24 carry the elaborator scheme
and **22 change** — again the `^`-bearing ones, including `n_pow4_mod5`/`n_fourth_mod_five`, the pair
ADR 0078 cites as why that scheme exists. Those are records; they cannot be regenerated.

## Decision 1 — move the pin, rebuild both images base-first

`lean-toolchain`, `lakefile.toml`'s Mathlib `rev`, both Dockerfiles (repl clone at
`--branch v4.34.0-rc2`), `DEFAULT_IMAGE`, `REPL_IMAGE`. ADR 0011's order holds and its
`RUN lake build Mathlib` stays. The `lakefile.toml` rev is load-bearing: without it `lake update`
resolves Mathlib v4.31.0 against a 4.34 toolchain and the build fails.

**Build commands move with the pin; they are not prose.** The Dockerfile takes its Lean from
`lean-toolchain`, so `-t` is the only thing setting the label: `-t leibniz-lean:v4.31.0` against the
now-4.34 Dockerfile mints a 4.34 image *wearing the 4.31 tag*, destroying the one provenance signal
there is. All four were moved with it — `README.md:141-142`,
`docs/runbooks/terwilliger-sdp-cli.md:59`, `tests/test_lean_backend_r1.py:7`,
`tests/test_lean_repl_r0011.py:7`.

**One literal, derived everywhere.** `lean_cli.KERNEL_VERSION` is now the single source of truth:
`DEFAULT_IMAGE`, `REPL_IMAGE`, the Newton folio emitter and the two tests that had pinned a version
string all derive from it, so the next pin move cannot leave a stale literal behind. That closes the
trap this ADR documents in Decision 3 rather than resetting it one version along.

**This pins production to a release candidate.** v4.34.0 stable is not out; mathlib4 master is on rc2
and both it and `leanprover-community/repl` carry the tag. The trade is deliberate: the alternative
is running a kernel with a known route to a proof of `False`.

## Decision 2 — regenerate the keys, and treat that as the trust-surface change

`scripts/build_corpus.py` regenerates the corpus; the three literals in
`test_corpus_known_families_r0031.py:24-26` move with it. `corpus/mathlib_modules.json` regenerates
from the new image (8,169 → 8,370 modules, all three `test_import_resolver_r412` assertions holding).
Regeneration produced 51 entries, 15 changed, 0 dropped, 0 added, and all 15 changed entries contain
`^` — the prediction above, confirmed by the run. The pin move is mechanical; **this** touches the
boundary and gets the ADR 0089 treatment — attacked before it is called sound. Note
`build_corpus.py:217-219` **fails open**: a non-elaborating entry
warns to stderr, `continue`s, and the script still exits 0, silently shrinking the corpus in the same
false-NOVEL direction. It did not bite here (0 failed).

## Decision 3 — put the staleness detector in a lane that runs

`test_novelty_corpus_r3.py::test_omega_n_log_n_rederivation_is_caught_known` is the only test that
recomputes a corpus hash live. It is failing right now, exactly as designed — and runs in **neither
enforced lane**: `skipif(not available())` skips it on GitHub-hosted `ci`, and it is not among the
three files `run_kernel_tests.sh` executed. **It is now in that list** (lane: 34 -> 35 tests, still
0 skipped). It re-elaborates *one* entry, and caught this bump only because that statement carries
`^` — so it is a tripwire, not coverage. `test_corpus_known_families_r0031.py` is not a
substitute: it compares the committed JSON against literals in the same file, so both go stale
together — it passes right now on a provably stale corpus, and goes red precisely when the corpus is
*correctly* regenerated.

**The mirror image sat in the blocking lane.** Neither `test_cwc_check.py:75` (`"v4.31.0" in
committed`) nor `test_newton_exchange.py:43` (`"Lean 4.31" in text`) carries a skip-guard, so both
were inside `ci.yml`'s blocking `pytest -q` and went **red** the moment the artifact and the emitter
were correctly updated. Both now assert against `KERNEL_VERSION` instead of a literal, which is the
only version of that test worth having.

## Decision 4 — the back-out is not a revert

Reverting the pin files alone restores the 4.31 kernel while leaving a 4.34-keyed corpus in place, so
every `^`-bearing entry misses under the restored kernel and — the gate being kill-only — misses as
NOVEL. **A half-revert re-creates the exact condition this ADR closes, in the direction nothing
detects.** The back-out is all-or-nothing and ordered: revert the pins, regenerate both corpora
against the restored image, restore the three literals, re-run the detector green. Do not delete the
4.31 images while rollback is plausible — a concurrent worktree is using them regardless. Moving
rc2 → stable later is this same procedure again, regeneration included.

## Consequences

**Touches the proof edge.** This swaps the kernel that is the sole decider of `kernel_verified` and
re-keys the novelty gate's identity map. `newton_exchange.py:114,125` *emits* `Lean 4.31` as a live
string and must move with the pin or it will mislabel post-bump folios.

**The ledger becomes mixed-version with no mechanical way to tell the versions apart.** `memory` has
no image, toolchain or run-id column and the journal stamps neither, so wall-clock `ts` is the only
separator — which fails the moment a rollback puts two toolchains on one day. `write_provenance`
exists for this and `assembly.py:441` says the run entrypoint calls it, but its only non-test caller
was `scripts/calibrate_discovery.py:92`: **6 provenance records against 453 ledger rows**. That was
treated as a prerequisite rather than a follow-up: `scripts/heartbeat.py::beat` now resolves the
instance config and calls `write_provenance` before it turns a cycle, and journals `instance`,
`lean_image` and `corpus_version` in every entry. Rows written from here on are attributable; the
453 already in the ledger are not, and cannot be made so.

**What this does not do:**

- It does not close the `native_decide` fail-open (ADR 0096), and does not defend against #14838 — a
  kernel-internal `False` has a clean footprint, so no in-repo guard can see it.
- The ADR 0017/0033 publish gate was run and is green: all 27 published laws re-elaborate on
  4.34.0-rc2 with footprints inside {propext, Classical.choice, Quot.sound}. Note the gate exits 0
  when the ledger file is simply ABSENT, so a green run means nothing unless the ledger resolved —
  that is a fail-open shape of its own and is not fixed here.
- It does not re-measure the ADR 0089 `#print axioms` parse contract, whose accepted report forms
  were "verified against live Lean 4.31".
- The one live guard that hardcoded the tag — `test_terwilliger_f2a.py:18`, a *false gate* rather
  than a skip — now reads `REPL_IMAGE`. What still says `4.31` is deliberate: the historical ADRs
  0003/0011/0088 (amended here, not rewritten), the dated measurement records under `docs/results/`,
  and the gate docstrings recording what was validated against 4.31 — five of the six fragments were
  NOT re-validated, so changing those would assert something untrue.
- It does not recover the alpha-rename-invariant key for the 22 historical ledger rows. Nothing can.
- No rebase was required: `origin/main` was still at `7f05d4a` when this landed, so every number
  here was taken against the merge base. A later rebase does not re-validate them.
- It does not touch ADR 0096. The `native_decide` fail-open survives this bump untouched, and its two
  build obligations are unmet.
