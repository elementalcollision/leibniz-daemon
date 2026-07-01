<!--
Session handoff for the three queued Terwilliger fresh sessions (tasks #99/#100/#101). Written to be the FIRST
file a fresh session reads: state snapshot, per-ticket spec with kickoff prompt, gates, pitfalls carried from
the 2026-07-01 session (things a cold session cannot cheaply re-derive), and process constants. The deep specs
for F1/F2a/F2b live in docs/terwilliger-formalization-scope-2026-07-01.md — this doc does not duplicate them.
-->

# Handoff — Terwilliger next sessions (2026-07-01)

## State snapshot (what is on `main` at `c666c8f`)

The SDP three-point producer is **complete at the audit tier** (`DUAL_CERTIFICATE_CHECKED`), PRs #216–#228:
**A(19,6) ≤ 1280** (Schrijver's Table I record; Delsarte LP gives 1289) is reproduced as an exact-rational
dual certificate and **kernel-attested** — the real Lean 4.31 kernel verifies all 20 PSD blocks and rejects a
corrupted one. Trust boundary untouched throughout (`tests/test_invariants.py` byte-identical).

**Code map** (all operator-local legs need cvxpy+numpy; kernel legs need docker + `leibniz-lean:v4.31.0`;
all present on the operator machine — verify with
`python3 -c "from leibniz.backends.lean_cli import available; print(available())"`):
- `scripts/terwilliger_beta.py` — validated integer β (eq. 7) + real-code PSD oracle.
- `scripts/terwilliger_dual.py` — reduced primal structure + the mechanical dual; **`collected()` is the
  authoritative spec of the stationarity system**; `dual_check()` is the exact checker.
- `scripts/terwilliger_sdp.py` — cvxpy primal (`run_numerical`, `build_labeled`); `TABLE_I`, `LOWER` dicts.
- `scripts/terwilliger_cert.py` — rationalize + clamp certifier (small cells), `cert_psd_blocks`,
  `render_cert_lean` (per-block theorems + `maxHeartbeats 0`), `kernel_verify`.
- `scripts/terwilliger_exact_lp.py` — **the workhorse**: `certify_lp(n,d,target,return_duals=)` (exact
  rational simplex; A(19,6) in ~17 s) and `kernel_verify_lp` (the Path B2 kernel leg).
- `scripts/terwilliger_scale_probe.py` — the n-scaling diagnostic.
- Tests: `tests/test_terwilliger_{beta,dual,sdp,cert,exact_lp,scale_probe}.py` (cvxpy/docker-gated, CI-skip).
- Results docs: `docs/results/terwilliger-*.md`; runbook: `docs/runbooks/terwilliger-sdp-cli.md`.

**Known numbers a fresh session should not re-measure:** A(19,6) full solve ~2 s (Clarabel,
`optimal_inaccurate` is NORMAL); exact LP cert ~17 s at P=1e10 (P=1e8 gives a valid-but-loose 1470 — precision
matters for the BOUND, not just PSD); kernel: 20 blocks in ~16 s valid / ~13 s bogus-reject; the LP-optimal
dual is sparse (55/4621 multipliers nonzero); nonzero β entries at n=19: 8076.

**Standing traps (each cost this session real time — do not rediscover):**
1. `check_source` returns **False on ANY elaboration failure** (resource errors included). Debugging a False:
   `bk._run_lean(src).output` for raw diagnostics. Never one giant `decide` conjunction — per-obligation
   theorems + `set_option maxHeartbeats 0`.
2. Impossible triples: `x^t_{i,j}=0` when `binom(n; i−t,j−t,t)=0` (i.e. `i+j−t>n`) — enforced by
   `td.possible()`; any new enumeration must use it (the A(8,4)=13.7 invalid-bound bug).
3. macOS has no `timeout` command; use the Bash tool's timeout and time-cap sweeps in-code (per-cell
   try/except + budget) — the naive-clamp A(19,6) run hung >10 min before the LP existed.
4. Operator-local deps (cvxpy/numpy/ortools/docker) must be `find_spec`/`available()`-gated so CI skips clean.
5. `python3` (not `python`); `ruff check` before commit; `pytest -q tests/test_invariants.py` must stay 11/11.

**Process constants:** branch `terwilliger-<ticket>` → PR to main (body ends with the Claude Code attribution
line) → CI (invariants lane, ~3.5 min; docker/cvxpy tests skip there — run them locally before pushing) →
**operator merges** (`gh pr merge <n> --admin --squash --delete-branch`). Results doc in `docs/results/`,
roadmap bullet appended in `docs/optimization-roadmap.md` (Terwilliger section, near line ~390). Trust
invariants: never edit `tests/test_invariants.py` or guarded files; all of this work is audit-tier.

---

## Ticket ① (task #99) — beyond-Table-I discovery reach probe  ← START HERE

**Kickoff prompt:**
> Run the Terwilliger beyond-Table-I discovery reach probe — task #99. Read
> `docs/handoff-terwilliger-sessions-2026-07-01.md` (ticket ①) first, then
> `docs/terwilliger-formalization-scope-2026-07-01.md` (discovery outlook).

**Question it answers:** can this producer *discover* (tighten a current best-known upper bound), or only
reproduce? This decides whether the F2b formalization spend has a discovery payoff.

**Design (one session, operator-local, ~$0):**
1. **Snapshot targets.** Fetch Brouwer's table (`https://www.win.tue.nl/~aeb/codes/binary-1.html`) for
   unrestricted binary cells, n = 20..30, d ∈ {6, 8, 10, 12} (even d only — the machinery is validated for
   even d; odd d goes via A(n,d)=A(n+1,d+1) and is out of scope for the probe). Check in
   `docs/data/brouwer-snapshot-2026-07.json`: `{(n,d): {"lb": .., "ub": .., "ub_source": ".."}}`.
   **Trust note:** the snapshot is targeting context only — never a decider; soundness stays with the kernel.
2. **Sweep, cheap-first.** For each cell: `run_numerical(n,d)` (float, seconds) with a per-cell time cap
   (~120 s) and try/except; record `sdp_floor` vs snapshot ub. Expect solver strain to grow with n
   (conditioning, Q-pit-2) — record failures honestly, they are the n-scaling measurement.
3. **Escalate only candidates.** Where `sdp_floor < snapshot_ub`: run `certify_lp(n,d,target=sdp_floor)` for
   the exact certificate, then `kernel_verify_lp`. A candidate counts ONLY with a certified exact bound.
4. **Deliverables:** `scripts/terwilliger_reach_probe.py` (+ gated test) writing
   `docs/results/terwilliger_reach_probe.json`; results doc `docs/results/terwilliger-reach-probe-<date>.md`;
   roadmap bullet; PR.

**Gate:** **GREEN(candidate)** = ≥1 cell with a *certified exact* bound strictly below the snapshot ub —
stop and surface to the operator immediately (that is a publishable discovery claim; it will need independent
re-verification of the snapshot value before any announcement). **DRY** = 0 candidates — record honestly;
this is the *expected* outcome (post-2005 literature already applied stronger SDPs to these cells), and it
pivots the discovery effort to: eq. (25) sharpenings, the Johnson-scheme build (panel D1), or post-2005
hierarchies — an operator decision, not this session's.

**Honest expectations:** low hit-rate. The probe's guaranteed value is (a) the empirical answer, (b) the
n-scaling profile of solve/LP/kernel beyond n=19, (c) reproduction-banking of any Table I cells that pass
through the pipeline on the way.

---

## Ticket ② (task #100) — F1: whole-certificate-in-kernel

**Kickoff prompt:**
> Build Terwilliger F1 (whole-cert-in-kernel) — task #100. Read
> `docs/terwilliger-formalization-scope-2026-07-01.md` §F1 (incl. cold-start pointers) first; state snapshot
> and traps in `docs/handoff-terwilliger-sessions-2026-07-01.md`.

Fully specified in the scope doc §F1 (design, measured sizing, exit tests with 4 corrupted controls, risks,
cold-start pointers). One-line reminder of the core insight: **the Lean checker's spec is `collected()` in
`scripts/terwilliger_dual.py` — transcribe it; do not re-derive the dual.** Benchmark the k=0 β slice first.
Independent of ticket ① — can run in parallel with it.

## Ticket ③ (task #101) — F2a: weak duality in Lean/Mathlib (then the F2b/F2c decision)

**Kickoff prompt:**
> Build Terwilliger F2a (weak duality in Lean/Mathlib) — task #101. Read
> `docs/terwilliger-formalization-scope-2026-07-01.md` §F2 first.

Fully specified in the scope doc §F2a (statement sketch, Mathlib pieces). Sequencing note: best after ① and ②
(① tells the operator whether F2b is discovery-motivated; ② produces the kernel-side definitions F2a's
statement should align with). Ends with two operator decisions: send the F2b external brief (drafted in the
scope doc), and the F2c tier question (gated Q.E.D. wiring vs Observatory tier per ADR 0038).

---

## Sequencing
**① first** (cheap, decision-making) → **②** (independent; parallelizable with ①) → **③** → operator
decisions on F2b/F2c. Standing parked items unchanged: task #54 (kernel bridge, gated), task #68 (C
proof-edge trust edits, deferred pending witness round).
